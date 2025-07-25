# import json
# from typing import Any
#
# def open_json(file_path: str) -> dict:
#     with open(file_path, 'r', encoding="utf8") as f:
#         data = json.load(f)
#     return data
#
# template_ancestry = open_json("data_base/ancestry/human/human.json")
#
# def get_talent_by_name(data, talent_name):
#     for talent in data['talents']:
#         if talent['name'] == talent_name:
#             return talent
#     return None
#
# def add_spell(spell_name: str, tradition_name: str) -> Any | None:
#     tradition = open_json(f"data_base/spells/{tradition_name}_tradition.json")
#     for spell_level in tradition:
#         for spell in tradition[spell_level]:
#             if spell['name'] == spell_name:
#                 print(spell)
#                 return spell
#     return None
#
# def create_hero(template_ancestry: dict):
#     new_hero = open_json("data_base/new_hero.json")
#     new_hero.update(template_ancestry)
#     new_hero['spells'].append(add_spell("Light", "fire"))
#     new_hero['spells'].append(add_spell("Detect Magic"))
#     print(json.dumps(new_hero, indent=4))
import random


def roll_dice(num_dice: int, sides: int) -> int:
    """
    Method responsible for rolling dice and returning the result.
    :param num_dice:
    :param sides:
    :return:
    total: int - total sum of all dice rolls
    """
    if not isinstance(num_dice, int) or not isinstance(sides, int):
        raise TypeError("Number of dice and number of sides must be integers.")
    if num_dice < 1:
        raise ValueError("Number of dice must be greater than 0.")
    if sides < 1:
        raise ValueError("Number of sides must be greater than 0.")

    total = 0
    for _ in range(num_dice):
        total += random.randint(1, sides)

    if total<num_dice:
        raise ArithmeticError(f"Minimal value is {num_dice}, and you rolled {total}")
    elif total>sides*num_dice:
        raise ArithmeticError(f"Maximal value is {sides*num_dice}, and you rolled {total}")

    return total