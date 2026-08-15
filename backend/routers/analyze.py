"""
analyze.py — Module 1: Image validation and architectural analysis.

Endpoint: POST /api/analyze
- Accepts a house exterior image upload
- Validates: is it a house? not blurry? exterior view? usable?
- On success: saves image to temp/sessions/{session_id}/ and returns analysis
- On failure: returns rejection reason + suggestion (no session created)
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from services.gemini_client import call_gemini_vision
from utils import (
    create_session_id,
    save_session,
    image_bytes_to_base64,
    get_mime_type,
    Timer,
)
from config import get_logger

logger = get_logger("analyze")

router = APIRouter()


# ─────────────────────────────────────────────
#  Gemini Validation + Analysis Prompt
# ─────────────────────────────────────────────

ANALYSIS_PROMPT = """
You are an architectural image validation and analysis AI.

STEP 1 — VALIDATE the image by checking ALL of the following:
1. Is there a residential building or house clearly visible?
2. Is this an EXTERIOR view? (reject if interior room, aerial top-down, or satellite view)
3. Is the image quality acceptable? (reject if extremely blurry, very dark, or very low resolution)
4. Is the building facade reasonably visible? (reject if completely blocked by trees, vehicles, or people)

If the image FAILS any check:
  - Set "is_valid" to false
  - Set "rejection_reason" to a clear explanation
  - Set "suggestion" to help the user fix the problem

STEP 2 — If valid, ANALYZE the architecture:
  - Count number of visible floors
  - List which regions are present (ONLY from the allowed list below)
  - List protected regions present (windows, doors)
  - Write a brief observation about the house

Return ONLY a valid JSON object. No markdown, no extra text:
{
  "is_valid": true,
  "rejection_reason": null,
  "suggestion": null,
  "image_quality": "good",
  "is_exterior": true,
  "house_detected": true,
  "floors": 2,
  "regions_present": ["main_wall", "pillar", "balcony", "roof", "boundary_wall"],
  "protected_regions": ["window", "door"],
  "confidence": 0.95,
  "notes": "Two-story residential house with front balcony and compound wall"
}

Allowed region values: main_wall, pillar, balcony, roof, boundary_wall
Allowed protected values: window, door
Image quality values: good, acceptable, poor, unusable
""".strip()


# ─────────────────────────────────────────────
#  Route
# ─────────────────────────────────────────────

@router.post("/api/analyze")
async def analyze_image(image: UploadFile = File(...)):
    """
    Upload a house image for validation and analysis.

    On success:
        - Creates a session folder at temp/sessions/{session_id}/
        - Saves original.png inside that folder
        - Saves session.json with analysis metadata
        - Returns session_id + analysis to frontend

    On rejection:
        - Returns reason + suggestion, no session created
    """
    logger.info(f"Upload received: '{image.filename}' ({image.content_type})")

    # 1. Read image bytes
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    file_size_kb = len(image_bytes) / 1024
    logger.debug(f"Image size: {file_size_kb:.1f} KB")

    # 2. Encode to base64 for Gemini
    image_b64 = image_bytes_to_base64(image_bytes)
    mime_type  = get_mime_type(image.filename or "upload.png")

    # 3. Call Gemini Vision for validation + analysis
    with Timer() as t:
        try:
            result = call_gemini_vision(image_b64, mime_type, ANALYSIS_PROMPT)
        except RuntimeError as e:
            logger.error(f"Gemini call failed: {e}")
            raise HTTPException(status_code=502, detail=f"AI analysis failed: {str(e)}")

    logger.info(f"Gemini completed in {t}")

    # 4. Handle rejection — do NOT create a session
    if not result.get("is_valid", False):
        reason     = result.get("rejection_reason", "Image could not be validated.")
        suggestion = result.get("suggestion", "Please upload a clear front-facing photo of a house exterior.")

        logger.warning(f"Image rejected: {reason}")

        return {
            "status":           "rejected",
            "session_id":       None,
            "rejection_reason": reason,
            "suggestion":       suggestion,
            "image_quality":    result.get("image_quality", "unknown"),
        }

    # 5. Create session and persist image to disk
    session_id = create_session_id()

    metadata = {
        "filename":         image.filename,
        "mime_type":        mime_type,
        "file_size_kb":     round(file_size_kb, 1),
        "analysis":         {
            "image_quality":     result.get("image_quality"),
            "floors":            result.get("floors"),
            "regions_present":   result.get("regions_present", []),
            "protected_regions": result.get("protected_regions", []),
            "confidence":        result.get("confidence"),
            "notes":             result.get("notes"),
        },
    }

    save_session(session_id, image_bytes, metadata)

    logger.info(f"Session saved: {session_id}")

    # 6. Return success to frontend
    return {
        "status":       "success",
        "session_id":   session_id,
        "analysis":     metadata["analysis"],
        "elapsed_seconds": t.elapsed,
    }
