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


class PersonaState(BaseModel):
    """Dynamic cognitive state of a persona during a simulation run."""

    model_config = ConfigDict(extra="forbid")

    remaining_patience: float = Field(default=1.0, ge=0.0, le=1.0,
                                      description="Fraction of patience remaining (1.0 = full, 0.0 = exhausted).")
    current_motivation: float = Field(default=1.0, ge=0.0, le=1.0,
                                      description="Current drive to complete the task (1.0 = high, 0.0 = none).")
    confusion_level: float = Field(default=0.0, ge=0.0, le=1.0,
                                   description="Accumulated cognitive confusion (0.0 = clear, 1.0 = overwhelmed).")
    execution_history: list[dict] = Field(default_factory=list,
                                          description="Ordered list of actions taken so far in this run.")
