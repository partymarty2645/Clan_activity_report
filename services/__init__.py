"""
Service Initialization Rules:
- NEVER instantiate services at module level
- ALWAYS use ServiceFactory for singleton access
- Tests should use ServiceFactory.set_*() for mocking
"""

from .factory import ServiceFactory
from .wom import WOMClient
from .discord import DiscordFetcher

__all__ = [
    "ServiceFactory",
    "WOMClient",
    "DiscordFetcher",
]