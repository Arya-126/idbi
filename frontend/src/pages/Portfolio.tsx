import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { api } from "../api";
import type {
  ConcentrationSummary,
  PortfolioBucket,
  PortfolioEntry,
  PortfolioSummary,
  StressResult,
  StressScenario,
  VintageCohort,
  WatchlistAction,
  WatchlistActionKind,
} from "../types";
import { bandColor, paiseToInr, recommendationStyle } from "../utils/format";

export default function PortfolioPage() {
  const [data, setData] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<
    "all" | "watch" | "ntc" | "demo" | "divergent"
  >("all");
  const [refreshing, setRefreshing] = useState(false);
  const [drawerEntry, setDrawerEntry] = useState<PortfolioEntry | null>(null);

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
    if (filter === "divergent") return e.ml_divergent;
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

      <section className="grid gap-4 md:grid-cols-5">
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
        <Kpi
          label="ML disagrees"
          value={`${data.ml_divergent_count}`}
          sub="champion/challenger queue"
          tone={data.ml_divergent_count > 0 ? "warn" : "good"}
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

      <section className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <GuardrailsPanel c={data.concentration} />
        <VintagePanel cohorts={data.vintage_cohorts} />
      </section>

      <StressPanel />

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
                ["divergent", `ML disagrees (${data.ml_divergent_count})`],
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
                  <th className="px-4 py-2 font-medium text-center">Trend</th>
                  <th className="px-4 py-2 font-medium text-right">PD</th>
                  <th className="px-4 py-2 font-medium">Decision / EWS</th>
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
                    <td className="px-4 py-3 text-center">
                      <TrendChip trend={e.trend} />
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
                      {e.ml_divergent && (
                        <span
                          className="ml-1 pill bg-amber-50 text-amber-700 border border-amber-200 text-[9px]"
                          title="Advisory ML PD disagrees with the rulebook decision — champion/challenger review case"
                        >
                          ML disagrees
                        </span>
                      )}
                      {e.ews_flags.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1 max-w-64">
                          {e.ews_flags.map((f, i) => (
                            <span
                              key={i}
                              className="pill bg-red-50 text-red-700 border border-red-200 text-[9px]"
                            >
                              ⚠ {f}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-xs text-ink-700">
                      {e.suggested_limit_paise > 0
                        ? paiseToInr(e.suggested_limit_paise)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {e.is_watchlist && (
                        <button
                          onClick={() => setDrawerEntry(e)}
                          className="text-amber-700 hover:underline text-xs mr-2"
                          title="Open the watch-list action drawer"
                        >
                          Act ⚑
                        </button>
                      )}
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

      {drawerEntry && (
        <WatchlistDrawer
          entry={drawerEntry}
          onClose={() => setDrawerEntry(null)}
        />
      )}
    </div>
  );
}

function GuardrailsPanel({ c }: { c: ConcentrationSummary | null }) {
  if (!c) return null;
  return (
    <div className="card p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-sm font-semibold text-ink-900">
          Concentration guardrails
        </h3>
        <span
          className="text-[11px] text-ink-500"
          title="Herfindahl–Hirschman index over sector exposure shares; higher = more concentrated"
        >
          HHI {c.hhi.toFixed(2)} · caps: sector {Math.round(c.sector_cap * 100)}% ·
          single name {Math.round(c.single_name_cap * 100)}%
        </span>
      </div>
      <ul className="space-y-2">
        {c.sector_exposures.map((s) => (
          <li key={s.sector} className="flex items-center gap-3">
            <span className="text-xs text-ink-700 min-w-32">{s.sector}</span>
            <div className="flex-1 h-2 rounded-full bg-ink-100 overflow-hidden">
              <div
                className={clsx(
                  "h-full transition-all duration-700",
                  s.breach ? "bg-red-500" : "bg-brand-500",
                )}
                style={{ width: `${Math.min(100, s.share * 100)}%` }}
              />
            </div>
            <span
              className={clsx(
                "text-xs tabular-nums w-24 text-right",
                s.breach ? "text-red-700 font-medium" : "text-ink-600",
              )}
            >
              {paiseToInr(s.exposure_paise)} ({(s.share * 100).toFixed(0)}%)
            </span>
          </li>
        ))}
      </ul>
      {c.breaches.length > 0 ? (
        <div className="mt-3 space-y-1">
          {c.breaches.map((b) => (
            <div
              key={b}
              className="text-[11px] text-red-700 bg-red-50 border border-red-200 rounded-lg px-2.5 py-1.5"
            >
              ⚠ Guardrail breach: {b}
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-3 text-[11px] text-brand-700 bg-brand-50 border border-brand-200 rounded-lg px-2.5 py-1.5">
          ✓ All diversification guardrails within policy caps
        </div>
      )}
    </div>
  );
}

function VintagePanel({ cohorts }: { cohorts: VintageCohort[] }) {
  if (cohorts.length === 0) return null;
  return (
    <div className="card p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-sm font-semibold text-ink-900">Vintage cohorts</h3>
        <span className="text-[11px] text-ink-500">
          young ≠ unscorable — the inclusion proof
        </span>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-wider text-ink-500 border-b border-ink-100">
            <th className="py-1.5 font-medium">Firm age</th>
            <th className="py-1.5 font-medium text-right">Firms</th>
            <th className="py-1.5 font-medium text-right">Avg score</th>
            <th className="py-1.5 font-medium text-right">Approval</th>
            <th className="py-1.5 font-medium text-right">Avg PD</th>
          </tr>
        </thead>
        <tbody>
          {cohorts.map((v) => (
            <tr key={v.key} className="border-b border-ink-100 last:border-b-0">
              <td className="py-2 text-ink-800">{v.label}</td>
              <td className="py-2 text-right tabular-nums">{v.count}</td>
              <td className="py-2 text-right tabular-nums font-medium">
                {v.avg_score.toFixed(0)}
              </td>
              <td className="py-2 text-right tabular-nums">
                {(v.approval_rate * 100).toFixed(0)}%
              </td>
              <td className="py-2 text-right tabular-nums">
                {(v.avg_pd * 100).toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StressPanel() {
  const [presets, setPresets] = useState<StressScenario[]>([]);
  const [result, setResult] = useState<StressResult | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.stressPresets().then(setPresets).catch(() => {});
  }, []);

  function run(s: StressScenario) {
    setRunning(s.key);
    setError(null);
    api
      .runStress(s)
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setRunning(null));
  }

  if (presets.length === 0) return null;

  return (
    <section className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink-900">
            Stress test the book
          </h3>
          <p className="text-[11px] text-ink-500">
            Shocks every borrower's features, re-runs the full scorecard, and
            reports the band migration — live, nothing persisted.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {presets.map((s) => (
            <button
              key={s.key}
              onClick={() => run(s)}
              disabled={running !== null}
              className={clsx(
                "btn-ghost !py-1 !px-2.5 text-xs border rounded-lg",
                result?.scenario.key === s.key
                  ? "border-brand-400 bg-brand-50 text-brand-800"
                  : "border-ink-200",
                running === s.key && "opacity-60",
              )}
            >
              {running === s.key ? "Running…" : s.label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="mt-3 text-xs text-red-700">{error}</div>}

      {result && (
        <div className="mt-4 grid gap-5 lg:grid-cols-[auto_1fr]">
          <div className="flex flex-wrap gap-x-8 gap-y-3">
            <Kpi
              label="Avg score"
              value={`${result.avg_score_after.toFixed(0)}`}
              sub={`was ${result.avg_score_before.toFixed(0)}`}
              tone="warn"
            />
            <Kpi
              label="Band downgrades"
              value={`${result.downgraded}`}
              sub="of 30 firms"
              tone={result.downgraded > 8 ? "bad" : "warn"}
            />
            <Kpi
              label="Decisions worsened"
              value={`${result.decisions_worsened}`}
              sub="approve→refer/decline"
              tone={result.decisions_worsened > 8 ? "bad" : "warn"}
            />
            <Kpi
              label="Exposure at risk"
              value={paiseToInr(result.exposure_at_risk_paise)}
              sub="limits of worsened decisions"
              tone="bad"
            />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-1.5">
              Band migration · worst hit
            </div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {result.migrations.map((m) => (
                <span
                  key={`${m.from_band}${m.to_band}`}
                  className="pill bg-amber-50 text-amber-800 border border-amber-200 text-[10px]"
                >
                  {m.from_band} → {m.to_band}: {m.count}
                </span>
              ))}
              {result.migrations.length === 0 && (
                <span className="text-xs text-ink-500">No band movement.</span>
              )}
            </div>
            <ul className="text-xs text-ink-700 space-y-0.5">
              {result.worst_hit.slice(0, 4).map((w) => (
                <li key={w.gstin} className="flex items-center gap-2">
                  <span className="min-w-40 truncate">{w.trade_name}</span>
                  <span className="font-mono tabular-nums">
                    {w.score_before} → {w.score_after}
                  </span>
                  <span className="text-ink-500">
                    ({w.band_before}→{w.band_after}
                    {w.recommendation_before !== w.recommendation_after &&
                      `, ${w.recommendation_before}→${w.recommendation_after}`}
                    )
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}

const ACTION_LABEL: Record<WatchlistActionKind, string> = {
  ACKNOWLEDGE: "Acknowledge",
  REQUEST_REPULL: "Request fresh pull",
  SCHEDULE_REVIEW: "Schedule review",
};

function WatchlistDrawer({
  entry,
  onClose,
}: {
  entry: PortfolioEntry;
  onClose: () => void;
}) {
  const [history, setHistory] = useState<WatchlistAction[] | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<WatchlistActionKind | null>(null);

  function load() {
    api.watchlistActions(entry.gstin).then(setHistory).catch(() => setHistory([]));
  }
  useEffect(load, [entry.gstin]);

  function act(kind: WatchlistActionKind) {
    setBusy(kind);
    api
      .watchlistAction(entry.gstin, kind, note)
      .then(() => {
        setNote("");
        load();
      })
      .finally(() => setBusy(null));
  }

  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal>
      <div className="absolute inset-0 bg-ink-900/30" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl p-6 overflow-y-auto">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-ink-500">
              Watch-list actions
            </div>
            <h2 className="text-lg font-display font-semibold text-ink-900">
              {entry.trade_name}
            </h2>
            <div className="text-[11px] font-mono text-ink-500">{entry.gstin}</div>
          </div>
          <button
            onClick={onClose}
            className="btn-ghost !py-1 !px-2 text-sm border border-ink-200 rounded-lg"
          >
            ✕
          </button>
        </div>

        <div className="mt-4 rounded-xl border border-red-200 bg-red-50/50 p-3">
          <div className="text-[10px] uppercase tracking-wider text-red-700 mb-1">
            Why it's flagged
          </div>
          <div className="text-xs text-ink-800">{entry.watchlist_reason}</div>
          {entry.ews_flags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {entry.ews_flags.map((f, i) => (
                <span
                  key={i}
                  className="pill bg-red-50 text-red-700 border border-red-200 text-[9px]"
                >
                  ⚠ {f}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="mt-4">
          <label className="text-[10px] uppercase tracking-wider text-ink-500">
            Note (optional)
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="mt-1 w-full rounded-lg border border-ink-200 p-2 text-xs"
            placeholder="e.g. spoke to promoter, GST dues cleared last week"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            {(Object.keys(ACTION_LABEL) as WatchlistActionKind[]).map((k) => (
              <button
                key={k}
                onClick={() => act(k)}
                disabled={busy !== null}
                className="btn-ghost !py-1.5 !px-3 text-xs border border-ink-200 rounded-lg hover:border-brand-300"
              >
                {busy === k ? "Saving…" : ACTION_LABEL[k]}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-5">
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-2">
            Action history
          </div>
          {!history ? (
            <div className="text-xs text-ink-500">Loading…</div>
          ) : history.length === 0 ? (
            <div className="text-xs text-ink-500">
              No actions recorded yet for this borrower.
            </div>
          ) : (
            <ul className="space-y-2">
              {history.map((a) => (
                <li
                  key={a.action_id}
                  className="rounded-lg border border-ink-100 p-2.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-ink-900">
                      {ACTION_LABEL[a.action]}
                    </span>
                    <span className="text-[10px] text-ink-500">
                      {new Date(a.created_at).toLocaleString("en-IN")}
                    </span>
                  </div>
                  {a.note && <p className="mt-1 text-ink-600">{a.note}</p>}
                </li>
              ))}
            </ul>
          )}
        </div>

        <Link
          to={`/msme/${entry.gstin}`}
          className="mt-5 inline-block text-xs text-brand-700 hover:underline"
        >
          Open full health card →
        </Link>
      </aside>
    </div>
  );
}

function TrendChip({ trend }: { trend: string }) {
  const map: Record<string, { glyph: string; className: string; label: string }> = {
    IMPROVING: {
      glyph: "↑",
      className: "bg-brand-50 text-brand-700 border-brand-200",
      label: "up",
    },
    STABLE: {
      glyph: "→",
      className: "bg-ink-100 text-ink-600 border-ink-200",
      label: "flat",
    },
    DECLINING: {
      glyph: "↓",
      className: "bg-red-50 text-red-700 border-red-200",
      label: "down",
    },
    UNKNOWN: {
      glyph: "·",
      className: "bg-ink-50 text-ink-400 border-ink-100",
      label: "—",
    },
  };
  const t = map[trend] ?? map.UNKNOWN;
  return (
    <span
      className={
        "inline-flex items-center gap-0.5 rounded-md border px-1.5 py-0.5 text-[10px] " +
        t.className
      }
    >
      <span className="font-mono">{t.glyph}</span> {t.label}
    </span>
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
