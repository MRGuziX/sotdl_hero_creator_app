import json
import logging
import os
import pathlib
import random
import re

from pydantic import TypeAdapter

from models.action import (
    Action,
    AddAttribute,
    AddItem,
    AddLanguage,
    AddProfession,
    AddReligion,
    AddSpell,
    AddTalent,
    AddTradition,
    Choice,
    GrantLiteracy,
    UpdateLanguage,
)
from models.ancestry import AncestryData
from models.base_hero import AncestryHero
from models.equipment import Armor, Shield, Weapon
from models.language import Language
from models.path import PathData
from models.spell import Spell
from models.tables import ProfessionEntry, RollTableEntry, WealthEntry
from models.talent import Talent

logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

ALL_LANGUAGES = [
    "Wspólny",
    "Mroczna mowa",
    "Krasnoludzki",
    "Elficki",
    "Wysoki archaik",
    "Trolli",
    "Sekretne języki",
    "Martwe języki",
]

CORE_ATTRIBUTES = ["strength", "dexterity", "intelligence", "will"]

SECONDARY_ATTRIBUTES = [
    "perception",
    "health",
    "defense",
    "healing_rate",
    "speed",
    "power",
    "damage",
    "insanity",
    "corruption",
]

PROFESSION_CATEGORIES = [
    "naukowa",
    "pospolita",
    "przestępcza",
    "wojenna",
    "religijna",
    "koczownicza",
]

TRADITION_FILE_MAP = {
    "Magia Niebiańska": "heaven_tradition.json",
    "Życie": "life_tradition.json",
    "Magia Ognia": "fire_tradition.json",
    "Ogień": "fire_tradition.json",
    "Magia Wody": "water_tradition.json",
    "Woda": "water_tradition.json",
    "Magia Bitewna": "battle_tradition.json",
    "Ziemia": "earth_tradition.json",
    "Natura": "nature_tradition.json",
    "Magia Pierwotna": "primal_tradition.json",
    "Klątwy": "curse_tradition.json",
    "Uroki": "enchantment_tradition.json",
    "Teurgia": "theurgy_tradition.json",
    "Wiedźmiarstwo": "witchcraft_tradition.json",
}


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
        raise ArithmeticError(
            f"Maximal value is {sides * num_dice}, and you rolled {total}"
        )

    return total


def _parse_dice_value(value: int | float | str) -> int | float:
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        raise TypeError("Dice value must be a number or string.")

    expression = value.strip().lower()
    dice_match = re.fullmatch(r"(?:(\d+)?d)(\d+)", expression)
    if dice_match:
        num_dice = int(dice_match.group(1) or 1)
        sides = int(dice_match.group(2))
        return roll_dice(num_dice, sides)

    try:
        return int(expression)
    except ValueError as error:
        raise ValueError(f"Invalid dice value: {value!r}") from error


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
    level: int = 0,
    path_name: str | None = None,
) -> tuple[AncestryHero, list[Action], list[Choice]]:
    data = _load_json(f"data_base/ancestry/{ancestry}/{ancestry}.json")
    ancestry_data = AncestryData.model_validate(data)

    logger.info(
        "Building hero: ancestry=%s, level=%d, path=%s", ancestry, level, path_name
    )

    hero = AncestryHero(
        ancestry_name=ancestry_data.general.ancestry_name,
        ancestry_id=ancestry,
        level=level,
        path_name=path_name,
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

    for lvl, benefit in ancestry_data.level_benefits.items():
        if lvl <= level:
            logger.info("  adding ancestry level %d benefits", lvl)
            actions.extend(benefit.actions)
            choices.extend(benefit.choices)

    if level >= 1 and path_name:
        path_file = f"data_base/paths/novice/{path_name.lower()}.json"
        if os.path.exists(PROJECT_ROOT / path_file):
            path_data_json = _load_json(path_file)
            for benefit in path_data_json.get("level_benefits", {}).values():
                benefit_choices = benefit.get("choices", [])
                if benefit_choices and isinstance(benefit_choices[0], dict):
                    benefit["choices"] = [benefit_choices]
            path_data = PathData.model_validate(path_data_json)
            for lvl, benefit in path_data.level_benefits.items():
                if int(lvl) <= level:
                    logger.info("  adding path %s level %s benefits", path_name, lvl)
                    actions.extend(benefit.actions)
                    choices.extend(benefit.choices)

        else:
            logger.warning("Path file %s not found", path_file)

    def _update_backstory(entry: RollTableEntry | None, category: str):
        if entry is None:
            return
        hero.backstory[category] = entry.description
        logger.info("  backstory [%s]: %s", category, entry.description[:80])
        if entry.actions:
            logger.info(
                "  backstory [%s] adds actions: %s",
                category,
                [a.type for a in entry.actions],
            )
        if entry.choices:
            logger.info(
                "  backstory [%s] adds %d choice group(s)", category, len(entry.choices)
            )
        actions.extend(entry.actions)
        choices.extend(entry.choices)

    match ancestry:
        case "human":
            _update_backstory(
                get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "personality", ancestry),
                "personality",
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "religion", ancestry), "religion"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "body", ancestry), "body"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "appearance", ancestry), "appearance"
            )
        case "automaton":
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(1, 20), "function", ancestry), "function"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "form", ancestry), "form"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "appearance", ancestry), "appearance"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "personality", ancestry),
                "personality",
            )
            _update_backstory(
                get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past"
            )
        case "goblin":
            _update_backstory(
                get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "personality", ancestry),
                "personality",
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "quirk", ancestry), "quirk"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "body", ancestry), "body"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(1, 20), "appearance", ancestry),
                "appearance",
            )
        case "dwarf":
            _update_backstory(
                get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "personality", ancestry),
                "personality",
            )
            _update_backstory(
                get_from_ancestry(roll_dice(1, 20), "quirk", ancestry), "quirk"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "body", ancestry), "body"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "appearance", ancestry), "appearance"
            )
        case "orc":
            _update_backstory(
                get_from_ancestry(roll_dice(1, 20), "past", ancestry), "past"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "personality", ancestry),
                "personality",
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "age", ancestry), "age"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "body", ancestry), "body"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "appearance", ancestry), "appearance"
            )
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
            origin_key = (
                origin.lower()
                if origin.lower() in origin_ancestry_map
                else random.choice(list(origin_ancestry_map.keys()))
            )
            source_ancestry = origin_ancestry_map[origin_key]

            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "age", source_ancestry), "age"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "body", source_ancestry), "body"
            )
            _update_backstory(
                get_from_ancestry(
                    roll_dice(1, 20)
                    if source_ancestry == "goblin"
                    else roll_dice(3, 6),
                    "appearance",
                    source_ancestry,
                ),
                "appearance",
            )

            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "personality", ancestry),
                "personality",
            )
            _update_backstory(
                get_from_ancestry(roll_dice(1, 6), "apparent_sex", ancestry),
                "apparent_sex",
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "true_age", ancestry), "true_age"
            )
            _update_backstory(
                get_from_ancestry(roll_dice(3, 6), "oddity", ancestry), "oddity"
            )

    logger.info(
        "  ancestry actions: %s",
        [f"{a.type}({a.name})" if hasattr(a, "name") else a.type for a in actions],
    )
    logger.info("  ancestry choices: %d group(s)", len(choices))

    return hero, actions, choices


def add_attribute(
    name: str, value: int | float | str, hero: AncestryHero, is_random: bool = False
):
    resolved_value = _parse_dice_value(value)

    if name == "any":
        name = random.choice(CORE_ATTRIBUTES)

    if name == "size":
        hero.size = [resolved_value]
        return

    if name in CORE_ATTRIBUTES or name in SECONDARY_ATTRIBUTES:
        current = getattr(hero, name)
        setattr(hero, name, current + int(resolved_value))


def add_language(
    name: str, hero: AncestryHero, can_write: bool = False, is_random: bool = False
):
    spoken_names = [language.name for language in hero.languages if not language.can_write]
    known_names = [language.name for language in hero.languages]
    learnable = [language for language in ALL_LANGUAGES if language not in known_names]
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
                hero.languages.append(
                    Language(name=name, can_speak=True, can_write=False)
                )
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
                hero.languages.append(
                    Language(name=name, can_speak=True, can_write=False)
                )


def grant_literacy(target: str, hero: AncestryHero, is_random: bool = False):
    spoken_names = [language.name for language in hero.languages if not language.can_write]

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


def add_talent(
    name: str,
    description: str | None,
    hero: AncestryHero,
    level: int = 0,
    upgrade: str | None = None,
):
    upgraded_name = f"{name} (poz. 2)"
    existing = next(
        (talent for talent in hero.talents if talent.name in {name, upgraded_name}),
        None,
    )
    if existing:
        if existing.name == name:
            existing.name = upgraded_name
        if upgrade:
            if "2k6" in upgrade and "1k6" in (description or existing.description):
                existing.description = (description or existing.description).replace(
                    "1k6", "2k6"
                )
            else:
                existing.description = upgrade
        return
    hero.talents.append(Talent(name=name, description=description or "", level=level))


def add_spell(name: str, hero: AncestryHero):
    # Try to find full spell data in known traditions
    known_trads = [
        get_tradition_name_from_talent(t.name)
        for t in hero.talents
        if get_tradition_name_from_talent(t.name)
    ]

    for trad in known_trads:
        filename = TRADITION_FILE_MAP.get(trad)
        if not filename:
            continue
        path = f"data_base/spells/{filename}"
        if not os.path.exists(PROJECT_ROOT / path):
            continue

        data = _load_json(path)
        for lvl_key, spells in data.items():
            for s_data in spells:
                if s_data["name"] == name:
                    hero.spells.append(
                        Spell(
                            name=s_data["name"],
                            description=s_data.get("description")
                            or s_data.get("mechanics")
                            or "Brak opisu",
                            level=s_data.get("level", 0),
                            tags=s_data.get("tags", []),
                            target=s_data.get("target"),
                            area=s_data.get("area"),
                            duration=s_data.get("duration"),
                            critical_success=s_data.get("critical_success"),
                        )
                    )
                    return

    # Fallback
    hero.spells.append(Spell(name=name, description="Nowe zaklęcie", level=0))


def add_tradition(name: str, hero: AncestryHero):
    # For now we just store it in a way that can be seen, maybe as a talent or just a note
    # Actually, hero should probably have a list of traditions
    hero.talents.append(
        Talent(
            name=f"Tradycja: {name}",
            description="Dostęp do zaklęć tej tradycji",
            level=0,
        )
    )


def add_religion(name: str, hero: AncestryHero):
    hero.religion = name


def update_language(
    name: str, hero: AncestryHero, can_speak: bool = True, can_write: bool = True
):
    if name == "known":
        for lang in hero.languages:
            lang.can_speak = can_speak
            lang.can_write = can_write
        return

    for lang in hero.languages:
        if lang.name == name:
            lang.can_speak = can_speak
            lang.can_write = can_write
            return


def get_tradition_name_from_talent(talent_name: str) -> str | None:
    if talent_name.startswith("Tradycja: "):
        return talent_name.replace("Tradycja: ", "")
    return None


def get_spells_for_tradition(tradition_name: str, power_level: int) -> list[str]:
    filename = TRADITION_FILE_MAP.get(tradition_name)
    if not filename:
        logger.warning(f"No file mapping for tradition: {tradition_name}")
        return []

    path = f"data_base/spells/{filename}"
    if not os.path.exists(PROJECT_ROOT / path):
        logger.warning(f"Spell file not found: {path}")
        return []

    data = _load_json(path)
    available_spells = []
    for lvl in range(power_level + 1):
        key = f"level_{lvl}"
        if key in data:
            for spell_data in data[key]:
                available_spells.append(spell_data["name"])
    return available_spells


def add_item(name: str, hero: AncestryHero, item_data: AddItem | None = None):
    if not name:
        return

    if item_data and item_data.item_type == "weapon" and item_data.damage:
        hero.equipment.weapons.append(
            Weapon(
                name=item_data.name,
                damage=item_data.damage,
                grip=item_data.grip or "",
                properties=item_data.properties or "",
                price=item_data.price or "",
                availability=item_data.availability or "",
            )
        )
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
        case AddTalent():
            add_talent(
                action.name, action.description, hero, hero.level, action.upgrade
            )
        case AddSpell():
            add_spell(action.name, hero)
        case AddTradition():
            if action.name == "religious_tradition" and is_random:
                religions_data = _load_json(
                    "data_base/paths/novice/cleric_religions.json"
                )
                if hero.religion in religions_data:
                    trad = random.choice(religions_data[hero.religion])
                    add_tradition(trad, hero)
                else:
                    # Fallback if religion not set? Let's pick a random religion first if so
                    all_religions = list(religions_data.keys())
                    hero.religion = random.choice(all_religions)
                    trad = random.choice(religions_data[hero.religion])
                    add_tradition(trad, hero)
            else:
                add_tradition(action.name, hero)
        case AddReligion():
            add_religion(action.name, hero)
        case UpdateLanguage():
            update_language(action.name, hero, action.can_speak, action.can_write)
        case _:
            raise TypeError(f"Unsupported action type: {type(action).__name__}")


def _expand_dynamic_choice_group(
    hero: AncestryHero, choice_group: Choice
) -> list[Action]:
    religions_data = _load_json("data_base/paths/novice/cleric_religions.json")
    known_traditions = {
        tradition
        for talent in hero.talents
        if (tradition := get_tradition_name_from_talent(talent.name))
    }
    expanded_group = []
    for action in choice_group:
        match action:
            case AddTradition(name="religious_tradition"):
                traditions = [
                    tradition
                    for tradition in religions_data.get(hero.religion, [])
                    if tradition not in known_traditions
                ]
                if traditions:
                    expanded_group.extend(
                        AddTradition(name=tradition)
                        for tradition in sorted(set(traditions))
                    )
                else:
                    expanded_group.append(action)
            case AddSpell(name="known_tradition"):
                known_traditions = sorted(
                    {
                        tradition
                        for talent in hero.talents
                        if (tradition := get_tradition_name_from_talent(talent.name))
                    }
                )
                known_spells = {spell.name for spell in hero.spells}
                spells = sorted(
                    {
                        spell
                        for tradition in known_traditions
                        for spell in get_spells_for_tradition(tradition, hero.power)
                        if spell not in known_spells
                    }
                )
                if spells:
                    expanded_group.extend(AddSpell(name=spell) for spell in spells)
                else:
                    expanded_group.append(action)
            case _:
                expanded_group.append(action)
    return expanded_group


def resolve_choices(
    hero: AncestryHero,
    actions: list[Action],
    choices: list[Choice],
    is_random: bool = True,
    selected_choices: list[Action] | None = None,
) -> list[Action]:
    if is_random:
        for i, choice_group in enumerate(choices):
            expanded_group = _expand_dynamic_choice_group(hero, choice_group)

            picked = random.choice(expanded_group)
            if isinstance(picked, dict):
                picked = TypeAdapter(Action).validate_python(picked)

            # Apply immediately to help subsequent choices (e.g. pick tradition, then pick spell from it)
            apply_action(picked, hero, is_random=True)
            actions.append(picked)
    elif selected_choices:
        for choice in selected_choices:
            label = (
                f"{choice.type}({choice.name})"
                if hasattr(choice, "name")
                else choice.type
            )
            logger.info("  user selected: %s", label)
        actions.extend(selected_choices)

    return actions


def expand_any_to_choices(
    hero: AncestryHero | list[Action],
    actions: list[Action] | list[Choice],
    choices: list[Choice] | None = None,
) -> tuple[list[Action], list[Choice]]:
    if choices is None:
        choices = actions  # type: ignore[assignment]
        actions = hero  # type: ignore[assignment]
        hero = AncestryHero(
            ancestry_name="", strength=0, dexterity=0, intelligence=0, will=0,
            perception=0, defense=0, health=0, healing_rate=0, size=[0], speed=0,
        )

    assert isinstance(hero, AncestryHero)
    remaining_actions = []
    # Use a temporary list for new choices to keep them at the beginning if needed,
    # but actually we want to preserve the relative order of actions converted to choices.
    new_placeholder_choices = []
    religions_data = _load_json("data_base/paths/novice/cleric_religions.json")

    placeholder_names = ["any", "known", "religious_tradition", "known_tradition"]

    for action in actions:
        # Check if it's a placeholder that should NOT be applied as a hardcoded action
        is_placeholder = False
        if hasattr(action, "name") and action.name in placeholder_names:
            is_placeholder = True
        elif hasattr(action, "target") and action.target in placeholder_names:
            is_placeholder = True

        match action:
            case AddAttribute(name="any", value=value):
                new_placeholder_choices.append(
                    [AddAttribute(name=attr, value=value) for attr in CORE_ATTRIBUTES]
                )
            case AddProfession(name="any"):
                new_placeholder_choices.append(
                    [AddProfession(name=cat) for cat in PROFESSION_CATEGORIES]
                )
            case AddLanguage(name="any", can_write=can_write):
                new_placeholder_choices.append(
                    [
                        AddLanguage(name=lang, can_write=can_write)
                        for lang in ALL_LANGUAGES
                    ]
                )
            case AddSpell(name="any"):
                new_placeholder_choices.append(
                    [
                        AddSpell(name="Zaklęcie 1"),
                        AddSpell(name="Zaklęcie 2"),
                    ]
                )
            case AddReligion(name="any"):
                new_placeholder_choices.append(
                    [AddReligion(name=religion) for religion in religions_data.keys()]
                )
            case AddTradition(name="religious_tradition"):
                # Only add as choice if religion is already set, otherwise wait
                if hero.religion:
                    new_placeholder_choices.append([action])
            case AddSpell(name="known_tradition"):
                # Only add as choice if there are traditions to pick from
                known_trads = [
                    get_tradition_name_from_talent(t.name)
                    for t in hero.talents
                    if get_tradition_name_from_talent(t.name)
                ]
                if known_trads:
                    new_placeholder_choices.append([action])
            case _:
                if not is_placeholder:
                    remaining_actions.append(action)

    # Combine: actions-converted-to-choices first, then existing choices
    all_choices = new_placeholder_choices + choices

    final_choices = []
    for choice_group in all_choices:
        expanded_group = _expand_dynamic_choice_group(hero, choice_group)
        final_choices.append(expanded_group)

    return remaining_actions, final_choices


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


def get_hero(
    ancestry: str, is_random: bool, level: int = 0, path_name: str | None = None
) -> AncestryHero | tuple[AncestryHero, list[Choice]]:
    logger.info(
        "=== get_hero: ancestry=%s, is_random=%s, level=%d, path=%s ===",
        ancestry,
        is_random,
        level,
        path_name,
    )
    hero, actions, choices = build_hero(
        ancestry=ancestry, level=level, path_name=path_name
    )

    add_wealth(hero, actions, choices)
    add_oddity(hero)

    # Expand placeholders to real choices
    actions, choices = expand_any_to_choices(hero, actions, choices)

    if not is_random:
        logger.info(
            "Manual mode: %d actions to apply, %d choice groups for user",
            len(actions),
            len(choices),
        )
        for action in actions:
            apply_action(action, hero, is_random=False)

        if choices:
            logger.info(
                "Returning hero with %d unresolved choice group(s)", len(choices)
            )
            return hero, choices

    if is_random:
        logger.info("Random mode: resolving %d choice group(s)", len(choices))
        # First apply initial actions
        for action in actions:
            apply_action(action, hero, is_random=True)

        # Then resolve and apply choices one by one
        choice_actions = resolve_choices(hero, [], choices, is_random=True)
        actions.extend(choice_actions)

    logger.info(
        "=== Hero complete: %s | STR=%d DEX=%d INT=%d WILL=%d | %d prof(s) | %d lang(s) | wealth=%s ===",
        hero.ancestry_name,
        hero.strength,
        hero.dexterity,
        hero.intelligence,
        hero.will,
        len(hero.professions),
        len(hero.languages),
        hero.wealth[:30] if hero.wealth else "none",
    )
    return hero
