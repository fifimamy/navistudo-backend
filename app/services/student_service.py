"""
NaviStudo Backend - Student Service.

Handles retrieval and validation of student profiles from Firebase.
"""

from typing import Any
from dataclasses import dataclass

from app.exceptions import StudentNotFoundError, FirebaseError, ServiceNotImplementedError
from app.integrations.firebase_client import FirebaseClient


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
    question_context: dict[str, str] | None = None  # question_id -> description
    # Additional fields as needed
    raw_data: dict[str, Any] | None = None


class StudentService:
    """Service for fetching student profiles from Firebase.

    All Firebase access goes through this service.
    """

    def __init__(self, firebase_client: FirebaseClient):
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
        data = self._firebase.get_student_profile(uid)
        if data is None:
            raise StudentNotFoundError(uid)

        # Extract free-text answers and question context before creating raw_data
        free_text_answers = data.get("free_text_answers")
        question_context = data.get("question_context")

        # Create raw_data for structured profile (excluding free-text fields)
        raw_data = {
            k: v
            for k, v in data.items()
            if k not in ("free_text_answers", "question_context")
        }

        return StudentProfile(
            uid=data.get("uid", uid),
            school_year=data.get("school_year"),
            current_branch=data.get("current_branch"),
            wilaya=data.get("wilaya"),
            grades=data.get("grades"),
            free_text_answers=free_text_answers,
            question_context=question_context,
            raw_data=raw_data,
        )

    def get_free_text_answers(self, uid: str) -> dict[str, str]:
        """Extract only the free-text answers from a student's profile.

        Args:
            uid: Firebase Auth UID of the student.

        Returns:
            Dict mapping question_id -> free-text answer string.

        Raises:
            StudentNotFoundError: If no profile exists for the UID.
            FirebaseError: If Firebase is unavailable or returns an error.
        """
        answers = self._firebase.get_student_free_text_answers(uid)
        if answers is None:
            raise StudentNotFoundError(uid)
        return answers or {}

    def get_structured_profile(self, uid: str) -> dict[str, Any]:
        """Get the student's structured profile (excluding free-text answers).

        Args:
            uid: Firebase Auth UID of the student.

        Returns:
            Dict with structured profile data suitable for Model 2 input.

        Raises:
            StudentNotFoundError: If no profile exists for the UID.
            FirebaseError: If Firebase is unavailable or returns an error.
        """
        profile = self.get_student_profile(uid)
        return profile.raw_data or {}

    def save_profile(self, uid: str, profile_data: dict[str, Any]) -> str:
        """Persist a student profile document (create or update).

        Args:
            uid: Firebase Auth UID of the student (used as the document ID).
            profile_data: Profile fields to persist.

        Returns:
            The UID of the saved profile.

        Raises:
            FirebaseError: If Firebase is unavailable or returns an error.
        """
        return self._firebase.save_student_profile(uid, profile_data)