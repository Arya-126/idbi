import clsx from "clsx";
import type { DimensionScore } from "../types";
import { factorKindColor, trendColor, trendGlyph } from "../utils/format";

export default function DimensionCard({ dim }: { dim: DimensionScore }) {
  return (
    <div className={clsx("card p-5", !dim.consented && "opacity-60 bg-ink-50/50")}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <div className="text-sm font-semibold text-ink-900">{dim.label}</div>
            {!dim.consented && (
              <span
                className="pill bg-ink-100 text-ink-500 border border-ink-200 text-[9px]"
                title="Borrower did not share this data source — dimension excluded, remaining weights renormalized"
              >
                not shared
              </span>
            )}
          </div>
          <div className="text-xs text-ink-500 mt-0.5 leading-snug">
            {dim.summary}
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-display font-semibold text-ink-900 leading-none">
            {dim.consented ? dim.score : "—"}
            <span className="text-xs font-normal text-ink-500 ml-1">/100</span>
          </div>
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mt-1">
            weight {(dim.weight * 100).toFixed(0)}% ·{" "}
            {dim.peer_percentile != null && (
              <>
                <span
                  className={
                    "font-medium " +
                    (dim.peer_percentile >= 75
                      ? "text-brand-700"
                      : dim.peer_percentile <= 25
                        ? "text-red-700"
                        : "text-ink-600")
                  }
                  title="Percentile among same-sector peers in the portfolio"
                >
                  {percentileLabel(dim.peer_percentile)}
                </span>{" "}
                ·{" "}
              </>
            )}
            <span className={trendColor(dim.trend)}>
              {trendGlyph(dim.trend)} {dim.trend.toLowerCase()}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-3 h-2 rounded-full bg-ink-100 overflow-hidden">
        <div
          className={clsx(
            "h-full transition-all duration-700",
            dim.score >= 75
              ? "bg-brand-500"
              : dim.score >= 55
                ? "bg-emerald-400"
                : dim.score >= 35
                  ? "bg-amber-500"
                  : "bg-red-500",
          )}
          style={{ width: `${dim.score}%` }}
        />
      </div>

      {dim.peer_percentile != null && (
        <div className="mt-1 text-[10px] text-ink-500">
          {percentileNarrative(dim.peer_percentile, dim.label)}
        </div>
      )}

      <div className="mt-4 space-y-2">
        {dim.factors.map((f, i) => (
          <div
            key={i}
            className={clsx(
              "border-l-2 pl-3 pr-2 py-2 rounded-r-lg flex items-start justify-between gap-3",
              factorKindColor(f.kind),
            )}
          >
            <div className="min-w-0">
              <div className="text-[11px] font-semibold text-ink-900">
                {f.name}
                {f.code && (
                  <span
                    className="ml-1.5 font-mono font-normal text-[9px] text-ink-400"
                    title="Stable reason code — every decision traces to coded factors"
                  >
                    {f.code}
                  </span>
                )}
              </div>
              <div className="text-[11px] text-ink-600 leading-snug">
                {f.detail}
              </div>
            </div>
            <div
              className={clsx(
                "text-xs font-mono tabular-nums shrink-0 mt-0.5",
                f.contribution > 0
                  ? "text-emerald-700"
                  : f.contribution < 0
                    ? "text-red-700"
                    : "text-ink-500",
              )}
            >
              {f.contribution > 0 ? "+" : ""}
              {f.contribution}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function percentileLabel(p: number): string {
  if (p >= 90) return `top 10% in sector`;
  if (p >= 75) return `top ${100 - p}% in sector`;
  if (p >= 50) return `median for sector`;
  if (p >= 25) return `bottom ${p}% in sector`;
  return `bottom ${p}% in sector`;
}

function percentileNarrative(p: number, label: string): string {
  if (p >= 75) return `Ahead of ${p}% of same-sector peers on ${label.toLowerCase()}.`;
  if (p >= 50) return `Around the sector median on ${label.toLowerCase()}.`;
  if (p >= 25) return `Behind the sector median — ${p}th percentile.`;
  return `Bottom ${p}% of same-sector peers — priority area to improve.`;
}
