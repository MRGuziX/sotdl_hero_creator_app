from pydantic import BaseModel, ConfigDict

from models.equipment import Equipment, Money
from models.language import Language
from models.talent import Talent
from models.spell import Spell


class AncestryHero(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    ancestry_name: str
    ancestry_id: str = "human"
    level: int = 0
    path_name: str | None = None
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
    spells: list[Spell] = []
    professions: list[str] = []
    backstory: dict = {}
    wealth: str = ""
    money: Money = Money()
    oddity: str = ""
    equipment: Equipment = Equipment()
    religion: str = ""
