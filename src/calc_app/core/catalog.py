# src/calc_app/core/catalog.py
"""
Catalog (items) — id/name resolution helpers + lean recipe parsing.

Supported catalog JSON shapes:
1) List of objects (items.v1):
   {"schema":"items.v1","items":[{"id":6210,"name_pt":"...", "type":"...", "recipe":"10_713+10_509+1_7455+5_528"}, ...]}
2) Plain list of objects:
   [{"id":6210,"name_pt":"...", "type":"...", "recipe":"..."} , ...]
3) Mapping by id:
   {"6210": {"name_pt":"...", "type":"...", "recipe":"..."} , ...}

Display name preference: 'name_pt', then 'name_en', then 'name'.

Recipe format (simplified, fixed):
Always a string like: "10_713+10_509+1_7455+5_528"
Meaning: qty_id + qty_id + ...
Example above = 10×713, 10×509, 1×7455, 5×528.
"""

from typing import Dict, Optional, Iterable, Tuple, Any, List

from calc_app.paths import catalog_json
from calc_app.utils.jsonio import read_json

# ──────────────────────────────────────────────────────────────────────────────
# Internal caches
# ──────────────────────────────────────────────────────────────────────────────
_NAME_TO_ID: Dict[str, int] = {}
_ID_TO_NAME: Dict[int, str] = {}
_LOADED_NAMES: bool = False

# Raw payload cache for richer queries (type/recipe/etc.)
_RAW_PAYLOAD: Any = None
_LOADED_RAW: bool = False


# ──────────────────────────────────────────────────────────────────────────────
# Loading / parsing
# ──────────────────────────────────────────────────────────────────────────────
def _normalize_name(s: str) -> str:
    return s.strip().lower()


def _pick_name(obj: dict) -> str:
    """Return best available display name from a row/mapping."""
    for key in ("name_pt", "name_en", "name"):
        v = obj.get(key)
        if v:
            return str(v).strip()
    return ""  # unknown/missing


def _ingest_item(item_id: int, name: str) -> None:
    if not name:
        return
    _ID_TO_NAME[item_id] = name
    _NAME_TO_ID[name] = item_id
    _NAME_TO_ID[_normalize_name(name)] = item_id  # tolerant lookup


def _parse_list(payload: Iterable[dict]) -> None:
    """Parse the list-of-objects form into id↔name caches."""
    for row in payload:
        if not isinstance(row, dict):
            continue
        try:
            item_id = int(row["id"])
        except (KeyError, ValueError, TypeError):
            continue
        name = _pick_name(row)
        _ingest_item(item_id, name)


def _parse_mapping(payload: dict) -> None:
    """Parse the mapping form keyed by id into id↔name caches."""
    for raw_id, data in payload.items():
        try:
            item_id = int(raw_id)
        except (ValueError, TypeError):
            continue
        name = _pick_name(data) if isinstance(data, dict) else ""
        _ingest_item(item_id, name)


def _ensure_raw_loaded() -> None:
    """Load the raw catalog.json once (for row/type/recipe access)."""
    global _LOADED_RAW, _RAW_PAYLOAD
    if _LOADED_RAW:
        return
    ok, payload = read_json(catalog_json())
    _RAW_PAYLOAD = payload if ok else None
    _LOADED_RAW = True


def _ensure_names_loaded() -> None:
    """Load catalog.json once into id↔name maps (fast lookups)."""
    global _LOADED_NAMES
    if _LOADED_NAMES:
        return
    _NAME_TO_ID.clear()
    _ID_TO_NAME.clear()

    ok, payload = read_json(catalog_json())
    if ok and isinstance(payload, dict) and "items" in payload and isinstance(payload["items"], list):
        _parse_list(payload["items"])
    elif ok and isinstance(payload, list):
        _parse_list(payload)  # plain list
    elif ok and isinstance(payload, dict):
        _parse_mapping(payload)
    # else: leave caches empty

    _LOADED_NAMES = True


# ──────────────────────────────────────────────────────────────────────────────
# Public API — id/name resolution (unchanged behavior)
# ──────────────────────────────────────────────────────────────────────────────
def name_to_id(name: str) -> Optional[int]:
    _ensure_names_loaded()
    return _NAME_TO_ID.get(name) or _NAME_TO_ID.get(_normalize_name(name))


def id_to_name(item_id: int) -> Optional[str]:
    _ensure_names_loaded()
    return _ID_TO_NAME.get(item_id)


def all_item_ids() -> Tuple[int, ...]:
    _ensure_names_loaded()
    return tuple(sorted(_ID_TO_NAME.keys()))


def all_items() -> Tuple[Tuple[int, str], ...]:
    _ensure_names_loaded()
    return tuple(sorted(_ID_TO_NAME.items(), key=lambda kv: kv[1]))


def clear_cache() -> None:
    """Clears both name caches and raw payload cache."""
    global _LOADED_NAMES, _LOADED_RAW, _RAW_PAYLOAD
    _NAME_TO_ID.clear()
    _ID_TO_NAME.clear()
    _RAW_PAYLOAD = None
    _LOADED_NAMES = False
    _LOADED_RAW = False


# ──────────────────────────────────────────────────────────────────────────────
# Public API — rich row access (type/recipe and friends)
# ──────────────────────────────────────────────────────────────────────────────
def _iter_rows() -> List[Tuple[int, dict]]:
    """
    Iterate catalog as (id, row) pairs covering all supported shapes:
      1) {"schema":"items.v1","items":[{...}, ...]}
      2) [ {...}, ... ]
      3) {"6210": {...}, ...}
    Returns a fresh list (safe to sort/filter).
    """
    _ensure_raw_loaded()
    payload = _RAW_PAYLOAD
    out: List[Tuple[int, dict]] = []
    if not payload:
        return out

    if isinstance(payload, dict) and "items" in payload and isinstance(payload["items"], list):
        for row in payload["items"]:
            if not isinstance(row, dict):
                continue
            try:
                iid = int(row.get("id"))
                out.append((iid, row))
            except Exception:
                pass
        return out

    if isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict):
                continue
            try:
                iid = int(row.get("id"))
                out.append((iid, row))
            except Exception:
                pass
        return out

    if isinstance(payload, dict):
        for raw_id, row in payload.items():
            if not isinstance(row, dict):
                continue
            try:
                iid = int(raw_id)
                out.append((iid, row))
            except Exception:
                pass
        return out

    return out


def entry(item_id: int) -> Optional[dict]:
    """Return the raw catalog row for an id, or None."""
    iid = int(item_id)
    for rid, row in _iter_rows():
        if rid == iid:
            return row
    return None


def items_with_type(type_value: str) -> Tuple[int, ...]:
    """
    Return all ids where row['type'] equals `type_value` (case-insensitive).
    Example: items_with_type('final')
    """
    needle = str(type_value).strip().lower()
    ids: List[int] = []
    for iid, row in _iter_rows():
        if str(row.get("type", "")).strip().lower() == needle:
            ids.append(iid)
    return tuple(sorted(set(ids)))


def final_item_ids() -> Tuple[int, ...]:
    """Convenience alias for items_with_type('final')."""
    return items_with_type("final")


def display_name_from_row(row: dict, fallback_id: Optional[int] = None) -> str:
    """Resolve display name directly from a row dict (without touching caches)."""
    name = _pick_name(row)
    if name:
        return name
    return f"#{fallback_id}" if fallback_id is not None else "#?"


# ──────────────────────────────────────────────────────────────────────────────
# Public API — recipe handling (simplified, fixed format)
# ──────────────────────────────────────────────────────────────────────────────
def parse_recipe(recipe_field: Any) -> List[Tuple[int, int]]:
    """
    Parse recipe strings of the fixed form: "QTY_ID+QTY_ID+..."
    Example: "10_713+10_509+1_7455+5_528" -> [(713,10), (509,10), (7455,1), (528,5)]
    Notes:
      • Spaces are ignored.
      • Invalid chunks are skipped silently.
    """
    if not recipe_field or not isinstance(recipe_field, str):
        return []

    s = recipe_field.replace(" ", "")
    parts = s.split("+")
    out: List[Tuple[int, int]] = []
    for part in parts:
        if not part:
            continue
        try:
            qty_str, id_str = part.split("_", 1)
            qty = int(qty_str)
            mid = int(id_str)
            if qty > 0 and mid >= 0:
                out.append((mid, qty))
        except Exception:
            # skip malformed piece
            pass
    return out


def raw_recipe(item_id: int) -> Any:
    """Return the raw 'recipe' field for an item id (string in the fixed format), or None."""
    row = entry(item_id)
    return row.get("recipe") if isinstance(row, dict) else None


def parsed_recipe(item_id: int) -> List[Tuple[int, int]]:
    """Return normalized recipe [(material_id, qty), ...] for the given item id."""
    return parse_recipe(raw_recipe(item_id))
