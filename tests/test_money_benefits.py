from data.repository import load_json
from models.tables import RollTableEntry
from utils.utils import apply_action
import pytest


@pytest.mark.parametrize("ancestry", ["goblin", "human", "automaton"])
def test_inheritance_adds_copper_to_existing_wealth(hero, monkeypatch, ancestry):
    tables = load_json(f"ancestry/{ancestry}/{ancestry}_tables.json")

    def find_inheritance(value):
        if isinstance(value, list):
            for entry in value:
                if any(action.get("name") == "miedziaki" for action in entry.get("actions", [])):
                    return entry
        if isinstance(value, dict):
            for item in value.values():
                match = find_inheritance(item)
                if match:
                    return match

    benefit = RollTableEntry.model_validate(find_inheritance(tables))
    hero.money.miedziaki = 3
    monkeypatch.setattr("utils.utils.roll_dice", lambda dice, sides: 8)
    apply_action(benefit.actions[0], hero, False)
    assert hero.money.miedziaki == 11


@pytest.mark.parametrize("penalty", [-2, -3])
def test_automaton_form_defense_penalties_reach_the_action_pipeline(hero, penalty):
    from models.action import AddAttribute
    from utils.utils import finalize_defense

    apply_action(AddAttribute(name="defense", value=penalty), hero, False)
    finalize_defense(hero)
    assert hero.defense == 10 + penalty
