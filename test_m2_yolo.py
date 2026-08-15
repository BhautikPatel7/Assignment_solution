"""
E2M - Module 2: High-Accuracy Hybrid Segmentation
===================================================
Combines SegFormer-b5 (sliding window) + YOLO-World + SAM2

Key improvements over v1:
 1) Sliding window inference at native resolution (no 5.5x downscale)
 2) SegFormer-b5 (larger, more accurate model)
 3) Area-constrained YOLO detections (no more "balcony = entire house")
 4) Exclusive mask assignment (each pixel -> exactly one region)
 5) Morphological cleanup (remove noise, fill holes)
"""

import os
import json
import base64
import cv2
import numpy as np
import torch
from PIL import Image

# -- CONFIG ----------------------------------------------------------------
TEST_IMAGE  = "data/old_weathered_house.png"
OUTPUT_DIR  = "test_masks"

# ADE20K class index -> our region mapping
ADE20K_TO_REGION = {
    0:   "main_wall",       # wall
    1:   "main_wall",       # building / facade
    8:   "window",          # windowpane (protected - separate from wall)
    14:  "door",            # door (protected - separate from wall)
    18:  "window",          # curtain (visible through windows)
    25:  "main_wall",       # house
    32:  "boundary_wall",   # fence
    38:  "railing",         # railing / balustrade
    42:  "pillar",          # column / pillar
}

# YOLO classes and mapping
YOLO_CLASSES = ["wall", "roof", "pillar", "balcony", "railing", "fence", "window", "door"]
YOLO_TO_REGION = {
    "wall":    None,           # SegFormer handles this
    "railing": None,           # SegFormer handles this
    "roof":    "roof",
    "pillar":  "pillar",
    "balcony": "balcony",
    "fence":   "boundary_wall",
    "window":  "window",
    "door":    "door",
}
YOLO_CONF = 0.03

# Max allowed area (fraction of image) per YOLO-detected region
# This prevents false positives like "balcony = entire house"
MAX_AREA_FRACTION = {
    "roof":          0.05,
    "pillar":        0.05,
    "balcony":       0.15,
    "boundary_wall": 0.20,
    "window":        0.10,
    "door":          0.10,
}

# Max allowed YOLO bounding box area (fraction of image)
MAX_BOX_FRACTION = 0.35

# Mask priority (higher number = higher priority, wins conflicts)
MASK_PRIORITY = {
    "main_wall":     1,
    "balcony":       2,
    "roof":          3,
    "boundary_wall": 4,
    "railing":       5,
    "pillar":        6,
    "window":        7,   # Protected: carves hole in wall
    "door":          8,   # Protected: carves hole in wall
}

# Sliding window config for SegFormer
TILE_SIZE = 512
TILE_STRIDE = 256   # 50% overlap

# Colors for overlay (RGB)
COLORS = {
    "main_wall":     (255,  80,  80),
    "pillar":        ( 80,  80, 255),
    "balcony":       (255, 200,  50),
    "railing":       (200,  50, 200),
    "roof":          ( 50, 200, 200),
    "boundary_wall": (200, 150,  50),
    "window":        (100, 200, 100),
    "door":          (150, 100,  50),
}

# Minimum mask area to keep (pixels) -- removes tiny noise patches
MIN_MASK_PIXELS = 500

# -- STARTUP ---------------------------------------------------------------
print("=" * 66)
print("  E2M - Module 2 (High-Accuracy Hybrid Segmentation)")
print("=" * 66)

device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    print(f"\n  Device: CUDA | GPU: {torch.cuda.get_device_name(0)}")
else:
    print(f"\n  Device: CPU (this will be slower but still works)")

# -- LOAD IMAGE ------------------------------------------------------------
print(f"\n  [1] Loading image: {TEST_IMAGE}")
image_bgr = cv2.imread(TEST_IMAGE)
if image_bgr is None:
    print(f"  ERROR: Cannot read {TEST_IMAGE}")
    exit(1)
image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
h, w = image_bgr.shape[:2]
total_pixels = h * w
print(f"      Size: {w} x {h} px ({total_pixels:,} pixels)")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==================================================================
#  PHASE 1: SegFormer-b5 with SLIDING WINDOW inference
# ==================================================================
print(f"\n  [2] SegFormer-b5: Loading model...")
print(f"      Model: nvidia/segformer-b4-finetuned-ade-512-512")

from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

seg_model_name = "nvidia/segformer-b4-finetuned-ade-512-512"
processor = SegformerImageProcessor.from_pretrained(seg_model_name)
model = SegformerForSemanticSegmentation.from_pretrained(seg_model_name).to(device)
model.eval()

num_classes = model.config.num_labels
print(f"      Model loaded OK ({num_classes} classes)")

print(f"\n      Running sliding window inference...")
print(f"      Tile: {TILE_SIZE}x{TILE_SIZE}, Stride: {TILE_STRIDE}, Overlap: 50%")

# Accumulate logits at full resolution
logit_sum = np.zeros((num_classes, h, w), dtype=np.float32)
count_map = np.zeros((h, w), dtype=np.float32)

# Calculate tile positions
y_positions = list(range(0, h - TILE_SIZE + 1, TILE_STRIDE))
if y_positions[-1] + TILE_SIZE < h:
    y_positions.append(h - TILE_SIZE)
x_positions = list(range(0, w - TILE_SIZE + 1, TILE_STRIDE))
if x_positions[-1] + TILE_SIZE < w:
    x_positions.append(w - TILE_SIZE)

total_tiles = len(y_positions) * len(x_positions)
tile_idx = 0

for y0 in y_positions:
    for x0 in x_positions:
        tile_idx += 1
        y1 = y0 + TILE_SIZE
        x1 = x0 + TILE_SIZE

        tile_rgb = image_rgb[y0:y1, x0:x1]
        tile_pil = Image.fromarray(tile_rgb)

        inputs = processor(images=tile_pil, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)

        # Upsample logits to tile size
        tile_logits = torch.nn.functional.interpolate(
            outputs.logits, size=(TILE_SIZE, TILE_SIZE),
            mode="bilinear", align_corners=False
        )[0].cpu().numpy()  # shape: (num_classes, TILE_SIZE, TILE_SIZE)

        logit_sum[:, y0:y1, x0:x1] += tile_logits
        count_map[y0:y1, x0:x1] += 1.0

        if tile_idx % 10 == 0 or tile_idx == total_tiles:
            print(f"      Tile {tile_idx}/{total_tiles} done")

# Average logits in overlap regions
count_map = np.maximum(count_map, 1.0)
for c in range(num_classes):
    logit_sum[c] /= count_map

seg_map = logit_sum.argmax(axis=0)  # shape: (H, W)

detected_classes = sorted(np.unique(seg_map).tolist())
id2label = model.config.id2label
class_names = [id2label.get(str(c), id2label.get(c, f'class_{c}')) for c in detected_classes]
print(f"      Classes found: {class_names}")

# Free GPU memory
del model, logit_sum, count_map
torch.cuda.empty_cache()

# Build region masks from SegFormer
region_masks = {}
for ade_class, region_id in ADE20K_TO_REGION.items():
    class_mask = (seg_map == ade_class)
    if class_mask.any():
        if region_id not in region_masks:
            region_masks[region_id] = np.zeros((h, w), dtype=bool)
        region_masks[region_id] |= class_mask

for rid, mask in region_masks.items():
    pct = round(mask.sum() / total_pixels * 100, 1)
    print(f"      SegFormer -> {rid:20s}  {pct}%")

# ==================================================================
#  PHASE 2: YOLO-World + SAM2 with AREA CONSTRAINTS
# ==================================================================
print(f"\n  [3] YOLO-World + SAM2 (area-constrained)...")

from ultralytics import YOLO, SAM

yolo = YOLO("yolov8s-worldv2.pt")
yolo.set_classes(YOLO_CLASSES)

yolo_results = yolo.predict(
    source=TEST_IMAGE, conf=YOLO_CONF, device=device, verbose=False
)[0]

boxes  = yolo_results.boxes
names  = yolo_results.names

# Group boxes by region, filtering oversized ones
yolo_regions = {}
for box in boxes:
    cls_name = names[int(box.cls[0])]
    conf     = float(box.conf[0])
    xyxy     = box.xyxy[0].cpu().numpy().astype(int).tolist()
    region_id = YOLO_TO_REGION.get(cls_name, cls_name)

    if region_id is None:
        continue  # Handled by SegFormer

    # Filter oversized bounding boxes
    box_area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])
    box_frac = box_area / total_pixels
    if box_frac > MAX_BOX_FRACTION:
        print(f"      SKIP {region_id:20s}  conf={conf:.2f}  box={xyxy}  (too large: {box_frac:.1%})")
        continue

    print(f"      YOLO -> {region_id:20s}  conf={conf:.2f}  box={xyxy}  ({box_frac:.1%})")
    if region_id not in yolo_regions:
        yolo_regions[region_id] = []
    yolo_regions[region_id].append(xyxy)

# Run SAM2 on filtered YOLO detections
if yolo_regions:
    sam = SAM("sam2_b.pt")
    for region_id, box_list in yolo_regions.items():
        # Skip if SegFormer already found this region with decent coverage
        if region_id in region_masks:
            existing_pct = region_masks[region_id].sum() / total_pixels * 100
            if existing_pct > 1.0:
                print(f"      Skip {region_id} (SegFormer already has {existing_pct:.1f}%)")
                continue

        sam_result = sam.predict(
            source=TEST_IMAGE, bboxes=box_list, device=device, verbose=False
        )[0]

        if sam_result.masks is not None and len(sam_result.masks) > 0:
            mask_data = sam_result.masks.data.cpu().numpy().astype(bool)
            if mask_data.ndim == 3:
                combined = np.any(mask_data, axis=0)
            else:
                combined = mask_data

            # Enforce maximum area constraint
            max_frac = MAX_AREA_FRACTION.get(region_id, 0.5)
            mask_frac = combined.sum() / total_pixels
            if mask_frac > max_frac:
                print(f"      TRIM {region_id}: {mask_frac:.1%} exceeds max {max_frac:.0%} -- keeping SegFormer only")
                continue

            if region_id not in region_masks:
                region_masks[region_id] = np.zeros((h, w), dtype=bool)
            region_masks[region_id] |= combined
            pct = round(region_masks[region_id].sum() / total_pixels * 100, 1)
            print(f"      SAM2 -> {region_id:20s}  {pct}%")
else:
    print(f"      YOLO found nothing extra.")

# ==================================================================
#  PHASE 3: MASK CLEANUP & CONFLICT RESOLUTION
# ==================================================================
print(f"\n  [4] Post-processing: cleanup + conflict resolution...")

# Step A: Morphological cleanup per mask
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
for rid in list(region_masks.keys()):
    mask = region_masks[rid].astype(np.uint8) * 255

    # Close small holes
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    # Open to remove small noise
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Remove small connected components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    clean_mask = np.zeros_like(mask)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= MIN_MASK_PIXELS:
            clean_mask[labels == i] = 255

    region_masks[rid] = clean_mask > 127

# Step B: Exclusive mask assignment (higher priority wins)
# Sort regions by priority
sorted_regions = sorted(region_masks.keys(), key=lambda r: MASK_PRIORITY.get(r, 0))

# Assign each pixel to its highest-priority region
assigned = np.zeros((h, w), dtype=bool)
final_masks = {}

# Process from highest priority to lowest
for rid in reversed(sorted_regions):
    mask = region_masks[rid].copy()
    # Remove pixels already assigned to higher-priority regions
    mask &= ~assigned
    if mask.any():
        final_masks[rid] = mask
        assigned |= mask

region_masks = final_masks

print(f"      Cleanup complete. Checking overlaps...")
total_assigned = sum(m.sum() for m in region_masks.values())
print(f"      Total assigned pixels: {total_assigned:,} / {total_pixels:,} ({total_assigned/total_pixels*100:.1f}%)")

# ==================================================================
#  SAVE MASKS + OVERLAY
# ==================================================================
print(f"\n  [5] Saving masks and creating overlay...")

results = []
for region_id, mask in region_masks.items():
    mask_uint8 = (mask * 255).astype(np.uint8)
    mask_path = os.path.join(OUTPUT_DIR, f"{region_id}.png")
    cv2.imwrite(mask_path, mask_uint8)

    pixel_count  = int(mask.sum())
    coverage_pct = round(pixel_count / total_pixels * 100, 1)
    print(f"      {region_id:20s}  pixels={pixel_count:>10,}  ({coverage_pct}%)")

    with open(mask_path, "rb") as f:
        mask_b64 = base64.b64encode(f.read()).decode("utf-8")

    ys, xs = np.where(mask)
    if len(ys) == 0:
        continue
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

    results.append({
        "region_id":    region_id,
        "pixel_count":  pixel_count,
        "coverage_pct": coverage_pct,
        "mask_path":    mask_path,
        "mask_b64":     mask_b64[:80] + "...",
        "box_pixels":   [x1, y1, x2, y2],
    })

# Overlay
overlay = image_bgr.copy().astype(np.float64)
for r in results:
    rid   = r["region_id"]
    color = COLORS.get(rid, (200, 200, 200))
    mask  = cv2.imread(r["mask_path"], cv2.IMREAD_GRAYSCALE)
    if mask is None:
        continue
    colored = np.zeros_like(image_bgr, dtype=np.float64)
    colored[:] = color[::-1]
    alpha = 0.45
    mask_bool = np.squeeze(mask > 127)
    mask_3d = np.stack([mask_bool]*3, axis=2)
    overlay = np.where(mask_3d, overlay * (1 - alpha) + colored * alpha, overlay)
    box = r["box_pixels"]
    cv2.putText(overlay.astype(np.uint8), rid, (box[0]+4, box[1]+18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

overlay = overlay.astype(np.uint8)
overlay_path = os.path.join(OUTPUT_DIR, "overlay.png")
cv2.imwrite(overlay_path, overlay)
print(f"      Overlay saved: {overlay_path}")

# JSON
summary = {"image": TEST_IMAGE, "regions": results}
for r in summary["regions"]:
    del r["mask_b64"]
with open("test_m2_result.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n{'='*66}")
print(f"  Regions segmented : {[r['region_id'] for r in results]}")
print(f"  Masks saved to    : {OUTPUT_DIR}/")
print(f"  Overlay image     : {overlay_path}")
print(f"  Summary JSON      : test_m2_result.json")
print("=" * 66)
print(f"\n  Open {OUTPUT_DIR}/overlay.png to visually verify masks!")
