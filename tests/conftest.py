"""
NaviStudo Backend - Pytest configuration and fixtures.
"""

import pytest

from app import create_app
from app.config import TestingConfig


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