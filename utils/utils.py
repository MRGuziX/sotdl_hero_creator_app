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
                if roll_value.get("user_actions"):
                    action = {"user_actions": roll_value.get("user_actions")}
                    return description, action
                elif roll_value.get("complex_choices"):
                    action = {"complex_choices": roll_value.get("complex_choices")}
                    return description, action
                else:
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
            description, action = backstory_type  # it can be 'user_actions' or 'complex_choices'
            data["backstory"].update(description)
            if "user_actions" in action:
                data["user_actions"].append(action["user_actions"])
            elif "complex_choices" in action:
                data["complex_choices"].append(action["complex_choices"])
            else:
                pass
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
            case "automaton":
                age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry=ancestry)
                _update_backstory(data, age)

                function = get_from_ancestry(roll=roll_dice(1, 20), category="function", ancestry=ancestry)
                _update_backstory(data, function)

                form = get_from_ancestry(roll=roll_dice(3, 6), category="form", ancestry=ancestry)
                _update_backstory(data, form)

                appearance = get_from_ancestry(roll=roll_dice(3, 6), category="appearance", ancestry=ancestry)
                _update_backstory(data, appearance)

                personality = get_from_ancestry(roll=roll_dice(3, 6), category="personality", ancestry=ancestry)
                _update_backstory(data, personality)

                past = get_from_ancestry(roll=roll_dice(1, 20), category="past", ancestry=ancestry)
                _update_backstory(data, past)

    # print(data)
    return data


# TODO: Add open_json_template method
# TODO: Add save_dict_to_json method
# TODO: Pydantic?
# TODO: Inject new_hero.json to PDF
# TODO: save pdf

#
# data = build_hero(ancestry="automaton")
#
#
# def complex_choices_extractor(data: dict) -> dict:
#     complex = data.get("complex_choices")
#     print(complex)
#     converted_choices = {
#     }
#
#     for choice in complex:
#         for key, value in choice.items():
#             converted_action = {"add_attribute": {key: value}}
#             converted_choices.update(converted_action)
#
#     print(converted_choices)
#     return converted_choices
#
#
# complex_choices_extractor(data)
