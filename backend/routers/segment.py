"""
segment.py — Module 2: Segmentation Router.

Endpoints:
  POST  /api/segment
    - Accepts { session_id }  (image already on disk from Module 1)
    - Runs the full hybrid segmentation pipeline (SegFormer + YOLO + SAM2)
    - Saves individual mask PNGs to temp/sessions/{session_id}/masks/
    - Updates session.json with segmentation results
    - Returns full details: masks (base64), overlay (base64), region stats

  PATCH /api/segment/{session_id}/masks
    - Accepts { region_id, mask_b64 }
    - Overwrites the mask PNG on disk with the user-corrected mask
    - Recalculates pixel_count and coverage_pct for that region
    - Rebuilds the full overlay PNG from all current masks
    - Updates session.json with new stats
    - Returns updated region info + new overlay

Because segmentation takes 3-5 minutes, the response includes elapsed_seconds.
The frontend should show a loading/progress indicator.
"""

import os
import base64
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import get_logger
from utils import (
    load_session,
    update_session,
    session_exists,
    Timer,
)
from services.segmentation import (
    run_segmentation,
    REGION_COLORS,
    REGION_LABELS,
    MASK_PRIORITY,
    PROTECTED_REGIONS,
    EDITABLE_REGIONS,
    _image_to_b64,
    _build_overlay,
)

logger = get_logger("segment")
router = APIRouter()


# ──────────────────────────────────────────────────────────────
#  Request Schemas
# ──────────────────────────────────────────────────────────────

class SegmentRequest(BaseModel):
    session_id: str


class PatchMaskRequest(BaseModel):
    """
    Payload for brush-correction of a single region mask.

    Fields:
        region_id  — which region to update (e.g. "main_wall")
        mask_b64   — full corrected mask as a base64-encoded grayscale PNG
                     (same dimensions as the original image, white = masked)
    """
    region_id: str
    mask_b64:  str


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

    # ── Read original image as base64 (for frontend brush canvas) ───
    try:
        with open(image_path, "rb") as f:
            original_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        original_b64 = ""

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

    # ── Build region detail list (no mask_b64 in this sub-list to keep it tidy) ──
    regions_out = [
        {
            "region_id":    r.region_id,
            "label":        r.label,
            "pixel_count":  r.pixel_count,
            "coverage_pct": r.coverage_pct,
            "bbox":         r.bounding_box,  # mapped to "bbox" for estimate.py
            "color_rgb":    r.color_rgb,
            "is_protected": r.is_protected,
        }
        for r in result.regions
    ]

    # ── Persist segmentation metadata to session.json ───────────
    seg_metadata = {
        "segmentation_data": {
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
            "regions":           regions_out,
        }
    }
    update_session(session_id, seg_metadata)

    # ── Return full response ────────────────────────────────────
    return {
        "status":            "success",
        "session_id":        session_id,
        "image_width":       result.image_width,
        "image_height":      result.image_height,
        "total_pixels":      result.total_pixels,
        "device_used":       result.device_used,
        "elapsed_seconds":   result.elapsed_seconds,

        # Base64 masks (per region) + overlay + original
        "masks":             result.masks_b64,
        "overlay_image":     result.overlay_b64,
        "original_image":    original_b64,    # needed by brush canvas as background

        # Region lists
        "detected_regions":  result.detected_regions,
        "protected_regions": result.protected_regions,
        "region_coverage":   result.region_coverage,

        # Full per-region details
        "regions":           regions_out,
    }


# ──────────────────────────────────────────────────────────────
#  PATCH /api/segment/{session_id}/masks
#  Brush-correction: save a user-edited mask back to disk
# ──────────────────────────────────────────────────────────────

VALID_REGIONS = {
    "main_wall", "pillar", "balcony", "roof",
    "boundary_wall", "window", "door",
}


@router.patch("/api/segment/{session_id}/masks")
async def update_mask(session_id: str, req: PatchMaskRequest):
    """
    Save a user-corrected mask for one region.

    The frontend canvas brush produces a full-size grayscale PNG (same
    dimensions as the original image) where white pixels = masked region
    and black pixels = background.  This endpoint:

      1. Validates session + region name
      2. Decodes the incoming base64 PNG
      3. Validates dimensions match original image
      4. Overwrites masks/{region_id}.png on disk
      5. Recalculates pixel_count + coverage_pct for that region
      6. Rebuilds the full colored overlay from ALL current masks on disk
      7. Updates session.json (region_coverage entry)
      8. Returns updated region info + new overlay_image (base64)

    Input (JSON body):
        {
          "region_id": "main_wall",
          "mask_b64":  "<base64 grayscale PNG>"
        }

    Response:
        {
          "status":       "success",
          "region_id":    "main_wall",
          "pixel_count":  1043200,
          "coverage_pct": 50.3,
          "bounding_box": [0, 120, 1919, 950],
          "overlay_image": "<base64 PNG>",   ← full overlay rebuilt
          "message":      "Mask updated successfully"
        }
    """
    logger.info(f"[{session_id}] PATCH /masks  region={req.region_id}")

    # ── 1. Validate region name ─────────────────────────────────
    if req.region_id not in VALID_REGIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid region_id '{req.region_id}'. "
                   f"Must be one of: {sorted(VALID_REGIONS)}"
        )

    # ── 2. Validate session exists ──────────────────────────────
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    session   = load_session(session_id)
    seg_info  = session.get("segmentation_data")
    if not seg_info:
        raise HTTPException(
            status_code=400,
            detail="Segmentation has not been run for this session yet. "
                   "Call POST /api/segment first."
        )

    image_path = session.get("image_path")
    masks_dir  = seg_info.get("masks_dir")
    img_w      = seg_info.get("image_width")
    img_h      = seg_info.get("image_height")
    total_px   = seg_info.get("total_pixels")

    if not masks_dir or not os.path.exists(masks_dir):
        raise HTTPException(status_code=404, detail="Masks directory not found for this session.")

    # ── 3. Decode incoming mask ─────────────────────────────────
    try:
        mask_bytes = base64.b64decode(req.mask_b64)
        mask_arr   = np.frombuffer(mask_bytes, dtype=np.uint8)
        new_mask   = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Cannot decode mask_b64: {e}")

    if new_mask is None:
        raise HTTPException(status_code=422, detail="mask_b64 did not decode to a valid image.")

    # ── 4. Validate dimensions ──────────────────────────────────
    m_h, m_w = new_mask.shape[:2]
    if m_h != img_h or m_w != img_w:
        raise HTTPException(
            status_code=422,
            detail=f"Mask dimensions {m_w}x{m_h} do not match image {img_w}x{img_h}. "
                   "The corrected mask must be the same size as the original image."
        )

    # ── 5. Save the RAW corrected mask to disk (before conflict resolution) ──
    #  We'll overwrite it again after conflict resolution below.
    mask_file    = os.path.join(masks_dir, f"{req.region_id}.png")
    raw_new_mask = new_mask > 127   # boolean (H, W)
    cv2.imwrite(mask_file, (raw_new_mask.astype(np.uint8)) * 255)
    logger.info(f"[{session_id}] Raw corrected mask saved: {mask_file}")

    # ── 6. Load ALL current masks from disk and inject the corrected one ────
    #  This is the full set of masks that will be conflict-resolved.
    region_masks_all: dict = {}
    for region_id in VALID_REGIONS:
        f = os.path.join(masks_dir, f"{region_id}.png")
        if region_id == req.region_id:
            # Use the newly corrected mask (already in memory)
            region_masks_all[region_id] = raw_new_mask
        elif os.path.exists(f):
            m = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
            if m is not None:
                region_masks_all[region_id] = np.squeeze(m).astype(bool)

    # ── 7. User-intent-aware conflict resolution ──────────────────────────────
    #
    #  KEY PRINCIPLE: The user's manual correction ALWAYS wins.
    #
    #  Example: behind the balcony railing there are windows visible.
    #  The AI labeled those pixels as "window" (priority 7).
    #  The user paints them as "balcony" (priority 3).
    #  Normal priority would give them back to "window" — WRONG!
    #  The user explicitly corrected this, so balcony must win.
    #
    #  Algorithm:
    #    Step A: Assign the corrected region's mask FIRST (infinite priority)
    #    Step B: Subtract those pixels from ALL other regions
    #    Step C: Resolve remaining overlaps among OTHER regions using
    #            the normal priority system
    #
    #  This way:
    #    • User paints balcony over window area → stays balcony ✅
    #    • User paints wall into boundary_wall area → stays wall ✅
    #    • Other regions still resolve among themselves normally ✅

    corrected_id   = req.region_id
    corrected_mask = region_masks_all[corrected_id].copy()

    # Step A: corrected region is assigned first
    assigned       = corrected_mask.copy()
    resolved_masks = {corrected_id: corrected_mask}

    # Step B+C: resolve OTHER regions with normal priority, excluding
    #           any pixels the user already claimed
    other_regions = [
        rid for rid in region_masks_all
        if rid != corrected_id
    ]
    other_sorted = sorted(
        other_regions,
        key=lambda r: MASK_PRIORITY.get(r, 0),
    )

    for rid in reversed(other_sorted):   # highest priority first
        mask = region_masks_all[rid].copy()
        mask &= ~assigned                 # remove user-claimed + already-assigned pixels
        if mask.any():
            resolved_masks[rid] = mask
            assigned |= mask

    logger.info(
        f"[{session_id}] User-intent conflict resolution done. "
        f"Corrected region '{corrected_id}' got priority. "
        f"Regions: {list(resolved_masks.keys())}"
    )

    # ── 8. Save ALL resolved masks back to disk ─────────────────────────────
    #  Important: other regions may also have changed (pixels taken from them
    #  by the user's correction), so all must be re-persisted.
    new_coverage: dict = {}
    for rid, mask in resolved_masks.items():
        mask_path = os.path.join(masks_dir, f"{rid}.png")
        cv2.imwrite(mask_path, (mask.astype(np.uint8)) * 255)
        new_coverage[rid] = round(mask.sum() / total_px * 100, 2)

    # Collect stats for the specifically corrected region
    final_corrected = resolved_masks.get(corrected_id, np.zeros((img_h, img_w), dtype=bool))
    pixel_count     = int(final_corrected.sum())
    coverage        = new_coverage.get(corrected_id, 0.0)

    ys, xs = np.where(final_corrected)
    bbox   = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(ys) > 0 else [0,0,0,0]

    logger.info(
        f"[{session_id}] After resolution — {corrected_id}: "
        f"{pixel_count:,} px ({coverage}%)"
    )

    # ── 9. Rebuild overlay from resolved masks ──────────────────────────────
    orig_bgr = cv2.imread(image_path)
    if orig_bgr is None:
        raise HTTPException(status_code=500, detail="Could not reload original image.")

    overlay_bgr  = _build_overlay(orig_bgr, resolved_masks, REGION_COLORS)
    overlay_path = os.path.join(masks_dir, "overlay.png")
    cv2.imwrite(overlay_path, overlay_bgr)
    overlay_b64  = _image_to_b64(overlay_bgr)

    logger.info(f"[{session_id}] Overlay rebuilt after mask correction.")

    # ── 8. Update session.json ──────────────────────────────────
    current_coverage = seg_info.get("region_coverage", {})
    current_coverage[req.region_id] = coverage
    update_session(session_id, {
        "segmentation": {
            **seg_info,
            "region_coverage": current_coverage,
        }
    })

    # ── 9. Return response ──────────────────────────────────────
    return {
        "status":        "success",
        "region_id":     req.region_id,
        "label":         REGION_LABELS.get(req.region_id, req.region_id),
        "pixel_count":   pixel_count,
        "coverage_pct":  coverage,
        "bounding_box":  bbox,
        "color_rgb":     list(REGION_COLORS.get(req.region_id, (200, 200, 200))),
        "is_protected":  req.region_id in PROTECTED_REGIONS,
        "overlay_image": overlay_b64,
        "message":       f"Mask for '{req.region_id}' updated successfully.",
    }
