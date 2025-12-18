"""
Data validation utilities for clan statistics
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("Validators")


class DataValidator:
    """Validates and sanitizes clan data"""
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate OSRS username format"""
        if not username or not isinstance(username, str):
            return False
        username = username.strip()
        if len(username) < 1 or len(username) > 12:
            return False
        # OSRS usernames: alphanumeric, spaces, hyphens, underscores
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_")
        return all(c in allowed for c in username)
    
    @staticmethod
    def validate_role(role: str) -> bool:
        """Validate clan role"""
        valid_roles = {'owner', 'deputy_owner', 'overseer', 'coordinator', 
                      'organizer', 'admin', 'administrator', 'general', 'corporal', 
                      'sergeant', 'lieutenant', 'captain', 'recruit', 'member',
                      'zenyte', 'dragonstone', 'saviour', 'prospector'}
        return role.lower() in valid_roles
    
    @staticmethod
    def sanitize_stats_dict(stats: Dict) -> Dict:
        """Sanitize and validate statistics dictionary"""
        sanitized = {}
        
        # Ensure numeric values are valid
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                if value < 0:
                    logger.warning(f"Negative value for {key}: {value}, setting to 0")
                    sanitized[key] = 0
                elif value > 1e15:  # Sanity check for unrealistic values
                    logger.warning(f"Unrealistic value for {key}: {value}, capping")
                    sanitized[key] = min(value, 1e15)
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value
                
        return sanitized
    
    @staticmethod
    def validate_timestamp(ts: datetime) -> bool:
        """Validate timestamp is reasonable"""
        if not isinstance(ts, datetime):
            return False
        
        # Must be after OSRS release (2013-02-22)
        osrs_release = datetime(2013, 2, 22, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        
        # Make timezone-aware comparison
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
            
        return osrs_release <= ts <= now
    
    @staticmethod
    def validate_report_data(data_list: List[Dict]) -> tuple[List[Dict], List[str]]:
        """
        Validate report data and return clean data + warnings.
        
        Returns:
            (clean_data, warnings)
        """
        clean_data = []
        warnings = []
        
        for idx, entry in enumerate(data_list):
            username = entry.get('Username', '').lower()
            
            # Validate username
            if not DataValidator.validate_username(username):
                warnings.append(f"Row {idx}: Invalid username '{username}'")
                continue
            
            # Validate role if present
            role = entry.get('Role', 'member')
            if not DataValidator.validate_role(role):
                warnings.append(f"Row {idx}: Invalid role '{role}' for {username}, defaulting to 'member'")
                entry['Role'] = 'member'
            
            # Sanitize numeric columns
            entry = DataValidator.sanitize_stats_dict(entry)
            clean_data.append(entry)
        
        if warnings:
            logger.warning(f"Data validation found {len(warnings)} issues")
            for w in warnings[:10]:  # Log first 10 warnings
                logger.warning(w)
        
        return clean_data, warnings


class ConfigValidator:
    """Validates configuration settings"""
    
    @staticmethod
    def validate_config(config) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Required fields
        if not config.WOM_GROUP_ID:
            issues.append("WOM_GROUP_ID is not set")
        
        if not config.DISCORD_TOKEN:
            issues.append("DISCORD_TOKEN is not set")
        
        if not config.WOM_API_KEY:
            issues.append("WOM_API_KEY is not set (optional but recommended)")
        
        # Numeric validations
        if hasattr(config, 'WOM_TARGET_RPM') and config.WOM_TARGET_RPM:
            rpm = int(config.WOM_TARGET_RPM)
            if rpm < 1 or rpm > 200:
                issues.append(f"WOM_TARGET_RPM ({rpm}) outside reasonable range (1-200)")
        
        # Color format validation
        color_fields = ['COLOR_IDENTITY', 'COLOR_XP', 'COLOR_MESSAGES', 'COLOR_BOSS']
        for field in color_fields:
            if hasattr(config, field):
                color = getattr(config, field)
                if not color.startswith('#') or len(color) != 7:
                    issues.append(f"{field} ({color}) is not a valid hex color")
        
        return issues
