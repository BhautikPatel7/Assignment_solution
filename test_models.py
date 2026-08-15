import os
import json
import base64
import requests
import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account

# ─── CONFIG ────────────────────────────────────────────────────────────────────
CREDS_PATH = "model-choir-436813-m8-b86cfdc682b0.json"
TEST_IMAGE  = "data/Gemini_Generated_Image_8a6p4x8a6p4x8a6p.png"
LOCATION    = "us-central1"

M1_MODELS = [
    "gemini-2.5-pro-preview-06-05",
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

M2_MODELS = [
    "gemini-2.5-pro-preview-06-05",
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.0-flash-exp",
]

M1_PROMPT = """You are an architectural analysis AI.
Analyze this exterior house image and return ONLY a valid JSON object:
{
  "image_quality": "good",
  "house_detected": true,
  "rejection_reason": null,
  "floors": 2,
  "regions_present": ["main_wall", "pillar", "balcony", "railing", "roof", "boundary_wall"],
  "protected_regions": ["window", "door", "sky", "trees"],
  "confidence": 0.95,
  "notes": "brief observation"
}
Only include regions from: main_wall, accent_wall, pillar, balcony, railing, roof, boundary_wall, window, door
Return ONLY valid JSON, no markdown, no explanation."""

M2_PROMPT = """Detect and segment the following architectural elements from this house exterior image.
Segment these regions: main_wall, pillar, balcony, railing, roof, boundary_wall
For each detected region, return a JSON array with objects containing:
- "label": region name
- "box_2d": [y_min, x_min, y_max, x_max] normalized 0-1000
- "mask": base64-encoded PNG mask image
Do NOT segment: windows, doors, sky, trees, vehicles, people.
Return ONLY a valid JSON array."""

def get_project_id():
    with open(CREDS_PATH) as f:
        return json.load(f)["project_id"]

def get_token():
    creds = service_account.Credentials.from_service_account_file(CREDS_PATH, scopes=['https://www.googleapis.com/auth/cloud-platform'])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token

def encode_image(image_path):
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8'), mime

def call_vertex(project_id, model, token, image_b64, mime, prompt):
    url = f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/{LOCATION}/publishers/google/models/{model}:generateContent"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": mime, "data": image_b64}}, {"text": prompt}]}], "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}
    return requests.post(url, json=payload, headers=headers, timeout=120)

def parse_response(resp):
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {resp.text[:300]}"
    try:
        data = resp.json()
        raw = data['candidates'][0]['content']['parts'][0]['text']
        raw = raw.strip()
        if raw.startswith(" + "`" + json"): raw = raw[7:]
        if raw.startswith(" + "`" + "): raw = raw[3:]
        if raw.endswith(" + "`" + "): raw = raw[:-3]
        return json.loads(raw.strip()), None
    except Exception as e:
        return None, f"Parse error: {e}"

def test_m1(project_id, token, image_b64, mime):
    print("\n" + "="*60)
    print("  MODULE 1 - Image Analysis (JSON output)")
    print("="*60)
    for model in M1_MODELS:
        print(f"\n  Testing: {model} ...")
        try:
            resp = call_vertex(project_id, model, token, image_b64, mime, M1_PROMPT)
            result, err = parse_response(resp)
            if err:
                print(f"  FAILED - {err}")
            else:
                print(f"  SUCCESS!")
                print(f"     house_detected : {result.get('house_detected')}")
                print(f"     floors         : {result.get('floors')}")
                print(f"     image_quality  : {result.get('image_quality')}")
                print(f"     regions_present: {result.get('regions_present')}")
                with open("test_m1_result.json", "w") as f:
                    json.dump(result, f, indent=2)
                print(f"  RECOMMENDED M1 MODEL: {model}")
                return model
        except Exception as e:
            print(f"  EXCEPTION - {e}")
    return None

def test_m2(project_id, token, image_b64, mime):
    print("\n" + "="*60)
    print("  MODULE 2 - Segmentation (Mask output)")
    print("="*60)
    for model in M2_MODELS:
        print(f"\n  Testing: {model} ...")
        try:
            resp = call_vertex(project_id, model, token, image_b64, mime, M2_PROMPT)
            result, err = parse_response(resp)
            if err:
                print(f"  FAILED - {err}")
            else:
                if isinstance(result, list) and len(result) > 0:
                    detected = [r.get("label") for r in result]
                    has_masks = all("mask" in r for r in result)
                    has_boxes = all("box_2d" in r for r in result)
                    print(f"  SUCCESS!")
                    print(f"     Detected regions : {detected}")
                    print(f"     Has masks        : {has_masks}")
                    print(f"     Has bounding boxes: {has_boxes}")
                    if has_masks:
                        first_mask = result[0]["mask"]
                        label = result[0]["label"]
                        mask_bytes = base64.b64decode(first_mask)
                        with open(f"test_mask_{label}.png", "wb") as f:
                            f.write(mask_bytes)
                        print(f"     Mask saved: test_mask_{label}.png")
                    summary = [{"label": r.get("label"), "box_2d": r.get("box_2d"), "mask_length": len(r.get("mask", ""))} for r in result]
                    with open("test_m2_result.json", "w") as f:
                        json.dump(summary, f, indent=2)
                    print(f"  RECOMMENDED M2 MODEL: {model}")
                    return model
                else:
                    print(f"  UNEXPECTED FORMAT: {type(result)} | {str(result)[:200]}")
        except Exception as e:
            print(f"  EXCEPTION - {e}")
    return None

print("\nE2M - Model Validation Test")
project_id = get_project_id()
token = get_token()
print(f"  Project: {project_id}")
image_b64, mime = encode_image(TEST_IMAGE)
print(f"  Image encoded: {len(image_b64)} chars, type: {mime}")
m1 = test_m1(project_id, token, image_b64, mime)
m2 = test_m2(project_id, token, image_b64, mime)
print("\n" + "="*60)
print(f"  M1 (Analysis)    : {m1 or 'None worked'}")
print(f"  M2 (Segmentation): {m2 or 'None worked'}")
print("="*60)
