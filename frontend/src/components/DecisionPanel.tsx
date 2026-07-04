import { useState } from "react";
import type { Decision } from "../types";
import { paiseToInr, recommendationStyle } from "../utils/format";

export default function DecisionPanel({
  decision,
  band,
  extraTail,
}: {
  decision: Decision;
  band: string;
  extraTail?: React.ReactNode;
}) {
  const rec = recommendationStyle(decision.recommendation);
  const declined = decision.recommendation === "DECLINE";
  const [showMath, setShowMath] = useState(false);
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

      {decision.limit_workings.length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => setShowMath((s) => !s)}
            className="text-[11px] text-brand-700 hover:underline"
          >
            {showMath ? "▾ Hide the math" : "▸ How did we get this limit?"}
          </button>
          {showMath && (
            <ul className="mt-2 space-y-1.5 text-xs">
              {decision.limit_workings.map((step, i) => {
                const isFinal = i === decision.limit_workings.length - 1;
                return (
                  <li
                    key={i}
                    className={
                      "grid grid-cols-[1fr_auto] gap-3 py-1.5 border-b border-ink-100 last:border-b-0 " +
                      (isFinal ? "font-semibold text-ink-900" : "text-ink-700")
                    }
                  >
                    <div>
                      <div>{step.label}</div>
                      <div className="text-[10px] text-ink-500">{step.note}</div>
                    </div>
                    <div className="font-mono tabular-nums self-center">
                      {paiseToInr(step.value_paise)}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
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

      {extraTail}
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
