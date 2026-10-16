"""
NaviStudo Backend - Tests for GET /api/v1/health/firebase.

Covers successful connectivity, Firebase initialization failure, Firestore
read failure, and guarantees that sensitive error details are never returned.
Firebase is mocked, so these tests need no real credentials or network access.
"""

from unittest.mock import MagicMock, patch

from app.integrations.firebase_client import FirebaseConfigError

FIREBASE_HEALTH_PATH = "/api/v1/health/firebase"
HEALTH_PATH = "/api/v1/health"


class TestFirebaseHealthEndpoint:
    """Tests for the read-only Firebase connectivity endpoint."""

    def test_firebase_health_success(self, client):
        """A successful read-only check returns 200 with a generic status."""
        fake_client = MagicMock()
        fake_client.check_firestore_read.return_value = True

        with patch("app.routes.health.get_firebase_client", return_value=fake_client):
            response = client.get(FIREBASE_HEALTH_PATH)

        assert response.status_code == 200
        assert response.is_json
        assert response.get_json() == {"status": "ok", "firebase": "connected"}

    def test_firebase_health_uses_bounded_timeout(self, client):
        """The connectivity check passes a short, bounded timeout."""
        fake_client = MagicMock()
        fake_client.check_firestore_read.return_value = True

        with patch("app.routes.health.get_firebase_client", return_value=fake_client):
            client.get(FIREBASE_HEALTH_PATH)

        fake_client.check_firestore_read.assert_called_once()
        _, kwargs = fake_client.check_firestore_read.call_args
        assert kwargs.get("timeout") is not None
        assert 0 < kwargs["timeout"] <= 10

    def test_firebase_health_initialization_failure(self, client):
        """Missing/invalid credentials return a non-200 generic error."""
        with patch(
            "app.routes.health.get_firebase_client",
            side_effect=FirebaseConfigError("credentials not configured"),
        ):
            response = client.get(FIREBASE_HEALTH_PATH)

        assert response.status_code == 503
        assert response.get_json() == {"status": "error", "firebase": "unavailable"}

    def test_firebase_health_read_failure(self, client):
        """A Firestore read failure returns a non-200 generic error."""
        fake_client = MagicMock()
        fake_client.check_firestore_read.side_effect = Exception(
            "permission denied on projects/secret-project"
        )

        with patch("app.routes.health.get_firebase_client", return_value=fake_client):
            response = client.get(FIREBASE_HEALTH_PATH)

        assert response.status_code == 503
        assert response.get_json() == {"status": "error", "firebase": "unavailable"}

    def test_firebase_health_does_not_leak_error_details(self, client):
        """Sensitive exception details are never returned to the client."""
        secret_marker = "SUPER_SECRET_ERROR_DETAIL_12345"
        fake_client = MagicMock()
        fake_client.check_firestore_read.side_effect = Exception(
            f"Firebase Admin failed: {secret_marker} "
            "private_key=-----BEGIN PRIVATE KEY----- token=abc.def.ghi"
        )

        with patch("app.routes.health.get_firebase_client", return_value=fake_client):
            response = client.get(FIREBASE_HEALTH_PATH)

        body = response.get_data(as_text=True)
        assert response.status_code == 503
        assert secret_marker not in body
        assert "private_key" not in body
        assert "BEGIN PRIVATE KEY" not in body
        # The response contains only the generic status fields.
        assert response.get_json() == {"status": "error", "firebase": "unavailable"}

    def test_firebase_health_does_not_leak_credentials_on_init_failure(self, client):
        """Credential-like strings in init errors are never returned."""
        with patch(
            "app.routes.health.get_firebase_client",
            side_effect=FirebaseConfigError(
                "invalid client_email=foo@bar.iam.gserviceaccount.com"
            ),
        ):
            response = client.get(FIREBASE_HEALTH_PATH)

        body = response.get_data(as_text=True)
        assert response.status_code == 503
        assert "gserviceaccount.com" not in body
        assert "client_email" not in body


class TestExistingHealthEndpointUnchanged:
    """The existing liveness endpoint must keep its exact behaviour."""

    def test_health_returns_200_and_ok(self, client):
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}

    def test_health_does_not_touch_firebase(self, client):
        """The liveness endpoint must not call Firebase at all."""
        with patch("app.routes.health.get_firebase_client") as mock_get_client:
            response = client.get(HEALTH_PATH)

        assert response.status_code == 200
        mock_get_client.assert_not_called()
