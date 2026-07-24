"""Backstory boundary for the existing ancestry-specific rules."""

from models.base_hero import AncestryHero
from utils.utils import build_hero


def build_with_backstory(
    ancestry: str, level: int = 0, path_name: str | None = None
) -> tuple[AncestryHero, list, list]:
    """Preserve the existing backstory rolls behind a focused interface."""
    return build_hero(
        ancestry, level=level, path_name=path_name
    )