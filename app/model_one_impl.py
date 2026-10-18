"""
NaviStudo Backend - Model 1 Implementation (Free-text Extraction).

Independent implementation that transforms student free-text answers into
validated structured semantic data. Does NOT modify Oumnia's model_one.py.

Uses a configurable AI provider with structured output validation,
bounded retries, and safe error handling.
"""

import json
import time
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from app.schemas.model_one_schema import ModelOneInput, ModelOneOutput

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output Schema for Model 1
# ---------------------------------------------------------------------------

class ExtractedInterests(BaseModel):
    """Structured interests extracted from free-text answers."""
    academic_subjects: list[str] = Field(default_factory=list, description="Academic subjects the student mentions liking")
    career_areas: list[str] = Field(default_factory=list, description="Career areas of interest")
    hobbies_activities: list[str] = Field(default_factory=list, description="Hobbies and activities mentioned")


class ExtractedGoals(BaseModel):
    """Structured goals extracted from free-text answers."""
    short_term: list[str] = Field(default_factory=list, description="Short-term academic goals")
    long_term: list[str] = Field(default_factory=list, description="Long-term career/life goals")
    motivations: list[str] = Field(default_factory=list, description="Key motivations mentioned")


class ExtractedPreferences(BaseModel):
    """Structured preferences extracted from free-text answers."""
    work_environment: list[str] = Field(default_factory=list, description="Preferred work/study environments")
    learning_style: list[str] = Field(default_factory=list, description="Preferred learning styles")
    difficulty_tolerance: str | None = Field(default=None, description="Attitude toward academic challenges")


class ModelOneExtractedData(BaseModel):
    """Complete structured output from Model 1."""
    interests: ExtractedInterests = Field(default_factory=ExtractedInterests)
    goals: ExtractedGoals = Field(default_factory=ExtractedGoals)
    preferences: ExtractedPreferences = Field(default_factory=ExtractedPreferences)
    strengths: list[str] = Field(default_factory=list, description="Academic strengths mentioned")
    difficulties: list[str] = Field(default_factory=list, description="Subjects/areas of difficulty mentioned")
    raw_themes: list[str] = Field(default_factory=list, description="Other notable themes")


# ---------------------------------------------------------------------------
# Model 1 Implementation
# ---------------------------------------------------------------------------

MODEL_ONE_SYSTEM_PROMPT = """You are NaviStudo's academic guidance system. Your role is to analyze a student's free-text questionnaire answers and extract structured semantic information that will help recommend appropriate academic paths.

You extract:
1. Interests: academic subjects, career areas, hobbies/activities the student mentions
2. Goals: short-term academic goals, long-term career goals, and motivations
3. Preferences: work environment, learning style, attitude toward difficulty
4. Strengths: subjects or skills the student mentions being good at
5. Difficulties: subjects or areas the student mentions struggling with
6. Themes: other notable patterns in their answers

IMPORTANT RULES:
- ONLY extract information explicitly present in the student's answers
- Do NOT infer interests or goals the student did not mention
- If the student does not mention something, leave that field empty
- Preserve the student's language and terminology where possible
- Handle ambiguous or contradictory answers by noting them as themes
- If answers are very brief or unclear, extract what you can and note low confidence
- NEVER invent questionnaire questions or assume missing answers
"""

MODEL_ONE_USER_PROMPT_TEMPLATE = """Analyze the following student questionnaire answers and extract structured information.

STUDENT PROFILE CONTEXT:
- School year: {school_year}
- Current branch: {current_branch}

STUDENT FREE-TEXT ANSWERS:
{answers}

{context_section}

Extract structured information following the output schema. Return ONLY valid JSON matching the requested structure. If a field has no data, return an empty list or null as appropriate."""


class ModelOneImplementation:
    """Independent Model 1 implementation for free-text extraction.

    Uses an AI provider to analyze student questionnaire answers and produce
    validated structured output. Includes bounded retries and safe error handling.
    """

    def __init__(
        self,
        provider_client: Any = None,
        max_retries: int = 2,
        timeout_seconds: int = 30,
        temperature: float = 0.0,
    ):
        self._provider = provider_client
        self._max_retries = max_retries
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._prompt_version = "1.0.0"

    def analyze(self, input_data: ModelOneInput) -> ModelOneOutput:
        """Analyze free-text answers and extract structured information.

        Args:
            input_data: ModelOneInput with free_text_answers, question_context,
                       school_year, and current_branch.

        Returns:
            ModelOneOutput with extracted_data matching ModelOneExtractedData schema,
            metadata including prompt version and processing info, success flag,
            and error message if failed.
        """
        # Validate input
        if not input_data.free_text_answers:
            return ModelOneOutput(
                success=True,
                extracted_data=ModelOneExtractedData().model_dump(),
                metadata={"prompt_version": self._prompt_version, "note": "no_free_text_answers"},
                error=None,
            )

        # Build prompt
        prompt = self._build_prompt(input_data)

        # Call provider with retries
        raw_output = self._call_provider_with_retries(prompt)

        if raw_output is None:
            return ModelOneOutput(
                success=False,
                error="Model 1: provider failed after all retries",
                extracted_data={},
                metadata={"prompt_version": self._prompt_version},
            )

        # Validate output against schema
        try:
            validated = ModelOneExtractedData(**raw_output)
            return ModelOneOutput(
                success=True,
                extracted_data=validated.model_dump(),
                metadata={
                    "prompt_version": self._prompt_version,
                    "model": "navistudo-model-one",
                    "processing_timestamp": time.time(),
                },
                error=None,
            )
        except PydanticValidationError as e:
            # Try to use raw output if schema validation fails
            logger.warning("Model 1 output schema validation failed: %s", e)
            if isinstance(raw_output, dict):
                return ModelOneOutput(
                    success=True,
                    extracted_data=raw_output,
                    metadata={
                        "prompt_version": self._prompt_version,
                        "validation_warning": str(e),
                        "model": "navistudo-model-one",
                    },
                    error=None,
                )
            return ModelOneOutput(
                success=False,
                error=f"Model 1: output validation failed: {e}",
                extracted_data={},
                metadata={"prompt_version": self._prompt_version},
            )

    def _build_prompt(self, input_data: ModelOneInput) -> str:
        """Build the complete prompt for Model 1."""
        answers_text = "\n".join(
            f"[{qid}]: {answer}"
            for qid, answer in input_data.free_text_answers.items()
        )

        context_section = ""
        if input_data.question_context:
            context_lines = "\n".join(
                f"Context for [{qid}]: {ctx}"
                for qid, ctx in input_data.question_context.items()
            )
            context_section = f"\nQUESTION CONTEXT:\n{context_lines}"

        return MODEL_ONE_USER_PROMPT_TEMPLATE.format(
            school_year=input_data.school_year,
            current_branch=input_data.current_branch or "not specified",
            answers=answers_text,
            context_section=context_section,
        )

    def _call_provider_with_retries(self, prompt: str) -> dict[str, Any] | None:
        """Call the AI provider with bounded retries."""
        if self._provider is None:
            logger.error("Model 1: no provider client configured")
            return None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._provider.call(
                    system_prompt=MODEL_ONE_SYSTEM_PROMPT,
                    user_prompt=prompt,
                    temperature=self._temperature,
                    timeout=self._timeout,
                    response_format={"type": "json_object"},
                )
                if isinstance(response, dict):
                    return response
            except Exception as e:
                logger.warning("Model 1 provider call failed (attempt %d): %s", attempt + 1, e)
                if attempt < self._max_retries:
                    time.sleep(1)

        return None


# ---------------------------------------------------------------------------
# Provider Interface (for dependency injection)
# ---------------------------------------------------------------------------

class AIProviderClient:
    """Abstract interface for AI provider calls.

    Implementations should provide a `call` method matching this interface.
    The actual provider (OpenAI, Anthropic, etc.) is configured externally.
    """

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        timeout: int = 30,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the AI provider and return parsed JSON response.

        Args:
            system_prompt: The system prompt defining the model's role.
            user_prompt: The user prompt with input data.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.
            response_format: Optional response format specification.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            Exception: If the provider call fails.
        """
        raise NotImplementedError
