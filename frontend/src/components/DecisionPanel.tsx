import type { Decision } from "../types";
import { paiseToInr, recommendationStyle } from "../utils/format";

export default function DecisionPanel({
  decision,
  band,
}: {
  decision: Decision;
  band: string;
}) {
  const rec = recommendationStyle(decision.recommendation);
  const declined = decision.recommendation === "DECLINE";
  return (
    <section className="card p-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-ink-900">
          Lending recommendation
        </h2>
        <span className="text-[11px] text-ink-500">Band {band}</span>
      </div>
      <div className={"mt-3 inline-flex items-center rounded-xl px-3 py-1.5 text-sm font-semibold " + rec.chip}>
        {rec.label}
      </div>

      {!declined ? (
        <dl className="mt-5 grid grid-cols-3 gap-3 text-center">
          <Metric
            label="Suggested limit"
            value={paiseToInr(decision.suggested_limit_paise)}
            emphasize
          />
          <Metric
            label="Tenor"
            value={`${decision.suggested_tenor_months} mo`}
          />
          <Metric
            label="Indicative ROI"
            value={`${decision.suggested_roi_pct.toFixed(1)}%`}
          />
        </dl>
      ) : (
        <div className="mt-5 text-xs text-ink-500 italic">
          No limit computed — profile does not clear the credit gate.
        </div>
      )}

      <div className="mt-5 border-t border-ink-100 pt-4">
        <div className="text-[11px] uppercase tracking-wider text-ink-500">
          Rationale
        </div>
        <p className="mt-1 text-sm text-ink-700 leading-relaxed">
          {decision.rationale}
        </p>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: string;
  emphasize?: boolean;
}) {
  return (
    <div className="rounded-xl border border-ink-100 bg-ink-50/50 py-3 px-2">
      <div className="text-[10px] uppercase tracking-wider text-ink-500">
        {label}
      </div>
      <div
        className={
          "mt-1 font-display font-semibold " +
          (emphasize ? "text-xl text-brand-700" : "text-base text-ink-900")
        }
      >
        {value}
      </div>
    </div>
  );
}
