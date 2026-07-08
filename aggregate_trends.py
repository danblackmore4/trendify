# Reads clothing_results.json and produces a trends summary.
# For each garment type it builds a "trend card" with post count, unique influencer
# count, top colours, top fits, top style features, and example images ranked by engagement.

import json
import os
import re
from collections import defaultdict, Counter

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clothing_results.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trends_summary.json")

# Longer/hyphenated phrases are listed before shorter ones that contain them,
# so "wide-leg" is matched before "wide" and we don't accidentally double-count
KNOWN_FITS = [
    "wide-leg", "straight-leg", "slim-fit", "three-quarter", "full-length",
    "oversized", "cropped", "fitted", "relaxed", "tapered", "straight",
    "baggy", "boxy", "loose", "skinny", "flared", "longline", "slim",
    "mini", "midi", "maxi",
]

KNOWN_FEATURES = [
    "high-waisted", "off-shoulder", "square neck", "crew neck", "boat neck",
    "puff sleeve", "tie-front", "button-down", "mock neck", "scoop neck",
    "v-neck", "ribbed", "pleated", "distressed", "tie-dye", "broderie",
    "high-low", "wrap", "belted", "ruched", "gathered", "smocked",
    "linen", "knit", "cotton", "satin", "silk", "velvet", "leather",
    "denim", "mesh", "crochet", "sheer", "sequin", "embroidered",
    "striped", "checked", "plaid", "floral", "printed", "colourblock",
    "cargo", "fringe", "cutout", "asymmetric", "strapless", "halter",
    "turtleneck", "collared", "ruffled",
]

# Sort longest first so multi-word phrases are checked before their component words
KNOWN_FITS = sorted(KNOWN_FITS, key=len, reverse=True)
KNOWN_FEATURES = sorted(KNOWN_FEATURES, key=len, reverse=True)


def engagement_score(likes, comments, reposts, followers) -> float | None:
    # Weighted formula that accounts for Instagram hiding like counts (-1 means hidden).
    # Comments and reposts are weighted higher because they represent stronger intent
    # than a passive like. Returns None if we don't have follower data to normalise against.
    if not followers:
        return None
    l = max(likes or 0, 0)  # treat -1 (hidden likes) as 0
    c = comments or 0
    r = reposts or 0
    return round((l + c * 3 + r * 5) / followers * 100, 4)


def counter_to_ranked(counter: Counter, limit: int) -> list[dict]:
    return [{"value": v, "count": c} for v, c in counter.most_common(limit)]


def extract_terms(text: str, terms: list[str]) -> list[str]:
    # Use regex rather than plain "in" so we don't match substrings accidentally,
    # e.g. "slim" inside "slim-fit" being counted separately
    found = []
    for term in terms:
        if re.search(re.escape(term), text, re.IGNORECASE):
            found.append(term)
    return found


def collect_post_items(post: dict) -> dict[str, tuple[dict, dict]]:
    # Returns one item per garment type for this post — if the same garment
    # appears in multiple carousel images we only count it once per post
    seen: dict[str, tuple[dict, dict]] = {}
    for image in post.get("images", []):
        clothing = image.get("clothing", [])
        if not isinstance(clothing, list):
            continue
        for item in clothing:
            if not isinstance(item, dict):
                continue
            garment_type = (item.get("garment_type") or "").strip().lower()
            if garment_type and garment_type not in seen:
                # Keep a reference to the image too so we can read engagement metrics later
                seen[garment_type] = (item, image)
    return seen


def build_trends(posts: list[dict]) -> tuple[dict, list[dict]]:
    type_counts: Counter = Counter()
    type_influencers: dict[str, set] = defaultdict(set)
    type_colours: dict[str, Counter] = defaultdict(Counter)
    type_fits: dict[str, Counter] = defaultdict(Counter)
    type_features: dict[str, Counter] = defaultdict(Counter)
    type_examples: dict[str, list] = defaultdict(list)

    total_items = 0

    for post in posts:
        username = (post.get("username") or "unknown").strip().lower()

        for garment_type, (item, image) in collect_post_items(post).items():
            colour = (item.get("colour") or "").strip().lower()
            style_details = (item.get("style_details") or "").strip()

            likes_count = image.get("likes_count")
            comments_count = image.get("comments_count")
            reposts_count = image.get("reposts_count")
            follower_count = image.get("follower_count")
            image_url = image.get("image_url", "")

            total_items += 1
            type_counts[garment_type] += 1
            type_influencers[garment_type].add(username)

            if colour:
                type_colours[garment_type][colour] += 1

            # Pull fits and features out of the free-text style_details field
            for fit in extract_terms(style_details, KNOWN_FITS):
                type_fits[garment_type][fit] += 1

            for feature in extract_terms(style_details, KNOWN_FEATURES):
                type_features[garment_type][feature] += 1

            score = engagement_score(likes_count, comments_count, reposts_count, follower_count)
            if score is not None:
                type_examples[garment_type].append({
                    "image_url": image_url,
                    "username": username,
                    "likes_count": likes_count,
                    "comments_count": comments_count,
                    "reposts_count": reposts_count,
                    "follower_count": follower_count,
                    "engagement_score": score,
                    # Internal fields used for example selection — stripped before writing to summary
                    "_is_good_example": image.get("is_good_example", True),
                    "_confidence": item.get("confidence", 1.0),
                })

    garment_list = []
    for garment_type, count in type_counts.most_common():
        all_candidates = sorted(
            type_examples[garment_type],
            key=lambda x: x["engagement_score"],
            reverse=True,
        )
        # Prefer images that are good examples (clear personal outfit photo) with high
        # classification confidence. Fall back to all candidates if none qualify.
        good_candidates = [
            e for e in all_candidates
            if e.get("_is_good_example", True) and e.get("_confidence", 1.0) > 0.7
        ]
        examples = (good_candidates if good_candidates else all_candidates)[:3]
        # Strip the internal selection fields before writing to the summary
        for e in examples:
            e.pop("_is_good_example", None)
            e.pop("_confidence", None)

        garment_list.append({
            "garment_type": garment_type,
            "post_count": count,
            "unique_influencer_count": len(type_influencers[garment_type]),
            "top_colours": counter_to_ranked(type_colours[garment_type], 3),
            "top_fits": counter_to_ranked(type_fits[garment_type], 2),
            "top_style_features": counter_to_ranked(type_features[garment_type], 2),
            "example_images": examples,
        })

    summary = {
        "total_posts_analysed": len(posts),
        "total_items_analysed": total_items,
        "garment_types": garment_list,
    }

    top_10 = [
        {"garment_type": g["garment_type"], "post_count": g["post_count"]}
        for g in garment_list[:10]
    ]

    return summary, top_10


def print_terminal_summary(top_10: list[dict], total_items: int) -> None:
    print("\n" + "=" * 52)
    print("  TRENDIFY — TOP 10 ITEMS ACROSS ALL POSTS")
    print("=" * 52)
    for rank, item in enumerate(top_10, start=1):
        pct = (item["post_count"] / total_items * 100) if total_items else 0
        bar = "█" * min(int(pct * 1.5), 30)
        print(f"  {rank:>2}. {item['garment_type'].title():<32} {item['post_count']:>4}x  {pct:.1f}%  {bar}")
    print("=" * 52)
    print(f"  Total items analysed: {total_items}")
    print("=" * 52 + "\n")


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    print(f"Loaded {len(posts)} posts from {INPUT_FILE}")

    summary, top_10 = build_trends(posts)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"Trends summary written to {OUTPUT_FILE}")
    print_terminal_summary(top_10, summary["total_items_analysed"])


if __name__ == "__main__":
    main()
