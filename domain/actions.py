"""Action application boundary.

The implementation remains in the compatibility module during the strangler
migration; callers can depend on this focused interface immediately.
"""

from models.action import Action
from models.base_hero import AncestryHero
from utils.utils import apply_action as _apply_action


def apply_action(action: Action, hero: AncestryHero, is_random: bool = False) -> None:
    _apply_action(action, hero, is_random=is_random)