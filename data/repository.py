"""Repository boundary for JSON game data.

The existing JSON files remain the source of truth. This module centralizes
path resolution, validation, and the one known legacy shape normalization, so
domain code does not need to mutate loaded dictionaries.
"""

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from models.ancestry import AncestryData
from models.path import PathData

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "data_base"


class DataRepositoryError(ValueError):
    """Raised when game data cannot be loaded or validated."""


def load_json(relative_path: str | Path) -> dict[str, Any]:
    requested = Path(relative_path)
    if requested.parts and requested.parts[0] == "data_base":
        requested = Path(*requested.parts[1:])
    path = (DATA_ROOT / requested).resolve()
    if not path.is_relative_to(DATA_ROOT.resolve()):
        raise DataRepositoryError("Game data path is outside the catalog")
    return deepcopy(_read_json(path))


@lru_cache(maxsize=256)
def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as data_file:
            value = json.load(data_file)
    except FileNotFoundError as exc:
        raise DataRepositoryError(f"Game data file not found: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise DataRepositoryError(f"Invalid JSON in game data: {path.name}") from exc
    if not isinstance(value, dict):
        raise DataRepositoryError(f"Expected an object in game data: {path.name}")
    return value


def load_ancestry(ancestry_id: str) -> AncestryData:
    raw = load_json(Path("ancestry") / ancestry_id / f"{ancestry_id}.json")
    try:
        return AncestryData.model_validate(raw)
    except (TypeError, ValueError) as exc:
        raise DataRepositoryError(f"Invalid ancestry data: {ancestry_id}") from exc


def normalize_action(action: dict) -> dict:
    result = dict(action)
    if result.get("type") == "learn_tradition":
        result["type"] = "add_tradition"
    if result.get("type") == "learn_spell":
        result["type"] = "add_spell"
        tradition = result.pop("tradition", None)
        if tradition:
            result["name"] = "known_tradition" if tradition == "any" else f"tradition:{tradition}"
    if result.get("type") == "add_spell" and result.get("description"):
        # The two embedded path spells are explicitly rank 1 in their existing text.
        result["spell"] = {
            "name": result["name"],
            "description": result.pop("description"),
            "level": 1,
            "origin": {"source": "PG"},
        }
    return result


def normalize_benefit(benefit: dict) -> dict:
    normalized = dict(benefit)
    choices = benefit.get("choices", [])
    if choices and isinstance(choices[0], dict):
        choices = [choices]
    normalized["choices"] = [[normalize_action(action) for action in group] for group in choices]
    normalized["actions"] = [normalize_action(action) for action in benefit.get("actions", [])]
    return normalized


def _normalize_path_choices(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(raw)
    benefits = {}
    for level, benefit in raw.get("level_benefits", {}).items():
        benefits[level] = normalize_benefit(benefit)
    normalized["level_benefits"] = benefits
    return normalized


def load_novice_path(path_name: str) -> PathData:
    return load_path("novice", path_name)


def load_path(tier: str, path_name: str) -> PathData:
    raw = load_json(Path("paths") / tier / f"{path_name.lower()}.json")
    try:
        return PathData.model_validate(_normalize_path_choices(raw))
    except (TypeError, ValueError) as exc:
        raise DataRepositoryError(f"Invalid {tier} path data: {path_name}") from exc
