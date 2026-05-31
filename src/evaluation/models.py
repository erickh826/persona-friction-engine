from typing import Literal

from pydantic import BaseModel, Field


class FrictionPoint(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    recommendation: str


class StepEvaluationResult(BaseModel):
    visual_complexity_score: int = Field(..., ge=1, le=100)
    interaction_friction_score: int = Field(..., ge=1, le=100)
    cognitive_alignment_score: int = Field(..., ge=1, le=100)
    composite_cls: int = Field(..., ge=1, le=100)
    identified_friction_points: list[FrictionPoint] = Field(default_factory=list)
