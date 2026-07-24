"""Progression boundary for ancestry and path benefits."""

import os

from models.action import Action
from models.ancestry import AncestryData
from models.base_hero import AncestryHero
from models.path import PathData
from utils.utils import PROJECT_ROOT, _load_json, build_hero


def benefits_for(
    ancestry: str, level: int = 0, path_name: str | None = None
) -> tuple[AncestryHero, list[Action], list[list[Action]]]:
    """Return the current compatibility builder's initial progression output."""
    hero, actions, choices = build_hero(ancestry, level=level, path_name=path_name)
    return hero, actions, choices


def benefits_between(
    ancestry: str,
    path_name: str | None,
    from_level: int,
    to_level: int,
) -> tuple[list[Action], list[list[Action]]]:
    """Return only the actions/choice groups gained moving from `from_level`
    (exclusive) up to `to_level` (inclusive).

    This lets the wizard advance one level at a time instead of rebuilding
    the whole hero for the target level. Backstory, wealth, and oddity are
    intentionally excluded: those are one-time creation benefits, not tied
    to a specific level_benefits entry.
    """
    data = _load_json(f"data_base/ancestry/{ancestry}/{ancestry}.json")
    ancestry_data = AncestryData.model_validate(data)

    actions: list[Action] = []
    choices: list[list[Action]] = []
    for lvl, benefit in ancestry_data.level_benefits.items():
        if from_level < lvl <= to_level:
            actions.extend(benefit.actions)
            choices.extend(benefit.choices)

    if to_level >= 1 and path_name:
        path_file = f"data_base/paths/novice/{path_name.lower()}.json"
        if os.path.exists(PROJECT_ROOT / path_file):
            path_data_json = _load_json(path_file)
            for benefit in path_data_json.get("level_benefits", {}).values():
                benefit_choices = benefit.get("choices", [])
                if benefit_choices and isinstance(benefit_choices[0], dict):
                    benefit["choices"] = [benefit_choices]
            path_data = PathData.model_validate(path_data_json)
            for lvl, benefit in path_data.level_benefits.items():
                if from_level < int(lvl) <= to_level:
                    actions.extend(benefit.actions)
                    choices.extend(benefit.choices)

    return actions, choices