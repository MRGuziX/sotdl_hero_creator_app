"""Hero-building orchestration boundary retained for compatibility."""

from models.base_hero import AncestryHero
from utils.utils import build_hero as _build_hero


def build_hero(
    ancestry: str,
    level: int = 0,
    path_name: str | None = None,
) -> tuple[AncestryHero, list, list]:
    return _build_hero(
        ancestry,
        level=level, path_name=path_name
    )