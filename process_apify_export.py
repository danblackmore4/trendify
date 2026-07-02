# Takes the raw JSON export from Apify's Instagram scraper and runs every image
# through a two-stage OpenAI pipeline: a cheap GPT-4o-mini pre-filter to skip
# non-fashion images, then a full GPT-4o classification for the ones that pass.
# Results are written to clothing_results.json.

import json
import re
import os
import time
import base64
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from identify_clothing import identify_clothing, download_image

load_dotenv()

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apify_export.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clothing_results.json")
INFLUENCERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "influencers.json")

# 3 workers is the sweet spot — enough for parallelism without hammering the API
MAX_WORKERS = 3
RETRY_DELAYS = [5, 10, 20]  # seconds to wait before each successive retry on 429


def call_with_retry(fn, *args):
    # We hit 429s fairly often with concurrent workers, so retry with increasing
    # delays rather than failing immediately. identify_clothing() wraps its HTTP
    # errors as RuntimeErrors, so we check both the raw HTTPError and the message.
    last_exc = None
    for attempt, delay in enumerate([0] + RETRY_DELAYS):
        if delay:
            print(f"\n  Rate limited — waiting {delay}s (retry {attempt}/{len(RETRY_DELAYS)})...")
            time.sleep(delay)
        try:
            return fn(*args)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                last_exc = e
                continue
            raise
        except RuntimeError as e:
            if "429" in str(e):
                last_exc = e
                continue
            raise
    raise RuntimeError(f"Failed after {len(RETRY_DELAYS)} retries due to rate limiting") from last_exc


def parse_week(timestamp: str) -> str | None:
    # Converts an ISO 8601 timestamp to "YYYY-WW" format for weekly trend grouping.
    # Python's datetime.fromisoformat doesn't handle the trailing "Z" before 3.11,
    # so we replace it manually with the UTC offset.
    if not timestamp:
        return None
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        iso = dt.isocalendar()
        return f"{iso[0]}-{iso[1]:02d}"
    except ValueError:
        return None


def extract_username(post: dict) -> str:
    # Try the most common field names first, then fall back to parsing the post URL
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
    # Carousel posts have an "images" array; single-image posts only have "displayUrl"
    images = [img for img in (post.get("images") or []) if isinstance(img, str) and img]
    if images:
        return images
    display_url = post.get("displayUrl")
    if display_url:
        return [display_url]
    return []


def is_fashion_image(url: str) -> bool:
    # Quick cheap check using GPT-4o-mini before spending money on the full classification.
    # max_tokens=5 is enough for "YES" or "NO" and keeps this call very cheap.
    api_key = os.environ.get("OPENAI_API_KEY")
    local_path, mime_type = download_image(url)
    with open(local_path, "rb") as f:
        b64_image = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Does this image show a person wearing an outfit suitable for fashion analysis? Reply with only YES or NO.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 5,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))

    answer = result["choices"][0]["message"]["content"].strip().upper()
    return answer.startswith("YES")


def process_image(url: str) -> dict:
    # This function is called concurrently by the thread pool — it must never raise,
    # otherwise the whole executor would stop. Errors are returned as dicts instead.
    try:
        if not call_with_retry(is_fashion_image, url):
            return {"image_url": url, "clothing": [], "filtered": True}
        result = call_with_retry(identify_clothing, url)
        if result == "no clothing detected":
            return {"image_url": url, "clothing": []}
        return {"image_url": url, "clothing": result}
    except Exception as e:
        return {"image_url": url, "clothing": [], "error": str(e)}
    finally:
        # Brief pause after every image regardless of outcome to avoid overwhelming the API
        time.sleep(1)


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    with open(INFLUENCERS_FILE, "r", encoding="utf-8") as f:
        influencers = json.load(f)

    print(f"Loaded {len(posts)} posts from {INPUT_FILE}")
    print(f"Loaded {len(influencers)} influencers from {INFLUENCERS_FILE}")

    skipped = 0
    work_items = []
    post_results = {}

    for i, post in enumerate(posts):
        if (post.get("type") or "").lower() == "video":
            skipped += 1
            continue

        image_urls = extract_image_urls(post)
        if not image_urls:
            continue

        username = extract_username(post)
        raw_ts = post.get("timestamp") or post.get("taken_at_timestamp") or ""
        week = parse_week(raw_ts)
        post_results[i] = {
            "username": username,
            "follower_count": influencers.get(username.lower()),
            "likes_count": post.get("likesCount"),
            "comments_count": post.get("commentsCount"),
            # Apify doesn't export a reposts/shares count, so this will always be 0
            "reposts_count": 0,
            "post_url": post.get("url") or post.get("shortCode", ""),
            "timestamp": raw_ts,
            "week": week,
            # Pre-allocate slots so results land in the right position regardless of completion order
            "images": [None] * len(image_urls),
        }
        for j, url in enumerate(image_urls):
            work_items.append((i, j, url))

    total_images = len(work_items)
    print(f"Queuing {total_images} images from {len(post_results)} posts "
          f"({skipped} videos skipped) across {MAX_WORKERS} workers\n")

    counter_lock = threading.Lock()
    counts = {"done": 0, "classified": 0, "filtered": 0, "errors": 0}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_item = {
            executor.submit(process_image, url): (post_idx, img_idx)
            for post_idx, img_idx, url in work_items
        }

        for future in as_completed(future_to_item):
            post_idx, img_idx = future_to_item[future]
            image_result = future.result()

            if "error" in image_result:
                print(f"\n  Error — {image_result['image_url']}: {image_result['error']}")

            # Stamp post-level engagement fields onto the image so each image record
            # is self-contained and doesn't need to be joined back to the post later
            post = post_results[post_idx]
            image_result["likes_count"] = post["likes_count"]
            image_result["comments_count"] = post["comments_count"]
            image_result["reposts_count"] = post["reposts_count"]
            image_result["follower_count"] = post["follower_count"]
            post_results[post_idx]["images"][img_idx] = image_result

            with counter_lock:
                counts["done"] += 1
                if image_result.get("filtered"):
                    counts["filtered"] += 1
                elif "error" in image_result:
                    counts["errors"] += 1
                else:
                    counts["classified"] += 1
                print(
                    f"Processed {counts['done']}/{total_images} images  "
                    f"({counts['classified']} classified, "
                    f"{counts['filtered']} filtered out, "
                    f"{counts['errors']} errors)",
                    end="\r", flush=True,
                )

    print(f"\nAll images processed.")

    # Build outfit_combination after all images are done — it needs the full picture
    # of what was worn across every slide in a carousel post
    for post in post_results.values():
        seen = set()
        for image in post["images"]:
            if not image or not isinstance(image.get("clothing"), list):
                continue
            for item in image["clothing"]:
                if isinstance(item, dict):
                    gt = (item.get("garment_type") or "").strip().lower()
                    if gt:
                        seen.add(gt)
        post["outfit_combination"] = sorted(seen)

    # Sort back into original post order before writing — futures complete out of order
    ordered_results = [
        post_results[i]
        for i in sorted(post_results)
        if any(img is not None for img in post_results[i]["images"])
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(ordered_results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to {OUTPUT_FILE}")
    print(
        f"Done. {len(ordered_results)} posts written, {skipped} videos skipped.\n"
        f"  Images classified : {counts['classified']}\n"
        f"  Images filtered out: {counts['filtered']}\n"
        f"  Errors             : {counts['errors']}"
    )


if __name__ == "__main__":
    main()
