"""
composite.py — Module 4: Composite Router

POST /api/composite
  Input:  { session_id, selections: { region_id: { type, value } } }
  Output: { composite_image: base64_png, session_id }

GET /api/composite/{session_id}
  Returns the last saved composite for a session (cached).
"""

import os
import base64
import numpy as np
import cv2

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Optional

from config import logger, BASE_DIR
from utils import load_session, session_exists, update_session
from services.compositor import build_composite

router = APIRouter()

# Textures stored next to backend code for server-side access
TEXTURES_DIR = os.path.join(BASE_DIR, "static", "textures")
os.makedirs(TEXTURES_DIR, exist_ok=True)


# ── Request / Response models ──────────────────────────────────

class MaterialSelection(BaseModel):
    type:  str = Field(..., description="'paint' or 'texture'")
    value: str = Field(..., description="Hex color (e.g. '#F5F5F0') or texture filename (e.g. 'stone_natural.jpg')")


class CompositeRequest(BaseModel):
    session_id: str
    selections: Dict[str, MaterialSelection] = Field(
        default_factory=dict,
        description="Map of region_id → material selection"
    )


# ── POST /api/composite ────────────────────────────────────────

@router.post("/api/composite")
async def composite_image(req: CompositeRequest):
    """
    Apply selected materials to the house image and return composite.
    Fast (~0.5-1s). Called live whenever user changes a material selection.
    """
    session_id = req.session_id

    # ── 1. Validate session ──────────────────────────────────────
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    session  = load_session(session_id)
    seg_info = session.get("segmentation_data")

    if not seg_info:
        raise HTTPException(
            status_code=400,
            detail="Segmentation not run yet. Call POST /api/segment first."
        )

    image_path = session.get("image_path")
    masks_dir  = seg_info.get("masks_dir")

    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Original image not found.")
    if not masks_dir or not os.path.exists(masks_dir):
        raise HTTPException(status_code=404, detail="Masks directory not found.")

    # ── 2. Convert selections to plain dicts ─────────────────────
    selections_dict = {
        rid: {"type": sel.type, "value": sel.value}
        for rid, sel in req.selections.items()
    }

    logger.info(f"[{session_id}] Composite requested — {len(selections_dict)} regions")

    # ── 3. Run compositor ────────────────────────────────────────
    try:
        composite_bgr = build_composite(
            image_path   = image_path,
            masks_dir    = masks_dir,
            selections   = selections_dict,
            textures_dir = TEXTURES_DIR,
        )
    except Exception as e:
        logger.error(f"[{session_id}] Composite error: {e}")
        raise HTTPException(status_code=500, detail=f"Composite failed: {str(e)}")

    # ── 4. Encode to base64 PNG ──────────────────────────────────
    ok, buf = cv2.imencode(".png", composite_bgr)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode composite image.")
    composite_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    # ── 5. Save composite to disk (for later use by visualize/estimate) ──
    composite_path = os.path.join(os.path.dirname(image_path), "composite.png")
    cv2.imwrite(composite_path, composite_bgr)

    # ── 6. Save selections to session.json ──────────────────────
    update_session(session_id, {
        "material_selections": selections_dict,
        "composite_path":      composite_path,
    })

    logger.info(f"[{session_id}] Composite done. Saved to {composite_path}")

    return {
        "status":          "success",
        "session_id":      session_id,
        "composite_image": composite_b64,
        "regions_applied": list(selections_dict.keys()),
    }


# ── GET /api/composite/{session_id} ───────────────────────────

@router.get("/api/composite/{session_id}")
async def get_composite(session_id: str):
    """Return the last saved composite image for a session."""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    session        = load_session(session_id)
    composite_path = session.get("composite_path")

    if not composite_path or not os.path.exists(composite_path):
        raise HTTPException(
            status_code=404,
            detail="No composite generated yet. Call POST /api/composite first."
        )

    with open(composite_path, "rb") as f:
        composite_b64 = base64.b64encode(f.read()).decode("utf-8")

    return {
        "status":             "success",
        "session_id":         session_id,
        "composite_image":    composite_b64,
        "material_selections": session.get("material_selections", {}),
    }
