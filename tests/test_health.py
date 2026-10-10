"""
NaviStudo Backend - Tests for health check endpoint.
"""

import pytest


class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    def test_health_returns_200(self, client):
        """Health endpoint returns HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_correct_json(self, client):
        """Health endpoint returns correct JSON response."""
        response = client.get("/api/v1/health")
        assert response.is_json
        data = response.get_json()
        assert data == {"status": "ok"}

    def test_health_content_type(self, client):
        """Health endpoint returns application/json content type."""
        response = client.get("/api/v1/health")
        assert response.content_type == "application/json"