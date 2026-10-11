"""
NaviStudo Backend - Validation of Model 2 (ranking) output.

Pure function, no Flask / Firebase / AI dependency. The AI is never trusted:
every recommendation it returns is checked here before reaching the frontend.
"""

from collections.abc import Collection, Sequence

from app.schemas.model_two_schema import RankedRecommendation


class RecommendationValidationError(Exception):
    """Raised when Model 2's output breaks one or more rules.

    Attributes:
        problems: every problem found (not just the first), useful for
            logging and for deciding whether to retry the model call.
    """

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Invalid recommendations: " + "; ".join(problems))


def collect_validation_problems(
    recommendations: Sequence[RankedRecommendation],
    eligible_ids: Collection[str],
    max_results: int,
) -> list[str]:
    """Return a list of human-readable problems (empty list = output is valid)."""
    problems: list[str] = []
    eligible = set(eligible_ids)

    # Nothing returned although options were available.
    if not recommendations:
        if eligible:
            problems.append("no recommendations returned although eligible options exist")
        return problems

    # Too many results.
    if len(recommendations) > max_results:
        problems.append(
            f"{len(recommendations)} recommendations returned, maximum is {max_results}"
        )

    # Unknown option IDs (the AI invented an option or used a wrong ID).
    unknown = sorted({r.option_id for r in recommendations if r.option_id not in eligible})
    if unknown:
        problems.append(f"unknown option_id(s): {unknown}")

    # Duplicate option IDs.
    seen: set[str] = set()
    duplicates: set[str] = set()
    for r in recommendations:
        if r.option_id in seen:
            duplicates.add(r.option_id)
        seen.add(r.option_id)
    if duplicates:
        problems.append(f"duplicate option_id(s): {sorted(duplicates)}")

    # Ranks must be exactly 1..N: no gaps, no repeats.
    ranks = sorted(r.rank for r in recommendations)
    expected = list(range(1, len(recommendations) + 1))
    if ranks != expected:
        problems.append(f"ranks must be exactly {expected}, got {ranks}")

    # Reasoning must contain actual text.
    empty_reasoning = sorted(r.option_id for r in recommendations if not r.reasoning.strip())
    if empty_reasoning:
        problems.append(f"empty reasoning for option_id(s): {empty_reasoning}")

    # Optional score must stay in the documented 0.0-1.0 range.
    bad_scores = sorted(
        r.option_id
        for r in recommendations
        if r.score is not None and not 0.0 <= r.score <= 1.0
    )
    if bad_scores:
        problems.append(f"score outside 0.0-1.0 for option_id(s): {bad_scores}")

    return problems


def validate_ranked_recommendations(
    recommendations: Sequence[RankedRecommendation],
    eligible_ids: Collection[str],
    max_results: int,
) -> None:
    """Validate Model 2's recommendations; raise RecommendationValidationError if invalid.

    Args:
        recommendations: what Model 2 returned.
        eligible_ids: IDs of the options that were sent to Model 2.
        max_results: maximum number of recommendations allowed in the response.
    """
    problems = collect_validation_problems(recommendations, eligible_ids, max_results)
    if problems:
        raise RecommendationValidationError(problems)
