"""Progression boundary for ancestry and path benefits."""

from models.action import Action
from models.base_hero import AncestryHero
from utils.utils import build_hero


def benefits_for(
    ancestry: str, level: int = 0, path_name: str | None = None
) -> tuple[AncestryHero, list[Action], list[list[Action]]]:
    """Return the current compatibility builder's initial progression output."""
    hero, actions, choices = build_hero(ancestry, level=level, path_name=path_name)
    return hero, actions, choices