"""
NaviStudo Backend - Pipeline tests using fakes (no Firebase, no real AI).

Doubles as living documentation of how to use the fakes in tests/fakes.py.
"""

import pytest

from app.schemas.model_two_schema import ModelTwoInput, RecommendationOption
from app.services.recommendation_service import (
    ModelOneError,
    ModelTwoError,
    ValidationError,
)
from app.services.recommendation_validation import collect_validation_problems
from app.services.student_service import StudentNotFoundError

from tests.fakes import (
    EXPECTED_ELIGIBLE_IDS,
    FakeModelTwoClient,
    make_fake_kb_options,
)


class TestEligibilityWithFakes:
    def test_only_eligible_options_are_sent_to_model_two(self, make_service, fake_uid):
        service, _, model_two = make_service()
        service.create_recommendation(fake_uid)

        sent_ids = {o.id for o in model_two.calls[0].eligible_options}
        assert sent_ids == EXPECTED_ELIGIBLE_IDS

    def test_ineligible_options_never_reach_the_model(self, make_service, fake_uid):
        service, _, model_two = make_service()
        service.create_recommendation(fake_uid)

        sent_ids = {o.id for o in model_two.calls[0].eligible_options}
        assert "fake_opt_c" not in sent_ids  # wrong branch
        assert "fake_opt_e" not in sent_ids  # grade too low

    def test_no_eligible_options_returns_empty_result_and_skips_models(self, make_service, fake_uid):
        ineligible_only = [o for o in make_fake_kb_options() if o.id in {"fake_opt_c", "fake_opt_e"}]
        service, model_one, model_two = make_service(options=ineligible_only)

        result = service.create_recommendation(fake_uid)

        assert result.recommendations == []
        assert model_one.calls == []
        assert model_two.calls == []


class TestHappyPath:
    def test_valid_flow_returns_ranked_recommendations(self, recommendation_service, fake_uid):
        result = recommendation_service.create_recommendation(fake_uid)

        assert result.student_uid == fake_uid
        assert result.recommendation_type == "university_major"
        assert [r["rank"] for r in result.recommendations] == [1, 2, 3]
        assert {r["option_id"] for r in result.recommendations} == EXPECTED_ELIGIBLE_IDS

    def test_model_two_receives_model_one_output(self, make_service, fake_uid):
        service, _, model_two = make_service()
        service.create_recommendation(fake_uid)

        assert "interests" in model_two.calls[0].model_one_output

    def test_free_text_goes_to_model_one_but_not_to_model_two_profile(self, make_service, fake_uid):
        service, model_one, model_two = make_service()
        service.create_recommendation(fake_uid)

        assert "fake_q_goal" in model_one.calls[0].free_text_answers
        assert "free_text_answers" not in model_two.calls[0].student_profile


class TestFailures:
    def test_unknown_student_raises(self, make_service):
        service, _, _ = make_service()
        with pytest.raises(StudentNotFoundError):
            service.create_recommendation("fake_uid_missing")

    def test_model_one_failure_raises_model_one_error(self, make_service, fake_uid):
        service, _, model_two = make_service(model_one="failure")
        with pytest.raises(ModelOneError):
            service.create_recommendation(fake_uid)
        assert model_two.calls == []  # pipeline stopped before Model 2

    def test_model_two_failure_raises_model_two_error(self, make_service, fake_uid):
        service, _, _ = make_service(model_two="failure")
        with pytest.raises(ModelTwoError):
            service.create_recommendation(fake_uid)

    def test_unknown_option_id_is_rejected_by_current_service(self, make_service, fake_uid):
        service, _, _ = make_service(model_two="unknown_id")
        with pytest.raises(ValidationError):
            service.create_recommendation(fake_uid)


class TestBadModelOutputsAgainstNewValidator:
    """Each bad scenario must be caught by recommendation_validation.

    The CURRENT service only checks unknown IDs, so these scenarios would pass
    straight through it. That gap goes away once the new validator is wired in.
    """

    EXPECTED_PROBLEM = {
        "unknown_id": "unknown option_id",
        "duplicate_id": "duplicate option_id",
        "duplicate_rank": "ranks must be exactly",
        "rank_gap": "ranks must be exactly",
        "empty_reasoning": "empty reasoning",
        "bad_score": "score outside",
        "empty": "no recommendations returned",
    }

    @pytest.mark.parametrize("scenario", sorted(EXPECTED_PROBLEM))
    def test_bad_scenario_is_flagged(self, make_service, fake_uid, scenario):
        service, _, model_two = make_service(model_two=scenario)
        eligible = service._kb_service.filter_eligible_options(
            service._student_service.get_structured_profile(fake_uid),
            service._determine_recommendation_type(3),
        )
        input_data = ModelTwoInput(
            eligible_options=[RecommendationOption(id=o.id, name=o.name) for o in eligible],
            recommendation_type="university_major",
        )
        output = model_two.rank(input_data)

        problems = collect_validation_problems(
            output.recommendations, {o.id for o in eligible}, max_results=5
        )
        assert any(self.EXPECTED_PROBLEM[scenario] in p for p in problems)


class TestFakeClientsThemselves:
    def test_valid_scenario_is_actually_valid(self, make_service, fake_uid):
        service, _, model_two = make_service()
        service.create_recommendation(fake_uid)
        ids = {o.id for o in model_two.calls[0].eligible_options}
        output = FakeModelTwoClient("valid").rank(model_two.calls[0])
        assert collect_validation_problems(output.recommendations, ids, 5) == []

    def test_unknown_scenario_name_is_rejected(self):
        with pytest.raises(ValueError):
            FakeModelTwoClient("not_a_scenario")
