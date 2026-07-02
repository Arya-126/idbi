import clsx from "clsx";
import type { DimensionScore } from "../types";
import { factorKindColor, trendColor, trendGlyph } from "../utils/format";

export default function DimensionCard({ dim }: { dim: DimensionScore }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-ink-900">{dim.label}</div>
          <div className="text-xs text-ink-500 mt-0.5 truncate">
            {dim.summary}
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-display font-semibold text-ink-900 leading-none">
            {dim.score}
            <span className="text-xs font-normal text-ink-500 ml-1">/100</span>
          </div>
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mt-1">
            weight {(dim.weight * 100).toFixed(0)}% ·{" "}
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
