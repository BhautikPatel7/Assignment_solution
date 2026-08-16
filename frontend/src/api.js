/**
 * api.js — Centralized API client for E2M backend
 * Backend runs on http://localhost:8004
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Analyze a house image — Module 1
 * @param {File} imageFile
 * @returns {Promise<object>} API response
 */
export async function analyzeImage(imageFile) {
  const formData = new FormData();
  formData.append('image', imageFile);

  const response = await fetch(`${BASE_URL}/api/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Segment a validated house image — Module 2
 * Takes ~4-5 minutes. Pass session_id from M1 analyze response.
 * @param {string} sessionId
 * @returns {Promise<object>} Masks, overlay image, region details
 */
export async function segmentImage(sessionId) {
  const response = await fetch(`${BASE_URL}/api/segment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Segmentation failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Health check
 */
export async function checkHealth() {
  const response = await fetch(`${BASE_URL}/health`);
  return response.ok;
}

/**
 * Save a brush-corrected mask for one region — Module 2b
 * @param {string} sessionId
 * @param {string} regionId   — e.g. "main_wall"
 * @param {string} maskB64    — base64 grayscale PNG (same dims as original image)
 * @returns {Promise<object>} Updated region info + new overlay_image
 */
export async function updateMask(sessionId, regionId, maskB64) {
  const response = await fetch(`${BASE_URL}/api/segment/${sessionId}/masks`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ region_id: regionId, mask_b64: maskB64 }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to save mask: ${response.status}`);
  }

  return response.json();
}

/**
 * Apply material selections to house image — Module 4
 * Fast (~0.5-1s). Called live on every material change.
 *
 * @param {string} sessionId
 * @param {Object} selections  — { region_id: { type: "paint"|"texture", value: hex|filename } }
 * @returns {Promise<object>}  — { composite_image: base64, regions_applied: [] }
 */
export async function compositeImage(sessionId, selections) {
  const response = await fetch(`${BASE_URL}/api/composite`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, selections }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Composite failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Generate AI visualization of the renovated house — Module 4
 * Takes ~20-30 seconds. Uses HuggingFace img2img + Gemini Vision.
 *
 * @param {string} sessionId
 * @returns {Promise<object>} { visualization_image: base64, prompt_used, house_description }
 */
export async function visualizeImage(sessionId) {
  const response = await fetch(`${BASE_URL}/api/visualize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Visualization failed: ${response.status}`);
  }

  return response.json();
}
