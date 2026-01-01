"""
Dynamic Asset Management System for OSRS-Themed Dashboard
Provides context-aware selection of backgrounds, borders, and icons
"""

import os
import random
import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class AssetContext(Enum):
    """Context categories for asset selection"""
    PVM = "pvm"              # Boss kills, combat stats
    SOCIAL = "social"         # Messages, activity
    SKILLS = "skills"         # XP gains, skill levels
    GENERAL = "general"       # Default/mixed content
    LEADERBOARD = "leaderboard"  # Rankings
    MILESTONE = "milestone"   # Achievements

class ThemeStyle(Enum):
    """Visual theme styles"""
    PARCHMENT = "parchment"   # Old paper texture
    ORNATE = "ornate"         # Gold borders, fancy
    DARK = "dark"             # Dark stone/wood
    MAGICAL = "magical"       # Glowing, mystical

class AssetManager:
    """Manages dynamic asset selection based on data context"""
    
    # Map contexts to preferred color schemes
    CONTEXT_COLORS = {
        AssetContext.PVM: {
            'primary': '#8B0000',      # Dark red (blood)
            'secondary': '#FF4500',    # Orange-red
            'border': '#DAA520',       # Goldenrod
            'bg': 'rgba(139, 0, 0, 0.15)'
        },
        AssetContext.SOCIAL: {
            'primary': '#4169E1',      # Royal blue
            'secondary': '#00BFFF',    # Deep sky blue
            'border': '#4682B4',       # Steel blue
            'bg': 'rgba(65, 105, 225, 0.15)'
        },
        AssetContext.SKILLS: {
            'primary': '#228B22',      # Forest green
            'secondary': '#32CD32',    # Lime green
            'border': '#FFD700',       # Gold
            'bg': 'rgba(34, 139, 34, 0.15)'
        },
        AssetContext.GENERAL: {
            'primary': '#8B4513',      # Saddle brown
            'secondary': '#D2691E',    # Chocolate
            'border': '#CD853F',       # Peru
            'bg': 'rgba(139, 69, 19, 0.15)'
        },
        AssetContext.LEADERBOARD: {
            'primary': '#FFD700',      # Gold
            'secondary': '#FFA500',    # Orange
            'border': '#FF8C00',       # Dark orange
            'bg': 'rgba(255, 215, 0, 0.15)'
        },
        AssetContext.MILESTONE: {
            'primary': '#9370DB',      # Medium purple
            'secondary': '#BA55D3',    # Medium orchid
            'border': '#DDA0DD',       # Plum
            'bg': 'rgba(147, 112, 219, 0.15)'
        }
    }
    
    # Map contexts to preferred boss fallbacks
    CONTEXT_BOSS_FALLBACKS = {
        AssetContext.PVM: [
            'boss_tztok_jad.png',
            'boss_nex.png', 
            'boss_corporeal_beast.png',
            'boss_zulrah.png'
        ],
        AssetContext.SOCIAL: [
            'boss_pet_rock.png',
            'boss_baby_mole.png',
            'boss_gull_(pet).png'
        ],
        AssetContext.SKILLS: [
            'boss_phoenix.png',
            'boss_rocky.png',
            'boss_giant_squirrel.png'
        ],
        AssetContext.GENERAL: [
            'boss_pet_rock.png',
            'boss_chaos_elemental.png'
        ],
        AssetContext.LEADERBOARD: [
            'boss_tzkal-zuk.png',
            'boss_infernal_cape.png',
            'boss_fire_cape.png'
        ],
        AssetContext.MILESTONE: [
            'boss_phoenix.png',
            'boss_vorki.png',
            'boss_hellpuppy.png'
        ]
    }
    
    @classmethod
    def get_context_style(cls, context: AssetContext) -> Dict[str, str]:
        """Get color scheme for a given context"""
        return cls.CONTEXT_COLORS.get(context, cls.CONTEXT_COLORS[AssetContext.GENERAL])
    
    @classmethod
    def get_boss_fallback(cls, context: AssetContext, assets_dir: str = "assets") -> str:
        """Get context-appropriate boss image fallback"""
        fallbacks = cls.CONTEXT_BOSS_FALLBACKS.get(
            context, 
            cls.CONTEXT_BOSS_FALLBACKS[AssetContext.GENERAL]
        )
        
        # Try each fallback in order until we find one that exists
        for img in fallbacks:
            path = os.path.join(assets_dir, img)
            if os.path.exists(path):
                return img
        
        # Ultimate fallback
        return 'boss_pet_rock.png'
    
    @classmethod
    def get_rank_fallback(cls, context: AssetContext, assets_dir: str = "assets") -> str:
        """Get context-appropriate rank image fallback"""
        # Map contexts to rank styles
        context_ranks = {
            AssetContext.PVM: ['rank_legend.png', 'rank_champion.png', 'rank_warrior.png'],
            AssetContext.SOCIAL: ['rank_helper.png', 'rank_friend.png', 'rank_member.png'],
            AssetContext.SKILLS: ['rank_maxed.png', 'rank_master.png', 'rank_expert.png'],
            AssetContext.LEADERBOARD: ['rank_dragon.png', 'rank_rune.png', 'rank_adamant.png'],
            AssetContext.GENERAL: ['rank_member.png', 'rank_recruit.png']
        }
        
        ranks = context_ranks.get(context, context_ranks[AssetContext.GENERAL])
        
        for img in ranks:
            path = os.path.join(assets_dir, img)
            if os.path.exists(path):
                return img
        
        return 'rank_minion.png'
    
    @classmethod
    def generate_css_classes(cls) -> str:
        """Generate CSS classes for all contexts"""
        css_lines = ["/* Auto-generated context styles */\n"]
        
        for context in AssetContext:
            style = cls.get_context_style(context)
            class_name = f"context-{context.value}"
            
            css_lines.append(f".{class_name} {{")
            css_lines.append(f"  --primary-color: {style['primary']};")
            css_lines.append(f"  --secondary-color: {style['secondary']};")
            css_lines.append(f"  --border-color: {style['border']};")
            css_lines.append(f"  --bg-overlay: {style['bg']};")
            css_lines.append("}\n")
            
            # Card style
            css_lines.append(f".card.{class_name} {{")
            css_lines.append(f"  background: linear-gradient(135deg, {style['bg']}, rgba(0,0,0,0.3));")
            css_lines.append(f"  border: 2px solid {style['border']};")
            css_lines.append(f"  box-shadow: 0 4px 12px {style['bg']}, 0 0 20px {style['bg']};")
            css_lines.append("}\n")
        
        return "\n".join(css_lines)
    
    @classmethod
    def select_texture(cls, context: AssetContext, theme: ThemeStyle = ThemeStyle.PARCHMENT) -> str:
        """Select appropriate background texture CSS"""
        # Map to CSS background properties
        textures = {
            ThemeStyle.PARCHMENT: "background: linear-gradient(to bottom, #f4e8d0, #e8d7b0); background-image: url('data:image/svg+xml,%3Csvg width=\"100\" height=\"100\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cfilter id=\"noise\"%3E%3CfeTurbulence baseFrequency=\"0.9\" /%3E%3C/filter%3E%3Crect width=\"100\" height=\"100\" filter=\"url(%23noise)\" opacity=\"0.05\" /%3E%3C/svg%3E');",
            ThemeStyle.ORNATE: "background: radial-gradient(ellipse at center, #3a2f1f 0%, #1a1510 100%); border: 3px solid #d4af37; box-shadow: inset 0 0 30px rgba(212, 175, 55, 0.3);",
            ThemeStyle.DARK: "background: linear-gradient(135deg, #2c2416 0%, #1a1510 50%, #2c2416 100%); background-image: url('data:image/svg+xml,%3Csvg width=\"100\" height=\"100\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cfilter id=\"grain\"%3E%3CfeTurbulence baseFrequency=\"2.5\" /%3E%3C/filter%3E%3Crect width=\"100\" height=\"100\" filter=\"url(%23grain)\" opacity=\"0.08\" /%3E%3C/svg%3E');",
            ThemeStyle.MAGICAL: "background: radial-gradient(ellipse at center, rgba(147, 112, 219, 0.2) 0%, rgba(75, 0, 130, 0.3) 100%); box-shadow: 0 0 30px rgba(138, 43, 226, 0.5), inset 0 0 20px rgba(138, 43, 226, 0.2);"
        }
        
        return textures.get(theme, textures[ThemeStyle.PARCHMENT])
    
    @classmethod
    def get_chart_theme(cls, context: AssetContext) -> Dict:
        """Get G2Plot/Chart.js theme configuration for context"""
        style = cls.get_context_style(context)
        
        return {
            'colors': [style['primary'], style['secondary'], style['border']],
            'fontFamily': "'MedievalSharp', 'Cinzel', serif",
            'backgroundColor': style['bg'],
            'borderColor': style['border']
        }

# Generate CSS file on import
if __name__ == "__main__":
    css = AssetManager.generate_css_classes()
    with open("assets/dynamic_styles.css", "w") as f:
        f.write(css)
    logger.info("Generated dynamic_styles.css")
