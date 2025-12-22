"""
UsernameNormalizer - Centralized username handling and comparison.

This module provides a single source of truth for all username normalization logic
across the ClanStats project. All scripts should use these functions instead of
rolling their own normalization.

Design Principles:
- Single responsibility: normalize usernames consistently
- Support multiple comparison modes: fuzzy vs strict
- Handle unicode, spaces, underscores, hyphens
- Fail gracefully on invalid input
"""

import logging
import re
from typing import Optional

logger = logging.getLogger("UsernameNormalizer")


class UsernameNormalizer:
    """
    Centralized username normalization and comparison.
    
    Supports multiple normalization strategies:
    1. normalize() - for comparison (strict, removes all non-alphanumeric)
    2. canonical() - for display (preserves case, cleans whitespace)
    3. are_same_user() - direct comparison of two usernames
    """

    # Regex patterns for character validation
    VALID_USERNAME_PATTERN = re.compile(r'^[\w\s\-]{1,255}$', re.UNICODE)
    WHITESPACE_PATTERN = re.compile(r'\s+')
    SPECIAL_CHARS = re.compile(r'[\s_\-]+')

    @staticmethod
    def normalize(name: Optional[str], for_comparison: bool = True) -> str:
        """
        Normalize a username for comparison or storage.
        
        Args:
            name: The username to normalize
            for_comparison: If True, removes all non-alphanumeric for maximum flexibility.
                          If False, preserves structure but cleans whitespace.
        
        Returns:
            Normalized username (lowercase), or empty string if invalid
            
        Examples:
            >>> UsernameNormalizer.normalize("J O H N")
            "john"
            
            >>> UsernameNormalizer.normalize("Jo_hn-Doe")
            "johndoe"
            
            >>> UsernameNormalizer.normalize("Jo_hn-Doe", for_comparison=False)
            "johmDoe"
            
            >>> UsernameNormalizer.normalize(None)
            ""
            
            >>> UsernameNormalizer.normalize("   ")
            ""
        """
        if not name:
            return ""

        # Handle non-string types
        if not isinstance(name, str):
            logger.warning(f"normalize() called with non-string: {type(name).__name__}")
            return ""

        # Strip leading/trailing whitespace
        name = name.strip()

        if not name:
            return ""

        # Validate length
        if len(name) > 255:
            logger.warning(f"normalize() called with overly long username ({len(name)} chars)")
            return ""

        # Replace various whitespace characters (including unicode spaces) with standard space
        name = re.sub(r'[\s\u00A0\u2000-\u200B\uFEFF]+', ' ', name)

        if for_comparison:
            # For comparison: remove all non-alphanumeric characters
            # This handles: "J O H N", "Jo-hn_Doe", "JöHñ" etc.
            name = ''.join(c for c in name if c.isalnum())
        else:
            # For display/storage: just clean up spacing and underscores/hyphens
            # Replace underscores and hyphens with spaces, then collapse multiple spaces
            name = re.sub(UsernameNormalizer.SPECIAL_CHARS, ' ', name)
            name = re.sub(r'\s+', ' ', name)

        # Lowercase for comparison
        name = name.lower()

        # Final validation: must have at least one alphanumeric character
        if not re.search(r'\w', name):
            logger.debug(f"normalize() resulted in invalid username: {name}")
            return ""

        return name

    @staticmethod
    def canonical(name: Optional[str]) -> str:
        """
        Normalize a username for display while preserving readability.
        
        This is useful for Discord author names where we want to preserve
        the original casing and structure, but clean up whitespace.
        
        Args:
            name: The username to canonicalize
            
        Returns:
            Canonical form (original case preserved, whitespace cleaned)
            
        Examples:
            >>> UsernameNormalizer.canonical("J O H N")
            "J O H N"  (whitespace normalized)
            
            >>> UsernameNormalizer.canonical("DocOfMed")
            "DocOfMed"
        """
        if not name:
            return ""

        if not isinstance(name, str):
            return ""

        # Strip and normalize whitespace (including unicode spaces)
        name = name.strip()
        name = re.sub(r'[\s\u00A0\u2000-\u200B\uFEFF]+', ' ', name)

        return name

    @staticmethod
    def are_same_user(name1: Optional[str], name2: Optional[str]) -> bool:
        """
        Check if two username strings refer to the same user.
        
        Uses strict comparison after normalization.
        
        Args:
            name1: First username
            name2: Second username
            
        Returns:
            True if both normalize to the same value, False otherwise
            
        Examples:
            >>> UsernameNormalizer.are_same_user("J O H N", "john")
            True
            
            >>> UsernameNormalizer.are_same_user("Jo-hn_Doe", "johndoe")
            True
            
            >>> UsernameNormalizer.are_same_user("john", "jane")
            False
        """
        if not name1 or not name2:
            return name1 == name2

        norm1 = UsernameNormalizer.normalize(name1, for_comparison=True)
        norm2 = UsernameNormalizer.normalize(name2, for_comparison=True)

        if not norm1 or not norm2:
            # If normalization failed for either, they're not the same
            return False

        return norm1 == norm2

    @staticmethod
    def validate(name: Optional[str]) -> tuple[bool, Optional[str]]:
        """
        Validate a username for unusual characters or patterns.
        
        Args:
            name: The username to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - If valid: (True, None)
            - If invalid: (False, error_message)
            
        Examples:
            >>> UsernameNormalizer.validate("john")
            (True, None)
            
            >>> UsernameNormalizer.validate("j!@#")
            (False, "Username contains invalid characters: !@#")
        """
        if not name:
            return False, "Username is empty"

        if not isinstance(name, str):
            return False, f"Username must be string, got {type(name).__name__}"

        if len(name) > 255:
            return False, f"Username too long: {len(name)} characters (max 255)"

        # Check for invalid characters (but allow spaces, underscores, hyphens)
        invalid_chars = set()
        for char in name:
            if not (char.isalnum() or char in ' _-' or ord(char) > 127):
                invalid_chars.add(char)

        if invalid_chars:
            return False, f"Username contains invalid characters: {repr(''.join(invalid_chars))}"

        # Must have at least one letter or digit
        if not any(c.isalnum() for c in name):
            return False, "Username must contain at least one letter or digit"

        return True, None
