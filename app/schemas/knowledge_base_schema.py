"""
NaviStudo Backend - Knowledge Base Schemas.

Defines validated data structures for the academic knowledge base.
Supports secondary-school branches and university majors with
eligibility rules, matching metadata, and source tracking.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from enum import Enum


class RecommendationType(str, Enum):
    """Type of recommendation based on student's school year."""

    SECONDARY_BRANCH = "secondary_branch"  # Year 1 students -> secondary branches
    UNIVERSITY_MAJOR = "university_major"  # Year 3 students -> university majors


class EligibilityStatus(str, Enum):
    """Verification status of eligibility criteria."""

    VERIFIED = "verified"          # Officially confirmed by ministry/source
    PENDING = "pending"            # Awaiting official confirmation
    UNKNOWN = "unknown"            # Status not determined
    NOT_APPLICABLE = "not_applicable"  # Criterion doesn't apply to this option


class SubjectArea(str, Enum):
    """Academic subject areas for matching metadata."""

    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    ARABIC = "arabic"
    FRENCH = "french"
    ENGLISH = "english"
    PHILOSOPHY = "philosophy"
    HISTORY_GEOGRAPHY = "history_geography"
    TECHNOLOGY = "technology"
    ECONOMICS = "economics"
    MANAGEMENT = "management"
    LAW = "law"
    MEDICINE = "medicine"
    ENGINEERING = "engineering"
    COMPUTER_SCIENCE = "computer_science"
    ARTS = "arts"
    SPORTS = "sports"


class WilayaCode(str, Enum):
    """Algerian wilaya codes (1-58)."""

    ADRAR = "01"
    CHLEF = "02"
    LAGHOUAT = "03"
    OUM_EL_BOUGHI = "04"
    BATNA = "05"
    BEJAIA = "06"
    BISKRA = "07"
    BECHAR = "08"
    BLIDA = "09"
    BOUIRA = "10"
    TAMANRASSET = "11"
    TEBESSA = "12"
    TLEMCEN = "13"
    TIARET = "14"
    TIZI_OUZOU = "15"
    ALGER = "16"
    DJELFA = "17"
    JIJEL = "18"
    SETIF = "19"
    SAIDA = "20"
    SKIKDA = "21"
    SIDI_BEL_ABBES = "22"
    ANNABA = "23"
    GUELMA = "24"
    CONSTANTINE = "25"
    MEDEA = "26"
    MOSTAGANEM = "27"
    MSILA = "28"
    MASCARA = "29"
    OUARGLA = "30"
    ORAN = "31"
    EL_BAYADH = "32"
    ILLIZI = "33"
    BORDJ_BO_ARRERIDJ = "34"
    BOUMERDES = "35"
    EL_TARF = "36"
    TINDOUF = "37"
    TISSEMSILT = "38"
    EL_OUED = "39"
    KHENCHELA = "40"
    SOUK_AHRAS = "41"
    TIPAZA = "42"
    MILA = "43"
    AIN_DEFLAL = "44"
    NAAMA = "45"
    AIN_TEMOUCHENT = "46"
    GHARDAIA = "47"
    RELIZANE = "48"
    TIMIMOUN = "49"
    BORDJ_BADJI_MOKHTAR = "50"
    OUED_EL_ALEUG = "51"
    BENI_ABBES = "52"
    IN_SALAH = "53"
    IN_GUEZZAM = "54"
    TOUGGOURT = "55"
    DJANAH = "56"
    EL_MGHAIR = "57"
    EL_MENIAA = "58"


class SecondaryBranch(str, Enum):
    """Algerian secondary school branches."""

    MATHEMATICS = "mathématiques"
    EXPERIMENTAL_SCIENCES = "sciences_expérimentales"
    TECHNICAL_MATHEMATICS = "mathématiques_techniques"
    MANAGEMENT_ECONOMICS = "gestion_économie"
    FOREIGN_LANGUAGES = "langues_étrangères"
    LETTERS_PHILOSOPHY = "lettres_philosophie"


class KnowledgeBaseEligibilityCriteria(BaseModel):
    """Eligibility criteria for an academic option."""

    # Branch requirements (for university majors)
    required_branches: list[SecondaryBranch] | None = Field(
        default=None,
        description="Required secondary branches. None = no restriction.",
    )
    required_branches_status: EligibilityStatus = Field(
        default=EligibilityStatus.UNKNOWN,
        description="Verification status of branch requirements.",
    )

    # Geographic requirements
    required_wilayas: list[WilayaCode] | None = Field(
        default=None,
        description="Required wilayas. None = no restriction.",
    )
    required_wilayas_status: EligibilityStatus = Field(
        default=EligibilityStatus.UNKNOWN,
        description="Verification status of wilaya requirements.",
    )

    # Minimum grade requirements
    min_grades: dict[str, float] | None = Field(
        default=None,
        description="Minimum grades per subject (subject_code -> min_grade).",
    )
    min_grades_status: EligibilityStatus = Field(
        default=EligibilityStatus.UNKNOWN,
        description="Verification status of grade requirements.",
    )

    # Capacity constraints
    max_capacity: int | None = Field(
        default=None,
        description="Maximum number of students. None = no limit.",
    )
    max_capacity_status: EligibilityStatus = Field(
        default=EligibilityStatus.UNKNOWN,
        description="Verification status of capacity limit.",
    )

    # Additional criteria (flexible for future extensions)
    additional_criteria: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional eligibility criteria with their status.",
    )

    @field_validator("min_grades")
    @classmethod
    def validate_min_grades(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        if v is not None:
            for subject, grade in v.items():
                if not 0 <= grade <= 20:
                    raise ValueError(f"Grade for {subject} must be between 0 and 20")
        return v


class KnowledgeBaseMatchingMetadata(BaseModel):
    """Metadata for AI-based academic suitability matching."""

    # Subject relevance weights (0.0-1.0)
    subject_relevance: dict[SubjectArea, float] = Field(
        default_factory=dict,
        description="Relevance of each subject area for this option (0.0-1.0).",
    )

    # Career themes/keywords
    career_themes: list[str] = Field(
        default_factory=list,
        description="Career themes associated with this option.",
    )

    # Required skills/interests
    recommended_interests: list[str] = Field(
        default_factory=list,
        description="Recommended student interests for this option.",
    )

    # Personality/work style traits
    work_style_traits: list[str] = Field(
        default_factory=list,
        description="Work style traits that match this option.",
    )

    # Difficulty level (1-5)
    difficulty_level: int | None = Field(
        default=None,
        ge=1, le=5,
        description="Perceived difficulty level (1=easiest, 5=hardest).",
    )

    # Prestige/selectivity indicator
    selectivity_tier: Literal["low", "medium", "high", "very_high"] | None = Field(
        default=None,
        description="Selectivity tier of this option.",
    )

    # Employment prospects
    employment_prospects: Literal["excellent", "good", "moderate", "limited"] | None = Field(
        default=None,
        description="Employment prospects after graduation.",
    )

    @field_validator("subject_relevance")
    @classmethod
    def validate_subject_relevance(cls, v: dict[SubjectArea, float]) -> dict[SubjectArea, float]:
        for subject, weight in v.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"Subject relevance for {subject} must be between 0.0 and 1.0")
        return v


class KnowledgeBaseSource(BaseModel):
    """Source reference for knowledge base entry."""

    source_type: Literal["ministry_decree", "university_website", "official_brochure", "api", "manual_entry"]
    source_id: str = Field(description="Unique identifier of the source document.")
    source_url: str | None = Field(default=None, description="URL if available.")
    last_verified: datetime | None = Field(default=None, description="Last verification date.")
    verified_by: str | None = Field(default=None, description="Who verified this entry.")
    notes: str | None = Field(default=None, description="Additional notes about the source.")


class KnowledgeBaseOption(BaseModel):
    """A complete academic option (branch or major) from the knowledge base."""

    # Core identification
    id: str = Field(description="Unique identifier (e.g., 'univ_usthb_cs', 'branch_math').")
    name: str = Field(description="Official display name in Arabic/French.")
    name_ar: str | None = Field(default=None, description="Arabic name.")
    name_fr: str | None = Field(default=None, description="French name.")

    # Type and categorization
    type: RecommendationType
    level: Literal["secondary", "university"]
    field: str | None = Field(default=None, description="Academic field (e.g., 'engineering', 'medicine').")

    # Descriptions
    description: str | None = Field(default=None, description="Detailed description.")
    description_ar: str | None = Field(default=None, description="Arabic description.")
    description_fr: str | None = Field(default=None, description="French description.")

    # Eligibility criteria (official rules)
    eligibility: KnowledgeBaseEligibilityCriteria = Field(
        default_factory=KnowledgeBaseEligibilityCriteria,
    )

    # Matching metadata (for AI suitability assessment)
    matching_metadata: KnowledgeBaseMatchingMetadata = Field(
        default_factory=KnowledgeBaseMatchingMetadata,
    )

    # Source tracking
    sources: list[KnowledgeBaseSource] = Field(
        default_factory=list,
        description="Source references for this entry.",
    )

    # Review status
    review_status: Literal["draft", "reviewed", "approved", "deprecated"] = Field(
        default="draft",
        description="Review status of this entry.",
    )
    last_reviewed: datetime | None = Field(default=None)
    reviewed_by: str | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Extra fields for flexibility
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_consistency(self) -> "KnowledgeBaseOption":
        # Ensure level matches type
        if self.type == RecommendationType.SECONDARY_BRANCH and self.level != "secondary":
            raise ValueError("Secondary branch type must have level='secondary'")
        if self.type == RecommendationType.UNIVERSITY_MAJOR and self.level != "university":
            raise ValueError("University major type must have level='university'")
        return self


class KnowledgeBaseCollection(BaseModel):
    """Complete knowledge base collection with metadata."""

    version: str = Field(default="1.0.0")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    source: str | None = Field(default=None)
    options: list[KnowledgeBaseOption] = Field(default_factory=list)

    def get_by_type(self, rec_type: RecommendationType) -> list[KnowledgeBaseOption]:
        return [opt for opt in self.options if opt.type == rec_type]

    def get_by_id(self, option_id: str) -> KnowledgeBaseOption | None:
        return next((opt for opt in self.options if opt.id == option_id), None)

    def get_eligible_for_student(
        self,
        student_profile: dict[str, Any],
        recommendation_type: RecommendationType,
    ) -> list[KnowledgeBaseOption]:
        """Filter options by eligibility criteria (deterministic)."""
        eligible = []
        for option in self.get_by_type(recommendation_type):
            if self._check_eligibility(option, student_profile):
                eligible.append(option)
        return eligible

    def _check_eligibility(self, option: KnowledgeBaseOption, profile: dict[str, Any]) -> bool:
        """Check if student meets all eligibility criteria."""
        criteria = option.eligibility

        # Branch check
        if criteria.required_branches:
            student_branch = profile.get("current_branch")
            if student_branch:
                try:
                    student_branch_enum = SecondaryBranch(student_branch)
                    if student_branch_enum not in criteria.required_branches:
                        return False
                except ValueError:
                    return False  # Unknown branch -> not eligible
            else:
                return False  # Missing branch -> not eligible

        # Wilaya check
        if criteria.required_wilayas:
            student_wilaya = profile.get("wilaya")
            if student_wilaya:
                try:
                    student_wilaya_enum = WilayaCode(student_wilaya)
                    if student_wilaya_enum not in criteria.required_wilayas:
                        return False
                except ValueError:
                    return False
            else:
                return False

        # Grade check
        if criteria.min_grades:
            student_grades = profile.get("grades", {})
            for subject, min_grade in criteria.min_grades.items():
                if student_grades.get(subject, 0) < min_grade:
                    return False

        # Unknown eligibility status = NOT eligible (safe default)
        if criteria.required_branches and criteria.required_branches_status == EligibilityStatus.UNKNOWN:
            return False
        if criteria.required_wilayas and criteria.required_wilayas_status == EligibilityStatus.UNKNOWN:
            return False
        if criteria.min_grades and criteria.min_grades_status == EligibilityStatus.UNKNOWN:
            return False

        return True