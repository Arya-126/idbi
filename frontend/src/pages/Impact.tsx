import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { api } from "../api";
import type { ImpactSummary } from "../types";
import { paiseToInr } from "../utils/format";

export default function ImpactPage() {
  const [data, setData] = useState<ImpactSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.impact().then(setData).catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-14 card p-4 border-red-200 bg-red-50 text-red-700 text-sm">
        {error}
      </div>
    );
  }
  if (!data) return <div className="mx-auto max-w-7xl px-6 py-8 text-sm text-ink-500">Computing impact…</div>;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      <header>
        <div className="text-[11px] uppercase tracking-wider text-ink-500">
          Before / after impact
        </div>
        <h1 className="mt-1 text-2xl font-display font-semibold text-ink-900">
          How much more do we onboard?
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          {data.additional_msmes_served} additional MSMEs (of {data.total_msmes})
          receive credit vs a bureau-only workflow — {data.ntc_ntb_included} of
          them credit-invisible today.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-4">
        {data.metrics.map((m) => (
          <div key={m.key} className="card p-5">
            <div className="text-[10px] uppercase tracking-wider text-ink-500">
              {m.label}
            </div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <div>
                <div className="text-[9px] text-ink-400 uppercase">Traditional</div>
                <div className="mt-0.5 text-lg font-display text-ink-500 line-through">
                  {m.traditional}
                </div>
              </div>
              <div>
                <div className="text-[9px] text-ink-400 uppercase">Alternate</div>
                <div className="mt-0.5 text-lg font-display font-semibold text-ink-900">
                  {m.alternate}
                </div>
              </div>
            </div>
            <div
              className={clsx(
                "mt-2 text-xs font-medium",
                m.positive ? "text-brand-700" : "text-amber-700",
              )}
            >
              {m.lift}
            </div>
            {m.note && (
              <p className="mt-1.5 text-[10px] leading-snug text-ink-400">
                {m.note}
              </p>
            )}
          </div>
        ))}
      </section>

      {data.inclusion.length > 0 && (
        <section className="card p-5">
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-sm font-semibold text-ink-900">
              Inclusion dashboard — credit-invisible vs established
            </h2>
            <span className="text-[11px] text-ink-500">
              same book, same metrics, no bureau anywhere
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-ink-500 border-b border-ink-100 bg-ink-50/40">
                  <th className="px-3 py-2 font-medium">Segment</th>
                  <th className="px-3 py-2 font-medium text-right">Firms</th>
                  <th className="px-3 py-2 font-medium text-right">Approval rate</th>
                  <th className="px-3 py-2 font-medium text-right">Avg score</th>
                  <th className="px-3 py-2 font-medium text-right">Avg PD</th>
                  <th className="px-3 py-2 font-medium text-right">Avg limit (approved)</th>
                </tr>
              </thead>
              <tbody>
                {data.inclusion.map((s) => (
                  <tr key={s.key} className="border-b border-ink-100 last:border-b-0">
                    <td className="px-3 py-2.5 font-medium text-ink-900">
                      {s.label}
                      {s.key === "ntc_ntb" && (
                        <span className="ml-1.5 pill bg-violet-50 text-violet-700 border border-violet-200 text-[9px]">
                          the target segment
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{s.count}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums font-medium">
                      {(s.approval_rate * 100).toFixed(0)}%
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {s.avg_score.toFixed(0)}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {(s.avg_pd * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {s.avg_limit_paise > 0 ? paiseToInr(s.avg_limit_paise) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[11px] text-ink-500">
            A credit-invisible firm is approvable at comparable quality when the
            alternate-data signals support it — inclusion without adverse
            selection.
          </p>
        </section>
      )}

      <section className="card p-5">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-sm font-semibold text-ink-900">
            Rescued borrowers ({data.rescued_rows.length})
          </h2>
          <span className="text-[11px] text-ink-500">
            Alternate approves, traditional rejects
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-ink-500 border-b border-ink-100 bg-ink-50/40">
                <th className="px-3 py-2 font-medium">MSME</th>
                <th className="px-3 py-2 font-medium">Sector</th>
                <th className="px-3 py-2 font-medium text-right">Turnover</th>
                <th className="px-3 py-2 font-medium">Traditional</th>
                <th className="px-3 py-2 font-medium">Alternate</th>
                <th className="px-3 py-2 font-medium text-right">Limit</th>
                <th className="px-3 py-2 font-medium text-right">PD</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {data.rescued_rows.map((r) => (
                <tr key={r.gstin} className="border-b border-ink-100 last:border-b-0">
                  <td className="px-3 py-2.5">
                    <div className="font-medium text-ink-900">
                      {r.trade_name}
                      {r.is_ntc && (
                        <span className="ml-1.5 pill bg-violet-50 text-violet-700 border border-violet-200 text-[9px]">
                          NTC
                        </span>
                      )}
                      {r.is_ntb && (
                        <span className="ml-1 pill bg-sky-50 text-sky-700 border border-sky-200 text-[9px]">
                          NTB
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-ink-700">{r.sector}</td>
                  <td className="px-3 py-2.5 text-right text-xs font-mono tabular-nums">
                    {paiseToInr(r.monthly_turnover_paise)}
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    <span className="pill bg-red-50 text-red-700 border border-red-200 text-[9px]">
                      REJECT
                    </span>
                    <div className="text-[10px] text-ink-500 mt-0.5">{r.traditional_reason}</div>
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    <span
                      className={clsx(
                        "pill text-[9px]",
                        r.alternate_verdict === "APPROVE"
                          ? "bg-brand-600 text-white"
                          : "bg-amber-500 text-white",
                      )}
                    >
                      {r.alternate_verdict}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs font-mono tabular-nums">
                    {paiseToInr(r.alternate_limit_paise)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs font-mono tabular-nums text-ink-700">
                    {(r.probability_of_default * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <Link
                      to={`/msme/${r.gstin}`}
                      className="text-brand-600 hover:underline text-xs"
                    >
                      Open →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-[11px] text-ink-500">
          Traditional heuristic rejects any of: no bureau footprint (NTC),
          vintage &lt; 24 months, monthly turnover &lt; ₹12L, or proprietorship
          under ₹20L. The alternate-data engine uses 6 dimensions plus an ML
          second opinion to make a bureau-independent call.
        </p>
      </section>
    </div>
  );
}
