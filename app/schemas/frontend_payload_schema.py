"""
NaviStudo Backend - Frontend Questionnaire Payload Schema.

Defines the external request contract for the questionnaire payload submitted
by the frontend to ``POST /api/v1/recommendations``.

This schema is intentionally permissive (``extra="allow"``): unknown frontend
fields are preserved rather than rejected, so a valid payload is never silently
dropped.

NOTE: The exact frontend contract is being confirmed with the frontend team.
See ``docs/PAYLOAD_NOTES.md`` for the current assumptions and the mapping
decisions that still require confirmation.
"""

from typing import Any

from pydantic import BaseModel, Field


class SubjectPerformanceEntry(BaseModel):
    """A single subject score range reported by the frontend."""

    subject_id: str = Field(
        ...,
        min_length=1,
        description="Frontend subject identifier (e.g. 'mathematics').",
    )
    min_score: float | None = Field(
        default=None,
        description="Lower bound of the reported score range (0-20).",
    )
    max_score: float | None = Field(
        default=None,
        description="Upper bound of the reported score range (0-20).",
    )
    model_config = {"extra": "allow"}


class StudentProfileSection(BaseModel):
    """The ``student_profile`` section of the frontend payload."""

    current_stage_id: str | None = Field(
        default=None,
        description="Frontend stage identifier mapped to school_year (see adapter).",
    )
    wilaya_code: str | None = Field(
        default=None,
        description="Algerian wilaya code, e.g. '16'.",
    )
    wilaya: str | None = Field(
        default=None,
        description="Wilaya display name (kept for audit).",
    )
    school_name: str | None = Field(default=None)
    full_name: str | None = Field(default=None)
    subject_performance: list[SubjectPerformanceEntry] = Field(
        default_factory=list,
        description="Reported subject score ranges.",
    )
    model_config = {"extra": "allow"}


class FrontendPayload(BaseModel):
    """The complete frontend questionnaire payload."""

    student_profile: StudentProfileSection = Field(
        ...,
        description="Required student profile section.",
    )
    interests: dict[str, Any] | None = Field(
        default=None,
        description="Interest fields (academic, career, activity, topics, motivations).",
    )
    future_direction: dict[str, Any] | None = Field(
        default=None,
        description="Goal and direction fields.",
    )
    problem_preferences: dict[str, Any] | None = Field(
        default=None,
        description="Problem-solving preference fields.",
    )
    model_config = {"extra": "allow"}


class FrontendPayloadError(ValueError):
    """Raised when a frontend payload is malformed or cannot be mapped."""

    pass
