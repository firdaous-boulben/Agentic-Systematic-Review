from typing import Dict
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    topic: str = Field(..., min_length=3)


class ScreeningDecision(BaseModel):
    approved: bool
    uncertain_decisions: Dict[str, str] = Field(default_factory=dict)