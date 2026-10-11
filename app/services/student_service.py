"""
NaviStudo Backend - Student Service.

Handles retrieval and validation of student profiles from Firebase.
"""

from typing import Any
from dataclasses import dataclass


@dataclass
class StudentProfile:
    """Structured student profile from Firebase.

    Fields will be finalized when the Firestore schema is confirmed.
    This is a placeholder with expected common fields.
    """

    uid: str
    school_year: int  # 1, 2, or 3
    current_branch: str | None = None  # e.g., "sciences", "maths", "lettres"
    wilaya: str | None = None
    grades: dict[str, float] | None = None  # subject -> grade
    free_text_answers: dict[str, str] | None = None  # question_id -> answer
    # Additional fields as needed
    raw_data: dict[str, Any] | None = None


class StudentService:
    """Service for fetching student profiles from Firebase.

    All Firebase access goes through this service.
    """

    def __init__(self, firebase_client):
        """Initialize with a Firebase client instance.

        Args:
            firebase_client: An instance of FirebaseClient (from integrations.firebase_client).
        """
        self._firebase = firebase_client

    def get_student_profile(self, uid: str) -> StudentProfile:
        """Fetch a student's complete profile by UID.

        Args:
            uid: Firebase Auth UID of the student.

        Returns:
            StudentProfile with all available data.

        Raises:
            StudentNotFoundError: If no profile exists for the UID.
            FirebaseError: If Firebase is unavailable or returns an error.
        """
        # TODO: Implement when Firebase schema is confirmed
        # Expected flow:
        # 1. Fetch document from 'students' collection (or equivalent)
        # 2. Map Firestore document to StudentProfile
        # 3. Handle missing document gracefully
        raise NotImplementedError(
            "StudentService.get_student_profile not yet implemented. "
            "Waiting for Firebase schema confirmation."
        )

    def get_free_text_answers(self, uid: str) -> dict[str, str]:
        """Extract only the free-text answers from a student's profile.

        Args:
            uid: Firebase Auth UID of the student.

        Returns:
            Dict mapping question_id -> free-text answer string.
        """
        # TODO: Implement when Firebase schema is confirmed
        # Can be optimized to fetch only the free-text fields if needed
        profile = self.get_student_profile(uid)
        return profile.free_text_answers or {}

    def get_structured_profile(self, uid: str) -> dict[str, Any]:
        """Get the student's structured profile (excluding free-text answers).

        Args:
            uid: Firebase Auth UID of the student.

        Returns:
            Dict with structured profile data suitable for Model 2 input.
        """
        # TODO: Implement when Firebase schema is confirmed
        # Should exclude free_text_answers, include everything else
        profile = self.get_student_profile(uid)
        data = profile.raw_data or {}
        data.pop("free_text_answers", None)
        return data


class StudentNotFoundError(Exception):
    """Raised when a student profile is not found in Firebase."""

    def __init__(self, uid: str):
        self.uid = uid
        super().__init__(f"Student profile not found for UID: {uid}")


class FirebaseError(Exception):
    """Raised when Firebase operations fail."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.original_error = original_error
        super().__init__(message)