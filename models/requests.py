"""Validated request envelopes for the creation API."""

from typing import Annotated, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from models.action import Action
from domain.state_token import MAX_TOKEN_LENGTH

PathID = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+$")]
Level = Annotated[int, Field(ge=0, le=10)]
Version = Annotated[int, Field(ge=0)]


class RequestModel(BaseModel):
    model_config = ConfigDict(strict=True)


class PathSelection(RequestModel):
    novice: PathID | None = None
    expert: list[PathID] = Field(default_factory=list, max_length=2)
    master: PathID | None = None

    @model_validator(mode="after")
    def validate_expert_slots(self):
        if len(set(self.expert)) != len(self.expert):
            raise ValueError("Expert paths must be distinct")
        if self.master and len(self.expert) > 1:
            raise ValueError("Choose a Master path or a second Expert path")
        return self


class StartCreation(RequestModel):
    mode: Literal["manual", "random"] = "manual"
    ancestry: Literal["human", "automaton", "goblin", "dwarf", "orc", "changeling", "swd_elf"]
    target_level: Level = 0
    paths: PathSelection = Field(default_factory=PathSelection)
    enabled_sources: list[Literal["PG", "SWD"]] = Field(default_factory=lambda: ["PG"])

    @field_validator("enabled_sources")
    @classmethod
    def require_core_source(cls, sources):
        if "PG" not in sources:
            raise ValueError("PG must be enabled")
        return list(dict.fromkeys(sources))


class CarriedStateRequest(RequestModel):
    state_token: Annotated[str, StringConstraints(min_length=1, max_length=MAX_TOKEN_LENGTH)]


class VersionedRequest(CarriedStateRequest):
    state_version: Version


class ApplyChoices(VersionedRequest):
    selections: list[Action] = Field(
        min_length=1, validation_alias=AliasChoices("selections", "selected_choices")
    )
    choice_cursor: Annotated[int, Field(ge=0)] | None = None


class PickPath(VersionedRequest):
    path_id: PathID = Field(validation_alias=AliasChoices("path_id", "path"))


class PickEquipment(VersionedRequest):
    armors: list[str] = Field(default_factory=list, max_length=1)
    weapons: list[str] = Field(default_factory=list, max_length=5)
    shields: list[str] = Field(default_factory=list, max_length=1)


class Rewind(VersionedRequest):
    target_level: Level
