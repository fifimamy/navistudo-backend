"""
NaviStudo Backend - Flask application factory.

Provides the Flask application factory used to create the app instance.
Handles CORS configuration, blueprint registration, and config loading.
"""

import os
from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.routes.health import health_bp
from app.routes.recommendations import recommendations_bp


def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application.

    Returns:
        A configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # CORS configuration - allow specific origins.
    # Set via environment: CORS_ORIGINS=http://localhost:3000
    # The wildcard is development-only and must not be combined with
    # credentials (browsers reject "*" with Access-Control-Allow-Credentials).
    cors_origins = os.environ.get("CORS_ORIGINS", "*")
    allow_credentials = cors_origins.strip() != "*"
    CORS(
        app,
        resources={r"/api/v1/*": {"origins": cors_origins}},
        supports_credentials=allow_credentials,
    )

    # Register blueprints
    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(recommendations_bp, url_prefix="/api/v1")

    return app