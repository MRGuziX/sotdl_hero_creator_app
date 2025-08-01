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
from typing import Any


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


def get_from_ancestry(roll: int, category: str, ancestry: str) -> None | tuple[dict[str, Any], Any] | dict[str, Any]:
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
                if roll_value.get("user_actions") is not None:
                    user_action = roll_value.get("user_actions")
                    return description, user_action
                return description

    except FileNotFoundError:
        raise FileNotFoundError(f"File {path_to_file} not found.")


def build_hero(ancestry: str, hero_lvl: int = 0, is_random: bool = False):
    project_root = pathlib.Path(__file__).parent.parent

    path_to_hero = project_root / "data_base" / "ancestry" / ancestry / f'{ancestry}.json'

    with open(path_to_hero, "r", encoding="utf8") as file:
        data = json.load(file)

    def _update_backstory(data: dict, backstory_type: tuple | dict) -> dict:
        if isinstance(backstory_type, tuple):
            description, action = backstory_type #it can be 'user_actions' or 'complex_choices'
            data["backstory"].update(description)
            if "user_actions" in action:
                data["user_actions"].append(action)
            else:
                data["complex_choices"].append(action)
        else:
            data["backstory"].update(backstory_type)
        return data

    if is_random:
        pass
    else:
        match ancestry:
            case "human":
                past = get_from_ancestry(roll=roll_dice(1, 20), category="past", ancestry=ancestry)
                _update_backstory(data, past)

                character = get_from_ancestry(roll=roll_dice(3, 6), category="character", ancestry=ancestry)
                _update_backstory(data, character)

                religion = get_from_ancestry(roll=roll_dice(3, 6), category="religion", ancestry=ancestry)
                _update_backstory(data, religion)

                age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry=ancestry)
                _update_backstory(data, age)

                body = get_from_ancestry(roll=roll_dice(3, 6), category="body", ancestry=ancestry)
                _update_backstory(data, body)

                appearance = get_from_ancestry(roll=roll_dice(3, 6), category="appearance",
                                               ancestry=ancestry)
                _update_backstory(data, appearance)

    print(data)
    return data


# TODO: Add open_json_template method
# TODO: Add save_dict_to_json method
# TODO: Pydantic?
# TODO: Inject new_hero.json to PDF
# TODO: save pdf


build_hero(ancestry="human")


def extract_attribute_choices(ancestry: str = "automaton") :
    """
    Specifically extracts attribute choices from complex_choices actions.

    Returns tuples like: ({\"strength\": 2}, {\"dexterity\": 2})
    """
    project_root = pathlib.Path(__file__).parent.parent

    path_to_hero = project_root / "data_base" / "ancestry" / ancestry / f'{ancestry}.json'

    with open(path_to_hero, "r", encoding="utf8") as file:
        data = json.load(file)

    attribute_choices = []
    user_actions = data.get('user_actions', [])

    for action in user_actions:
        if 'complex_choices' in action:
            complex_choices = action['complex_choices']

            # Look for add_attribute choices specifically
            if 'add_attribute' in complex_choices:
                add_attribute_options = complex_choices['add_attribute']
                if isinstance(add_attribute_options, list):
                    choice_tuple = tuple(add_attribute_options)
                    attribute_choices.append(choice_tuple)

    return attribute_choices

extract_attribute_choices()
