import json
from typing import Any

def open_json(file_path: str) -> dict:
    with open(file_path, 'r', encoding="utf8") as f:
        data = json.load(f)
    return data

template_ancestry = open_json("data_base/ancestry/human/human.json")

def get_talent_by_name(data, talent_name):
    for talent in data['talents']:
        if talent['name'] == talent_name:
            return talent
    return None

def add_spell(spell_name: str, tradition_name: str) -> Any | None:
    tradition = open_json(f"data_base/spells/{tradition_name}_tradition.json")
    for spell_level in tradition:
        for spell in tradition[spell_level]:
            if spell['name'] == spell_name:
                print(spell)
                return spell
    return None

def create_hero(template_ancestry: dict):
    new_hero = open_json("data_base/new_hero.json")
    new_hero.update(template_ancestry)
    new_hero['spells'].append(add_spell("Light", "fire"))
    new_hero['spells'].append(add_spell("Detect Magic"))
    print(json.dumps(new_hero, indent=4))
