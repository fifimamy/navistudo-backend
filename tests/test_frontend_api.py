"""
Tests for the frontend payload API flow on POST /api/v1/recommendations.

Verifies that the frontend can submit its questionnaire payload, that the
payload is persisted before the pipeline runs, that the verified token UID is
used (not a body UID), and that invalid payloads are rejected.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

DOCS_DIR = Path(__file__).parent.parent / "docs"


def _load_payload() -> dict:
    with open(DOCS_DIR / "frontend_payload_sample.json", encoding="utf-8") as f:
        return json.load(f)


def _make_result(uid: str = "uid123") -> object:
    from app.services.recommendation_service import RecommendationResult

    return RecommendationResult(
        analysis_id="analysis-abc",
        student_uid=uid,
        recommendation_type="university_major",
        recommendations=[
            {
                "id": "major_computer_science",
                "option_id": "major_computer_science",
                "name": "Informatique",
                "description": "Computer science",
                "rank": 1,
                "score": 0.9,
                "reasoning": "Strong fit for a mathematics/physics student.",
            }
        ],
        created_at=datetime.utcnow(),
        model_one_metadata={"model": "test"},
        model_two_metadata={"model": "test"},
    )


class TestFrontendPayloadApi:
    """API-level tests with the service layer mocked."""

    def _auth(self):
        return {"Authorization": "Bearer valid_token"}

    def test_payload_is_persisted_before_pipeline(self, client):
        payload = _load_payload()
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client, \
             patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:

            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            mock_service = Mock()
            mock_service.create_recommendation.return_value = _make_result()
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/recommendations",
                json=payload,
                headers=self._auth(),
            )

            assert response.status_code == 201
            data = response.get_json()
            assert data["profile_saved"] is True
            assert data["analysis_id"] == "analysis-abc"
            assert mock_service.persist_student_profile.called
            assert mock_service.create_recommendation.called

    def test_verified_uid_is_used_not_body_uid(self, client):
        payload = _load_payload()
        payload["student_uid"] = "attacker_uid"  # must be ignored
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client, \
             patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:

            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            mock_service = Mock()
            mock_service.create_recommendation.return_value = _make_result("uid123")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/recommendations",
                json=payload,
                headers=self._auth(),
            )

            assert response.status_code == 201
            args, _ = mock_service.create_recommendation.call_args
            assert args[0] == "uid123"

    def test_unknown_stage_id_returns_400(self, client):
        payload = _load_payload()
        payload["student_profile"]["current_stage_id"] = "nonsense"
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/v1/recommendations",
                json=payload,
                headers=self._auth(),
            )
            assert response.status_code == 400
            assert response.get_json()["error"] == "bad_request"

    def test_non_object_body_returns_400(self, client):
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/v1/recommendations",
                data=json.dumps([1, 2, 3]),
                content_type="application/json",
                headers=self._auth(),
            )
            assert response.status_code == 400

    def test_empty_body_is_still_accepted(self, client):
        """Backward compatibility: empty body reads the profile from Firestore."""
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client, \
             patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:

            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            mock_service = Mock()
            mock_service.create_recommendation.return_value = _make_result()
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/recommendations",
                json={},
                headers=self._auth(),
            )
            assert response.status_code == 201
            assert response.get_json()["profile_saved"] is False
            assert not mock_service.persist_student_profile.called


class _FakeFirebaseClient:
    """Minimal in-memory Firebase client used by the integration test."""

    def __init__(self):
        self.students = {}
        self.results = {}
        self.kb_options = []

    def verify_id_token(self, token):
        return {"uid": "uid123", "email": "student@example.com"}

    def get_student_profile(self, uid):
        return self.students.get(uid)

    def get_student_free_text_answers(self, uid):
        profile = self.students.get(uid)
        return profile.get("free_text_answers") if profile else None

    def get_knowledge_base_options(self, recommendation_type):
        return [o for o in self.kb_options if o.get("type") == recommendation_type]

    def save_student_profile(self, uid, profile_data):
        self.students[uid] = profile_data
        return uid

    def save_recommendation_result(self, result_data):
        self.results[result_data["analysis_id"]] = result_data
        return result_data["analysis_id"]

    def get_recommendation_result(self, analysis_id, student_uid):
        result = self.results.get(analysis_id)
        if result and result.get("student_uid") == student_uid:
            return result
        return None

    def list_recommendation_results(self, student_uid, limit=10):
        return [r for r in self.results.values() if r.get("student_uid") == student_uid][:limit]


class _FakeAIProvider:
    """Deterministic AI provider compatible with both model implementations."""

    def call(self, system_prompt, user_prompt, temperature=0.0, timeout=30, response_format=None):
        if "free-text" in system_prompt.lower():
            return {
                "interests": {
                    "academic_subjects": ["mathematics", "physics"],
                    "career_areas": ["software_engineering"],
                    "hobbies_activities": ["programming"],
                },
                "goals": {"long_term": ["become a software engineer"]},
                "preferences": {"difficulty_tolerance": "high"},
                "strengths": ["mathematics"],
                "difficulties": [],
                "raw_themes": [],
            }
        import re

        ids = [i for i in re.findall(r"id=([a-zA-Z0-9_]+)", user_prompt) if i.startswith("major_")]
        return {
            "ranked_options": [
                {
                    "option_id": oid,
                    "rank": i + 1,
                    "score": round(1.0 - 0.1 * i, 2),
                    "reasoning": "Good fit for student interests and grades.",
                }
                for i, oid in enumerate(ids)
            ]
        }


class TestFrontendPayloadEndToEnd:
    """Full flow through the route using fakes (no real Firebase / AI)."""

    def test_submit_payload_persists_and_returns_recommendations(self, client):
        from app.services.knowledge_base_service import KnowledgeBaseService

        fake_firebase = _FakeFirebaseClient()
        # Seed a KB option eligible for a mathematics/physics student.
        # Note: subject id is the FRONTEND id ('mathematics'); this is the
        # documented subject-id normalization gap (docs/PAYLOAD_NOTES.md).
        fake_firebase.kb_options = [
            {
                "id": "major_computer_science",
                "name": "Informatique",
                "type": "university_major",
                "description": "Computer science",
                "required_branches": ["mathématiques"],
                "required_branches_status": "verified",
                "min_grades": {"mathématiques": 13.0},
                "min_grades_status": "verified",
                "required_wilayas": None,
                "required_wilayas_status": "not_applicable",
                "max_capacity": None,
                "max_capacity_status": "not_applicable",
            }
        ]

        payload = _load_payload()
        # A year-3 student reports their current branch.
        payload["student_profile"]["current_branch_id"] = "mathématiques"

        with patch("app.routes.recommendations.get_firebase_client", return_value=fake_firebase), \
             patch(
                 "app.routes.recommendations.JsonKnowledgeBaseService",
                 side_effect=lambda *a, **k: KnowledgeBaseService(fake_firebase),
             ), \
             patch("app.ai_client.get_ai_client", return_value=_FakeAIProvider()):

            response = client.post(
                "/api/v1/recommendations",
                json=payload,
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 201, response.get_json()
        data = response.get_json()
        assert data["profile_saved"] is True
        assert data["recommendation_type"] == "university_major"
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["option_id"] == "major_computer_science"

        # The profile was persisted and is readable back.
        persisted = fake_firebase.students.get("uid123")
        assert persisted is not None
        assert persisted["school_year"] == 3
        assert persisted["current_branch"] == "mathématiques"
        # The frontend subject id is mapped to the knowledge-base subject code.
        assert persisted["grades"]["mathématiques"] == 16.0
        assert persisted["free_text_answers"]["interests.academic_interests"]

        # The result was persisted.
        assert fake_firebase.results
        saved = next(iter(fake_firebase.results.values()))
        assert saved["student_uid"] == "uid123"
        assert saved["recommendations"][0]["option_id"] == "major_computer_science"

    def test_response_includes_frontend_envelope_fields(self, client):
        """The response must satisfy the frontend contract.ts envelope."""
        from app.services.knowledge_base_service import KnowledgeBaseService

        fake_firebase = _FakeFirebaseClient()
        fake_firebase.kb_options = [
            {
                "id": "major_computer_science",
                "name": "Informatique",
                "type": "university_major",
                "description": "Computer science",
                "required_branches": ["mathématiques"],
                "required_branches_status": "verified",
                "min_grades": {"mathématiques": 13.0},
                "min_grades_status": "verified",
                "required_wilayas": None,
                "required_wilayas_status": "not_applicable",
                "max_capacity": None,
                "max_capacity_status": "not_applicable",
            }
        ]

        payload = _load_payload()
        payload["student_profile"]["current_branch_id"] = "mathematics"

        with patch("app.routes.recommendations.get_firebase_client", return_value=fake_firebase), \
             patch(
                 "app.routes.recommendations.JsonKnowledgeBaseService",
                 side_effect=lambda *a, **k: KnowledgeBaseService(fake_firebase),
             ), \
             patch("app.ai_client.get_ai_client", return_value=_FakeAIProvider()):

            response = client.post(
                "/api/v1/recommendations",
                json=payload,
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 201, response.get_json()
        data = response.get_json()
        # Envelope
        assert data["schema_version"] == "1.0.0"
        assert "summary" in data
        assert data["summary"]["total_evaluated"] >= 1
        # Recommendation fields the frontend ResultsView renders
        rec = data["recommendations"][0]
        for field in (
            "major_id", "title_en", "title_ar", "category", "match_score",
            "match_level", "explanation_en", "explanation_ar", "key_subjects",
            "typical_careers", "prerequisite_branches", "study_duration_years",
            "institution_types",
        ):
            assert field in rec, f"missing frontend field: {field}"
        assert rec["major_id"] == "major_computer_science"
        assert rec["match_level"] in (
            "strong_match", "great_alternative", "field_to_explore"
        )
