import pytest

from data.repository import DataRepositoryError, load_json, load_path
from data.validate import validate_catalog
from utils.utils import apply_action


def test_entire_catalog():
    validate_catalog()


def test_repository_returns_isolated_cached_data():
    first = load_json("paths/novice/warrior.json")
    first["level_benefits"].clear()
    assert load_json("data_base/paths/novice/warrior.json")["level_benefits"]


def test_repository_rejects_escape():
    with pytest.raises(DataRepositoryError):
        load_json("../config.py")


def test_path_descriptions_are_grounded_in_existing_content():
    from main import load_expert_paths, load_master_paths

    for entry in load_expert_paths() + load_master_paths():
        assert entry.get("description") != "sample text"
    witch = next(entry for entry in load_expert_paths() if entry["id"] == "witch")
    assert "Wsparcie" in witch["description"]


@pytest.mark.parametrize(
    "tier,path,level,name",
    [("master", "exorcist", 7, "Egzorcyzm"), ("expert", "witch", 3, "Wiedźmi ogień")],
)
def test_embedded_spell_preserves_rules(hero, tier, path, level, name):
    benefit = load_path(tier, path).level_benefits[level]
    action = next(action for action in benefit.actions if action.type == "add_spell")
    apply_action(action, hero, False)
    assert hero.spells[-1].name == name
    assert hero.spells[-1].description == action.spell.description
    assert hero.spells[-1].level == 1
