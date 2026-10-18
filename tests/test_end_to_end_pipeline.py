"""
End-to-end pipeline test covering the entire recommendation flow
using deterministic test clients and a test persistence layer.
"""

import pytest
from dataclasses import asdict
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from app.model_one_impl import ModelOneImplementation
from app.model_two_impl import ModelTwoImplementation
from app.services.recommendation_service import RecommendationService
from app.services.student_service import StudentService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.results_service import ResultsService
from app.services.recommendation_validation import validate_ranked_recommendations
from app.schemas.model_one_schema import ModelOneInput
from app.schemas.model_two_schema import ModelTwoInput, RecommendationOption
from app.exceptions import StudentNotFoundError, ModelOneError, ModelTwoError, ValidationError


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class FakeAIProvider:
    """Deterministic AI provider for end-to-end testing."""

    def __init__(self):
        self.model_one_call_count = 0
        self.model_two_call_count = 0

    def call(self, system_prompt, user_prompt, temperature=0.0, timeout=30, response_format=None):
        if "Model 1" in system_prompt or "free-text" in system_prompt.lower():
            self.model_one_call_count += 1
            return {
                "interests": {
                    "academic_subjects": ["mathematics", "physics"],
                    "career_areas": ["engineering", "research"],
                    "hobbies_activities": ["building things", "problem solving"],
                },
                "goals": {
                    "short_term": ["improve grades"],
                    "long_term": ["become an engineer"],
                    "motivations": ["solving real problems"],
                },
                "preferences": {
                    "work_environment": ["structured", "collaborative"],
                    "learning_style": ["hands-on", "visual"],
                    "difficulty_tolerance": "high",
                },
                "strengths": ["mathematics", "logical thinking"],
                "difficulties": ["literature"],
                "raw_themes": ["enjoys building things"],
            }
        else:
            self.model_two_call_count += 1
            # Return recommendations for known test option IDs
            # This is a test double - we know what options exist in our test data
            all_possible_ids = ["opt_a", "opt_b", "opt_c", "branch_sciences", "branch_letters"]
            ranked = []
            for i, oid in enumerate(all_possible_ids):
                ranked.append({
                    "option_id": oid,
                    "rank": i + 1,
                    "score": round(1.0 - 0.1 * i, 2),
                    "reasoning": f"Rank {i+1}: Good fit based on student profile and interests",
                })
            return {
                "ranked_options": ranked,
                "overall_confidence": 0.85,
            }


class FakeFirebaseClient:
    """In-memory Firebase client for testing."""

    def __init__(self):
        self.students = {}
        self.results = {}
        self.kb_options = []

    def get_student_profile(self, uid):
        return self.students.get(uid)

    def get_student_free_text_answers(self, uid):
        profile = self.students.get(uid)
        if profile:
            return profile.get("free_text_answers")
        return None

    def get_knowledge_base_options(self, recommendation_type):
        return [opt for opt in self.kb_options if opt.get("type") == recommendation_type]

    def save_recommendation_result(self, result_data):
        analysis_id = result_data["analysis_id"]
        self.results[analysis_id] = result_data
        return analysis_id

    def get_recommendation_result(self, analysis_id, student_uid):
        result = self.results.get(analysis_id)
        if result and result.get("student_uid") == student_uid:
            return result
        return None

    def list_recommendation_results(self, student_uid, limit=10):
        results = [
            r for r in self.results.values()
            if r.get("student_uid") == student_uid
        ]
        return sorted(results, key=lambda r: r.get("created_at", ""), reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_firebase():
    """Create a fake Firebase client with test data."""
    client = FakeFirebaseClient()
    client.students["student_1"] = {
        "uid": "student_1",
        "school_year": 3,
        "current_branch": "sciences",
        "wilaya": "Alger",
        "grades": {"math": 15.0, "physics": 14.0, "chemistry": 13.0},
        "free_text_answers": {
            "q1": "I love mathematics and physics, and I enjoy building things",
            "q2": "I want to become an engineer",
        },
    }
    client.students["student_2"] = {
        "uid": "student_2",
        "school_year": 1,
        "current_branch": None,
        "wilaya": "Oran",
        "grades": {"math": 12.0, "french": 14.0},
        "free_text_answers": {
            "q1": "I enjoy literature and writing",
        },
    }
    return client


@pytest.fixture
def fake_ai_provider():
    """Create a fake AI provider."""
    return FakeAIProvider()


@pytest.fixture
def kb_options():
    """Create test knowledge base options."""
    from app.services.knowledge_base_service import KnowledgeBaseOption, RecommendationType
    t = RecommendationType.UNIVERSITY_MAJOR
    return [
        KnowledgeBaseOption(
            id="opt_a", name="Engineering", type=t,
            description="Engineering program",
            required_branches=["sciences"],
            min_grades={"math": 12.0},
        ),
        KnowledgeBaseOption(
            id="opt_b", name="Computer Science", type=t,
            description="CS program",
            required_branches=["sciences"],
            min_grades={"math": 11.0},
        ),
        KnowledgeBaseOption(
            id="opt_c", name="Law", type=t,
            description="Law program",
            required_branches=["lettres"],
        ),
    ]


@pytest.fixture
def services(fake_firebase, fake_ai_provider, kb_options):
    """Create all services with test doubles."""
    # Set KB options on the fake firebase client
    fake_firebase.kb_options = [asdict(opt) for opt in kb_options]

    student_service = StudentService(firebase_client=fake_firebase)
    kb_service = KnowledgeBaseService(firebase_client=fake_firebase)
    results_service = ResultsService(firebase_client=fake_firebase)
    model_one = ModelOneImplementation(provider_client=fake_ai_provider)
    model_two = ModelTwoImplementation(provider_client=fake_ai_provider)

    recommendation_service = RecommendationService(
        student_service=student_service,
        kb_service=kb_service,
        model_one=model_one,
        model_two=model_two,
        firebase_client=fake_firebase,
        results_service=results_service,
    )

    return {
        "student_service": student_service,
        "kb_service": kb_service,
        "results_service": results_service,
        "model_one": model_one,
        "model_two": model_two,
        "recommendation_service": recommendation_service,
        "ai_provider": fake_ai_provider,
    }


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    """Test the complete recommendation pipeline."""

    def test_full_pipeline_year3_student(self, services, fake_firebase):
        """Test complete pipeline for a year 3 student."""
        result = services["recommendation_service"].create_recommendation("student_1")

        assert result.student_uid == "student_1"
        assert result.recommendation_type == "university_major"
        assert len(result.recommendations) == 2  # Only 2 eligible options (opt_a, opt_b)
        assert result.recommendations[0]["option_id"] == "opt_a"
        assert result.recommendations[0]["rank"] == 1
        assert result.model_one_metadata is not None
        assert result.model_two_metadata is not None

        # Verify Model 1 was called
        assert services["ai_provider"].model_one_call_count == 1
        # Verify Model 2 was called
        assert services["ai_provider"].model_two_call_count == 1

        # Verify result was persisted
        stored = fake_firebase.results.get(result.analysis_id)
        assert stored is not None
        assert stored["student_uid"] == "student_1"

    def test_full_pipeline_year1_student(self, services, fake_firebase):
        """Test pipeline for a year 1 student (secondary branch recommendations)."""
        # Add secondary branch options to KB via fake firebase
        from app.services.knowledge_base_service import KnowledgeBaseOption, RecommendationType
        t = RecommendationType.SECONDARY_BRANCH
        fake_firebase.kb_options = [
            asdict(KnowledgeBaseOption(
                id="branch_sciences", name="Sciences", type=t,
                description="Science branch",
            )),
            asdict(KnowledgeBaseOption(
                id="branch_letters", name="Letters", type=t,
                description="Letters branch",
            )),
        ]

        result = services["recommendation_service"].create_recommendation("student_2")

        assert result.student_uid == "student_2"
        assert result.recommendation_type == "secondary_branch"
        assert len(result.recommendations) == 2

    def test_retrieve_recommendation(self, services, fake_firebase):
        """Test retrieving a saved recommendation."""
        # Create a recommendation
        created = services["recommendation_service"].create_recommendation("student_1")

        # Retrieve it
        retrieved = services["recommendation_service"].get_recommendation(
            created.analysis_id, "student_1"
        )

        assert retrieved is not None
        assert retrieved.analysis_id == created.analysis_id
        assert retrieved.student_uid == created.student_uid
        assert len(retrieved.recommendations) == len(created.recommendations)

    def test_retrieve_wrong_owner(self, services, fake_firebase):
        """Test that students cannot retrieve others' recommendations."""
        # Create a recommendation for student_1
        created = services["recommendation_service"].create_recommendation("student_1")

        # Try to retrieve as student_2
        result = services["recommendation_service"].get_recommendation(
            created.analysis_id, "student_2"
        )

        assert result is None

    def test_retrieve_nonexistent(self, services):
        """Test retrieving a non-existent recommendation."""
        result = services["recommendation_service"].get_recommendation(
            "nonexistent-id", "student_1"
        )
        assert result is None

    def test_unknown_student_raises(self, services):
        """Test that unknown student raises StudentNotFoundError."""
        with pytest.raises(StudentNotFoundError):
            services["recommendation_service"].create_recommendation("unknown_student")

    def test_no_eligible_options_returns_empty(self, services, fake_firebase):
        """Test that no eligible options returns empty result when no KB options match type."""
        # Save original KB options
        original_kb = fake_firebase.kb_options

        # Set empty KB for secondary branches (student_low is year 1)
        fake_firebase.students["student_low"] = {
            "uid": "student_low",
            "school_year": 1,
            "current_branch": None,
            "wilaya": "Alger",
            "grades": {"math": 5.0},
            "free_text_answers": {"q1": "I like literature"},
        }
        # Empty KB - no options at all
        fake_firebase.kb_options = []

        result = services["recommendation_service"].create_recommendation("student_low")

        assert result.student_uid == "student_low"
        assert result.recommendations == []
        # Restore original KB
        fake_firebase.kb_options = original_kb
        # Models should not be called when no eligible options
        assert services["ai_provider"].model_one_call_count == 0
        assert services["ai_provider"].model_two_call_count == 0

    def test_ownership_enforcement_on_results(self, services, fake_firebase):
        """Test that results are only accessible by their owner."""
        # Create recommendations for two students
        result1 = services["recommendation_service"].create_recommendation("student_1")

        # student_2 should not be able to access student_1's result
        retrieved = services["recommendation_service"].get_recommendation(
            result1.analysis_id, "student_2"
        )
        assert retrieved is None

        # student_1 should be able to access their own result
        retrieved = services["recommendation_service"].get_recommendation(
            result1.analysis_id, "student_1"
        )
        assert retrieved is not None
