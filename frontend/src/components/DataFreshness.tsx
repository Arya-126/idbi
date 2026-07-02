import type { HealthCard } from "../types";

export default function DataFreshness({ card }: { card: HealthCard }) {
  const generated = new Date(card.generated_at);
  return (
    <section className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-ink-900">
          Data provenance & freshness
        </h3>
        <span className="text-[11px] text-ink-500">
          Card generated {generated.toLocaleString("en-IN")}
        </span>
      </div>
      <div className="grid gap-2 md:grid-cols-4 text-xs">
        {Object.entries(card.data_freshness).map(([src, iso]) => (
          <div
            key={src}
            className="rounded-lg border border-ink-100 bg-ink-50/40 px-3 py-2"
          >
            <div className="text-[10px] uppercase tracking-wider text-ink-500">
              {src}
            </div>
            <div className="mt-0.5 text-ink-900 font-mono text-[11px]">
              {iso ? `latest ${iso.slice(0, 7)}` : "n/a"}
            </div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-[11px] text-ink-500 italic">
        {card.disclaimer}
      </p>
    </section>
  );
}
