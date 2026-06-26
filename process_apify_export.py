import json
import time
import re
import os
from dotenv import load_dotenv
from identify_clothing import identify_clothing

load_dotenv()

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apify_export.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clothing_results.json")
DELAY_SECONDS = 1.5


def extract_username(post: dict) -> str:
    username = (
        post.get("ownerUsername")
        or post.get("username")
        or post.get("ownerId")
    )
    if not username:
        url = post.get("url") or post.get("shortCode", "")
        match = re.search(r"instagram\.com/([^/]+)/", url)
        if match:
            username = match.group(1)
    return username or "unknown"


def extract_image_urls(post: dict) -> list[str]:
    # images is a flat list of URL strings in this export
    images = [img for img in (post.get("images") or []) if isinstance(img, str) and img]
    if images:
        return images

    # Single-image posts only have displayUrl
    display_url = post.get("displayUrl")
    if display_url:
        return [display_url]

    return []


def process_post(post: dict) -> dict | None:
    if (post.get("type") or "").lower() == "video":
        return None

    image_urls = extract_image_urls(post)
    if not image_urls:
        return None

    username = extract_username(post)
    post_url = post.get("url") or post.get("shortCode", "")
    timestamp = post.get("timestamp") or post.get("taken_at_timestamp") or ""

    clothing_items = []
    for i, url in enumerate(image_urls):
        if i > 0:
            time.sleep(DELAY_SECONDS)
        try:
            result = identify_clothing(url)
            if result == "no clothing detected":
                clothing_items.append({"image_url": url, "clothing": []})
            else:
                clothing_items.append({"image_url": url, "clothing": result})
        except Exception as e:
            print(f"  Warning: failed to process image {url}: {e}")
            clothing_items.append({"image_url": url, "error": str(e)})

    return {
        "username": username,
        "post_url": post_url,
        "timestamp": timestamp,
        "images": clothing_items,
    }


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    print(f"Loaded {len(posts)} posts from {INPUT_FILE}")

    results = []
    skipped = 0

    for i, post in enumerate(posts):
        post_url = post.get("url") or post.get("shortCode") or f"post #{i+1}"

        if (post.get("type") or "").lower() == "video":
            print(f"[{i+1}/{len(posts)}] Skipping video: {post_url}")
            skipped += 1
            continue

        print(f"[{i+1}/{len(posts)}] Processing: {post_url}")
        result = process_post(post)
        if result:
            results.append(result)

        if i < len(posts) - 1:
            time.sleep(DELAY_SECONDS)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(results)} posts processed, {skipped} skipped.")
    print(f"Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
