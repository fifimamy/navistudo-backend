"""
NaviStudo Backend - Model 1 (Free-text Extraction) Schemas.

Defines the input/output contracts for the free-text analysis model.
The actual field structure will be finalized by Oumnia.
"""

from typing import Any
from pydantic import BaseModel, Field


class ModelOneInput(BaseModel):
    """Input to Model 1: student's free-text answers with context."""

    # Mapping of question_id -> free-text answer
    free_text_answers: dict[str, str] = Field(
        default_factory=dict,
        description="Student's free-text responses keyed by question identifier.",
    )

    # Context that helps the model understand the questions
    question_context: dict[str, str] = Field(
        default_factory=dict,
        description="Optional context for each question (e.g., question text, domain).",
    )

    # Student's school year for context (1, 2, or 3)
    school_year: int = Field(
        ge=1, le=3, description="Student's current school year (1, 2, or 3)."
    )

    # Current branch if applicable (for year 2/3 students)
    current_branch: str | None = Field(
        default=None, description="Student's current branch (e.g., 'sciences', 'maths', 'lettres')."
    )


class ModelOneOutput(BaseModel):
    """Output from Model 1: structured information extracted from free text.

    The exact fields will be determined by Oumnia based on the prompt design.
    This is a placeholder structure that will be replaced.
    """

    # Extracted structured information - keys and types TBD
    extracted_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured information extracted from free-text answers. "
        "Schema to be defined by Oumnia.",
    )

    # Optional confidence scores or metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (confidence scores, processing info, etc.).",
    )

    # Flag indicating if extraction was successful
    success: bool = Field(
        default=True, description="Whether the extraction completed successfully."
    )

    # Error message if extraction failed
    error: str | None = Field(
        default=None, description="Error message if extraction failed."
    )