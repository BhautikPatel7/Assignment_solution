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
