from pydantic import BaseModel


class Spell(BaseModel):
    name: str
    description: str
    level: int = 0


class Tradition(BaseModel):
    name: str
    spells: dict[int, list[Spell]]
