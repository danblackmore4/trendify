import type { OutfitPair } from "@/app/types/trends";

export default function OutfitPairings({ pairs }: { pairs: OutfitPair[] }) {
  if (pairs.length === 0) return null;

  return (
    <div className="mt-10 pt-8 border-t border-white/[0.06]">
      <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-zinc-600 mb-4">
        Worn Together
      </p>
      <div className="flex flex-wrap gap-3">
        {pairs.map((pair, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-[11px] text-zinc-400 border border-zinc-700 px-3 py-1 capitalize">
              {pair.garment_a}
            </span>
            <span className="text-zinc-600 text-xs font-light">+</span>
            <span className="text-[11px] text-zinc-400 border border-zinc-700 px-3 py-1 capitalize">
              {pair.garment_b}
            </span>
            {pair.count > 1 && (
              <span className="text-[10px] text-zinc-700 font-mono tabular-nums">
                ×{pair.count}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
