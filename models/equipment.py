from typing import Literal

from pydantic import BaseModel, ConfigDict


class Weapon(BaseModel):
    name: str
    damage: str
    grip: str
    properties: str = ""
    price: str = ""
    availability: str = ""
    item_type: Literal["weapon"] = "weapon"


class Armor(BaseModel):
    name: str
    defence: str
    defence_base: str = ""
    defence_bonus: int = 0
    defence_value: int = 0
    special: str = ""
    requirements: str = ""
    item_type: Literal["armor"] = "armor"


class Shield(BaseModel):
    name: str
    damage: str
    grip: str
    properties: str = ""
    defence_bonus: int = 0
    price: str = ""
    availability: str = ""
    requirements: str = ""
    item_type: Literal["shield"] = "shield"


class Money(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    okrawki: int = 0
    miedziaki: int = 0
    srebrniki: int = 0
    zlote_korony: int = 0


class Equipment(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    weapons: list[Weapon] = []
    shields: list[Shield] = []
    armors: list[Armor] = []
    backpack: list[str] = []
