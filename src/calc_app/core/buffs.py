# src/calc_app/core/buffs.py
"""
Catálogo declarativo de buffs + função utilitária para aplicá-los.

• Cada buff tem:
  - key: identificador estável para salvar no profile.json
  - label: texto exibido na UI
  - add: deltas aditivos por atributo (ex.: {"int_stat": 20})
  - mul_pct: multiplicadores percentuais (ex.: {"int_stat": 0.10}) [opcional, não usado agora]

• Stats suportados devem bater com o AppState.CharacterStats:
  for_stat, agi_stat, vit_stat, int_stat, des_stat, sor_stat
"""

from dataclasses import dataclass
from typing import Dict, Mapping, Tuple

StatDict = Dict[str, int]


@dataclass(frozen=True)
class BuffDef:
    key: str                      # chave salva no profile
    label: str                    # rótulo para a UI
    add: Mapping[str, int]        # bônus aditivos
    mul_pct: Mapping[str, float]  # bônus percentuais (+10% -> 0.10)


# ---------------------------------------------------------------------------
# BUFFS DEFINIDOS
# ---------------------------------------------------------------------------
# 1) Glória -> SOR +30
# 2) Benção -> INT, DEX e FOR +10
# 3) Comida de INT (GRANDE) -> INT +20
# 4) Comida de SOR (GRANDE) -> SOR +20
# 5) Comida de DES (GRANDE) -> DES +20
# 6) Bolinho Divino -> todos os atributos +10
# ---------------------------------------------------------------------------

BUFFS: Tuple[BuffDef, ...] = (
    BuffDef(
        key="gloria",
        label="Glória",
        add={"sor_stat": 30},
        mul_pct={},
    ),
    BuffDef(
        key="bencao",
        label="Benção",
        add={"int_stat": 10, "des_stat": 10, "for_stat": 10},
        mul_pct={},
    ),
    BuffDef(
        key="comida_int_grande",
        label="Comida de INT (Grande)",
        add={"int_stat": 20},
        mul_pct={},
    ),
    BuffDef(
        key="comida_sor_grande",
        label="Comida de SOR (Grande)",
        add={"sor_stat": 20},
        mul_pct={},
    ),
    BuffDef(
        key="comida_des_grande",
        label="Comida de DES (Grande)",
        add={"des_stat": 20},
        mul_pct={},
    ),
    BuffDef(
        key="bolinho_divino",
        label="Bolinho Divino",
        add={
            "for_stat": 10,
            "agi_stat": 10,
            "vit_stat": 10,
            "int_stat": 10,
            "des_stat": 10,
            "sor_stat": 10,
        },
        mul_pct={},
    ),
)

# lookup rápido
BUFF_BY_KEY: Dict[str, BuffDef] = {b.key: b for b in BUFFS}


def apply_buffs(base: StatDict, toggles: Mapping[str, bool]) -> StatDict:
    """
    Aplica buffs sobre um dict de stats base e retorna um novo dict.
    Ordem: soma todos 'add', depois aplica todos 'mul_pct' (se existirem).
    """
    out: StatDict = dict(base)

    # aditivos
    for k, on in toggles.items():
        if not on:
            continue
        b = BUFF_BY_KEY.get(k)
        if not b:
            continue
        for stat, delta in b.add.items():
            out[stat] = int(out.get(stat, 0) + int(delta))

    # percentuais (não usados nos 6 atuais, mas já suportado)
    for k, on in toggles.items():
        if not on:
            continue
        b = BUFF_BY_KEY.get(k)
        if not b:
            continue
        for stat, pct in b.mul_pct.items():
            out[stat] = int(round(out.get(stat, 0) * (1.0 + float(pct))))

    return out
