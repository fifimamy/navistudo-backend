"""
NaviStudo Backend - Test fakes.

Everything here is made-up data and in-memory stand-ins, so the whole
recommendation pipeline can be tested without Firebase or a real AI model.

IMPORTANT: names, IDs, subjects and branches below are deliberately fake
("fake_*"). Do not copy real knowledge-base content into tests.
"""

from copy import deepcopy
from typing import Any

from app.schemas.model_one_schema import ModelOneInput, ModelOneOutput
from app.schemas.model_two_schema import (
    ModelTwoInput,
    ModelTwoOutput,
    RankedRecommendation,
)
from app.services.knowledge_base_service import (
    KnowledgeBaseOption,
    KnowledgeBaseService,
    RecommendationType,
)
from app.services.student_service import (
    StudentNotFoundError,
    StudentProfile,
    StudentService,
)

# ---------------------------------------------------------------------------
# Fake data
# ---------------------------------------------------------------------------

FAKE_UID = "fake_uid_001"


def make_fake_student_profile(uid: str = FAKE_UID, **overrides: Any) -> StudentProfile:
    """A year-3 student in a fake branch, with fake grades and free text.

    raw_data holds the *structured* fields (what the eligibility filter and
    Model 2 see). Free-text answers live only in free_text_answers.
    """
    fields: dict[str, Any] = {
        "uid": uid,
        "school_year": 3,
        "current_branch": "fake_branch_x",
        "wilaya": "fake_wilaya",
        "grades": {"fake_subject_1": 14.0, "fake_subject_2": 12.5},
        "free_text_answers": {
            "fake_q_goal": "I like building small tools and fixing things.",
            "fake_q_interest": "Fake interest: puzzles and logic games.",
        },
    }
    fields.update(overrides)

    fields["raw_data"] = {
        "school_year": fields["school_year"],
        "current_branch": fields["current_branch"],
        "wilaya": fields["wilaya"],
        "grades": fields["grades"],
    }
    return StudentProfile(**fields)


def make_fake_kb_options() -> list[KnowledgeBaseOption]:
    """Five fake university majors: three the default student can enter, two not.

    - fake_opt_a: needs branch fake_branch_x            -> eligible
    - fake_opt_b: branch x + fake_subject_1 >= 10       -> eligible (14 >= 10)
    - fake_opt_c: needs branch fake_branch_y            -> NOT eligible (wrong branch)
    - fake_opt_d: no requirements                       -> eligible
    - fake_opt_e: branch x + fake_subject_1 >= 18       -> NOT eligible (14 < 18)
    """
    t = RecommendationType.UNIVERSITY_MAJOR
    return [
        KnowledgeBaseOption(
            id="fake_opt_a", name="Fake Major Alpha", type=t,
            description="Fake description A.",
            required_branches=["fake_branch_x"],
        ),
        KnowledgeBaseOption(
            id="fake_opt_b", name="Fake Major Beta", type=t,
            description="Fake description B.",
            required_branches=["fake_branch_x"],
            min_grades={"fake_subject_1": 10.0},
        ),
        KnowledgeBaseOption(
            id="fake_opt_c", name="Fake Major Gamma", type=t,
            description="Fake description C.",
            required_branches=["fake_branch_y"],
        ),
        KnowledgeBaseOption(
            id="fake_opt_d", name="Fake Major Delta", type=t,
            description="Fake description D.",
        ),
        KnowledgeBaseOption(
            id="fake_opt_e", name="Fake Major Epsilon", type=t,
            description="Fake description E.",
            required_branches=["fake_branch_x"],
            min_grades={"fake_subject_1": 18.0},
        ),
    ]


# IDs a correct filter must keep for the default fake student.
EXPECTED_ELIGIBLE_IDS = {"fake_opt_a", "fake_opt_b", "fake_opt_d"}


# ---------------------------------------------------------------------------
# Fake services (real filtering logic, in-memory data)
# ---------------------------------------------------------------------------

class FakeStudentService(StudentService):
    """StudentService backed by a dict instead of Firestore."""

    def __init__(self, profiles: list[StudentProfile] | None = None):
        super().__init__(firebase_client=None)
        self._profiles = {p.uid: p for p in (profiles or [])}

    def get_student_profile(self, uid: str) -> StudentProfile:
        if uid not in self._profiles:
            raise StudentNotFoundError(uid)
        # Copy so a test (or the code under test) can't mutate shared fixtures.
        return deepcopy(self._profiles[uid])


class FakeKnowledgeBaseService(KnowledgeBaseService):
    """KnowledgeBaseService backed by a list instead of Firestore.

    Only the data access is faked: filter_eligible_options / _is_eligible are
    the REAL ones, so eligibility tests exercise the real rules.
    """

    def __init__(self, options: list[KnowledgeBaseOption] | None = None):
        super().__init__(firebase_client=None)
        self._options = list(options or [])

    def get_all_options(self, recommendation_type: RecommendationType) -> list[KnowledgeBaseOption]:
        return [o for o in self._options if o.type == recommendation_type]

    def get_option_by_id(self, option_id: str) -> KnowledgeBaseOption | None:
        return next((o for o in self._options if o.id == option_id), None)


# ---------------------------------------------------------------------------
# Fake model clients
# ---------------------------------------------------------------------------

class FakeModelOneClient:
    """Stand-in for ModelOneClient (free-text analysis).

    scenario:
        "ok"      -> success with a made-up extracted_data structure
        "failure" -> success=False with an error message

    Every call's input is stored in self.calls so tests can assert on it.
    NOTE: the shape of extracted_data is a placeholder; the real schema is
    being defined by Oumnia.
    """

    SCENARIOS = ("ok", "failure")

    def __init__(self, scenario: str = "ok"):
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario {scenario!r}. Choose from {self.SCENARIOS}.")
        self.scenario = scenario
        self.calls: list[ModelOneInput] = []

    def analyze(self, input_data: ModelOneInput) -> ModelOneOutput:
        self.calls.append(input_data)
        if self.scenario == "failure":
            return ModelOneOutput(success=False, error="fake model one failure")
        return ModelOneOutput(
            success=True,
            extracted_data={
                "interests": ["fake_interest_puzzles"],
                "goals": ["fake_goal_build_tools"],
            },
            metadata={"model": "fake-model-one"},
        )


class FakeModelTwoClient:
    """Stand-in for ModelTwoClient (ranking), with deliberately bad outputs.

    Every scenario starts from a VALID ranking built from the options it
    receives (ranked in the order given), then breaks one thing:

        "valid"            -> correct ranking
        "unknown_id"       -> first recommendation uses an ID not in the input
        "duplicate_id"     -> second recommendation repeats the first one's ID
        "duplicate_rank"   -> second recommendation gets rank 1 (same as first)
        "rank_gap"         -> last recommendation jumps to rank N+2
        "empty_reasoning"  -> first recommendation has an empty reasoning
        "bad_score"        -> first recommendation has score 1.7
        "empty"            -> success=True but no recommendations at all
        "failure"          -> success=False with an error message

    Every call's input is stored in self.calls.
    """

    SCENARIOS = (
        "valid", "unknown_id", "duplicate_id", "duplicate_rank",
        "rank_gap", "empty_reasoning", "bad_score", "empty", "failure",
    )

    def __init__(self, scenario: str = "valid"):
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario {scenario!r}. Choose from {self.SCENARIOS}.")
        self.scenario = scenario
        self.calls: list[ModelTwoInput] = []

    def rank(self, input_data: ModelTwoInput) -> ModelTwoOutput:
        self.calls.append(input_data)

        if self.scenario == "failure":
            return ModelTwoOutput(success=False, error="fake model two failure")

        recs = [
            RankedRecommendation(
                option_id=opt.id,
                rank=i,
                score=round(max(0.0, 1.0 - 0.1 * (i - 1)), 2),
                reasoning=f"Fake reasoning for {opt.id}.",
            )
            for i, opt in enumerate(input_data.eligible_options, start=1)
        ]
        self._break(recs)

        return ModelTwoOutput(
            success=True,
            recommendations=recs,
            metadata={"model": "fake-model-two", "scenario": self.scenario},
        )

    def _break(self, recs: list[RankedRecommendation]) -> None:
        """Corrupt a valid ranking in place according to the scenario."""
        if not recs or self.scenario in ("valid", "empty"):
            if self.scenario == "empty":
                recs.clear()
            return

        if self.scenario == "unknown_id":
            recs[0].option_id = "fake_opt_does_not_exist"
        elif self.scenario == "duplicate_id" and len(recs) > 1:
            recs[1].option_id = recs[0].option_id
        elif self.scenario == "duplicate_rank" and len(recs) > 1:
            recs[1].rank = 1
        elif self.scenario == "rank_gap":
            recs[-1].rank = len(recs) + 2
        elif self.scenario == "empty_reasoning":
            recs[0].reasoning = ""
        elif self.scenario == "bad_score":
            recs[0].score = 1.7
