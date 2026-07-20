from pydantic import BaseModel
from models.action import LevelBenefit

class PathData(BaseModel):
    path_name: str
    path_type: str
    level_benefits: dict[int, LevelBenefit]
