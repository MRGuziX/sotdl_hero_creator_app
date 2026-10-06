from pydantic import BaseModel
from models.action import LevelBenefit


class PathData(BaseModel):
    path_name: str
    path_type: str
    path_description: str | None = None
    origin: dict | None = None
    level_benefits: dict[int, LevelBenefit]
