import os
import sys
import json
import base64
import mimetypes
import hashlib
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def download_image(image_url: str) -> tuple[str, str]:
    """Download image to local images/ folder. Returns (local_path, mime_type)."""
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # Derive a stable filename from the URL so we don't re-download duplicates
    url_hash = hashlib.md5(image_url.encode()).hexdigest()

    req = urllib.request.Request(
        image_url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req) as response:
        content_type = response.headers.get_content_type()
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        # mimetypes can return .jpe for JPEG on some platforms
        if ext in (".jpe", ".jpeg"):
            ext = ".jpg"
        local_path = os.path.join(IMAGES_DIR, f"{url_hash}{ext}")
        with open(local_path, "wb") as f:
            f.write(response.read())

    return local_path, content_type


def identify_clothing(image_url: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found — add it to a .env file in the project root")

    local_path, mime_type = download_image(image_url)
    with open(local_path, "rb") as f:
        b64_image = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Identify all clothing items visible in this image. "
                            "For each item provide: garment type, colour, and style details. "
                            "Return the result as a JSON array of objects with keys "
                            '"garment_type", "colour", and "style_details". '
                            'If no clothing is visible, return the string "no clothing detected".'
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 1024,
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

    try:
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"OpenAI API error {e.code}: {error_body}") from e

    content = result["choices"][0]["message"]["content"].strip()

    # Normalise: if the model returned a bare "no clothing detected" string, pass it through
    if content.lower() == "no clothing detected":
        return "no clothing detected"

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        items = json.loads(content)
        if isinstance(items, list):
            return items
        # Model may have returned {"items": [...]} or similar
        if isinstance(items, dict):
            for v in items.values():
                if isinstance(v, list):
                    return v
    except json.JSONDecodeError:
        pass

    # Fall back to returning the raw text if parsing fails
    return content


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
