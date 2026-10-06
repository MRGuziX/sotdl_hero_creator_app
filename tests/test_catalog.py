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


def test_novice_tooltips_use_editable_draft_path_descriptions():
    from main import load_novice_paths

    for entry in load_novice_paths():
        definition = load_path("novice", entry["id"])
        assert entry["description"] == definition.path_description
        assert entry["description"].startswith("Opis roboczy:")
        assert "Talenty ścieżki:" not in entry["description"]


def test_missing_path_descriptions_use_labeled_templates_not_talent_lists():
    from main import load_expert_paths, load_master_paths

    for entry in load_expert_paths() + load_master_paths():
        assert entry["name"] in entry["description"]
        assert "szablon tymczasowy" in entry["description"]
        assert "Talenty ścieżki:" not in entry["description"]


@pytest.mark.parametrize("description", [None, "", "   "])
def test_empty_descriptions_use_a_placeholder(monkeypatch, description):
    from main import load_expert_paths

    monkeypatch.setattr(
        "main._load_json",
        lambda path: {
            "path_name": "Ścieżka testowa",
            "path_description": description,
            "level_benefits": {},
        },
    )
    assert all("szablon tymczasowy" in entry["description"] for entry in load_expert_paths())


def test_supplied_path_description_is_preferred_over_the_template(monkeypatch):
    from main import load_expert_paths

    description = "Gotowy opis fabularny ścieżki."
    monkeypatch.setattr(
        "main._load_json",
        lambda path: {
            "path_name": "Ścieżka testowa",
            "path_description": description,
            "level_benefits": {},
        },
    )
    assert all(entry["description"] == description for entry in load_expert_paths())


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
