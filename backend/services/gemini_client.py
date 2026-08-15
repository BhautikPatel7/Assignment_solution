"""
gemini_client.py — Calls Gemini Vision via Vertex AI REST API.
Shared by all modules that need to call Gemini.
"""

import json
import requests
import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account

from config import (
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_APPLICATION_CREDENTIALS,
    VERTEX_LOCATION,
    GEMINI_MODEL_VISION,
    get_logger,
)

logger = get_logger("gemini_client")


def _get_access_token() -> str:
    """Get a short-lived OAuth2 access token from the service account."""
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_APPLICATION_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())
    logger.debug("Gemini access token refreshed")
    return creds.token


def call_gemini_vision(image_b64: str, mime_type: str, prompt: str) -> dict:
    """
    Send an image + text prompt to Gemini Vision and return parsed JSON.

    Args:
        image_b64:  Base64-encoded image string
        mime_type:  e.g. "image/png" or "image/jpeg"
        prompt:     The text instruction for Gemini

    Returns:
        Parsed dict from Gemini's JSON response

    Raises:
        RuntimeError: If the API call fails or JSON cannot be parsed
    """
    token = _get_access_token()

    url = (
        f"https://aiplatform.googleapis.com/v1/projects/{GOOGLE_CLOUD_PROJECT}"
        f"/locations/{VERTEX_LOCATION}/publishers/google/models/{GEMINI_MODEL_VISION}:generateContent"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inlineData": {"mimeType": mime_type, "data": image_b64}},
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    logger.info(f"Calling Gemini Vision: {GEMINI_MODEL_VISION}")

    resp = requests.post(url, json=payload, headers=headers, timeout=120)

    if resp.status_code != 200:
        logger.error(f"Gemini API error: {resp.status_code} — {resp.text[:300]}")
        raise RuntimeError(f"Gemini API returned {resp.status_code}: {resp.text[:200]}")

    data = resp.json()

    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Strip markdown code fences if present
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

        result = json.loads(raw.strip())
        logger.info("Gemini response parsed successfully")
        return result

    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        raise RuntimeError(f"Could not parse Gemini response: {e}")
