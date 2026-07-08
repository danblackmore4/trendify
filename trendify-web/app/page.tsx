import fs from "fs";
import path from "path";
import { colorToHex } from "@/app/lib/colors";
import { groupByCategory } from "@/app/lib/categories";
import type {
  GarmentTrend,
  TrendsSummary,
  VelocityData,
  WeeklyColour,
  OutfitPair,
} from "@/app/types/trends";
import ColourStory from "@/app/components/ColourStory";
import TrendView from "@/app/components/TrendView";

// ---------------------------------------------------------------------------
// Raw types for clothing_results.json
// ---------------------------------------------------------------------------

interface ClothingItem {
  garment_type: string;
  colour: string;
  season: string;
}

interface ClothingImage {
  clothing: ClothingItem[];
}

interface ClothingPost {
  week: string | null;
  images: ClothingImage[];
}

// ---------------------------------------------------------------------------
// Data loaders
// ---------------------------------------------------------------------------

function loadTrends(): TrendsSummary | null {
  const filePath = path.join(process.cwd(), "..", "trends_summary.json");
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as TrendsSummary;
  } catch {
    return null;
  }
}

function loadClothingResults(): ClothingPost[] {
  const filePath = path.join(process.cwd(), "..", "clothing_results.json");
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as ClothingPost[];
  } catch {
    return [];
  }
}

function loadOutfitPairs(): OutfitPair[] {
  const filePath = path.join(process.cwd(), "..", "outfit_combinations.json");
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as OutfitPair[];
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Derived data computations
// ---------------------------------------------------------------------------

function computeVelocityMap(posts: ClothingPost[]): Record<string, VelocityData> {
  // Count distinct posts per garment type per week.
  // A post "features" a garment type if any image contains it.
  const weekCounts = new Map<string, Map<string, number>>();

  for (const post of posts) {
    if (!post.week) continue;
    if (!weekCounts.has(post.week)) weekCounts.set(post.week, new Map());
    const wc = weekCounts.get(post.week)!;

    const typesInPost = new Set<string>();
    for (const img of post.images ?? []) {
      for (const item of img.clothing ?? []) {
        if (!item.garment_type) continue;
        typesInPost.add(item.garment_type.toLowerCase().trim());
      }
    }
    for (const t of typesInPost) {
      wc.set(t, (wc.get(t) ?? 0) + 1);
    }
  }

  const weeks = [...weekCounts.keys()].sort();
  if (weeks.length < 2) return {};

  const thisWeekKey = weeks[weeks.length - 1];
  const lastWeekKey = weeks[weeks.length - 2];
  const thisMap = weekCounts.get(thisWeekKey)!;
  const lastMap = weekCounts.get(lastWeekKey)!;

  const allTypes = new Set([...thisMap.keys(), ...lastMap.keys()]);
  const velocityMap: Record<string, VelocityData> = {};

  for (const type of allTypes) {
    const thisCount = thisMap.get(type) ?? 0;
    const lastCount = lastMap.get(type) ?? 0;

    let direction: VelocityData["direction"];
    let pct: number;

    if (lastCount === 0) {
      direction = "new";
      pct = 100;
    } else {
      const change = (thisCount - lastCount) / lastCount;
      pct = Math.round(Math.abs(change) * 100);
      direction = change > 0.02 ? "up" : change < -0.02 ? "down" : "flat";
    }

    velocityMap[type] = { direction, pct, thisWeek: thisCount, lastWeek: lastCount };
  }

  return velocityMap;
}

function computeSeasonMap(posts: ClothingPost[]): Record<string, string> {
  // For each garment type, pick the most common season across all posts.
  const votes = new Map<string, Map<string, number>>();

  for (const post of posts) {
    for (const img of post.images ?? []) {
      for (const item of img.clothing ?? []) {
        if (!item.garment_type) continue;
        const type = item.garment_type.toLowerCase().trim();
        const season = item.season?.toLowerCase().trim() || "all-season";
        if (!votes.has(type)) votes.set(type, new Map());
        const sv = votes.get(type)!;
        sv.set(season, (sv.get(season) ?? 0) + 1);
      }
    }
  }

  const seasonMap: Record<string, string> = {};
  for (const [type, sv] of votes) {
    let bestSeason = "all-season";
    let bestCount = 0;
    for (const [season, count] of sv) {
      if (count > bestCount) {
        bestCount = count;
        bestSeason = season;
      }
    }
    seasonMap[type] = bestSeason;
  }
  return seasonMap;
}

function computeWeeklyColours(posts: ClothingPost[]): WeeklyColour[] {
  const weeks = [
    ...new Set(
      posts.map((p) => p.week).filter((w): w is string => !!w)
    ),
  ].sort();
  if (weeks.length === 0) return [];

  const latest = weeks[weeks.length - 1];
  const counts = new Map<string, number>();

  for (const post of posts) {
    if (post.week !== latest) continue;
    for (const img of post.images ?? []) {
      for (const item of img.clothing ?? []) {
        const colour = item.colour?.toLowerCase().trim();
        if (!colour) continue;
        counts.set(colour, (counts.get(colour) ?? 0) + 1);
      }
    }
  }

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([colour, count]) => ({ colour, count, hex: colorToHex(colour) }));
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  const data = loadTrends();
  const clothingPosts = loadClothingResults();
  const outfitPairs = loadOutfitPairs();

  const sections: Array<{ category: string; trends: GarmentTrend[] }> = data
    ? groupByCategory(data.garment_types)
    : [];

  const velocityMap = computeVelocityMap(clothingPosts);
  const seasonMap = computeSeasonMap(clothingPosts);
  const weeklyColours = computeWeeklyColours(clothingPosts);

  return (
    <div className="min-h-screen px-6 py-12 md:px-12 lg:px-16">

      {/* Header */}
      <header className="mb-14">
        <div className="flex items-baseline gap-3 mb-3">
          <h1 className="font-serif text-5xl md:text-6xl font-semibold tracking-tight text-[#f0ece6]">
            Trendify
          </h1>
          <span className="hidden sm:block text-zinc-600 text-sm font-mono tracking-widest uppercase self-end pb-1">
            Fashion Intelligence
          </span>
        </div>

        {data ? (
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-zinc-500 font-mono">
            <span>
              <span className="text-zinc-300 font-semibold tabular-nums">
                {data.total_posts_analysed}
              </span>{" "}
              posts analysed
            </span>
            <span className="text-zinc-700">·</span>
            <span>
              <span className="text-zinc-300 font-semibold tabular-nums">
                {data.total_items_analysed}
              </span>{" "}
              items identified
            </span>
            <span className="text-zinc-700">·</span>
            <span>
              <span className="text-zinc-300 font-semibold tabular-nums">
                {data.garment_types.length}
              </span>{" "}
              garment types
            </span>
          </div>
        ) : (
          <p className="text-zinc-600 text-sm font-mono">
            Run{" "}
            <code className="text-zinc-400">python aggregate_trends.py</code> to
            generate trend data.
          </p>
        )}

        <div className="h-px bg-white/[0.08] mt-8" />
      </header>

      {data ? (
        <main>
          {/* Colour Story */}
          <ColourStory colours={weeklyColours} />

          {/* Category sections + season filter */}
          <TrendView
            sections={sections}
            velocityMap={velocityMap}
            seasonMap={seasonMap}
            outfitPairs={outfitPairs}
          />
        </main>
      ) : (
        <main className="flex flex-col items-center justify-center py-32 text-center">
          <p className="font-serif text-3xl text-zinc-600 mb-4">No data yet</p>
          <p className="text-zinc-700 text-sm font-mono">
            Run the pipeline to populate trend data.
          </p>
        </main>
      )}

      {/* Footer */}
      <footer className="mt-20 pt-8 border-t border-white/[0.06] flex flex-wrap gap-6 justify-between items-center">
        <span className="font-serif text-zinc-700 text-sm tracking-wide">
          Trendify
        </span>
        {data && (
          <span className="text-zinc-700 text-xs font-mono">
            {data.garment_types.length} trends · {data.total_posts_analysed}{" "}
            posts
          </span>
        )}
      </footer>

    </div>
  );
}
