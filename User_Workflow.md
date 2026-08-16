# E2M : End-User Workflow

This document outlines the step-by-step journey an end-user takes when using the E2M platform. The interface is designed as an intuitive, five-step wizard, ensuring that users with no architectural or technical background can seamlessly generate a home renovation visualization and cost estimate.

---

## Step 1: Image Upload & AI Validation

**Objective:** Capture the current state of the house.
**User Action:** 
- The user lands on the homepage and clicks the "Upload Photo" button. 
- They select a single, 2D photograph of their house exterior.

**System Response:**
- The image is immediately sent to the Validation AI.
- The system checks if the image is actually a house, well-lit, and unobstructed.
- **Success:** The user sees a "Validation Successful" message and is automatically moved to the next step.
- **Error Handling:** If the user uploads a photo of an interior room or a blurry image, the system halts and provides a friendly error message (e.g., "Please upload a clearer exterior photo"), preventing bad data from entering the pipeline.

---

## Step 2: AI Segmentation & Mask Correction

**Objective:** Identify the specific architectural components of the house (walls, roof, pillars).
**User Action:**
- The user clicks **"Proceed to Segmentation"**.
- After a brief loading screen, the user is presented with their image overlaid with colorful, semi-transparent masks highlighting different detected regions (e.g., Main Wall is blue, Roof is red).

**Interactive Correction (The Brush Tool):**
- If the AI missed a small section of a wall or accidentally highlighted a window, the user can select the "Eraser" or "Draw" brush tools.
- They can manually paint over the image to correct the mask boundaries, ensuring perfect precision before applying materials.

---

## Step 3: Material Selection

**Objective:** Choose the new aesthetic for the house.
**User Action:**
- The user clicks **"Proceed to Materials"** and is taken to the Material Catalog.
- The interface displays a list of the architectural regions detected in Step 2 (e.g., *Main Wall, Boundary Wall, Balcony*).
- For each region, the user opens a dropdown menu to select from a curated list of materials. 
  - They can choose rich textures (like *Slate Stone* or *Exposed Concrete*).
  - They can choose paint colors (like *Modern Grey* or *Terracotta Orange*).

---

## Step 4: Renovation Visualization

**Objective:** See the renovated house in real-time.
**User Action:**
- The user clicks **"Visualize Renovation"**.
- A loading screen indicates that the Direct Compositing Engine is mathematically blending their selected materials onto the house.
- The user is then presented with an interactive **Before & After Slider**.
- They can drag the slider left and right to compare their original house with the newly rendered, photorealistic visualization.
- **Action Options:** The user can download the rendered image directly to their device or proceed to calculate costs.

---

## Step 5: Cost Estimation & PDF Report

**Objective:** Generate a real-world cost breakdown based on the visual renovation.
**User Action:**
- The user clicks **"Proceed to Cost Estimation"**.
- The system displays a comprehensive financial dashboard showing:
  1. A line-item breakdown of every region edited.
  2. The calculated physical quantity needed (e.g., liters of paint or square feet of stone).
  3. The individual Material Cost and Labor Cost for each item.
  4. The **Grand Total** for the entire project.

**Final Deliverable:**
- The user clicks the **"Download PDF Report"** button.
- The browser downloads a beautifully formatted, professional PDF. The PDF contains the Before/After photos side-by-side, the exact materials chosen, the line-item cost breakdown, and the final grand total—ready to be handed to a contractor.
