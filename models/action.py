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


class AddItem(BaseModel):
    type: Literal["add_item"] = "add_item"
    name: str
    damage: str | None = None
    grip: str | None = None
    properties: str | None = None
    price: str | None = None
    availability: str | None = None
    item_type: str | None = None


class GrantLiteracy(BaseModel):
    type: Literal["grant_literacy"] = "grant_literacy"
    target: str


Action = Annotated[
    AddAttribute | AddProfession | AddLanguage | AddItem | GrantLiteracy,
    Field(discriminator="type"),
]

Choice = list[Action]
