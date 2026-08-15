/**
 * api.js — Centralized API client for E2M backend
 * Backend runs on http://localhost:8004
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8004';

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
 * Health check
 */
export async function checkHealth() {
  const response = await fetch(`${BASE_URL}/health`);
  return response.ok;
}
