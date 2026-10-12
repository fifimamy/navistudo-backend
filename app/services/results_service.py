"""
NaviStudo Backend - Results Service.

Handles persistence and retrieval of recommendation analysis results.
Separate from RecommendationService to keep concerns isolated.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from app.integrations.firebase_client import FirebaseClient
from app.exceptions import FirebaseError, ServiceNotImplementedError


@dataclass
class StoredRecommendationResult:
    """A recommendation result as stored in Firebase."""

    analysis_id: str
    student_uid: str
    recommendation_type: str
    recommendations: list[dict[str, Any]]
    created_at: datetime
    model_one_metadata: dict[str, Any] | None
    model_two_metadata: dict[str, Any] | None
    # Raw model outputs for debugging/auditing
    model_one_raw_output: dict[str, Any] | None = None
    model_two_raw_output: dict[str, Any] | None = None


class ResultsService:
    """Service for saving and retrieving recommendation results."""

    def __init__(self, firebase_client: FirebaseClient):
        self._firebase = firebase_client
        self._collection = "recommendation_results"  # TODO: confirm collection name

    def save(self, result: StoredRecommendationResult) -> None:
        """Save a recommendation result.

        Args:
            result: The result to persist.

        Raises:
            FirebaseError: If the write operation fails.
        """
        # TODO: Implement when Firebase schema is confirmed
        # Expected:
        # doc_ref = self._firebase.db.collection(self._collection).document(result.analysis_id)
        # doc_ref.set(result.__dict__)
        raise ServiceNotImplementedError(
            "ResultsService.save not yet implemented. "
            "Waiting for Firebase results collection schema confirmation."
        )

    def get(self, analysis_id: str, student_uid: str) -> StoredRecommendationResult | None:
        """Retrieve a recommendation result by ID, verifying ownership.

        Args:
            analysis_id: The analysis ID to retrieve.
            student_uid: The student's UID (must match the stored result).

        Returns:
            StoredRecommendationResult if found and owned by student, None otherwise.

        Raises:
            FirebaseError: If the read operation fails.
        """
        # TODO: Implement when Firebase schema is confirmed
        # Expected:
        # doc = self._firebase.db.collection(self._collection).document(analysis_id).get()
        # if not doc.exists: return None
        # data = doc.to_dict()
        # if data.get("student_uid") != student_uid: return None
        # return StoredRecommendationResult(**data)
        raise ServiceNotImplementedError(
            "ResultsService.get not yet implemented. "
            "Waiting for Firebase results collection schema confirmation."
        )

    def list_for_student(self, student_uid: str, limit: int = 10) -> list[StoredRecommendationResult]:
        """List recent recommendation results for a student.

        Args:
            student_uid: The student's UID.
            limit: Maximum number of results to return.

        Returns:
            List of results, most recent first.
        """
        # TODO: Implement when Firebase schema is confirmed
        raise ServiceNotImplementedError(
            "ResultsService.list_for_student not yet implemented. "
            "Waiting for Firebase results collection schema confirmation."
        )