from pydantic import BaseModel, Field, model_validator


class Spell(BaseModel):
    name: str
    description: str = ""
    book_description: str | None = None
    card_description: str | None = None
    level: int = 0
    tags: list[str] = Field(default_factory=list)
    target: str | None = None
    area: str | None = None
    duration: str | None = None
    critical_success: str | None = None
    requirements: str | None = None
    sacrifice: str | None = None
    permanent: str | None = None
    table: dict | None = None
    origin: dict | None = None

    @model_validator(mode="before")
    @classmethod
    def use_book_description_as_description(cls, values):
        if isinstance(values, dict) and not values.get("description"):
            values = dict(values)
            values["description"] = values.get("book_description") or ""
        return values
