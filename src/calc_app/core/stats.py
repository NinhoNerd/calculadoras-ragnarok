"""
Calculations for the *Special Pharmacy* skill:
- enumeration of all outcomes
- probability buckets relative to difficulty
"""

from typing import Dict, List, Tuple, Final
from .engine import (
    special_pharmacy,
    R1_MIN, R1_MAX,   # random in [30..150]
    R2_MIN, R2_MAX,   # random in [4..10]
)

# Totals derived from authoritative ranges in engine.py
SPECIAL_PHARMACY_R1_TOTAL: Final[int] = R1_MAX - R1_MIN + 1   # 121
SPECIAL_PHARMACY_R2_TOTAL: Final[int] = R2_MAX - R2_MIN + 1   # 7
PHARMACY_SPECIAL_TOTAL_COMBOS: Final[int] = (
    SPECIAL_PHARMACY_R1_TOTAL * SPECIAL_PHARMACY_R2_TOTAL     # 847
)

__all__ = [
    "enumerate_special_pharmacy_results",
    "pharmacy_special_probability_by_ranges",
    "PHARMACY_SPECIAL_TOTAL_COMBOS",
]


def enumerate_special_pharmacy_results(
    int_stat: int,
    des_stat: int,
    sor_stat: int,
    job_level: int,
    base_level: int,
    potion_research_level: int,
    chemical_protection_level: int,
) -> List[int]:
    """
    Enumerate all outcomes for the two integer RNGs:
      r1 ∈ [R1_MIN..R1_MAX], r2 ∈ [R2_MIN..R2_MAX]
    Returns a list of length SPECIAL_PHARMACY_TOTAL_COMBOS (847).
    """
    return [
        special_pharmacy(
            int_stat, des_stat, sor_stat,
            job_level, base_level,
            potion_research_level, chemical_protection_level,
            r1, r2,
        )
        for r1 in range(R1_MIN, R1_MAX + 1)
        for r2 in range(R2_MIN, R2_MAX + 1)
    ]


def pharmacy_special_probability_by_ranges(
    results: List[int],
    difficulty: int
) -> Dict[str, Tuple[int, float]]:
    """
    Partition outcomes into 5 mutually-exclusive buckets relative to 'difficulty'.

      MAX   : result >= difficulty + 400
      MAX-3 : difficulty + 300 <= result <  difficulty + 400
      MAX-4 : difficulty + 100 <= result <  difficulty + 300
      MAX-5 : difficulty        <= result <  difficulty + 100
      MAX-6 : result < difficulty

    Returns: dict[label] -> (count, probability)
    """
    labels = ("MAX", "MAX-3", "MAX-4", "MAX-5", "MAX-6")
    counts: Dict[str, int] = {k: 0 for k in labels}

    t1 = difficulty + 400
    t2 = difficulty + 300
    t3 = difficulty + 100
    t4 = difficulty

    for val in results:
        if val >= t1:
            counts["MAX"] += 1
        elif val >= t2:
            counts["MAX-3"] += 1
        elif val >= t3:
            counts["MAX-4"] += 1
        elif val >= t4:
            counts["MAX-5"] += 1
        else:
            counts["MAX-6"] += 1

    return {k: (v, v / PHARMACY_SPECIAL_TOTAL_COMBOS) for k, v in counts.items()}

