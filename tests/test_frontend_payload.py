"""
Tests for the frontend questionnaire payload schema and adapter.

Covers the reconstructed fixture in docs/frontend_payload_sample.json, the
malformed fixture in tests/fixtures/, and the documented mapping decisions.
"""

import json
from pathlib import Path

import pytest

from app.schemas.frontend_payload_schema import FrontendPayload, FrontendPayloadError
from app.services.frontend_adapter import (
    adapt_frontend_payload,
    to_student_document,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
DOCS_DIR = Path(__file__).parent.parent / "docs"


def _load_reconstructed_payload() -> dict:
    with open(DOCS_DIR / "frontend_payload_sample.json", encoding="utf-8") as f:
        return json.load(f)


class TestFrontendPayloadValidation:
    """Schema validation of the frontend payload."""

    def test_reconstructed_fixture_is_valid_json(self):
        data = _load_reconstructed_payload()
        assert "student_profile" in data
        assert "interests" in data
        assert "future_direction" in data
        assert "problem_preferences" in data

    def test_reconstructed_payload_parses(self):
        data = _load_reconstructed_payload()
        payload = FrontendPayload(**data)
        assert payload.student_profile.current_stage_id == "third_secondary"
        assert len(payload.student_profile.subject_performance) == 3

    def test_malformed_fixture_is_rejected(self):
        with open(FIXTURE_DIR / "frontend_payload_malformed.json", encoding="utf-8") as f:
            with pytest.raises(json.JSONDecodeError):
                json.load(f)

    def test_missing_student_profile_is_rejected(self):
        with pytest.raises(Exception):
            FrontendPayload(**{"interests": {}})

    def test_unknown_fields_are_preserved(self):
        data = _load_reconstructed_payload()
        data["student_profile"]["custom_field"] = "kept"
        payload = FrontendPayload(**data)
        assert payload.student_profile.model_dump()["custom_field"] == "kept"

    def test_malformed_json_string_is_rejected(self):
        with pytest.raises(json.JSONDecodeError):
            json.loads('{"problem_preferences": {"abstract_concrete_preference": "concrete"')


class TestFrontendAdapter:
    """Mapping decisions and preservation guarantees."""

    def test_stage_id_maps_to_school_year(self):
        data = _load_reconstructed_payload()
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        assert adapted.school_year == 3

    def test_first_secondary_maps_to_year_one(self):
        data = _load_reconstructed_payload()
        data["student_profile"]["current_stage_id"] = "first_secondary"
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        assert adapted.school_year == 1

    def test_unknown_stage_id_raises(self):
        data = _load_reconstructed_payload()
        data["student_profile"]["current_stage_id"] = "nonsense"
        with pytest.raises(FrontendPayloadError):
            adapt_frontend_payload(FrontendPayload(**data))

    def test_grades_use_max_score_not_average(self):
        data = _load_reconstructed_payload()
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        # mathematics range is 14.5 - 16.0 -> max_score is used, NOT the average.
        # The frontend subject id is mapped to the knowledge-base subject code.
        assert adapted.grades["mathématiques"] == 16.0

    def test_subject_range_is_preserved_in_document(self):
        data = _load_reconstructed_payload()
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        doc = to_student_document(adapted)
        maths = next(s for s in doc["subject_performance"] if s["subject_id"] == "mathematics")
        assert maths["min_score"] == 14.5
        assert maths["max_score"] == 16.0

    def test_rich_fields_are_flattened_for_model_one(self):
        data = _load_reconstructed_payload()
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        assert "interests.academic_interests" in adapted.free_text_answers
        assert "future_direction.long_term_goals" in adapted.free_text_answers
        assert (
            "problem_preferences.abstract_concrete_preference" in adapted.free_text_answers
        )
        assert (
            adapted.free_text_answers["problem_preferences.abstract_concrete_preference"]
            == "concrete"
        )

    def test_question_context_describes_known_fields(self):
        data = _load_reconstructed_payload()
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        assert (
            "Academic subjects"
            in adapted.question_context["interests.academic_interests"]
        )

    def test_unknown_fields_are_recorded_not_dropped(self):
        data = _load_reconstructed_payload()
        data["student_profile"]["custom_field"] = "x"
        data["brand_new_section"] = {"a": 1}
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        assert "student_profile.custom_field" in adapted.unknown_fields
        assert "brand_new_section" in adapted.unknown_fields
        assert "brand_new_section.a" in adapted.free_text_answers

    def test_mapping_notes_flag_unconfirmed_decisions(self):
        data = _load_reconstructed_payload()
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        assert any("requires frontend confirmation" in n for n in adapted.mapping_notes)

    def test_to_student_document_preserves_original_payload(self):
        data = _load_reconstructed_payload()
        adapted = adapt_frontend_payload(FrontendPayload(**data))
        doc = to_student_document(adapted)
        assert doc["school_year"] == 3
        assert doc["questionnaire"]["student_profile"]["full_name"] == "Amina Benali"
        assert doc["free_text_answers"]["interests.academic_interests"]
        assert "questionnaire" in doc
