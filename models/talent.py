from pydantic import BaseModel


class Talent(BaseModel):
    name: str
    description: str
    level: int = 0
