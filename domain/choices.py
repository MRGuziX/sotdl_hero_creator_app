"""Choice expansion and resolution compatibility boundary."""

from models.action import Action
from models.base_hero import AncestryHero
from utils.utils import expand_any_to_choices as _expand_any_to_choices
from utils.utils import resolve_choices as _resolve_choices


def expand_choices(
    hero: AncestryHero,
    actions: list[Action],
    choices: list[list[Action]],
) -> tuple[list[Action], list[list[Action]]]:
    return _expand_any_to_choices(hero, actions, choices)


def resolve_choices(
    hero: AncestryHero,
    actions: list[Action],
    choices: list[list[Action]],
    is_random: bool = True,
) -> list[Action]:
    return _resolve_choices(hero, actions, choices, is_random=is_random)