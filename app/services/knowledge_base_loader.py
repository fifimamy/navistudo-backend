"""
NaviStudo Backend - Knowledge Base Data Loader.

Loads and validates the academic knowledge base from JSON files.
Provides typed access to options with full eligibility and matching metadata.
"""

import json
import os
from pathlib import Path
from typing import Any

from app.schemas.knowledge_base_schema import (
    KnowledgeBaseCollection,
    KnowledgeBaseOption,
    KnowledgeBaseEligibilityCriteria,
    KnowledgeBaseMatchingMetadata,
    KnowledgeBaseSource,
    RecommendationType,
    EligibilityStatus,
    SubjectArea,
    WilayaCode,
    SecondaryBranch,
)


class KnowledgeBaseLoadError(Exception):
    """Raised when knowledge base loading or validation fails."""

    def __init__(self, message: str, errors: list[str] | None = None):
        self.errors = errors or []
        super().__init__(message)


class KnowledgeBaseLoader:
    """Loads and validates the knowledge base from JSON files."""

    def __init__(self, data_dir: str | None = None):
        """
        Initialize the loader.

        Args:
            data_dir: Path to the knowledge base data directory.
                      Defaults to 'data/knowledge_base' relative to project root.
        """
        if data_dir is None:
            # Default to project_root/data/knowledge_base
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data" / "knowledge_base"
        self.data_dir = Path(data_dir)

    def load(self) -> KnowledgeBaseCollection:
        """
        Load the complete knowledge base from JSON files.

        Expected directory structure:
            data/knowledge_base/
            ├── secondary_branches.json
            ├── university_majors.json
            └── sources.json (optional)

        Returns:
            Validated KnowledgeBaseCollection.

        Raises:
            KnowledgeBaseLoadError: If loading or validation fails.
        """
        all_options: list[KnowledgeBaseOption] = []
        errors: list[str] = []

        # Load secondary branches
        secondary_file = self.data_dir / "secondary_branches.json"
        if secondary_file.exists():
            try:
                with open(secondary_file, "r", encoding="utf-8") as f:
                    secondary_data = json.load(f)
                for item in secondary_data.get("options", []):
                    try:
                        option = self._load_option(item, RecommendationType.SECONDARY_BRANCH)
                        all_options.append(option)
                    except Exception as e:
                        errors.append(f"Secondary branch '{item.get('id', 'unknown')}': {e}")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in secondary_branches.json: {e}")
        else:
            errors.append(f"Missing required file: {secondary_file}")

        # Load university majors
        university_file = self.data_dir / "university_majors.json"
        if university_file.exists():
            try:
                with open(university_file, "r", encoding="utf-8") as f:
                    university_data = json.load(f)
                for item in university_data.get("options", []):
                    try:
                        option = self._load_option(item, RecommendationType.UNIVERSITY_MAJOR)
                        all_options.append(option)
                    except Exception as e:
                        errors.append(f"University major '{item.get('id', 'unknown')}': {e}")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in university_majors.json: {e}")
        else:
            errors.append(f"Missing required file: {university_file}")

        if errors:
            raise KnowledgeBaseLoadError(
                f"Knowledge base validation failed with {len(errors)} error(s)",
                errors
            )

        # Load sources if available
        sources_file = self.data_dir / "sources.json"
        source_refs: list[KnowledgeBaseSource] = []
        if sources_file.exists():
            try:
                with open(sources_file, "r", encoding="utf-8") as f:
                    sources_data = json.load(f)
                for src in sources_data.get("sources", []):
                    try:
                        source_refs.append(KnowledgeBaseSource(**src))
                    except Exception as e:
                        errors.append(f"Source '{src.get('source_id', 'unknown')}': {e}")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in sources.json: {e}")

        # Create collection
        collection = KnowledgeBaseCollection(
            version="1.0.0",
            options=all_options,
        )

        # Validate cross-references
        self._validate_cross_references(collection, errors)

        if errors:
            raise KnowledgeBaseLoadError(
                f"Knowledge base cross-reference validation failed with {len(errors)} error(s)",
                errors
            )

        return collection

    def _load_option(self, data: dict[str, Any], expected_type: RecommendationType) -> KnowledgeBaseOption:
        """Load a single option with type-specific validation."""
        # Ensure type matches expected
        if data.get("type") != expected_type.value:
            raise ValueError(f"Expected type '{expected_type.value}', got '{data.get('type')}'")

        # Parse eligibility criteria
        eligibility_data = data.get("eligibility", {})
        eligibility = KnowledgeBaseEligibilityCriteria(
            required_branches=eligibility_data.get("required_branches"),
            required_branches_status=EligibilityStatus(
                eligibility_data.get("required_branches_status", "unknown")
            ),
            required_wilayas=eligibility_data.get("required_wilayas"),
            required_wilayas_status=EligibilityStatus(
                eligibility_data.get("required_wilayas_status", "unknown")
            ),
            min_grades=eligibility_data.get("min_grades"),
            min_grades_status=EligibilityStatus(
                eligibility_data.get("min_grades_status", "unknown")
            ),
            max_capacity=eligibility_data.get("max_capacity"),
            max_capacity_status=EligibilityStatus(
                eligibility_data.get("max_capacity_status", "unknown")
            ),
            additional_criteria=eligibility_data.get("additional_criteria", {}),
        )

        # Parse matching metadata
        matching_data = data.get("matching_metadata", {})
        matching_metadata = KnowledgeBaseMatchingMetadata(
            subject_relevance={
                SubjectArea(k): v for k, v in matching_data.get("subject_relevance", {}).items()
            },
            career_themes=matching_data.get("career_themes", []),
            recommended_interests=matching_data.get("recommended_interests", []),
            work_style_traits=matching_data.get("work_style_traits", []),
            difficulty_level=matching_data.get("difficulty_level"),
            selectivity_tier=matching_data.get("selectivity_tier"),
            employment_prospects=matching_data.get("employment_prospects"),
        )

        # Parse sources
        sources = [
            KnowledgeBaseSource(**src) for src in data.get("sources", [])
        ]

        # Create option
        option = KnowledgeBaseOption(
            id=data["id"],
            name=data["name"],
            name_ar=data.get("name_ar"),
            name_fr=data.get("name_fr"),
            type=RecommendationType(data["type"]),
            level=data.get("level", "secondary" if expected_type == RecommendationType.SECONDARY_BRANCH else "university"),
            field=data.get("field"),
            description=data.get("description"),
            description_ar=data.get("description_ar"),
            description_fr=data.get("description_fr"),
            eligibility=eligibility,
            matching_metadata=matching_metadata,
            sources=sources,
            review_status=data.get("review_status", "draft"),
            last_reviewed=data.get("last_reviewed"),
            reviewed_by=data.get("reviewed_by"),
            extra=data.get("extra", {}),
        )

        return option

    def _validate_cross_references(
        self,
        collection: KnowledgeBaseCollection,
        errors: list[str],
    ) -> None:
        """Validate cross-references within the knowledge base."""
        option_ids = {opt.id for opt in collection.options}

        # Check for duplicate IDs
        seen = set()
        duplicates = set()
        for opt in collection.options:
            if opt.id in seen:
                duplicates.add(opt.id)
            seen.add(opt.id)
        if duplicates:
            errors.append(f"Duplicate option IDs: {sorted(duplicates)}")

        # Validate that matching_metadata subject_relevance weights are reasonable
        for opt in collection.options:
            total_weight = sum(opt.matching_metadata.subject_relevance.values())
            if total_weight > 0 and total_weight < 0.5:
                errors.append(
                    f"Option '{opt.id}': subject_relevance weights sum to {total_weight:.2f} "
                    f"(should be >= 0.5 for meaningful matching)"
                )

    def load_option_by_id(self, option_id: str) -> KnowledgeBaseOption | None:
        """Load a single option by ID (for validation)."""
        collection = self.load()
        return collection.get_by_id(option_id)


# Convenience function for tests and scripts
def load_knowledge_base(data_dir: str | None = None) -> KnowledgeBaseCollection:
    """Load the knowledge base from the default data directory."""
    loader = KnowledgeBaseLoader(data_dir)
    return loader.load()