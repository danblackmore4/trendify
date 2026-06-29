import json
import os
from collections import defaultdict, Counter

INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clothing_results.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trends_summary.json")


def counter_to_ranked(counter: Counter, limit: int = 10) -> list[dict]:
    return [{"value": v, "count": c} for v, c in counter.most_common(limit)]


def collect_post_items(post: dict) -> dict[str, dict]:
    """Return one item per garment_type for this post (first occurrence across all images)."""
    seen: dict[str, dict] = {}
    for image in post.get("images", []):
        clothing = image.get("clothing", [])
        if not isinstance(clothing, list):
            continue
        for item in clothing:
            if not isinstance(item, dict):
                continue
            garment_type = (item.get("garment_type") or "").strip().lower()
            if garment_type and garment_type not in seen:
                seen[garment_type] = item
    return seen


def build_trends(posts: list[dict]) -> tuple[dict, list[dict]]:
    type_counts: Counter = Counter()
    type_colours: dict[str, Counter] = defaultdict(Counter)
    type_styles: dict[str, Counter] = defaultdict(Counter)

    total_items = 0

    for post in posts:
        # Deduplicate within this post before counting
        for garment_type, item in collect_post_items(post).items():
            colour = (item.get("colour") or "").strip().lower()
            style_details = (item.get("style_details") or "").strip().lower()

            total_items += 1
            type_counts[garment_type] += 1

            if colour:
                type_colours[garment_type][colour] += 1
            if style_details:
                type_styles[garment_type][style_details] += 1

    # All garment types land in a single uncategorised bucket since the data
    # has no category field — sorted by count descending
    garment_list = [
        {
            "garment_type": g,
            "count": count,
            "top_colours": counter_to_ranked(type_colours[g]),
            "top_styles": counter_to_ranked(type_styles[g]),
        }
        for g, count in type_counts.most_common()
    ]

    summary = {
        "total_posts_analysed": len(posts),
        "total_items_analysed": total_items,
        "garment_types": garment_list,
    }

    top_10 = [
        {"garment_type": g["garment_type"], "count": g["count"]}
        for g in garment_list[:10]
    ]

    return summary, top_10


def print_terminal_summary(top_10: list[dict], total_items: int) -> None:
    print("\n" + "=" * 52)
    print("  TRENDIFY — TOP 10 ITEMS ACROSS ALL POSTS")
    print("=" * 52)
    for rank, item in enumerate(top_10, start=1):
        pct = (item["count"] / total_items * 100) if total_items else 0
        bar = "█" * min(int(pct * 1.5), 30)
        print(f"  {rank:>2}. {item['garment_type'].title():<32} {item['count']:>4}x  {pct:.1f}%  {bar}")
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
