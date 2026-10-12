"""
NaviStudo Backend - Pytest configuration and fixtures.
"""

import pytest

from app import create_app
from app.config import TestingConfig
from app.services.recommendation_service import RecommendationService

from tests.fakes import (
    FAKE_UID,
    FakeKnowledgeBaseService,
    FakeModelOneClient,
    FakeModelTwoClient,
    FakeStudentService,
    make_fake_kb_options,
    make_fake_student_profile,
)


@pytest.fixture
def app():
    """Create a Flask app configured for testing."""
    app = create_app(TestingConfig)
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Fakes for pipeline tests (no Firebase, no real AI)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_uid():
    return FAKE_UID


@pytest.fixture
def fake_student_profile():
    """Default fake year-3 student (branch fake_branch_x, fake grades)."""
    return make_fake_student_profile()


@pytest.fixture
def fake_kb_options():
    """Five fake majors; three are eligible for the default fake student."""
    return make_fake_kb_options()


@pytest.fixture
def make_service(monkeypatch, fake_student_profile, fake_kb_options):
    """Factory that builds a RecommendationService wired with fakes.

    Usage in a test:
        service, model_one, model_two = make_service(model_two="unknown_id")
        result = service.create_recommendation(fake_uid)

    Scenarios: see FakeModelOneClient.SCENARIOS / FakeModelTwoClient.SCENARIOS.
    Pass profiles=[...] or options=[...] to override the default fake data.
    """
    # RecommendationService._save_result is not implemented yet (it raises
    # NotImplementedError). Replace it with a no-op so the full flow can run.
    # TODO: remove this patch once persistence is implemented.
    monkeypatch.setattr(RecommendationService, "_save_result", lambda self, result: None)

    def _make(model_one="ok", model_two="valid", profiles=None, options=None):
        model_one_client = FakeModelOneClient(model_one)
        model_two_client = FakeModelTwoClient(model_two)
        service = RecommendationService(
            student_service=FakeStudentService(profiles if profiles is not None else [fake_student_profile]),
            kb_service=FakeKnowledgeBaseService(options if options is not None else fake_kb_options),
            model_one=model_one_client,
            model_two=model_two_client,
            firebase_client=None,
        )
        return service, model_one_client, model_two_client

    return _make


@pytest.fixture
def recommendation_service(make_service):
    """Service with all-happy-path fakes."""
    service, _, _ = make_service()
    return service
