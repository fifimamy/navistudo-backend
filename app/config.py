"""
NaviStudo Backend - Configuration classes.
"""

import os


class Config:
    """Base configuration."""

    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    pass


# Mapping for easy selection
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name: str | None = None) -> type[Config]:
    """Get configuration class by name."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")
    return CONFIG_MAP.get(config_name.lower(), CONFIG_MAP["default"])