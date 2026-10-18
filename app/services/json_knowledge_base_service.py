"""
NaviStudo Backend - JSON Knowledge Base Service.

Production-ready knowledge base service that loads from JSON files.
Uses the KnowledgeBaseLoader for validation and cross-reference checking.

This service is used by the recommendation pipeline when Firestore is not
available for knowledge base storage, or as the primary KB source.
"""

import logging
from typing import Any

from app.services.knowledge_base_loader import KnowledgeBaseLoader, KnowledgeBaseLoadError
from app.services.knowledge_base_service import RecommendationType

logger = logging.getLogger(__name__)


class JsonKnowledgeBaseService:
    """Knowledge base service backed by JSON files.

    Loads and validates the knowledge base from JSON files using the
    KnowledgeBaseLoader. Provides the same interface as KnowledgeBaseService
    for eligibility filtering.

    Usage:
        service = JsonKnowledgeBaseService()
        eligible = service.filter_eligible_options(student_profile, RecommendationType.UNIVERSITY_MAJOR)
    """

    def __init__(self, data_dir: str | None = None):
        """Initialize with optional custom data directory.

        Args:
            data_dir: Path to knowledge_base directory. If None, uses default.
        """
        self._loader = KnowledgeBaseLoader(data_dir)
        self._collection = None

    def _ensure_loaded(self):
        """Lazy-load the knowledge base on first access."""
        if self._collection is None:
            try:
                self._collection = self._loader.load()
                logger.info(
                    "Knowledge base loaded: %d options",
                    len(self._collection.options),
                )
            except KnowledgeBaseLoadError as e:
                logger.error("Failed to load knowledge base: %s", e)
                raise

    def get_all_options(self, recommendation_type: RecommendationType) -> list[Any]:
        """Get all options of a given type from the knowledge base.

        Args:
            recommendation_type: SECONDARY_BRANCH or UNIVERSITY_MAJOR.

        Returns:
            List of KnowledgeBaseOption-like objects.

        Raises:
            KnowledgeBaseLoadError: If the knowledge base cannot be loaded.
        """
        self._ensure_loaded()
        return self._collection.get_by_type(recommendation_type)

    def filter_eligible_options(
        self,
        student_profile: dict[str, Any],
        recommendation_type: RecommendationType,
    ) -> list[Any]:
        """Filter knowledge-base options by student eligibility.

        Args:
            student_profile: Structured student profile.
            recommendation_type: SECONDARY_BRANCH or UNIVERSITY_MAJOR.

        Returns:
            List of eligible options.

        Raises:
            KnowledgeBaseLoadError: If the knowledge base cannot be loaded.
        """
        self._ensure_loaded()
        return self._collection.get_eligible_for_student(student_profile, recommendation_type)

    def get_option_by_id(self, option_id: str) -> Any | None:
        """Get a single option by ID.

        Args:
            option_id: The option ID to look up.

        Returns:
            The option if found, None otherwise.
        """
        self._ensure_loaded()
        return self._collection.get_by_id(option_id)

    @property
    def is_loaded(self) -> bool:
        """Check if the knowledge base has been loaded."""
        return self._collection is not None

    @property
    def option_count(self) -> int:
        """Get the total number of options in the knowledge base."""
        if self._collection is None:
            return 0
        return len(self._collection.options)
