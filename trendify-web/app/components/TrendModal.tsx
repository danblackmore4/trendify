"use client";

import { useEffect } from "react";
import { colorToHex } from "@/app/lib/colors";
import type { GarmentTrend, VelocityData, OutfitPair } from "@/app/types/trends";
import ExampleImages from "./ExampleImages";

interface TrendModalProps {
  trend: GarmentTrend;
  velocity?: VelocityData;
  season?: string;
  wornWith: OutfitPair[];
  onClose: () => void;
}

const SEASON_STYLES: Record<string, { label: string; className: string }> = {
  "warm-weather": {
    label: "Warm Weather",
    className: "text-amber-400 border-amber-400/30 bg-amber-400/[0.08]",
  },
  "cold-weather": {
    label: "Cold Weather",
    className: "text-sky-400 border-sky-400/30 bg-sky-400/[0.08]",
  },
  "all-season": {
    label: "All Season",
    className: "text-zinc-400 border-zinc-700 bg-zinc-800/60",
  },
};

function CloseIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    >
      <path d="M1 1L13 13M13 1L1 13" />
    </svg>
  );
}

export default function TrendModal({
  trend,
  velocity,
  season,
  wornWith,
  onClose,
}: TrendModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  const seasonStyle =
    SEASON_STYLES[season ?? ""] ?? SEASON_STYLES["all-season"];

  const pairLabel = trend.garment_type.toLowerCase().trim();
  const pairedWith = wornWith.map((p) =>
    p.garment_a === pairLabel ? p.garment_b : p.garment_a
  );

  const hasColours = trend.top_colours.length > 0;
  const hasFits = trend.top_fits.length > 0;
  const hasFeatures = trend.top_style_features.length > 0;
  const hasImages = trend.example_images.length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8 bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl max-h-[92vh] flex flex-col md:flex-row bg-[#111111] border border-white/[0.1] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute top-4 right-4 z-20 w-7 h-7 flex items-center justify-center text-zinc-600 hover:text-zinc-200 border border-zinc-800 hover:border-zinc-600 bg-[#111111] transition-colors duration-150"
        >
          <CloseIcon />
        </button>

        {/* Left: image carousel */}
        {hasImages && (
          <div className="md:w-[42%] flex-shrink-0 md:self-stretch">
            <ExampleImages
              images={trend.example_images}
              containerClassName="relative h-64 md:h-full bg-zinc-900 group overflow-hidden"
            />
          </div>
        )}

        {/* Right: details */}
        <div className="flex-1 overflow-y-auto p-7 md:p-9">

          {/* Heading */}
          <h2 className="font-serif text-3xl md:text-4xl font-semibold uppercase tracking-wide text-[#f0ece6] leading-tight pr-8">
            {trend.garment_type}
          </h2>

          {/* Season badge */}
          {season && (
            <span
              className={`inline-block mt-3 text-xs font-mono uppercase tracking-[0.15em] border px-2.5 py-1 ${seasonStyle.className}`}
            >
              {seasonStyle.label}
            </span>
          )}

          <div className="h-px bg-white/10 my-5" />

          {/* Stats */}
          <div className="flex items-baseline gap-5 mb-7">
            <div>
              <span className="text-[#f0ece6] font-semibold tabular-nums text-2xl">
                {trend.post_count}
              </span>
              <span className="text-zinc-500 ml-1.5 text-sm">posts</span>
            </div>
            <div className="text-zinc-700 text-base">·</div>
            <div>
              <span className="text-[#f0ece6] font-semibold tabular-nums text-2xl">
                {trend.unique_influencer_count}
              </span>
              <span className="text-zinc-500 ml-1.5 text-sm">
                {trend.unique_influencer_count === 1
                  ? "influencer"
                  : "influencers"}
              </span>
            </div>
          </div>

          {/* Colours */}
          {hasColours && (
            <div className="mb-6">
              <p className="text-xs font-mono uppercase tracking-[0.15em] text-zinc-600 mb-3">
                Colour Breakdown
              </p>
              <div className="flex flex-col gap-2.5">
                {trend.top_colours.map((c) => (
                  <div key={c.value} className="flex items-center gap-3">
                    <span
                      className="w-3.5 h-3.5 rounded-full flex-shrink-0 border border-white/10"
                      style={{ backgroundColor: colorToHex(c.value) }}
                    />
                    <span className="text-base text-zinc-300 capitalize flex-1">
                      {c.value}
                    </span>
                    <span className="text-sm text-zinc-600 font-mono tabular-nums">
                      {c.count}×
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Fits */}
          {hasFits && (
            <div className="mb-6">
              <p className="text-xs font-mono uppercase tracking-[0.15em] text-zinc-600 mb-3">
                Fits
              </p>
              <div className="flex flex-wrap gap-2">
                {trend.top_fits.map((f) => (
                  <div key={f.value} className="flex items-center gap-1.5">
                    <span className="text-sm text-zinc-300 border border-zinc-700 px-2.5 py-1 capitalize">
                      {f.value}
                    </span>
                    <span className="text-xs text-zinc-600 font-mono tabular-nums">
                      {f.count}×
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Style features */}
          {hasFeatures && (
            <div className="mb-6">
              <p className="text-xs font-mono uppercase tracking-[0.15em] text-zinc-600 mb-3">
                Style Details
              </p>
              <div className="flex flex-wrap gap-2">
                {trend.top_style_features.map((f) => (
                  <div key={f.value} className="flex items-center gap-1.5">
                    <span className="text-sm text-zinc-300 border border-zinc-700 px-2.5 py-1 capitalize">
                      {f.value}
                    </span>
                    <span className="text-xs text-zinc-600 font-mono tabular-nums">
                      {f.count}×
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Worn with */}
          {pairedWith.length > 0 && (
            <div className="mb-6">
              <p className="text-xs font-mono uppercase tracking-[0.15em] text-zinc-600 mb-3">
                Worn With
              </p>
              <div className="flex flex-wrap gap-2">
                {pairedWith.map((item) => (
                  <span
                    key={item}
                    className="text-sm text-zinc-300 border border-zinc-600 px-3 py-1.5 capitalize"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Velocity */}
          {velocity && (
            <div className="pt-4 border-t border-white/[0.06]">
              <p className="text-xs font-mono uppercase tracking-[0.15em] text-zinc-600 mb-2">
                Week-on-Week
              </p>
              {velocity.direction === "new" ? (
                <p className="text-base font-mono text-zinc-400">
                  New this week — {velocity.thisWeek}{" "}
                  {velocity.thisWeek === 1 ? "post" : "posts"}
                </p>
              ) : velocity.direction === "flat" ? (
                <p className="text-base font-mono text-zinc-500">
                  Stable — {velocity.thisWeek}{" "}
                  {velocity.thisWeek === 1 ? "post" : "posts"} this week
                </p>
              ) : (
                <p
                  className={`text-base font-mono tabular-nums ${
                    velocity.direction === "up"
                      ? "text-emerald-500"
                      : "text-rose-400"
                  }`}
                >
                  {velocity.direction === "up" ? "↑" : "↓"} {velocity.pct}%
                  &nbsp;—&nbsp;
                  {velocity.lastWeek} → {velocity.thisWeek} posts
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
