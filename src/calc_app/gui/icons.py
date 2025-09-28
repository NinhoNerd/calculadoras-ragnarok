"""
Icon loading helpers (Qt QIcon) with simple in-memory caching.

Responsibilities
---------------
• Provide a tiny, centralized API to fetch:
  - item icons by item *id* or *name*
  - skill icons by key
  - social icons by name

• Use project-wide paths from `calc_app.config` so dev and PyInstaller
  builds both work transparently.

• Return `None` when an icon is missing — the UI layer decides on fallbacks
  (e.g., `style().standardIcon(...)`), keeping this module pure.
"""

from pathlib import Path
from typing import Optional, Dict

from PySide6.QtGui import QIcon

# Centralized, packaging-aware paths:
from calc_app.config import ITEM_ICONS_DIR, SKILL_ICONS_DIR, SOCIAL_ICONS_DIR

# Catalog resolver to translate item names → ids when needed.
from ..core.catalog import name_to_id

# Simple shared cache so we don’t reload the same images repeatedly.
_ICON_CACHE: Dict[str, QIcon] = {}


def _icon_from(path: Path, cache_key: str) -> Optional[QIcon]:
    """
    Load an icon from a file path with caching.
    - Returns None if the file does not exist.
    - Caches by an explicit key so callers can choose stable names.
    """
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]
    if not path.exists():
        return None
    icon = QIcon(str(path))
    _ICON_CACHE[cache_key] = icon
    return icon


# ---------------------------------------------------------------------------
# Item icons
# ---------------------------------------------------------------------------

def icon_for_item_id(item_id: int) -> Optional[QIcon]:
    """
    Load an item icon using its numeric id.
    Expects files like:  assets/icons/items/<item_id>.png
    """
    return _icon_from(ITEM_ICONS_DIR / f"{item_id}.png", f"item:{item_id}")


def icon_for_item_name(item_name: str) -> Optional[QIcon]:
    """
    Load an item icon using the human-readable name:
    - Resolves name → id via the catalog.
    - Delegates to icon_for_item_id.
    """
    iid = name_to_id(item_name)
    if iid is None:
        return None
    return icon_for_item_id(iid)


# ---------------------------------------------------------------------------
# Skill icons
# ---------------------------------------------------------------------------

def icon_for_skill(key: str) -> Optional[QIcon]:
    """
    Load a skill icon by key.
    Expects files like:  assets/icons/skills/<key>.png

    Example keys (per your config.BUTTON_SPECS):
      "pharmacy_adv", "pharmacy", "cooking_adv", "cooking", "prices", "costs"
    """
    return _icon_from(SKILL_ICONS_DIR / f"{key}.png", f"skill:{key}")


# ---------------------------------------------------------------------------
# Social icons
# ---------------------------------------------------------------------------

def icon_for_social(name: str) -> Optional[QIcon]:
    """
    Load a social icon by name.
    Expects files like:  assets/icons/social/<name>.png

    Common names: "instagram", "youtube", "github"
    """
    key = name.lower()
    return _icon_from(SOCIAL_ICONS_DIR / f"{key}.png", f"social:{key}")


# ---------------------------------------------------------------------------
# Dev utility
# ---------------------------------------------------------------------------

def clear_icon_cache() -> None:
    """Clear the in-memory icon cache (useful in live-reload/dev tools)."""
    _ICON_CACHE.clear()
