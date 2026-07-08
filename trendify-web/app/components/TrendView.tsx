"use client";

import { useState } from "react";
import { CATEGORY_SETS } from "@/app/lib/categories";
import TrendCard from "./TrendCard";
import OutfitPairings from "./OutfitPairings";
import type { GarmentTrend, VelocityData, OutfitPair } from "@/app/types/trends";

type SeasonFilter = "all" | "warm" | "cold";

interface TrendViewProps {
  sections: Array<{ category: string; trends: GarmentTrend[] }>;
  velocityMap: Record<string, VelocityData>;
  seasonMap: Record<string, string>;
  outfitPairs: OutfitPair[];
}

const FILTER_LABELS: Record<SeasonFilter, string> = {
  all: "All",
  warm: "Warm Weather",
  cold: "Cold Weather",
};

function getPairsForCategory(category: string, pairs: OutfitPair[]): OutfitPair[] {
  const members = CATEGORY_SETS[category];
  if (!members) return [];
  return pairs
    .filter((p) => members.has(p.garment_a) || members.has(p.garment_b))
    .slice(0, 5);
}

export default function TrendView({ sections, velocityMap, seasonMap, outfitPairs }: TrendViewProps) {
  const [filter, setFilter] = useState<SeasonFilter>("all");

  const filteredSections = sections
    .map(({ category, trends }) => ({
      category,
      trends: trends.filter((trend) => {
        if (filter === "all") return true;
        const season = seasonMap[trend.garment_type.toLowerCase().trim()] ?? "all-season";
        if (filter === "warm") return season === "warm-weather" || season === "all-season";
        return season === "cold-weather" || season === "all-season";
      }),
    }))
    .filter(({ trends }) => trends.length > 0);

  return (
    <div>
      {/* Season filter bar */}
      <div className="flex flex-wrap gap-2 mb-12">
        {(["all", "warm", "cold"] as SeasonFilter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 text-xs font-mono uppercase tracking-widest border transition-colors duration-200 ${
              filter === f
                ? "border-[#f0ece6] text-[#f0ece6] bg-white/[0.04]"
                : "border-zinc-800 text-zinc-600 hover:border-zinc-600 hover:text-zinc-400"
            }`}
          >
            {FILTER_LABELS[f]}
          </button>
        ))}
      </div>

      {/* Category sections */}
      {filteredSections.length > 0 ? (
        <div className="space-y-20">
          {filteredSections.map(({ category, trends }) => (
            <section key={category}>

              {/* Section heading */}
              <div className="flex items-center gap-6 mb-8">
                <h2 className="font-serif text-4xl font-semibold uppercase tracking-wide text-[#f0ece6] shrink-0">
                  {category}
                </h2>
                <div className="h-px bg-white/[0.08] flex-1" />
                <span className="text-[10px] font-mono text-zinc-600 shrink-0 tabular-nums">
                  {trends.length}{" "}
                  {trends.length === 1 ? "type" : "types"}
                </span>
              </div>

              {/* Cards grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-px bg-white/[0.04]">
                {trends.map((trend, i) => (
                  <TrendCard
                    key={trend.garment_type}
                    trend={trend}
                    rank={i + 1}
                    velocity={velocityMap[trend.garment_type.toLowerCase().trim()]}
                  />
                ))}
              </div>

              {/* Worn Together */}
              <OutfitPairings pairs={getPairsForCategory(category, outfitPairs)} />

            </section>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <p className="font-serif text-2xl text-zinc-600 mb-2">No trends match this filter</p>
          <p className="text-zinc-700 text-sm font-mono">Try selecting a different season.</p>
        </div>
      )}
    </div>
  );
}
