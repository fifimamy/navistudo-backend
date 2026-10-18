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

from app.model_one_impl import ModelOneImplementation
from app.model_two_impl import ModelTwoImplementation
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
from app.services.response_adapter import enrich_recommendation


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
    total_evaluated: int = 0  # Number of eligible options considered


class RecommendationService:
    """Orchestrates the end-to-end recommendation pipeline."""

    def __init__(
        self,
        student_service: StudentService,
        kb_service: KnowledgeBaseService,
        model_one: Any,
        model_two: Any,
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
        # Merge the default question context with any per-student context
        # persisted from the frontend payload.
        question_context = dict(self._get_question_context())
        if profile.question_context:
            question_context.update(profile.question_context)

        model_one_input = ModelOneInput(
            free_text_answers=profile.free_text_answers or {},
            question_context=question_context,
            school_year=profile.school_year,
            current_branch=profile.current_branch,
        )

        # 5. Invoke Model 1
        model_one_output: ModelOneOutput = self._model_one.analyze(model_one_input)

        if not model_one_output.success:
            raise ModelOneError(model_one_output.error or "Model 1 analysis failed")

        # 6. Prepare Model 2 input
        # Convert KnowledgeBaseOption objects to RecommendationOption schema
        # Filter out keys already passed explicitly to avoid duplicate kwargs
        eligible_for_model = []
        for opt in eligible_options:
            raw = opt.raw_data or {}
            extra = {k: v for k, v in raw.items() if k not in ("id", "name", "description")}
            eligible_for_model.append(
                RecommendationOption(
                    id=opt.id,
                    name=opt.name,
                    description=opt.description,
                    **extra,
                )
            )

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

        # Enrich each ranked recommendation with the knowledge-base option's
        # display metadata so the API response can expose id/name/description.
        option_meta = {opt.id: opt for opt in eligible_options}
        recommendations: list[dict[str, Any]] = []
        for rec in model_two_output.recommendations:
            meta = option_meta.get(rec.option_id)
            base = rec.model_dump()
            base["id"] = rec.option_id
            base["name"] = meta.name if meta is not None else rec.option_id
            base["name_ar"] = getattr(meta, "name_ar", None) if meta is not None else None
            base["description"] = meta.description if meta is not None else None
            recommendations.append(enrich_recommendation(base, meta))

        # 9. Persist result
        analysis_id = str(uuid4())
        result = RecommendationResult(
            analysis_id=analysis_id,
            student_uid=student_uid,
            recommendation_type=recommendation_type.value,
            recommendations=recommendations,
            created_at=datetime.utcnow(),
            model_one_metadata=model_one_output.metadata,
            model_two_metadata=model_two_output.metadata,
            total_evaluated=len(eligible_options),
        )

        # Save via ResultsService if available
        if self._results_service is not None:
            stored_result = StoredRecommendationResult(
                analysis_id=analysis_id,
                student_uid=student_uid,
                recommendation_type=recommendation_type.value,
                recommendations=recommendations,
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

    def persist_student_profile(self, student_uid: str, adapted: Any) -> None:
        """Persist a validated frontend payload as the student's profile.

        The frontend submits its questionnaire payload to the API; this method
        writes it to Firestore using the documented schema so the pipeline can
        read the same data back through ``get_student_profile``.

        Args:
            student_uid: Firebase Auth UID of the authenticated student.
            adapted: A ``FrontendAdapted`` produced by ``adapt_frontend_payload``.

        Raises:
            FirebaseError: If the write operation fails.
        """
        from app.services.frontend_adapter import to_student_document

        document = to_student_document(adapted)
        document["uid"] = student_uid
        self._student_service.save_profile(student_uid, document)

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

        Provides context for known question fields used in the MVP.
        Additional questions can be added here when the question set is finalized.
        """
        return {
            "q_goal": "What are your academic and career goals?",
            "q_interest": "What subjects or activities do you enjoy most?",
            "q_strength": "What are your academic strengths?",
            "q_difficulty": "What subjects or areas do you find challenging?",
            "q_work_env": "What type of work or study environment do you prefer?",
        }

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