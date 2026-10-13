"""
NaviStudo Backend - Knowledge Base Service.

Handles retrieval and filtering of academic options (branches/majors) from Firebase.
Eligibility rules are applied here, NOT delegated to AI models.
"""

from typing import Any
from dataclasses import dataclass
from enum import Enum

from app.exceptions import FirebaseError, ServiceNotImplementedError
from app.integrations.firebase_client import FirebaseClient


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

    def __init__(self, firebase_client: FirebaseClient):
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
        options_data = self._firebase.get_knowledge_base_options(recommendation_type.value)
        options = []
        for data in options_data:
            # Convert Firestore data to KnowledgeBaseOption
            # Handle the type field - it comes as string from Firestore
            type_str = data.get("type", recommendation_type.value)
            try:
                opt_type = RecommendationType(type_str)
            except ValueError:
                opt_type = recommendation_type

            option = KnowledgeBaseOption(
                id=data.get("id", ""),
                name=data.get("name", ""),
                type=opt_type,
                description=data.get("description"),
                required_branches=data.get("required_branches"),
                required_wilayas=data.get("required_wilayas"),
                min_grades=data.get("min_grades"),
                max_capacity=data.get("max_capacity"),
                raw_data=data,
            )
            options.append(option)
        return options

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
            student_grades = student_profile.get("grades") or {}
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

        Raises:
            FirebaseError: If Firebase is unavailable or returns an error.
        """
        data = self._firebase.get_knowledge_base_option_by_id(option_id)
        if data is None:
            return None

        type_str = data.get("type", "")
        try:
            opt_type = RecommendationType(type_str)
        except ValueError:
            # Default to UNIVERSITY_MAJOR if type is invalid
            opt_type = RecommendationType.UNIVERSITY_MAJOR

        return KnowledgeBaseOption(
            id=data.get("id", option_id),
            name=data.get("name", ""),
            type=opt_type,
            description=data.get("description"),
            required_branches=data.get("required_branches"),
            required_wilayas=data.get("required_wilayas"),
            min_grades=data.get("min_grades"),
            max_capacity=data.get("max_capacity"),
            raw_data=data,
        )