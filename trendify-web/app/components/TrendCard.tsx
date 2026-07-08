import { colorToHex } from "@/app/lib/colors";
import type { GarmentTrend, VelocityData } from "@/app/types/trends";
import ExampleImages from "./ExampleImages";

function VelocityBadge({ velocity }: { velocity: VelocityData }) {
  if (velocity.direction === "new") {
    return (
      <span className="text-[10px] font-mono uppercase tracking-widest px-1.5 py-0.5 bg-zinc-800 text-zinc-400 border border-zinc-700">
        NEW
      </span>
    );
  }
  if (velocity.direction === "flat") {
    return (
      <span className="text-[11px] font-mono text-zinc-600">→ {velocity.pct}%</span>
    );
  }
  const isUp = velocity.direction === "up";
  return (
    <span
      className={`text-[11px] font-mono tabular-nums ${
        isUp ? "text-emerald-500" : "text-rose-500"
      }`}
    >
      {isUp ? "↑" : "↓"} {velocity.pct}%
    </span>
  );
}

interface TrendCardProps {
  trend: GarmentTrend;
  rank: number;
  velocity?: VelocityData;
}

export default function TrendCard({ trend, rank, velocity }: TrendCardProps) {
  const hasColours = trend.top_colours.length > 0;
  const hasFits = trend.top_fits.length > 0;
  const hasImages = trend.example_images.length > 0;

  return (
    <article className="flex flex-col bg-[#111111] border border-white/[0.07] hover:border-white/[0.15] transition-colors duration-300">
      <div className="flex flex-col flex-1 p-6">
        {/* Rank + name */}
        <div className="mb-4">
          <span className="text-zinc-600 text-xs font-mono tracking-widest tabular-nums">
            {String(rank).padStart(2, "0")}
          </span>
          <h2 className="font-serif text-2xl font-semibold tracking-wide uppercase mt-1 leading-tight text-[#f0ece6]">
            {trend.garment_type}
          </h2>
        </div>

        {/* Divider */}
        <div className="h-px bg-white/10 mb-4" />

        {/* Stats row */}
        <div className="flex items-center gap-4 text-sm mb-5 flex-wrap">
          <div>
            <span className="text-[#f0ece6] font-semibold tabular-nums">{trend.post_count}</span>
            <span className="text-zinc-500 ml-1">posts</span>
          </div>
          <div className="text-zinc-700">·</div>
          <div>
            <span className="text-[#f0ece6] font-semibold tabular-nums">{trend.unique_influencer_count}</span>
            <span className="text-zinc-500 ml-1">
              {trend.unique_influencer_count === 1 ? "influencer" : "influencers"}
            </span>
          </div>
          {velocity && (
            <>
              <div className="text-zinc-700">·</div>
              <VelocityBadge velocity={velocity} />
            </>
          )}
        </div>

        {/* Colours */}
        {hasColours && (
          <div className="mb-4">
            <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-zinc-600 mb-2">
              Colour
            </p>
            <div className="flex flex-col gap-1.5">
              {trend.top_colours.map((c) => (
                <div key={c.value} className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0 border border-white/10"
                    style={{ backgroundColor: colorToHex(c.value) }}
                  />
                  <span className="text-xs text-zinc-400 capitalize leading-none">{c.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Fits */}
        {hasFits && (
          <div className="mb-2">
            <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-zinc-600 mb-2">
              Fit
            </p>
            <div className="flex flex-wrap gap-1.5">
              {trend.top_fits.map((f) => (
                <span
                  key={f.value}
                  className="text-[11px] text-zinc-400 border border-zinc-700 px-2 py-0.5 capitalize"
                >
                  {f.value}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Example images pinned to bottom */}
      {hasImages && (
        <ExampleImages images={trend.example_images} />
      )}
    </article>
  );
}
