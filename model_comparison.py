# Runs the same 20 test images through both gpt-4o and gpt-4o-mini side by side,
# recording response time and token counts for each call. Results are written to
# model_comparison.json and a summary is printed to the terminal.
#
# Usage:
#   1. Put up to 20 image URLs or local file paths in test_images.txt (one per line).
#   2. Run: python model_comparison.py

import os
import sys
import json
import time
import urllib.error
from dotenv import load_dotenv
from identify_clothing import classify_with_model

load_dotenv()

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images.txt")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_comparison.json")

MAX_IMAGES = 20
RETRY_DELAYS = [5, 10, 20]

# Pricing per 1 million tokens (as of mid-2024 OpenAI pricing)
PRICING = {
    "gpt-4o": {
        "input_per_million": 2.50,
        "output_per_million": 10.00,
    },
    "gpt-4o-mini": {
        "input_per_million": 0.15,
        "output_per_million": 0.60,
    },
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING[model]
    return (
        input_tokens / 1_000_000 * p["input_per_million"]
        + output_tokens / 1_000_000 * p["output_per_million"]
    )


def call_with_retry(image_source: str, model: str) -> tuple:
    # Same retry pattern as process_apify_export.py — backs off on 429 rate limit errors
    last_exc = None
    for attempt, delay in enumerate([0] + RETRY_DELAYS):
        if delay:
            print(f"    Rate limited — waiting {delay}s (retry {attempt}/{len(RETRY_DELAYS)})...")
            time.sleep(delay)
        try:
            return classify_with_model(image_source, model)
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


def run_one_image(image_source: str, index: int, total: int) -> dict:
    entry = {"image": image_source}

    for model, key in [("gpt-4o", "gpt4o"), ("gpt-4o-mini", "gpt4o_mini")]:
        print(f"  [{index}/{total}] {key} ...", end=" ", flush=True)
        try:
            result, input_tok, output_tok, elapsed = call_with_retry(image_source, model)
            cost = compute_cost(model, input_tok, output_tok)
            entry[key] = {
                "result": result,
                "time_seconds": round(elapsed, 3),
                "input_tokens": input_tok,
                "output_tokens": output_tok,
                "cost_usd": round(cost, 6),
            }
            print(f"{elapsed:.1f}s  {input_tok}in/{output_tok}out  ${cost:.5f}")
        except Exception as e:
            entry[key] = {"error": str(e)}
            print(f"ERROR — {e}")

    return entry


def print_summary(results: list[dict]) -> None:
    print("\n" + "=" * 64)
    print("  MODEL COMPARISON SUMMARY")
    print("=" * 64)

    for model, key in [("gpt-4o", "gpt4o"), ("gpt-4o-mini", "gpt4o_mini")]:
        times = []
        total_input = 0
        total_output = 0
        total_cost = 0.0
        errors = 0

        for entry in results:
            model_data = entry.get(key, {})
            if "error" in model_data:
                errors += 1
                continue
            times.append(model_data.get("time_seconds", 0))
            total_input += model_data.get("input_tokens", 0)
            total_output += model_data.get("output_tokens", 0)
            total_cost += model_data.get("cost_usd", 0)

        successful = len(times)
        avg_time = sum(times) / successful if successful else 0

        print(f"\n  {model}")
        print(f"    Images processed : {successful}/{len(results)}" + (f"  ({errors} errors)" if errors else ""))
        print(f"    Avg response time: {avg_time:.2f}s")
        print(f"    Total tokens     : {total_input} input / {total_output} output")
        print(f"    Total cost       : ${total_cost:.4f}")
        # Project to the full 20-image run in case some images errored
        if successful and successful < MAX_IMAGES:
            projected = total_cost / successful * MAX_IMAGES
            print(f"    Projected (20)   : ${projected:.4f}")

    print("=" * 64 + "\n")


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found.")
        print("Create it with one image URL or local file path per line (up to 20 lines).")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    images = lines[:MAX_IMAGES]
    if not images:
        print(f"ERROR: {INPUT_FILE} is empty.")
        sys.exit(1)

    print(f"Loaded {len(images)} image(s) from {INPUT_FILE}")
    print(f"Running each through gpt-4o and gpt-4o-mini...\n")

    results = []
    for i, image_source in enumerate(images, start=1):
        entry = run_one_image(image_source, i, len(images))
        results.append(entry)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {OUTPUT_FILE}")
    print_summary(results)


if __name__ == "__main__":
    main()
