import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { api } from "../api";
import type { PortfolioBucket, PortfolioSummary } from "../types";
import { bandColor, paiseToInr, recommendationStyle } from "../utils/format";

export default function PortfolioPage() {
  const [data, setData] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "watch" | "ntc" | "demo">("all");
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    api
      .portfolio()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  async function refresh() {
    setRefreshing(true);
    try {
      setData(await api.refreshPortfolio());
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshing(false);
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-14">
        <div className="card p-4 border-red-200 bg-red-50 text-red-700 text-sm">
          {error}
        </div>
      </div>
    );
  }

  if (!data) return <PortfolioSkeleton />;

  const filtered = data.entries.filter((e) => {
    if (filter === "watch") return e.is_watchlist;
    if (filter === "demo") return e.is_demo;
    if (filter === "ntc") return e.is_ntc || e.is_ntb;
    return true;
  });
  const ntcNtbTotal = data.entries.filter((e) => e.is_ntc || e.is_ntb).length;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-ink-500">
            Credit officer view
          </div>
          <h1 className="mt-1 text-2xl font-display font-semibold text-ink-900">
            Portfolio overview
          </h1>
          <p className="mt-1 text-sm text-ink-600">
            {data.total_msmes} MSMEs scored via alternate data.{" "}
            {data.ntc_ntb_count} NTC/NTB firms onboarded despite absent bureau
            history · {data.watchlist_count} on watch-list.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-ink-500 font-mono">
            refreshed {new Date(data.generated_at).toLocaleString("en-IN")}
          </span>
          <button
            onClick={refresh}
            disabled={refreshing}
            className={clsx(
              "btn-ghost !py-1 !px-2.5 text-xs border border-ink-200 rounded-lg",
              refreshing && "opacity-60 cursor-not-allowed",
            )}
          >
            {refreshing ? "Re-scoring…" : "↻ Re-score book"}
          </button>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-4">
        <Kpi
          label="Avg composite score"
          value={data.avg_composite_score.toFixed(0)}
          sub="of 1000"
        />
        <Kpi
          label="Avg PD (ML)"
          value={`${(data.avg_pd * 100).toFixed(1)}%`}
          sub="12-month horizon"
          tone={data.avg_pd < 0.15 ? "good" : data.avg_pd < 0.25 ? "warn" : "bad"}
        />
        <Kpi
          label="Total exposure"
          value={paiseToInr(data.total_exposure_paise)}
          sub="Σ suggested limits"
        />
        <Kpi
          label="Financial inclusion"
          value={`${data.ntc_ntb_count}`}
          sub="NTC/NTB approved"
          tone="good"
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1fr_1fr]">
        <BucketPanel
          title="Risk band mix"
          buckets={data.band_distribution}
          colorFn={bandColor}
        />
        <BucketPanel
          title="Recommendation mix"
          buckets={data.recommendation_mix}
          colorFn={(k) => {
            const r = recommendationStyle(k).chip;
            return `${r} border-transparent`;
          }}
          isSolid
        />
        <BucketPanel
          title="Sector mix"
          buckets={data.sector_mix}
          colorFn={() => "text-ink-700 bg-ink-100 border-ink-200"}
        />
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-ink-900">
            Portfolio book — {filtered.length}{" "}
            <span className="text-ink-500 font-normal">
              of {data.total_msmes}
            </span>
          </h2>
          <div className="flex items-center gap-1 rounded-xl border border-ink-200 bg-white p-1 text-xs">
            {(
              [
                ["all", "All"],
                ["watch", `Watch-list (${data.watchlist_count})`],
                ["ntc", `NTC/NTB (${ntcNtbTotal})`],
                ["demo", "Demo personas"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                onClick={() => setFilter(k)}
                className={clsx(
                  "px-2.5 py-1 rounded-lg transition",
                  filter === k
                    ? "bg-brand-600 text-white"
                    : "text-ink-600 hover:bg-ink-50",
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-ink-500 border-b border-ink-100 bg-ink-50/40">
                  <th className="px-4 py-2 font-medium">MSME</th>
                  <th className="px-4 py-2 font-medium">Sector</th>
                  <th className="px-4 py-2 font-medium text-right">Turnover</th>
                  <th className="px-4 py-2 font-medium text-right">Score</th>
                  <th className="px-4 py-2 font-medium text-center">Band</th>
                  <th className="px-4 py-2 font-medium text-right">PD</th>
                  <th className="px-4 py-2 font-medium">Decision</th>
                  <th className="px-4 py-2 font-medium text-right">Limit</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <tr
                    key={e.gstin}
                    className={clsx(
                      "border-b border-ink-100 last:border-b-0",
                      e.is_watchlist && "bg-red-50/20",
                    )}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-ink-900">
                        {e.trade_name}
                        {e.is_demo && (
                          <span className="ml-2 pill bg-brand-50 text-brand-700 border border-brand-200 text-[9px]">
                            demo
                          </span>
                        )}
                        {e.is_ntc && (
                          <span className="ml-1.5 pill bg-violet-50 text-violet-700 border border-violet-200 text-[9px]">
                            NTC
                          </span>
                        )}
                        {e.is_ntb && (
                          <span className="ml-1.5 pill bg-sky-50 text-sky-700 border border-sky-200 text-[9px]">
                            NTB
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-ink-500">
                        {e.registered_city} · {e.msme_category}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-ink-700 text-xs">
                      {e.sub_sector}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-xs">
                      {paiseToInr(e.monthly_turnover_paise)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums font-medium">
                      {e.composite_score}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={
                          "inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold border " +
                          bandColor(e.risk_band)
                        }
                      >
                        {e.risk_band}
                      </span>
                    </td>
                    <td
                      className={clsx(
                        "px-4 py-3 text-right font-mono tabular-nums text-xs",
                        e.probability_of_default > 0.25
                          ? "text-red-700 font-medium"
                          : e.probability_of_default > 0.15
                            ? "text-amber-700"
                            : "text-ink-700",
                      )}
                    >
                      {(e.probability_of_default * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          "pill text-[10px] " +
                          recommendationStyle(e.recommendation).chip
                        }
                      >
                        {recommendationStyle(e.recommendation).label}
                      </span>
                      {e.watchlist_reason && (
                        <div className="text-[10px] text-red-600 mt-0.5 truncate max-w-56">
                          {e.watchlist_reason}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-xs text-ink-700">
                      {e.suggested_limit_paise > 0
                        ? paiseToInr(e.suggested_limit_paise)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/msme/${e.gstin}`}
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
        </div>
      </section>
    </div>
  );
}

function Kpi({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone?: "good" | "warn" | "bad";
}) {
  const toneClass =
    tone === "good"
      ? "text-brand-700"
      : tone === "warn"
        ? "text-amber-700"
        : tone === "bad"
          ? "text-red-700"
          : "text-ink-900";
  return (
    <div className="card p-5">
      <div className="text-[10px] uppercase tracking-wider text-ink-500">
        {label}
      </div>
      <div className={"mt-1 text-2xl font-display font-semibold " + toneClass}>
        {value}
      </div>
      <div className="text-[11px] text-ink-500 mt-0.5">{sub}</div>
    </div>
  );
}

function BucketPanel({
  title,
  buckets,
  colorFn,
  isSolid,
}: {
  title: string;
  buckets: PortfolioBucket[];
  colorFn: (k: string) => string;
  isSolid?: boolean;
}) {
  const max = Math.max(...buckets.map((b) => b.count), 1);
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-ink-900 mb-3">{title}</h3>
      <ul className="space-y-2">
        {buckets.map((b) => (
          <li key={b.key} className="flex items-center gap-3">
            <span
              className={clsx(
                "pill border text-[11px] min-w-28 justify-start",
                colorFn(b.key),
                isSolid && "text-white border-transparent",
              )}
            >
              {b.label}
            </span>
            <div className="flex-1 h-2 rounded-full bg-ink-100 overflow-hidden">
              <div
                className={"h-full transition-all duration-700 " + bucketFill(b.key, colorFn, isSolid)}
                style={{ width: `${(b.count / max) * 100}%` }}
              />
            </div>
            <span className="text-xs text-ink-700 tabular-nums w-12 text-right">
              {b.count} <span className="text-ink-400">({(b.share * 100).toFixed(0)}%)</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function bucketFill(k: string, colorFn: (k: string) => string, isSolid?: boolean): string {
  if (isSolid) {
    // reuse the recommendation chip bg
    const cn = colorFn(k);
    if (cn.includes("brand-600")) return "bg-brand-600";
    if (cn.includes("amber")) return "bg-amber-500";
    if (cn.includes("red")) return "bg-red-600";
    return "bg-ink-500";
  }
  // For bands: A green, B emerald, C amber, D red; default ink
  if (k === "A") return "bg-brand-500";
  if (k === "B") return "bg-emerald-400";
  if (k === "C") return "bg-amber-500";
  if (k === "D") return "bg-red-500";
  return "bg-ink-400";
}

function PortfolioSkeleton() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      <div className="h-12 w-1/3 bg-ink-100 rounded animate-pulse" />
      <div className="grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card p-6 h-24 animate-pulse" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="card p-6 h-56 animate-pulse" />
        ))}
      </div>
    </div>
  );
}
