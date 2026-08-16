"""
segment.py — Module 2: Segmentation Router.

Endpoint: POST /api/segment
  - Accepts { session_id }  (image already on disk from Module 1)
  - Runs the full hybrid segmentation pipeline (SegFormer + YOLO + SAM2)
  - Saves individual mask PNGs to temp/sessions/{session_id}/masks/
  - Updates session.json with segmentation results
  - Returns full details: masks (base64), overlay (base64), region stats

Because segmentation takes 3-5 minutes, the response includes elapsed_seconds.
The frontend should show a loading/progress indicator.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import get_logger
from utils import (
    load_session,
    update_session,
    session_exists,
    Timer,
)
from services.segmentation import run_segmentation

logger = get_logger("segment")
router = APIRouter()


# ──────────────────────────────────────────────────────────────
#  Request Schema
# ──────────────────────────────────────────────────────────────

class SegmentRequest(BaseModel):
    session_id: str


# ──────────────────────────────────────────────────────────────
#  Route
# ──────────────────────────────────────────────────────────────

@router.post("/api/segment")
async def segment_image(req: SegmentRequest):
    """
    Run segmentation on the image stored for a given session.

    Input (JSON body):
        { "session_id": "<uuid>" }

    Returns:
        {
          "status":           "success",
          "session_id":       "...",
          "image_width":      1920,
          "image_height":     1080,
          "total_pixels":     2073600,
          "device_used":      "cuda",
          "elapsed_seconds":  247.3,

          "masks": {
              "main_wall":     "<base64 PNG>",
              "pillar":        "<base64 PNG>",
              ...
          },
          "overlay_image":    "<base64 PNG>",           ← colored overlay

          "detected_regions":  ["main_wall", "pillar", ...],   ← editable
          "protected_regions": ["window", "door"],              ← read-only
          "region_coverage":   { "main_wall": 51.9, ... },     ← % of image

          "regions": [
              {
                "region_id":    "main_wall",
                "label":        "Main Wall",
                "pixel_count":  1075450,
                "coverage_pct": 51.9,
                "bounding_box": [0, 120, 1919, 950],
                "color_rgb":    [255, 80, 80],
                "is_protected": false
              },
              ...
          ]
        }
    """
    session_id = req.session_id
    logger.info(f"[{session_id}] /api/segment called")

    # ── Validate session ────────────────────────────────────────
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    session = load_session(session_id)
    image_path = session.get("image_path")

    if not image_path or not os.path.exists(image_path):
        raise HTTPException(
            status_code=404,
            detail=f"Original image not found for session {session_id}. Run /api/analyze first."
        )

    # ── Determine masks directory ───────────────────────────────
    masks_dir = os.path.join(os.path.dirname(image_path), "masks")

    # ── Run segmentation ────────────────────────────────────────
    logger.info(f"[{session_id}] Starting segmentation pipeline...")
    try:
        with Timer() as t:
            result = run_segmentation(
                image_path = image_path,
                session_id = session_id,
                masks_dir  = masks_dir,
            )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[{session_id}] Segmentation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")

    logger.info(f"[{session_id}] Segmentation done in {t}. Regions: {result.detected_regions}")

    # ── Persist segmentation metadata to session.json ───────────
    seg_metadata = {
        "segmentation": {
            "status":            "done",
            "elapsed_seconds":   result.elapsed_seconds,
            "device_used":       result.device_used,
            "image_width":       result.image_width,
            "image_height":      result.image_height,
            "total_pixels":      result.total_pixels,
            "detected_regions":  result.detected_regions,
            "protected_regions": result.protected_regions,
            "region_coverage":   result.region_coverage,
            "masks_dir":         masks_dir,
        }
    }
    update_session(session_id, seg_metadata)

    # ── Build region detail list (no mask_b64 in this sub-list to keep it tidy) ──
    regions_out = [
        {
            "region_id":    r.region_id,
            "label":        r.label,
            "pixel_count":  r.pixel_count,
            "coverage_pct": r.coverage_pct,
            "bounding_box": r.bounding_box,
            "color_rgb":    r.color_rgb,
            "is_protected": r.is_protected,
        }
        for r in result.regions
    ]

    # ── Return full response ────────────────────────────────────
    return {
        "status":            "success",
        "session_id":        session_id,
        "image_width":       result.image_width,
        "image_height":      result.image_height,
        "total_pixels":      result.total_pixels,
        "device_used":       result.device_used,
        "elapsed_seconds":   result.elapsed_seconds,

        # Base64 masks (per region) + overlay
        "masks":             result.masks_b64,
        "overlay_image":     result.overlay_b64,

        # Region lists
        "detected_regions":  result.detected_regions,
        "protected_regions": result.protected_regions,
        "region_coverage":   result.region_coverage,

        # Full per-region details
        "regions":           regions_out,
    }
