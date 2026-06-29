import json
import re
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from identify_clothing import identify_clothing

load_dotenv()

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apify_export.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clothing_results.json")
MAX_WORKERS = 10


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
    images = [img for img in (post.get("images") or []) if isinstance(img, str) and img]
    if images:
        return images
    display_url = post.get("displayUrl")
    if display_url:
        return [display_url]
    return []


def process_image(url: str) -> dict:
    """Process a single image URL. Always returns a dict, never raises."""
    try:
        result = identify_clothing(url)
        if result == "no clothing detected":
            return {"image_url": url, "clothing": []}
        return {"image_url": url, "clothing": result}
    except Exception as e:
        return {"image_url": url, "clothing": [], "error": str(e)}


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    print(f"Loaded {len(posts)} posts from {INPUT_FILE}")

    # Separate videos and build a flat work list of (image_url, post_metadata)
    # so every image is an independent unit of work for the thread pool.
    skipped = 0
    work_items = []  # list of (image_url, post_index, image_index)
    post_results = {}  # keyed by post index, filled as futures complete

    for i, post in enumerate(posts):
        if (post.get("type") or "").lower() == "video":
            skipped += 1
            continue

        image_urls = extract_image_urls(post)
        if not image_urls:
            continue

        post_results[i] = {
            "username": extract_username(post),
            "post_url": post.get("url") or post.get("shortCode", ""),
            "timestamp": post.get("timestamp") or post.get("taken_at_timestamp") or "",
            "images": [None] * len(image_urls),
        }
        for j, url in enumerate(image_urls):
            work_items.append((i, j, url))

    total_images = len(work_items)
    print(f"Queuing {total_images} images from {len(post_results)} posts "
          f"({skipped} videos skipped) across {MAX_WORKERS} workers\n")

    counter_lock = threading.Lock()
    processed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_item = {
            executor.submit(process_image, url): (post_idx, img_idx)
            for post_idx, img_idx, url in work_items
        }

        for future in as_completed(future_to_item):
            post_idx, img_idx = future_to_item[future]
            image_result = future.result()  # process_image never raises

            if "error" in image_result:
                print(f"  Error on {image_result['image_url']}: {image_result['error']}")

            post_results[post_idx]["images"][img_idx] = image_result

            with counter_lock:
                processed += 1
                print(f"Processed {processed}/{total_images} images", end="\r", flush=True)

    print(f"\nAll images processed.")

    # Serialise back into original post order, dropping posts with no images
    ordered_results = [
        post_results[i]
        for i in sorted(post_results)
        if any(img is not None for img in post_results[i]["images"])
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(ordered_results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to {OUTPUT_FILE}")
    print(f"Done. {len(ordered_results)} posts written, {skipped} videos skipped.")


if __name__ == "__main__":
    main()
