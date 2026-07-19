from pydantic import BaseModel


class Language(BaseModel):
    name: str
    can_speak: bool = True
    can_write: bool = False
