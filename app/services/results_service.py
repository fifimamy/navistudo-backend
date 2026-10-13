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

    def save(self, result: StoredRecommendationResult) -> None:
        """Save a recommendation result.

        Args:
            result: The result to persist.

        Raises:
            FirebaseError: If the write operation fails.
        """
        result_data = {
            "analysis_id": result.analysis_id,
            "student_uid": result.student_uid,
            "recommendation_type": result.recommendation_type,
            "recommendations": result.recommendations,
            "created_at": result.created_at.isoformat() if isinstance(result.created_at, datetime) else result.created_at,
            "model_one_metadata": result.model_one_metadata,
            "model_two_metadata": result.model_two_metadata,
            "model_one_raw_output": result.model_one_raw_output,
            "model_two_raw_output": result.model_two_raw_output,
        }
        self._firebase.save_recommendation_result(result_data)

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
        data = self._firebase.get_recommendation_result(analysis_id, student_uid)
        if data is None:
            return None

        # Convert back to StoredRecommendationResult
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return StoredRecommendationResult(
            analysis_id=data.get("analysis_id", analysis_id),
            student_uid=data.get("student_uid", student_uid),
            recommendation_type=data.get("recommendation_type", ""),
            recommendations=data.get("recommendations", []),
            created_at=created_at or datetime.utcnow(),
            model_one_metadata=data.get("model_one_metadata"),
            model_two_metadata=data.get("model_two_metadata"),
            model_one_raw_output=data.get("model_one_raw_output"),
            model_two_raw_output=data.get("model_two_raw_output"),
        )

    def list_for_student(self, student_uid: str, limit: int = 10) -> list[StoredRecommendationResult]:
        """List recent recommendation results for a student.

        Args:
            student_uid: The student's UID.
            limit: Maximum number of results to return.

        Returns:
            List of results, most recent first.

        Raises:
            FirebaseError: If the read operation fails.
        """
        results_data = self._firebase.list_recommendation_results(student_uid, limit)
        results = []
        for data in results_data:
            created_at = data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            results.append(StoredRecommendationResult(
                analysis_id=data.get("analysis_id", ""),
                student_uid=data.get("student_uid", student_uid),
                recommendation_type=data.get("recommendation_type", ""),
                recommendations=data.get("recommendations", []),
                created_at=created_at or datetime.utcnow(),
                model_one_metadata=data.get("model_one_metadata"),
                model_two_metadata=data.get("model_two_metadata"),
                model_one_raw_output=data.get("model_one_raw_output"),
                model_two_raw_output=data.get("model_two_raw_output"),
            ))
        return results