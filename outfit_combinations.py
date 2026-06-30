import json
import os
from collections import Counter
from itertools import combinations

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clothing_results.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outfit_combinations.json")


def get_outfit_garments(post: dict) -> list[str]:
    """Return the deduplicated garment list for a post.
    Uses the pre-built outfit_combination field if present, otherwise
    falls back to collecting garment_types from images directly.
    """
    if "outfit_combination" in post:
        return post["outfit_combination"]

    seen = set()
    for image in post.get("images", []):
        clothing = image.get("clothing", [])
        if not isinstance(clothing, list):
            continue
        for item in clothing:
            if isinstance(item, dict):
                gt = (item.get("garment_type") or "").strip().lower()
                if gt:
                    seen.add(gt)
    return sorted(seen)


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    print(f"Loaded {len(posts)} posts from {INPUT_FILE}")

    pair_counts: Counter = Counter()
    posts_with_pairs = 0

    for post in posts:
        garments = get_outfit_garments(post)
        pairs = list(combinations(sorted(garments), 2))
        if pairs:
            posts_with_pairs += 1
            for pair in pairs:
                pair_counts[pair] += 1

    print(f"Found co-occurrence pairs across {posts_with_pairs} posts")

    top_15 = [
        {
            "garment_a": pair[0],
            "garment_b": pair[1],
            "count": count,
        }
        for pair, count in pair_counts.most_common(15)
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(top_15, f, indent=2, ensure_ascii=False)

    print(f"Top 15 pairs saved to {OUTPUT_FILE}")

    print("\n" + "=" * 58)
    print("  TOP 10 OUTFIT COMBINATIONS")
    print("=" * 58)
    for rank, entry in enumerate(top_15[:10], start=1):
        bar = "█" * min(entry["count"], 30)
        print(f"  {rank:>2}. {entry['garment_a'].title()} + {entry['garment_b'].title():<28} {entry['count']:>3}x  {bar}")
    print("=" * 58 + "\n")


if __name__ == "__main__":
    main()
