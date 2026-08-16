import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import InferenceClient


# --------------------------------------------------
# Load .env
# --------------------------------------------------

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise RuntimeError(
        "HF_TOKEN not found in .env"
    )


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MODEL = "black-forest-labs/FLUX.1-schnell"

PROMPT = """
A photorealistic modern Indian house exterior,
two-story contemporary architecture,
white walls with dark gray accents,
large glass windows,
modern balcony with glass railing,
warm exterior lighting,
beautiful landscaping,
professional architectural photography,
front elevation,
no people,
no text
"""

OUTPUT_DIR = Path("image")
OUTPUT_FILE = OUTPUT_DIR / "house.png"


# --------------------------------------------------
# Create output directory
# --------------------------------------------------

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# Create Hugging Face client
# --------------------------------------------------

client = InferenceClient(
    provider="auto",
    api_key=HF_TOKEN
)


# --------------------------------------------------
# Generate image
# --------------------------------------------------

print("Generating image...")
print(f"Model: {MODEL}")

try:

    image = client.text_to_image(
        prompt=PROMPT,
        model=MODEL
    )

except Exception as e:

    print("Image generation failed.")
    print(f"Error: {e}")
    raise


# --------------------------------------------------
# Save
# --------------------------------------------------

image.save(OUTPUT_FILE)

print()
print("Image generated successfully!")
print(f"Saved to: {OUTPUT_FILE.resolve()}")