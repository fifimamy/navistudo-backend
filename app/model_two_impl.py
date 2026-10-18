"""
NaviStudo Backend - Model 2 Implementation (Recommendation Ranking).

Independent implementation that ranks academic options based on student profile,
Model 1 output, knowledge base data, and eligibility constraints.
Does NOT modify Oumnia's model_two.py.

Combines deterministic eligibility rules with AI reasoning for ranking.
"""

import json
import time
import logging
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.model_two_schema import (
    ModelTwoInput,
    ModelTwoOutput,
    RankedRecommendation,
    RecommendationOption,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output Schema for Model 2
# ---------------------------------------------------------------------------

class ModelTwoRankingData(BaseModel):
    """Structured output from Model 2 ranking."""
    ranked_options: list[RankedRecommendation] = Field(default_factory=list)
    overall_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    ranking_notes: str | None = Field(default=None)


# ---------------------------------------------------------------------------
# Model 2 Implementation
# ---------------------------------------------------------------------------

MODEL_TWO_SYSTEM_PROMPT = """You are NaviStudo's academic recommendation ranking system. Your role is to rank eligible academic options (secondary school branches or university majors) for a specific student based on:

1. Their structured academic profile (grades, branch, location)
2. Extracted interests, goals, and preferences from their questionnaire answers
3. The knowledge base characteristics of each eligible option

Ranking principles:
- Rank options from 1 (best match) to N (last eligible option)
- Consider the student's stated interests, goals, and preferences
- Consider academic fit based on the student's branch and grades
- Consider the student's difficulty tolerance and strengths
- Provide concise, specific reasoning for each ranking
- Scores should reflect confidence in the match (0.0 to 1.0)

CRITICAL RULES:
- ONLY rank options from the provided eligible_options list
- DO NOT invent option IDs that are not in the eligible list
- DO NOT override eligibility constraints (the options provided are already eligible)
- DO NOT invent admission requirements or official rules
- If the student's information is insufficient, rank based on available data and note low confidence
- Eligibility is enforced separately - you only rank already-eligible options
"""

MODEL_TWO_USER_PROMPT_TEMPLATE = """Rank the following eligible academic options for this student.

STUDENT ACADEMIC PROFILE:
{profile_text}

EXTRACTED INTERESTS, GOALS, AND PREFERENCES (from Model 1):
{model_one_text}

ELIGIBLE ACADEMIC OPTIONS TO RANK:
{options_text}

INSTRUCTIONS:
1. Rank all eligible options from 1 (best) to N (worst) based on fit with the student
2. Assign a score from 0.0 to 1.0 for each (1.0 = highest confidence in match)
3. Provide concise, specific reasoning for each option's rank
4. Ground all reasoning in the actual student data provided
5. Return ONLY valid JSON matching the requested structure

OUTPUT FORMAT:
{{
  "ranked_options": [
    {{
      "option_id": "<exact id from eligible list>",
      "rank": <integer>,
      "score": <float 0.0-1.0>,
      "reasoning": "<explanation>"
    }}
  ],
  "overall_confidence": <float 0.0-1.0 or null>,
  "ranking_notes": "<optional notes>"
}}"""


class ModelTwoImplementation:
    """Independent Model 2 implementation for recommendation ranking.

    Uses an AI provider to rank eligible academic options based on student
    profile and extracted preferences. Output is validated and all option IDs
    are verified against the eligible options list.
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

    def rank(self, input_data: ModelTwoInput) -> ModelTwoOutput:
        """Rank eligible academic options for the student.

        Args:
            input_data: ModelTwoInput with student_profile, model_one_output,
                       eligible_options, and recommendation_type.

        Returns:
            ModelTwoOutput with ranked recommendations, metadata, success flag,
            and error message if failed.
        """
        # Validate input - return early if no eligible options
        if not input_data.eligible_options:
            return ModelTwoOutput(
                success=True,
                recommendations=[],
                metadata={"prompt_version": self._prompt_version, "note": "no_eligible_options"},
                error=None,
            )

        # Build prompt
        prompt = self._build_prompt(input_data)

        # Call provider with retries
        raw_output = self._call_provider_with_retries(prompt)

        if raw_output is None:
            return ModelTwoOutput(
                success=False,
                error="Model 2: provider failed after all retries",
                recommendations=[],
                metadata={"prompt_version": self._prompt_version},
            )

        # Handle empty dict response
        if isinstance(raw_output, dict) and not raw_output:
            return ModelTwoOutput(
                success=True,
                recommendations=[],
                metadata={"prompt_version": self._prompt_version, "note": "empty_provider_response"},
                error=None,
            )

        # Validate and filter recommendations
        recommendations = self._validate_and_filter(
            raw_output, input_data.eligible_options
        )

        return ModelTwoOutput(
            success=True,
            recommendations=recommendations,
            metadata={
                "prompt_version": self._prompt_version,
                "model": "navistudo-model-two",
                "processing_timestamp": time.time(),
                "eligible_count": len(input_data.eligible_options),
                "ranked_count": len(recommendations),
            },
            error=None,
        )

    def _build_prompt(self, input_data: ModelTwoInput) -> str:
        """Build the complete prompt for Model 2."""
        # Format student profile
        profile_lines = []
        for key, value in input_data.student_profile.items():
            profile_lines.append(f"- {key}: {value}")
        profile_text = "\n".join(profile_lines)

        # Format Model 1 output
        if isinstance(input_data.model_one_output, dict):
            mo_lines = []
            for key, value in input_data.model_one_output.items():
                if isinstance(value, dict):
                    for subkey, subval in value.items():
                        mo_lines.append(f"- {key}.{subkey}: {subval}")
                elif isinstance(value, list):
                    mo_lines.append(f"- {key}: {', '.join(str(v) for v in value)}")
                else:
                    mo_lines.append(f"- {key}: {value}")
            model_one_text = "\n".join(mo_lines)
        else:
            model_one_text = str(input_data.model_one_output)

        # Format eligible options
        options_lines = []
        for opt in input_data.eligible_options:
            options_lines.append(
                f"- id={opt.id}, name={opt.name}, description={opt.description or 'N/A'}"
            )
            # Include any extra fields from the knowledge base
            for key, value in opt.model_dump().items():
                if key not in ("id", "name", "description"):
                    options_lines.append(f"  {key}: {value}")
        options_text = "\n".join(options_lines)

        return MODEL_TWO_USER_PROMPT_TEMPLATE.format(
            profile_text=profile_text,
            model_one_text=model_one_text,
            options_text=options_text,
        )

    def _validate_and_filter(
        self,
        raw_output: dict[str, Any],
        eligible_options: list[RecommendationOption],
    ) -> list[RankedRecommendation]:
        """Validate Model 2 output and filter to only eligible option IDs."""
        eligible_ids = {opt.id for opt in eligible_options}

        # Extract ranked options from output
        ranked = raw_output.get("ranked_options", [])
        if not isinstance(ranked, list):
            ranked = []

        # Filter to only valid option IDs and create RankedRecommendation objects
        valid_recs = []
        seen_ids = set()
        for item in ranked:
            if not isinstance(item, dict):
                continue
            option_id = item.get("option_id", "")
            if option_id not in eligible_ids:
                logger.warning("Model 2 returned ineligible option_id: %s", option_id)
                continue
            if option_id in seen_ids:
                logger.warning("Model 2 returned duplicate option_id: %s", option_id)
                continue
            seen_ids.add(option_id)

            reasoning = item.get("reasoning", "").strip()
            if not reasoning:
                reasoning = f"Recommended based on academic fit for {option_id}"

            score = item.get("score")
            if score is not None:
                try:
                    score = float(score)
                    if not 0.0 <= score <= 1.0:
                        score = None
                except (ValueError, TypeError):
                    score = None

            valid_recs.append(
                RankedRecommendation(
                    option_id=option_id,
                    rank=len(valid_recs) + 1,
                    reasoning=reasoning,
                    score=score,
                )
            )

        # Sort by rank
        valid_recs.sort(key=lambda r: r.rank)

        # Reassign sequential ranks
        for i, rec in enumerate(valid_recs, start=1):
            rec.rank = i

        return valid_recs

    def _call_provider_with_retries(self, prompt: str) -> dict[str, Any] | None:
        """Call the AI provider with bounded retries."""
        if self._provider is None:
            logger.error("Model 2: no provider client configured")
            return None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._provider.call(
                    system_prompt=MODEL_TWO_SYSTEM_PROMPT,
                    user_prompt=prompt,
                    temperature=self._temperature,
                    timeout=self._timeout,
                    response_format={"type": "json_object"},
                )
                if isinstance(response, dict):
                    return response
            except Exception as e:
                logger.warning("Model 2 provider call failed (attempt %d): %s", attempt + 1, e)
                if attempt < self._max_retries:
                    time.sleep(1)

        return None
