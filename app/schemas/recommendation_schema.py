"""
NaviStudo Backend - Recommendation API Schemas.

Defines request/response schemas for the recommendations endpoints.
These are the external API contracts (separate from internal model schemas).
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Request to create a new recommendation analysis."""

    # No body needed - student is identified by Firebase ID token
    # Future: could add optional parameters like "force_refresh"
    pass


class RecommendationOptionResponse(BaseModel):
    """A single recommendation option in the API response."""

    id: str = Field(description="Unique identifier.")
    name: str = Field(description="Display name.")
    description: str | None = Field(default=None)
    rank: int = Field(ge=1, description="Rank position.")
    score: float | None = Field(default=None, description="Confidence score (0.0-1.0).")
    reasoning: str = Field(description="Explanation for this recommendation.")
    # Allow extra fields from knowledge base
    model_config = {"extra": "allow"}


class RecommendationResponse(BaseModel):
    """Response for a completed recommendation analysis."""

    analysis_id: str = Field(description="Unique ID for this analysis.")
    student_uid: str = Field(description="Firebase UID of the student.")
    recommendation_type: str = Field(
        description="Type: 'secondary_branch' (year 1) or 'university_major' (year 3)."
    )
    recommendations: list[RecommendationOptionResponse] = Field(
        default_factory=list, description="Ranked recommendations."
    )
    created_at: datetime = Field(description="When the analysis was created.")
    model_one_metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata from Model 1."
    )
    model_two_metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata from Model 2."
    )


class RecommendationErrorResponse(BaseModel):
    """Error response for recommendation endpoints."""

    error: str = Field(description="Error code.")
    message: str = Field(description="Human-readable error message.")
    details: dict[str, Any] | None = Field(default=None)