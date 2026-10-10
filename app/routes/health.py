"""
NaviStudo Backend - Health check endpoint.
"""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """Health check endpoint.

    Returns:
        JSON response with status "ok" and HTTP 200.
    """
    return jsonify({"status": "ok"}), 200