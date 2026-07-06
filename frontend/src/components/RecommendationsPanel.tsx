import type { ImprovementRecommendation, PathToNextBand } from "../types";

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
  path,
}: {
  items: ImprovementRecommendation[];
  path?: PathToNextBand | null;
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
          Uplifts computed by re-running your scorecard, not estimates
        </span>
      </div>

      {path && (
        <div
          className={
            "mt-4 rounded-xl border p-4 " +
            (path.achievable
              ? "border-brand-200 bg-brand-50/60"
              : "border-amber-200 bg-amber-50/60")
          }
        >
          <div className="text-xs font-semibold text-ink-900">
            {path.achievable
              ? `Path to Band ${path.target_band} — within reach`
              : `Toward Band ${path.target_band} — these actions close most of the gap`}
          </div>
          <div className="mt-1 text-xs text-ink-700">
            {path.actions.length === 1 ? (
              <>1 action</>
            ) : (
              <>{path.actions.length} actions</>
            )}{" "}
            → projected score{" "}
            <span className="font-mono font-semibold">{path.projected_score}</span>{" "}
            (+{path.uplift_pts} pts), roughly {path.time_horizon_months} months:
          </div>
          <ol className="mt-2 list-decimal list-inside space-y-0.5 text-xs text-ink-700">
            {path.actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ol>
        </div>
      )}
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
