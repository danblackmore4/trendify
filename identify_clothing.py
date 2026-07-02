# Sends an image to the OpenAI Vision API and returns a list of clothing items
# identified in it. Can accept either a remote URL or a local file path.
# Run directly: python identify_clothing.py <image_url_or_path>

import os
import sys
import json
import base64
import mimetypes
import hashlib
import time
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

# Extracted as a constant so both identify_clothing and classify_with_model
# use exactly the same prompt without duplication
_VISION_PROMPT = (
    "You are a fashion analyst helping to identify clothing for trend tracking. "
    "Identify every clothing item and pair of shoes visible in this image. "
    "Return a JSON array where each element has exactly these four keys:\n\n"

    # garment_type uses a fixed vocabulary so that aggregation works correctly —
    # if the model invents its own descriptions every time, we end up with
    # "oversized linen shirt" and "relaxed linen shirt" as separate trends
    # instead of both counting towards "linen shirt"
    '  "garment_type"  — you MUST pick the single closest matching value from the '
    "controlled vocabulary below. Do not invent new values, combine terms, or add "
    "descriptive words like 'oversized', 'fitted', 'linen', 'cropped', 'v-neck' — "
    "those details belong in style_details. The goal is consistent category labels "
    "across different images of the same item type.\n\n"
    "  Controlled vocabulary by category:\n"
    "  DRESSES: maxi dress, midi dress, mini dress, wrap dress, slip dress, "
    "shirt dress, bodycon dress, shift dress, sundress, kaftan dress, "
    "co-ord set, jumpsuit, playsuit\n"
    "  TOPS: crop top, tube top, fitted t-shirt, oversized t-shirt, "
    "longline t-shirt, blouse, button-up shirt, linen shirt, knit jumper, "
    "cardigan, vest top, bodysuit, polo shirt, hoodie, sweatshirt, "
    "corset top, halter top, off-shoulder top, tank top, cami top\n"
    "  BOTTOMS: wide-leg jeans, skinny jeans, straight-leg jeans, "
    "barrel-leg jeans, cargo trousers, tailored trousers, chinos, "
    "linen trousers, mini skirt, midi skirt, maxi skirt, denim skirt, "
    "pleated skirt, leather skirt, shorts, denim shorts, cycling shorts, "
    "leggings, wide-leg trousers\n"
    "  FOOTWEAR: trainers, loafers, sandals, strappy sandals, mules, "
    "heels, block heels, kitten heels, boots, ankle boots, knee-high boots, "
    "flip flops, ballet flats, platform shoes, mary janes, espadrilles, "
    "slip-on shoes\n"
    "  OUTERWEAR: blazer, oversized blazer, denim jacket, leather jacket, "
    "trench coat, puffer jacket, wool coat, bomber jacket, shacket, "
    "longline coat, faux fur coat, rain jacket\n"
    "  ACCESSORIES: tote bag, crossbody bag, shoulder bag, clutch, "
    "mini bag, sunglasses, headscarf, belt, hat, cap, bucket hat, "
    "jewellery, watch, scarf\n\n"

    '  "colour"        — always return the precise shade, never a generic colour name. '
    "Good examples: "
    '"washed light blue", "camel", "off-white", "ecru", "sage green", "cobalt blue", '
    '"chocolate brown", "dusty rose", "slate grey", "burgundy", "mustard yellow", '
    '"forest green", "blush pink", "charcoal", "rust orange", "navy", "butter yellow". '
    'Never use bare colour names like "blue", "white", "brown", "green", "grey".\n\n'

    # style_details captures everything descriptive that intentionally
    # stays out of garment_type — this is what makes aggregation consistent
    # while still preserving the nuance for display
    '  "style_details" — a short comma-separated phrase capturing everything descriptive '
    "that did NOT go into garment_type: fit, fabric, neckline, hem length, waistline, "
    "closures, print, texture, and any notable features. "
    "This is where 'oversized', 'cropped', 'v-neck', 'linen', 'ribbed', 'high-waisted', "
    "'distressed', 'wide-leg', 'pleated', 'square toe' etc all live. "
    'Examples: "v-neck, cropped hem, ruched side seam", '
    '"high-waisted, wide-leg, subtle pinstripe, linen", '
    '"square toe, block heel, ankle strap", '
    '"oversized fit, dropped shoulders, chest pocket, cotton". '
    "Leave as an empty string if nothing else is notable.\n\n"

    '  "season"        — classify based on fabric, weight, and style as exactly one of: '
    '"warm-weather", "cold-weather", or "all-season". '
    "Lightweight or open pieces (linen, voile, mesh, sandals, shorts, strappy tops) = warm-weather. "
    "Heavy or insulating pieces (wool, fleece, padded, thick knit, coats, boots) = cold-weather. "
    "Everything wearable year-round with light layering (cotton tees, mid-weight jeans, "
    "blazers, loafers, simple dresses) = all-season. "
    "If uncomfortable in cool weather without a layer, choose warm-weather over all-season.\n\n"

    "Include every item that is at least partially visible. "
    'If no clothing or shoes are visible at all, return the string "no clothing detected" '
    "instead of a JSON array."
)


def download_image(image_url: str) -> tuple[str, str]:
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # Hash the URL to get a stable cache filename — same URL always produces
    # the same filename so we never download the same image twice
    url_hash = hashlib.md5(image_url.encode()).hexdigest()

    # Instagram CDN blocks requests without a browser-like User-Agent
    req = urllib.request.Request(
        image_url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req) as response:
        content_type = response.headers.get_content_type()
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        # mimetypes returns ".jpe" for JPEG on some platforms, normalise it
        if ext in (".jpe", ".jpeg"):
            ext = ".jpg"
        local_path = os.path.join(IMAGES_DIR, f"{url_hash}{ext}")
        with open(local_path, "wb") as f:
            f.write(response.read())

    return local_path, content_type


def load_image(image_source: str) -> tuple[bytes, str]:
    # If it looks like a URL, download it (with caching); otherwise read from disk
    if image_source.startswith("http"):
        local_path, mime_type = download_image(image_source)
        with open(local_path, "rb") as f:
            return f.read(), mime_type
    else:
        # For local files, guess the MIME type from the extension
        mime_type, _ = mimetypes.guess_type(image_source)
        mime_type = mime_type or "image/jpeg"
        with open(image_source, "rb") as f:
            return f.read(), mime_type


def classify_with_model(image_source: str, model: str = "gpt-4o") -> tuple:
    # Runs the full classification and returns (result, input_tokens, output_tokens, elapsed_seconds).
    # Used by identify_clothing and by model_comparison.py so both always call the exact same prompt.
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found — add it to a .env file in the project root")

    raw_bytes, mime_type = load_image(image_source)
    # OpenAI's vision API accepts images as base64-encoded data URIs
    b64_image = base64.b64encode(raw_bytes).decode("utf-8")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 2048,
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"OpenAI API error {e.code}: {error_body}") from e
    elapsed = time.perf_counter() - start

    input_tokens = raw.get("usage", {}).get("prompt_tokens", 0)
    output_tokens = raw.get("usage", {}).get("completion_tokens", 0)

    content = raw["choices"][0]["message"]["content"].strip()

    if content.lower() == "no clothing detected":
        return "no clothing detected", input_tokens, output_tokens, elapsed

    # The model sometimes wraps its JSON in markdown code fences — strip them
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        items = json.loads(content)
        if isinstance(items, list):
            return items, input_tokens, output_tokens, elapsed
        # Occasionally the model wraps the array in an object like {"items": [...]}
        if isinstance(items, dict):
            for v in items.values():
                if isinstance(v, list):
                    return v, input_tokens, output_tokens, elapsed
    except json.JSONDecodeError:
        pass

    # If we still can't parse it, return the raw string so the caller can decide what to do
    return content, input_tokens, output_tokens, elapsed


def identify_clothing(image_source: str) -> str:
    # Thin wrapper around classify_with_model kept for backwards compatibility —
    # process_apify_export.py calls this and doesn't need token counts or timing
    result, _, _, _ = classify_with_model(image_source)
    return result


def main():
    if len(sys.argv) != 2:
        print("Usage: python identify_clothing.py <image_url>")
        sys.exit(1)

    image_url = sys.argv[1]
    result = identify_clothing(image_url)

    if isinstance(result, list):
        print(json.dumps(result, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
