import json
import pathlib
import random
from typing import Any, Literal


# def add_spell(spell_name: str, tradition_name: str) -> Any | None:
#     tradition = open_json(f"data_base/spells/{tradition_name}_tradition.json")
#     for spell_level in tradition:
#         for spell in tradition[spell_level]:
#             if spell['name'] == spell_name:
#                 print(spell)
#                 return spell
#     return None


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
        is_random: bool = True
) -> dict:
    if is_random:
        ancestry = random.choice(["human", "automaton", "goblin", "dwarf", "orc", "changeling"])
        project_root = pathlib.Path(__file__).parent.parent
        path_to_hero = project_root / "data_base" / "ancestry" / ancestry / f'{ancestry}.json'

    with open(path_to_hero, "r", encoding="utf8") as file:
        data = json.load(file)

    def _update_backstory(data: dict, backstory_type: tuple | dict) -> dict:
        if backstory_type is None:
            return data
        if isinstance(backstory_type, tuple):
            description, action = backstory_type  # it can be 'actions' or 'choices'
            data["backstory"].update(description)
            if "actions" in action:
                # action["actions"] may already be a list; ensure we don't create nested lists
                actions_payload = action["actions"]
                if isinstance(actions_payload, list):
                    data["actions"].extend(actions_payload)
                else:
                    data["actions"].append(actions_payload)
            elif "choices" in action:
                # action["choices"] is typically a list of dicts; use extend to avoid nested lists
                choices_payload = action["choices"]
                if isinstance(choices_payload, list):
                    data["choices"].extend(choices_payload)
                else:
                    data["choices"].append(choices_payload)
        else:
            data["backstory"].update(backstory_type)
        return data

    match ancestry:
        case "human":
            past = get_from_ancestry(roll=roll_dice(1, 20), category="past", ancestry=ancestry)
            _update_backstory(data, past)

            personality = get_from_ancestry(roll=roll_dice(3, 6), category="personality", ancestry=ancestry)
            _update_backstory(data, personality)

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
        case "goblin":
            past = get_from_ancestry(roll=roll_dice(1, 20), category="past", ancestry=ancestry)
            _update_backstory(data, past)

            personality = get_from_ancestry(roll=roll_dice(3, 6), category="personality", ancestry=ancestry)
            _update_backstory(data, personality)

            quirk = get_from_ancestry(roll=roll_dice(3, 6), category="quirk", ancestry=ancestry)
            _update_backstory(data, quirk)

            age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry=ancestry)
            _update_backstory(data, age)

            body = get_from_ancestry(roll=roll_dice(3, 6), category="body", ancestry=ancestry)
            _update_backstory(data, body)

            appearance = get_from_ancestry(roll=roll_dice(1, 20), category="appearance",
                                           ancestry=ancestry)
            _update_backstory(data, appearance)
        case "dwarf":
            past = get_from_ancestry(roll=roll_dice(1, 20), category="past", ancestry=ancestry)
            _update_backstory(data, past)

            personality = get_from_ancestry(roll=roll_dice(3, 6), category="personality", ancestry=ancestry)
            _update_backstory(data, personality)

            quirk = get_from_ancestry(roll=roll_dice(1, 20), category="quirk", ancestry=ancestry)
            _update_backstory(data, quirk)

            age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry=ancestry)
            _update_backstory(data, age)

            body = get_from_ancestry(roll=roll_dice(3, 6), category="body", ancestry=ancestry)
            _update_backstory(data, body)

            appearance = get_from_ancestry(roll=roll_dice(3, 6), category="appearance", ancestry=ancestry)
            _update_backstory(data, appearance)
        case "orc":
            past = get_from_ancestry(roll=roll_dice(1, 20), category="past", ancestry=ancestry)
            _update_backstory(data, past)

            personality = get_from_ancestry(roll=roll_dice(3, 6), category="personality", ancestry=ancestry)
            _update_backstory(data, personality)

            age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry=ancestry)
            _update_backstory(data, age)

            body = get_from_ancestry(roll=roll_dice(3, 6), category="body", ancestry=ancestry)
            _update_backstory(data, body)

            appearance = get_from_ancestry(roll=roll_dice(3, 6), category="appearance", ancestry=ancestry)
            _update_backstory(data, appearance)
        case "changeling":
            origin = get_from_ancestry(roll=roll_dice(3, 6), category="origin", ancestry=ancestry)

            if origin not in ["goblin", "krasnolud", "człowiek", "ork"]:
                origin = random.choice(["goblin", "krasnolud", "człowiek", "ork"])
            match origin:
                case "goblin":
                    age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry="goblin")
                    _update_backstory(data, age)

                    body = get_from_ancestry(roll=roll_dice(3, 6), category="body", ancestry="goblin")
                    _update_backstory(data, body)

                    appearance = get_from_ancestry(roll=roll_dice(1, 20), category="appearance",
                                                   ancestry="goblin")
                    _update_backstory(data, appearance)
                case "krasnolud":
                    age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry="dwarf")
                    _update_backstory(data, age)

                    body = get_from_ancestry(roll=roll_dice(3, 6), category="body", ancestry="dwarf")
                    _update_backstory(data, body)

                    appearance = get_from_ancestry(roll=roll_dice(3, 6), category="appearance", ancestry="dwarf")
                    _update_backstory(data, appearance)
                case "człowiek":
                    age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry="human")
                    _update_backstory(data, age)

                    body = get_from_ancestry(roll=roll_dice(3, 6), category="body", ancestry="human")
                    _update_backstory(data, body)

                    appearance = get_from_ancestry(roll=roll_dice(3, 6), category="appearance", ancestry="human")
                    _update_backstory(data, appearance)
                case "ork":
                    age = get_from_ancestry(roll=roll_dice(3, 6), category="age", ancestry="orc")
                    _update_backstory(data, age)

                    body = get_from_ancestry(roll=roll_dice(3, 6), category="body", ancestry="orc")
                    _update_backstory(data, body)

                    appearance = get_from_ancestry(roll=roll_dice(3, 6), category="appearance", ancestry="orc")
                    _update_backstory(data, appearance)

            personality = get_from_ancestry(roll=roll_dice(3, 6), category="personality", ancestry=ancestry)
            _update_backstory(data, personality)

            apparent_sex = get_from_ancestry(roll=roll_dice(1, 6), category="apparent_sex", ancestry=ancestry)
            _update_backstory(data, apparent_sex)

            true_age = get_from_ancestry(roll=roll_dice(3, 6), category="true_age", ancestry=ancestry)
            _update_backstory(data, true_age)

            oddity = get_from_ancestry(roll=roll_dice(3, 6), category="oddity", ancestry=ancestry)
            _update_backstory(data, oddity)

    return data


def change_choices_to_actions(
        character_data: dict,
        is_random: bool = True
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

    choices_pool = character_data.get("choices", [])

    try:
        for entry_to_pick in choices_pool:
            if is_random:
                choice = random.choice(entry_to_pick)
                character_data["actions"].append(choice)
                character_data["choices"].remove(entry_to_pick)
            else:
                pass
    except IndexError:
        print("No choices left.")

    return character_data


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
        entry: str,
        value: str | int,
        character_data: dict,
        is_random: bool = False
) -> dict:
    core_attributes_list = [
        "strength", "dexterity", "intelligence", "will"
    ]
    secondary_attributes_list = ["perception", "health", "defense", "healing_rate",
                                 "speed", "power", "damage", "insanity", "corruption"]

    if entry in core_attributes_list or entry == "any":
        if is_random and entry == "any":
            entry = random.choice(core_attributes_list)
        elif entry == "any":  # user needs to choose
            entry = random.choice(core_attributes_list)

        original_value = character_data['general'].get(entry)
        character_data["general"][entry] = original_value + value

    if entry == "language":
        add_language(
            language_type=value,
            character_data=character_data,
            is_random=is_random
        )

    if entry == "profession":
        add_profession(
            profession_type=value,
            character_data=character_data,
            is_random=is_random
        )

    return character_data


def bulk_update_attributes(
        character_data: dict,
        is_random: bool = False
) -> None:
    actions = character_data.get("actions")

    for action in actions:
        for entry, value in action.items():
            for attribute, value in value.items():
                add_attribute(
                    entry=entry,
                    value=value,
                    character_data=character_data,
                    is_random=is_random
                )

    return character_data


def add_wealth(character_data: dict):
    dice_roll = roll_dice(3, 6)

    project_root = pathlib.Path(__file__).parent.parent
    path_to_file = project_root / "data_base" / "equipment" / "wealth.json"

    try:
        with open(path_to_file, "r", encoding="utf8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"File {path_to_file} not found.")

    for roll_range in data["zamożność"]:
        if dice_roll in roll_range["roll"]:
            if roll_range.get("backpack", ""):
                character_data["wealth"] = roll_range["description"]
            if roll_range.get("backpack", ""):
                character_data['equipment'][3]['backpack'] = roll_range["backpack"]
            if roll_range.get("choices", ""):
                for entry in roll_range["choices"]:
                    item = random.choice(entry)

                    if isinstance(item, dict):
                        character_data['equipment'][3]['backpack'] += f', {item.get("name")}'
                        character_data['equipment'][0]['weapons'].append(item)
                    else:
                        character_data['equipment'][3]['backpack'] += f', {item}'
            if roll_range.get("money", ""):
                amount = roll_dice(
                    num_dice=roll_range["money"].get("dice_amount"),
                    sides=roll_range["money"].get("dice_type")
                )

                add_money(
                    amount=amount,
                    money_type=roll_range["money"].get("type"),
                    character_data=character_data)
            break

    return character_data


def add_money(
        amount: int,
        money_type: Literal["okrawki", "miedziaki", "srebrniki", "złote korony"],
        character_data: dict
):
    money_list = ["okrawki", "miedziaki", "srebrniki", "złote korony"]

    if money_type not in money_list:
        raise ValueError(f"Wrong money type: {money_type}. Choose one of: {money_list}")

    match money_type:
        case "okrawki":
            character_data["money"][0]["okrawki"] += amount
        case "miedziaki":
            character_data["money"][1]["miedziaki"] += amount
        case "srebrniki":
            character_data["money"][2]["srebrniki"] += amount
        case "złote korony":
            character_data["money"][3]["złote korony"] += amount

    return character_data


def add_weapon(item_name: str, character_data: dict):
    project_root = pathlib.Path(__file__).parent.parent
    path_to_file = project_root / "data_base" / "equipment" / "equ.json"

    try:
        with open(path_to_file, "r", encoding="utf8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"File {path_to_file} not found.")
    all_weapons = data['store']['weapons']
    item_info = next(
        (item for item in all_weapons if item["name"].lower() == item_name.lower()),
        None
    )
    character_data['equipment'][0]['weapons'].append(item_info)
    return item_info


def add_shield(item_name: str, character_data: dict):
    project_root = pathlib.Path(__file__).parent.parent
    path_to_file = project_root / "data_base" / "equipment" / "equ.json"

    try:
        with open(path_to_file, "r", encoding="utf8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"File {path_to_file} not found.")
    all_shields = data['store']['shields']
    item_info = next(
        (item for item in all_shields if item["name"].lower() == item_name.lower()),
        None
    )
    character_data['equipment'][1]['shields'].append(item_info)
    return item_info


def add_armor(item_name: str, character_data: dict):
    project_root = pathlib.Path(__file__).parent.parent
    path_to_file = project_root / "data_base" / "equipment" / "equ.json"

    try:
        with open(path_to_file, "r", encoding="utf8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"File {path_to_file} not found.")
    all_armors = data['store']['armors']
    item_info = next(
        (item for item in all_armors if item["name"].lower() == item_name.lower()),
        None
    )
    character_data['equipment'][2]['armors'].append(item_info)
    return item_info


def add_oddity(character_data: dict):
    dice_roll = roll_dice(1, 120)

    project_root = pathlib.Path(__file__).parent.parent
    path_to_file = project_root / "data_base" / "equipment" / "oddity.json"

    try:
        with open(path_to_file, "r", encoding="utf8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"File {path_to_file} not found.")

    for roll_range in data["kurioza"]:
        if dice_roll in roll_range["roll"]:
            character_data["oddity"] = roll_range["description"]
    return character_data


def get_hero(ancestry, is_random):
    character_data = build_hero(ancestry=ancestry, is_random=is_random)

    add_wealth(character_data)
    add_oddity(character_data)

    change_choices_to_actions(character_data, is_random=is_random)

    bulk_update_attributes(character_data=character_data, is_random=is_random)
    print(character_data)
    return character_data
