"""
NaviStudo Backend - Recommendations API Routes.

Endpoints:
- POST /api/v1/recommendations - Create new recommendation analysis
- GET  /api/v1/recommendations/<analysis_id> - Retrieve existing analysis
"""

from flask import Blueprint, jsonify, request, g
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound, Forbidden

from app.integrations.firebase_client import get_firebase_client, FirebaseAuthError, FirebaseConfigError
from app.schemas.recommendation_schema import (
    RecommendationResponse,
    RecommendationErrorResponse,
)
from app.services.recommendation_service import (
    RecommendationService,
    StudentNotFoundError,
    FirebaseError,
    ModelOneError,
    ModelTwoError,
    ValidationError,
    ServiceNotImplementedError,
)
from app.services.student_service import StudentService
from app.services.json_knowledge_base_service import JsonKnowledgeBaseService
from app.services.results_service import ResultsService
from app.services.frontend_adapter import adapt_frontend_payload
from app.schemas.frontend_payload_schema import FrontendPayload, FrontendPayloadError
from app.model_one_impl import ModelOneImplementation
from app.model_two_impl import ModelTwoImplementation
from app.services.response_adapter import build_summary, SCHEMA_VERSION


recommendations_bp = Blueprint("recommendations", __name__)


# Error handlers to return JSON instead of HTML
@recommendations_bp.errorhandler(Unauthorized)
def handle_unauthorized(e):
    response = RecommendationErrorResponse(
        error="unauthorized",
        message=str(e.description) if e.description else "Unauthorized",
    )
    return jsonify(response.model_dump()), 401


@recommendations_bp.errorhandler(BadRequest)
def handle_bad_request(e):
    response = RecommendationErrorResponse(
        error="bad_request",
        message=str(e.description) if e.description else "Bad Request",
    )
    return jsonify(response.model_dump()), 400


@recommendations_bp.errorhandler(NotFound)
def handle_not_found(e):
    response = RecommendationErrorResponse(
        error="not_found",
        message=str(e.description) if e.description else "Not Found",
    )
    return jsonify(response.model_dump()), 404


@recommendations_bp.errorhandler(Forbidden)
def handle_forbidden(e):
    response = RecommendationErrorResponse(
        error="forbidden",
        message=str(e.description) if e.description else "Forbidden",
    )
    return jsonify(response.model_dump()), 403


def _get_firebase_uid() -> str:
    """Extract and verify Firebase UID from Authorization header.

    Returns:
        Verified Firebase UID string.

    Raises:
        Unauthorized: If token is missing, invalid, or expired.
        BadRequest: If Authorization header format is wrong.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise Unauthorized("Missing Authorization header")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise BadRequest("Invalid Authorization header format. Expected: 'Bearer <token>'")

    id_token = parts[1]

    try:
        firebase_client = get_firebase_client()
        decoded_token = firebase_client.verify_id_token(id_token)
        return decoded_token["uid"]
    except FirebaseAuthError as e:
        raise Unauthorized(str(e)) from e
    except FirebaseConfigError as e:
        # Firebase not configured on server - this is a server error, not client error
        raise Unauthorized("Authentication service unavailable") from e
    except Exception as e:
        # Catch any other unexpected errors from token verification
        raise Unauthorized(f"Token verification failed: {e}") from e


def _get_recommendation_service() -> RecommendationService:
    """Create a RecommendationService with all dependencies.

    In production, this could be cached or use dependency injection.
    For now, creates fresh instances per request.
    """
    firebase_client = get_firebase_client()
    student_service = StudentService(firebase_client)
    kb_service = JsonKnowledgeBaseService()
    results_service = ResultsService(firebase_client)

    # Import AI client lazily to avoid import errors when not configured
    try:
        from app.ai_client import get_ai_client
        ai_client = get_ai_client()
    except Exception:
        ai_client = None

    model_one = ModelOneImplementation(provider_client=ai_client)
    model_two = ModelTwoImplementation(provider_client=ai_client)

    return RecommendationService(
        student_service=student_service,
        kb_service=kb_service,
        model_one=model_one,
        model_two=model_two,
        firebase_client=firebase_client,
        results_service=results_service,
    )


@recommendations_bp.post("/recommendations")
def create_recommendation():
    """Create a new recommendation analysis for the authenticated student.

    Requires: Authorization: Bearer <Firebase ID token>

    Returns:
        201: RecommendationResponse with analysis_id and ranked recommendations
        400: Invalid request
        401: Missing or invalid token
        404: Student profile not found
        500: Internal error (Firebase, AI models, etc.)
        503: Required integrations not implemented
    """
    # Verify authentication
    try:
        student_uid = _get_firebase_uid()
    except (Unauthorized, BadRequest):
        raise

    # Parse and validate the request body. The frontend submits its
    # questionnaire payload here. An empty body is still accepted for
    # backward compatibility (the profile is then read from Firestore).
    request_data = request.get_json(silent=True) or {}
    adapted = None
    if request_data:
        if not isinstance(request_data, dict):
            raise BadRequest("Request body must be a JSON object")
        if "student_profile" in request_data:
            try:
                payload = FrontendPayload(**request_data)
                adapted = adapt_frontend_payload(payload)
            except FrontendPayloadError as e:
                raise BadRequest(f"Invalid questionnaire payload: {e}")
            except Exception as e:
                raise BadRequest(f"Invalid questionnaire payload: {e}")

    # Execute recommendation workflow
    service = _get_recommendation_service()

    try:
        if adapted is not None:
            # Persist the submitted questionnaire before running the pipeline
            # so the pipeline reads the same validated data back.
            service.persist_student_profile(student_uid, adapted)
        result = service.create_recommendation(student_uid)
    except StudentNotFoundError as e:
        raise NotFound(str(e))
    except FrontendPayloadError as e:
        raise BadRequest(str(e))
    except (FirebaseError, FirebaseConfigError) as e:
        # Firebase configuration or connection error
        raise Unauthorized("Database service unavailable") from e
    except ModelOneError as e:
        # Model 1 failed - return 503 since AI integration isn't ready
        error_response = RecommendationErrorResponse(
            error="model_one_unavailable",
            message="Free-text analysis service is not available",
            details={"reason": str(e)},
        )
        return jsonify(error_response.model_dump()), 503
    except ModelTwoError as e:
        # Model 2 failed
        error_response = RecommendationErrorResponse(
            error="model_two_unavailable",
            message="Recommendation ranking service is not available",
            details={"reason": str(e)},
        )
        return jsonify(error_response.model_dump()), 503
    except ValidationError as e:
        # Model 2 returned invalid option IDs - this is a server bug
        error_response = RecommendationErrorResponse(
            error="validation_failed",
            message="Recommendation validation failed",
            details={"reason": str(e)},
        )
        return jsonify(error_response.model_dump()), 500
    except ServiceNotImplementedError as e:
        # Explicitly catch ServiceNotImplementedError from unimplemented services
        error_response = RecommendationErrorResponse(
            error="not_implemented",
            message="Required backend component not yet implemented",
            details={"reason": str(e)},
        )
        return jsonify(error_response.model_dump()), 503
    except Exception as e:
        # Unexpected error
        error_response = RecommendationErrorResponse(
            error="internal_error",
            message="An unexpected error occurred",
            details={"reason": str(e)},
        )
        return jsonify(error_response.model_dump()), 500

    # Build response
    response = RecommendationResponse(
        analysis_id=result.analysis_id,
        student_uid=result.student_uid,
        recommendation_type=result.recommendation_type,
        recommendations=result.recommendations,
        created_at=result.created_at,
        model_one_metadata=result.model_one_metadata,
        model_two_metadata=result.model_two_metadata,
        profile_saved=adapted is not None,
        schema_version=SCHEMA_VERSION,
        summary=build_summary(result.recommendations, result.total_evaluated),
    )

    return jsonify(response.model_dump()), 201


@recommendations_bp.get("/recommendations/<analysis_id>")
def get_recommendation(analysis_id: str):
    """Retrieve a previous recommendation analysis.

    Requires: Authorization: Bearer <Firebase ID token>
    Returns: 403 if the analysis belongs to a different student.

    Args:
        analysis_id: The analysis ID returned from POST /recommendations

    Returns:
        200: RecommendationResponse
        401: Missing or invalid token
        403: Analysis belongs to different student
        404: Analysis not found
        500: Internal error
        503: Not implemented
    """
    # Verify authentication
    try:
        student_uid = _get_firebase_uid()
    except (Unauthorized, BadRequest):
        raise

    # Execute recommendation retrieval
    service = _get_recommendation_service()

    try:
        result = service.get_recommendation(analysis_id, student_uid)
    except ServiceNotImplementedError as e:
        error_response = RecommendationErrorResponse(
            error="not_implemented",
            message="Retrieving past recommendations is not yet implemented",
            details={"reason": str(e)},
        )
        return jsonify(error_response.model_dump()), 503
    except (FirebaseError, FirebaseConfigError) as e:
        raise Unauthorized("Database service unavailable") from e
    except Exception as e:
        error_response = RecommendationErrorResponse(
            error="internal_error",
            message="An unexpected error occurred",
            details={"reason": str(e)},
        )
        return jsonify(error_response.model_dump()), 500

    if result is None:
        # Not found or doesn't belong to this student
        raise NotFound(f"Recommendation analysis {analysis_id} not found")

    # Build response
    response = RecommendationResponse(
        analysis_id=result.analysis_id,
        student_uid=result.student_uid,
        recommendation_type=result.recommendation_type,
        recommendations=result.recommendations,
        created_at=result.created_at,
        model_one_metadata=result.model_one_metadata,
        model_two_metadata=result.model_two_metadata,
        schema_version=SCHEMA_VERSION,
        summary=build_summary(
            result.recommendations,
            result.total_evaluated or len(result.recommendations),
        ),
    )

    return jsonify(response.model_dump()), 200