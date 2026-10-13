"""
NaviStudo Backend - Recommendation Orchestration Service.

Coordinates the complete recommendation workflow:
1. Fetch student profile
2. Filter knowledge base by eligibility
3. Invoke Model 1 (free-text extraction)
4. Invoke Model 2 (ranking)
5. Validate recommendations
6. Persist results
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.integrations.model_one import ModelOneClient
from app.integrations.model_two import ModelTwoClient
from app.schemas.model_one_schema import ModelOneInput, ModelOneOutput
from app.schemas.model_two_schema import ModelTwoInput, ModelTwoOutput, RecommendationOption
from app.services.knowledge_base_service import KnowledgeBaseService, RecommendationType
from app.services.student_service import StudentService
from app.services.results_service import ResultsService, StoredRecommendationResult
from app.integrations.firebase_client import FirebaseClient, FirebaseAuthError, FirebaseConfigError
from app.exceptions import (
    StudentNotFoundError,
    FirebaseError,
    ValidationError,
    ModelOneError,
    ModelTwoError,
    ServiceNotImplementedError,
)
from app.services.recommendation_validation import (
    validate_ranked_recommendations,
    RecommendationValidationError,
)


@dataclass
class RecommendationResult:
    """Complete result of a recommendation analysis."""

    analysis_id: str
    student_uid: str
    recommendation_type: str
    recommendations: list[dict[str, Any]]  # RankedRecommendation dicts
    created_at: datetime
    model_one_metadata: dict[str, Any] | None
    model_two_metadata: dict[str, Any] | None


class RecommendationService:
    """Orchestrates the end-to-end recommendation pipeline."""

    def __init__(
        self,
        student_service: StudentService,
        kb_service: KnowledgeBaseService,
        model_one: ModelOneClient,
        model_two: ModelTwoClient,
        firebase_client: FirebaseClient,
        results_service: ResultsService | None = None,
        max_results: int = 10,
    ):
        self._student_service = student_service
        self._kb_service = kb_service
        self._model_one = model_one
        self._model_two = model_two
        self._firebase = firebase_client
        self._results_service = results_service
        self._max_results = max_results

    def create_recommendation(self, student_uid: str) -> RecommendationResult:
        """Execute the full recommendation workflow for a student.

        Args:
            student_uid: Firebase Auth UID of the authenticated student.

        Returns:
            RecommendationResult with ranked recommendations.

        Raises:
            StudentNotFoundError: If student profile doesn't exist.
            FirebaseAuthError: If Firebase authentication fails.
            FirebaseConfigError: If Firebase is not configured.
            ModelOneError: If Model 1 fails.
            ModelTwoError: If Model 2 fails.
            ValidationError: If Model 2 returns invalid option IDs.
        """
        # 1. Fetch student profile
        profile = self._student_service.get_student_profile(student_uid)

        # 2. Determine recommendation type from school year
        recommendation_type = self._determine_recommendation_type(profile.school_year)

        # 3. Filter knowledge base by eligibility
        eligible_options = self._kb_service.filter_eligible_options(
            student_profile=self._student_service.get_structured_profile(student_uid),
            recommendation_type=recommendation_type,
        )

        if not eligible_options:
            # No eligible options - return empty result (not an error)
            return RecommendationResult(
                analysis_id=str(uuid4()),
                student_uid=student_uid,
                recommendation_type=recommendation_type.value,
                recommendations=[],
                created_at=datetime.utcnow(),
                model_one_metadata=None,
                model_two_metadata=None,
            )

        # 4. Prepare Model 1 input (free-text answers only)
        model_one_input = ModelOneInput(
            free_text_answers=profile.free_text_answers or {},
            question_context=self._get_question_context(),  # TODO: define context source
            school_year=profile.school_year,
            current_branch=profile.current_branch,
        )

        # 5. Invoke Model 1
        model_one_output: ModelOneOutput = self._model_one.analyze(model_one_input)

        if not model_one_output.success:
            raise ModelOneError(model_one_output.error or "Model 1 analysis failed")

        # 6. Prepare Model 2 input
        # Convert KnowledgeBaseOption objects to RecommendationOption schema
        eligible_for_model = [
            RecommendationOption(
                id=opt.id,
                name=opt.name,
                description=opt.description,
                **(opt.raw_data or {}),
            )
            for opt in eligible_options
        ]

        model_two_input = ModelTwoInput(
            student_profile=self._student_service.get_structured_profile(student_uid),
            model_one_output=model_one_output.extracted_data,
            eligible_options=eligible_for_model,
            recommendation_type=recommendation_type.value,
        )

        # 7. Invoke Model 2
        model_two_output: ModelTwoOutput = self._model_two.rank(model_two_input)

        if not model_two_output.success:
            raise ModelTwoError(model_two_output.error or "Model 2 ranking failed")

        # 8. Validate recommendations using the new comprehensive validator
        eligible_ids = {opt.id for opt in eligible_options}
        try:
            validate_ranked_recommendations(
                model_two_output.recommendations,
                eligible_ids,
                self._max_results,
            )
        except RecommendationValidationError as e:
            raise ValidationError(str(e)) from e

        # 9. Persist result
        analysis_id = str(uuid4())
        result = RecommendationResult(
            analysis_id=analysis_id,
            student_uid=student_uid,
            recommendation_type=recommendation_type.value,
            recommendations=[r.model_dump() for r in model_two_output.recommendations],
            created_at=datetime.utcnow(),
            model_one_metadata=model_one_output.metadata,
            model_two_metadata=model_two_output.metadata,
        )

        # Save via ResultsService if available
        if self._results_service is not None:
            stored_result = StoredRecommendationResult(
                analysis_id=analysis_id,
                student_uid=student_uid,
                recommendation_type=recommendation_type.value,
                recommendations=[r.model_dump() for r in model_two_output.recommendations],
                created_at=datetime.utcnow(),
                model_one_metadata=model_one_output.metadata,
                model_two_metadata=model_two_output.metadata,
                model_one_raw_output=model_one_output.extracted_data,
                model_two_raw_output=model_two_output.model_dump(),
            )
            self._results_service.save(stored_result)
        else:
            # Fallback to legacy _save_result if ResultsService not configured
            self._save_result(result)

        return result

    def get_recommendation(self, analysis_id: str, student_uid: str) -> RecommendationResult | None:
        """Retrieve a previous recommendation result.

        Args:
            analysis_id: The analysis ID to retrieve.
            student_uid: The student's UID (for ownership verification).

        Returns:
            RecommendationResult if found and owned by student, None otherwise.
        """
        if self._results_service is None:
            raise ServiceNotImplementedError(
                "RecommendationService.get_recommendation requires ResultsService. "
                "Waiting for results collection schema confirmation."
            )

        stored = self._results_service.get(analysis_id, student_uid)
        if stored is None:
            return None

        # Convert StoredRecommendationResult to RecommendationResult
        return RecommendationResult(
            analysis_id=stored.analysis_id,
            student_uid=stored.student_uid,
            recommendation_type=stored.recommendation_type,
            recommendations=stored.recommendations,
            created_at=stored.created_at,
            model_one_metadata=stored.model_one_metadata,
            model_two_metadata=stored.model_two_metadata,
        )

    def _determine_recommendation_type(self, school_year: int) -> RecommendationType:
        """Map school year to recommendation type."""
        if school_year == 1:
            return RecommendationType.SECONDARY_BRANCH
        elif school_year == 3:
            return RecommendationType.UNIVERSITY_MAJOR
        else:
            # Year 2 is out of MVP scope
            raise ValueError(
                f"School year {school_year} is not supported in the current MVP. "
                "Only year 1 (secondary branches) and year 3 (university majors) are supported."
            )

    def _get_question_context(self) -> dict[str, str]:
        """Get context for free-text questions.

        This could come from a config file, knowledge base, or be hardcoded.
        For now, returns empty dict - to be implemented when questions are finalized.
        """
        # TODO: Implement when question set is finalized
        return {}

    def _validate_recommendations(
        self,
        recommendations: list[Any],  # RankedRecommendation objects
        eligible_options: list[Any],  # KnowledgeBaseOption objects
    ) -> None:
        """Ensure all recommended option_ids exist in eligible options.

        Kept for backward compatibility. The comprehensive validation
        in recommendation_validation.py is now used in create_recommendation.

        Args:
            recommendations: List of RankedRecommendation from Model 2.
            eligible_options: List of KnowledgeBaseOption that were passed to Model 2.

        Raises:
            ValidationError: If any recommendation references an unknown option_id.
        """
        eligible_ids = {opt.id for opt in eligible_options}

        for rec in recommendations:
            if rec.option_id not in eligible_ids:
                raise ValidationError(
                    f"Model 2 recommended unknown option_id: {rec.option_id}. "
                    f"Valid IDs: {sorted(eligible_ids)}"
                )

    def _save_result(self, result: RecommendationResult) -> None:
        """Legacy fallback for saving recommendation result.

        This is only called when ResultsService is not configured.
        Prefer using ResultsService directly.

        Args:
            result: The complete recommendation result to persist.
        """
        raise ServiceNotImplementedError(
            "RecommendationService._save_result not implemented. "
            "Configure ResultsService to enable persistence."
        )