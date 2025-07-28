# 1"""
# 1. dostali karte postaci jako edytowalny PDF
# 2. wybór poziomu postaci
# 2a. Losowanie postaci..
# 3. wybór pochodzenia (człowiekiem, orkiem)
# 4. wybór klasy
# 4. Wypisywanie informacji o postacji na forncie UI - FLASK
# 5. Gdzie trzymamy dane o rzeczach ( zaklęcia, pochodzenia, talenty, języki itd)
# 6. Rzucanie kostkami (losowanie z tabeli, wyciągnie informacji z JSONów)
#
#
#
#
# ---
# 1. random
# - Poziomu [ ]
# - Ścieżka [ ]
# - pochodzenie [ ]
#
# ---
# Obsługa suplementów
#
# """
import json
import pathlib

from utils.utils import roll_dice, get_from_ancestry

roll = roll_dice(1,20)
desc, actions = get_from_ancestry(roll, "past", "human")

project_root = pathlib.Path(__file__).parent
path_template = project_root / "data_base" / "new_hero.json"
new_hero_template = project_root / "output" / "new_human.json"

with open(path_template, "r", encoding="utf-8") as file:
    data = json.load(file)

data.update(desc)
data.update(actions)
print(data)

with open(new_hero_template, "w", encoding="utf-8") as file:
    json.dump(data,file, indent=4)

