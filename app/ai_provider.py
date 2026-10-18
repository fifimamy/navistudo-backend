"""
NaviStudo Backend - Real AI Provider Integration.

Provides real AI model integration with environment-based configuration,
request timeouts, structured-output validation, and safe error handling.

Supports two modes:
- Development/test mode: Uses deterministic fake model clients (default, no credentials needed)
- Real AI mode: Calls the configured AI provider (OpenAI, Anthropic, etc.)
"""

import os
import json
import time
from typing import Any, Optional

from app.schemas.model_one_schema import ModelOneInput, ModelOneOutput
from app.schemas.model_two_schema import ModelTwoInput, ModelTwoOutput, RankedRecommendation


# ---------------------------------------------------------------------------
# AI Provider Configuration
# ---------------------------------------------------------------------------

class AIProviderConfig:
    """Configuration for AI provider settings from environment variables."""

    # Model 1 configuration
    model_one_temperature: float = float(os.environ.get("AI_MODEL_ONE_TEMPERATURE", "0.0"))
    model_one_timeout_seconds: int = int(os.environ.get("AI_MODEL_ONE_TIMEOUT", "30"))
    model_one_max_retries: int = int(os.environ.get("AI_MODEL_ONE_MAX_RETRIES", "2"))

    # Model 2 configuration
    model_two_temperature: float = float(os.environ.get("AI_MODEL_TWO_TEMPERATURE", "0.0"))
    model_two_timeout_seconds: int = int(os.environ.get("AI_MODEL_TWO_TIMEOUT", "30"))
    model_two_max_retries: int = int(os.environ.get("AI_MODEL_TWO_MAX_RETRIES", "2"))

    # Provider selection
    model_one_provider: str = os.environ.get("AI_MODEL_ONE_PROVIDER", "openai").lower()
    model_two_provider: str = os.environ.get("AI_MODEL_TWO_PROVIDER", "openai").lower()

    # API keys (read from env at runtime to avoid secrets in source)
    @property
    def model_one_api_key(self) -> str | None:
        return os.environ.get("AI_MODEL_ONE_API_KEY") or os.environ.get("OPENAI_API_KEY")

    @property
    def model_two_api_key(self) -> str | None:
        return os.environ.get("AI_MODEL_TWO_API_KEY") or os.environ.get("OPENAI_API_KEY")

    # Enable real AI mode
    @property
    def real_model_one_enabled(self) -> bool:
        return os.environ.get("AI_REAL_MODE", "0") in ("1", "true", "True") and self.model_one_api_key is not None

    @property
    def real_model_two_enabled(self) -> bool:
        return os.environ.get("AI_REAL_MODE", "0") in ("1", "true", "True") and self.model_two_api_key is not None

    # Development mode flag
    @property
    def development_mode(self) -> bool:
        return os.environ.get("AI_DEVELOPMENT_MODE", "1") in ("1", "true", "True")


ai_config = AIProviderConfig()


def _import_fake_model_one():
    """Import fake Model 1 client lazily to avoid circular imports with tests module."""
    from tests.fakes import FakeModelOneClient
    return FakeModelOneClient


def _import_fake_model_two():
    """Import fake Model 2 client lazily to avoid circular imports with tests module."""
    from tests.fakes import FakeModelTwoClient
    return FakeModelTwoClient


def _is_development_mode() -> bool:
    """Check development mode at call time to avoid circular imports with tests module."""
    return (ai_config.development_mode and not ai_config.real_model_one_enabled)


# ---------------------------------------------------------------------------
# Real Model 1 Client (OpenAI-compatible)
# ---------------------------------------------------------------------------

class RealModelOneClient:
    """Real Model 1 client using OpenAI or compatible provider.

    Wraps the free-text extraction prompt with proper error handling,
    timeouts, and retries. Output is validated against the ModelOneOutput
    schema.

    Does NOT modify Oumnia's model_one.py — this is a separate provider
    that can be used when AI_REAL_MODE=1 and OPENAI_API_KEY is set.
    """

    def __init__(self):
        self.timeout = ai_config.model_one_timeout_seconds
        self.max_retries = ai_config.model_one_max_retries
        self.temperature = ai_config.model_one_temperature
        self._api_key = ai_config.model_one_api_key

    def _call_provider(self, prompt: str) -> dict[str, Any]:
        """Call the AI provider with retries and timeout."""
        import openai  # type: ignore

        openai.api_key = self._api_key
        openai.api_type = "openai"
        openai.api_version = "2020-12-01"

        for attempt in range(self.max_retries + 1):
            try:
                messages = [
                    {"role": "system", "content": "You are NaviStudo's Model 1, extracting structured academic information from student questionnaire answers."},
                    {"role": "user", "content": prompt},
                ]

                response = openai.ChatCompletion.create(
                    model=os.environ.get("AI_MODEL_ONE_NAME", "gpt-4o-mini"),
                    messages=messages,
                    temperature=self.temperature,
                    max_completion_tokens=1000,
                    timeout=self.timeout,
                )

                result = response.choices[0].message.content
                if result:
                    return json.loads(result)
                return {}

            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(1)
                    continue
                raise RuntimeError(f"AI provider call failed: {e}") from e

        return {}

    def analyze(self, input_data: ModelOneInput) -> ModelOneOutput:
        """Analyze free-text answers and extract structured information.

        Args:
            input_data: ModelOneInput with free_text_answers, question_context,
                       school_year, and current_branch.

        Returns:
            ModelOneOutput with extracted_data, metadata, success flag,
            and error message if failed.
        """
        # Development mode: use fake client
        if _is_development_mode():
            FakeModelOneClient = _import_fake_model_one()
            fake = FakeModelOneClient(scenario="ok")
            return fake.analyze(input_data)

        # Real AI mode
        if not self._api_key:
            return ModelOneOutput(
                success=False,
                error="Model 1: no API key configured. Set OPENAI_API_KEY or AI_MODEL_ONE_API_KEY.",
            )

        # Construct prompt from student's free-text answers
        prompt_parts = [
            "You are extracting structured academic information from a student's questionnaire answers. "
            "Focus on: interests, goals, relevant subjects, skills, and preferences that would help "
            "recommend academic options (secondary branches or university majors).",
        ]

        # Add free-text answers
        answers = input_data.free_text_answers
        if answers:
            answer_lines = []
            for qid, answer in answers.items():
                answer_lines.append(f"Question {qid}: {answer}")
            prompt_parts.append("\n".join(answer_lines))

        # Add context
        if input_data.question_context:
            ctx_lines = []
            for qid, ctx in input_data.question_context.items():
                ctx_lines.append(f"Question {qid} context: {ctx}")
            prompt_parts.append("\n".join(ctx_lines))

        # Add student profile context
        prompt_parts.append(
            f"\nStudent school year: {input_data.school_year}. "
            f"Current branch: {input_data.current_branch or 'not specified'}."
        )

        prompt = "\n".join(prompt_parts) + "\n\n"
        prompt += json.dumps({
            "extracted_data": {"type": "object", "properties": {}},
            "metadata": {"type": "object", "properties": {}},
            "success": True,
        }, indent=2)

        try:
            raw = self._call_provider(prompt)
            if raw and isinstance(raw, dict):
                extracted_data = raw.get("extracted_data", raw)
                metadata = raw.get("metadata", {})
                success = raw.get("success", True)
                error = raw.get("error", None)
            else:
                extracted_data = raw if raw else {}
                metadata = {}
                success = True
                error = None

            return ModelOneOutput(
                success=success,
                extracted_data=extracted_data,
                metadata=metadata,
                error=error,
            )

        except Exception as e:
            return ModelOneOutput(
                success=False,
                error=f"Model 1 provider error: {str(e)}",
                extracted_data={},
                metadata={},
            )


# ---------------------------------------------------------------------------
# Real Model 2 Client (OpenAI-compatible)
# ---------------------------------------------------------------------------

class RealModelTwoClient:
    """Real Model 2 client using OpenAI or compatible provider.

    Wraps the recommendation ranking prompt with proper error handling,
    timeouts, and retries. Output is validated against the ModelTwoOutput
    schema. CRITICAL: Every recommended option_id MUST exist in the
    eligible_options list — the orchestrator validates this after this
    method returns, but we also perform basic validation here.

    Does NOT modify Oumnia's model_two.py — this is a separate provider
    that can be used when AI_REAL_MODE=1 and OPENAI_API_KEY is set.
    """

    def __init__(self):
        self.timeout = ai_config.model_two_timeout_seconds
        self.max_retries = ai_config.model_two_max_retries
        self.temperature = ai_config.model_two_temperature
        self._api_key = ai_config.model_two_api_key

    def _call_provider(self, prompt: str) -> dict[str, Any]:
        """Call the AI provider with retries and timeout."""
        import openai  # type: ignore

        openai.api_key = self._api_key
        openai.api_type = "openai"
        openai.api_version = "2020-12-01"

        for attempt in range(self.max_retries + 1):
            try:
                messages = [
                    {"role": "system", "content": "You are NaviStudo's Model 2, ranking academic options for a student based on their profile and eligibility. "
                    "Return exactly the recommended options with ranks, scores, and reasoning. "
                    "CRITICAL: Every option_id must correspond to one of the eligible_options provided in the prompt context."},
                    {"role": "user", "content": prompt},
                ]

                response = openai.ChatCompletion.create(
                    model=os.environ.get("AI_MODEL_TWO_NAME", "gpt-4o-mini"),
                    messages=messages,
                    temperature=self.temperature,
                    max_completion_tokens=1500,
                    timeout=self.timeout,
                )

                result = response.choices[0].message.content
                if result:
                    return json.loads(result)
                return {}

            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(1)
                    continue
                raise RuntimeError(f"AI provider call failed: {e}") from e

        return {}

    def rank(self, input_data: ModelTwoInput) -> ModelTwoOutput:
        """Rank eligible academic options for the student.

        Args:
            input_data: ModelTwoInput with student_profile, model_one_output,
                       eligible_options, and recommendation_type.

        Returns:
            ModelTwoOutput with ranked recommendations, metadata, success flag,
            and error message if failed.
        """
        # Development mode: use fake client
        if _is_development_mode():
            from tests.fakes import FakeModelTwoClient as _FakeMTwo
            fake = _FakeMTwo(scenario="valid")
            return fake.rank(input_data)

        # Real AI mode
        if not self._api_key:
            return ModelTwoOutput(
                success=False,
                error="Model 2: no API key configured. Set OPENAI_API_KEY or AI_MODEL_TWO_API_KEY.",
                recommendations=[],
                metadata={},
            )

        # Build the prompt for the AI
        options_desc = []
        for i, opt in enumerate(input_data.eligible_options, start=1):
            options_desc.append(
                f"Option {i}: id='{opt.id}', name='{opt.name}', "
                f"description='{opt.description or ''}'"
            )

        options_text = "\n".join(options_desc)

        # Build student profile summary
        profile = input_data.student_profile
        profile_summary = (
            f"School year: {profile.get('school_year', 'unknown')}. "
        )
        if profile.get('current_branch'):
            profile_summary += f"Current branch: {profile['current_branch']}. "
        if profile.get('wilaya'):
            profile_summary += f"Wilaya: {profile['wilaya']}. "
        if profile.get('grades'):
            profile_summary += f"Grades: {profile['grades']}. "

        # Build model one output summary
        mo_output = input_data.model_one_output
        mo_summary = ""
        if mo_output:
            if isinstance(mo_output, dict):
                interests = mo_output.get("interests", [])
                goals = mo_output.get("goals", [])
                if interests:
                    mo_summary += f"Extracted interests: {interests}. "
                if goals:
                    mo_summary += f"Extracted goals: {goals}. "

        # Construct the prompt
        prompt = f"""You are NaviStudo's Model 2, ranking academic options for a student.

STUDENT PROFILE:
{profile_summary}
{mo_summary}

ELIGIBLE ACADEMIC OPTIONS (the student is eligible for these):
{options_text}

INSTRUCTIONS:
- Rank the eligible options from 1 (best match) to N (last eligible option).
- Provide a score between 0.0 and 1.0 for each recommendation (1.0 = highest confidence).
- Provide a concise reasoning string explaining why each option is a good fit.
- Return a JSON array of objects with: option_id, rank, score (optional), reasoning.
- DO NOT invent option IDs that are not in the eligible list above.
- DO NOT return fewer recommendations than there are eligible options unless genuinely no options qualify.

RESPONSE FORMAT:
[
  {{
    "option_id": "<exact id from eligible list>",
    "rank": <integer 1-N>,
    "score": <float 0.0-1.0 or omitted>,
    "reasoning": "<short text explanation>"
  }}
]"""

        try:
            raw = self._call_provider(prompt)

            # Parse the response
            if raw and isinstance(raw, dict):
                recs = raw.get("recommendations", raw.get("recommendations", []))
                if isinstance(recs, list):
                    recommendations = recs
                else:
                    recommendations = []
            elif raw and isinstance(raw, list):
                recommendations = raw
            else:
                recommendations = []

            # Basic validation: ensure all option_ids are from eligible list
            eligible_id_set = {opt.id for opt in input_data.eligible_options}
            valid_recs = []
            for rec in recommendations:
                if isinstance(rec, dict) and rec.get("option_id") in eligible_id_set:
                    valid_recs.append(rec)

            # Sort by rank
            sorted_recs = sorted(valid_recs, key=lambda r: r.get("rank", 999))

            # Build RankedRecommendation objects
            ranked_recs = []
            for i, rec in enumerate(sorted_recs, start=1):
                option_id = rec.get("option_id", "")
                reasoning = rec.get("reasoning", "").strip()
                score = rec.get("score")
                if score is not None and not 0.0 <= score <= 1.0:
                    score = None

                ranked_recs.append(
                    RankedRecommendation(
                        option_id=option_id,
                        rank=i,
                        reasoning=reasoning if reasoning else "",
                        score=score,
                    )
                )

            # Build metadata
            metadata = {
                "model": os.environ.get("AI_MODEL_TWO_NAME", "gpt-4o-mini"),
                "provider": ai_config.model_two_provider,
                "temperature": self.temperature,
                "timestamp": int(time.time()),
            }

            return ModelTwoOutput(
                success=True,
                recommendations=ranked_recs,
                metadata=metadata,
                error=None,
            )

        except Exception as e:
            return ModelTwoOutput(
                success=False,
                error=f"Model 2 provider error: {str(e)}",
                recommendations=[],
                metadata={},
            )


def _is_development_mode() -> bool:
    """Check development mode at call time to avoid circular imports with tests module."""
    return (ai_config.development_mode and not ai_config.real_model_one_enabled)


# ---------------------------------------------------------------------------
# Provider Factory
# ---------------------------------------------------------------------------

def get_model_one_client():
    """Get a Model 1 client instance based on configuration.

    Returns:
        ModelOneClient instance — either real or fake depending on AI config.
    """
    if _is_development_mode():
        from tests.fakes import FakeModelOneClient
        return FakeModelOneClient(scenario="ok")
    return RealModelOneClient()


def get_model_two_client():
    """Get a Model 2 client instance based on configuration.

    Returns:
        ModelTwoClient instance — either real or fake depending on AI config.
    """
    if _is_development_mode():
        from tests.fakes import FakeModelTwoClient
        return FakeModelTwoClient(scenario="valid")
    return RealModelTwoClient()


# Convenience wrappers (preserving existing API)
analyze_free_text = lambda input_data: get_model_one_client().analyze(input_data)
rank_recommendations = lambda input_data: get_model_two_client().rank(input_data)