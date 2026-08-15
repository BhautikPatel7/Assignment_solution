# E2M Segmentation Setup & Process Guide

This document outlines the architecture and setup process for **Module 2 (Segmentation)** using our local, GPU-accelerated pipeline.

## 🧠 How the Process Works
We initially tried using Cloud APIs (Gemini) and GroundingDINO, but ran into deprecation issues and Windows compilation blockers (Rust/MSVC). We pivoted to a **100% local, no-compilation approach** using the `ultralytics` library.

The pipeline uses two state-of-the-art AI models working together:
1. **YOLO-World (Zero-Shot Object Detection):** 
   - **Exact Model Used:** `yolov8s-worldv2.pt` (Small version, ~49 MB)
   - We give it a list of plain English words (e.g., `"wall"`, `"balcony"`, `"roof"`).
   - It scans the image and draws **bounding boxes** around where it thinks those items are.
2. **SAM2 (Segment Anything Model 2 by Meta):**
   - **Exact Model Used:** `sam2_b.pt` (Base version, ~154 MB)
   - We feed the bounding boxes from YOLO-World into SAM2.
   - SAM2 converts those rough boxes into **pixel-perfect masks** (silhouettes) of the objects.

This combination gives us high-quality architectural segmentation in just a few seconds, entirely for free on your local GPU.

---

## ⚙️ Installation Guide (Windows + NVIDIA GPU)

Since PyTorch is very large (~2.5GB), standard `pip install` sometimes times out. Follow these steps to set up the environment reliably.

### 1. Download PyTorch CUDA Manually
1. Open your web browser and download this exact wheel file:
   ```text
   https://download.pytorch.org/whl/cu124/torch-2.6.0%2Bcu124-cp313-cp313-win_amd64.whl
   ```
2. Save it to your project root (e.g., `A:\Temp\E2M solution\`).

### 2. Install PyTorch from the Local File
Open your terminal, activate your virtual environment, and install the downloaded file:
```powershell
.\venv\Scripts\activate
pip install ".\torch-2.6.0+cu124-cp313-cp313-win_amd64.whl"
```

### 3. Install Ultralytics & Dependencies
Ultralytics handles YOLO-World and SAM2 without requiring complex C++ or Rust compilers.
```powershell
pip install ultralytics opencv-python Pillow numpy
```

### 4. Fix Torchvision Compatibility
Because we installed a specific PyTorch version (`2.6.0+cu124`), we must install the matching `torchvision` version to avoid missing operator errors (`torchvision::nms`).
```powershell
pip install torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
```

---

## 🚀 How to Run the Segmentation

Run the test script:
```powershell
python test_m2_yolo.py
```

### What happens when you run it:
1. **First Run Only:** It will automatically download the lightweight model weights from Ultralytics (`yolov8s-worldv2.pt` ~49MB and `sam2_b.pt` ~154MB).
2. It reads `data/old_weathered_house.png`.
3. It detects the regions based on the text prompts defined in `REGION_CLASSES`.
4. It saves individual black-and-white mask files for each region into the `test_masks/` directory (e.g., `main_wall.png`, `roof.png`).
5. It generates a summary JSON file (`test_m2_result.json`).
6. It creates a colored visual overlay (`test_masks/overlay.png`) so you can verify the AI's accuracy.

### Tuning the AI
If the AI misses parts of the house, open `test_m2_yolo.py` and tweak two things:
- **`REGION_CLASSES`**: Keep the names simple (e.g., `"wall"` works better than `"exterior concrete wall"`).
- **`DETECTION_CONF`**: Lowering this number (e.g., to `0.05`) makes the AI more sensitive and likely to find objects, but increases the chance of false positives.
