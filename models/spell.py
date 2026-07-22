from pydantic import BaseModel, Field


class Spell(BaseModel):
    name: str
    description: str
    level: int = 0
    tags: list[str] = Field(default_factory=list)
    target: str | None = None
    area: str | None = None
    duration: str | None = None
    critical_success: str | None = None


class Tradition(BaseModel):
    name: str
    spells: dict[int, list[Spell]]
