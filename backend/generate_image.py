import os
import base64
from pathlib import Path

from dotenv import load_dotenv
from google import genai


MODEL_NAME = "gemini-3.1-flash-image"

OUTPUT_DIR = Path("image")
OUTPUT_FILE = OUTPUT_DIR / "generated_house.jpg"

PROMPT = """
Create a photorealistic architectural visualization of a modern
Indian house exterior.

The house should have:

- modern contemporary architecture
- white and dark gray exterior walls
- large glass windows
- modern balcony with glass railing
- warm exterior lighting
- landscaped front yard
- realistic construction materials
- realistic shadows
- professional architectural photography

Show the complete front elevation of the house.

No people.
No text.
"""


# ------------------------------------------------------------
# Load .env
# ------------------------------------------------------------

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env file."
    )


# ------------------------------------------------------------
# Gemini client
# ------------------------------------------------------------

client = genai.Client(api_key=api_key)


# ------------------------------------------------------------
# Create output directory
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# Generate image
# ------------------------------------------------------------

print("Generating image...")
print(f"Model: {MODEL_NAME}")

try:

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=PROMPT,
        response_format={
            "type": "image",
            "mime_type": "image/jpeg",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        },
    )

except Exception as e:

    print("\nFailed to generate image.")
    print(f"Error: {e}")
    raise


# ------------------------------------------------------------
# Check response
# ------------------------------------------------------------

if not interaction.output_image:

    print("Gemini did not return an image.")

    if interaction.output_text:
        print("Model response:")
        print(interaction.output_text)

    raise RuntimeError("No image returned.")


# ------------------------------------------------------------
# Decode Base64
# ------------------------------------------------------------

image_bytes = base64.b64decode(
    interaction.output_image.data
)


# ------------------------------------------------------------
# Save image
# ------------------------------------------------------------

with open(OUTPUT_FILE, "wb") as f:
    f.write(image_bytes)


print("\nImage generated successfully!")
print(f"Saved to: {OUTPUT_FILE.resolve()}")