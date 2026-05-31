from pydantic import BaseModel, ConfigDict, Field


class PersonaProfile(BaseModel):
    """Demographic and cognitive profile used to simulate a target user."""

    model_config = ConfigDict(extra="forbid")

    name: str
    age: int = Field(ge=0)
    tech_savviness: int = Field(ge=1, le=5)
    attention_span_seconds: int = Field(ge=1)
    motivation_level: int = Field(ge=1, le=5)
    cognitive_biases: list[str] = Field(default_factory=list)
