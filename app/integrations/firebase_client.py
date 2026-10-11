"""
NaviStudo Backend - Firebase Client.

Provides initialized Firebase Admin SDK access for authenticated operations.
All Firebase configuration via environment variables - no committed secrets.
"""

import os
from typing import Any
from functools import lru_cache

import firebase_admin
from firebase_admin import auth, credentials, firestore


class FirebaseClient:
    """Wrapper for Firebase Admin SDK with explicit initialization.

    Usage:
        client = FirebaseClient()
        # Verify token
        decoded_token = client.verify_id_token(id_token)
        # Access Firestore
        doc = client.db.collection("students").document(uid).get()
    """

    def __init__(self):
        """Initialize Firebase Admin SDK if not already initialized."""
        self._app = self._get_or_initialize_app()
        self._db = firestore.client(app=self._app)

    @property
    def db(self) -> firestore.Client:
        """Get the Firestore client for database operations."""
        return self._db

    @property
    def app(self) -> firebase_admin.App:
        """Get the underlying Firebase App instance."""
        return self._app

    def verify_id_token(self, id_token: str) -> dict[str, Any]:
        """Verify a Firebase ID token and return decoded claims.

        Args:
            id_token: The ID token string from the client (Authorization header).

        Returns:
            Dict containing decoded token claims (including 'uid').

        Raises:
            FirebaseAuthError: If token is invalid, expired, or verification fails.
        """
        try:
            decoded_token = auth.verify_id_token(id_token, app=self._app)
            return decoded_token
        except auth.InvalidIdTokenError as e:
            raise FirebaseAuthError(f"Invalid ID token: {e}") from e
        except auth.ExpiredIdTokenError as e:
            raise FirebaseAuthError(f"Expired ID token: {e}") from e
        except Exception as e:
            raise FirebaseAuthError(f"Token verification failed: {e}") from e

    def _get_or_initialize_app(self) -> firebase_admin.App:
        """Get existing Firebase app or initialize a new one.

        Initialization uses environment variables for credentials.
        Required env vars:
            - FIREBASE_PROJECT_ID
            - FIREBASE_CLIENT_EMAIL
            - FIREBASE_PRIVATE_KEY (with literal \\n newlines)
        Or: GOOGLE_APPLICATION_CREDENTIALS pointing to a service account JSON file.

        Returns:
            Initialized Firebase App instance.

        Raises:
            FirebaseConfigError: If credentials are missing or invalid.
        """
        # Check if already initialized
        if firebase_admin._apps:
            return firebase_admin.get_app()

        # Try to initialize from environment variables
        cred = self._build_credentials_from_env()
        if cred:
            return firebase_admin.initialize_app(cred)

        # Fall back to GOOGLE_APPLICATION_CREDENTIALS
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            return firebase_admin.initialize_app()

        raise FirebaseConfigError(
            "Firebase credentials not configured. Set FIREBASE_PROJECT_ID, "
            "FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY environment variables, "
            "or set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON file."
        )

    def _build_credentials_from_env(self) -> credentials.Certificate | None:
        """Build Certificate credentials from environment variables.

        Returns:
            Certificate object if all required env vars are present, None otherwise.
        """
        project_id = os.environ.get("FIREBASE_PROJECT_ID")
        client_email = os.environ.get("FIREBASE_CLIENT_EMAIL")
        private_key = os.environ.get("FIREBASE_PRIVATE_KEY")

        if not all([project_id, client_email, private_key]):
            return None

        # Private key comes with literal \n newlines - convert to actual newlines
        private_key = private_key.replace("\\n", "\n")

        return credentials.Certificate({
            "type": "service_account",
            "project_id": project_id,
            "client_email": client_email,
            "private_key": private_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        })


@lru_cache(maxsize=1)
def get_firebase_client() -> FirebaseClient:
    """Get a singleton FirebaseClient instance.

    Uses lru_cache to ensure only one instance is created per process.
    Safe for use in Flask request handlers.

    Returns:
        FirebaseClient instance.

    Raises:
        FirebaseConfigError: If Firebase is not configured.
    """
    return FirebaseClient()


class FirebaseAuthError(Exception):
    """Raised when Firebase Authentication operations fail."""

    pass


class FirebaseConfigError(Exception):
    """Raised when Firebase configuration is missing or invalid."""

    pass