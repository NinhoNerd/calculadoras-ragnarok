# src/calc_app/core/engine.py
from typing import Final

# RNG ranges used by the Special Pharmacy formula (inclusive)
R1_MIN: Final[int] = 30
R1_MAX: Final[int] = 150
R2_MIN: Final[int] = 4
R2_MAX: Final[int] = 10

__all__ = [
    "special_pharmacy",
    "R1_MIN", "R1_MAX",
    "R2_MIN", "R2_MAX",
]


def special_pharmacy(
    int_stat: int,
    des_stat: int,
    sor_stat: int,
    job_level: int,
    base_level: int,
    potion_research_level: int,
    chemical_protection_level: int,
    rand_30_150: int,
    rand_4_10: int,
) -> int:
    """
    Compute the Special Pharmacy (Farmacologia Avançada) outcome.

    Formula implemented:
        INT
      + (DEX / 2)
      + LUK
      + JobLevel
      + Rand[30..150]
      + (BaseLevel - 100)
      + (PotionResearchLevel * 5)
      + (FullChemicalProtectionLevel * Rand[4..10])

    Notes
    -----
    • The return value is cast to `int` at the end (same as your Excel behavior).
      Since all terms are non-negative, `int(x)` is equivalent to floor here.
    • We validate the random inputs to catch programming errors early.

    Args:
        int_stat: INT stat.
        des_stat: DEX stat.
        sor_stat: LUK stat.
        job_level: Job/Class level.
        base_level: Base level.
        potion_research_level: Potion Research level.
        chemical_protection_level: Full Chemical Protection level.
        rand_30_150: Integer in [30, 150].
        rand_4_10: Integer in [4, 10].

    Returns:
        Integer result of the formula.
    """
    # Guard against out-of-range RNG values; helps catch bugs in callers/tests.
    if not (R1_MIN <= rand_30_150 <= R1_MAX):
        raise ValueError(f"rand_30_150 must be in [{R1_MIN}, {R1_MAX}], got {rand_30_150}")
    if not (R2_MIN <= rand_4_10 <= R2_MAX):
        raise ValueError(f"rand_4_10 must be in [{R2_MIN}, {R2_MAX}], got {rand_4_10}")

    value = (
        int_stat
        + (des_stat / 2.0)  # keep float division, then truncate at the end
        + sor_stat
        + job_level
        + rand_30_150
        + (base_level - 100)
        + (potion_research_level * 5)
        + (chemical_protection_level * rand_4_10)
    )
    return int(value)
