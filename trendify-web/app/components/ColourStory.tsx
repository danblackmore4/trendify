import type { WeeklyColour } from "@/app/types/trends";

export default function ColourStory({ colours }: { colours: WeeklyColour[] }) {
  if (colours.length === 0) return null;

  return (
    <section className="mb-16">
      <div className="flex items-center gap-6 mb-8">
        <h2 className="font-serif text-3xl font-semibold tracking-wide text-[#f0ece6] shrink-0">
          This Week&apos;s Colour Story
        </h2>
        <div className="h-px bg-white/[0.08] flex-1" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
        {colours.map((c) => (
          <div key={c.colour} className="flex flex-col">
            <div
              className="w-full aspect-square rounded-sm border border-white/[0.06]"
              style={{ backgroundColor: c.hex }}
            />
            <p className="text-base text-zinc-300 capitalize mt-3 leading-snug">{c.colour}</p>
            <p className="text-sm text-zinc-600 font-mono mt-0.5 tabular-nums">
              {c.count} {c.count === 1 ? "item" : "items"}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
