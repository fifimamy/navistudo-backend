"""
NaviStudo Backend - Frontend Payload Adapter.

Maps the frontend questionnaire payload to the internal backend models used by
the recommendation pipeline.

MAPPING DECISIONS (documented in docs/PAYLOAD_NOTES.md; several require
frontend confirmation before production use):

1. ``student_profile.current_stage_id`` -> ``school_year`` using
   ``STAGE_ID_TO_SCHOOL_YEAR``. Unrecognised stage ids raise
   ``FrontendPayloadError`` — we never guess a school year.

2. ``student_profile.subject_performance[].max_score`` -> ``grades[subject_id]``.
   The full range is preserved in ``subject_performance``. ``DEFAULT_GRADE_ENDPOINT``
   selects which bound is used for eligibility. **No averaging is performed.**

3. Rich fields (``interests``, ``future_direction``, ``problem_preferences``)
   are flattened into ``free_text_answers`` for Model 1 and described in
   ``question_context``. Nothing is discarded.

All original data is preserved verbatim in ``raw_payload`` and in the persisted
``questionnaire`` Firestore document.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.schemas.frontend_payload_schema import FrontendPayload, FrontendPayloadError


# ---------------------------------------------------------------------------
# Documented mappings
# ---------------------------------------------------------------------------

STAGE_ID_TO_SCHOOL_YEAR: dict[str, int] = {
    # Canonical frontend stage ids (see frontend src/types/taxonomy.ts)
    "first_year_secondary": 1,
    "third_year_secondary": 3,
    # Legacy / alternative identifiers kept for compatibility
    "first_secondary": 1,
    "premiere_secondaire": 1,
    "1": 1,
    "second_secondary": 2,
    "deuxieme_secondaire": 2,
    "2": 2,
    "third_secondary": 3,
    "troisieme_secondaire": 3,
    "3": 3,
}

# Frontend branch ids -> knowledge-base SecondaryBranch values.
# (frontend src/types/taxonomy.ts THIRD_YEAR_BRANCHES)
FRONTEND_BRANCH_TO_KB: dict[str, str] = {
    "experimental_sciences": "sciences_expérimentales",
    "mathematics": "mathématiques",
    "mathematical_technique": "mathématiques_techniques",
    "management_and_economics": "gestion_économie",
    "foreign_languages": "langues_étrangères",
    "literature_and_philosophy": "lettres_philosophie",
}

# Frontend subject ids -> knowledge-base subject codes used in min_grades.
# (frontend src/types/taxonomy.ts ALL_SUBJECTS)
FRONTEND_SUBJECT_TO_KB: dict[str, str] = {
    "mathematics": "mathématiques",
    "physics_chemistry": "physique_chimie",
    "natural_sciences": "svt",
    "arabic_language": "arabe",
    "french_language": "francais",
    "english_language": "anglais",
    "history_geography": "histoire_geographie",
    "philosophy": "philosophie",
    "islamic_education": "education_islamique",
    "technology": "technologie",
    "economics_management": "economie",
    "accounting_finance": "comptabilite",
    "law": "droit",
    "third_foreign_language": "langue_etrangere",
    "engineering_specialty": "specialite_technique",
}

# Reverse mappings (KB -> frontend) used when building the response.
KB_BRANCH_TO_FRONTEND: dict[str, str] = {v: k for k, v in FRONTEND_BRANCH_TO_KB.items()}
KB_SUBJECT_TO_FRONTEND: dict[str, str] = {v: k for k, v in FRONTEND_SUBJECT_TO_KB.items()}

# Which end of the reported score range is used for eligibility.
# "max" | "min"  — requires frontend confirmation. No averaging.
DEFAULT_GRADE_ENDPOINT = "max"

# Human-readable descriptions used as Model 1 question context.
QUESTION_CONTEXT: dict[str, str] = {
    "interests.academic_interests": "Academic subjects the student is interested in",
    "interests.career_interests": "Career areas the student is interested in",
    "interests.activity_interests": "Activities and hobbies the student enjoys",
    "interests.preferred_topics": "Topics the student wants to learn more about",
    "interests.motivations": "Motivations driving the student's choices",
    "future_direction.short_term_goals": "Short-term academic goals",
    "future_direction.long_term_goals": "Long-term career goals",
    "future_direction.preferred_fields": "Academic fields the student prefers",
    "future_direction.work_environment_preference": "Preferred work or study environment",
    "problem_preferences.abstract_concrete_preference": "Preference for abstract vs concrete problems",
    "problem_preferences.human_vs_system_preference": "Preference for human-centred vs system problems",
    "problem_preferences.preferred_problem_types": "Types of problems the student enjoys",
    "problem_preferences.disliked_activities": "Activities the student dislikes",
}

KNOWN_SECTIONS = ("student_profile", "interests", "future_direction", "problem_preferences")
KNOWN_PROFILE_FIELDS = {
    "current_stage_id",
    "wilaya_code",
    "wilaya",
    "school_name",
    "full_name",
    "subject_performance",
    "current_branch_id",
    "current_branch",
    "branch_id",
}


@dataclass
class FrontendAdapted:
    """Internal representation of a validated frontend payload."""

    school_year: int
    current_branch: str | None
    wilaya: str | None
    grades: dict[str, float]
    free_text_answers: dict[str, str]
    question_context: dict[str, str]
    raw_payload: dict[str, Any]
    mapping_notes: list[str] = field(default_factory=list)
    unknown_fields: list[str] = field(default_factory=list)


def _flatten(
    value: Any,
    prefix: str,
    out: dict[str, str],
) -> None:
    """Flatten a nested structure into ``prefix.key -> text`` entries."""
    if value is None:
        return
    if isinstance(value, dict):
        for key, sub in value.items():
            _flatten(sub, f"{prefix}.{key}" if prefix else str(key), out)
        return
    if isinstance(value, list):
        if not value:
            return
        if all(not isinstance(item, (dict, list)) for item in value):
            out[prefix] = ", ".join(str(item) for item in value)
        else:
            out[prefix] = json.dumps(value, ensure_ascii=False)
        return
    out[prefix] = str(value)


def adapt_frontend_payload(payload: FrontendPayload) -> FrontendAdapted:
    """Convert a validated frontend payload into backend internal models.

    Args:
        payload: A validated ``FrontendPayload``.

    Returns:
        ``FrontendAdapted`` with school_year, grades, free-text answers and
        question context ready for the recommendation pipeline.

    Raises:
        FrontendPayloadError: If a required mapping cannot be made.
    """
    data = payload.model_dump()
    profile = payload.student_profile
    profile_raw = data.get("student_profile", {}) or {}
    notes: list[str] = []

    # --- 1. stage id -> school_year -------------------------------------
    stage_id = profile.current_stage_id
    if not stage_id:
        raise FrontendPayloadError(
            "student_profile.current_stage_id is required to determine school_year"
        )
    school_year = STAGE_ID_TO_SCHOOL_YEAR.get(str(stage_id).strip().lower())
    if school_year is None:
        raise FrontendPayloadError(
            f"Unknown current_stage_id: {stage_id!r}. "
            f"Known values: {sorted(STAGE_ID_TO_SCHOOL_YEAR)}"
        )

    # --- 2. subject performance -> grades -------------------------------
    grades: dict[str, float] = {}
    for entry in profile.subject_performance:
        value: float | None
        if DEFAULT_GRADE_ENDPOINT == "max":
            value = entry.max_score if entry.max_score is not None else entry.min_score
        else:
            value = entry.min_score if entry.min_score is not None else entry.max_score
        if value is None:
            notes.append(f"subject {entry.subject_id!r} has no score; skipped from grades")
            continue
        # Map the frontend subject id onto the knowledge-base subject code so
        # eligibility checks can compare like with like.
        kb_subject = FRONTEND_SUBJECT_TO_KB.get(entry.subject_id, entry.subject_id)
        grades[kb_subject] = float(value)

    # --- 3. current branch (optional) ------------------------------------
    raw_branch = (
        profile_raw.get("current_branch_id")
        or profile_raw.get("current_branch")
        or profile_raw.get("branch_id")
    )
    current_branch = (
        FRONTEND_BRANCH_TO_KB.get(raw_branch, raw_branch) if raw_branch else None
    )

    # --- 4. wilaya -------------------------------------------------------
    wilaya = profile.wilaya_code or profile.wilaya

    # --- 5. flatten rich sections for Model 1 ----------------------------
    free_text_answers: dict[str, str] = {}
    for section in ("interests", "future_direction", "problem_preferences"):
        section_value = data.get(section)
        if isinstance(section_value, dict):
            _flatten(section_value, section, free_text_answers)

    # Preserve additional profile fields that carry matching signal
    # (subject preference order, difficult subjects, baccalaureate result, ...).
    for key in (
        "current_study_group_id",
        "current_branch_subtype_id",
        "subject_preference_order",
        "difficult_subject_ids",
        "has_taken_baccalaureate",
        "baccalaureate_average",
    ):
        if profile_raw.get(key) is not None:
            _flatten(profile_raw[key], f"student_profile.{key}", free_text_answers)

    # Preserve any unknown top-level sections as well.
    unknown_fields: list[str] = []
    for key, value in data.items():
        if key in KNOWN_SECTIONS:
            continue
        unknown_fields.append(key)
        _flatten(value, key, free_text_answers)

    # Record unknown fields inside student_profile.
    for key in profile_raw:
        if key not in KNOWN_PROFILE_FIELDS:
            unknown_fields.append(f"student_profile.{key}")

    # --- 6. question context --------------------------------------------
    question_context = {
        key: QUESTION_CONTEXT[key]
        for key in free_text_answers
        if key in QUESTION_CONTEXT
    }

    notes.append(
        f"grades derived from subject_performance.{DEFAULT_GRADE_ENDPOINT}_score "
        "(mapping requires frontend confirmation)"
    )
    if unknown_fields:
        notes.append(f"unmapped frontend fields preserved: {unknown_fields}")

    return FrontendAdapted(
        school_year=school_year,
        current_branch=current_branch,
        wilaya=wilaya,
        grades=grades,
        free_text_answers=free_text_answers,
        question_context=question_context,
        raw_payload=data,
        mapping_notes=notes,
        unknown_fields=unknown_fields,
    )


def to_student_document(adapted: FrontendAdapted) -> dict[str, Any]:
    """Build the Firestore ``students/{uid}`` document.

    The document is backward compatible with ``StudentService`` and preserves
    the original payload for audit.
    """
    profile_raw = adapted.raw_payload.get("student_profile", {}) or {}
    return {
        "school_year": adapted.school_year,
        "current_branch": adapted.current_branch,
        "wilaya": adapted.wilaya,
        "grades": adapted.grades,
        "subject_performance": profile_raw.get("subject_performance", []),
        "free_text_answers": adapted.free_text_answers,
        "question_context": adapted.question_context,
        "questionnaire": adapted.raw_payload,
        "mapping_notes": adapted.mapping_notes,
    }
