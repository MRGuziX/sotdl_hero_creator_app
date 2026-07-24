"""Serializable, server-authoritative state for the creation wizard."""

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter

from models.action import Action
from models.base_hero import AncestryHero


CREATION_STATE_VERSION = 1


class CreationStateError(ValueError):
    """Raised when a creation state is missing or incompatible data."""


@dataclass
class CreationState:
    """The authoritative mutable hero and its pending deterministic work."""

    hero: AncestryHero
    pending_choices: list[list[Action]] = field(default_factory=list)
    choice_cursor: int = 0
    creation_inputs: dict[str, Any] = field(default_factory=dict)
    applied_actions: list[Action] = field(default_factory=list)
    roll_results: dict[str, Any] = field(default_factory=dict)
    version: int = CREATION_STATE_VERSION
    state_id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "state_id": self.state_id,
            "creation_inputs": self.creation_inputs,
            "hero": self.hero.model_dump(mode="json"),
            "pending_choices": [
                [action.model_dump(mode="json") for action in group]
                for group in self.pending_choices
            ],
            "choice_cursor": self.choice_cursor,
            "applied_actions": [
                action.model_dump(mode="json") for action in self.applied_actions
            ],
            "roll_results": self.roll_results,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CreationState":
        if not isinstance(data, dict) or data.get("version") != CREATION_STATE_VERSION:
            raise CreationStateError("Unsupported or missing creation state version")
        try:
            action_adapter = TypeAdapter(Action)
            return cls(
                hero=AncestryHero.model_validate(data["hero"]),
                pending_choices=[
                    [action_adapter.validate_python(action) for action in group]
                    for group in data.get("pending_choices", [])
                ],
                choice_cursor=data["choice_cursor"],
                creation_inputs=dict(data.get("creation_inputs", {})),
                applied_actions=[
                    action_adapter.validate_python(action)
                    for action in data.get("applied_actions", [])
                ],
                roll_results=dict(data.get("roll_results", {})),
                version=data["version"],
                state_id=data["state_id"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CreationStateError("Malformed creation state") from exc

    def validate_cursor(self, cursor: int) -> None:
        if not isinstance(cursor, int) or cursor < 0 or cursor != self.choice_cursor:
            raise CreationStateError("Invalid choice cursor")