from pydantic import BaseModel, Field


class Plant(BaseModel):
    id: str
    name: str
    planting_start_month: int = Field(ge=1, le=12)
    planting_end_month: int = Field(ge=1, le=12)
    incompatible_with: list[str]


class Warning(BaseModel):
    type: str
    message: str
    plants_involved: list[str]  # list of plant IDs, not names
