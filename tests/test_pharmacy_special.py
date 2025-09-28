import pytest
import calc_app.core.pharmacy_special as ps


# ----------------------------
# Helpers (payloads falsos)
# ----------------------------

def valid_rules_payload():
    # NÃO inclui item_ids (deve ser derivado das chaves de base_difficulty_by_item_id)
    return {
        "base_difficulty_by_level": {"0": 0, "1": 10, "10": 100},
        "max_potions_by_level": {"0": 1, "1": 2, "10": 10},
        "base_difficulty_by_item_id": {"1001": 5, "1002": 15},
    }


# ----------------------------
# Testes com payloads falsos
# ----------------------------

def test_from_dict_derives_item_ids_and_queries_work():
    data = valid_rules_payload()
    rules = ps.Rules.from_dict(data)

    # Estrutura básica
    assert isinstance(rules, ps.Rules)

    # item_ids deve ser derivado e ordenado
    assert rules.item_ids == (1001, 1002)

    # lookups
    assert rules.base_difficulty_by_level(0) == 0
    assert rules.base_difficulty_by_level(1) == 10
    assert rules.base_difficulty_by_level(10) == 100

    assert rules.base_difficulty_by_item_id(1001) == 5
    assert rules.base_difficulty_by_item_id(1002) == 15

    # soma
    assert rules.item_difficulty(1002, 1) == 10 + 15

    # cap + fallback
    assert rules.potion_cap(10, fallback=-1) == 10
    assert rules.potion_cap(5, fallback=99) == 99

    # níveis disponíveis
    assert rules.levels() == (0, 1, 10)

    # to_dict inclui item_ids (derivados)
    back = rules.to_dict()
    assert "item_ids" in back
    assert back["item_ids"] == [1001, 1002]


def test_invalid_type_raises():
    with pytest.raises(ps.InvalidRulesError):
        ps.Rules.from_dict("not-a-dict")  # tipo inválido


def test_level_out_of_range_raises():
    rules = ps.Rules.from_dict(valid_rules_payload())
    with pytest.raises(ps.LevelOutOfRange):
        rules.base_difficulty_by_level(-1)
    with pytest.raises(ps.LevelOutOfRange):
        rules.base_difficulty_by_level(11)


def test_unknown_item_id_raises():
    rules = ps.Rules.from_dict(valid_rules_payload())
    with pytest.raises(ps.UnknownItemId):
        rules.base_difficulty_by_item_id(9999)


@pytest.mark.parametrize("section_key", [
    "base_difficulty_by_level",
    "max_potions_by_level",
    "base_difficulty_by_item_id",
])
def test_negative_values_raise(section_key):
    data = valid_rules_payload()
    # Pegue qualquer chave existente e torne negativa
    key = next(iter(data[section_key].keys()))
    data[section_key][key] = -1
    with pytest.raises(ps.InvalidRulesError) as e:
        ps.Rules.from_dict(data)
    assert "non-negative" in str(e.value)


def test_missing_sections_raise():
    data = valid_rules_payload()
    del data["base_difficulty_by_item_id"]  # remove seção obrigatória
    with pytest.raises(ps.InvalidRulesError) as e:
        ps.Rules.from_dict(data)
    assert "Missing or empty sections" in str(e.value)


# ----------------------------
# Teste de integração com arquivo real
# ----------------------------

def test_real_pharmacy_special_json_loads_ok():
    """
    Integração: valida que o arquivo real (assets/skills/pharmacy_special.json)
    pode ser carregado e contém dados coerentes, além de checar itens específicos.
    """
    rules = ps.load_rules()
    assert isinstance(rules, ps.Rules)

    # Deve ter itens e níveis
    assert rules.item_ids, "item_ids está vazio no arquivo real!"
    assert rules.levels(), "levels está vazio no arquivo real!"

    # Todo item listado deve ter dificuldade
    for iid in rules.item_ids:
        assert iid in rules.diff_by_item_id, f"Faltando dificuldade para item {iid}"

    # Níveis dentro da faixa
    for lvl in rules.levels():
        assert 0 <= lvl <= 10

    # --- Checagens específicas ---
    # IDs e dificuldades por item esperadas
    esperados = {
        12428: 10,
        12436: 20,
        12437: 30,
        12475: 40,
    }

    # Confere base de nível 7
    assert rules.base_difficulty_by_level(7) == 480, "Dificuldade base do nível 7 deveria ser 480"

    # Cada item: existe, bate per-item e bate total com nível 7
    for iid, diff_item in esperados.items():
        assert iid in rules.item_ids, f"Item {iid} não está em item_ids"
        assert rules.base_difficulty_by_item_id(iid) == diff_item, (
            f"Dificuldade por item de {iid} deveria ser {diff_item}"
        )
        total = rules.item_difficulty(iid, 7)
        assert total == 480 + diff_item, (
            f"Total para item {iid} no nível 7 deveria ser {480 + diff_item}, obtido {total}"
        )
