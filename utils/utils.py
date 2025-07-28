
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
import json
import pathlib
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

    if total < num_dice:
        raise ArithmeticError(f"Minimal value is {num_dice}, and you rolled {total}")
    elif total > sides * num_dice:
        raise ArithmeticError(f"Maximal value is {sides * num_dice}, and you rolled {total}")

    return total

def get_from_ancestry(roll: int, category: str, ancestry: str) -> dict:

    project_root = pathlib.Path(__file__).parent.parent
    path_to_file = project_root / "data_base" / "ancestry" / ancestry / f'{ancestry}_tables.json'

    if not isinstance(roll, int) or not isinstance(category, str) or not isinstance(category, str):
        raise TypeError("'roll', 'category' and 'ancestry' params must be expected types: int, str, str.")

    try:
        with open(path_to_file, "r", encoding="utf8") as file:
            data = json.load(file)

        if category not in data:
            raise ValueError(f"Category {category} not found in {path_to_file}")

        for roll_value in data[category]:
            if roll in roll_value["roll"]:
                description = {category: roll_value.get("description", "")}
                user_action = roll_value.get("user_actions", "")
                return description, user_action

    except FileNotFoundError:
        raise FileNotFoundError(f"File {path_to_file} not found.")


# TODO: Add open_json_template method
# TODO: Add save_dict_to_json method
# TODO: inject value to new_hero.json
# TODO: Inject new_hero.json to PDF
# TODO: save pdf
