"""
NaviStudo Backend - Application entry point.
"""

import os

from app import create_app
from app.config import get_config


config_name = os.environ.get("FLASK_ENV", "default")
app = create_app(get_config(config_name))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)