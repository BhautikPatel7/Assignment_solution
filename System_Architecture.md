# E2M (Exterior to Material) System Architecture

This document provides a detailed architectural overview of the E2M platform. The system is an end-to-end computer vision and estimation pipeline designed to convert a single 2D photograph of a house exterior into a precise material-mapped renovation and an accurate, line-item cost estimate.

---

## 1. High-Level Architecture

The platform operates on a robust **Client-Server architecture**, strictly divided into two main components:

- **Frontend (Client):** A dynamic, single-page application built with React and Vite. It provides an intuitive, step-by-step wizard interface. The frontend manages state progression, handles large image uploads, provides an interactive canvas for manual mask correction, and renders the material catalog.
- **Backend (Server):** A high-performance Python API built with FastAPI. It coordinates the complex pipeline of image processing, computer vision inference, spatial math, and cost calculation.

To ensure performance and scalability without the overhead of a relational database, the backend utilizes a stateless **Session Manager**. Every image upload initializes a temporary session folder. This folder securely caches intermediate states—such as the original image, segmentation masks, and current material selections—enabling rapid progression between the five modules.

---

## 2. Core Services and AI Models

The backend is structured as a series of specialized microservices. Each service encapsulates a specific domain of the renovation workflow:

### A. Validation Service
- **Engine:** Google Gemini Vision (via Google Cloud Vertex AI REST API).
- **Purpose:** Acts as the initial intelligent gatekeeper. It analyzes the uploaded photo to validate that it is a well-lit, unobstructed exterior view of a residential building. It also performs a preliminary architectural breakdown (e.g., counting floors, detecting windows and doors) to flag edge cases before computationally expensive segmentation begins.

### B. Hybrid Segmentation Service
- **Engines:** 
  1. **SegFormer-b4**: Executes Phase 1 semantic segmentation using a 50% overlap sliding window mechanism. This generates initial broad masks identifying foundational regions (walls, roofs, pillars).
  2. **YOLO-World + SAM2 (Segment Anything Model)**: Executes Phase 2 as an area-constrained refinement pass. YOLO detects specific architectural bounding boxes, allowing SAM2 to generate precise, pixel-perfect sub-masks.
- **Purpose:** To isolate the exact pixel boundaries of different architectural components, resolving overlapping geometries and ensuring materials do not bleed across edges (e.g., paint spilling onto windows).

### C. Direct Compositing & Visualization Engine
- **Technology:** OpenCV and NumPy (Direct Image Processing).
- **Purpose:** To render the "After" image, the system utilizes a custom **Direct Compositing Engine** rather than relying on generative image models. Generative AI is prone to altering structural geometry or hallucinating non-existent architectural details. By using OpenCV math to warp, scale, and blend high-resolution textures (like Slate Stone or Paint Hex Colors) directly onto the segmented semantic masks, the system guarantees **100% preservation** of the original house's geometry, perspective, shadows, and lighting.

### D. Cost Estimation Service
- **Technology:** Python mathematical engine.
- **Purpose:** To calculate realistic material and labor costs based on the visual data. The engine bridges the gap between pixels and physical dimensions.

---

## 3. The 5-Step System Workflow

The architecture follows a strict, sequential pipeline where each module depends on the successful execution of the previous one:

### Step 1: Upload & Analysis
The user uploads an image. The Backend sends it to the Validation Engine for structural verification. If valid, a session is initialized and the original image is cached.

### Step 2: Segmentation & Mask Correction
The image is passed through the Hybrid Segmentation Service (SegFormer -> YOLO -> SAM2). The backend returns discrete mask layers to the frontend. The user is presented with a **Brush Tool Canvas**, allowing them to manually erase or add mask areas to correct any AI discrepancies before proceeding.

### Step 3: Material Application
The user enters the Material Catalog. They map real-world materials (e.g., *Natural Rough Stone*, *Modern Grey Paint*, *Stainless Steel Railings*) to the isolated architectural regions (*Main Wall*, *Balcony*, *Pillar*). This mapping dictionary is sent to the backend and saved to the session.

### Step 4: Intelligent Visualization
The Backend invokes the Direct Compositing Engine. The engine extracts the user's material selections, fetches the corresponding texture files or paint hex codes, and mathematically blends them onto the original image using the segmentation masks as stencils. The frontend receives the rendered composite and displays an interactive "Before & After" comparison slider.

### Step 5: Cost Calculation & PDF Report
The final step triggers the **Estimator Module**, which calculates the exact renovation cost using the following methodology:

1. **Spatial Conversion:** The system calculates the physical surface area. It counts the exact number of pixels in a given mask (e.g., the Main Wall mask) and converts that into Square Feet by scaling against an assumed default reference height (e.g., house height = 20 feet).
2. **Material Quantity:** The system calculates how much material is needed. For example, knowing that 1 liter of paint covers a specific square footage, it derives the total liters required.
3. **Cost Aggregation:** The physical quantity is multiplied by predefined local material rates and labor rates.
4. **PDF Generation:** A backend router utilizes **ReportLab** to compile the original image, the rendered composite, the material manifest, and the line-item cost calculations into a highly professional, downloadable PDF Report.
