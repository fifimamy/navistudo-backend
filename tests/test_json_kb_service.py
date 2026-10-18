"""
Tests for JSON Knowledge Base Service integration.
Verifies that the production KB loading path works correctly.
"""

import pytest

from app.services.json_knowledge_base_service import JsonKnowledgeBaseService
from app.services.knowledge_base_service import RecommendationType


class TestJsonKnowledgeBaseService:
    """Tests for the JSON knowledge base service."""

    def test_loads_from_json_files(self):
        """Service should load KB from JSON files."""
        service = JsonKnowledgeBaseService()
        service._ensure_loaded()
        assert service.is_loaded
        assert service.option_count > 0

    def test_loads_secondary_branches(self):
        """Service should load secondary branches from JSON."""
        service = JsonKnowledgeBaseService()
        branches = service.get_all_options(RecommendationType.SECONDARY_BRANCH)
        assert len(branches) == 6

    def test_loads_university_majors(self):
        """Service should load university majors from JSON."""
        service = JsonKnowledgeBaseService()
        majors = service.get_all_options(RecommendationType.UNIVERSITY_MAJOR)
        assert len(majors) == 5

    def test_filter_eligible_university_majors(self):
        """Service should filter university majors by eligibility."""
        service = JsonKnowledgeBaseService()
        student = {
            "school_year": 3,
            "current_branch": "mathématiques",
            "wilaya": "16",
            "grades": {"mathématiques": 14.0, "physique_chimie": 13.0},
        }
        eligible = service.filter_eligible_options(student, RecommendationType.UNIVERSITY_MAJOR)
        assert len(eligible) > 0
        for opt in eligible:
            assert opt.type == RecommendationType.UNIVERSITY_MAJOR

    def test_filter_eligible_excludes_ineligible(self):
        """Service should exclude options the student is not eligible for."""
        service = JsonKnowledgeBaseService()
        service._ensure_loaded()
        # Student in lettres branch with required grades for law
        student = {
            "school_year": 3,
            "current_branch": "lettres_philosophie",
            "wilaya": "16",
            "grades": {"francais": 14.0, "philosophie": 12.0},
        }
        eligible = service.filter_eligible_options(student, RecommendationType.UNIVERSITY_MAJOR)
        # Law should be eligible (requires lettres_philosophie + grades)
        eligible_ids = [opt.id for opt in eligible]
        assert "major_law" in eligible_ids
        # Medicine should NOT be eligible (requires sciences_expérimentales)
        assert "major_medicine" not in eligible_ids

    def test_get_option_by_id(self):
        """Service should retrieve options by ID."""
        service = JsonKnowledgeBaseService()
        option = service.get_option_by_id("major_medicine")
        assert option is not None
        assert option.id == "major_medicine"

    def test_get_option_by_id_not_found(self):
        """Service should return None for unknown option ID."""
        service = JsonKnowledgeBaseService()
        option = service.get_option_by_id("nonexistent")
        assert option is None

    def test_option_count(self):
        """Service should report correct total option count."""
        service = JsonKnowledgeBaseService()
        service._ensure_loaded()
        assert service.option_count == 11  # 6 branches + 5 majors
