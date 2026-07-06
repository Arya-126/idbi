import clsx from "clsx";
import type { MlAssessment, MlDriver } from "../types";

export default function MlPanel({ ml }: { ml: MlAssessment }) {
  const pdPct = ml.probability_of_default * 100;
  const zone = pdPct < 5 ? "safe" : pdPct < 15 ? "watch" : pdPct < 30 ? "elevated" : "high";
  const agrees = ml.agrees_with_rulebook;

  return (
    <section className="card p-6">
      <div className="flex items-baseline justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-ink-900">
            ML second opinion
          </h2>
          <span className="pill bg-ink-50 border border-ink-200 text-ink-500 text-[10px]">
            HistGB · trained on {ml.trained_on_n_samples} synthetic MSMEs
          </span>
          {ml.monotonic_constraints && (
            <span
              className="pill bg-sky-50 border border-sky-200 text-sky-700 text-[10px]"
              title="Every direction-known feature is monotonicity-constrained — the model provably cannot learn 'more bounces is safer'"
            >
              monotonic
            </span>
          )}
          <span
            className="pill bg-sky-50 border border-sky-200 text-sky-700 text-[10px]"
            title="Probabilities are Platt-calibrated on a 5-fold split; Brier score measures probability quality on the holdout"
          >
            calibrated
          </span>
        </div>
        <span
          className={clsx(
            "pill text-[10px] border",
            agrees
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : "bg-amber-50 text-amber-700 border-amber-200",
          )}
        >
          {agrees ? "agrees with rulebook" : "disagrees with rulebook"}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-[1fr_auto] items-end gap-6">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-ink-500">
            Probability of default (12m)
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span
              className={
                "text-3xl font-display font-semibold " + zoneTextColor(zone)
              }
            >
              {pdPct.toFixed(1)}%
            </span>
            <span className="text-xs text-ink-500">
              · confidence {ml.confidence}
            </span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-ink-100 overflow-hidden">
            <div
              className={"h-full transition-all duration-700 " + zoneBarColor(zone)}
              style={{ width: `${Math.min(100, pdPct * 2.2)}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-ink-500 font-mono">
            <span>0%</span>
            <span>~15%</span>
            <span>~30%</span>
            <span>≥45%</span>
          </div>
        </div>
      </div>

      <p className="mt-4 text-sm text-ink-700">{ml.summary}</p>

      {(ml.drivers.length > 0 || ml.supports.length > 0) && (
        <div className="mt-5 border-t border-ink-100 pt-4 space-y-4">
          {ml.drivers.length > 0 && (
            <DriverList
              title="Pushing PD up"
              chipClass="bg-red-50 text-red-700 border-red-200"
              items={ml.drivers}
              signPrefix="+"
              signColor="text-red-700"
            />
          )}
          {ml.supports.length > 0 && (
            <DriverList
              title="Holding PD down"
              chipClass="bg-emerald-50 text-emerald-700 border-emerald-200"
              items={ml.supports}
              signPrefix=""
              signColor="text-emerald-700"
            />
          )}
        </div>
      )}

      <div className="mt-4 text-[10px] text-ink-400 font-mono">
        model {ml.model_version}
        {ml.holdout_auc != null &&
          ` · holdout AUC ${ml.holdout_auc.toFixed(2)}`}
        {ml.holdout_brier != null &&
          ` · Brier ${ml.holdout_brier.toFixed(3)}`}
        {` · ${ml.calibration}-calibrated`}
      </div>
    </section>
  );
}

function DriverList({
  title,
  chipClass,
  items,
  signPrefix,
  signColor,
}: {
  title: string;
  chipClass: string;
  items: MlDriver[];
  signPrefix: string;
  signColor: string;
}) {
  return (
    <div>
      <div className={"inline-flex pill border text-[10px] mb-2 " + chipClass}>
        {title}
      </div>
      <ul className="space-y-1.5">
        {items.map((d) => (
          <li
            key={d.feature_key}
            className="flex items-baseline justify-between gap-3 text-xs"
          >
            <span className="text-ink-700 truncate">
              <span className="font-medium">{d.feature_label}</span>
              <span className="text-ink-500"> · {d.detail}</span>
            </span>
            <span className={"font-mono tabular-nums shrink-0 " + signColor}>
              {signPrefix}
              {(d.contribution * 100).toFixed(1)} pp
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function zoneTextColor(z: string): string {
  switch (z) {
    case "safe":
      return "text-brand-700";
    case "watch":
      return "text-emerald-700";
    case "elevated":
      return "text-amber-700";
    case "high":
      return "text-red-700";
    default:
      return "text-ink-900";
  }
}

function zoneBarColor(z: string): string {
  switch (z) {
    case "safe":
      return "bg-brand-500";
    case "watch":
      return "bg-emerald-500";
    case "elevated":
      return "bg-amber-500";
    case "high":
      return "bg-red-500";
    default:
      return "bg-ink-500";
  }
}
