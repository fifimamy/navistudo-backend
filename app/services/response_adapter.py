"""
NaviStudo Backend - Frontend Response Adapter.

Maps internal recommendation results onto the frontend response envelope
defined in the frontend repository (``src/types/contract.ts``).

The backend keeps its internal fields (``id``/``name``/``rank``/``score``/
``reasoning``) and adds the frontend fields so both contracts can coexist.
Fields that require knowledge-base data the backend does not yet store
(``min_indicative_average``, ``study_duration_years``, ``institution_types``)
are returned as ``null``/empty and must be populated by enriching the
knowledge base.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0.0"

# Knowledge-base field -> frontend category.
KB_FIELD_TO_CATEGORY: dict[str, str] = {
    "medicine": "health",
    "computer_science": "engineering",
    "engineering": "engineering",
    "science": "science",
    "law": "humanities",
    "humanities": "humanities",
    "economics": "business",
    "business": "business",
    "health": "health",
}


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Read an attribute from a KB option, falling back to its raw_data."""
    if obj is None:
        return default
    if hasattr(obj, name):
        return getattr(obj, name)
    raw = getattr(obj, "raw_data", None)
    if isinstance(raw, dict):
        return raw.get(name, default)
    return default


def _matching_metadata(option: Any) -> Any:
    md = _get(option, "matching_metadata", None)
    if md is None:
        raw = _get(option, "raw_data", None)
        if isinstance(raw, dict):
            md = raw.get("matching_metadata")
    return md


def _eligibility(option: Any) -> Any:
    el = _get(option, "eligibility", None)
    if el is None:
        raw = _get(option, "raw_data", None)
        if isinstance(raw, dict):
            el = raw.get("eligibility")
    return el


def _subject_relevance_keys(md: Any) -> list[str]:
    if md is None:
        return []
    if isinstance(md, dict):
        rel = md.get("subject_relevance", {}) or {}
    else:
        rel = getattr(md, "subject_relevance", {}) or {}
    return [getattr(k, "value", k) for k in rel.keys()]


def _career_themes(md: Any) -> list[str]:
    if md is None:
        return []
    if isinstance(md, dict):
        return list(md.get("career_themes", []) or [])
    return list(getattr(md, "career_themes", []) or [])


def _required_branches(el: Any) -> list[Any]:
    if el is None:
        return []
    if isinstance(el, dict):
        return list(el.get("required_branches", []) or [])
    return list(getattr(el, "required_branches", []) or [])


def _match_level(match_score: float) -> str:
    if match_score >= 85:
        return "strong_match"
    if match_score >= 75:
        return "great_alternative"
    return "field_to_explore"


def enrich_recommendation(rec: dict[str, Any], option: Any | None) -> dict[str, Any]:
    """Return a copy of ``rec`` with the frontend fields added.

    Args:
        rec: Internal recommendation dict (id/name/description/rank/score/reasoning).
        option: The matching knowledge-base option, or None if unavailable.
    """
    from app.services.frontend_adapter import KB_BRANCH_TO_FRONTEND, KB_SUBJECT_TO_FRONTEND

    out = dict(rec)

    score = rec.get("score")
    match_score = round(float(score) * 100) if score is not None else 50
    match_score = max(40, min(97, match_score))
    out["match_score"] = match_score
    out["match_level"] = _match_level(match_score)

    title_en = _get(option, "name") or rec.get("name") or ""
    title_ar = _get(option, "name_ar") or rec.get("name_ar") or title_en

    if option is None:
        out["major_id"] = rec.get("option_id") or rec.get("id")
        out["title_en"] = title_en
        out["title_ar"] = title_ar
        out["category"] = "science"
        out["key_subjects"] = []
        out["typical_careers"] = []
        out["prerequisite_branches"] = []
        out["min_indicative_average"] = None
        out["study_duration_years"] = None
        out["institution_types"] = []
        out["explanation_en"] = rec.get("description") or rec.get("reasoning") or ""
        out["explanation_ar"] = out["explanation_en"]
        return out

    out["major_id"] = _get(option, "id") or rec.get("option_id")
    out["title_en"] = title_en
    out["title_ar"] = title_ar
    out["category"] = KB_FIELD_TO_CATEGORY.get(_get(option, "field") or "", "science")
    out["key_subjects"] = [
        KB_SUBJECT_TO_FRONTEND.get(s, s) for s in _subject_relevance_keys(_matching_metadata(option))
    ]
    out["typical_careers"] = _career_themes(_matching_metadata(option))
    out["prerequisite_branches"] = [
        KB_BRANCH_TO_FRONTEND.get(getattr(b, "value", b), getattr(b, "value", b))
        for b in _required_branches(_eligibility(option))
    ]
    # Not stored in the knowledge base yet — requires data enrichment.
    out["min_indicative_average"] = None
    out["study_duration_years"] = None
    out["institution_types"] = []
    out["explanation_en"] = _get(option, "description") or rec.get("reasoning") or ""
    out["explanation_ar"] = _get(option, "description_ar") or out["explanation_en"]
    return out


def build_summary(
    recommendations: list[dict[str, Any]],
    total_evaluated: int,
) -> dict[str, Any]:
    """Build the frontend ``summary`` block."""
    top = recommendations[0] if recommendations else None
    return {
        "primary_strength": (
            top.get("title_en") if top else "Scientific & Technical Reasoning"
        ),
        "suggested_focus": (
            f"Strong alignment with {top.get('category', '').upper()} pathways given your "
            "academic performance and interest profile."
            if top
            else "Comprehensive orientation recommended across high-demand pathways."
        ),
        "total_evaluated": total_evaluated,
    }
