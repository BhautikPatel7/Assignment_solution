# E2M — Full Detailed Implementation Plan
## AI-Based Exterior House Renovation & Cost Estimation System

---

## System Summary

| Item | Detail |
|------|--------|
| **Backend** | FastAPI (Python 3.13) |
| **Frontend** | React + Vite |
| **Segmentation** | SegFormer-b4 + YOLOv8s-worldv2 + SAM2-b |
| **AI Analysis** | Gemini 3.1 Pro (Vertex AI) |
| **AI Visualization** | Gemini 2.0 Flash / Imagen 3 (Vertex AI) |
| **Compositing** | OpenCV + NumPy |
| **PDF** | ReportLab |
| **Hosting** | Render (backend) + Vercel (frontend) |
| **Storage** | Stateless — temp files only |

---

## Models Used

| Model | Purpose | Size | Source |
|-------|---------|------|--------|
| `nvidia/segformer-b4-finetuned-ade-512-512` | Pixel-level semantic segmentation (wall, window, door, pillar) | ~60MB | HuggingFace (transformers) |
| `yolov8s-worldv2.pt` | Open-vocabulary object detection (roof, balcony, fence) | ~26MB | Ultralytics |
| `sam2_b.pt` | High-quality mask refinement from bounding boxes | ~162MB | Ultralytics (Meta SAM2) |
| `gemini-3.1-pro-preview` | Image validation + architectural analysis (M1) | Cloud API | Google Vertex AI |
| `gemini-2.0-flash-exp` | Photorealistic renovation visualization (M5) | Cloud API | Google Vertex AI |

---

## Segmented Regions (7 total)

| Region ID | Detected By | Editable | Color (RGB) |
|-----------|-------------|----------|-------------|
| `main_wall` | SegFormer (ADE20K classes: wall, building, house) | ✅ Yes | (255, 80, 80) Red |
| `pillar` | SegFormer (column) + YOLO+SAM2 backup | ✅ Yes | (80, 80, 255) Blue |
| `balcony` | YOLO-World + SAM2 | ✅ Yes | (255, 200, 50) Yellow |
| `roof` | YOLO-World + SAM2 (smart-clipped boxes) | ✅ Yes | (50, 200, 200) Teal |
| `boundary_wall` | SegFormer (fence) + YOLO+SAM2 backup | ✅ Yes | (200, 150, 50) Gold |
| `window` | SegFormer (windowpane, curtain) + YOLO+SAM2 | 🔒 Protected | (100, 200, 100) Green |
| `door` | SegFormer (door) + YOLO+SAM2 | 🔒 Protected | (255, 140, 0) Orange |

---

## File Structure

```
backend/
├── main.py                     # FastAPI app + CORS + routes
├── requirements.txt
├── .env                        # GCP credentials, project ID
│
├── routers/
│   ├── analyze.py              # M1 — Image validation + analysis
│   ├── segment.py              # M2 — SegFormer + YOLO + SAM2
│   ├── composite.py            # M4 — OpenCV paint/texture overlay
│   ├── visualize.py            # M5 — Gemini image generation
│   ├── estimate.py             # M6 — Area + cost calculation
│   └── report.py               # M7 — PDF generation
│
├── services/
│   ├── gemini_client.py        # Vertex AI Gemini client (shared)
│   ├── segmentation.py         # SegFormer + YOLO + SAM2 pipeline
│   ├── compositing.py          # OpenCV paint/texture logic
│   ├── cost_engine.py          # Rate DB + calculation
│   └── pdf_builder.py          # ReportLab PDF assembly
│
├── models/                     # AI model weights (gitignored)
│   ├── yolov8s-worldv2.pt
│   └── sam2_b.pt
│   # SegFormer auto-downloads from HuggingFace cache
│
├── data/
│   ├── materials.json          # Material catalog
│   ├── rates.json              # Material + labor rates (INR)
│   └── textures/               # Texture image files (PNG)
│       ├── stone_natural.png
│       ├── stone_slate.png
│       ├── tile_marble.png
│       └── texture_sand.png
│
└── temp/                       # Runtime temp (gitignored)

frontend/
├── index.html
├── vite.config.js
├── package.json
│
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── index.css               # Design system
│   │
│   ├── pages/
│   │   ├── UploadPage.jsx      # Step 1 — Upload + M1 validation
│   │   ├── SegmentPage.jsx     # Step 2 — View segmented regions
│   │   ├── MaterialPage.jsx    # Step 3 — Select materials
│   │   ├── VisualizePage.jsx   # Step 4 — AI render + before/after
│   │   ├── CostPage.jsx        # Step 5 — Cost breakdown
│   │   └── ReportPage.jsx      # Step 6 — Download PDF
│   │
│   ├── components/
│   │   ├── Stepper.jsx
│   │   ├── ImageUploader.jsx
│   │   ├── SegmentOverlay.jsx
│   │   ├── MaterialCard.jsx
│   │   ├── BeforeAfterSlider.jsx
│   │   ├── CostTable.jsx
│   │   └── LoadingOverlay.jsx
│   │
│   ├── store/
│   │   └── projectStore.js     # Zustand global state
│   │
│   └── api/
│       └── client.js           # Axios API calls
```

---

## Module 1 — Image Validation & Analysis (Gemini Vision)

**Purpose**: Validate uploaded image is a usable house exterior photo. Reject blurry, non-house, or low-quality images.

**File**: `backend/routers/analyze.py`
**API**: `POST /api/analyze`
**Model**: `gemini-3.1-pro-preview` via Vertex AI

### What It Validates

| Check | How | Reject If |
|-------|-----|-----------|
| **Is it a house?** | Gemini Vision analysis | No building detected |
| **Image quality** | Gemini checks blur/noise/resolution | Extremely blurry or dark |
| **Exterior view?** | Gemini checks if it's interior | Interior photo detected |
| **Obstruction** | Gemini checks if house is visible | House mostly hidden by trees/vehicles |
| **Orientation** | Gemini checks angle | Extreme angle (top-down, too close) |

### Gemini Prompt
```
You are an architectural image validation and analysis AI.

FIRST, validate this image:
1. Is there a residential building/house clearly visible?
2. Is this an EXTERIOR view (not interior)?
3. Is the image quality acceptable (not extremely blurry, dark, or low resolution)?
4. Is the building facade reasonably visible (not completely blocked by trees/vehicles)?

IF the image fails any check, set "is_valid" to false and explain in "rejection_reason".

IF valid, analyze the architecture and return:
- Number of floors
- Which regions are visible
- Any notable observations

Return ONLY a valid JSON object:
{
  "is_valid": true,
  "rejection_reason": null,
  "image_quality": "good|acceptable|poor",
  "is_exterior": true,
  "house_detected": true,
  "floors": 2,
  "regions_present": ["main_wall", "pillar", "balcony", "roof", "boundary_wall"],
  "protected_regions": ["window", "door"],
  "confidence": 0.95,
  "notes": "Two-story residential building with front balcony and boundary wall"
}
```

### API Request/Response
```
POST /api/analyze
Content-Type: multipart/form-data

Body: image file (PNG/JPG)
```

```json
// Success Response
{
  "session_id": "uuid-string",
  "is_valid": true,
  "analysis": {
    "image_quality": "good",
    "floors": 2,
    "regions_present": ["main_wall", "pillar", "balcony", "roof", "boundary_wall"],
    "protected_regions": ["window", "door"],
    "confidence": 0.95,
    "notes": "Two-story house with front balcony"
  }
}

// Rejection Response
{
  "session_id": null,
  "is_valid": false,
  "rejection_reason": "No building detected. The image appears to be a landscape photo.",
  "suggestion": "Please upload a clear front-facing photo of a house exterior."
}
```

### Implementation
```python
# backend/routers/analyze.py

from fastapi import APIRouter, UploadFile, File
import uuid, base64, json
from services.gemini_client import call_gemini_vision

router = APIRouter()

@router.post("/api/analyze")
async def analyze_image(image: UploadFile = File(...)):
    # 1. Read and encode image
    image_bytes = await image.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = image.content_type or "image/png"

    # 2. Call Gemini Vision for validation + analysis
    result = call_gemini_vision(image_b64, mime, VALIDATION_PROMPT)

    # 3. Check validation
    if not result.get("is_valid", False):
        return {
            "session_id": None,
            "is_valid": False,
            "rejection_reason": result.get("rejection_reason", "Image not usable"),
            "suggestion": "Please upload a clear front-facing photo of a house exterior."
        }

    # 4. Return analysis
    session_id = str(uuid.uuid4())
    return {
        "session_id": session_id,
        "is_valid": True,
        "image_b64": image_b64,
        "analysis": result
    }
```

---

## Module 2 — Segmentation (SegFormer + YOLO-World + SAM2)

**Purpose**: Generate pixel-accurate binary masks for each architectural region.

**File**: `backend/routers/segment.py` + `backend/services/segmentation.py`
**API**: `POST /api/segment`

### Pipeline (3 Phases)

```
Phase 1: SegFormer-b4 (Sliding Window)
    Input:  House image (2816x1536)
    Method: 50 overlapping 512x512 tiles, logit averaging
    Output: Pixel-level masks for: main_wall, window, door, pillar, boundary_wall
    
Phase 2: YOLO-World + SAM2 (Area-Constrained)
    Input:  House image
    Method: YOLO detects boxes → SAM2 refines to masks
    Output: Masks for: roof, balcony, pillar, boundary_wall (backup)
    Filters:
      - Per-region max box size (roof ≤ 10%, balcony ≤ 20%)
      - Per-region max mask area (roof ≤ 10%, pillar ≤ 5%)
      - Smart roof clipping: oversized roof boxes → clip to top 25%

Phase 3: Post-Processing
    - Morphological cleanup (close holes, remove noise < 500px)
    - Gentle cleanup for thin structures (pillar: 3x3 kernel, no opening)
    - Exclusive mask assignment (priority-based, no pixel overlap)
    - Priority: door(8) > window(7) > pillar(5) > boundary_wall(4)
              > balcony(3) > roof(2) > main_wall(1)
```

### ADE20K Class Mapping (SegFormer)
```python
ADE20K_TO_REGION = {
    0:   "main_wall",       # wall
    1:   "main_wall",       # building / facade
    8:   "window",          # windowpane
    14:  "door",            # door
    18:  "window",          # curtain (visible through windows)
    25:  "main_wall",       # house
    32:  "boundary_wall",   # fence
    42:  "pillar",          # column / pillar
}
```

### YOLO-World Classes
```python
YOLO_CLASSES = ["wall", "roof", "pillar", "balcony", "fence", "window", "door"]
```

### API Request/Response
```
POST /api/segment
Content-Type: application/json

Body: { "session_id": "uuid", "image_b64": "base64..." }
```

```json
{
  "session_id": "uuid",
  "masks": {
    "main_wall":     "base64_png_mask",
    "pillar":        "base64_png_mask",
    "balcony":       "base64_png_mask",
    "roof":          "base64_png_mask",
    "boundary_wall": "base64_png_mask",
    "window":        "base64_png_mask",
    "door":          "base64_png_mask"
  },
  "overlay_image": "base64_png",
  "detected_regions": ["main_wall", "pillar", "balcony", "roof", "boundary_wall"],
  "protected_regions": ["window", "door"],
  "region_coverage": {
    "main_wall": 51.9,
    "pillar": 2.4,
    "balcony": 3.5,
    "roof": 2.0,
    "boundary_wall": 3.8,
    "window": 5.2,
    "door": 1.3
  }
}
```

### Processing Time
- SegFormer sliding window (50 tiles on GTX 1650): ~3-4 minutes
- YOLO-World detection: ~2 seconds
- SAM2 mask refinement: ~5 seconds per region
- Post-processing: ~1 second
- **Total: ~4-5 minutes per image**

---

## Module 3 — Material Catalog (Frontend Only)

**No backend call needed** — pure frontend state.

### Material Options Per Region

| Region | Paint (5 colors) | Texture Options |
|--------|-----------------|-----------------|
| `main_wall` | White, Cream, Beige, Grey, Terracotta | Stone Cladding (3), Texture Finish (2) |
| `pillar` | White, Cream, Beige, Grey, Terracotta | Texture Finish (2), Stone Cladding (2) |
| `balcony` | White, Cream, Beige, Grey, Terracotta | Tile (2 types) |
| `roof` | — | Tile Roofing (2), Flat Concrete |
| `boundary_wall` | White, Cream, Beige, Grey, Terracotta | Stone Cladding (2) |

### Frontend Data Structure
```javascript
// frontend/src/constants/materials.js
export const MATERIAL_CATALOG = {
  main_wall: {
    label: "Main Wall",
    options: [
      {
        id: "paint", label: "Paint", type: "color",
        colors: [
          { id: "white",      hex: "#F5F5F0", label: "Classic White" },
          { id: "cream",      hex: "#F2E7D0", label: "Warm Cream" },
          { id: "beige",      hex: "#D8C7A3", label: "Sandy Beige" },
          { id: "grey",       hex: "#9E9E9E", label: "Modern Grey" },
          { id: "terracotta", hex: "#C1714A", label: "Terracotta" },
        ]
      },
      {
        id: "stone_cladding", label: "Stone Cladding", type: "texture",
        options: [
          { id: "natural_stone", label: "Natural Stone", texture: "stone_natural.png", rate: 180 },
          { id: "slate_stone",   label: "Slate Stone",   texture: "stone_slate.png",   rate: 160 },
          { id: "sandstone",     label: "Sandstone",      texture: "stone_sand.png",    rate: 140 },
        ]
      },
      {
        id: "texture_finish", label: "Texture Finish", type: "texture",
        options: [
          { id: "sand_texture",     label: "Sand Texture",     texture: "texture_sand.png",     rate: 90 },
          { id: "concrete_texture", label: "Concrete Texture", texture: "texture_concrete.png", rate: 80 },
        ]
      }
    ]
  },
  // ... other regions follow same structure
}
```

---

## Module 4 — OpenCV Compositing (Preview)

**Purpose**: Apply selected materials to the house image using masks. Fast preview (~1-2 seconds).

**File**: `backend/routers/composite.py` + `backend/services/compositing.py`
**API**: `POST /api/composite`

### Paint Application (HSL Blend)
```python
def apply_paint(image, mask, hex_color):
    """Apply paint color while preserving original shadows and depth."""
    rgb = hex_to_rgb(hex_color)  # e.g. "#F5F5F0" → (245, 245, 240)
    colored = np.zeros_like(image)
    colored[:] = rgb[::-1]  # RGB → BGR

    # Extract luminance from original image to preserve shadows
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    luminance = gray / 255.0

    result = image.copy()
    mask_bool = mask > 127
    for c in range(3):
        result[:, :, c] = np.where(
            mask_bool,
            np.clip(colored[:, :, c] * luminance * 1.2, 0, 255),
            image[:, :, c]
        )
    return result.astype(np.uint8)
```

### Texture Application (Tiled Overlay)
```python
def apply_texture(image, mask, texture_path):
    """Tile texture over masked region with edge blending."""
    texture = cv2.imread(texture_path)
    h, w = image.shape[:2]

    # Tile texture to fill image dimensions
    th, tw = texture.shape[:2]
    repeat_y = (h // th) + 1
    repeat_x = (w // tw) + 1
    tiled = np.tile(texture, (repeat_y, repeat_x, 1))[:h, :w]

    # Blend: 70% texture + 30% original luminance for realism
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) / 255.0
    gray_3ch = np.stack([gray]*3, axis=2)

    blended = (tiled * 0.7 + tiled * gray_3ch * 0.3).astype(np.uint8)

    # Apply only within mask
    mask_3ch = np.stack([mask > 127]*3, axis=2)
    result = np.where(mask_3ch, blended, image)
    return result.astype(np.uint8)
```

### API Request/Response
```
POST /api/composite
Body: {
  "session_id": "uuid",
  "image_b64": "base64...",
  "masks": { "main_wall": "base64...", ... },
  "selections": {
    "main_wall": { "type": "paint", "color": "#F5F5F0" },
    "pillar":    { "type": "texture", "texture": "stone_natural.png" },
    "balcony":   { "type": "paint", "color": "#D8C7A3" }
  }
}
```
```json
{
  "composite_image": "base64_png"
}
```

---

## Module 5 — AI Visualization (Gemini Image Generation)

**Purpose**: Generate photorealistic renovation image using Gemini.

**File**: `backend/routers/visualize.py`
**API**: `POST /api/visualize`
**Model**: `gemini-2.0-flash-exp` or `imagen-3.0-capability-001`

### Dynamic Prompt Builder
```python
def build_prompt(selections: dict) -> str:
    lines = [
        "You are a photorealistic architectural visualization AI.",
        "",
        "Renovate this house exterior with these specifications:",
        "- Preserve the EXACT original structure, geometry, and camera angle",
        "- Keep all windows, doors, and surroundings UNCHANGED",
        "- Apply materials realistically with correct lighting and shadows",
        "",
        "Material specifications:",
    ]

    REGION_LABELS = {
        "main_wall": "Main exterior walls",
        "pillar": "Pillars and columns",
        "balcony": "Balcony area",
        "roof": "Roof surface",
        "boundary_wall": "Boundary/compound wall",
    }

    for region_id, sel in selections.items():
        label = REGION_LABELS.get(region_id, region_id)
        if sel["type"] == "paint":
            lines.append(f"- {label}: Apply {sel['color_name']} exterior paint")
        elif sel["type"] == "texture":
            lines.append(f"- {label}: Apply {sel['texture_name']} finish")

    lines += [
        "",
        "Generate a single photorealistic image.",
        "Output must look like a real architectural photograph.",
    ]
    return "\n".join(lines)
```

### API Response
```json
{
  "final_image": "base64_png",
  "prompt_used": "string (for debugging)"
}
```

---

## Module 6 — Cost Estimation

**Purpose**: Calculate area, material quantities, and costs from masks.

**File**: `backend/routers/estimate.py` + `backend/services/cost_engine.py`
**API**: `POST /api/estimate`

### Area Calculation from Masks
```python
def calculate_area_sqft(mask_b64: str, image_width_px: int, house_width_ft: float) -> float:
    """
    Convert mask pixel count to square feet.
    User provides house_width_ft as reference scale.
    """
    mask = base64_to_array(mask_b64)
    mask_pixels = np.count_nonzero(mask)

    pixels_per_ft = image_width_px / house_width_ft
    area_sqft = mask_pixels / (pixels_per_ft ** 2)

    return round(area_sqft, 1)
```

### Rates Database (`backend/data/rates.json`)
```json
{
  "material_rates": {
    "paint":          { "unit": "litre",  "rate_inr": 450,  "coverage_sqft": 100 },
    "stone_cladding": { "unit": "sqft",   "rate_inr": 180,  "wastage": 0.10 },
    "tile":           { "unit": "sqft",   "rate_inr": 150,  "wastage": 0.10 },
    "texture_finish": { "unit": "sqft",   "rate_inr": 90,   "wastage": 0.05 },
    "tile_roofing":   { "unit": "sqft",   "rate_inr": 200,  "wastage": 0.10 }
  },
  "labor_rates": {
    "paint":          { "unit": "sqft",   "rate_inr": 25  },
    "stone_cladding": { "unit": "sqft",   "rate_inr": 70  },
    "tile":           { "unit": "sqft",   "rate_inr": 50  },
    "texture_finish": { "unit": "sqft",   "rate_inr": 40  },
    "tile_roofing":   { "unit": "sqft",   "rate_inr": 60  }
  }
}
```

### API Response
```json
{
  "areas": {
    "main_wall": { "area_sqft": 820.5, "pixels": 2245000 },
    "pillar":    { "area_sqft": 48.2,  "pixels": 103000 }
  },
  "cost_breakdown": [
    {
      "region": "Main Wall",
      "material": "Natural Stone Cladding",
      "area_sqft": 820.5,
      "quantity": "902 sqft (incl. 10% wastage)",
      "material_cost": 162360,
      "labor_cost": 57435,
      "total": 219795
    }
  ],
  "summary": {
    "total_material_cost": 195000,
    "total_labor_cost": 72000,
    "grand_total": 267000,
    "currency": "INR"
  }
}
```

---

## Module 7 — PDF Report (ReportLab)

**Purpose**: Generate downloadable PDF report.

**File**: `backend/routers/report.py` + `backend/services/pdf_builder.py`
**API**: `POST /api/report`

### PDF Sections
1. **Cover Page** — Title, date, project reference
2. **Original House Image** — Full width
3. **Segmentation Overlay** — Colored region map
4. **AI Renovated Image** — Full width
5. **Material Selection Table** — Region → Material → Color/Texture
6. **Area Calculation Table** — Region → Pixels → Sqft
7. **Cost Breakdown Table** — Material cost + Labor cost per region
8. **Grand Total** — Highlighted box
9. **Assumptions & Disclaimer**

### API Response
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="renovation_report.pdf"
```

---

## Frontend Page Flow

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: Upload Page                                     │
│  ├── Drag & drop image upload                           │
│  ├── POST /api/analyze                                  │
│  ├── Show validation result (pass/fail)                 │
│  ├── If fail: show rejection reason + suggestion        │
│  └── If pass: show analysis (floors, regions) → Next    │
├─────────────────────────────────────────────────────────┤
│  Step 2: Segment Page                                    │
│  ├── "Segment My House" button                          │
│  ├── POST /api/segment (loading: ~4-5 min)              │
│  ├── Show: original image with colored overlay           │
│  ├── Sidebar: list detected regions with toggle          │
│  └── "Looks Good, Continue" → Next                      │
├─────────────────────────────────────────────────────────┤
│  Step 3: Material Selection Page                         │
│  ├── Left: House image, highlight region on hover        │
│  ├── Right: Material panel for selected region           │
│  ├── For each region: choose Paint/Texture               │
│  ├── Live preview: POST /api/composite on change         │
│  └── "Generate AI Visualization" → Next                  │
├─────────────────────────────────────────────────────────┤
│  Step 4: Visualization Page                              │
│  ├── POST /api/visualize (loading: 10-30s)              │
│  ├── Before/After slider comparison                     │
│  └── "Calculate Cost" → Next                            │
├─────────────────────────────────────────────────────────┤
│  Step 5: Cost Page                                       │
│  ├── Input: house_width_ft (default 30ft)               │
│  ├── POST /api/estimate                                 │
│  ├── Editable cost table (change rates → recalculate)   │
│  └── Grand total highlighted                            │
├─────────────────────────────────────────────────────────┤
│  Step 6: Report Page                                     │
│  ├── Preview summary of all data                        │
│  └── "Download PDF" → POST /api/report                  │
└─────────────────────────────────────────────────────────┘
```

---

## API Summary

| Method | Endpoint | Module | Time | Input | Output |
|--------|----------|--------|------|-------|--------|
| POST | `/api/analyze` | M1 | ~5s | Image file | Validation + analysis JSON |
| POST | `/api/segment` | M2 | ~4-5min | Image base64 | Masks + overlay |
| POST | `/api/composite` | M4 | ~1-2s | Image + masks + selections | Preview image |
| POST | `/api/visualize` | M5 | ~10-30s | Image + prompt | AI-generated image |
| POST | `/api/estimate` | M6 | ~1s | Masks + selections + width | Cost JSON |
| POST | `/api/report` | M7 | ~2s | Full project data | PDF binary |

---

## Dependencies

### Backend (`requirements.txt`)
```
fastapi
uvicorn[standard]
python-multipart
python-dotenv
pydantic

# AI Models
torch
transformers
ultralytics
Pillow

# Image Processing
opencv-python-headless
numpy

# Google Cloud
google-cloud-aiplatform
google-auth
requests

# PDF
reportlab
```

### Frontend (`package.json`)
```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "react-router-dom": "^6",
    "zustand": "^4",
    "axios": "^1",
    "react-dropzone": "^14",
    "react-before-after-slider-component": "^1",
    "react-colorful": "^5"
  }
}
```

---

## Build Order

```
Phase 1 — Backend Setup + M1 + M2 Service
  1. Create backend/ folder with FastAPI scaffold
  2. Port segmentation logic from test_m1_m2.py → services/segmentation.py
  3. Create /api/analyze endpoint (Gemini validation)
  4. Create /api/segment endpoint (wraps segmentation service)
  5. Test both endpoints with curl/Postman

Phase 2 — M4 Compositing
  6. Create services/compositing.py (paint + texture overlay)
  7. Create /api/composite endpoint
  8. Create texture files in data/textures/
  9. Test with sample masks

Phase 3 — Frontend Core
  10. Scaffold React/Vite frontend
  11. Build Upload page + M1 integration
  12. Build Segment page + M2 integration
  13. Build Material page + M4 live preview

Phase 4 — M5 + M6 + M7
  14. Build /api/visualize (Gemini image generation)
  15. Build /api/estimate (cost calculation)
  16. Build /api/report (PDF generation)
  17. Build remaining frontend pages

Phase 5 — Polish + Deploy
  18. End-to-end testing
  19. Deploy backend to Render
  20. Deploy frontend to Vercel
```

---

## Open Questions

> [!IMPORTANT]
> **GPU Hosting**: Segmentation requires GPU (~4GB VRAM). Render free tier has NO GPU. Options:
> 1. Run M2 locally, deploy M1+M4-M7 to Render (cheapest)
> 2. Use GPU cloud (RunPod/Modal) for M2 only
> 3. Pre-compute masks locally, upload to frontend
>
> Which approach?

> [!IMPORTANT]
> **Gemini Image Model**: Which model do you have access to for Module 5?
> - `gemini-2.0-flash-exp` (image editing)
> - `imagen-3.0-capability-001` (image generation)
> - Both?

> [!NOTE]
> All cost rates are in **Indian Rupees (₹)**. Confirm if correct.
