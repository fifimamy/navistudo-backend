"""
NaviStudo Backend - Health check endpoints.

- ``GET /api/v1/health`` — liveness only; confirms Flask is running.
- ``GET /api/v1/health/firebase`` — read-only Firebase/Firestore connectivity
  check used for deployed-environment diagnostics (e.g. Render without Shell).
"""

import logging

from flask import Blueprint, jsonify

from app.integrations.firebase_client import get_firebase_client

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)

# Per-call timeout for the read-only connectivity check. Kept short so a
# dependency outage fails fast instead of holding a request open.
HEALTH_CHECK_TIMEOUT_SECONDS = 5.0


@health_bp.get("/health")
def health_check():
    """Liveness check.

    Returns:
        JSON response with status "ok" and HTTP 200. Does not touch Firebase.
    """
    return jsonify({"status": "ok"}), 200


@health_bp.get("/health/firebase")
def firebase_health_check():
    """Read-only Firebase/Firestore connectivity check.

    Performs a single document read through the existing ``FirebaseClient``
    (no duplicate initialization logic). It never creates, updates, or deletes
    data.

    Returns a generic status only. It never returns exception messages, stack
    traces, credentials, private keys, tokens, or document contents.
    """
    try:
        get_firebase_client().check_firestore_read(
            timeout=HEALTH_CHECK_TIMEOUT_SECONDS
        )
    except Exception as e:  # noqa: BLE001 - never leak details to the client
        # Log only the exception class name; never the message or a traceback.
        logger.warning("Firebase health check failed: %s", type(e).__name__)
        return jsonify({"status": "error", "firebase": "unavailable"}), 503

    return jsonify({"status": "ok", "firebase": "connected"}), 200
