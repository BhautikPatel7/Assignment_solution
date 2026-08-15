import os
import json
import base64
import requests
import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account

# ── CONFIG ────────────────────────────────────────────────────────
CREDS_PATH = "model-choir-436813-m8-b86cfdc682b0.json"
TEST_IMAGE  = "data/old_weathered_house.png"
MODEL       = "gemini-3.1-pro-preview"
LOCATION    = "us-central1"

# ── PROMPT ────────────────────────────────────────────────────────
PROMPT = (
    "You are an architectural analysis AI.\n"
    "Analyze this exterior house image and return ONLY a valid JSON object.\n"
    "Use exactly this structure:\n"
    "{\n"
    '  "image_quality": "good",\n'
    '  "house_detected": true,\n'
    '  "rejection_reason": null,\n'
    '  "floors": 2,\n'
    '  "regions_present": ["main_wall", "pillar", "balcony", "railing", "roof", "boundary_wall"],\n'
    '  "protected_regions": ["window", "door", "sky", "trees"],\n'
    '  "confidence": 0.95,\n'
    '  "notes": "short observation about the house"\n'
    "}\n"
    "Only use region names from: main_wall, accent_wall, pillar, balcony, railing, roof, boundary_wall, window, door\n"
    "Return ONLY valid JSON. No markdown. No explanation."
)

# ── STEP 1: Get project ID ─────────────────────────────────────────
print("=" * 55)
print("  E2M - Module 1 Test")
print("=" * 55)

with open(CREDS_PATH) as f:
    creds_data = json.load(f)
project_id = creds_data["project_id"]
print(f"  Project  : {project_id}")
print(f"  Model    : {MODEL}")
print(f"  Location : {LOCATION}")

# ── STEP 2: Get access token ───────────────────────────────────────
print("\n  [1] Getting access token...")
creds = service_account.Credentials.from_service_account_file(
    CREDS_PATH,
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
creds.refresh(google.auth.transport.requests.Request())
token = creds.token
print("      Token OK")

# ── STEP 3: Encode image ───────────────────────────────────────────
print(f"\n  [2] Encoding image: {TEST_IMAGE}")
with open(TEST_IMAGE, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")
print(f"      Size: {len(image_b64):,} chars  |  MIME: image/png")

# ── STEP 4: Call Vertex AI ─────────────────────────────────────────
url = (
    f"https://aiplatform.googleapis.com/v1/projects/{project_id}"
    f"/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent"
)
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}
payload = {
    "contents": [
        {
            "role": "user",
            "parts": [
                {"inlineData": {"mimeType": "image/png", "data": image_b64}},
                {"text": PROMPT},
            ],
        }
    ],
    "generationConfig": {
        "temperature": 0.1,
        "responseMimeType": "application/json",
    },
}

print(f"\n  [3] Calling Vertex AI...")
print(f"      URL: {url}")
resp = requests.post(url, json=payload, headers=headers, timeout=120)
print(f"      HTTP Status: {resp.status_code}")

# ── STEP 5: Parse response ─────────────────────────────────────────
print("\n  [4] Raw response:")
print("-" * 55)
print(resp.text[:2000])
print("-" * 55)

if resp.status_code == 200:
    try:
        data = resp.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```json"): raw = raw[7:]
        if raw.startswith("```"):     raw = raw[3:]
        if raw.endswith("```"):       raw = raw[:-3]
        result = json.loads(raw.strip())

        print("\n  Parsed JSON result:")
        print(json.dumps(result, indent=2))

        with open("test_m1_result.json", "w") as f:
            json.dump(result, f, indent=2)
        print("\n  Saved to: test_m1_result.json")

    except Exception as e:
        print(f"\n  Parse error: {e}")
else:
    print(f"\n  Request failed with status {resp.status_code}")
