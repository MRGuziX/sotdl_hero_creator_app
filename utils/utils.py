import json
import pathlib
import random
from typing import Any


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


def roll_dice(
        num_dice: int,
        sides: int
) -> int:
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


def get_from_ancestry(
        roll: int,
        category: str,
        ancestry: str
) -> None | tuple[dict[str, Any], Any] | dict[str, Any]:
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
                if roll_value.get("actions"):
                    action = {"actions": roll_value.get("actions")}
                    return description, action
                elif roll_value.get("choices"):
                    action = {"choices": roll_value.get("choices")}
                    return description, action
                else:
                    return description

    except FileNotFoundError:
        raise FileNotFoundError(f"File {path_to_file} not found.")


def build_hero(
        ancestry: str,
        hero_lvl: int = 0,
        is_random: bool = False
) -> dict:
    project_root = pathlib.Path(__file__).parent.parent
    path_to_hero = project_root / "data_base" / "ancestry" / ancestry / f'{ancestry}.json'

    with open(path_to_hero, "r", encoding="utf8") as file:
        data = json.load(file)

    def _update_backstory(data: dict, backstory_type: tuple | dict) -> dict:
        if isinstance(backstory_type, tuple):
            description, action = backstory_type  # it can be 'actions' or 'choices'
            data["backstory"].update(description)
            if "actions" in action:
                data["actions"].append(action["actions"])
            elif "choices" in action:
                data["choices"].append(action["choices"])
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
# TODO: Inject new_hero.json to PDF
# TODO: save pdf

character_data = build_hero(ancestry="human")


def change_choices_to_actions(
        character_data: dict,
        is_random: bool = False
) -> list[dict]:
    """
    Handles user choices from a list of choice dictionaries.

    Args:
        choices_list: [{'language': 'any', 'profession': 'any'}, {'strength': 2, 'dexterity': 2}]
        random_choice: If True, randomly selects options instead of asking the user

    Returns:
        List of actions based on user selections or random choices
        :param is_random:
        :param character_data:
    """

    actions = []
    choices_list = character_data.get("choices", [])

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
            actions.append(user_action)
        else:
            # Only one option, add it directly
            key, value = list(choice_dict.items())[0]
            user_action = {
                "add_attribute": {key: value}
            }
            actions.append(user_action)

    return actions


actions = change_choices_to_actions(character_data, is_random=True)


def add_profession(
        profession_type: str,
        character_data: dict,
        is_random: bool = False,
) -> None:
    project_root = pathlib.Path(__file__).parent.parent
    path_to_professions = project_root / "data_base" / "professions" / "profession_tables.json"

    roll = roll_dice(1, 20)

    with open(path_to_professions, "r", encoding="utf8") as file:
        professions = json.load(file)

    professions_list = [
        "naukowa", "pospolita", "przestępcza", "wojenna", "religijna", "koczownicza"
    ]

    if is_random:
        if profession_type == "any":
            profession_type = random.choice(professions_list)
            if profession_type == "naukowa":
                add_language(
                    language_type="any",
                    known=True,
                    character_data=character_data,
                    is_random=is_random
                )

            for roll_value in professions[profession_type]:
                if roll in roll_value["roll"]:
                    description = roll_value.get("description", "")
                    if roll_value.get("add_attribute"):
                        language = roll_value.get("add_attribute")['language']
                        known = roll_value.get("add_attribute")['known']

                        add_language(
                            language_type=language,
                            known=known,
                            character_data=character_data,
                            is_random=is_random
                        )
                    character_data["professions"].append(description)

    else:
        pass
    return character_data

def add_language(
        language_type: str,
        character_data: dict,
        known: bool = False,
        is_random: bool = False
):
    languages_list = [
        "Wspólny", "Mroczna mowa", "Krasnoludzki",
        "Elficki", "Wysoki archaik", "Trolli",
        "Sekretne języki", "Martwe języki"
    ]
    character_languages_data = character_data["general"].get("language")

    languages_character_speak = [lang["name"] for lang in character_languages_data if lang["known"] is False]
    languages_character_write = [lang["name"] for lang in character_languages_data if lang["known"] is True]
    possible_languages_to_learn = []
    try:
        possible_languages_to_learn = [lang for lang in languages_list if lang not in str(character_languages_data)]
        possible_languages_to_learn.extend(languages_character_speak)
    except Exception as e:
        print(e)

    try:
        if is_random:
            if known and language_type == "any":
                # learn to write in a language that you can speak
                language_type = random.choice(languages_character_speak)
                for lang in character_data["general"]["language"]:
                    if lang['name'] == language_type:
                        lang.update(
                            {'known': True, 'name': language_type}
                        )
            elif not known and language_type == "any":
                # learn to speak in a language that you cannot speak
                language_type = random.choice(possible_languages_to_learn)
                character_data["general"]["language"].append(
                    {'known': False, 'name': language_type}
                )
        else:
            if known:
                print(languages_character_speak)
                for lang in character_data["general"]["language"]:
                    if lang['name'] == language_type:
                        lang.update(
                            {'known': True, 'name': language_type}
                        )
            elif not known and language_type not in possible_languages_to_learn:
                character_data["general"]["language"].append(
                    {'known': False, 'name': language_type}
                )
    except IndexError as e:
        print(e)
    return character_data


def add_attribute(
        attribute: str,
        value: str | int,
        character_data: dict,
        is_random: bool = False
) -> dict:
    core_attributes_list = [
        "strength", "dexterity", "intelligence", "will",
        "perception", "health", "defense", "healing_rate",
        "speed", "power", "damage", "insanity", "corruption"
    ]

    if attribute in core_attributes_list or attribute == "any":
        if is_random and attribute == "any":
            attribute = random.choice(core_attributes_list)
        elif attribute == "any":  # user needs to choose
            attribute = random.choice(core_attributes_list)

        original_value = character_data['general'].get(attribute)
        character_data["general"][attribute] = original_value + value

    # probably this should be add_language() method that is called here
    if attribute == "language":
        add_language(
            language_type=value,
            character_data=character_data,
            is_random=is_random
        )

    if attribute == "profession":
        add_profession(
            profession_type=value,
            character_data=character_data,
            is_random=is_random
        )
    return character_data


def bulk_update_attributes(
        character_data: dict,
        actions: list[dict],
        is_random: bool = False
) -> None:
    for action in actions:
        character_data["actions"].append(action)
    attributes_to_update = character_data.get("actions")

    for attribute in attributes_to_update:
        for key, value in attribute.items():
            for attribute, value in value.items():
                add_attribute(
                    attribute=attribute,
                    value=value,
                    character_data=character_data,
                    is_random=is_random
                )

    print(character_data)

# bulk_update_attributes(character_data=character_data, actions=actions, is_random=True)
