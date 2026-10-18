"""
Tests for Model 2 independent implementation.
"""

import pytest
from unittest.mock import MagicMock

from app.model_two_impl import ModelTwoImplementation
from app.schemas.model_two_schema import (
    ModelTwoInput,
    ModelTwoOutput,
    RankedRecommendation,
    RecommendationOption,
)


def _make_eligible_options():
    """Create test eligible options."""
    return [
        RecommendationOption(
            id="opt_a", name="Option A", description="First option",
            field="sciences", difficulty_level=3,
        ),
        RecommendationOption(
            id="opt_b", name="Option B", description="Second option",
            field="mathematics", difficulty_level=4,
        ),
        RecommendationOption(
            id="opt_c", name="Option C", description="Third option",
            field="letters", difficulty_level=2,
        ),
    ]


def _make_input_data(eligible_options=None):
    """Create test input data."""
    if eligible_options is None:
        eligible_options = _make_eligible_options()
    return ModelTwoInput(
        student_profile={
            "school_year": 3,
            "current_branch": "sciences",
            "grades": {"math": 15.0, "physics": 14.0},
            "wilaya": "Alger",
        },
        model_one_output={
            "interests": {"academic_subjects": ["math", "physics"]},
            "goals": {"long_term": ["engineer"]},
            "preferences": {"difficulty_tolerance": "high"},
        },
        eligible_options=eligible_options,
        recommendation_type="university_major",
    )


class TestModelTwoImplementation:
    """Tests for Model 2 implementation."""

    def test_rank_with_no_eligible_options(self):
        """Model 2 should handle empty eligible options."""
        impl = ModelTwoImplementation(provider_client=None)
        input_data = _make_input_data(eligible_options=[])
        output = impl.rank(input_data)
        assert output.success is True
        assert output.recommendations == []
        assert output.metadata["note"] == "no_eligible_options"

    def test_rank_with_no_provider(self):
        """Model 2 should fail gracefully when no provider is configured."""
        impl = ModelTwoImplementation(provider_client=None)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is False
        assert "provider" in output.error.lower()

    def test_rank_with_working_provider(self):
        """Model 2 should return validated rankings when provider works."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "ranked_options": [
                {
                    "option_id": "opt_a",
                    "rank": 1,
                    "score": 0.95,
                    "reasoning": "Strong match for sciences student with good grades",
                },
                {
                    "option_id": "opt_b",
                    "rank": 2,
                    "score": 0.8,
                    "reasoning": "Good match, student enjoys math",
                },
                {
                    "option_id": "opt_c",
                    "rank": 3,
                    "score": 0.5,
                    "reasoning": "Weak match, student prefers sciences",
                },
            ],
            "overall_confidence": 0.85,
        }

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is True
        assert len(output.recommendations) == 3
        assert output.recommendations[0].option_id == "opt_a"
        assert output.recommendations[0].rank == 1
        assert output.recommendations[0].score == 0.95
        assert output.metadata["eligible_count"] == 3
        assert output.metadata["ranked_count"] == 3

    def test_rank_filters_unknown_option_ids(self):
        """Model 2 should filter out unknown option IDs."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "ranked_options": [
                {
                    "option_id": "opt_a",
                    "rank": 1,
                    "score": 0.9,
                    "reasoning": "Good match",
                },
                {
                    "option_id": "unknown_id",
                    "rank": 2,
                    "score": 0.8,
                    "reasoning": "Should be filtered out",
                },
                {
                    "option_id": "opt_b",
                    "rank": 3,
                    "score": 0.7,
                    "reasoning": "Also good",
                },
            ],
        }

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is True
        assert len(output.recommendations) == 2
        option_ids = {r.option_id for r in output.recommendations}
        assert "unknown_id" not in option_ids
        assert "opt_a" in option_ids
        assert "opt_b" in option_ids

    def test_rank_removes_duplicate_option_ids(self):
        """Model 2 should remove duplicate option IDs."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "ranked_options": [
                {
                    "option_id": "opt_a",
                    "rank": 1,
                    "score": 0.9,
                    "reasoning": "Good match",
                },
                {
                    "option_id": "opt_a",
                    "rank": 2,
                    "score": 0.8,
                    "reasoning": "Duplicate - should be removed",
                },
                {
                    "option_id": "opt_b",
                    "rank": 3,
                    "score": 0.7,
                    "reasoning": "Also good",
                },
            ],
        }

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is True
        assert len(output.recommendations) == 2
        option_ids = [r.option_id for r in output.recommendations]
        assert len(option_ids) == len(set(option_ids))

    def test_rank_provides_default_reasoning(self):
        """Model 2 should provide default reasoning when missing."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "ranked_options": [
                {
                    "option_id": "opt_a",
                    "rank": 1,
                    "score": 0.9,
                    "reasoning": "",
                },
            ],
        }

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is True
        assert len(output.recommendations) == 1
        assert len(output.recommendations[0].reasoning) > 0

    def test_rank_handles_invalid_scores(self):
        """Model 2 should handle invalid score values."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "ranked_options": [
                {
                    "option_id": "opt_a",
                    "rank": 1,
                    "score": 1.5,  # Invalid: > 1.0
                    "reasoning": "Good match",
                },
                {
                    "option_id": "opt_b",
                    "rank": 2,
                    "score": -0.1,  # Invalid: < 0.0
                    "reasoning": "Also good",
                },
                {
                    "option_id": "opt_c",
                    "rank": 3,
                    "score": 0.5,  # Valid
                    "reasoning": "Weak match",
                },
            ],
        }

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is True
        assert output.recommendations[0].score is None  # Invalid -> None
        assert output.recommendations[1].score is None  # Invalid -> None
        assert output.recommendations[2].score == 0.5  # Valid

    def test_rank_with_provider_exception(self):
        """Model 2 should handle provider exceptions with retries."""
        mock_provider = MagicMock()
        mock_provider.call.side_effect = Exception("API error")

        impl = ModelTwoImplementation(
            provider_client=mock_provider,
            max_retries=2,
        )
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is False
        assert "provider" in output.error.lower()
        assert mock_provider.call.call_count == 3

    def test_rank_reassigns_sequential_ranks(self):
        """Model 2 should reassign sequential ranks after filtering."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "ranked_options": [
                {
                    "option_id": "opt_a",
                    "rank": 1,
                    "score": 0.9,
                    "reasoning": "Good",
                },
                {
                    "option_id": "opt_b",
                    "rank": 5,  # Gap in ranks
                    "score": 0.8,
                    "reasoning": "Also good",
                },
                {
                    "option_id": "opt_c",
                    "rank": 10,  # Another gap
                    "score": 0.7,
                    "reasoning": "Weak",
                },
            ],
        }

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is True
        assert [r.rank for r in output.recommendations] == [1, 2, 3]

    def test_prompt_contains_student_data(self):
        """Model 2 prompt should contain student profile and options."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {
            "ranked_options": [
                {
                    "option_id": "opt_a",
                    "rank": 1,
                    "score": 0.9,
                    "reasoning": "Good match",
                },
            ],
        }

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        impl.rank(input_data)

        call_args = mock_provider.call.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        # Should contain student profile info
        assert "school_year" in user_prompt
        assert "sciences" in user_prompt
        # Should contain eligible options
        assert "opt_a" in user_prompt
        assert "Option A" in user_prompt
        # Should contain Model 1 output
        assert "interests" in user_prompt

    def test_rank_with_empty_provider_response(self):
        """Model 2 should handle empty provider response."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = {}

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is True
        assert output.recommendations == []

    def test_rank_with_no_provider_return(self):
        """Model 2 should handle None from provider."""
        mock_provider = MagicMock()
        mock_provider.call.return_value = None

        impl = ModelTwoImplementation(provider_client=mock_provider)
        input_data = _make_input_data()
        output = impl.rank(input_data)
        assert output.success is False
