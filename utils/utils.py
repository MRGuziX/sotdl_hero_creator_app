import json
import logging
import os
import pathlib
import random
import tempfile

logger = logging.getLogger(__name__)

from models.action import (
    Action,
    AddAttribute,
    AddItem,
    AddLanguage,
    AddProfession,
    Choice,
    GrantLiteracy,
)
from models.base_hero import AncestryHero
from models.ancestry import AncestryData
from models.equipment import Weapon, Armor, Shield
from models.language import Language
from models.tables import ProfessionEntry, RollTableEntry, WealthEntry
from .pdf_creator import fill_pdf

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

ALL_LANGUAGES = [
    "Wspólny", "Mroczna mowa", "Krasnoludzki",
    "Elficki", "Wysoki archaik", "Trolli",
    "Sekretne języki", "Martwe języki",
]

CORE_ATTRIBUTES = ["strength", "dexterity", "intelligence", "will"]

SECONDARY_ATTRIBUTES = [
    "perception", "health", "defense", "healing_rate",
    "speed", "power", "damage", "insanity", "corruption",
]

PROFESSION_CATEGORIES = [
    "naukowa", "pospolita", "przestępcza", "wojenna", "religijna", "koczownicza",
]


def roll_dice(num_dice: int, sides: int) -> int:
    if not isinstance(num_dice, int) or not isinstance(sides, int):
        raise TypeError("Number of dice and number of sides must be integers.")
    if num_dice < 1:
        raise ValueError("Number of dice must be greater than 0.")
    if sides < 1:
        raise ValueError("Number of sides must be greater than 0.")

    total = sum(random.randint(1, sides) for _ in range(num_dice))

    if total < num_dice:
        raise ArithmeticError(f"Minimal value is {num_dice}, and you rolled {total}")
    if total > sides * num_dice:
        raise ArithmeticError(f"Maximal value is {sides * num_dice}, and you rolled {total}")

    return total


def _parse_dice_value(value: int | float | str) -> int | float:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and "d" in value.lower():
        parts = value.lower().split("d")
        if len(parts) == 2:
            num_dice = int(parts[0]) if parts[0] else 1
            sides = int(parts[1])
            return roll_dice(num_dice, sides)
    return int(value)


def _load_json(relative_path: str) -> dict:
    path = PROJECT_ROOT / relative_path
    with open(path, "r", encoding="utf8") as f:
        return json.load(f)


def get_from_ancestry(
        roll: int,
        category: str,
        ancestry: str,
) -> RollTableEntry | None:
    data = _load_json(f"data_base/ancestry/{ancestry}/{ancestry}_tables.json")

    if category not in data:
        raise ValueError(f"Category {category} not found for ancestry {ancestry}")

    for entry_data in data[category]:
        if roll in entry_data["roll"]:
            return RollTableEntry.model_validate(entry_data)

    return None


def build_hero(
        ancestry: str,
) -> tuple[AncestryHero, list[Action], list[Choice]]:
    data = _load_json(f"data_base/ancestry/{ancestry}/{ancestry}.json")
    ancestry_data = AncestryData.model_validate(data)

    logger.info("Building hero: ancestry=%s", ancestry)

    hero = AncestryHero(
        ancestry_name=ancestry_data.general.ancestry_name,
        strength=ancestry_data.general.strength,
        dexterity=ancestry_data.general.dexterity,
        intelligence=ancestry_data.general.intelligence,
        will=ancestry_data.general.will,
        perception=ancestry_data.general.perception,
        defense=ancestry_data.general.defense,
        health=ancestry_data.general.health,
        healing_rate=ancestry_data.general.healing_rate,
        size=ancestry_data.general.size,
        speed=ancestry_data.general.speed,
        power=ancestry_data.general.power,
        damage=ancestry_data.general.damage,
        insanity=ancestry_data.general.insanity,
        corruption=ancestry_data.general.corruption,
        languages=ancestry_data.general.languages,
        talents=ancestry_data.talents,
    )

    actions = list(ancestry_data.actions)
    choices = list(ancestry_data.choices)

    def _update_backstory(entry: RollTableEntry | None, category: str):
        if entry is None:
            return
        hero.backstory[category] = entry.description
        logger.info("  backstory [%s]: %s", category, entry.description[:80])
        if entry.actions:
            logger.info("  backstory [%s] adds actions: %s", category, [a.type for a in entry.actions])
        if entry.choices:
            logger.info("  backstory [%s] adds %d choice group(s)", category, len(entry.choices))
        actions.extend(entry.actions)
        choices.extend(entry.choices)

    match ancestry:
        case "human":
            _update_backstory(get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "personality", ancestry), "personality")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "religion", ancestry), "religion")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "body", ancestry), "body")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "appearance", ancestry), "appearance")
        case "automaton":
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age")
            _update_backstory(get_from_ancestry(roll_dice(1, 20), "function", ancestry), "function")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "form", ancestry), "form")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "appearance", ancestry), "appearance")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "personality", ancestry), "personality")
            _update_backstory(get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past")
        case "goblin":
            _update_backstory(get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "personality", ancestry), "personality")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "quirk", ancestry), "quirk")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "body", ancestry), "body")
            _update_backstory(get_from_ancestry(roll_dice(1, 20), "appearance", ancestry), "appearance")
        case "dwarf":
            _update_backstory(get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "personality", ancestry), "personality")
            _update_backstory(get_from_ancestry(roll_dice(1, 20), "quirk", ancestry), "quirk")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "body", ancestry), "body")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "appearance", ancestry), "appearance")
        case "orc":
            _update_backstory(get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "personality", ancestry), "personality")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "body", ancestry), "body")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "appearance", ancestry), "appearance")
        case "changeling":
            origin_entry = get_from_ancestry(roll_dice(3, 6), "origin", ancestry)
            if origin_entry:
                hero.backstory["origin"] = origin_entry.description

            origin = origin_entry.description if origin_entry else ""
            origin_ancestry_map = {
                "goblin": "goblin",
                "krasnolud": "dwarf",
                "człowiek": "human",
                "ork": "orc",
            }
            origin_key = origin.lower() if origin.lower() in origin_ancestry_map else random.choice(
                list(origin_ancestry_map.keys()))
            source_ancestry = origin_ancestry_map[origin_key]

            _update_backstory(get_from_ancestry(roll_dice(3, 6), "age", source_ancestry), "age")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "body", source_ancestry), "body")
            _update_backstory(
                get_from_ancestry(
                    roll_dice(1, 20) if source_ancestry == "goblin" else roll_dice(3, 6),
                    "appearance", source_ancestry,
                ), "appearance")

            _update_backstory(get_from_ancestry(roll_dice(3, 6), "personality", ancestry), "personality")
            _update_backstory(get_from_ancestry(roll_dice(1, 6), "apparent_sex", ancestry), "apparent_sex")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "true_age", ancestry), "true_age")
            _update_backstory(get_from_ancestry(roll_dice(3, 6), "oddity", ancestry), "oddity")

    logger.info("  ancestry actions: %s", [f"{a.type}({a.name})" if hasattr(a, 'name') else a.type for a in actions])
    logger.info("  ancestry choices: %d group(s)", len(choices))

    return hero, actions, choices


def add_attribute(name: str, value: int | float | str, hero: AncestryHero, is_random: bool = False):
    resolved_value = _parse_dice_value(value)

    if name == "any":
        name = random.choice(CORE_ATTRIBUTES)

    if name == "size":
        hero.size = [resolved_value]
        return

    if name in CORE_ATTRIBUTES or name in SECONDARY_ATTRIBUTES:
        current = getattr(hero, name)
        setattr(hero, name, current + int(resolved_value))


def add_language(name: str, hero: AncestryHero, can_write: bool = False, is_random: bool = False):
    spoken_names = [l.name for l in hero.languages if not l.can_write]
    known_names = [l.name for l in hero.languages]
    learnable = [l for l in ALL_LANGUAGES if l not in known_names]
    learnable.extend(spoken_names)

    if is_random:
        if can_write and name == "any":
            if spoken_names:
                name = random.choice(spoken_names)
                for lang in hero.languages:
                    if lang.name == name:
                        lang.can_write = True
                        return
        elif not can_write and name == "any":
            if learnable:
                name = random.choice(learnable)
                hero.languages.append(Language(name=name, can_speak=True, can_write=False))
            return
    else:
        if can_write:
            if name == "any" and spoken_names:
                name = random.choice(spoken_names)
            for lang in hero.languages:
                if lang.name == name:
                    lang.can_write = True
                    return
        else:
            if name == "any" and learnable:
                name = random.choice(learnable)

            if name != "any" and name not in known_names:
                hero.languages.append(Language(name=name, can_speak=True, can_write=False))


def grant_literacy(target: str, hero: AncestryHero, is_random: bool = False):
    spoken_names = [l.name for l in hero.languages if not l.can_write]

    if target == "any" and spoken_names:
        target = random.choice(spoken_names)

    for lang in hero.languages:
        if lang.name == target:
            lang.can_write = True
            return


def add_profession(name: str, hero: AncestryHero, is_random: bool = True):
    if name == "any":
        name = random.choice(PROFESSION_CATEGORIES)

    data = _load_json("data_base/professions/profession_tables.json")

    if name == "naukowa":
        grant_literacy("any", hero, is_random)

    roll = roll_dice(1, 20)
    for entry_data in data[name]:
        entry = ProfessionEntry.model_validate(entry_data)
        if roll in entry.roll:
            if entry.action:
                apply_action(entry.action, hero, is_random)
            hero.professions.append(entry.description)
            return


def add_item(name: str, hero: AncestryHero, item_data: AddItem | None = None):
    if not name:
        return

    if item_data and item_data.item_type == "weapon" and item_data.damage:
        hero.equipment.weapons.append(Weapon(
            name=item_data.name,
            damage=item_data.damage,
            grip=item_data.grip or "",
            properties=item_data.properties or "",
            price=item_data.price or "",
            availability=item_data.availability or "",
        ))
        hero.equipment.backpack.append(name.lower())
        return

    store_data = _load_json("data_base/equipment/equ.json")
    store = store_data.get("store", {})

    for category in ["weapons", "armors", "shields"]:
        for item in store.get(category, []):
            if item.get("name", "").lower() == name.lower():
                item_type = item.get("item_type")
                if item_type == "weapon":
                    hero.equipment.weapons.append(Weapon.model_validate(item))
                elif item_type == "shield":
                    hero.equipment.shields.append(Shield.model_validate(item))
                elif item_type == "armor":
                    hero.equipment.armors.append(Armor.model_validate(item))
                hero.equipment.backpack.append(name.lower())
                return

    hero.equipment.backpack.append(name.lower())


def apply_action(action: Action, hero: AncestryHero, is_random: bool = False):
    logger.info("  apply: %s", action.model_dump())
    match action:
        case AddAttribute():
            add_attribute(action.name, action.value, hero, is_random)
        case AddProfession():
            add_profession(action.name, hero, is_random)
        case AddLanguage():
            add_language(action.name, hero, action.can_write, is_random)
        case AddItem():
            add_item(action.name, hero, action)
        case GrantLiteracy():
            grant_literacy(action.target, hero, is_random)


def resolve_choices(
        hero: AncestryHero,
        actions: list[Action],
        choices: list[Choice],
        is_random: bool = True,
        selected_choices: list[Action] | None = None,
) -> list[Action]:
    if is_random:
        for i, choice_group in enumerate(choices):
            picked = random.choice(choice_group)
            options = [f"{a.type}({a.name})" if hasattr(a, 'name') else a.type for a in choice_group]
            picked_label = f"{picked.type}({picked.name})" if hasattr(picked, 'name') else picked.type
            logger.info("  choice group %d: options=%s -> picked=%s", i, options, picked_label)
            actions.append(picked)
    elif selected_choices:
        for choice in selected_choices:
            label = f"{choice.type}({choice.name})" if hasattr(choice, 'name') else choice.type
            logger.info("  user selected: %s", label)
        actions.extend(selected_choices)

    return actions


def expand_any_to_choices(
        actions: list[Action],
        choices: list[Choice],
) -> tuple[list[Action], list[Choice]]:
    remaining_actions = []
    for action in actions:
        match action:
            case AddAttribute(name="any", value=value):
                choices.append([
                    AddAttribute(name=attr, value=value) for attr in CORE_ATTRIBUTES
                ])
            case AddProfession(name="any"):
                choices.append([
                    AddProfession(name=cat) for cat in PROFESSION_CATEGORIES
                ])
            case AddLanguage(name="any", can_write=can_write):
                choices.append([
                    AddLanguage(name=lang, can_write=can_write) for lang in ALL_LANGUAGES
                ])
            case _:
                remaining_actions.append(action)
    return remaining_actions, choices


def add_wealth(hero: AncestryHero, actions: list[Action], choices: list[Choice]):
    dice_roll = roll_dice(3, 6)
    logger.info("  wealth roll: %d", dice_roll)
    data = _load_json("data_base/equipment/wealth.json")

    for entry_data in data["zamożność"]:
        entry = WealthEntry.model_validate(entry_data)
        if dice_roll in entry.roll:
            logger.info("  wealth result: %s", entry.description[:60])
            hero.wealth = entry.description

            if entry.backpack:
                hero.equipment.backpack.append(entry.backpack)

            actions.extend(entry.actions)
            choices.extend(entry.choices)

            if entry.money:
                amount = roll_dice(
                    num_dice=entry.money.dice_amount,
                    sides=entry.money.dice_type,
                )
                money_type = entry.money.type
                if money_type == "złote korony":
                    money_type = "zlote_korony"
                current = getattr(hero.money, money_type)
                setattr(hero.money, money_type, current + amount)

            break


def add_oddity(hero: AncestryHero):
    dice_roll = roll_dice(1, 120)
    data = _load_json("data_base/equipment/oddity.json")

    for entry in data["kurioza"]:
        if dice_roll in entry["roll"]:
            hero.oddity = entry["description"]
            logger.info("  oddity roll %d: %s", dice_roll, hero.oddity[:60])
            return


def get_hero(ancestry: str, is_random: bool) -> AncestryHero | tuple[AncestryHero, list[Choice]]:
    logger.info("=== get_hero: ancestry=%s, is_random=%s ===", ancestry, is_random)
    hero, actions, choices = build_hero(ancestry=ancestry)

    add_wealth(hero, actions, choices)
    add_oddity(hero)

    if not is_random:
        actions, choices = expand_any_to_choices(actions, choices)
        logger.info("Manual mode: %d actions to apply, %d choice groups for user", len(actions), len(choices))
        for action in actions:
            apply_action(action, hero, is_random=False)

        if choices:
            logger.info("Returning hero with %d unresolved choice group(s)", len(choices))
            return hero, choices

    if is_random:
        logger.info("Random mode: resolving %d choice group(s)", len(choices))
        actions = resolve_choices(hero, actions, choices, is_random=True)
        logger.info("Applying %d total actions", len(actions))
        for action in actions:
            apply_action(action, hero, is_random=True)
        fill_pdf(hero, os.path.join(tempfile.gettempdir(), "hero_card.pdf"))

    logger.info(
        "=== Hero complete: %s | STR=%d DEX=%d INT=%d WILL=%d | %d prof(s) | %d lang(s) | wealth=%s ===",
        hero.ancestry_name, hero.strength, hero.dexterity, hero.intelligence, hero.will,
        len(hero.professions), len(hero.languages), hero.wealth[:30] if hero.wealth else "none",
    )
    return hero
