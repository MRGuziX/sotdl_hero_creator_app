from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    expert_path_names: list[str] = Field(default_factory=list)
    master_path_name: str | None = None
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
    ancestry_defense_bonus: int = 0
    defense_from_stats: int = 0
    languages: list[Language] = Field(default_factory=list)
    talents: list[Talent] = Field(default_factory=list)
    spells: list[Spell] = Field(default_factory=list)
    professions: list[str] = Field(default_factory=list)
    backstory: dict = Field(default_factory=dict)
    wealth: str = ""
    money: Money = Field(default_factory=Money)
    oddity: str = ""
    equipment: Equipment = Field(default_factory=Equipment)
    religion: str = ""

    @model_validator(mode="after")
    def _init_defense_tracking(self):
        if self.defense_from_stats == 0 and self.defense > 0:
            self.defense_from_stats = self.defense
        return self
