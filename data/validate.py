"""Run `python -m data.validate` to check models and catalog references."""

from data.repository import DATA_ROOT, load_ancestry, load_json, load_path
from models.action import (
    AddAttribute,
    AddLanguage,
    AddProfession,
    AddReligion,
    AddSpell,
    AddTradition,
)
from models.spell import Spell
from utils.utils import (
    ALL_LANGUAGES,
    CORE_ATTRIBUTES,
    SECONDARY_ATTRIBUTES,
    PROFESSION_CATEGORIES,
    TRADITION_FILE_MAP,
)


def validate_catalog() -> None:
    spell_names = set()
    for filename in TRADITION_FILE_MAP.values():
        for rank, spells in load_json(f"spells/{filename}").items():
            if not rank.startswith("level_"):
                continue
            for raw in spells:
                spell = Spell.model_validate(raw)
                assert spell.level == int(rank.removeprefix("level_")), (
                    f"{filename}: inconsistent spell rank"
                )
                assert (spell.origin or {}).get("source", "PG") in {"PG", "SWD"}
                assert spell.description, f"{filename}: missing spell description"
                spell_names.add(spell.name)
    religions = load_json("paths/novice/cleric_religions.json")
    assert all(
        tradition in TRADITION_FILE_MAP for names in religions.values() for tradition in names
    )
    professions = load_json("professions/profession_tables.json")
    assert all(category in professions for category in PROFESSION_CATEGORIES)

    definitions = [
        load_ancestry(path.parent.name)
        for path in DATA_ROOT.glob("ancestry/*/*.json")
        if path.stem == path.parent.name
    ]
    for tier in ("novice", "expert", "master"):
        for path in (DATA_ROOT / "paths" / tier).glob("*.json"):
            if path.stem == "cleric_religions":
                continue
            definition = load_path(tier, path.stem)
            assert definition.path_type == tier, str(path)
            assert (
                set(definition.level_benefits)
                <= {"novice": {1, 2, 5, 8}, "expert": {3, 6, 9}, "master": {7, 10}}[tier]
            ), str(path)
            definitions.append(definition)
    for definition in definitions:
        actions = list(getattr(definition, "actions", []))
        groups = list(getattr(definition, "choices", []))
        for benefit in definition.level_benefits.values():
            actions.extend(benefit.actions)
            groups.extend(benefit.choices)
        actions.extend(action for group in groups for action in group)
        for action in actions:
            if isinstance(action, AddAttribute):
                assert action.name in CORE_ATTRIBUTES + SECONDARY_ATTRIBUTES + ["any"], action
            elif isinstance(action, AddProfession):
                assert action.name in PROFESSION_CATEGORIES + ["any"], action
            elif isinstance(action, AddLanguage):
                assert action.name in ALL_LANGUAGES + ["any"], action
            elif isinstance(action, AddReligion):
                assert action.name == "any" or action.name in religions, action
            elif isinstance(action, AddTradition):
                assert action.name in TRADITION_FILE_MAP or action.name in {
                    "any",
                    "religious_tradition",
                }, action
            elif isinstance(action, AddSpell):
                if action.spell:
                    assert action.name == action.spell.name and action.spell.description, action
                elif action.name.startswith(("tradition:", "tradition_rank0:")):
                    assert action.name.split(":", 1)[1] in TRADITION_FILE_MAP, action
                else:
                    assert action.name in spell_names or action.name in {
                        "any",
                        "known_tradition",
                    }, action


if __name__ == "__main__":
    validate_catalog()
    print("Game catalog validation passed")
