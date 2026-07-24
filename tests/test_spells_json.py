import json
import os
import glob
import pytest

def get_spell_files():
    base_path = os.path.join("data_base", "spells")
    return glob.glob(os.path.join(base_path, "*.json"))

@pytest.mark.parametrize("file_path", get_spell_files())
def test_each_spell_has_card_description(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for level_key, spells in data.items():
        if level_key.startswith("level_"):
            for spell in spells:
                assert "card_description" in spell, f"Missing 'card_description' in {file_path}, spell: {spell.get('name')}"

if __name__ == "__main__":
    # Quick manual check if run directly
    files = get_spell_files()
    missing_count = 0
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for level_key, spells in data.items():
            if level_key.startswith("level_"):
                for spell in spells:
                    if "card_description" not in spell:
                        print(f"MISSING: {file_path} -> {spell.get('name')}")
                        missing_count += 1
    print(f"Total missing: {missing_count}")
