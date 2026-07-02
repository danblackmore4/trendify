import json
import os
import re
import mimetypes
import urllib.request
import urllib.error

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trends_summary.json")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def slugify(text: str) -> str:
    """Convert a garment type or username into a safe filename segment."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)   # remove anything not word/space/hyphen
    text = re.sub(r"[\s]+", "_", text)      # spaces to underscores
    text = re.sub(r"-+", "-", text)         # collapse multiple hyphens
    return text


def build_filename(garment_type: str, username: str, index: int, ext: str) -> str:
    base = f"{slugify(garment_type)}__{slugify(username)}"
    suffix = f"_{index}" if index > 0 else ""
    return f"{base}{suffix}{ext}"


def download_image(url: str, dest_path: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        content_type = response.headers.get_content_type()
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        if ext in (".jpe", ".jpeg"):
            ext = ".jpg"
        # Re-derive final path with correct extension if the caller used a placeholder
        final_path = os.path.splitext(dest_path)[0] + ext
        if os.path.exists(final_path):
            return final_path, True   # already exists
        with open(final_path, "wb") as f:
            f.write(response.read())
    return final_path, False          # freshly downloaded


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        summary = json.load(f)

    os.makedirs(IMAGES_DIR, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    all_garment_types = summary.get("garment_types", [])
    garment_types = sorted(all_garment_types, key=lambda g: g.get("post_count", 0), reverse=True)[:10]
    total_examples = sum(len(g.get("example_images", [])) for g in garment_types)
    print(f"Processing top {len(garment_types)} garment types by post count, {total_examples} example images total\n")

    for garment in garment_types:
        garment_type = garment.get("garment_type", "unknown")
        examples = garment.get("example_images", [])

        # Track how many times we've seen each garment+username combo to avoid collisions
        seen_combos: dict[str, int] = {}

        for example in examples:
            url = example.get("image_url", "")
            username = example.get("username", "unknown")

            if not url:
                continue

            combo_key = f"{slugify(garment_type)}__{slugify(username)}"
            index = seen_combos.get(combo_key, 0)
            seen_combos[combo_key] = index + 1

            # Use .jpg as placeholder; download_image corrects extension from Content-Type
            dest_path = os.path.join(IMAGES_DIR, build_filename(garment_type, username, index, ".jpg"))

            # Fast existence check using the placeholder name (catches most cases)
            if os.path.exists(dest_path):
                print(f"  [skip]  {os.path.basename(dest_path)}")
                skipped += 1
                continue

            try:
                final_path, was_existing = download_image(url, dest_path)
                if was_existing:
                    print(f"  [skip]  {os.path.basename(final_path)}")
                    skipped += 1
                else:
                    print(f"  [ok]    {os.path.basename(final_path)}")
                    downloaded += 1
            except urllib.error.HTTPError as e:
                print(f"  [fail]  garment='{garment_type}' user='{username}' — HTTP {e.code} (URL likely expired)")
                failed += 1
            except Exception as e:
                print(f"  [fail]  garment='{garment_type}' user='{username}' — {e}")
                failed += 1

    print(f"\n{'=' * 40}")
    print(f"  Downloaded : {downloaded}")
    print(f"  Skipped    : {skipped}")
    print(f"  Failed     : {failed}")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
