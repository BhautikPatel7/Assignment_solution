"""
compositor.py — Module 4: Composite Service

Applies user-selected materials (paint colors or texture images)
onto the original house image using per-region masks.

Methods:
  build_composite(image_path, masks_dir, selections, textures_dir) -> np.ndarray

selections format:
  {
    "main_wall":     {"type": "paint",   "value": "#F5F5F0"},
    "balcony":       {"type": "texture", "value": "tile_marble.jpg"},
    "roof":          {"type": "texture", "value": "roof_clay_tile.jpg"},
  }
"""

import os
import cv2
import numpy as np
from typing import Dict, Optional
from config import logger


# ── Constants ──────────────────────────────────────────────────
VALID_REGIONS = [
    'main_wall', 'pillar', 'balcony', 'roof', 'boundary_wall',
    'window', 'door',
]

# Blend alpha for paint and texture overlays
PAINT_ALPHA   = 0.82   # how strongly paint covers original (higher = more opaque)
TEXTURE_ALPHA = 0.88   # how strongly texture covers original


# ── Helpers ────────────────────────────────────────────────────

def _hex_to_bgr(hex_color: str):
    """Convert #RRGGBB to (B, G, R) tuple for OpenCV."""
    h = hex_color.lstrip('#')
    if len(h) != 6:
        return (200, 200, 200)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


def _load_mask(masks_dir: str, region_id: str, img_h: int, img_w: int) -> Optional[np.ndarray]:
    """Load a region mask from disk. Returns bool (H, W) or None."""
    path = os.path.join(masks_dir, f"{region_id}.png")
    if not os.path.exists(path):
        return None
    m = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if m is None:
        return None
    m = np.squeeze(m)
    if m.shape != (img_h, img_w):
        m = cv2.resize(m, (img_w, img_h), interpolation=cv2.INTER_NEAREST)
    return m > 127


def _apply_paint(
    image: np.ndarray,
    mask: np.ndarray,
    hex_color: str,
    alpha: float = PAINT_ALPHA,
) -> np.ndarray:
    """Blend a solid paint color onto the masked region."""
    bgr = _hex_to_bgr(hex_color)
    color_layer    = np.full_like(image, bgr, dtype=np.uint8)
    mask_3d        = mask[:, :, np.newaxis]
    blended        = (image * (1 - alpha) + color_layer * alpha).astype(np.uint8)
    return np.where(mask_3d, blended, image)


def _load_texture_tiled(texture_path: str, target_h: int, target_w: int) -> Optional[np.ndarray]:
    """Load a texture image and tile it to cover (target_h, target_w).
    Best for: stone, sand, concrete, marble, rubble textures."""
    if not os.path.exists(texture_path):
        logger.warning(f"Texture not found: {texture_path}")
        return None
    tex = cv2.imread(texture_path)
    if tex is None:
        return None

    th, tw = tex.shape[:2]
    # Tile to cover the full image
    reps_y = (target_h // th) + 2
    reps_x = (target_w // tw) + 2
    tiled  = np.tile(tex, (reps_y, reps_x, 1))
    tiled  = tiled[:target_h, :target_w]
    return tiled


def _load_texture_stretched(
    texture_path: str,
    mask: np.ndarray,
    img_h: int,
    img_w: int,
) -> Optional[np.ndarray]:
    """Load a texture and stretch it to fill the mask's bounding box.
    Best for: railings, structural elements that shouldn't repeat."""
    if not os.path.exists(texture_path):
        logger.warning(f"Texture not found: {texture_path}")
        return None
    tex = cv2.imread(texture_path)
    if tex is None:
        return None

    # Get bounding box of the mask
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return None

    y_min, y_max = int(ys.min()), int(ys.max())
    x_min, x_max = int(xs.min()), int(xs.max())
    bbox_h = y_max - y_min + 1
    bbox_w = x_max - x_min + 1

    # Resize texture to fit the bounding box
    tex_resized = cv2.resize(tex, (bbox_w, bbox_h), interpolation=cv2.INTER_AREA)

    # Place into full-size canvas
    canvas = np.zeros((img_h, img_w, 3), dtype=np.uint8)
    canvas[y_min:y_max + 1, x_min:x_max + 1] = tex_resized
    return canvas


# All regions use tiled mode now.
# Balcony railing images should be proper front-facing repeatable patterns.


def _apply_texture(
    image: np.ndarray,
    mask: np.ndarray,
    texture_path: str,
    region_id: str = '',
    alpha: float = TEXTURE_ALPHA,
) -> np.ndarray:
    """Apply a texture image over the masked region.

    - Wall/stone/roof textures → tiled (seamless repeat)
    - Railing textures → stretched to fit bounding box
    """
    h, w = image.shape[:2]

    textured = _load_texture_tiled(texture_path, h, w)

    if textured is None:
        logger.warning(f"Could not load texture {texture_path}, skipping.")
        return image

    mask_3d = mask[:, :, np.newaxis]
    blended = (image * (1 - alpha) + textured * alpha).astype(np.uint8)
    return np.where(mask_3d, blended, image)


def _apply_railing_texture(
    image: np.ndarray,
    mask: np.ndarray,
    texture_path: str,
    alpha: float = TEXTURE_ALPHA,
) -> np.ndarray:
    """Apply a railing texture by scaling to mask height and repeating horizontally.

    Steps:
      1. Find the bounding box of the mask (the railing area)
      2. Scale the railing image to match the bounding box HEIGHT
         (keeps the railing bars proportional — not squished or stretched)
      3. Repeat (tile) horizontally to cover the full image width
      4. Blend only within the mask
    """
    if not os.path.exists(texture_path):
        logger.warning(f"Railing texture not found: {texture_path}")
        return image

    tex = cv2.imread(texture_path)
    if tex is None:
        logger.warning(f"Could not read railing texture: {texture_path}")
        return image

    img_h, img_w = image.shape[:2]

    # Get bounding box of the mask
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return image

    bbox_h = int(ys.max()) - int(ys.min()) + 1

    # Scale texture to match the railing's height, keeping aspect ratio
    tex_h, tex_w = tex.shape[:2]
    scale = bbox_h / tex_h
    new_h = bbox_h
    new_w = max(1, int(tex_w * scale))
    tex_scaled = cv2.resize(tex, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Tile horizontally to cover full image width
    reps_x = (img_w // new_w) + 2
    tiled_row = np.tile(tex_scaled, (1, reps_x, 1))[:, :img_w, :]

    # Tile vertically to cover full image height
    reps_y = (img_h // new_h) + 2
    tiled_full = np.tile(tiled_row, (reps_y, 1, 1))[:img_h, :, :]

    # Blend within mask
    mask_3d = mask[:, :, np.newaxis]
    blended = (image * (1 - alpha) + tiled_full * alpha).astype(np.uint8)
    return np.where(mask_3d, blended, image)


# ── Main Composite Function ────────────────────────────────────

def build_composite(
    image_path: str,
    masks_dir: str,
    selections: Dict[str, dict],
    textures_dir: str,
) -> np.ndarray:
    """
    Apply selected materials to the original image using masks.

    Args:
        image_path:   Path to original house photo (PNG/JPEG)
        masks_dir:    Directory containing {region}.png mask files
        selections:   { region_id: {"type": "paint"|"texture", "value": hex|filename} }
        textures_dir: Directory containing texture image files

    Returns:
        Composite image as BGR numpy array (H, W, 3) uint8
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")

    h, w   = img.shape[:2]
    result = img.copy()

    # Apply in a specific order so higher-priority regions draw on top
    # Roof excluded — not editable in renovation
    region_order = ['main_wall', 'boundary_wall', 'balcony', 'pillar']

    for region_id in region_order:
        sel = selections.get(region_id)
        if not sel:
            continue  # no material chosen for this region — keep original

        mask = _load_mask(masks_dir, region_id, h, w)
        if mask is None or not mask.any():
            logger.info(f"[composite] No mask for {region_id}, skipping.")
            continue

        sel_type  = sel.get('type', 'paint')
        sel_value = sel.get('value', '')

        if sel_type == 'paint':
            logger.info(f"[composite] {region_id}: paint {sel_value}")
            result = _apply_paint(result, mask, sel_value)

        elif sel_type == 'texture':
            tex_path = os.path.join(textures_dir, sel_value)

            if region_id == 'balcony':
                # Railing: scale image to match mask height, then repeat horizontally
                logger.info(f"[composite] {region_id}: railing texture {tex_path}")
                result = _apply_railing_texture(result, mask, tex_path)
            else:
                # Wall/stone textures → normal tile
                logger.info(f"[composite] {region_id}: texture {tex_path}")
                result = _apply_texture(result, mask, tex_path, region_id=region_id)

        else:
            logger.warning(f"[composite] Unknown type '{sel_type}' for {region_id}")

    return result

