from dataclasses import dataclass
from typing import Tuple, Mapping, Optional
from types import MappingProxyType

from calc_app import paths
from calc_app.utils.jsonio import read_json  # PyInstaller-friendly


# ---------- Constants ----------

MIN_LEVEL = 0
MAX_LEVEL = 10


# ---------- Exceptions ----------

class RulesError(Exception):
    """Base error for Pharmacy Special rules problems."""


class InvalidRulesError(RulesError):
    """Raised when JSON is missing required keys or has wrong types."""


class LevelOutOfRange(RulesError):
    """Raised when an invalid Pharmacy level is requested."""


class UnknownItemId(RulesError):
    """Raised when an item_id is not present in rules."""


IntMap = Mapping[int, int]


# ---------- Data Model ----------

@dataclass(frozen=True)
class Rules:
    """
    Immutable rules for 'Farmacologia Avançada'.

    Fields:
        item_ids: tuple of craftable item IDs (always derived from base_difficulty_by_item_id).
        diff_by_level: base difficulty by skill level (0..10).
        max_by_level: max number of potions allowed by level.
        diff_by_item_id: per-item base difficulty.
    """
    item_ids: Tuple[int, ...]
    diff_by_level: IntMap
    max_by_level: IntMap
    diff_by_item_id: IntMap

    # -------- Construction / Validation --------
    @classmethod
    def from_dict(cls, data) -> "Rules":
        """
        Parse and normalize a raw JSON dict into a Rules object.
        Assumes JSON contains ONLY:
          - base_difficulty_by_level
          - max_potions_by_level
          - base_difficulty_by_item_id
        Derives item_ids from base_difficulty_by_item_id.keys() (sorted).
        """
        if not isinstance(data, dict):
            raise InvalidRulesError("Rules JSON must be a dict.")

        try:
            raw_diff_by_level = {int(k): int(v) for k, v in data.get("base_difficulty_by_level", {}).items()}
            raw_max_by_level  = {int(k): int(v) for k, v in data.get("max_potions_by_level", {}).items()}
            raw_diff_by_item  = {int(k): int(v) for k, v in data.get("base_difficulty_by_item_id", {}).items()}
        except (TypeError, ValueError) as e:
            raise InvalidRulesError(f"Failed to coerce values to int: {e}") from e

        # item_ids é sempre derivado das chaves de diff_by_item
        derived_item_ids = tuple(sorted(raw_diff_by_item.keys()))

        rules = cls(
            item_ids=derived_item_ids,
            diff_by_level=MappingProxyType(raw_diff_by_level),
            max_by_level=MappingProxyType(raw_max_by_level),
            diff_by_item_id=MappingProxyType(raw_diff_by_item),
        )
        rules._validate()
        return rules

    def _validate(self) -> None:
        # Presença das 3 seções obrigatórias
        required = [
            ("base_difficulty_by_level", self.diff_by_level),
            ("max_potions_by_level", self.max_by_level),
            ("base_difficulty_by_item_id", self.diff_by_item_id),
        ]
        missing = [name for name, value in required if not value]
        if missing:
            raise InvalidRulesError(f"Missing or empty sections: {', '.join(missing)}")

        # Faixa de níveis permitida
        for lvl in self.diff_by_level:
            if not (MIN_LEVEL <= int(lvl) <= MAX_LEVEL):
                raise InvalidRulesError(
                    f"Invalid level key '{lvl}' (expected {MIN_LEVEL}..{MAX_LEVEL})."
                )

        # Não-negatividade
        if any(v < 0 for v in self.diff_by_level.values()):
            raise InvalidRulesError("base_difficulty_by_level must be non-negative integers.")
        if any(v < 0 for v in self.max_by_level.values()):
            raise InvalidRulesError("max_potions_by_level must be non-negative integers.")
        if any(v < 0 for v in self.diff_by_item_id.values()):
            raise InvalidRulesError("base_difficulty_by_item_id must be non-negative integers.")

        # Como item_ids é derivado de diff_by_item_id, não há como haver inconsistência entre eles.

    # -------- Query Helpers (pure, no IO) --------

    def base_difficulty_by_level(self, level: int) -> int:
        try:
            return self.diff_by_level[level]
        except KeyError:
            raise LevelOutOfRange(
                f"Invalid Pharmacy level {level}. Expected {MIN_LEVEL}..{MAX_LEVEL}."
            ) from None

    def base_difficulty_by_item_id(self, item_id: int) -> int:
        try:
            return self.diff_by_item_id[item_id]
        except KeyError:
            raise UnknownItemId(f"Item ID {item_id} not found in rules.") from None

    def item_difficulty(self, item_id: int, level: int) -> int:
        return self.base_difficulty_by_level(level) + self.base_difficulty_by_item_id(item_id)

    def potion_cap(self, level: int, fallback: int) -> int:
        return self.max_by_level.get(level, fallback)

    def levels(self) -> Tuple[int, ...]:
        """Return available levels sorted ascending (e.g., (0,1,2,...))."""
        return tuple(sorted(self.diff_by_level.keys()))

    def to_dict(self) -> dict:
        """Serialize back to a JSON-safe dict (includes derived item_ids)."""
        return {
            "item_ids": list(self.item_ids),
            "base_difficulty_by_level": {str(k): int(v) for k, v in self.diff_by_level.items()},
            "max_potions_by_level": {str(k): int(v) for k, v in self.max_by_level.items()},
            "base_difficulty_by_item_id": {str(k): int(v) for k, v in self.diff_by_item_id.items()},
        }


# ---------- IO (no caching) ----------

def load_rules(file_path: Optional[str] = None) -> Rules:
    """
    Load rules from JSON file and return an immutable Rules instance.

    Args:
        file_path: Optional explicit path. Defaults to calc_app.paths.pharmacy_special_rules_json().

    Raises:
        InvalidRulesError, RulesError, RuntimeError
    """
    rules_path = file_path or paths.pharmacy_special_rules_json()
    ok, data = read_json(rules_path)
    if not ok or not isinstance(data, dict):
        raise RuntimeError(f"Missing or invalid rules: {rules_path}")
    return Rules.from_dict(data)
