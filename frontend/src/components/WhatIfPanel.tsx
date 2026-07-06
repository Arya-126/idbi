import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { api, storedConsent } from "../api";
import type { WhatIfRequest, WhatIfResponse } from "../types";

// Officer-facing sensitivity simulator: move a lever, watch the composite,
// band, decision and ML PD respond. Works around the deterministic demo data
// (a re-pull can't change the score, but a counterfactual can).

const LEVERS: {
  key: keyof WhatIfRequest;
  label: string;
  min: number;
  max: number;
  step: number;
  fmt: (v: number) => string;
}[] = [
  {
    key: "gst_filing_on_time_pct",
    label: "GST on-time filing",
    min: 0,
    max: 1,
    step: 0.05,
    fmt: (v) => `${Math.round(v * 100)}%`,
  },
  {
    key: "bounce_count",
    label: "Bounces (12m)",
    min: 0,
    max: 8,
    step: 1,
    fmt: (v) => `${v}`,
  },
  {
    key: "turnover_growth_pct",
    label: "Turnover growth",
    min: -0.3,
    max: 0.3,
    step: 0.05,
    fmt: (v) => `${v >= 0 ? "+" : ""}${Math.round(v * 100)}%`,
  },
  {
    key: "balance_buffer_months",
    label: "Balance buffer",
    min: 0,
    max: 4,
    step: 0.25,
    fmt: (v) => `${v.toFixed(2)} mo`,
  },
  {
    key: "upi_unique_payers",
    label: "UPI unique payers",
    min: 0,
    max: 1000,
    step: 10,
    fmt: (v) => `${v}`,
  },
];

export default function WhatIfPanel({ gstin }: { gstin: string }) {
  const [base, setBase] = useState<WhatIfResponse | null>(null);
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [values, setValues] = useState<Partial<Record<string, number>>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  // First call with no overrides seats the sliders at the borrower's actual
  // values and gives the baseline.
  useEffect(() => {
    api
      .whatIf(gstin, {}, storedConsent(gstin))
      .then((r) => {
        setBase(r);
        setResult(r);
        setValues({ ...r.current });
      })
      .catch((e) => setError(String(e)));
  }, [gstin]);

  function onSlide(key: string, v: number) {
    const next = { ...values, [key]: v };
    setValues(next);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      if (!base) return;
      // Send only levers that moved off the borrower's actual value.
      const overrides: WhatIfRequest = {};
      for (const l of LEVERS) {
        const cur = base.current[l.key as string];
        const val = next[l.key as string];
        if (val !== undefined && Math.abs(val - cur) > 1e-9) {
          (overrides as Record<string, number>)[l.key as string] = val;
        }
      }
      setBusy(true);
      api
        .whatIf(gstin, overrides, storedConsent(gstin))
        .then(setResult)
        .catch((e) => setError(String(e)))
        .finally(() => setBusy(false));
    }, 350);
  }

  function reset() {
    if (!base) return;
    setValues({ ...base.current });
    setResult(base);
  }

  if (error) return null; // sensitivity is a bonus panel — fail quiet
  if (!base || !result) {
    return (
      <section className="card p-6 animate-pulse">
        <div className="h-4 w-1/4 bg-ink-100 rounded" />
        <div className="h-24 w-full bg-ink-100 rounded mt-4" />
      </section>
    );
  }

  const moved = result.delta_pts !== 0 || result.changed.length > 0;

  return (
    <section className="card p-6 print:hidden">
      <div className="flex items-baseline justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-ink-900">
            What-if simulator
          </h2>
          <span className="pill bg-ink-50 border border-ink-200 text-ink-500 text-[10px]">
            re-runs scorecard + ML live · nothing saved
          </span>
        </div>
        <button
          onClick={reset}
          className="btn-ghost !py-1 !px-2.5 text-xs border border-ink-200 rounded-lg"
        >
          Reset
        </button>
      </div>

      <div className="mt-4 grid gap-x-8 gap-y-3 md:grid-cols-2">
        {LEVERS.map((l) => {
          const v = values[l.key as string] ?? base.current[l.key as string];
          const cur = base.current[l.key as string];
          const changed = Math.abs(v - cur) > 1e-9;
          return (
            <label key={l.key} className="block text-xs">
              <div className="flex justify-between">
                <span className={clsx("font-medium", changed ? "text-brand-700" : "text-ink-700")}>
                  {l.label}
                </span>
                <span className="font-mono tabular-nums text-ink-600">
                  {l.fmt(v)}
                  {changed && (
                    <span className="text-ink-400"> (was {l.fmt(cur)})</span>
                  )}
                </span>
              </div>
              <input
                type="range"
                min={l.min}
                max={l.max}
                step={l.step}
                value={v}
                onChange={(e) => onSlide(l.key as string, Number(e.target.value))}
                className="mt-1 w-full accent-brand-600"
              />
            </label>
          );
        })}
      </div>

      <div
        className={clsx(
          "mt-5 rounded-xl border p-4 flex flex-wrap items-center gap-x-8 gap-y-2 transition-colors",
          !moved
            ? "border-ink-100 bg-ink-50/40"
            : result.delta_pts >= 0
              ? "border-brand-200 bg-brand-50/60"
              : "border-red-200 bg-red-50/60",
          busy && "opacity-60",
        )}
      >
        <Stat
          label="Composite"
          value={`${result.new_composite}`}
          sub={
            moved
              ? `${result.delta_pts >= 0 ? "+" : ""}${result.delta_pts} vs ${result.base_composite}`
              : "current"
          }
        />
        <Stat
          label="Band"
          value={result.new_band}
          sub={moved && result.new_band !== result.base_band ? `was ${result.base_band}` : undefined}
        />
        <Stat
          label="Decision"
          value={result.new_recommendation}
          sub={
            moved && result.new_recommendation !== result.base_recommendation
              ? `was ${result.base_recommendation}`
              : undefined
          }
        />
        <Stat
          label="ML PD"
          value={`${(result.new_pd * 100).toFixed(1)}%`}
          sub={
            moved
              ? `${result.new_pd >= result.base_pd ? "+" : ""}${((result.new_pd - result.base_pd) * 100).toFixed(1)} pp`
              : undefined
          }
        />
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-ink-500">
        {label}
      </div>
      <div className="text-lg font-display font-semibold text-ink-900 leading-tight">
        {value}
      </div>
      {sub && <div className="text-[10px] text-ink-500">{sub}</div>}
    </div>
  );
}
