"""
NaviStudo Backend - Tests for KnowledgeBaseService eligibility logic.
"""

import pytest
from app.services.knowledge_base_service import KnowledgeBaseService, KnowledgeBaseOption, RecommendationType


class TestKnowledgeBaseServiceEligibility:
    """Tests for KnowledgeBaseService._is_eligible method."""

    def setup_method(self):
        """Set up a KnowledgeBaseService instance with a mock firebase client."""
        self.service = KnowledgeBaseService(firebase_client=None)

    # --- Branch eligibility tests ---

    def test_eligible_when_no_branch_requirement(self):
        """Option with no required_branches should be eligible regardless of student branch."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=None,
        )
        student = {"current_branch": "sciences"}
        assert self.service._is_eligible(student, option) is True

    def test_eligible_when_branch_matches(self):
        """Option with required_branches should be eligible if student branch matches."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=["sciences", "maths"],
        )
        student = {"current_branch": "sciences"}
        assert self.service._is_eligible(student, option) is True

    def test_ineligible_when_branch_mismatch(self):
        """Option with required_branches should be ineligible if student branch doesn't match."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=["sciences", "maths"],
        )
        student = {"current_branch": "lettres"}
        assert self.service._is_eligible(student, option) is False

    def test_ineligible_when_student_has_no_branch(self):
        """Option with required_branches should be ineligible if student has no branch."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=["sciences"],
        )
        student = {"current_branch": None}
        assert self.service._is_eligible(student, option) is False

    def test_ineligible_when_branch_field_missing(self):
        """Option with required_branches should be ineligible if student profile lacks current_branch."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=["sciences"],
        )
        student = {}  # missing current_branch
        assert self.service._is_eligible(student, option) is False

    # --- Wilaya eligibility tests ---

    def test_eligible_when_no_wilaya_requirement(self):
        """Option with no required_wilayas should be eligible regardless of student wilaya."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_wilayas=None,
        )
        student = {"wilaya": "Alger"}
        assert self.service._is_eligible(student, option) is True

    def test_eligible_when_wilaya_matches(self):
        """Option with required_wilayas should be eligible if student wilaya matches."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_wilayas=["Alger", "Oran"],
        )
        student = {"wilaya": "Alger"}
        assert self.service._is_eligible(student, option) is True

    def test_ineligible_when_wilaya_mismatch(self):
        """Option with required_wilayas should be ineligible if student wilaya doesn't match."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_wilayas=["Alger", "Oran"],
        )
        student = {"wilaya": "Constantine"}
        assert self.service._is_eligible(student, option) is False

    def test_ineligible_when_student_has_no_wilaya(self):
        """Option with required_wilayas should be ineligible if student has no wilaya."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_wilayas=["Alger"],
        )
        student = {"wilaya": None}
        assert self.service._is_eligible(student, option) is False

    # --- Grade eligibility tests ---

    def test_eligible_when_no_grade_requirement(self):
        """Option with no min_grades should be eligible regardless of student grades."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            min_grades=None,
        )
        student = {"grades": {"math": 15.0}}
        assert self.service._is_eligible(student, option) is True

    def test_eligible_when_all_grades_meet_minimum(self):
        """Option with min_grades should be eligible if all student grades meet or exceed minimum."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            min_grades={"math": 12.0, "physics": 10.0},
        )
        student = {"grades": {"math": 14.0, "physics": 11.0}}
        assert self.service._is_eligible(student, option) is True

    def test_eligible_when_grade_exactly_equals_minimum(self):
        """Grade exactly equal to minimum should be eligible."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            min_grades={"math": 12.0},
        )
        student = {"grades": {"math": 12.0}}
        assert self.service._is_eligible(student, option) is True

    def test_ineligible_when_one_grade_below_minimum(self):
        """Option should be ineligible if any required grade is below minimum."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            min_grades={"math": 12.0, "physics": 10.0},
        )
        student = {"grades": {"math": 14.0, "physics": 9.0}}  # physics below minimum
        assert self.service._is_eligible(student, option) is False

    def test_ineligible_when_required_grade_missing(self):
        """Option should be ineligible if student is missing a required grade subject."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            min_grades={"math": 12.0, "physics": 10.0},
        )
        student = {"grades": {"math": 14.0}}  # physics missing
        assert self.service._is_eligible(student, option) is False

    def test_ineligible_when_grades_field_missing(self):
        """Option should be ineligible if student profile lacks grades entirely."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            min_grades={"math": 12.0},
        )
        student = {}  # missing grades
        assert self.service._is_eligible(student, option) is False

    def test_ineligible_when_grades_is_none(self):
        """Option should be ineligible if student grades is None."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            min_grades={"math": 12.0},
        )
        student = {"grades": None}
        assert self.service._is_eligible(student, option) is False

    # --- Combined eligibility tests ---

    def test_eligible_when_all_criteria_met(self):
        """Option should be eligible when all requirements are satisfied."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=["sciences"],
            required_wilayas=["Alger"],
            min_grades={"math": 12.0},
        )
        student = {
            "current_branch": "sciences",
            "wilaya": "Alger",
            "grades": {"math": 14.0},
        }
        assert self.service._is_eligible(student, option) is True

    def test_ineligible_when_any_criterion_fails(self):
        """Option should be ineligible if any single requirement fails."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=["sciences"],
            required_wilayas=["Alger"],
            min_grades={"math": 12.0},
        )
        # Branch fails
        student = {
            "current_branch": "lettres",
            "wilaya": "Alger",
            "grades": {"math": 14.0},
        }
        assert self.service._is_eligible(student, option) is False

        # Wilaya fails
        student = {
            "current_branch": "sciences",
            "wilaya": "Oran",
            "grades": {"math": 14.0},
        }
        assert self.service._is_eligible(student, option) is False

        # Grade fails
        student = {
            "current_branch": "sciences",
            "wilaya": "Alger",
            "grades": {"math": 10.0},
        }
        assert self.service._is_eligible(student, option) is False

    # --- Edge cases ---

    def test_eligible_when_empty_requirements(self):
        """Option with all empty requirements should be eligible for any student."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=[],
            required_wilayas=[],
            min_grades={},
        )
        student = {}
        assert self.service._is_eligible(student, option) is True

    def test_eligible_with_extra_student_fields(self):
        """Extra fields in student profile should not affect eligibility."""
        option = KnowledgeBaseOption(
            id="opt1",
            name="Test Option",
            type=RecommendationType.SECONDARY_BRANCH,
            required_branches=["sciences"],
        )
        student = {
            "current_branch": "sciences",
            "extra_field": "ignored",
            "another_field": 123,
        }
        assert self.service._is_eligible(student, option) is True


class TestKnowledgeBaseServiceFilterEligibleOptions:
    """Tests for KnowledgeBaseService.filter_eligible_options method."""

    def setup_method(self):
        """Set up a KnowledgeBaseService instance with a mock firebase client."""
        self.service = KnowledgeBaseService(firebase_client=None)

    def _make_options(self):
        """Create a standard set of test options."""
        return [
            KnowledgeBaseOption(
                id="opt1",
                name="Sciences Branch",
                type=RecommendationType.SECONDARY_BRANCH,
                required_branches=["sciences"],
                required_wilayas=["Alger"],
                min_grades={"math": 12.0},
            ),
            KnowledgeBaseOption(
                id="opt2",
                name="Maths Branch",
                type=RecommendationType.SECONDARY_BRANCH,
                required_branches=["maths"],
                required_wilayas=None,
                min_grades={"math": 14.0},
            ),
            KnowledgeBaseOption(
                id="opt3",
                name="Open Branch",
                type=RecommendationType.SECONDARY_BRANCH,
                required_branches=None,
                required_wilayas=None,
                min_grades=None,
            ),
            KnowledgeBaseOption(
                id="opt4",
                name="University Major",
                type=RecommendationType.UNIVERSITY_MAJOR,
                required_branches=["sciences"],
                min_grades={"math": 15.0},
            ),
        ]

    def test_filter_returns_only_eligible(self):
        """filter_eligible_options should return only options matching student profile."""
        options = self._make_options()

        # Patch get_all_options to return our test options
        def mock_get_all(type_):
            return [o for o in options if o.type == type_]

        self.service.get_all_options = mock_get_all

        student = {
            "current_branch": "sciences",
            "wilaya": "Alger",
            "grades": {"math": 14.0},
        }

        eligible = self.service.filter_eligible_options(
            student, RecommendationType.SECONDARY_BRANCH
        )

        eligible_ids = {o.id for o in eligible}
        assert eligible_ids == {"opt1", "opt3"}  # opt2 needs maths branch, opt4 is wrong type

    def test_filter_excludes_wrong_type(self):
        """filter_eligible_options should not return options of different type."""
        options = self._make_options()

        def mock_get_all(type_):
            return [o for o in options if o.type == type_]

        self.service.get_all_options = mock_get_all

        student = {
            "current_branch": "sciences",
            "wilaya": "Alger",
            "grades": {"math": 14.0},
        }

        eligible = self.service.filter_eligible_options(
            student, RecommendationType.SECONDARY_BRANCH
        )

        for opt in eligible:
            assert opt.type == RecommendationType.SECONDARY_BRANCH

    def test_filter_returns_empty_when_none_eligible(self):
        """filter_eligible_options should return empty list when no options match."""
        # Create options that ALL have requirements the student doesn't meet
        # (no "open" option with no requirements)
        options = [
            KnowledgeBaseOption(
                id="opt1",
                name="Sciences Branch",
                type=RecommendationType.SECONDARY_BRANCH,
                required_branches=["sciences"],
                required_wilayas=["Alger"],
                min_grades={"math": 12.0},
            ),
            KnowledgeBaseOption(
                id="opt2",
                name="Maths Branch",
                type=RecommendationType.SECONDARY_BRANCH,
                required_branches=["maths"],
                required_wilayas=["Oran"],
                min_grades={"math": 14.0},
            ),
        ]

        def mock_get_all(type_):
            return [o for o in options if o.type == type_]

        self.service.get_all_options = mock_get_all

        # Student doesn't match ANY option
        student = {
            "current_branch": "lettres",
            "wilaya": "Constantine",
            "grades": {"math": 8.0},
        }

        eligible = self.service.filter_eligible_options(
            student, RecommendationType.SECONDARY_BRANCH
        )

        assert eligible == []

    def test_filter_returns_empty_when_no_options_exist(self):
        """filter_eligible_options should return empty list when KB has no options of that type."""
        def mock_get_all(type_):
            return []

        self.service.get_all_options = mock_get_all

        student = {"current_branch": "sciences"}

        eligible = self.service.filter_eligible_options(
            student, RecommendationType.SECONDARY_BRANCH
        )

        assert eligible == []

    def test_filter_preserves_option_objects(self):
        """filter_eligible_options should return the original KnowledgeBaseOption objects."""
        options = self._make_options()

        def mock_get_all(type_):
            return [o for o in options if o.type == type_]

        self.service.get_all_options = mock_get_all

        student = {"current_branch": "sciences", "wilaya": "Alger", "grades": {"math": 14.0}}

        eligible = self.service.filter_eligible_options(
            student, RecommendationType.SECONDARY_BRANCH
        )

        for opt in eligible:
            assert isinstance(opt, KnowledgeBaseOption)
            assert hasattr(opt, "id")
            assert hasattr(opt, "name")
            assert hasattr(opt, "required_branches")