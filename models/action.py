from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AddAttribute(BaseModel):
    type: Literal["add_attribute"] = "add_attribute"
    name: str
    value: int | float | str


class AddProfession(BaseModel):
    type: Literal["add_profession"] = "add_profession"
    name: str


class AddLanguage(BaseModel):
    type: Literal["add_language"] = "add_language"
    name: str
    can_write: bool = False


class AddTalent(BaseModel):
    type: Literal["add_talent"] = "add_talent"
    name: str
    description: str | None = None
    upgrade: str | None = None


class AddSpell(BaseModel):
    type: Literal["add_spell"] = "add_spell"
    name: str = "any"


class AddItem(BaseModel):
    type: Literal["add_item"] = "add_item"
    name: str
    damage: str | None = None
    grip: str | None = None
    properties: str | None = None
    price: str | None = None
    availability: str | None = None
    item_type: str | None = None


class AddTradition(BaseModel):
    type: Literal["add_tradition"] = "add_tradition"
    name: str = "any"


class AddReligion(BaseModel):
    type: Literal["add_religion"] = "add_religion"
    name: str = "any"


class UpdateLanguage(BaseModel):
    type: Literal["update_language"] = "update_language"
    name: str
    can_speak: bool = True
    can_write: bool = True


class GrantLiteracy(BaseModel):
    type: Literal["grant_literacy"] = "grant_literacy"
    target: str


Action = Annotated[
    AddAttribute
    | AddProfession
    | AddLanguage
    | AddItem
    | GrantLiteracy
    | AddTalent
    | AddSpell
    | AddTradition
    | AddReligion
    | UpdateLanguage,
    Field(discriminator="type"),
]

Choice = list[Action]


class LevelBenefit(BaseModel):
    actions: list[Action] = Field(default_factory=list)
    choices: list[Choice] = Field(default_factory=list)
