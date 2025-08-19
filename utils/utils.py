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

# TODO: Choose complex attribute ad add attribute to user actions in json

# TODO: Inject new_hero.json to PDF
# TODO: save pdf

character_data = build_hero(ancestry="human")


def change_complex_action_to_simple(character_data: dict, is_random: bool = False) -> list[dict]:
    """
    Handles user choices from a list of choice dictionaries.

    Args:
        choices_list: [{'language': 'any', 'profession': 'any'}, {'strength': 2, 'dexterity': 2}]
        random_choice: If True, randomly selects options instead of asking user

    Returns:
        List of user_actions based on user selections or random choices
        :param is_random:
        :param character_data:
    """

    user_actions = []
    choices_list = character_data.get("complex_choices", [])

    for choice_dict in choices_list:
        if len(choice_dict) > 1:  # Multiple options to choose from
            options = list(choice_dict.keys())

            if is_random:
                # Randomly select an option
                selected_key = random.choice(options)
                selected_value = choice_dict[selected_key]
                print(f"Randomly selected: {selected_key.capitalize()} = {selected_value}")
            else:
                print(f"Choose one of the following options:")
                for i, option in enumerate(options, 1):
                    print(f"{i}. {option.capitalize()}: {choice_dict[option]}")

                # Get user input
                while True:
                    try:
                        choice_num = int(input("Enter your choice (number): ")) - 1  # here we will change for API input
                        if 0 <= choice_num < len(options):
                            selected_key = options[choice_num]
                            selected_value = choice_dict[selected_key]
                            break
                        else:
                            print("Invalid choice. Please try again.")
                    except ValueError:
                        print("Please enter a valid number.")

            user_action = {
                "add_attribute": {selected_key: selected_value}
            }
            user_actions.append(user_action)
        else:
            # Only one option, add it directly
            key, value = list(choice_dict.items())[0]
            user_action = {
                "add_attribute": {key: value}
            }
            user_actions.append(user_action)

    return user_actions


user_actions = change_complex_action_to_simple(character_data, is_random=True)


def add_attribute(attribute: str, value: str | int, character_data: dict, is_random: bool = False) -> None:
    languages_list = ["Wspólny", "Mroczna mowa", "Krasnoludzki", "Elficki", "Wysoki archaik", "Trolli",
                      "Sekretne języki", "Martwe języki"]
    core_attributes = ["strength", "dexterity", "intelligence", "will"]
    character_languages = character_data["general"].get("language")
    possible_languages_to_learn = []
    langs_known = []

    if attribute in core_attributes or attribute == "any":
        if is_random and attribute == "any":
            attribute = random.choice(core_attributes)
        elif attribute == "any":        # user needs to choose
            attribute = random.choice(core_attributes)

        original_value = character_data['general'].get(attribute)
        character_data["general"][attribute] = original_value + value
        return


    if attribute == "language":
        character_languages = character_data["general"].get("language")
        possible_languages_to_learn = []
        langs_known = []

        for existing_language in character_languages:
            langs_known.append(existing_language['name'])

        if is_random and value['name'] == "any":
            language_to_add = random.choice(languages_list)
        #
        # elif value['name'] in languages_list:
        #     language_to_add = value['name']
        #
        # for existing_language in character_languages:
        #     if existing_language['name'] == language_to_add:
        #         language_to_add = random.choice(languages_list)
        #     if value['known'] is True:
        #         character_data["general"]["language"].append({'known': True, 'name': language_to_add})
        #     else:
        #         character_data["general"]["language"].append({'known': False, 'name': language_to_add})




def update_attributes(character_data: dict, user_actions: list[dict], is_random: bool = False) -> None:
    for action in user_actions:
        character_data["user_actions"].append(action)
    attributes_to_update = character_data.get("user_actions")

    for attribute in attributes_to_update:
        for key, value in attribute.items():
            for attribute, value in value.items():
                add_attribute(attribute=attribute,
                              value=value,
                              character_data=character_data,
                              is_random=is_random)

    print(character_data)


update_attributes(character_data=character_data, user_actions=user_actions, is_random=True)
