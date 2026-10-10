"""
NaviStudo Backend - Flask application factory.
"""

from flask import Flask

from app.config import Config, TestingConfig
from app.routes.health import health_bp


def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register blueprints
    app.register_blueprint(health_bp, url_prefix="/api/v1")

    return app