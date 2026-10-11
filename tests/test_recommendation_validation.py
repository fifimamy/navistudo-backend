"""
NaviStudo Backend - Tests for Model 2 output validation.
"""

import pytest

from app.schemas.model_two_schema import RankedRecommendation
from app.services.recommendation_validation import (
    RecommendationValidationError,
    collect_validation_problems,
    validate_ranked_recommendations,
)

ELIGIBLE = {"opt_a", "opt_b", "opt_c"}


def rec(option_id: str, rank: int, reasoning: str = "Good fit.", score: float | None = None):
    return RankedRecommendation(
        option_id=option_id, rank=rank, reasoning=reasoning, score=score
    )


class TestValidOutput:
    def test_valid_full_ranking_passes(self):
        recs = [rec("opt_a", 1), rec("opt_b", 2), rec("opt_c", 3)]
        validate_ranked_recommendations(recs, ELIGIBLE, max_results=5)

    def test_subset_of_eligible_passes(self):
        recs = [rec("opt_b", 1), rec("opt_a", 2)]
        validate_ranked_recommendations(recs, ELIGIBLE, max_results=5)

    def test_unordered_list_with_valid_ranks_passes(self):
        recs = [rec("opt_b", 2), rec("opt_a", 1)]
        validate_ranked_recommendations(recs, ELIGIBLE, max_results=5)

    def test_scores_in_range_pass(self):
        recs = [rec("opt_a", 1, score=1.0), rec("opt_b", 2, score=0.0)]
        validate_ranked_recommendations(recs, ELIGIBLE, max_results=5)

    def test_empty_result_ok_when_no_eligible_options(self):
        validate_ranked_recommendations([], set(), max_results=5)

    def test_accepts_list_of_ids(self):
        validate_ranked_recommendations([rec("opt_a", 1)], ["opt_a", "opt_b"], max_results=5)


class TestInvalidOutput:
    def test_empty_result_with_eligible_options_fails(self):
        with pytest.raises(RecommendationValidationError):
            validate_ranked_recommendations([], ELIGIBLE, max_results=5)

    def test_unknown_option_id_fails(self):
        problems = collect_validation_problems([rec("opt_x", 1)], ELIGIBLE, 5)
        assert any("unknown option_id" in p and "opt_x" in p for p in problems)

    def test_duplicate_option_id_fails(self):
        recs = [rec("opt_a", 1), rec("opt_a", 2)]
        problems = collect_validation_problems(recs, ELIGIBLE, 5)
        assert any("duplicate" in p for p in problems)

    def test_too_many_results_fails(self):
        recs = [rec("opt_a", 1), rec("opt_b", 2), rec("opt_c", 3)]
        problems = collect_validation_problems(recs, ELIGIBLE, max_results=2)
        assert any("maximum is 2" in p for p in problems)

    def test_rank_gap_fails(self):
        recs = [rec("opt_a", 1), rec("opt_b", 3)]
        problems = collect_validation_problems(recs, ELIGIBLE, 5)
        assert any("ranks must be exactly" in p for p in problems)

    def test_repeated_rank_fails(self):
        recs = [rec("opt_a", 1), rec("opt_b", 1)]
        problems = collect_validation_problems(recs, ELIGIBLE, 5)
        assert any("ranks must be exactly" in p for p in problems)

    def test_ranks_not_starting_at_one_fail(self):
        recs = [rec("opt_a", 2), rec("opt_b", 3)]
        problems = collect_validation_problems(recs, ELIGIBLE, 5)
        assert any("ranks must be exactly" in p for p in problems)

    @pytest.mark.parametrize("reasoning", ["", "   ", "\n\t"])
    def test_empty_reasoning_fails(self, reasoning):
        problems = collect_validation_problems([rec("opt_a", 1, reasoning=reasoning)], ELIGIBLE, 5)
        assert any("empty reasoning" in p for p in problems)

    @pytest.mark.parametrize("score", [-0.1, 1.5])
    def test_score_out_of_range_fails(self, score):
        problems = collect_validation_problems([rec("opt_a", 1, score=score)], ELIGIBLE, 5)
        assert any("score outside" in p for p in problems)


class TestErrorReporting:
    def test_all_problems_are_reported_together(self):
        recs = [rec("opt_x", 1, reasoning=""), rec("opt_x", 1)]
        with pytest.raises(RecommendationValidationError) as exc:
            validate_ranked_recommendations(recs, ELIGIBLE, max_results=5)
        problems = exc.value.problems
        assert len(problems) >= 4  # unknown, duplicate, ranks, empty reasoning

    def test_exception_message_contains_problems(self):
        with pytest.raises(RecommendationValidationError, match="opt_x"):
            validate_ranked_recommendations([rec("opt_x", 1)], ELIGIBLE, 5)
