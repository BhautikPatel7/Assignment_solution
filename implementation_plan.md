# AI-Based Exterior House Renovation & Cost Estimation System
## Full Implementation Plan — Prototype

---

## Overview

A full-stack web application that lets users upload a house exterior photo, segment architectural regions using Gemini (Vertex AI), apply materials, get a photorealistic AI-generated renovation preview, and download a PDF cost report.

**Stack**: FastAPI (Python) + React (Vite) + Gemini API (Vertex AI)  
**Hosting**: Render (backend) + Vercel (frontend)  
**Storage**: No DB — stateless, in-memory/temp processing  

---

## Prototype Scope (Controlled)

### Segments (MVP — 8 regions)
| ID | Region |
|----|--------|
| `main_wall` | Main exterior wall |
| `accent_wall` | Lower / secondary wall |
| `pillar` | Pillars / columns |
| `balcony` | Balcony slab/wall |
| `railing` | Balcony / staircase railing |
| `roof` | Roof / roof edge |
| `boundary_wall` | Compound / boundary wall |
| `window` | Windows (protected, not editable) |
| `door` | Doors (protected, not editable) |

### Materials Per Region (Limited Options)
| Region | Material Options |
|--------|----------------|
| main_wall | Paint (5 colors), Stone Cladding (3 types), Texture Finish (2 types) |
| accent_wall | Paint (5 colors), Tile (3 types), Stone Cladding (2 types) |
| pillar | Paint (5 colors), Texture Finish (2 types), Stone Cladding (2 types) |
| balcony | Paint (5 colors), Tile (2 types) |
| railing | Glass Railing, Black Metal, Stainless Steel |
| roof | Tile Roofing (2 types), Flat Concrete |
| boundary_wall | Paint (5 colors), Stone Cladding (2 types) |

---

## System Architecture

```
Frontend (React/Vite)          Backend (FastAPI)
        │                              │
        │  POST /api/analyze           │
        │ ──────────────────────────►  │  ── Gemini Vision (M1)
        │                              │
        │  POST /api/segment           │
        │ ──────────────────────────►  │  ── Gemini Segmentation (M2)
        │                              │
        │  POST /api/composite         │
        │ ──────────────────────────►  │  ── OpenCV Compositing (M4)
        │                              │
        │  POST /api/visualize         │
        │ ──────────────────────────►  │  ── Gemini Imagen (M5)
        │                              │
        │  POST /api/estimate          │
        │ ──────────────────────────►  │  ── Python Logic (M6)
        │                              │
        │  POST /api/report            │
        │ ──────────────────────────►  │  ── ReportLab PDF (M7)
        │                              │
```

---

## Proposed File Structure

### Backend
```
backend/
├── main.py                  # FastAPI app + CORS
├── requirements.txt
├── .env                     # GOOGLE_APPLICATION_CREDENTIALS, PROJECT_ID
│
├── routers/
│   ├── analyze.py           # M1 — Image understanding
│   ├── segment.py           # M2 — Gemini segmentation
│   ├── composite.py         # M4 — OpenCV compositing
│   ├── visualize.py         # M5 — Gemini image generation
│   ├── estimate.py          # M6 — Area + cost calculation
│   └── report.py            # M7 — PDF generation
│
├── services/
│   ├── gemini_client.py     # Vertex AI Gemini client (shared)
│   ├── segmentation.py      # Segmentation logic + mask processing
│   ├── compositing.py       # OpenCV texture overlay logic
│   ├── cost_engine.py       # Rates DB + calculation logic
│   └── pdf_builder.py       # ReportLab PDF assembly
│
├── data/
│   ├── materials.json       # Material catalog (rates, textures, colors)
│   ├── rates.json           # Labor + material rates (₹)
│   └── textures/            # Texture image files (PNG)
│       ├── stone_natural.png
│       ├── stone_slate.png
│       ├── tile_marble.png
│       ├── tile_wood.png
│       ├── texture_sand.png
│       └── texture_concrete.png
│
└── temp/                    # Runtime temp files (gitignored)
    └── .gitkeep
```

### Frontend
```
frontend/
├── index.html
├── vite.config.js
├── package.json
│
├── src/
│   ├── main.jsx
│   ├── App.jsx              # Route definitions
│   ├── index.css            # Global design system
│   │
│   ├── pages/
│   │   ├── UploadPage.jsx       # Step 1
│   │   ├── SegmentPage.jsx      # Step 2
│   │   ├── MaterialPage.jsx     # Step 3
│   │   ├── VisualizePage.jsx    # Step 4 + 5
│   │   ├── CostPage.jsx         # Step 6
│   │   └── ReportPage.jsx       # Step 7
│   │
│   ├── components/
│   │   ├── Stepper.jsx          # Step progress indicator
│   │   ├── ImageUploader.jsx    # Drag & drop upload
│   │   ├── SegmentOverlay.jsx   # Colored mask overlay on image
│   │   ├── RegionPanel.jsx      # Region list sidebar
│   │   ├── MaterialCard.jsx     # Material option card
│   │   ├── ColorPicker.jsx      # Paint color picker
│   │   ├── BeforeAfterSlider.jsx # Before/After comparison
│   │   ├── CostTable.jsx        # Editable cost breakdown
│   │   └── LoadingOverlay.jsx   # AI processing loading state
│   │
│   ├── store/
│   │   └── projectStore.js      # Zustand global state
│   │
│   ├── api/
│   │   └── client.js            # Axios API calls
│   │
│   └── constants/
│       ├── materials.js         # Material catalog (mirrored from backend)
│       └── regions.js           # Region display config + colors
```

---

## Module-by-Module Implementation

---

### Module 1 — Image Understanding (Gemini Vision)

**File**: `backend/routers/analyze.py`  
**API**: `POST /api/analyze`

**What it does**:
- Accepts uploaded image (base64 or multipart)
- Calls Gemini 1.5 Pro Vision via Vertex AI
- Returns structured JSON about the house

**Gemini Prompt**:
```
You are an architectural analysis AI.

Analyze this exterior house image and return ONLY a valid JSON object with this exact structure:

{
  "image_quality": "good|poor|unusable",
  "house_detected": true|false,
  "rejection_reason": null or "string",
  "floors": 1|2|3,
  "regions_present": ["main_wall", "pillar", "balcony", "railing", "roof", "boundary_wall"],
  "protected_regions": ["window", "door", "sky", "trees"],
  "confidence": 0.0-1.0,
  "notes": "any relevant observation"
}

Only include regions from this list:
main_wall, accent_wall, pillar, balcony, railing, roof, boundary_wall, window, door
```

**Response to frontend**:
```json
{
  "session_id": "uuid",
  "image_b64": "...",
  "analysis": { ... }
}
```

---

### Module 2 — Segmentation (Gemini Segmentation API via Vertex AI)

**File**: `backend/routers/segment.py`  
**API**: `POST /api/segment`

**What it does**:
- Takes the house image + list of regions from M1
- Calls Gemini Segmentation model (Vertex AI)
- Returns binary masks for each detected region
- Returns colored overlay for UI display

**Gemini Segmentation Call**:
```python
# Vertex AI Gemini segmentation
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel, Image

model = GenerativeModel("gemini-2.0-flash-exp")  # or segmentation variant

# Prompt format for segmentation
prompt = """
Segment the following architectural regions from this house exterior image.
Return segmentation masks for each region separately.

Regions to segment:
- main_wall (the primary exterior wall surface)
- accent_wall (lower or secondary wall, if present)
- pillar (any columns or pillars)
- balcony (balcony slab or wall)
- railing (balcony or staircase railing)
- roof (visible roof surface or edge)
- boundary_wall (compound wall)

Do NOT segment: windows, doors, sky, trees, vehicles, people.
"""
```

**Mask Processing** (`backend/services/segmentation.py`):
```python
def process_masks(raw_masks, image_shape):
    """
    Convert Gemini segmentation output to binary PNG masks.
    Returns dict: { "main_wall": binary_mask_array, ... }
    """
    masks = {}
    for region_id, mask_data in raw_masks.items():
        # Resize to match original image dimensions
        binary_mask = cv2.resize(mask_data, (image_shape[1], image_shape[0]))
        # Threshold to binary
        _, binary = cv2.threshold(binary_mask, 127, 255, cv2.THRESH_BINARY)
        masks[region_id] = binary
    return masks

def create_overlay_image(original_image, masks):
    """
    Create a colored overlay image for UI display.
    Each region gets a distinct semi-transparent color.
    """
    REGION_COLORS = {
        "main_wall":     (255, 100, 100, 120),  # Red
        "accent_wall":   (100, 200, 100, 120),  # Green
        "pillar":        (100, 100, 255, 120),  # Blue
        "balcony":       (255, 200,  50, 120),  # Yellow
        "railing":       (200,  50, 200, 120),  # Purple
        "roof":          (50,  200, 200, 120),  # Cyan
        "boundary_wall": (200, 150,  50, 120),  # Brown
    }
    overlay = original_image.copy()
    for region_id, mask in masks.items():
        color = REGION_COLORS.get(region_id, (200, 200, 200, 100))
        overlay = apply_colored_mask(overlay, mask, color)
    return overlay
```

**Response to frontend**:
```json
{
  "session_id": "uuid",
  "masks": {
    "main_wall":    "base64_png",
    "pillar":       "base64_png",
    "balcony":      "base64_png",
    "railing":      "base64_png",
    "roof":         "base64_png",
    "boundary_wall":"base64_png"
  },
  "overlay_image": "base64_png",
  "detected_regions": ["main_wall", "pillar", "balcony", "railing", "roof"]
}
```

---

### Module 3 — Material Catalog (Frontend)

**No backend call needed** — pure frontend state management.

**`frontend/src/constants/materials.js`**:
```javascript
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
          { id: "natural_stone", label: "Natural Stone",  texture: "/textures/stone_natural.png", rate: 180 },
          { id: "slate_stone",   label: "Slate Stone",    texture: "/textures/stone_slate.png",   rate: 160 },
          { id: "sandstone",     label: "Sandstone",      texture: "/textures/stone_sand.png",    rate: 140 },
        ]
      },
      {
        id: "texture_finish", label: "Texture Finish", type: "texture",
        options: [
          { id: "sand_texture",     label: "Sand Texture",     texture: "/textures/texture_sand.png",     rate: 90 },
          { id: "concrete_texture", label: "Concrete Texture",  texture: "/textures/texture_concrete.png", rate: 80 },
        ]
      },
    ]
  },
  railing: {
    label: "Railing",
    options: [
      { id: "glass",  label: "Glass Railing",     color: "#C8E6FA", rate: 2500 },
      { id: "black",  label: "Black Metal",        color: "#2D2D2D", rate: 1200 },
      { id: "steel",  label: "Stainless Steel",    color: "#C0C0C0", rate: 1500 },
    ]
  },
  // ... other regions
}
```

**Zustand Global State** (`frontend/src/store/projectStore.js`):
```javascript
{
  sessionId: null,
  originalImage: null,        // base64
  analysisResult: null,       // M1 output
  masks: {},                  // { region_id: base64_mask }
  overlayImage: null,         // colored overlay base64
  detectedRegions: [],        // list of region IDs
  
  materialSelection: {        // M3 — user choices
    // "main_wall": { material: "stone_cladding", style: "natural_stone", color: null }
    // "railing":   { material: "glass" }
  },
  
  compositeImage: null,       // M4 output
  finalImage: null,           // M5 output
  
  costData: null,             // M6 output
  houseWidth: 30,             // user input for scale (feet)
}
```

---

### Module 4 — OpenCV Compositing (Preview)

**File**: `backend/routers/composite.py`  
**API**: `POST /api/composite`

**What it does**:
- For each region → material selection:
  - **Paint**: Flood-fill mask region with selected color + brightness blend
  - **Texture** (Stone/Tile): Tile texture image over mask region with perspective correction
  - **Railing**: Apply color tint to railing mask
- Returns a composite preview image (fast, ~1-2 seconds)

**Core logic** (`backend/services/compositing.py`):
```python
def apply_paint(image, mask, hex_color):
    """Replace masked region pixels with color, preserve shadows/depth."""
    rgb = hex_to_rgb(hex_color)
    colored = np.zeros_like(image)
    colored[:] = rgb
    
    # Blend: keep original luminance, apply new color (HSL blend mode)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    luminance = gray / 255.0
    
    result = image.copy()
    for c in range(3):
        result[:, :, c] = np.where(
            mask > 0,
            np.clip(colored[:, :, c] * luminance * 1.2, 0, 255),
            image[:, :, c]
        )
    return result

def apply_texture(image, mask, texture_path):
    """Tile texture over masked region with perspective adjustment."""
    texture = cv2.imread(texture_path)
    h, w = image.shape[:2]
    
    # Tile texture to fill image dimensions
    tiled = tile_texture(texture, h, w)
    
    # Apply only within mask
    result = image.copy()
    mask_3ch = cv2.merge([mask, mask, mask]) / 255.0
    result = (result * (1 - mask_3ch) + tiled * mask_3ch).astype(np.uint8)
    
    return result
```

**Response**:
```json
{
  "composite_image": "base64_png"
}
```

---

### Module 5 — AI Visualization (Gemini Image Generation)

**File**: `backend/routers/visualize.py`  
**API**: `POST /api/visualize`

**What it does**:
- Builds a dynamic natural-language prompt from user's material selections
- Sends original house image + prompt to Gemini image generation (Vertex AI)
- Returns photorealistic renovated image

**Dynamic Prompt Builder**:
```python
def build_visualization_prompt(material_selection: dict) -> str:
    lines = [
        "You are a photorealistic architectural visualization AI.",
        "",
        "Renovate this house exterior image with the following specifications:",
        "- Preserve the exact original architecture, structure, geometry, and camera angle",
        "- Keep all windows, doors, and non-selected areas completely unchanged",
        "- Apply materials realistically with correct lighting, shadows, and perspective",
        "",
        "Material specifications:",
    ]
    
    MATERIAL_DESCRIPTIONS = {
        "paint":            lambda s, c: f"Apply {s['label']} exterior paint in color {c}",
        "stone_cladding":   lambda s, _: f"Apply realistic {s['label'].lower()} stone cladding texture",
        "texture_finish":   lambda s, _: f"Apply {s['label'].lower()} exterior texture finish",
        "tile":             lambda s, _: f"Apply {s['label'].lower()} ceramic tiles",
        "glass":            lambda s, _: "Install transparent glass railing panels",
        "black":            lambda s, _: "Install black powder-coated metal railing",
        "steel":            lambda s, _: "Install brushed stainless steel railing",
    }
    
    for region_id, selection in material_selection.items():
        region_label = REGION_LABELS[region_id]
        material = selection["material"]
        desc = MATERIAL_DESCRIPTIONS.get(material, lambda s, c: material)(selection, selection.get("color", ""))
        lines.append(f"- {region_label}: {desc}")
    
    lines += [
        "",
        "Generate a single photorealistic exterior renovation image.",
        "Output must look like a real architectural photograph.",
    ]
    
    return "\n".join(lines)
```

**Gemini API Call**:
```python
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
# OR use Gemini 2.0 with image editing capability

async def generate_visualization(image_b64: str, prompt: str):
    vertexai.init(project=PROJECT_ID, location="us-central1")
    
    # Option A: Gemini 2.0 Flash image editing
    model = GenerativeModel("gemini-2.0-flash-exp")
    response = await model.generate_content_async([
        image_from_base64(image_b64),
        prompt
    ])
    
    # Option B: Imagen 3 inpainting (if available)
    # model = ImageGenerationModel.from_pretrained("imagen-3.0-capability-001")
    
    return response
```

> **Note**: Use whichever Gemini image-generation endpoint you have access to on Vertex AI.
> If Gemini 2.0 Flash supports image output in your project, use that.
> Otherwise fall back to Imagen 3.

**Response**:
```json
{
  "final_image": "base64_png"
}
```

---

### Module 6 — Area + Quantity + Cost Estimation

**File**: `backend/routers/estimate.py`  
**API**: `POST /api/estimate`

**Rates Database** (`backend/data/rates.json`):
```json
{
  "material_rates": {
    "paint":            { "unit": "litre",      "rate": 450,  "coverage": 100 },
    "stone_cladding":   { "unit": "sqft",       "rate": 180,  "wastage": 0.10 },
    "tile":             { "unit": "sqft",       "rate": 150,  "wastage": 0.10 },
    "texture_finish":   { "unit": "sqft",       "rate": 90,   "wastage": 0.05 },
    "glass_railing":    { "unit": "running_ft", "rate": 2500 },
    "black_railing":    { "unit": "running_ft", "rate": 1200 },
    "steel_railing":    { "unit": "running_ft", "rate": 1500 }
  },
  "labor_rates": {
    "paint":          { "unit": "sqft",       "rate": 25  },
    "stone_cladding": { "unit": "sqft",       "rate": 70  },
    "tile":           { "unit": "sqft",       "rate": 50  },
    "texture_finish": { "unit": "sqft",       "rate": 40  },
    "railing":        { "unit": "running_ft", "rate": 300 }
  }
}
```

**Area Calculation from Masks**:
```python
def estimate_area_sqft(mask_b64: str, house_width_ft: float, image_width_px: int) -> float:
    """
    Pixel counting approach:
    1. Count non-zero pixels in mask
    2. Compute scale: pixels_per_ft = image_width_px / house_width_ft
    3. area_sqft = mask_pixels / (pixels_per_ft^2)
    """
    mask = base64_to_array(mask_b64)
    mask_pixels = np.count_nonzero(mask)
    
    pixels_per_ft = image_width_px / house_width_ft
    area_sqft = mask_pixels / (pixels_per_ft ** 2)
    
    return round(area_sqft, 1)
```

**Cost Calculation Output**:
```json
{
  "areas": {
    "main_wall":    { "area": 820, "unit": "sqft" },
    "pillar":       { "area": 120, "unit": "sqft" },
    "railing":      { "area": 42,  "unit": "running_ft" }
  },
  "quantities": {
    "main_wall":    { "material": "stone_cladding", "quantity": 275, "unit": "sqft" },
    "railing":      { "material": "glass_railing",  "quantity": 42,  "unit": "running_ft" }
  },
  "cost_breakdown": [
    {
      "region": "Main Wall",
      "material": "Natural Stone Cladding",
      "area": 275,
      "material_cost": 49500,
      "labor_cost": 19250,
      "total": 68750
    }
  ],
  "summary": {
    "total_material_cost": 95000,
    "total_labor_cost": 35000,
    "grand_total": 130000
  }
}
```

---

### Module 7 — PDF Report (ReportLab)

**File**: `backend/routers/report.py`  
**API**: `POST /api/report`

**Report Sections**:
1. Cover — Project title, date
2. Original house image
3. Renovated AI image
4. Material selection table
5. Area calculation table
6. Quantity table
7. Cost breakdown table
8. Grand total
9. Assumptions + Disclaimer

```python
from reportlab.platypus import SimpleDocTemplate, Image, Table, Paragraph
from reportlab.lib.pagesizes import A4

def build_report(data: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    story = []
    story.append(Paragraph("House Exterior Renovation Report", title_style))
    story.append(Paragraph(f"Date: {today}", normal_style))
    
    # Before / After images side by side
    story.append(two_column_images(data["original_image"], data["final_image"]))
    
    # Material selection
    story.append(material_table(data["material_selection"]))
    
    # Cost breakdown
    story.append(cost_table(data["cost_breakdown"]))
    
    # Grand total
    story.append(grand_total_box(data["summary"]))
    
    # Disclaimer
    story.append(Paragraph(DISCLAIMER_TEXT, small_style))
    
    doc.build(story)
    return buffer.getvalue()
```

---

## Frontend Page Flow

```
Step 1: Upload Page
  → Drag/drop or click to upload image
  → POST /api/analyze
  → Show: image quality, house detected, floors, regions found

Step 2: Segment Page
  → "Segment My House" button
  → POST /api/segment
  → Show: original image with colored mask overlay
  → List detected regions with checkboxes (user can deselect)
  → "Looks Good, Continue" button

Step 3: Material Selection Page
  → Left: House image with region highlight on hover
  → Right: Material panel for selected region
  → For each region: choose material type → color/texture
  → Show: composite preview (POST /api/composite, called on every selection change)
  → "Generate AI Visualization" button

Step 4: Visualization Page
  → POST /api/visualize (takes 10-30s, show loading)
  → Before/After slider (original vs AI image)
  → "Calculate Cost" button

Step 5: Cost Page
  → Input: house_width_ft (default 30ft)
  → POST /api/estimate
  → Editable rate table
  → On rate change: recalculate client-side
  → Grand total highlight

Step 6: Report Page
  → Preview of all data
  → "Download PDF Report" button
  → POST /api/report → download PDF file
```

---

## API Summary

| Method | Endpoint | Module | Input | Output |
|--------|----------|--------|-------|--------|
| POST | `/api/analyze` | M1 | image file | analysis JSON |
| POST | `/api/segment` | M2 | image + regions | masks + overlay |
| POST | `/api/composite` | M4 | image + masks + selection | preview image |
| POST | `/api/visualize` | M5 | image + selection | AI image |
| POST | `/api/estimate` | M6 | masks + selection + width | cost JSON |
| POST | `/api/report` | M7 | full project data | PDF binary |

---

## Environment Variables

```env
# backend/.env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GEMINI_MODEL_VISION=gemini-1.5-pro
GEMINI_MODEL_SEGMENT=gemini-2.0-flash-exp
GEMINI_MODEL_IMAGE=gemini-2.0-flash-exp
VERTEX_LOCATION=us-central1
```

---

## Dependencies

### Backend (`requirements.txt`)
```
fastapi
uvicorn
python-multipart
google-cloud-aiplatform
vertexai
opencv-python-headless
Pillow
numpy
reportlab
python-dotenv
pydantic
```

### Frontend (`package.json` deps)
```
react
react-router-dom
zustand
axios
react-dropzone
react-before-after-slider-component
react-colorful
```

---

## Deployment

### Backend (Render)
- Service type: Web Service
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Env vars: Set all from `.env` in Render dashboard
- GCP credentials: Upload service account JSON, set path env var

### Frontend (Vercel)
- Framework: Vite
- Build: `npm run build`
- Output: `dist/`
- Env: `VITE_API_URL=https://your-render-backend.onrender.com`

---

## Build Order (Recommended)

```
Day 1 — Morning
  1. Project setup (backend + frontend scaffold)
  2. M1 — Gemini image analysis endpoint + test
  3. M2 — Gemini segmentation endpoint + mask processing + test

Day 1 — Afternoon
  4. Frontend: Upload + Segment pages
  5. M3 — Material catalog (frontend only)
  6. M4 — OpenCV compositing endpoint

Day 2 — Morning
  7. Frontend: Material selection page + composite preview
  8. M5 — Gemini visualization endpoint
  9. Frontend: Visualization page + before/after slider

Day 2 — Afternoon
  10. M6 — Cost estimation endpoint
  11. M7 — PDF report endpoint
  12. Frontend: Cost + Report pages
  13. Testing end-to-end
  14. Deploy backend to Render, frontend to Vercel
```

---

## Open Questions

> [!IMPORTANT]
> **Gemini Image Generation Access**: Confirm which Gemini image generation model you have access to on Vertex AI. Options:
> - `gemini-2.0-flash-exp` (with image output)
> - `imagen-3.0-capability-001`
> - `imagegeneration@006`
> This determines the exact API call in Module 5.

> [!IMPORTANT]
> **Gemini Segmentation Model**: Confirm the exact model ID you are using for segmentation via Vertex AI. The segmentation output format (PNG masks vs polygon coordinates) will affect Module 2 processing logic.

> [!NOTE]
> **Currency**: All rates are in Indian Rupees (₹). Confirm if this is correct.
