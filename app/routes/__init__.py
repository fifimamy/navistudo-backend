"""
NaviStudo Backend - Routes package.
"""

from app.routes.health import health_bp
from app.routes.recommendations import recommendations_bp

__all__ = ["health_bp", "recommendations_bp"]