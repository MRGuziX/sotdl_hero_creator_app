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
    LevelBenefit,
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
NOVICE_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "novice"
EXPERT_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "expert"
MASTER_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "master"

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
    "Tradycja Powietrza": "air_tradition.json",
    "Tradycja Przemian": "alteration_tradition.json",
    "Tradycja Arkanów": "arcana_tradition.json",
    "Tradycja Bitewna": "battlemagic_tradition.json",
    "Tradycja Chaosu": "chaos_tradition.json",
    "Tradycja Przywołania": "conjuration_tradition.json",
    "Tradycja Klątw": "curse_tradition.json",
    "Tradycja Zniszczenia": "destruction_tradition.json",
    "Tradycja Jasnowidzenia": "divination_tradition.json",
    "Tradycja Ziemi": "earth_tradition.json",
    "Tradycja Uroków": "enchantment_tradition.json",
    "Tradycja Ognia": "fire_tradition.json",
    "Tradycja Zakazana": "forbidden_tradition.json",
    "Tradycja Niebiańska": "heaven_tradition.json",
    "Tradycja Iluzji": "illusion_tradition.json",
    "Tradycja Życia": "life_tradition.json",
    "Tradycja Natury": "nature_tradition.json",
    "Tradycja Nekromancji": "necromancy_tradition.json",
    "Tradycja Pierwotna": "primal_tradition.json",
    "Tradycja Ochrony": "protection_tradition.json",
    "Tradycja Run": "rune_tradition.json",
    "Tradycja Cieni": "shadow_tradition.json",
    "Tradycja Pieśni": "song_tradition.json",
    "Tradycja Burzy": "storm_tradition.json",
    "Tradycja Technomancji": "technomancy_tradition.json",
    "Tradycja Teleportacji": "teleportation_tradition.json",
    "Tradycja Teurgi": "theurgy_tradition.json",
    "Tradycja Czasu": "time_tradition.json",
    "Tradycja Transformacji": "transformation_tradition.json",
    "Tradycja Wody": "water_tradition.json",
}


def roll_dice(num_dice: int, sides: int) -> int:
    if not isinstance(num_dice, int) or not isinstance(sides, int):
        raise TypeError("Number of dice and number of sides must be integers.")
    if num_dice < 1:
        raise ValueError("Number of dice must be greater than 0.")
    if sides < 1:
        raise ValueError("Number of sides must be greater than 0.")

    return sum(random.randint(1, sides) for _ in range(num_dice))


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


load_json = _load_json


def _normalize_path_action(action: dict) -> dict:
    """Translate the legacy Master-path action aliases (`learn_tradition`/
    `learn_spell`) onto the existing `add_tradition`/`add_spell` vocabulary,
    so every path tier validates against the same `Action` union without
    growing new action types just for a naming difference in the data.
    """
    if not isinstance(action, dict):
        return action

    action_type = action.get("type")
    if action_type == "learn_tradition":
        return {"type": "add_tradition", "name": action.get("name", "any")}
    if action_type == "learn_spell":
        tradition = action.get("tradition")
        if tradition == "any":
            return {"type": "add_spell", "name": "known_tradition"}
        if tradition:
            return {"type": "add_spell", "name": f"tradition:{tradition}"}
        return {"type": "add_spell", "name": action.get("name", "any")}
    return action


def _normalize_level_benefit_json(benefit: dict) -> dict:
    """Normalize a raw `level_benefits` entry: wrap legacy flat choice lists
    into a single nested group (matching `PathData`'s `list[Choice]` shape)
    and normalize every action within it/`actions` via `_normalize_path_action`.
    """
    normalized = dict(benefit)
    choices = normalized.get("choices", [])
    if choices and isinstance(choices[0], dict):
        choices = [choices]
    normalized["choices"] = [
        [_normalize_path_action(action) for action in group] for group in choices
    ]
    normalized["actions"] = [
        _normalize_path_action(action) for action in normalized.get("actions", [])
    ]
    return normalized


def _load_path_data(tier: str, path_name: str) -> PathData | None:
    """Load and validate a single novice/expert/master path file, or return
    `None` (with a warning) when it does not exist, mirroring the previous
    novice-only lookup used by `build_hero`/`benefits_between`.
    """
    path_file = f"data_base/paths/{tier}/{path_name.lower()}.json"
    if not os.path.exists(PROJECT_ROOT / path_file):
        logger.warning("Path file %s not found", path_file)
        return None

    path_data_json = dict(_load_json(path_file))
    path_data_json["level_benefits"] = {
        level: _normalize_level_benefit_json(benefit)
        for level, benefit in path_data_json.get("level_benefits", {}).items()
    }
    return PathData.model_validate(path_data_json)


def _resolve_paths(paths: dict | None, path_name: str | None) -> dict:
    """Normalize the caller-supplied path selection into the canonical
    `{"novice": ..., "expert": [...], "master": ...}` shape. `paths` (the
    new multi-tier contract) always wins; the legacy single `path_name`
    keyword is kept as a novice-only shorthand for backward compatibility.
    """
    if paths:
        return {
            "novice": paths.get("novice"),
            "expert": list(paths.get("expert") or []),
            "master": paths.get("master"),
        }
    return {"novice": path_name, "expert": [], "master": None}


def _expert_level_offset(slot_index: int) -> dict[int, int]:
    """Map an Expert path file's own level keys (3/6/9) onto absolute hero
    levels. The first Expert path (chosen at level 3) uses its levels as-is.
    A second Expert path - chosen at the level 7 crossroads instead of a
    Master path - arrives later, so its 3rd/6th tier benefits are shifted to
    land on hero level 7/10; its 9th tier has no home within a level 10
    career and is intentionally dropped.
    """
    if slot_index == 1:
        return {3: 7, 6: 10}
    return {}


def _collect_path_level_benefits(paths: dict) -> list[tuple[int, LevelBenefit]]:
    """Return `(absolute_hero_level, benefit)` pairs gathered across every
    configured path tier (novice, up to two Expert paths, and Master),
    resolving each tier's own file so `build_hero`/`benefits_between` can
    filter them by level exactly like the ancestry's own level_benefits.
    """
    resolved: list[tuple[int, LevelBenefit]] = []

    novice_name = paths.get("novice")
    if novice_name:
        data = _load_path_data("novice", novice_name)
        if data:
            resolved.extend((int(lvl), benefit) for lvl, benefit in data.level_benefits.items())

    for slot_index, expert_name in enumerate((paths.get("expert") or [])[:2]):
        if not expert_name:
            continue
        data = _load_path_data("expert", expert_name)
        if not data:
            continue
        offset_map = _expert_level_offset(slot_index)
        for lvl, benefit in data.level_benefits.items():
            lvl = int(lvl)
            if slot_index == 0:
                resolved.append((lvl, benefit))
            elif lvl in offset_map:
                resolved.append((offset_map[lvl], benefit))

    master_name = paths.get("master")
    if master_name:
        data = _load_path_data("master", master_name)
        if data:
            resolved.extend((int(lvl), benefit) for lvl, benefit in data.level_benefits.items())

    return resolved


def is_duplicate_expert_path(paths: dict, tier: str, path_id: str) -> bool:
    """Return whether choosing `path_id` for `tier` would repeat an Expert
    path already chosen earlier. At the level 7 crossroads a player may add
    a *second* Expert path instead of a Master one, but never the same
    Expert path twice.
    """
    if tier != "expert" or not path_id:
        return False
    existing = [name.lower() for name in (paths.get("expert") or []) if name]
    return path_id.lower() in existing


def benefits_for_new_path_pick(
    paths_before: dict, tier: str, path_name: str, level: int
) -> tuple[list[Action], list[list[Action]]]:
    """Return only the actions/choice groups granted by freshly choosing
    `path_name` for `tier`, resolved at the exact hero `level` where that
    pick first unlocks (Novice level 1, Expert level 3, Master or second
    Expert level 7).

    `paths_before` is the tier selection *before* this pick is recorded; it
    is used to tell a first Expert path (chosen at level 3) apart from a
    second one (chosen at the level 7 crossroads instead of a Master path),
    since a second Expert path's own level 3/6 keys must be shifted to land
    on hero level 7/10 (see `_expert_level_offset`).
    """
    if tier == "expert":
        slot_index = len(paths_before.get("expert") or [])
        data = _load_path_data("expert", path_name)
        if not data:
            return [], []
        if slot_index == 0:
            own_level = level
        else:
            offset_map = _expert_level_offset(slot_index)
            own_level = next(
                (own for own, mapped in offset_map.items() if mapped == level), None
            )
    else:
        data = _load_path_data(tier, path_name)
        own_level = level

    if not data or own_level is None:
        return [], []
    benefit = data.level_benefits.get(own_level)
    if not benefit:
        return [], []
    return list(benefit.actions), list(benefit.choices)


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
    paths: dict | None = None,
) -> tuple[AncestryHero, list[Action], list[Choice]]:
    """Build a hero's baseline actions/choices for `level`.

    `path_name` is the legacy novice-only path keyword, still accepted for
    backward compatibility. `paths` is the newer `{"novice": ..., "expert":
    [...], "master": ...}` contract that also resolves Expert (levels 3-6-9)
    and Master/second-Expert (levels 7-10) benefits; when present it takes
    priority over `path_name`.
    """
    resolved_paths = _resolve_paths(paths, path_name)
    data = _load_json(f"data_base/ancestry/{ancestry}/{ancestry}.json")
    ancestry_data = AncestryData.model_validate(data)

    logger.info(
        "Building hero: ancestry=%s, level=%d, paths=%s", ancestry, level, resolved_paths
    )

    hero = AncestryHero(
        ancestry_name=ancestry_data.general.ancestry_name,
        ancestry_id=ancestry,
        level=level,
        path_name=resolved_paths.get("novice"),
        expert_path_names=resolved_paths.get("expert") or [],
        master_path_name=resolved_paths.get("master"),
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

    if level >= 1:
        for absolute_level, benefit in _collect_path_level_benefits(resolved_paths):
            if absolute_level <= level:
                logger.info("  adding path level %d benefits", absolute_level)
                actions.extend(benefit.actions)
                choices.extend(benefit.choices)

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
    # These names are choice placeholders, not spell records. They must not
    # become visible fallback cards when a manual choice is submitted early.
    if (
        name in {"any", "known_tradition"}
        or name.startswith("tradition:")
        or name.startswith("tradition_rank0:")
    ):
        return

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
                            book_description=s_data.get("book_description"),
                            card_description=s_data.get("card_description"),
                            level=s_data.get("level", 0),
                            tags=s_data.get("tags", []),
                            target=s_data.get("target"),
                            area=s_data.get("area"),
                            duration=s_data.get("duration"),
                            critical_success=s_data.get("critical_success"),
                            requirements=s_data.get("requirements"),
                            sacrifice=s_data.get("sacrifice"),
                            permanent=s_data.get("permanent"),
                            table=s_data.get("table"),
                            origin=s_data.get("origin"),
                        )
                    )
                    return

    # Fallback
    hero.spells.append(Spell(name=name, description="Nowe zaklęcie", level=0))


def add_tradition(name: str, hero: AncestryHero):
    hero.talents.append(
        Talent(name=name, description="Dostęp do zaklęć tej tradycji", level=0)
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
    if talent_name in TRADITION_FILE_MAP:
        return talent_name
    return None


def get_spells_for_tradition(tradition_name: str, power_level: int) -> list[str]:
    filename = TRADITION_FILE_MAP.get(tradition_name)
    if not filename:
        logger.warning("No file mapping for tradition: %s", tradition_name)
        return []

    path = f"data_base/spells/{filename}"
    if not os.path.exists(PROJECT_ROOT / path):
        logger.warning("Spell file not found: %s", path)
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
            case AddTradition(name="any"):
                available = [
                    t for t in sorted(TRADITION_FILE_MAP)
                    if t not in known_traditions
                ]
                if available:
                    expanded_group.extend(
                        AddTradition(name=t) for t in available
                    )
                else:
                    expanded_group.append(action)
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
            case AddSpell(name=spell_name) if spell_name.startswith("tradition_rank0:"):
                tradition_name = spell_name[len("tradition_rank0:"):]
                known_spells = {spell.name for spell in hero.spells}
                spells = sorted(
                    spell
                    for spell in get_spells_for_tradition(tradition_name, 0)
                    if spell not in known_spells
                )
                if spells:
                    expanded_group.extend(AddSpell(name=s) for s in spells)
                else:
                    expanded_group.append(action)
            case AddSpell(name=spell_name) if spell_name.startswith("tradition:"):
                tradition_name = spell_name[len("tradition:"):]
                known_spells = {spell.name for spell in hero.spells}
                spells = sorted(
                    spell
                    for spell in get_spells_for_tradition(
                        tradition_name, hero.power
                    )
                    if spell not in known_spells
                )
                if spells:
                    expanded_group.extend(AddSpell(name=s) for s in spells)
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

            apply_action(picked, hero, is_random=True)
            actions.append(picked)

            if isinstance(picked, AddTradition) and picked.name not in ("any", "religious_tradition"):
                rank0 = get_spells_for_tradition(picked.name, power_level=0)
                known = {s.name for s in hero.spells}
                available = [s for s in rank0 if s not in known]
                has_sztuczki = any(t.name == "Sztuczki" for t in hero.talents)
                num_picks = min(2 if has_sztuczki else 1, len(available))
                for spell_name in random.sample(available, num_picks) if available else []:
                    spell_action = AddSpell(name=spell_name)
                    apply_action(spell_action, hero, is_random=True)
                    actions.append(spell_action)
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
    """Expand placeholder actions (``name="any"``, etc.) into concrete choice groups.

    Supports two calling conventions:
      - ``expand_any_to_choices(hero, actions, choices)`` — uses *hero* to filter
        already-known languages/traditions.
      - ``expand_any_to_choices(actions, choices)`` — *choices* is omitted; the first
        two positional args are re-interpreted as *actions* and *choices*, and a
        zeroed-out dummy hero is used.
    """
    if choices is None:
        if not isinstance(hero, list):
            raise TypeError(
                "When choices is omitted, first arg must be list[Action], "
                f"got {type(hero).__name__}"
            )
        choices = actions  # type: ignore[assignment]
        actions = hero  # type: ignore[assignment]
        hero = AncestryHero(
            ancestry_name="", strength=0, dexterity=0, intelligence=0, will=0,
            perception=0, defense=0, health=0, healing_rate=0, size=[0], speed=0,
        )

    if not isinstance(hero, AncestryHero):
        raise TypeError(f"Expected AncestryHero, got {type(hero).__name__}")
    remaining_actions = []
    # Use a temporary list for new choices to keep them at the beginning if needed,
    # but actually we want to preserve the relative order of actions converted to choices.
    new_placeholder_choices = []
    deferred_placeholder_choices = []
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
            case AddTradition(name="any"):
                known_traditions = {
                    tradition
                    for talent in hero.talents
                    if (tradition := get_tradition_name_from_talent(talent.name))
                }
                available_traditions = [
                    tradition
                    for tradition in TRADITION_FILE_MAP
                    if tradition not in known_traditions
                ]
                if available_traditions:
                    new_placeholder_choices.append(
                        [
                            AddTradition(name=tradition)
                            for tradition in sorted(set(available_traditions))
                        ]
                    )
            case AddReligion(name="any"):
                new_placeholder_choices.append(
                    [AddReligion(name=religion) for religion in religions_data.keys()]
                )
            case AddTradition(name="religious_tradition"):
                # Keep this placeholder until the religion choice has been
                # applied. It must be expanded against the mutated hero later.
                if hero.religion:
                    new_placeholder_choices.append([action])
                else:
                    deferred_placeholder_choices.append([action])
            case AddSpell(name="known_tradition"):
                known_trads = [
                    get_tradition_name_from_talent(t.name)
                    for t in hero.talents
                    if get_tradition_name_from_talent(t.name)
                ]
                if known_trads:
                    new_placeholder_choices.append([action])
            case AddSpell(name=sn) if sn.startswith("tradition:"):
                new_placeholder_choices.append([action])
            case _:
                if not is_placeholder:
                    remaining_actions.append(action)

    # Combine: actions-converted-to-choices first, then existing choices
    all_choices = new_placeholder_choices + choices + deferred_placeholder_choices

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


def randomly_pick_paths(target_level: int, existing_paths: dict) -> dict:
    """Fill missing paths randomly based on the target level for Random mode."""
    paths = {
        "novice": existing_paths.get("novice"),
        "expert": list(existing_paths.get("expert") or []),
        "master": existing_paths.get("master"),
    }

    if target_level >= 1 and not paths["novice"]:
        options = [f.stem for f in NOVICE_PATHS_DIR.glob("*.json") if f.name != "cleric_religions.json"]
        if options:
            paths["novice"] = random.choice(options)

    if target_level >= 3 and len(paths["expert"]) < 1:
        options = [f.stem for f in EXPERT_PATHS_DIR.glob("*.json")]
        if options:
            paths["expert"].append(random.choice(options))

    if target_level >= 7:
        if not paths["master"] and len(paths["expert"]) < 2:
            if random.choice(["master", "expert"]) == "master":
                options = [f.stem for f in MASTER_PATHS_DIR.glob("*.json")]
                if options:
                    paths["master"] = random.choice(options)
            else:
                options = [f.stem for f in EXPERT_PATHS_DIR.glob("*.json") if f.stem not in paths["expert"]]
                if options:
                    paths["expert"].append(random.choice(options))

    return paths


def get_hero(
    ancestry: str,
    is_random: bool,
    level: int = 0,
    path_name: str | None = None,
    paths: dict | None = None,
) -> AncestryHero | tuple[AncestryHero, list[Choice]]:
    resolved_paths = _resolve_paths(paths, path_name)
    if is_random:
        resolved_paths = randomly_pick_paths(level, resolved_paths)
    logger.info(
        "=== get_hero: ancestry=%s, is_random=%s, level=%d, paths=%s ===",
        ancestry,
        is_random,
        level,
        resolved_paths,
    )
    hero, actions, choices = build_hero(
        ancestry=ancestry, level=level, paths=resolved_paths
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


def advance_hero(
    hero: AncestryHero,
    ancestry: str,
    path_name: str | None,
    from_level: int,
    to_level: int,
    is_random: bool = False,
    paths: dict | None = None,
) -> list[Choice]:
    """Apply the deterministic actions gained moving from `from_level` to
    `to_level` and return any unresolved choice groups still needed.

    This mirrors the level_benefits handling already used by `build_hero`/
    `get_hero`, but only for the incremental step, so the wizard can advance
    one level at a time instead of flattening the whole target level's
    choices together. Backstory, wealth, and oddity rolls are intentionally
    not repeated here: they are only granted once, at creation time.
    """
    from domain.progression import benefits_between

    resolved_paths = _resolve_paths(paths, path_name)
    logger.info(
        "advance_hero: %s from level %d to %d (paths=%s)",
        ancestry, from_level, to_level, resolved_paths,
    )
    actions, choices = benefits_between(ancestry, resolved_paths, from_level, to_level)
    remaining_actions, expanded_choices = expand_any_to_choices(hero, actions, choices)

    for action in remaining_actions:
        apply_action(action, hero, is_random=is_random)

    if is_random:
        resolve_choices(hero, [], expanded_choices, is_random=True)
        return []

    return expanded_choices
