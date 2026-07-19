from pydantic import BaseModel

from models.action import Action, Choice
from models.equipment import Equipment, Money
from models.language import Language
from models.spell import Spell
from models.talent import Talent


class GeneralStats(BaseModel):
    ancestry_name: str
    strength: int
    dexterity: int
    intelligence: int
    will: int
    perception: int
    defense: int
    health: int
    healing_rate: int
    size: list[float]
    speed: int
    power: int = 0
    damage: int = 0
    insanity: int = 0
    corruption: int = 0
    languages: list[Language] = []


class AncestryData(BaseModel):
    general: GeneralStats
    backstory: dict = {}
    talents: list[Talent] = []
    professions: list[str] = []
    spells: list[Spell] = []
    wealth: str = ""
    money: Money = Money()
    oddity: str = ""
    equipment: Equipment = Equipment()
    actions: list[Action] = []
    choices: list[Choice] = []
