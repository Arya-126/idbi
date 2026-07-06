import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { api } from "../api";
import type { ComplianceItem } from "../types";

const STATUS_STYLE: Record<ComplianceItem["status"], string> = {
  IMPLEMENTED: "bg-brand-100 text-brand-700 border-brand-200",
  SIMULATED: "bg-sky-50 text-sky-700 border-sky-200",
  PRODUCTION_PLAN: "bg-amber-50 text-amber-700 border-amber-200",
};

const STATUS_LABEL: Record<ComplianceItem["status"], string> = {
  IMPLEMENTED: "Implemented",
  SIMULATED: "Simulated",
  PRODUCTION_PLAN: "Production plan",
};

export default function CompliancePage() {
  const [items, setItems] = useState<ComplianceItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.compliance().then(setItems).catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-14 card p-4 border-red-200 bg-red-50 text-red-700 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 space-y-4">
      <header>
        <div className="text-[11px] uppercase tracking-wider text-ink-500">
          Regulatory perimeter
        </div>
        <h1 className="mt-1 text-2xl font-display font-semibold text-ink-900">
          RBI Digital Lending Guidelines checklist
        </h1>
        <p className="mt-1 text-sm text-ink-600 max-w-3xl">
          Honest status per requirement: <strong>Implemented</strong> works in
          this demo, <strong>Simulated</strong> means the mechanism exists but
          the counterparty is mocked, and <strong>Production plan</strong> is
          deliberately out of hackathon scope — noted, not hidden.
        </p>
      </header>

      {!items ? (
        <div className="grid gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-5 h-20 animate-pulse bg-white" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3">
          {items.map((item) => (
            <div key={item.requirement} className="card p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-ink-900">
                    {item.requirement}
                  </div>
                  <p className="mt-1 text-xs text-ink-600 leading-snug">
                    {item.evidence}
                  </p>
                  {item.link && (
                    <Link
                      to={item.link}
                      className="mt-1.5 inline-block text-xs text-brand-700 hover:underline"
                    >
                      See it in the demo →
                    </Link>
                  )}
                </div>
                <span
                  className={clsx(
                    "pill border text-[10px] shrink-0",
                    STATUS_STYLE[item.status],
                  )}
                >
                  {STATUS_LABEL[item.status]}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
