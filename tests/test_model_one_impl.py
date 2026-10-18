"""
Tests for Model 1 independent implementation.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.model_one_impl import (
    ModelOneImplementation,
    ModelOneExtractedData,
    ExtractedInterests,
    ExtractedGoals,
    ExtractedPreferences,
)
from app.schemas.model_one_schema import ModelOneInput, ModelOneOutput


class TestModelOneExtractedData:
    """Tests for the Model 1 output schema."""

    def test_empty_data_is_valid(self):
        """Empty extracted data should be valid."""
        data = ModelOneExtractedData()
        assert data.interests.academic_subjects == []
        assert data.goals.short_term == []
        assert data.preferences.work_environment == []
        assert data.strengths == []
        assert data.difficulties == []

    def test_full_data_is_valid(self):
        """Complete extracted data should be valid."""
        data = ModelOneExtractedData(
            interests=ExtractedInterests(
                academic_subjects=["mathematics", "physics"],
                career_areas=["engineering", "research"],
                hobbies_activities=["programming", "robotics"],
            ),
            goals=ExtractedGoals(
                short_term=["improve grades"],
                long_term=["become an engineer"],
                motivations=["problem solving"],
            ),
            preferences=ExtractedPreferences(
                work_environment=["quiet", "structured"],
                learning_style=["visual", "hands-on"],
                difficulty_tolerance="high",
            ),
            strengths=["mathematics", "logical thinking"],
            difficulties=["literature"],
            raw_themes=["enjoys building things"],
        )
        assert len(data.interests.academic_subjects) == 2
        assert data.preferences.difficulty_tolerance == "high"

    def test_invalid_data_raises_error(self):
        """Invalid data should raise ValidationError."""
        with pytest.raises(Exception):
            ModelOneExtractedData(
                interests="not_a_dict",  # Should be ExtractedInterests
            )


class TestModelOneImplementation:
    """Tests for Model 1 implementation."""

    def test_analyze_with_no_answers(self):
        """Model 1 should handle empty answers gracefully."""
        impl = ModelOneImplementation(provider_client=None)
        input_data = ModelOneInput(
            free_text_answers={},
            school_year=3,
            current_branch="sciences",
        )
        output = impl.analyze(input_data)
        assert output.success is True
        assert output.extracted_data == ModelOneExtractedData().model_dump()
        assert "no_free_text_answers" in output.metadata.get("note", "")

    def test_analyze_with_no_provider(self):
        """Model 1 should fail gracefully when no provider is configured."""
        impl = ModelOneImplementation(provider_client=None)
        input_data = ModelOneInput(
            free_text_answers={"q1": "I like math"},
            school_year=3,
            current_branch="sciences",
        )
        output = impl.analyze(input_data)
        assert output.success is False
        assert "provider" in output.error.lower()

    def test_analyze_with_working_provider(self):
        """Model 1 should return validated output when provider works."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "interests": {
                "academic_subjects": ["mathematics"],
                "career_areas": ["engineering"],
                "hobbies_activities": ["building things"],
            },
            "goals": {
                "short_term": ["improve grades"],
                "long_term": ["become engineer"],
                "motivations": ["problem solving"],
            },
            "preferences": {
                "work_environment": ["quiet"],
                "learning_style": ["hands-on"],
                "difficulty_tolerance": "high",
            },
            "strengths": ["math"],
            "difficulties": ["literature"],
            "raw_themes": [],
        }

        impl = ModelOneImplementation(provider_client=mock_provider)
        input_data = ModelOneInput(
            free_text_answers={"q1": "I love math and building things"},
            school_year=3,
            current_branch="sciences",
        )
        output = impl.analyze(input_data)
        assert output.success is True
        assert "mathematics" in output.extracted_data["interests"]["academic_subjects"]
        assert output.metadata["prompt_version"] == "1.0.0"

    def test_analyze_with_extra_fields_in_output(self):
        """Model 1 should handle provider output with extra fields."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "invalid_key": "invalid_value",
        }

        impl = ModelOneImplementation(provider_client=mock_provider)
        input_data = ModelOneInput(
            free_text_answers={"q1": "I like math"},
            school_year=3,
            current_branch="sciences",
        )
        output = impl.analyze(input_data)
        # Pydantic creates a valid object with defaults since all fields have defaults
        assert output.success is True
        assert output.extracted_data["interests"]["academic_subjects"] == []

    def test_analyze_with_provider_exception(self):
        """Model 1 should handle provider exceptions with retries."""
        mock_provider = MagicMock()
        mock_provider.call.side_effect = Exception("API error")

        impl = ModelOneImplementation(
            provider_client=mock_provider,
            max_retries=2,
        )
        input_data = ModelOneInput(
            free_text_answers={"q1": "I like math"},
            school_year=3,
            current_branch="sciences",
        )
        output = impl.analyze(input_data)
        assert output.success is False
        assert "provider" in output.error.lower()
        # Should have tried 3 times (initial + 2 retries)
        assert mock_provider.call.call_count == 3

    def test_analyze_with_malformed_json_response(self):
        """Model 1 should handle malformed JSON from provider."""
        mock_provider = MagicMock()
        mock_provider.call.side_effect = json.JSONDecodeError("test", "test", 0)

        impl = ModelOneImplementation(provider_client=mock_provider)
        input_data = ModelOneInput(
            free_text_answers={"q1": "I like math"},
            school_year=3,
            current_branch="sciences",
        )
        output = impl.analyze(input_data)
        assert output.success is False

    def test_prompt_contains_student_answers(self):
        """Model 1 prompt should contain the student's answers."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = ModelOneExtractedData().model_dump()

        impl = ModelOneImplementation(provider_client=mock_provider)
        input_data = ModelOneInput(
            free_text_answers={"q1": "I love mathematics and physics"},
            school_year=3,
            current_branch="sciences_expérimentales",
        )
        impl.analyze(input_data)

        # Check that the prompt contains the student's answer
        call_args = mock_provider.call.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        assert "I love mathematics and physics" in user_prompt
        assert "sciences_expérimentales" in user_prompt

    def test_prompt_contains_question_context(self):
        """Model 1 prompt should include question context when provided."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = ModelOneExtractedData().model_dump()

        impl = ModelOneImplementation(provider_client=mock_provider)
        input_data = ModelOneInput(
            free_text_answers={"q1": "I like math"},
            question_context={"q1": "What subjects do you enjoy?"},
            school_year=3,
            current_branch="sciences",
        )
        impl.analyze(input_data)

        call_args = mock_provider.call.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        assert "What subjects do you enjoy?" in user_prompt


import json
