"""
NaviStudo Backend - Model 2 (Recommendation Ranking) Schemas.

Defines the input/output contracts for the recommendation ranking model.
The actual field structure will be finalized by Oumnia.
"""

from typing import Any
from pydantic import BaseModel, Field


class RecommendationOption(BaseModel):
    """A single academic option (branch or major) that can be recommended."""

    id: str = Field(description="Unique identifier for this option.")
    name: str = Field(description="Display name of the option.")
    description: str | None = Field(
        default=None, description="Optional description of the option."
    )
    # Additional fields from knowledge base (eligibility criteria, etc.)
    # will be added as needed. Using extra='allow' for flexibility.
    model_config = {"extra": "allow"}


class ModelTwoInput(BaseModel):
    """Input to Model 2: combined student profile + extracted info + filtered options."""

    # Student's structured profile (excluding free-text answers)
    student_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="Student's structured academic profile from Firebase. "
        "Fields: school_year, current_branch, grades, wilaya, etc. (TBD).",
    )

    # Model 1's extracted output
    model_one_output: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured information extracted from free-text answers by Model 1. "
        "Schema defined in model_one_schema.ModelOneOutput.",
    )

    # Filtered knowledge-base options relevant to this student
    eligible_options: list[RecommendationOption] = Field(
        default_factory=list,
        description="Academic options (branches/majors) that pass eligibility filtering. "
        "Model 2 will rank these.",
    )

    # Recommendation type context
    recommendation_type: str = Field(
        description="Type of recommendation: 'secondary_branch' (year 1) or 'university_major' (year 3)."
    )


class RankedRecommendation(BaseModel):
    """A single ranked recommendation with reasoning."""

    option_id: str = Field(description="ID of the recommended option (must exist in eligible_options).")
    rank: int = Field(ge=1, description="Rank position (1 = top recommendation).")
    score: float | None = Field(
        default=None, description="Optional confidence/relevance score (0.0-1.0)."
    )
    reasoning: str = Field(description="Human-readable explanation for this recommendation.")
    # Additional fields from Model 2 output (metadata, etc.)
    model_config = {"extra": "allow"}


class ModelTwoOutput(BaseModel):
    """Output from Model 2: ranked academic recommendations with reasons."""

    recommendations: list[RankedRecommendation] = Field(
        default_factory=list,
        description="Ranked list of recommendations. Must only contain option_ids from eligible_options.",
    )

    # Optional metadata about the ranking process
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (model used, processing time, etc.).",
    )

    success: bool = Field(
        default=True, description="Whether the ranking completed successfully."
    )

    error: str | None = Field(
        default=None, description="Error message if ranking failed."
    )