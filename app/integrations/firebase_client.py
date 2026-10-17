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
from google.cloud.firestore_v1 import FieldFilter


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

    # ============================================================
    # Firestore operations - Student profiles
    # ============================================================
    # Collection names - to be confirmed with team
    STUDENTS_COLLECTION = os.environ.get("FIRESTORE_STUDENTS_COLLECTION", "students")
    KNOWLEDGE_BASE_COLLECTION = os.environ.get("FIRESTORE_KB_COLLECTION", "knowledge_base")
    RESULTS_COLLECTION = os.environ.get("FIRESTORE_RESULTS_COLLECTION", "recommendation_results")

    def get_student_profile(self, uid: str) -> dict[str, Any] | None:
        """Fetch a student's profile from Firestore.

        Args:
            uid: Firebase Auth UID of the student.

        Returns:
            Student profile dict if found, None otherwise.

        Raises:
            FirebaseError: If Firestore operation fails.
        """
        try:
            doc_ref = self._db.collection(self.STUDENTS_COLLECTION).document(uid)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return doc.to_dict()
        except Exception as e:
            raise FirebaseError(f"Failed to fetch student profile for UID {uid}: {e}") from e

    def get_student_free_text_answers(self, uid: str) -> dict[str, str] | None:
        """Fetch only the free-text answers from a student's profile.

        Args:
            uid: Firebase Auth UID of the student.

        Returns:
            Dict mapping question_id -> free-text answer string, or None if not found.

        Raises:
            FirebaseError: If Firestore operation fails.
        """
        try:
            doc_ref = self._db.collection(self.STUDENTS_COLLECTION).document(uid)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            return data.get("free_text_answers") if data else None
        except Exception as e:
            raise FirebaseError(f"Failed to fetch free-text answers for UID {uid}: {e}") from e

    def save_student_profile(self, uid: str, profile_data: dict[str, Any]) -> str:
        """Create or update a student profile document.

        Args:
            uid: Firebase Auth UID of the student (used as the document ID).
            profile_data: Profile fields to persist (see ``to_student_document``).

        Returns:
            The UID of the saved profile.

        Raises:
            FirebaseError: If the write operation fails.
        """
        try:
            doc_ref = self._db.collection(self.STUDENTS_COLLECTION).document(uid)
            doc_ref.set(profile_data, merge=True)
            return uid
        except Exception as e:
            raise FirebaseError(f"Failed to save student profile for UID {uid}: {e}") from e

    # ============================================================
    # Firestore connectivity check (read-only)
    # ============================================================

    # Sentinel document used only for the connectivity check. It is never
    # written: reading a non-existent document is a single read with no side
    # effects and no dependency on application data.
    # NOTE: Firestore reserves IDs that begin AND end with "__", so the
    # sentinel must not use leading/trailing double underscores.
    HEALTH_CHECK_DOCUMENT_ID = "navistudo_health_check"

    def check_firestore_read(self, timeout: float = 5.0) -> bool:
        """Perform a minimal, read-only Firestore connectivity check.

        Reads a single (never-written) document from the students collection.
        This is one document read — not a collection scan — and it creates,
        updates, or deletes nothing.

        Args:
            timeout: Per-call timeout in seconds, passed to the Firestore SDK.

        Returns:
            True if the read completed successfully.

        Raises:
            Exception: If Firebase Admin is not initialized or the read fails.
        """
        doc_ref = self._db.collection(self.STUDENTS_COLLECTION).document(
            self.HEALTH_CHECK_DOCUMENT_ID
        )
        doc_ref.get(timeout=timeout)
        return True

    # ============================================================
    # Firestore operations - Knowledge base
    # ============================================================

    def get_knowledge_base_options(self, recommendation_type: str) -> list[dict[str, Any]]:
        """Fetch all knowledge-base options of a given type.

        Args:
            recommendation_type: "secondary_branch" or "university_major".

        Returns:
            List of option dicts.

        Raises:
            FirebaseError: If Firestore operation fails.
        """
        try:
            query = (self._db.collection(self.KNOWLEDGE_BASE_COLLECTION)
                     .where(filter=FieldFilter("type", "==", recommendation_type)))
            docs = query.stream()
            options = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                options.append(data)
            return options
        except Exception as e:
            raise FirebaseError(f"Failed to fetch knowledge base options for type {recommendation_type}: {e}") from e

    def get_knowledge_base_option_by_id(self, option_id: str) -> dict[str, Any] | None:
        """Fetch a single knowledge-base option by ID.

        Args:
            option_id: Unique identifier of the option.

        Returns:
            Option dict if found, None otherwise.

        Raises:
            FirebaseError: If Firestore operation fails.
        """
        try:
            doc_ref = self._db.collection(self.KNOWLEDGE_BASE_COLLECTION).document(option_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        except Exception as e:
            raise FirebaseError(f"Failed to fetch knowledge base option {option_id}: {e}") from e

    # ============================================================
    # Firestore operations - Recommendation results
    # ============================================================

    def save_recommendation_result(self, result_data: dict[str, Any]) -> str:
        """Save a recommendation result to Firestore.

        Args:
            result_data: The result data to persist (must include 'analysis_id' and 'student_uid').

        Returns:
            The analysis_id of the saved result.

        Raises:
            FirebaseError: If Firestore operation fails.
        """
        try:
            analysis_id = result_data["analysis_id"]
            doc_ref = self._db.collection(self.RESULTS_COLLECTION).document(analysis_id)
            doc_ref.set(result_data)
            return analysis_id
        except KeyError as e:
            raise FirebaseError(f"Missing required field in result data: {e}") from e
        except Exception as e:
            raise FirebaseError(f"Failed to save recommendation result: {e}") from e

    def get_recommendation_result(self, analysis_id: str, student_uid: str) -> dict[str, Any] | None:
        """Retrieve a recommendation result by ID, verifying ownership.

        Args:
            analysis_id: The analysis ID to retrieve.
            student_uid: The student's UID (must match the stored result).

        Returns:
            Result dict if found and owned by student, None otherwise.

        Raises:
            FirebaseError: If Firestore operation fails.
        """
        try:
            doc_ref = self._db.collection(self.RESULTS_COLLECTION).document(analysis_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            # Verify ownership
            if data.get("student_uid") != student_uid:
                return None
            return data
        except Exception as e:
            raise FirebaseError(f"Failed to fetch recommendation result {analysis_id}: {e}") from e

    def list_recommendation_results(self, student_uid: str, limit: int = 10) -> list[dict[str, Any]]:
        """List recent recommendation results for a student.

        Args:
            student_uid: The student's UID.
            limit: Maximum number of results to return.

        Returns:
            List of results, most recent first.

        Raises:
            FirebaseError: If Firestore operation fails.
        """
        try:
            query = (self._db.collection(self.RESULTS_COLLECTION)
                     .where(filter=FieldFilter("student_uid", "==", student_uid))
                     .order_by("created_at", direction=firestore.Query.DESCENDING)
                     .limit(limit))
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            raise FirebaseError(f"Failed to list recommendation results for UID {student_uid}: {e}") from e


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