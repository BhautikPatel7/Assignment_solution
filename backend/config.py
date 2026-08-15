"""
config.py — Central config loader and logger setup.
Reads from .env file. All other modules import from here.
"""

import os
import logging
from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


# ─────────────────────────────────────────────
#  Settings — read once at startup
# ─────────────────────────────────────────────
GOOGLE_CLOUD_PROJECT       = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
VERTEX_LOCATION            = os.getenv("VERTEX_LOCATION", "us-central1")
GEMINI_MODEL_VISION        = os.getenv("GEMINI_MODEL_VISION", "gemini-2.5-pro-preview-06-05")

PORT = int(os.getenv("PORT", 8004))
ENV  = os.getenv("ENV", "development")


# ─────────────────────────────────────────────
#  Logger — shared across all modules
# ─────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_LEVEL  = logging.DEBUG if ENV == "development" else logging.INFO


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with consistent formatting."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)

    logger.setLevel(LOG_LEVEL)
    return logger


# Root logger used in main.py
logger = get_logger("e2m")
