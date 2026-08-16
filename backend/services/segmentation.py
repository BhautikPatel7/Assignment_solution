"""
segmentation.py — Module 2: High-Accuracy Hybrid Segmentation Service.

Pipeline:
  Phase 1  — SegFormer-b4 sliding window (50% overlap tiles)
  Phase 2  — YOLO-World + SAM2 (area-constrained)
  Phase 3  — Morphological cleanup + priority-based conflict resolution

Entry point: run_segmentation(image_path) → SegmentationResult
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import cv2
import numpy as np
import torch
from PIL import Image

from config import get_logger

logger = get_logger("segmentation")

# ──────────────────────────────────────────────────────────────
#  Constants (mirrored from test_m1_m2.py)
# ──────────────────────────────────────────────────────────────

# ADE20K class → region
ADE20K_TO_REGION: Dict[int, str] = {
    0:  "main_wall",      # wall
    1:  "main_wall",      # building / facade
    8:  "window",         # windowpane
    14: "door",           # door
    18: "window",         # curtain
    25: "main_wall",      # house
    32: "boundary_wall",  # fence
    42: "pillar",         # column / pillar
}

YOLO_CLASSES = ["wall", "roof", "pillar", "balcony", "fence", "window", "door"]
YOLO_TO_REGION: Dict[str, Optional[str]] = {
    "wall":    None,
    "roof":    "roof",
    "pillar":  "pillar",
    "balcony": "balcony",
    "fence":   "boundary_wall",
    "window":  "window",
    "door":    "door",
}
YOLO_CONF = 0.03

MAX_AREA_FRACTION: Dict[str, float] = {
    "roof":          0.10,
    "pillar":        0.05,
    "balcony":       0.15,
    "boundary_wall": 0.20,
    "window":        0.10,
    "door":          0.10,
}

MAX_BOX_FRACTION: Dict[str, float] = {
    "roof":          0.10,
    "pillar":        0.10,
    "balcony":       0.20,
    "boundary_wall": 0.25,
    "window":        0.15,
    "door":          0.15,
}
DEFAULT_MAX_BOX_FRACTION = 0.35

MASK_PRIORITY: Dict[str, int] = {
    "main_wall":     1,
    "roof":          2,
    "balcony":       3,
    "boundary_wall": 4,
    "pillar":        5,
    "window":        7,
    "door":          8,
}

# Colors for overlay (RGB)
REGION_COLORS: Dict[str, tuple] = {
    "main_wall":     (255,  80,  80),
    "pillar":        ( 80,  80, 255),
    "balcony":       (255, 200,  50),
    "roof":          ( 50, 200, 200),
    "boundary_wall": (200, 150,  50),
    "window":        (100, 200, 100),
    "door":          (255, 140,   0),
}

REGION_LABELS: Dict[str, str] = {
    "main_wall":     "Main Wall",
    "pillar":        "Pillar",
    "balcony":       "Balcony",
    "roof":          "Roof",
    "boundary_wall": "Boundary Wall",
    "window":        "Window",
    "door":          "Door",
}

PROTECTED_REGIONS = {"window", "door"}
EDITABLE_REGIONS  = {"main_wall", "pillar", "balcony", "roof", "boundary_wall"}

TILE_SIZE   = 512
TILE_STRIDE = 256   # 50% overlap

MIN_MASK_PIXELS = 500
THIN_REGIONS    = {"pillar"}


# ──────────────────────────────────────────────────────────────
#  Data classes
# ──────────────────────────────────────────────────────────────

@dataclass
class RegionInfo:
    region_id:    str
    label:        str
    pixel_count:  int
    coverage_pct: float
    mask_b64:     str        # PNG mask encoded as base64
    bounding_box: List[int]  # [x1, y1, x2, y2] in pixels
    color_rgb:    List[int]  # [R, G, B] display color
    is_protected: bool       # True for window / door


@dataclass
class SegmentationResult:
    session_id:       str
    image_width:      int
    image_height:     int
    total_pixels:     int
    masks_b64:        Dict[str, str]         # region_id → base64 PNG mask
    overlay_b64:      str                    # colored overlay PNG as base64
    regions:          List[RegionInfo]
    detected_regions: List[str]              # editable only
    protected_regions: List[str]
    region_coverage:  Dict[str, float]       # region_id → % of image
    elapsed_seconds:  float
    device_used:      str


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _mask_to_b64(mask_bool: np.ndarray) -> str:
    """Convert a boolean 2-D mask to a base64-encoded PNG string."""
    mask_uint8 = (mask_bool.astype(np.uint8)) * 255
    ok, buf = cv2.imencode(".png", mask_uint8)
    if not ok:
        raise RuntimeError("cv2.imencode failed for mask")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _image_to_b64(image_bgr: np.ndarray) -> str:
    """Convert a BGR numpy image to base64-encoded PNG string."""
    ok, buf = cv2.imencode(".png", image_bgr)
    if not ok:
        raise RuntimeError("cv2.imencode failed for image")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


# ──────────────────────────────────────────────────────────────
#  Main Pipeline
# ──────────────────────────────────────────────────────────────

def run_segmentation(image_path: str, session_id: str, masks_dir: str) -> SegmentationResult:
    """
    Full hybrid segmentation pipeline.

    Args:
        image_path:  Absolute path to the original.png saved by Module 1.
        session_id:  UUID string for the session.
        masks_dir:   Directory where individual mask PNGs will be saved.

    Returns:
        SegmentationResult with all masks + overlay as base64 strings.
    """
    import time
    t0 = time.perf_counter()

    # ── Load image ─────────────────────────────────────────────
    logger.info(f"[{session_id}] Loading image: {image_path}")
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    h, w      = image_bgr.shape[:2]
    total_px  = h * w
    logger.info(f"[{session_id}] Image size: {w}x{h} ({total_px:,} px)")

    os.makedirs(masks_dir, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"[{session_id}] Device: {device}")

    # ── Phase 1: SegFormer sliding window ─────────────────────
    region_masks = _phase1_segformer(image_rgb, h, w, total_px, device, session_id)

    # ── Phase 2: YOLO-World + SAM2 ────────────────────────────
    region_masks = _phase2_yolo_sam2(image_path, image_bgr, region_masks,
                                     total_px, device, session_id)

    # ── Phase 3: Post-processing ───────────────────────────────
    region_masks = _phase3_cleanup(region_masks, h, w, total_px, session_id)

    # ── Build results ──────────────────────────────────────────
    masks_b64: Dict[str, str] = {}
    regions:   List[RegionInfo] = []

    for region_id, mask_bool in region_masks.items():
        pixel_count  = int(mask_bool.sum())
        coverage_pct = round(pixel_count / total_px * 100, 2)

        # Save mask PNG to disk
        mask_uint8 = (mask_bool.astype(np.uint8)) * 255
        mask_file  = os.path.join(masks_dir, f"{region_id}.png")
        cv2.imwrite(mask_file, mask_uint8)

        # Base64
        b64 = _mask_to_b64(mask_bool)
        masks_b64[region_id] = b64

        # Bounding box
        ys, xs = np.where(mask_bool)
        if len(ys) == 0:
            bbox = [0, 0, 0, 0]
        else:
            bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]

        color_rgb = list(REGION_COLORS.get(region_id, (200, 200, 200)))

        regions.append(RegionInfo(
            region_id    = region_id,
            label        = REGION_LABELS.get(region_id, region_id.replace("_", " ").title()),
            pixel_count  = pixel_count,
            coverage_pct = coverage_pct,
            mask_b64     = b64,
            bounding_box = bbox,
            color_rgb    = color_rgb,
            is_protected = region_id in PROTECTED_REGIONS,
        ))

    # ── Overlay ────────────────────────────────────────────────
    overlay_bgr = _build_overlay(image_bgr, region_masks, REGION_COLORS)
    overlay_path = os.path.join(masks_dir, "overlay.png")
    cv2.imwrite(overlay_path, overlay_bgr)
    overlay_b64 = _image_to_b64(overlay_bgr)

    elapsed = round(time.perf_counter() - t0, 2)
    logger.info(f"[{session_id}] Segmentation complete in {elapsed}s")

    detected_regions  = [r.region_id for r in regions if r.region_id in EDITABLE_REGIONS]
    protected_regions = [r.region_id for r in regions if r.region_id in PROTECTED_REGIONS]
    region_coverage   = {r.region_id: r.coverage_pct for r in regions}

    return SegmentationResult(
        session_id        = session_id,
        image_width       = w,
        image_height      = h,
        total_pixels      = total_px,
        masks_b64         = masks_b64,
        overlay_b64       = overlay_b64,
        regions           = regions,
        detected_regions  = detected_regions,
        protected_regions = protected_regions,
        region_coverage   = region_coverage,
        elapsed_seconds   = elapsed,
        device_used       = device,
    )


# ──────────────────────────────────────────────────────────────
#  Phase 1: SegFormer-b4 Sliding Window
# ──────────────────────────────────────────────────────────────

def _phase1_segformer(
    image_rgb: np.ndarray,
    h: int, w: int, total_px: int,
    device: str, session_id: str,
) -> Dict[str, np.ndarray]:
    """Run SegFormer-b4 with 50% overlap sliding window. Returns bool masks."""
    from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

    logger.info(f"[{session_id}] Phase 1 — SegFormer sliding window")
    model_name = "nvidia/segformer-b4-finetuned-ade-512-512"
    processor  = SegformerImageProcessor.from_pretrained(model_name)
    seg_model  = SegformerForSemanticSegmentation.from_pretrained(model_name).to(device)
    seg_model.eval()

    num_classes = seg_model.config.num_labels
    logit_sum   = np.zeros((num_classes, h, w), dtype=np.float32)
    count_map   = np.zeros((h, w), dtype=np.float32)

    y_positions = list(range(0, h - TILE_SIZE + 1, TILE_STRIDE))
    if not y_positions or y_positions[-1] + TILE_SIZE < h:
        y_positions.append(max(0, h - TILE_SIZE))

    x_positions = list(range(0, w - TILE_SIZE + 1, TILE_STRIDE))
    if not x_positions or x_positions[-1] + TILE_SIZE < w:
        x_positions.append(max(0, w - TILE_SIZE))

    total_tiles = len(y_positions) * len(x_positions)
    tile_idx    = 0

    for y0 in y_positions:
        for x0 in x_positions:
            tile_idx += 1
            y1 = min(y0 + TILE_SIZE, h)
            x1 = min(x0 + TILE_SIZE, w)

            tile_rgb  = image_rgb[y0:y1, x0:x1]
            tile_h, tile_w = tile_rgb.shape[:2]
            tile_pil  = Image.fromarray(tile_rgb)

            inputs = processor(images=tile_pil, return_tensors="pt").to(device)
            with torch.no_grad():
                outputs = seg_model(**inputs)

            tile_logits = torch.nn.functional.interpolate(
                outputs.logits, size=(tile_h, tile_w),
                mode="bilinear", align_corners=False,
            )[0].cpu().numpy()

            logit_sum[:, y0:y1, x0:x1] += tile_logits
            count_map[y0:y1, x0:x1]    += 1.0

            if tile_idx % 10 == 0 or tile_idx == total_tiles:
                logger.debug(f"[{session_id}]   Tile {tile_idx}/{total_tiles}")

    count_map = np.maximum(count_map, 1.0)
    for c in range(num_classes):
        logit_sum[c] /= count_map

    seg_map = logit_sum.argmax(axis=0)

    # Log detected classes
    detected_classes = sorted(np.unique(seg_map).tolist())
    id2label         = seg_model.config.id2label
    class_names      = [id2label.get(str(c), id2label.get(c, f"cls_{c}")) for c in detected_classes]
    logger.info(f"[{session_id}]   ADE20K classes found: {class_names}")

    # Free GPU memory
    del seg_model, logit_sum, count_map
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Build region masks from seg_map
    region_masks: Dict[str, np.ndarray] = {}
    for ade_cls, region_id in ADE20K_TO_REGION.items():
        cls_mask = (seg_map == ade_cls)
        if cls_mask.any():
            if region_id not in region_masks:
                region_masks[region_id] = np.zeros((h, w), dtype=bool)
            region_masks[region_id] |= cls_mask

    for rid, mask in region_masks.items():
        pct = round(mask.sum() / total_px * 100, 1)
        logger.info(f"[{session_id}]   SegFormer → {rid}: {pct}%")

    return region_masks


# ──────────────────────────────────────────────────────────────
#  Phase 2: YOLO-World + SAM2
# ──────────────────────────────────────────────────────────────

def _phase2_yolo_sam2(
    image_path: str,
    image_bgr: np.ndarray,
    region_masks: Dict[str, np.ndarray],
    total_px: int,
    device: str,
    session_id: str,
) -> Dict[str, np.ndarray]:
    """Run YOLO-World detection then SAM2 mask refinement. Updates region_masks in-place."""
    from ultralytics import YOLO, SAM

    logger.info(f"[{session_id}] Phase 2 — YOLO-World + SAM2")
    h, w = image_bgr.shape[:2]

    yolo = YOLO("yolov8s-worldv2.pt")
    yolo.set_classes(YOLO_CLASSES)

    yolo_results = yolo.predict(source=image_path, conf=YOLO_CONF, device=device, verbose=False)[0]
    boxes = yolo_results.boxes
    names = yolo_results.names

    yolo_regions: Dict[str, List] = {}
    for box in boxes:
        cls_name  = names[int(box.cls[0])]
        conf      = float(box.conf[0])
        xyxy      = box.xyxy[0].cpu().numpy().astype(int).tolist()
        region_id = YOLO_TO_REGION.get(cls_name, cls_name)

        if region_id is None:
            continue

        box_area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])
        box_frac = box_area / total_px
        max_box  = MAX_BOX_FRACTION.get(region_id, DEFAULT_MAX_BOX_FRACTION)

        if box_frac > max_box:
            if region_id == "roof":
                # Smart clip: keep top 25% of oversized roof box
                box_h    = xyxy[3] - xyxy[1]
                xyxy[3]  = xyxy[1] + int(box_h * 0.25)
                new_frac = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1]) / total_px
                logger.info(f"[{session_id}]   CLIP roof → top 25% → {xyxy} ({new_frac:.1%})")
            else:
                logger.info(f"[{session_id}]   SKIP {region_id} conf={conf:.2f} (too large: {box_frac:.1%})")
                continue

        logger.info(f"[{session_id}]   YOLO → {region_id} conf={conf:.2f} {xyxy} ({box_frac:.1%})")
        yolo_regions.setdefault(region_id, []).append(xyxy)

    if not yolo_regions:
        logger.info(f"[{session_id}]   YOLO found nothing extra.")
        return region_masks

    sam = SAM("sam2_b.pt")
    for region_id, box_list in yolo_regions.items():
        # Skip if SegFormer already gave good coverage
        if region_id in region_masks:
            existing_pct = region_masks[region_id].sum() / total_px * 100
            if existing_pct > 1.0:
                logger.info(f"[{session_id}]   Skip {region_id} (SegFormer has {existing_pct:.1f}%)")
                continue

        sam_result = sam.predict(source=image_path, bboxes=box_list, device=device, verbose=False)[0]

        if sam_result.masks is None or len(sam_result.masks) == 0:
            continue

        mask_data = sam_result.masks.data.cpu().numpy().astype(bool)
        combined  = np.any(mask_data, axis=0) if mask_data.ndim == 3 else mask_data

        max_frac  = MAX_AREA_FRACTION.get(region_id, 0.5)
        mask_frac = combined.sum() / total_px
        if mask_frac > max_frac:
            logger.info(f"[{session_id}]   TRIM {region_id}: {mask_frac:.1%} > max {max_frac:.0%}")
            continue

        region_masks.setdefault(region_id, np.zeros((h, w), dtype=bool))
        region_masks[region_id] |= combined
        pct = round(region_masks[region_id].sum() / total_px * 100, 1)
        logger.info(f"[{session_id}]   SAM2 → {region_id}: {pct}%")

    return region_masks


# ──────────────────────────────────────────────────────────────
#  Phase 3: Post-processing
# ──────────────────────────────────────────────────────────────

def _phase3_cleanup(
    region_masks: Dict[str, np.ndarray],
    h: int, w: int, total_px: int,
    session_id: str,
) -> Dict[str, np.ndarray]:
    """Morphological cleanup, small-component removal, priority conflict resolution."""
    logger.info(f"[{session_id}] Phase 3 — cleanup + conflict resolution")

    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    for rid in list(region_masks.keys()):
        mask = region_masks[rid].astype(np.uint8) * 255

        if rid in THIN_REGIONS:
            mask     = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_small, iterations=3)
            min_area = 200
        else:
            mask     = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large, iterations=2)
            mask     = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel_large, iterations=1)
            min_area = MIN_MASK_PIXELS

        # Remove tiny components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        clean_mask = np.zeros_like(mask)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                clean_mask[labels == i] = 255

        region_masks[rid] = clean_mask > 127

    # Priority-based exclusive assignment
    sorted_regions = sorted(region_masks.keys(), key=lambda r: MASK_PRIORITY.get(r, 0))
    assigned       = np.zeros((h, w), dtype=bool)
    final_masks:   Dict[str, np.ndarray] = {}

    for rid in reversed(sorted_regions):
        mask = region_masks[rid].copy()
        mask &= ~assigned
        if mask.any():
            final_masks[rid] = mask
            assigned         |= mask

    total_assigned = sum(m.sum() for m in final_masks.values())
    logger.info(
        f"[{session_id}]   Assigned {total_assigned:,}/{total_px:,} px "
        f"({total_assigned/total_px*100:.1f}%)"
    )

    # Log per-region final coverage
    for rid, mask in final_masks.items():
        pct = round(mask.sum() / total_px * 100, 1)
        logger.info(f"[{session_id}]   Final {rid}: {pct}%")

    return final_masks


# ──────────────────────────────────────────────────────────────
#  Overlay Builder
# ──────────────────────────────────────────────────────────────

def _build_overlay(
    image_bgr: np.ndarray,
    region_masks: Dict[str, np.ndarray],
    colors: Dict[str, tuple],
    alpha: float = 0.45,
) -> np.ndarray:
    """Blend colored region masks over the original image.

    Robust to masks that come from the segmentation pipeline (bool, shape H×W),
    masks reloaded from grayscale PNG (uint8, shape H×W), or any masks with a
    spurious trailing channel dimension (H×W×1) produced by some PNG decoders.
    """
    overlay = image_bgr.copy().astype(np.float64)

    # Draw in priority order (lowest first so higher-priority draws on top)
    sorted_regions = sorted(region_masks.keys(), key=lambda r: MASK_PRIORITY.get(r, 0))

    for rid in sorted_regions:
        raw_mask = region_masks[rid]

        # ── Normalise to 2-D boolean (H, W) ────────────────────────
        # squeeze removes any trailing dimension of size 1 that some
        # cv2.imread / imencode round-trips may add (e.g. H×W×1).
        mask_2d = np.squeeze(raw_mask).astype(bool)
        if mask_2d.ndim != 2:
            # If somehow still wrong shape, skip this region gracefully
            logger.warning(f"_build_overlay: skipping {rid} — unexpected mask shape {raw_mask.shape}")
            continue

        color_rgb = colors.get(rid, (200, 200, 200))
        color_bgr = color_rgb[::-1]           # RGB → BGR for OpenCV

        colored    = np.zeros_like(image_bgr, dtype=np.float64)
        colored[:] = color_bgr

        # Expand to (H, W, 1) then broadcast to (H, W, 3) — avoids np.stack issues
        mask_3d = mask_2d[:, :, np.newaxis]   # shape (H, W, 1) → broadcasts to (H, W, 3)
        overlay = np.where(mask_3d, overlay * (1 - alpha) + colored * alpha, overlay)

        # Label text at bounding box top-left
        ys, xs = np.where(mask_2d)
        if len(ys) > 0:
            x1, y1 = int(xs.min()), int(ys.min())
            label  = REGION_LABELS.get(rid, rid)
            overlay_u8 = overlay.astype(np.uint8)
            cv2.putText(overlay_u8, label, (x1 + 4, y1 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
            overlay = overlay_u8.astype(np.float64)

    return overlay.astype(np.uint8)
