import type { HealthCard } from "../types";
import { bandColor, recommendationStyle } from "../utils/format";
import ScoreDial from "./ScoreDial";

export default function HealthHeader({ card }: { card: HealthCard }) {
  const e = card.enterprise;
  const rec = recommendationStyle(card.decision.recommendation);
  return (
    <section className="card p-6">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-display font-semibold text-ink-900 truncate">
              {e.trade_name}
            </h1>
            <span className="pill bg-ink-100 text-ink-600 border border-ink-200">
              {e.entity_type.replace("_", " ")}
            </span>
            <span className="pill bg-brand-50 text-brand-700 border border-brand-200">
              {e.msme_category}
            </span>
          </div>
          <div className="mt-1 text-sm text-ink-500">
            {e.legal_name} · {e.sector} · {e.sub_sector} · {e.registered_city},{" "}
            {e.registered_state}
          </div>
          <dl className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <Field label="GSTIN" value={e.gstin} mono />
            <Field label="PAN" value={e.pan} mono />
            <Field label="Udyam" value={e.udyam_number ?? "—"} mono />
            <Field
              label="Incorporated"
              value={new Date(e.incorporation_date).toLocaleDateString("en-IN", {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            />
          </dl>
        </div>

        <div className="flex items-stretch gap-6">
          <ScoreDial score={card.composite_score} band={card.risk_band} />
          <div className="flex flex-col justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-ink-500">
                Risk band
              </div>
              <div
                className={
                  "mt-1 inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-base font-semibold " +
                  bandColor(card.risk_band)
                }
              >
                <span className="text-2xl leading-none">{card.risk_band}</span>
                <span className="text-xs uppercase tracking-wider opacity-70">
                  {bandLabel(card.risk_band)}
                </span>
              </div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wider text-ink-500">
                Recommendation
              </div>
              <div
                className={
                  "mt-1 inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-sm font-semibold " +
                  rec.chip
                }
              >
                {rec.label}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function bandLabel(b: string): string {
  switch (b) {
    case "A":
      return "Prime";
    case "B":
      return "Standard";
    case "C":
      return "Marginal";
    case "D":
      return "High risk";
    default:
      return "";
  }
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-ink-500">
        {label}
      </dt>
      <dd
        className={
          "mt-0.5 text-ink-900 " + (mono ? "font-mono text-[11px]" : "text-xs")
        }
      >
        {value}
      </dd>
    </div>
  );
}
