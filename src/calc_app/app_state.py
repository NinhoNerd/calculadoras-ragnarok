# src/calc_app/gui/app_state.py
"""
Centralized application state (Qt signals + immutable snapshots).

Design goals
------------
• Single source of truth for editable state (stats/levels/skills/buffs).
• Zero direct IO in UI pages — expose tiny proxies here.
• Keep catalog logic inside core.catalog (id/name, type, recipe).
• Keep rules logic inside core.pharmacy_special (immutable, pure lookups).
• Snapshot bus pattern:
    - Farmacologia: PharmacySpecialSnapshot (already existed)
    - Base Preços:  BasePricesSnapshot  (NEW)  ← other tabs (e.g. Custo de Produção) consume this

What lives here?
----------------
• Profile load/save/reset.
• Prices load/save/reset + Live snapshot publish.
• Signals for UI reactivity and snapshot buses.
• Thin proxies to catalog + rules (so pages never import IO modules directly).
"""

from dataclasses import dataclass, asdict, replace, fields
from typing import Dict, Optional, TypedDict, Tuple, Mapping, List
from PySide6.QtCore import QObject, Signal

# IO / core helpers
from . import paths
from .utils.jsonio import read_json, write_json_atomic
from .core import catalog
from .core import pharmacy_special as sp
from .core import buffs as buffs_core


# ──────────────────────────────────────────────────────────────────────────────
# Snapshots (read-only views other tabs can consume)
# ──────────────────────────────────────────────────────────────────────────────

class ItemRow(TypedDict, total=False):
    """Per-item metrics used by UI tables and other modules (Farmacologia)."""
    difficulty: int
    p_max: float
    p_m3: float
    p_m4: float
    p_m5: float
    p_m6: float
    mean_weighted: float


@dataclass(frozen=True)
class PharmacySpecialSnapshot:
    """Result of Farmacologia Avançada compute."""
    results: List[int]
    max_cap: int
    per_item: Dict[str, ItemRow]  # key is display name
    global_min: int
    global_max: int

class PriceRow(TypedDict):
    item_id: int
    name: str
    price: int

@dataclass(frozen=True)
class BasePricesSnapshot:
    """Resolved, UI-friendly prices snapshot (immutable)."""
    rows: List[PriceRow]        # sorted by name
    by_id: Dict[int, int]       # fast lookups
    count: int                  # number of items in snapshot
    source: str                 # 'user' | 'default' | 'live'


# ──────────────────────────────────────────────────────────────────────────────
# Editable state dataclasses (persisted in profile.json)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CharacterStats:
    for_stat: int = 100
    agi_stat: int = 100
    vit_stat: int = 100
    int_stat: int = 100
    des_stat: int = 100  # DEX
    sor_stat: int = 100  # LUK


@dataclass(frozen=True)
class CharacterLevels:
    job_level: int = 50
    base_level: int = 120


@dataclass(frozen=True)
class Skills:
    """Keep in sync with profile.json. Add new skills here as modules grow."""
    potion_research: int = 10
    chemical_protection_full: int = 5
    advanced_pharmacy: int = 10
    pharmacy: int = 10


# ──────────────────────────────────────────────────────────────────────────────
# AppState
# ──────────────────────────────────────────────────────────────────────────────

class AppState(QObject):
    # Change signals (dict payloads so listeners don't need dataclasses)
    stats_changed  = Signal(object)
    levels_changed = Signal(object)
    skills_changed = Signal(object)
    buffs_changed  = Signal(object)

    # Snapshot buses
    pharmacy_special_changed = Signal(object)  # -> PharmacySpecialSnapshot
    base_prices_changed      = Signal(object)  # -> BasePricesSnapshot

    def __init__(self) -> None:
        super().__init__()

        # Immutable rules (load once)
        self._rules: sp.Rules = sp.load_rules()

        # Editable state (hydrate from profile or defaults)
        prof = self._load_profile()
        self._stats  = self._coerce(CharacterStats,  prof.get("stats",  {}))
        self._levels = self._coerce(CharacterLevels, prof.get("levels", {}))
        self._skills = self._coerce(Skills,         prof.get("skills", {}))

        # Buff toggles
        prof_buffs = prof.get("buffs", {})
        self._buffs: Dict[str, bool] = {b.key: bool(prof_buffs.get(b.key, False))
                                        for b in buffs_core.BUFFS}

        # Latest snapshots
        self._pharmacy_special_snapshot: Optional[PharmacySpecialSnapshot] = None
        self._base_prices_snapshot: Optional[BasePricesSnapshot] = None

        # In-memory prices cache (kept in sync with the base-prices snapshot)
        self._prices_cache: Dict[str, int] | None = None

        # Boot listeners in sync
        self.stats_changed.emit(self.get_stats())
        self.levels_changed.emit(self.get_levels())
        self.skills_changed.emit(self.get_skills())
        self.buffs_changed.emit(self.get_buffs())

        # Initialize Base Preços snapshot from disk (user → default)
        self._refresh_base_prices_from_disk_and_publish()

    # ── profile IO ───────────────────────────────────────────────────────────

    @staticmethod
    def _coerce(dc_type, data: Dict) -> object:
        defaults = dc_type()  # type: ignore[call-arg]
        kwargs = {f.name: data.get(f.name, getattr(defaults, f.name)) for f in fields(dc_type)}
        return dc_type(**kwargs)  # type: ignore[call-arg]

    def _profile_blob(self) -> Dict:
        return {
            "schema": "profile.v1",
            "stats":  self.get_stats(),
            "levels": self.get_levels(),
            "skills": self.get_skills(),
            "buffs":  self.get_buffs(),
        }

    def _load_profile(self) -> Dict:
        ok_user, user_data = read_json(paths.user_profile_json())
        if ok_user and isinstance(user_data, dict):
            return user_data
        ok_def, def_data = read_json(paths.profile_default_json())
        return def_data if ok_def and isinstance(def_data, dict) else {}

    def save_profile(self) -> str:
        target = paths.user_profile_json()
        write_json_atomic(target, self._profile_blob())
        return str(target)

    def import_profile_from_file(self, file_path: str) -> None:
        ok, data = read_json(file_path)
        if not ok or not isinstance(data, dict):
            raise RuntimeError(f"Invalid profile file: {file_path}")

        self._stats  = self._coerce(CharacterStats,  data.get("stats",  {}))
        self._levels = self._coerce(CharacterLevels, data.get("levels", {}))
        self._skills = self._coerce(Skills,         data.get("skills", {}))
        prof_buffs = data.get("buffs", {})
        self._buffs = {b.key: bool(prof_buffs.get(b.key, False)) for b in buffs_core.BUFFS}

        self.stats_changed.emit(self.get_stats())
        self.levels_changed.emit(self.get_levels())
        self.skills_changed.emit(self.get_skills())
        self.buffs_changed.emit(self.get_buffs())

    def export_profile_to_file(self, file_path: str) -> str:
        write_json_atomic(file_path, self._profile_blob())
        return str(file_path)

    def reset_profile_to_default(self) -> str:
        ok, def_data = read_json(paths.profile_default_json())
        if not ok or not isinstance(def_data, dict):
            raise RuntimeError(f"Missing/invalid default profile: {paths.profile_default_json()}")
        write_json_atomic(paths.user_profile_json(), def_data)

        self._stats  = self._coerce(CharacterStats,  def_data.get("stats",  {}))
        self._levels = self._coerce(CharacterLevels, def_data.get("levels", {}))
        self._skills = self._coerce(Skills,         def_data.get("skills", {}))
        self._buffs  = {b.key: bool(def_data.get("buffs", {}).get(b.key, False))
                        for b in buffs_core.BUFFS}

        self.stats_changed.emit(self.get_stats())
        self.levels_changed.emit(self.get_levels())
        self.skills_changed.emit(self.get_skills())
        self.buffs_changed.emit(self.get_buffs())
        return str(paths.user_profile_json())

    # ── Base Preços: IO + snapshot publish ───────────────────────────────────

    def base_prices(self) -> Optional[BasePricesSnapshot]:
        return self._base_prices_snapshot

    def _compute_base_prices_snapshot(self, blob: Dict[str, int], source: str) -> BasePricesSnapshot:
        """
        Turn a raw id->price mapping into a resolved, sorted, UI-friendly snapshot.
        """
        rows: List[PriceRow] = []
        by_id: Dict[int, int] = {}
        for k, v in blob.items():
            try:
                iid = int(k)
                price = int(v)
            except Exception:
                continue
            name = catalog.id_to_name(iid) or f"#{iid}"
            rows.append(PriceRow(item_id=iid, name=name, price=price))
            by_id[iid] = price

        rows.sort(key=lambda r: (r["name"].casefold(), r["item_id"]))
        return BasePricesSnapshot(rows=rows, by_id=by_id, count=len(rows), source=source)

    def _publish_base_prices_snapshot(self, blob: Dict[str, int], source: str) -> None:
        self._prices_cache = dict(blob)
        snap = self._compute_base_prices_snapshot(blob, source)
        self._base_prices_snapshot = snap
        self.base_prices_changed.emit(snap)

    def _refresh_base_prices_from_disk_and_publish(self) -> None:
        """
        Read prices (user → default), cache them, and publish snapshot once.
        """
        ok, data = read_json(paths.user_prices_json())
        if ok and isinstance(data, dict):
            clean = {str(k): int(v) for k, v in data.items() if isinstance(v, (int, float, int))}
            self._publish_base_prices_snapshot(clean, source="user")
            return
        ok, data = read_json(paths.prices_default_json())
        clean = {str(k): int(v) for k, v in (data if (ok and isinstance(data, dict)) else {}).items()
                 if isinstance(v, (int, float, int))}
        self._publish_base_prices_snapshot(clean, source="default")

    def load_prices_blob(self) -> dict:
        """
        Return a *copy* of the latest known prices (whatever the current snapshot holds).
        This is for consumers that still want the raw map.
        """
        if self._prices_cache is None:
            self._refresh_base_prices_from_disk_and_publish()
        return dict(self._prices_cache or {})

    def set_prices_live(self, blob: dict) -> None:
        """
        Update *live* prices (no disk write) and publish a new snapshot.
        Call this for transient edits (e.g., editingFinished in Base Preços).
        """
        clean = {str(k): int(v) for k, v in blob.items() if isinstance(v, (int, float, int))}
        self._publish_base_prices_snapshot(clean, source="live")

    def save_prices_blob(self, blob: dict) -> str:
        """
        Persist prices to the user file, refresh cache, and publish a snapshot.
        """
        clean = {str(k): int(v) for k, v in blob.items() if isinstance(v, (int, float, int))}
        write_json_atomic(paths.user_prices_json(), clean)
        self._publish_base_prices_snapshot(clean, source="user")
        return str(paths.user_prices_json())

    def reset_prices_to_default(self) -> str:
        ok, data = read_json(paths.prices_default_json())
        if not ok or not isinstance(data, dict):
            raise RuntimeError(f"Missing default prices: {paths.prices_default_json()}")
        clean = {str(k): int(v) for k, v in data.items() if isinstance(v, (int, float, int))}
        write_json_atomic(paths.user_prices_json(), clean)
        self._publish_base_prices_snapshot(clean, source="default")
        return str(paths.user_prices_json())

    def get_price(self, item_id: int, default: int = 0) -> int:
        blob = self.load_prices_blob()
        return int(blob.get(str(item_id), default))

    # ── getters (plain dicts for UI convenience) ─────────────────────────────

    def get_stats(self) -> Dict[str, int]:  return asdict(self._stats)
    def get_levels(self) -> Dict[str, int]: return asdict(self._levels)
    def get_skills(self) -> Dict[str, int]: return asdict(self._skills)

    def get_buffs(self) -> Dict[str, bool]:
        return {b.key: bool(self._buffs.get(b.key, False)) for b in buffs_core.BUFFS}

    def get_effective_stats(self) -> Dict[str, int]:
        return buffs_core.apply_buffs(self.get_stats(), self.get_buffs())

    def pharmacy_special(self) -> Optional[PharmacySpecialSnapshot]:
        return self._pharmacy_special_snapshot

    # ── setters (partial updates; emit only on actual change) ────────────────

    def set_stats(self, updates: Dict[str, int]) -> None:
        new = replace(self._stats, **{k: updates[k] for k in updates if hasattr(self._stats, k)})
        if new != self._stats:
            self._stats = new
            self.stats_changed.emit(self.get_stats())

    def set_levels(self, updates: Dict[str, int]) -> None:
        new = replace(self._levels, **{k: updates[k] for k in updates if hasattr(self._levels, k)})
        if new != self._levels:
            self._levels = new
            self.levels_changed.emit(self.get_levels())

    def set_skills(self, updates: Dict[str, int]) -> None:
        new = replace(self._skills, **{k: updates[k] for k in updates if hasattr(self._skills, k)})
        if new != self._skills:
            self._skills = new
            self.skills_changed.emit(self.get_skills())

    def set_buffs(self, updates: Mapping[str, bool]) -> None:
        new = dict(self._buffs); changed = False
        for k, v in updates.items():
            if k in new and new[k] != bool(v):
                new[k] = bool(v); changed = True
        if changed:
            self._buffs = new
            self.buffs_changed.emit(self.get_buffs())

    # ── snapshot publisher (Farmacologia) ────────────────────────────────────

    def set_pharmacy_special_snapshot(self, snap: PharmacySpecialSnapshot) -> None:
        self._pharmacy_special_snapshot = snap
        self.pharmacy_special_changed.emit(snap)

    # ── catalog proxies (thin, IO-free from UI perspective) ──────────────────

    def catalog_id_to_name(self, item_id: int) -> Optional[str]: return catalog.id_to_name(item_id)
    def catalog_name_to_id(self, name: str) -> Optional[int]:    return catalog.name_to_id(name)
    def catalog_entry(self, item_id: int) -> dict | None:        return catalog.entry(item_id)
    def catalog_final_item_ids(self) -> Tuple[int, ...]:         return catalog.final_item_ids()
    def catalog_parsed_recipe(self, item_id: int) -> List[tuple[int, int]]:
        return catalog.parsed_recipe(item_id)

    # ── rules proxies (pure lookups) ─────────────────────────────────────────

    def pharmacy_special_item_ids(self) -> Tuple[int, ...]:                    return self._rules.item_ids
    def pharmacy_special_item_difficulty(self, item_id: int, adv_level: int) -> int:
        return self._rules.item_difficulty(item_id, adv_level)
    def pharmacy_special_level_cap(self, level: int, fallback: int) -> int:
        return self._rules.potion_cap(level, fallback)
    def pharmacy_special_level_base_difficulty(self, level: int) -> int:
        return self._rules.base_difficulty_by_level(level)
