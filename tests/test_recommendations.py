"""
NaviStudo Backend - Tests for recommendations endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestRecommendationsEndpoint:
    """Tests for POST /api/v1/recommendations."""

    def _auth_headers(self):
        """Helper to return valid auth headers with mocked Firebase."""
        return {"Authorization": "Bearer valid_token"}

    def test_create_recommendation_missing_auth(self, client):
        """Request without Authorization header returns 401."""
        response = client.post("/api/v1/recommendations", json={})
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "unauthorized"

    def test_create_recommendation_invalid_auth_format(self, client):
        """Request with malformed Authorization header returns 400."""
        response = client.post(
            "/api/v1/recommendations",
            json={},
            headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "bad_request"

    def test_create_recommendation_invalid_token(self, client):
        """Request with invalid token returns 401."""
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.verify_id_token.side_effect = Exception("Invalid token")
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/v1/recommendations",
                json={},
                headers={"Authorization": "Bearer invalid_token"}
            )
            assert response.status_code == 401
            data = response.get_json()
            assert data["error"] == "unauthorized"

    def test_create_recommendation_firebase_not_configured(self, client):
        """Request when Firebase is not configured returns 401/503."""
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client:
            from app.integrations.firebase_client import FirebaseConfigError
            mock_get_client.side_effect = FirebaseConfigError("Not configured")

            response = client.post(
                "/api/v1/recommendations",
                json={},
                headers={"Authorization": "Bearer some_token"}
            )
            assert response.status_code in (401, 503)

    def test_create_recommendation_student_not_found(self, client):
        """Request for non-existent student returns 404."""
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client, \
             patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:

            # Mock Firebase auth
            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            # Mock service to raise StudentNotFoundError
            from app.services.recommendation_service import StudentNotFoundError
            mock_service = Mock()
            mock_service.create_recommendation.side_effect = StudentNotFoundError("uid123")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/recommendations",
                json={},
                headers={"Authorization": "Bearer valid_token"}
            )
            assert response.status_code == 404

    def test_create_recommendation_model_one_unavailable(self, client):
        """Request when Model 1 is not implemented returns 503."""
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client, \
             patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:

            # Mock Firebase auth
            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            # Mock service to raise ModelOneError
            from app.services.recommendation_service import ModelOneError
            mock_service = Mock()
            mock_service.create_recommendation.side_effect = ModelOneError("Model 1 not implemented")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/recommendations",
                json={},
                headers={"Authorization": "Bearer valid_token"}
            )
            assert response.status_code == 503
            data = response.get_json()
            assert data["error"] == "model_one_unavailable"

    def test_create_recommendation_model_two_unavailable(self, client):
        """Request when Model 2 is not implemented returns 503."""
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client, \
             patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:

            # Mock Firebase auth
            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            # Mock service to raise ModelTwoError
            from app.services.recommendation_service import ModelTwoError
            mock_service = Mock()
            mock_service.create_recommendation.side_effect = ModelTwoError("Model 2 not implemented")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/recommendations",
                json={},
                headers={"Authorization": "Bearer valid_token"}
            )
            assert response.status_code == 503
            data = response.get_json()
            assert data["error"] == "model_two_unavailable"

    def test_create_recommendation_validation_failed(self, client):
        """Request when Model 2 returns invalid option IDs returns 500."""
        with patch("app.routes.recommendations.get_firebase_client") as mock_get_client, \
             patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:

            # Mock Firebase auth
            mock_client = Mock()
            mock_client.verify_id_token.return_value = {"uid": "uid123"}
            mock_get_client.return_value = mock_client

            # Mock service to raise ValidationError
            from app.services.recommendation_service import ValidationError
            mock_service = Mock()
            mock_service.create_recommendation.side_effect = ValidationError("Invalid option_id")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/recommendations",
                json={},
                headers={"Authorization": "Bearer valid_token"}
            )
            assert response.status_code == 500
            data = response.get_json()
            assert data["error"] == "validation_failed"


class TestGetRecommendationEndpoint:
    """Tests for GET /api/v1/recommendations/<analysis_id>."""

    def test_get_recommendation_missing_auth(self, client):
        """Request without Authorization header returns 401."""
        response = client.get("/api/v1/recommendations/analysis123")
        assert response.status_code == 401

    def test_get_recommendation_not_found(self, client):
        """GET endpoint returns 404 when analysis doesn't exist or doesn't belong to student."""
        with patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:
            # Mock Firebase auth via the existing mechanism
            with patch("app.routes.recommendations.get_firebase_client") as mock_get_client:
                mock_client = Mock()
                mock_client.verify_id_token.return_value = {"uid": "student123"}
                mock_get_client.return_value = mock_client

                # Mock service to return None (not found)
                mock_service = Mock()
                mock_service.get_recommendation.return_value = None
                mock_get_service.return_value = mock_service

                response = client.get(
                    "/api/v1/recommendations/analysis123",
                    headers={"Authorization": "Bearer valid_token"}
                )
                assert response.status_code == 404
                data = response.get_json()
                assert data["error"] == "not_found"

    def test_get_recommendation_success(self, client):
        """GET endpoint returns 200 with recommendation data when found."""
        from datetime import datetime
        with patch("app.routes.recommendations._get_recommendation_service") as mock_get_service:
            with patch("app.routes.recommendations.get_firebase_client") as mock_get_client:
                mock_client = Mock()
                mock_client.verify_id_token.return_value = {"uid": "student123"}
                mock_get_client.return_value = mock_client

                # Mock service to return a valid result
                from app.services.recommendation_service import RecommendationResult
                mock_result = RecommendationResult(
                    analysis_id="analysis123",
                    student_uid="student123",
                    recommendation_type="university_major",
                    recommendations=[{"id": "opt1", "name": "Test Major", "rank": 1, "reasoning": "Good fit"}],
                    created_at=datetime.utcnow(),
                    model_one_metadata={"model": "test"},
                    model_two_metadata={"model": "test"},
                )
                mock_service = Mock()
                mock_service.get_recommendation.return_value = mock_result
                mock_get_service.return_value = mock_service

                response = client.get(
                    "/api/v1/recommendations/analysis123",
                    headers={"Authorization": "Bearer valid_token"}
                )
                assert response.status_code == 200
                data = response.get_json()
                assert data["analysis_id"] == "analysis123"
                assert data["recommendation_type"] == "university_major"
                assert len(data["recommendations"]) == 1
                assert data["recommendations"][0]["id"] == "opt1"


class TestHealthEndpointStillWorks:
    """Ensure existing health endpoint still works after changes."""

    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_correct_json(self, client):
        response = client.get("/api/v1/health")
        assert response.is_json
        data = response.get_json()
        assert data == {"status": "ok"}