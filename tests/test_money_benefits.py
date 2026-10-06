from data.repository import load_json
from models.tables import RollTableEntry
from utils.utils import apply_action


def test_goblin_inheritance_adds_copper_to_existing_wealth(hero, monkeypatch):
    tables = load_json("ancestry/goblin/goblin_tables.json")

    def find_inheritance(value):
        if isinstance(value, list):
            for entry in value:
                if "Odziedziczyłeś" in entry.get("description", ""):
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
