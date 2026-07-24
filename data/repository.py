"""Repository boundary for JSON game data.

The existing JSON files remain the source of truth. This module centralizes
path resolution, validation, and the one known legacy shape normalization, so
domain code does not need to mutate loaded dictionaries.
"""

import json
from pathlib import Path
from typing import Any

from models.ancestry import AncestryData
from models.path import PathData

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "data_base"


class DataRepositoryError(ValueError):
    """Raised when game data cannot be loaded or validated."""


def load_json(relative_path: str | Path) -> dict[str, Any]:
    path = DATA_ROOT / Path(relative_path)
    try:
        with path.open(encoding="utf-8") as data_file:
            value = json.load(data_file)
    except FileNotFoundError as exc:
        raise DataRepositoryError(f"Game data file not found: {relative_path}") from exc
    except json.JSONDecodeError as exc:
        raise DataRepositoryError(f"Invalid JSON in game data: {relative_path}") from exc
    if not isinstance(value, dict):
        raise DataRepositoryError(f"Expected an object in game data: {relative_path}")
    return value


def load_ancestry(ancestry_id: str) -> AncestryData:
    raw = load_json(Path("ancestry") / ancestry_id / f"{ancestry_id}.json")
    try:
        return AncestryData.model_validate(raw)
    except (TypeError, ValueError) as exc:
        raise DataRepositoryError(f"Invalid ancestry data: {ancestry_id}") from exc


def _normalize_path_choices(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(raw)
    benefits = {}
    for level, benefit in raw.get("level_benefits", {}).items():
        benefit_copy = dict(benefit)
        choices = benefit_copy.get("choices", [])
        if choices and isinstance(choices[0], dict):
            benefit_copy["choices"] = [choices]
        benefits[level] = benefit_copy
    normalized["level_benefits"] = benefits
    return normalized


def load_novice_path(path_name: str) -> PathData:
    raw = load_json(Path("paths") / "novice" / f"{path_name.lower()}.json")
    try:
        return PathData.model_validate(_normalize_path_choices(raw))
    except (TypeError, ValueError) as exc:
        raise DataRepositoryError(f"Invalid novice path data: {path_name}") from exc