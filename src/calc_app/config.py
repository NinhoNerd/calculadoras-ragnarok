# src/calc_app/config.py
from pathlib import Path
from PySide6.QtCore import QSize
import sys
import os

# =========================
# App metadata
# =========================
APP_NAME    = "Calculadora Ragnarok"
APP_VERSION = "0.1.0"
ORG_NAME    = "NinhoNerd"

# =========================
# UI defaults / sizes (ints; wrap into QSize in UI code)
# =========================
LEFT_PANE_WIDTH = 320
DEBOUNCE_MS     = 150
TABLE_ICON_PX   = 20
TAB_ICON_PX     = 18
SOCIAL_ICON_PX  = 36
SOCIAL_BUTTON_W = 200
SOCIAL_BUTTON_H = 60
SOCIAL_BUTTON_SIZE = (SOCIAL_BUTTON_W,SOCIAL_BUTTON_H)

# =========================
# Behavior toggles / feature flags
# =========================
HIDE_HISTOGRAM_Y_TICKS = True
ENABLE_BETA_TABS       = False

# =========================
# Tabs / modules & social links
# =========================
TAB_NAMES = {
    "farmacologia_avancada": "Farmacologia Avançada",
    "prepare_potion": "Preparar Poção",
    "advanced_cooking": "Culinária Avançada",
    "rune_mastery": "Perícia em Runas",
    "create_deadly_poison":"Criar Veneno Mortal",
    "new_poison_creation":"Criar Toxina",
    "price_base": "Base Preços",
    "production_cost": "Custo de Produção",
}

# Initial size for the Welcome view (locked)
DEFAULT_FIXED_SIZE = QSize(550, 700)

TAB_FIXED_SIZES = {
    "farmacologia_avancada": QSize(1200, 780),
    "prepare_potion": QSize(1000, 680),
    "advanced_cooking": QSize(1100, 720),
    "Perícia em Runas": QSize(950, 640),
    "price_base": QSize(1100, 720),
    "production_cost": QSize(1150, 740),
}
# (label, icon_key) — icon_key is used by icons.icon_for_skill(...)
BUTTON_SPECS = {
    "Farmacologia Avançada":"pharmacy_sp",
    "Preparar Poção":"pharmacy",
    "Culinária Avançada":"cooking_mix",
    "Perícia em Runas":"runes",
    "Criar Veneno Mortal":"create_deadly_poison",
    "Criar Toxina":"new_poison_creation",
    "Base Preços":"prices",
    "Custo de Produção":"costs"
}

# keys must match assets/icons/social/<key>.png when present
SOCIAL_LINKS = [
    ("instagram", "@ninhonerd_",            "https://www.instagram.com/ninhonerd_"),
    ("youtube",   "@ninhonerd",             "https://youtube.com/@ninhonerd"),
    ("github",    "@calculadoras-ragnarok", "https://github.com/NinhoNerd/calculadoras-ragnarok"),
]

# Optional per-skill metadata. If a skill is not listed here,
# the UI will default to range (0..10) and a prettified label.
SKILL_META = {
    "potion_research":          {"label": "Pesquisa de Poções",         "min": 0, "max": 10},
    "chemical_protection_full": {"label": "Proteção Química Total",     "min": 0, "max": 5},
    "advanced_pharmacy":        {"label": "Farmacologia Avançada",      "min": 1, "max": 10},
    "pharmacy":                 {"label": "Farmácia",                   "min": 1, "max": 10},
}


# =========================
# Asset file names (inside the package)
# =========================
CATALOG_JSON_NAME         = "items.json"          # id/name catalog
PHARMACY_SPECIAL_RULES_JSON_NAME  = "pharmacy_special.json"       # optional: per-skill fixed tables
CONSTRAINTS_JSON_NAME     = "constraints.v1.json" # optional: min/max clamps
PROFILE_DEFAULT_JSON_NAME      = "profile.default.json"
ITEM_PRICE_DEFAULT_JSON_NAME      = "prices.json"


# =========================
# User file names (user-writable, outside the package)
# =========================
PROFILE_JSON_NAME = "profile.json"  # user profile (stats/levels/skills)
PRICES_JSON_NAME  = "prices.json"   # (future) market prices

# =========================
# Packaged assets location (dev & PyInstaller)
# =========================
def PACKAGE_BASE() -> Path:
    """Root path for packaged assets."""
    if hasattr(sys, "_MEIPASS"):  # PyInstaller
        return Path(sys._MEIPASS) / "calc_app"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent

ASSETS_DIR       = PACKAGE_BASE() / "assets"
CATALOG_DIR      = ASSETS_DIR / "catalog"
DEFAULTS_DIR     = ASSETS_DIR / "defaults"

# icons layout:
ICONS_DIR        = ASSETS_DIR / "icons"
ITEM_ICONS_DIR   = ICONS_DIR / "items"
SKILL_ICONS_DIR  = ICONS_DIR / "skills"
SOCIAL_ICONS_DIR = ICONS_DIR / "social"

# =========================
# Cross-platform user data directories
# =========================
def USER_DATA_DIR() -> Path:
    """Per-user writable directory for settings/profiles/prices."""
    if os.name == "nt":  # Windows
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / APP_NAME
    elif sys.platform == "darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:  # Linux & others
        return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / APP_NAME

def USER_PROFILES_DIR() -> Path:
    return USER_DATA_DIR() / "profiles"

def USER_PRICES_DIR() -> Path:
    return USER_DATA_DIR() / "prices"
