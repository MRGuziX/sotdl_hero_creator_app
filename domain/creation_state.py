"""Serializable, server-authoritative state for the creation wizard."""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter

from models.action import Action
from models.base_hero import AncestryHero


CREATION_STATE_VERSION = 4


class CreationStateError(ValueError):
    """Raised when a creation state is missing or incompatible data."""


@dataclass
class CreationState:
    """The authoritative mutable hero and its pending deterministic work."""

    hero: AncestryHero
    level_choices: list[list[Action]] = field(default_factory=list)
    choice_cursor: int = 0
    total_choices_in_level: int = 0
    creation_inputs: dict[str, Any] = field(default_factory=dict)
    applied_actions: list[tuple[int, Action]] = field(default_factory=list)
    selections: dict[int, list[int]] = field(default_factory=dict)
    mode: str = "manual"
    current_level: int = 0
    completed_steps: list[int] = field(default_factory=list)
    invalidated_levels: list[int] = field(default_factory=list)
    equipment_confirmed_levels: list[int] = field(default_factory=list)
    equipment_picks: dict[str, Any] = field(default_factory=dict)
    enabled_sources: list[str] = field(default_factory=lambda: ["PG"])
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    state_version: int = 0
    version: int = CREATION_STATE_VERSION
    state_id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self, *, include_history: bool = True) -> dict[str, Any]:
        result = {
            "version": self.version,
            "state_id": self.state_id,
            "creation_inputs": self.creation_inputs,
            "hero": self.hero.model_dump(mode="json"),
            "level_choices": [
                [action.model_dump(mode="json") for action in group] for group in self.level_choices
            ],
            "choice_cursor": self.choice_cursor,
            "total_choices_in_level": self.total_choices_in_level,
            "applied_actions": [
                [lvl, action.model_dump(mode="json")] for lvl, action in self.applied_actions
            ],
            "selections": {str(k): v for k, v in self.selections.items()},
            "mode": self.mode,
            "current_level": self.current_level,
            "completed_steps": self.completed_steps,
            "invalidated_levels": self.invalidated_levels,
            "equipment_confirmed_levels": self.equipment_confirmed_levels,
            "equipment_picks": self.equipment_picks,
            "enabled_sources": self.enabled_sources,
            "state_version": self.state_version,
        }
        if include_history:
            result["checkpoints"] = deepcopy(self.checkpoints)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CreationState":
        if not isinstance(data, dict) or data.get("version") != CREATION_STATE_VERSION:
            raise CreationStateError("Unsupported or missing creation state version")
        data = deepcopy(data)
        try:
            action_adapter = TypeAdapter(Action)
            return cls(
                hero=AncestryHero.model_validate(data["hero"]),
                level_choices=[
                    [action_adapter.validate_python(action) for action in group]
                    for group in data.get("level_choices", [])
                ],
                choice_cursor=data["choice_cursor"],
                total_choices_in_level=data.get("total_choices_in_level", 0),
                creation_inputs=dict(data.get("creation_inputs", {})),
                applied_actions=[
                    (lvl, action_adapter.validate_python(action))
                    for lvl, action in data.get("applied_actions", [])
                ],
                selections={int(k): v for k, v in data.get("selections", {}).items()},
                version=data["version"],
                state_id=data["state_id"],
                mode=data.get("mode", "manual"),
                current_level=data.get("current_level", 0),
                completed_steps=list(data.get("completed_steps", [])),
                invalidated_levels=list(data.get("invalidated_levels", [])),
                equipment_confirmed_levels=list(data.get("equipment_confirmed_levels", [])),
                equipment_picks=dict(data.get("equipment_picks", {})),
                enabled_sources=list(data.get("enabled_sources", ["PG"])),
                checkpoints=deepcopy(data.get("checkpoints", [])),
                state_version=data.get("state_version", 0),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CreationStateError("Malformed creation state") from exc

    def checkpoint(self, kind: str) -> None:
        self.checkpoints.append(
            {
                "kind": kind,
                "level": self.current_level,
                "state": deepcopy(self.to_dict(include_history=False)),
            }
        )

    def restore_checkpoint(self, kind: str, level: int) -> None:
        matches = [
            index
            for index, item in enumerate(self.checkpoints)
            if item["kind"] == kind and item["level"] == level
        ]
        if not matches:
            raise CreationStateError("No saved checkpoint for this step")
        index = matches[0] if kind == "level" else matches[-1]
        history = deepcopy(self.checkpoints[: index + (kind == "level")])
        version = self.state_version
        restored = self.from_dict(deepcopy(self.checkpoints[index]["state"]))
        self.__dict__.update(restored.__dict__)
        self.checkpoints = history
        self.state_version = version

    def validate_cursor(self, cursor: int) -> None:
        if not isinstance(cursor, int) or cursor < 0 or cursor != self.choice_cursor:
            raise CreationStateError("Invalid choice cursor")

    def touch(self) -> None:
        """Advance the optimistic-concurrency version after a mutation."""
        self.state_version += 1

    @property
    def pending_choices(self) -> list[list[Action]]:
        """Return the current active choice group(s) for the wizard."""
        return self.level_choices[self.choice_cursor :]

    @property
    def required_complete(self) -> bool:
        """Return whether every required choice for the current step is resolved."""
        return self.choice_cursor >= self.total_choices_in_level

    @property
    def step_complete(self) -> bool:
        return (
            self.required_complete
            and not self.pending_choices
            and not self.awaiting_path_pick()
            and not self.awaiting_equipment_pick()
        )

    @property
    def can_finalize(self) -> bool:
        """Allow export at any level after every requirement is resolved."""
        return self.step_complete

    @property
    def can_advance(self) -> bool:
        """Return whether the crossroads screen may request advancing one
        more level via `POST /api/creations/<id>/advance`."""
        return self.mode == "manual" and self.step_complete and self.current_level < 10

    def awaiting_path_pick(self) -> str | None:
        """Return which path tier still needs to be chosen before the
        wizard may progress, or `None` when nothing is pending.

        Path picks unlock at level 1 (Novice), level 3 (Expert), and level 7
        (Master, or a second Expert path instead). They must be recorded
        before their level_benefits are resolved, so the crossroads screen
        routes into `<path-picker>` at those levels instead of advancing.

        Random mode resolves every path/level in one shot up front, so it
        never has anything pending here, regardless of which path tiers
        were left unset.
        """
        if self.mode != "manual" or not self.required_complete:
            return None
        paths = self.creation_inputs.get("paths") or {}
        level = self.current_level
        if level >= 1 and not paths.get("novice"):
            return "novice"
        if level >= 3 and not (paths.get("expert") or []):
            return "expert"
        if level >= 7 and not paths.get("master") and len(paths.get("expert") or []) < 2:
            return "master"
        return None

    def awaiting_equipment_pick(self) -> bool:
        if self.mode != "manual":
            return False
        if not self.required_complete:
            return False
        if self.awaiting_path_pick():
            return False
        if self.current_level not in (3, 5, 7):
            return False
        return self.current_level not in self.equipment_confirmed_levels

    def public_dict(self) -> dict[str, Any]:
        """Return the frontend contract without exposing implementation details."""
        paths = self.creation_inputs.get("paths") or {"novice": None, "expert": [], "master": None}
        return {
            "state_id": self.state_id,
            "state_version": self.state_version,
            "mode": self.mode,
            "current_level": self.current_level,
            "enabled_sources": list(self.enabled_sources),
            "completed_steps": self.completed_steps,
            "invalidated_levels": self.invalidated_levels,
            "hero": self.hero.model_dump(mode="json"),
            # Chosen path per tier, so the frontend can display/exclude
            # already-picked Expert paths without re-deriving server logic.
            "paths": {
                "novice": paths.get("novice"),
                "expert": list(paths.get("expert") or []),
                "master": paths.get("master"),
            },
            "level_choices": [
                [action.model_dump(mode="json") for action in group] for group in self.level_choices
            ],
            "pending_choices": [
                [action.model_dump(mode="json") for action in group]
                for group in self.level_choices[self.choice_cursor : self.choice_cursor + 1]
            ],
            "selections": self.selections.get(self.current_level, []),
            "choice_cursor": self.choice_cursor,
            "total_choices_in_level": self.total_choices_in_level,
            "required_complete": self.required_complete,
            "can_finalize": self.can_finalize,
            "can_advance": self.can_advance,
            "awaiting_path_pick": self.awaiting_path_pick(),
            "awaiting_equipment_pick": self.awaiting_equipment_pick(),
        }
