from pydantic import BaseModel, ConfigDict

from models.equipment import Equipment, Money
from models.language import Language
from models.talent import Talent


class AncestryHero(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    ancestry_name: str
    level: int = 0
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
    talents: list[Talent] = []
    professions: list[str] = []
    backstory: dict = {}
    wealth: str = ""
    money: Money = Money()
    oddity: str = ""
    equipment: Equipment = Equipment()
