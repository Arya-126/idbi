import type { ImprovementRecommendation } from "../types";

const DIM_LABEL: Record<string, string> = {
  revenue_health: "Revenue",
  cash_flow: "Cash Flow",
  digital_vitality: "Digital",
  compliance: "Compliance",
  employment: "Employment",
  obligation_leverage: "Obligation",
};

const DIM_TINT: Record<string, string> = {
  revenue_health: "bg-emerald-50 text-emerald-700 border-emerald-200",
  cash_flow: "bg-sky-50 text-sky-700 border-sky-200",
  digital_vitality: "bg-violet-50 text-violet-700 border-violet-200",
  compliance: "bg-amber-50 text-amber-700 border-amber-200",
  employment: "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200",
  obligation_leverage: "bg-rose-50 text-rose-700 border-rose-200",
};

export default function RecommendationsPanel({
  items,
}: {
  items: ImprovementRecommendation[];
}) {
  if (items.length === 0) {
    return null;
  }
  return (
    <section className="card p-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-ink-900">
          Improve your score
        </h2>
        <span className="text-[11px] text-ink-500">
          Actions ranked by potential score uplift
        </span>
      </div>
      <ul className="mt-4 space-y-3">
        {items.map((r, i) => (
          <li key={i} className="border-l-2 border-brand-400 pl-4 pr-2 py-1">
            <div className="flex items-baseline justify-between gap-3">
              <div className="flex items-center gap-2">
                <span
                  className={
                    "pill border text-[10px] " +
                    (DIM_TINT[r.dimension_key] ??
                      "bg-ink-100 text-ink-600 border-ink-200")
                  }
                >
                  {DIM_LABEL[r.dimension_key] ?? r.dimension_key}
                </span>
                <span className="text-sm font-semibold text-ink-900">
                  {r.action}
                </span>
              </div>
              <span className="text-xs font-mono tabular-nums text-brand-700 shrink-0">
                +{r.est_score_uplift_pts} pts
              </span>
            </div>
            <p className="mt-1 text-xs text-ink-600 leading-snug">{r.detail}</p>
            <p className="mt-1 text-[10px] text-ink-500">
              Effect visible in ~{r.time_horizon_months} months
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
