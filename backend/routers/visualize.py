"""
visualize.py — Module 4: Visualization Router

POST /api/visualize
  Input:  { session_id }
  Flow:
    1. Load session → get material_selections + composite_path
    2. Gemini Vision analyzes composite image → house description
    3. Build detailed FLUX prompt from materials + description
    4. HuggingFace img2img → photorealistic visualization
  Output: { visualization_image: base64_png, prompt_used: str }

GET /api/visualize/{session_id}
  Returns the cached visualization image.
"""

import os
import base64

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from config import logger, BASE_DIR
from utils import load_session, session_exists, update_session
from services.visualizer import build_prompt, generate_visualization
from services.gemini_client import call_gemini_vision

router = APIRouter()

HF_TOKEN     = os.getenv("HF_TOKEN", "")
SESSIONS_DIR = os.path.join(BASE_DIR, "temp", "sessions")

# ── Gemini prompt to describe the house ───────────────────────
GEMINI_HOUSE_PROMPT = """
Look at this house exterior image.
Describe it in ONE concise sentence (max 30 words) covering:
- Architectural style (e.g. modern, colonial, contemporary)
- Number of floors
- Key structural features visible (e.g. arches, flat roof, pillars)

Return ONLY the description sentence, no JSON, no extra text.
Example: "A two-story modern Indian house with flat roof, large pillars, and a prominent balcony on the upper floor."
"""


# ── Request Model ──────────────────────────────────────────────
class VisualizeRequest(BaseModel):
    session_id: str


# ── POST /api/visualize ────────────────────────────────────────
@router.post("/api/visualize")
async def visualize(req: VisualizeRequest):
    """
    Generate a photorealistic AI visualization of the renovated house.
    Uses the composite image (materials applied) + FLUX img2img.
    Takes ~15-30 seconds.
    """
    session_id = req.session_id

    # ── 1. Validate session ──────────────────────────────────────
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    session = load_session(session_id)
    material_selections = session.get("material_selections")
    composite_path      = session.get("composite_path")
    image_path          = session.get("image_path")

    if not material_selections:
        raise HTTPException(
            status_code=400,
            detail="No material selections found. Complete Module 3 first."
        )

    if not composite_path or not os.path.exists(composite_path):
        raise HTTPException(
            status_code=400,
            detail="Composite image not found. Complete Module 3 first."
        )

    logger.info(f"[{session_id}] Visualization requested — {len(material_selections)} regions")

    # ── 2. Gemini Vision — describe the house ───────────────────
    house_description = ""
    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            # Gemini returns raw text here, not JSON
            # We call it slightly differently - use the raw text path
            house_description = _call_gemini_text(img_b64, "image/png", GEMINI_HOUSE_PROMPT)
            logger.info(f"[{session_id}] House description: {house_description[:80]}...")
        else:
            logger.warning(f"[{session_id}] Original image not found, skipping Gemini step")
    except Exception as e:
        logger.warning(f"[{session_id}] Gemini house description failed: {e}")
        house_description = ""  # continue without it

    # ── 3. Build prompt ──────────────────────────────────────────
    prompt = build_prompt(material_selections, house_description)
    logger.info(f"[{session_id}] Prompt built ({len(prompt)} chars)")

    # ── 4. Generate visualization ────────────────────────────────
    if not HF_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="HF_TOKEN not configured. Add it to backend/.env"
        )

    try:
        viz_bytes = generate_visualization(
            composite_path=composite_path,
            prompt=prompt,
            hf_token=HF_TOKEN,
        )
    except Exception as e:
        logger.error(f"[{session_id}] Visualization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Visualization failed: {str(e)}")

    # ── 5. Save to disk ──────────────────────────────────────────
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    viz_path    = os.path.join(session_dir, "visualization.png")
    with open(viz_path, "wb") as f:
        f.write(viz_bytes)

    viz_b64 = base64.b64encode(viz_bytes).decode("utf-8")

    update_session(session_id, {
        "visualization_path": viz_path,
        "visualization_prompt": prompt,
    })

    logger.info(f"[{session_id}] Visualization saved: {viz_path}")

    return {
        "status":               "success",
        "session_id":           session_id,
        "visualization_image":  viz_b64,
        "prompt_used":          prompt,
        "house_description":    house_description,
    }


# ── GET /api/visualize/{session_id} ───────────────────────────
@router.get("/api/visualize/{session_id}")
async def get_visualization(session_id: str):
    """Return the cached AI visualization for a session."""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    session  = load_session(session_id)
    viz_path = session.get("visualization_path")

    if not viz_path or not os.path.exists(viz_path):
        raise HTTPException(
            status_code=404,
            detail="No visualization generated yet. Call POST /api/visualize first."
        )

    with open(viz_path, "rb") as f:
        viz_b64 = base64.b64encode(f.read()).decode("utf-8")

    return {
        "status":              "success",
        "session_id":          session_id,
        "visualization_image": viz_b64,
        "prompt_used":         session.get("visualization_prompt", ""),
    }


# ── Internal: Gemini text-only response (not JSON) ─────────────
def _call_gemini_text(image_b64: str, mime_type: str, prompt: str) -> str:
    """Call Gemini Vision and return raw text (not parsed JSON)."""
    import requests, google.auth.transport.requests
    from google.oauth2 import service_account
    from config import (
        GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS,
        VERTEX_LOCATION, GEMINI_MODEL_VISION,
    )

    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_APPLICATION_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())

    url = (
        f"https://aiplatform.googleapis.com/v1/projects/{GOOGLE_CLOUD_PROJECT}"
        f"/locations/{VERTEX_LOCATION}/publishers/google/models/{GEMINI_MODEL_VISION}:generateContent"
    )

    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"inlineData": {"mimeType": mime_type, "data": image_b64}},
                {"text": prompt},
            ],
        }],
        "generationConfig": {"temperature": 0.2},
    }

    resp = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Gemini error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
