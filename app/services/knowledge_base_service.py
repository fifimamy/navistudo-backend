"""
NaviStudo Backend - Knowledge Base Service.

Handles retrieval and filtering of academic options (branches/majors) from Firebase.
Eligibility rules are applied here, NOT delegated to AI models.
"""

from typing import Any
from dataclasses import dataclass
from enum import Enum


class RecommendationType(str, Enum):
    """Type of recommendation based on student's school year."""

    SECONDARY_BRANCH = "secondary_branch"  # Year 1 students -> secondary branches
    UNIVERSITY_MAJOR = "university_major"  # Year 3 students -> university majors
    # Year 2 is out of MVP scope


@dataclass
class KnowledgeBaseOption:
    """An academic option from the knowledge base.

    Fields will be finalized when the knowledge base schema is confirmed.
    """

    id: str
    name: str
    type: RecommendationType
    description: str | None = None
    # Eligibility criteria (examples - will be adjusted to match KB schema)
    required_branches: list[str] | None = None  # e.g., ["sciences", "maths"]
    required_wilayas: list[str] | None = None
    min_grades: dict[str, float] | None = None  # subject -> minimum grade
    max_capacity: int | None = None
    # Additional metadata
    raw_data: dict[str, Any] | None = None


class KnowledgeBaseService:
    """Service for fetching and filtering knowledge-base options.

    All eligibility filtering logic lives here, not in AI models.
    """

    def __init__(self, firebase_client):
        """Initialize with a Firebase client instance.

        Args:
            firebase_client: An instance of FirebaseClient (from integrations.firebase_client).
        """
        self._firebase = firebase_client

    def get_all_options(self, recommendation_type: RecommendationType) -> list[KnowledgeBaseOption]:
        """Fetch all options of a given type from the knowledge base.

        Args:
            recommendation_type: SECONDARY_BRANCH or UNIVERSITY_MAJOR.

        Returns:
            List of all KnowledgeBaseOption objects of that type.

        Raises:
            FirebaseError: If Firebase is unavailable or returns an error.
        """
        # TODO: Implement when knowledge base schema is confirmed
        # Expected flow:
        # 1. Query Firestore collection for options matching recommendation_type
        # 2. Map documents to KnowledgeBaseOption objects
        raise NotImplementedError(
            "KnowledgeBaseService.get_all_options not yet implemented. "
            "Waiting for knowledge base schema confirmation."
        )

    def filter_eligible_options(
        self,
        student_profile: dict[str, Any],
        recommendation_type: RecommendationType,
    ) -> list[KnowledgeBaseOption]:
        """Filter knowledge-base options by student eligibility.

        This is the authoritative eligibility check. AI models must NOT
        be responsible for enforcing eligibility rules.

        Args:
            student_profile: Structured student profile (from StudentService).
            recommendation_type: SECONDARY_BRANCH or UNIVERSITY_MAJOR.

        Returns:
            List of options the student is eligible for.
        """
        all_options = self.get_all_options(recommendation_type)
        eligible = []

        for option in all_options:
            if self._is_eligible(student_profile, option):
                eligible.append(option)

        return eligible

    def _is_eligible(self, student_profile: dict[str, Any], option: KnowledgeBaseOption) -> bool:
        """Check if a student is eligible for a specific option.

        Args:
            student_profile: Student's structured data.
            option: The option to check eligibility for.

        Returns:
            True if eligible, False otherwise.
        """
        # Branch requirement check
        if option.required_branches:
            student_branch = student_profile.get("current_branch")
            if student_branch not in option.required_branches:
                return False

        # Wilaya requirement check
        if option.required_wilayas:
            student_wilaya = student_profile.get("wilaya")
            if student_wilaya not in option.required_wilayas:
                return False

        # Minimum grade requirements
        if option.min_grades:
            student_grades = student_profile.get("grades", {})
            for subject, min_grade in option.min_grades.items():
                if student_grades.get(subject, 0) < min_grade:
                    return False

        # Additional eligibility rules can be added here as needed
        # (capacity, quotas, etc.)

        return True

    def get_option_by_id(self, option_id: str) -> KnowledgeBaseOption | None:
        """Fetch a single option by ID for validation.

        Args:
            option_id: Unique identifier of the option.

        Returns:
            KnowledgeBaseOption if found, None otherwise.
        """
        # TODO: Implement when knowledge base schema is confirmed
        raise NotImplementedError(
            "KnowledgeBaseService.get_option_by_id not yet implemented. "
            "Waiting for knowledge base schema confirmation."
        )


class FirebaseError(Exception):
    """Raised when Firebase operations fail."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.original_error = original_error
        super().__init__(message)