from pydantic import BaseModel

from models.action import Action, Choice


class RollTableEntry(BaseModel):
    roll: list[int]
    description: str
    actions: list[Action] = []
    choices: list[Choice] = []


class ProfessionEntry(BaseModel):
    roll: list[int]
    description: str
    action: Action | None = None


class MoneyRoll(BaseModel):
    type: str
    dice_type: int
    dice_amount: int


class WealthEntry(BaseModel):
    roll: list[int]
    description: str
    backpack: str = ""
    money: MoneyRoll | None = None
    actions: list[Action] = []
    choices: list[Choice] = []
