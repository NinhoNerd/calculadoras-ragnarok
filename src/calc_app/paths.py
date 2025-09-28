# src/calc_app/paths.py
"""
File & directory resolution helpers.

This module centralizes how the app locates:
- Packaged read-only assets (JSONs, icons) both in dev and when frozen (PyInstaller).
- User-writable files (profile.json, future prices.json) in a cross-platform way.

Order of sections:
1) Imports & config constants
2) Frozen-app detection
3) Packaged base directories (calc_app/, assets/, ...)
4) Packaged files (defaults/catalog/rules JSON paths)
5) User data directories (per-user writable)
6) Public convenience getters used elsewhere (data_store, icons, etc.)
"""

from pathlib import Path
import os
import sys
import platform

from calc_app.config import (
    APP_NAME,
    PROFILE_DEFAULT_JSON_NAME,
    ITEM_PRICE_DEFAULT_JSON_NAME,
    CATALOG_JSON_NAME,
    PROFILE_JSON_NAME,
    PHARMACY_SPECIAL_RULES_JSON_NAME,
    PRICES_JSON_NAME
)

# ---------------------------------------------------------------------
# 1) Frozen / dev detection
# ---------------------------------------------------------------------

def is_frozen() -> bool:
    """Return True if running under a PyInstaller-built executable."""
    return hasattr(sys, "_MEIPASS")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------
# 2) Packaged base directories (read-only)
# ---------------------------------------------------------------------

def base_dir() -> Path:
    """
    Root package directory that contains 'assets/'.
      Dev:     <repo>/src/calc_app
      Frozen:  <temp>/_MEIPASS/calc_app
    """
    if is_frozen():
        return Path(sys._MEIPASS) / "calc_app"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent

def assets_dir() -> Path:
    """calc_app/assets"""
    return base_dir() / "assets"

def defaults_dir() -> Path:
    """calc_app/assets/defaults"""
    return assets_dir() / "defaults"

def catalog_dir() -> Path:
    """calc_app/assets/catalog"""
    return assets_dir() / "catalog"

def skills_dir() -> Path:
    """
    Location for skill/mechanics JSON rules.
    (You mentioned this folder name might change later—keep usage centralized here.)
    """
    return assets_dir() / "skills"

def icons_root_dir() -> Path:
    """calc_app/assets/icons (root for item/skill/social icon sets)"""
    return assets_dir() / "icons"

def item_icons_dir() -> Path:
    """calc_app/assets/icons/items  (PNG files named '<id>.png')"""
    return icons_root_dir() / "items"

def skill_icons_dir() -> Path:
    """calc_app/assets/icons/skills  (skill PNGs named '<key>.png')"""
    return icons_root_dir() / "skills"

def social_icons_dir() -> Path:
    """calc_app/assets/icons/social  (social PNGs named 'instagram.png', etc.)"""
    return icons_root_dir() / "social"


# ---------------------------------------------------------------------
# 3) Packaged files (read-only JSON assets)
# ---------------------------------------------------------------------

def packaged_default_profile_path() -> Path:
    """Default profile JSON shipped with the app (fallback for first run)."""
    return defaults_dir() / PROFILE_DEFAULT_JSON_NAME

def packaged_items_catalog_path() -> Path:
    """Item catalog JSON (id ↔ name, optional extras)."""
    return catalog_dir() / CATALOG_JSON_NAME

def packaged_pharmacy_special_rules_path() -> Path:
    """Special Pharmacy rules JSON (caps, base difficulties, item lists)."""
    return skills_dir() / PHARMACY_SPECIAL_RULES_JSON_NAME

def packaged_default_prices_path() -> Path:
    """Default prices JSON shipped with the app (used by reset)."""
    return defaults_dir() / ITEM_PRICE_DEFAULT_JSON_NAME

# ---------------------------------------------------------------------
# 4) User-writable locations
# ---------------------------------------------------------------------

def _user_data_root() -> Path:
    """
    Cross-platform per-user data directory.
      Windows: %APPDATA%/APP_NAME
      macOS:   ~/Library/Application Support/APP_NAME
      Linux:   ~/.local/share/APP_NAME
    """
    system = platform.system()
    home = Path.home()

    if system == "Windows":
        base = Path(os.getenv("APPDATA") or (home / "AppData" / "Roaming"))
        return base / APP_NAME
    elif system == "Darwin":
        return home / "Library" / "Application Support" / APP_NAME
    else:
        return Path(os.getenv("XDG_DATA_HOME") or (home / ".local" / "share")) / APP_NAME

def ensure_user_data_dir() -> Path:
    """Create the per-user data directory if missing and return it."""
    p = _user_data_root()
    p.mkdir(parents=True, exist_ok=True)
    return p

def user_profile_path() -> Path:
    """Path where the user's profile is saved/loaded (writable)."""
    return ensure_user_data_dir() / PROFILE_JSON_NAME

def user_prices_path() -> Path:
    """Path where the user's prices.json would live (future feature)."""
    return ensure_user_data_dir() / PRICES_JSON_NAME


# ---------------------------------------------------------------------
# 5) Public convenience getters
# ---------------------------------------------------------------------

def catalog_json() -> Path:
    """Return the packaged catalog JSON path."""
    return packaged_items_catalog_path()

def pharmacy_special_rules_json() -> Path:
    """Return the packaged Special Pharmacy rules JSON path."""
    return packaged_pharmacy_special_rules_path()

def profile_default_json() -> Path:
    """Return the packaged default profile JSON path."""
    return packaged_default_profile_path()

def user_profile_json() -> Path:
    """Return the per-user writable profile JSON path."""
    return user_profile_path()

def prices_default_json() -> Path:
    """Return packaged default prices.json path."""
    return packaged_default_prices_path()

def user_prices_json() -> Path:
    """Return per-user writable prices.json path."""
    return user_prices_path()
