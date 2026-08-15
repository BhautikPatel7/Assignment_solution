"""
utils.py — Common utility functions shared across all modules.
"""

import os
import uuid
import json
import base64
import time
import shutil
from datetime import datetime, timezone
from config import get_logger

logger = get_logger("utils")

# ─────────────────────────────────────────────
#  Session Storage Root
#  Each session gets its own folder:
#  temp/sessions/{session_id}/
#      original.png      — uploaded image
#      session.json      — metadata (analysis result, regions, etc.)
#      masks/            — segmentation masks (added in M2)
# ─────────────────────────────────────────────

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "temp", "sessions")


def _session_dir(session_id: str) -> str:
    """Return the directory path for a given session."""
    return os.path.join(SESSIONS_DIR, session_id)


def _session_json_path(session_id: str) -> str:
    """Return the session.json path for a given session."""
    return os.path.join(_session_dir(session_id), "session.json")


def _image_path(session_id: str) -> str:
    """Return the original image path for a given session."""
    return os.path.join(_session_dir(session_id), "original.png")


# ─────────────────────────────────────────────
#  Session Lifecycle
# ─────────────────────────────────────────────

def create_session_id() -> str:
    """Generate a unique session ID (UUID4)."""
    return str(uuid.uuid4())


def save_session(session_id: str, image_bytes: bytes, metadata: dict) -> str:
    """
    Create the session folder, save the uploaded image, and write session.json.

    Args:
        session_id:   UUID string
        image_bytes:  Raw bytes of the uploaded image
        metadata:     Dict of data to persist (analysis result, filename, etc.)

    Returns:
        Path to the session directory
    """
    session_dir = _session_dir(session_id)
    os.makedirs(session_dir, exist_ok=True)
    os.makedirs(os.path.join(session_dir, "masks"), exist_ok=True)

    # Save original image
    image_file = _image_path(session_id)
    with open(image_file, "wb") as f:
        f.write(image_bytes)
    logger.debug(f"[{session_id}] Image saved: {image_file}")

    # Save session metadata
    session_data = {
        "session_id":  session_id,
        "created_at":  datetime.now(timezone.utc).isoformat(),
        "image_path":  image_file,
        **metadata,
    }
    with open(_session_json_path(session_id), "w") as f:
        json.dump(session_data, f, indent=2)
    logger.info(f"[{session_id}] Session created at {session_dir}")

    return session_dir


def load_session(session_id: str) -> dict:
    """
    Load session metadata from session.json.

    Returns:
        Session dict

    Raises:
        FileNotFoundError: If session does not exist
    """
    json_path = _session_json_path(session_id)
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Session not found: {session_id}")

    with open(json_path) as f:
        return json.load(f)


def update_session(session_id: str, updates: dict) -> dict:
    """
    Merge updates into an existing session and save.

    Returns:
        Updated session dict
    """
    session = load_session(session_id)
    session.update(updates)
    with open(_session_json_path(session_id), "w") as f:
        json.dump(session, f, indent=2)
    logger.debug(f"[{session_id}] Session updated: {list(updates.keys())}")
    return session


def load_session_image(session_id: str) -> bytes:
    """
    Load the original image bytes for a session.

    Returns:
        Raw image bytes

    Raises:
        FileNotFoundError: If session or image does not exist
    """
    path = _image_path(session_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found for session: {session_id}")
    with open(path, "rb") as f:
        return f.read()


def delete_session(session_id: str):
    """Delete the entire session folder (cleanup)."""
    session_dir = _session_dir(session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
        logger.info(f"[{session_id}] Session deleted")


def session_exists(session_id: str) -> bool:
    """Check if a session exists."""
    return os.path.exists(_session_json_path(session_id))


# ─────────────────────────────────────────────
#  Image Helpers
# ─────────────────────────────────────────────

def image_bytes_to_base64(image_bytes: bytes) -> str:
    """Convert raw image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def base64_to_image_bytes(b64_str: str) -> bytes:
    """Convert base64 string back to raw bytes."""
    return base64.b64decode(b64_str)


def get_mime_type(filename: str) -> str:
    """Guess MIME type from filename extension."""
    filename = filename.lower()
    if filename.endswith(".png"):
        return "image/png"
    elif filename.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    elif filename.endswith(".webp"):
        return "image/webp"
    return "image/png"


# ─────────────────────────────────────────────
#  Response Helpers
# ─────────────────────────────────────────────

def success_response(data: dict) -> dict:
    """Wrap data in a standard success envelope."""
    return {"status": "success", "data": data}


def error_response(message: str, code: str = "ERROR") -> dict:
    """Wrap error message in a standard error envelope."""
    return {"status": "error", "error": {"code": code, "message": message}}


# ─────────────────────────────────────────────
#  Timing Helper
# ─────────────────────────────────────────────

class Timer:
    """Simple context manager to measure elapsed time."""

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = round(time.perf_counter() - self._start, 2)

    def __str__(self):
        return f"{self.elapsed}s"
