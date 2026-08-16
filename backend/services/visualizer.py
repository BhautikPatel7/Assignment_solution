"""
visualizer.py — Module 4: Visualization Service

Two-stage pipeline:
  Stage 1: Gemini Vision analyzes the original house image + composite
           and builds a detailed scene description.
  Stage 2: HuggingFace FLUX img2img (or text-to-image fallback)
           generates a photorealistic renovation visualization.

Public API:
  build_prompt(material_selections, house_description) -> str
  generate_visualization(composite_path, prompt, hf_token) -> bytes (PNG)
"""

import io
import os
from PIL import Image
from huggingface_hub import InferenceClient
from config import logger


# ── Material → human-readable description map ─────────────────
MATERIAL_DESCRIPTIONS = {
    # Wall textures
    'stone_natural.png':          'natural rough stone cladding',
    'stone_slate.png':            'dark charcoal slate stone cladding',
    'stone_sandstone.png':        'warm golden sandstone textured finish',
    'texture_sand.png':           'smooth sand-textured plastered finish',
    'texture_concrete.png':       'modern exposed concrete textured finish',
    'texture_marble.png':         'polished white marble finish',
    # Railing textures
    'railing_ms_steel.png':       'matte black painted MS steel railings',
    'railing_stainless.png':      'polished stainless steel railings',
    'railing_aluminium.png':      'powder-coated grey aluminium railings',
    'railing_glass.png':          'frameless clear glass panel railings',
    'railing_decorative_iron.png':'ornamental black wrought iron railings',
    # Boundary wall
    'stone_rubble.png':           'rough rubble stone boundary wall',
    # Roof
    'roof_clay_tile.png':         'terracotta clay roof tiles',
    'roof_concrete.png':          'flat painted concrete roof',
    'roof_metal.png':             'corrugated metal sheet roof',
}

PAINT_NAMES = {
    '#F5F5F0': 'classic white',
    '#F2E7D0': 'warm cream',
    '#D8C7A3': 'sandy beige',
    '#9E9E9E': 'modern grey',
    '#C1714A': 'terracotta orange',
    '#1C1C1E': 'matte black',
    '#F0F0EE': 'pearl white',
    '#6B4423': 'antique bronze',
    '#36454F': 'charcoal grey',
    '#B0B7BC': 'brushed silver',
}

REGION_LABELS = {
    'main_wall':     'main exterior walls',
    'pillar':        'pillars and columns',
    'balcony':       'balcony railings',
    'boundary_wall': 'boundary compound wall',
    'roof':          'roof',
}


# ── Prompt Builder ─────────────────────────────────────────────

def build_prompt(material_selections: dict, house_description: str = '') -> str:
    """Build a detailed FLUX prompt from material selections + house description.

    Args:
        material_selections: { region_id: { type, value } }
        house_description:   Optional Gemini-generated description of the house

    Returns:
        A detailed text prompt suitable for FLUX image generation
    """
    lines = [
        "Photorealistic architectural visualization of an Indian residential house exterior.",
        "Front elevation view, professional architectural photography.",
        "Golden hour natural daylight, crisp sharp focus, ultra-detailed, 8K quality.",
    ]

    if house_description:
        lines.append(house_description.strip())

    # Build material description per region
    material_parts = []
    for region_id, sel in material_selections.items():
        region_name = REGION_LABELS.get(region_id, region_id.replace('_', ' '))
        sel_type  = sel.get('type', '')
        sel_value = sel.get('value', '')

        if sel_type == 'paint':
            color_name = PAINT_NAMES.get(sel_value, f'color {sel_value}')
            material_parts.append(f"{region_name} painted in {color_name}")
        elif sel_type == 'texture':
            mat_desc = MATERIAL_DESCRIPTIONS.get(
                sel_value,
                sel_value.replace('_', ' ').replace('.png', '')
            )
            material_parts.append(f"{region_name} finished with {mat_desc}")

    if material_parts:
        lines.append("The renovation features: " + "; ".join(material_parts) + ".")

    lines.extend([
        "Lush green landscaping in foreground, clear blue sky.",
        "No people, no vehicles, no text, no watermarks.",
        "Photorealistic render, high-end architectural magazine quality.",
    ])

    return "\n".join(lines)


# ── Visualization Generator ────────────────────────────────────

IMG2IMG_MODEL  = "timbrooks/instruct-pix2pix"   # instruction-based img editing
TEXT2IMG_MODEL = "black-forest-labs/FLUX.1-schnell"


def generate_visualization(
    composite_path: str,
    prompt: str,
    hf_token: str,
    strength: float = 0.65,
) -> bytes:
    """
    Generate a photorealistic renovation visualization.

    Strategy:
      1. Primary:  img2img using instruct-pix2pix
                   (keeps house structure, applies renovation style)
      2. Fallback: FLUX text-to-image if img2img fails

    Args:
        composite_path: Path to OpenCV composite PNG (house + materials)
        prompt:         Renovation visualization prompt
        hf_token:       HuggingFace API token
        strength:       img2img denoising strength (0 = no change, 1 = full regen)

    Returns:
        PNG image bytes
    """
    client = InferenceClient(api_key=hf_token)

    # Load composite image
    if not os.path.exists(composite_path):
        raise FileNotFoundError(f"Composite image not found: {composite_path}")

    composite_img = Image.open(composite_path).convert("RGB")
    logger.info(f"[visualize] Composite loaded: {composite_img.size}")

    # ── Stage 1: Try instruct-pix2pix img2img ─────────────────
    try:
        logger.info(f"[visualize] Trying img2img: {IMG2IMG_MODEL}")
        result_img = client.image_to_image(
            image=composite_img,
            prompt=prompt,
            negative_prompt=(
                "blurry, low quality, distorted, ugly, bad architecture, "
                "unrealistic, painting, cartoon, sketch, text, watermark"
            ),
            model=IMG2IMG_MODEL,
        )
        logger.info("[visualize] img2img succeeded")

    except Exception as e:
        logger.warning(f"[visualize] img2img failed ({e}), falling back to text2img")

        # ── Stage 2: FLUX text-to-image fallback ──────────────
        try:
            logger.info(f"[visualize] Using text2img: {TEXT2IMG_MODEL}")
            result_img = client.text_to_image(
                prompt=prompt,
                negative_prompt=(
                    "blurry, low quality, distorted, ugly, cartoon, sketch, text"
                ),
                model=TEXT2IMG_MODEL,
            )
            logger.info("[visualize] text2img succeeded")

        except Exception as e2:
            logger.error(f"[visualize] Both methods failed: {e2}")
            raise RuntimeError(f"Visualization generation failed: {e2}")

    # Convert PIL → PNG bytes
    buf = io.BytesIO()
    result_img.save(buf, format="PNG")
    buf.seek(0)
    logger.info("[visualize] Image encoded to PNG bytes")
    return buf.getvalue()
