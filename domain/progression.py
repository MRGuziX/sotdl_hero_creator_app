"""Progression boundary for ancestry and path benefits."""

from models.action import Action
from models.ancestry import AncestryData
from models.base_hero import AncestryHero
from utils.utils import _collect_path_level_benefits, _load_json, _resolve_paths, build_hero


def benefits_for(
    ancestry: str, level: int = 0, path_name: str | None = None
) -> tuple[AncestryHero, list[Action], list[list[Action]]]:
    """Return the current compatibility builder's initial progression output."""
    hero, actions, choices = build_hero(ancestry, level=level, path_name=path_name)
    return hero, actions, choices


def benefits_between(
    ancestry: str,
    paths: dict | None,
    from_level: int,
    to_level: int,
) -> tuple[list[Action], list[list[Action]]]:
    """Return only the actions/choice groups gained moving from `from_level`
    (exclusive) up to `to_level` (inclusive).

    `paths` is the `{"novice": ..., "expert": [...], "master": ...}`
    selection contract: it resolves Expert path files (levels 3-6-9) and
    Master/second-Expert path files (levels 7-10) alongside the novice path,
    the same way `build_hero` does for the cumulative case.

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

    if to_level >= 1:
        resolved_paths = _resolve_paths(paths, None)
        for absolute_level, benefit in _collect_path_level_benefits(resolved_paths):
            if from_level < absolute_level <= to_level:
                actions.extend(benefit.actions)
                choices.extend(benefit.choices)

    return actions, choices