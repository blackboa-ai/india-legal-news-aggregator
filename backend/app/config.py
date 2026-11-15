"""
Configuration alias re-exporting Settings from app.core.config.
Maintains compatibility with both app.config and app.core.config imports.
"""

from app.core.config import Settings, settings

__all__ = ["Settings", "settings"]
