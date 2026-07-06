import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import clsx from "clsx";
import { api, clearConsent, storedConsent } from "../api";
import type { HealthCard } from "../types";
import HealthHeader from "../components/HealthHeader";
import DimensionRadar from "../components/DimensionRadar";
import DimensionCard from "../components/DimensionCard";
import DecisionPanel from "../components/DecisionPanel";
import StrengthsRisks from "../components/StrengthsRisks";
import DataFreshness from "../components/DataFreshness";
import MlPanel from "../components/MlPanel";
import RecommendationsPanel from "../components/RecommendationsPanel";
import ScoreHistoryChart from "../components/ScoreHistoryChart";
import ApplyButton from "../components/ApplyButton";
import WhatIfPanel from "../components/WhatIfPanel";

type View = "officer" | "borrower";

// Pull the human-readable detail out of a `403 Forbidden: {"detail":"…"}` error.
function errorDetail(e: unknown): string {
  const m = String(e).match(/"detail"\s*:\s*"([^"]+)"/);
  return m ? m[1] : String(e);
}

export default function HealthCardPage() {
  const { gstin } = useParams();
  const [card, setCard] = useState<HealthCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 403 from a revoked/expired/invalid consent handle — surfaced, not retried,
  // so the demo can show enforcement actually blocking access.
  const [blocked, setBlocked] = useState<string | null>(null);
  const [view, setView] = useState<View>("officer");
  // Simulated fresh pull N months out (0 = live pull today).
  const [simMonths, setSimMonths] = useState(0);

  const fetchCard = useCallback(
    (consent?: string, sim = 0) => {
      if (!gstin) return;
      setCard(null);
      setBlocked(null);
      setError(null);
      api
        .healthCard(gstin, consent, sim)
        .then(setCard)
        .catch((e) => {
          if (consent && String(e).startsWith("Error: 403")) {
            clearConsent(gstin);
            setBlocked(errorDetail(e));
          } else {
            setError(String(e));
          }
        });
    },
    [gstin],
  );

  useEffect(() => {
    if (!gstin) return;
    setSimMonths(0);
    fetchCard(storedConsent(gstin));
  }, [gstin, fetchCard]);

  function simulatePull(n: number) {
    if (!gstin) return;
    setSimMonths(n);
    fetchCard(storedConsent(gstin), n);
  }

  if (blocked && gstin) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-14">
        <div className="card p-6 border-red-200 bg-red-50">
          <h1 className="text-sm font-semibold text-red-800">
            Data access blocked — consent not valid
          </h1>
          <p className="mt-2 text-sm text-red-700">{blocked}</p>
          <p className="mt-3 text-xs text-ink-600">
            Every data pull is validated against the consent registry. A
            revoked, expired or unknown handle is rejected with HTTP 403 —
            the borrower stays in control of their data.
          </p>
          <div className="mt-4 flex gap-3">
            <Link
              to={`/consent/${gstin}`}
              className="btn-primary !py-1.5 !px-3 text-xs rounded-lg"
            >
              Grant consent again
            </Link>
            <button
              onClick={() => fetchCard(undefined)}
              className="btn-ghost !py-1.5 !px-3 text-xs border border-ink-200 rounded-lg"
              title="Demo fallback: the registry treats a missing handle as consent on file"
            >
              Use consent on file (demo)
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-14">
        <div className="card p-4 border-red-200 bg-red-50 text-red-700 text-sm">
          Couldn't fetch health card. {error}
        </div>
      </div>
    );
  }

  if (!card) return <CardSkeleton />;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6" id="printable-card">
      <div className="flex flex-wrap justify-between items-center gap-2 print:hidden">
        <ViewToggle view={view} onChange={setView} />
        <div className="flex items-center gap-2">
          <div
            className="flex items-center gap-1 rounded-xl border border-ink-200 bg-white p-1 text-xs"
            title="Regenerates the consented data as of a later month and re-scores — demos on-demand assessment despite deterministic demo data. Each pull records an observed history point."
          >
            <span className="px-1.5 text-[10px] uppercase tracking-wider text-ink-500">
              Pull
            </span>
            {[0, 1, 2, 3].map((n) => (
              <button
                key={n}
                onClick={() => simulatePull(n)}
                className={clsx(
                  "px-2 py-1 rounded-lg transition",
                  simMonths === n
                    ? "bg-brand-600 text-white"
                    : "text-ink-600 hover:bg-ink-50",
                )}
              >
                {n === 0 ? "today" : `+${n} mo`}
              </button>
            ))}
          </div>
          <button
            onClick={() => window.print()}
            className="btn-ghost !py-1 !px-2.5 text-xs border border-ink-200 rounded-lg"
          >
            ⇩ Print / Save PDF
          </button>
        </div>
      </div>
      {simMonths > 0 && (
        <div className="rounded-xl border border-sky-200 bg-sky-50/70 px-4 py-2 text-xs text-sky-800 print:hidden">
          Simulated fresh pull {simMonths} month{simMonths > 1 ? "s" : ""} from
          now — synthetic data regenerated at the later anchor, full scorecard
          + ML re-run. The solid dot on the history chart is this pull.
        </div>
      )}
      <HealthHeader card={card} />
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <section className="card p-6">
          <div className="flex items-baseline justify-between mb-2">
            <h2 className="text-sm font-semibold text-ink-900">
              Dimension breakdown
            </h2>
            <span className="text-[11px] text-ink-500">
              Weighted composite of 6 dimensions
            </span>
          </div>
          <DimensionRadar dimensions={card.dimensions} />
          {card.score_history.length > 0 && (
            <div className="mt-6 border-t border-ink-100 pt-4">
              <ScoreHistoryChart points={card.score_history} />
            </div>
          )}
        </section>
        {view === "officer" ? (
          <DecisionPanel
            decision={card.decision}
            band={card.risk_band}
            extraTail={
              gstin && card.decision.recommendation !== "DECLINE" ? (
                <ApplyButton gstin={gstin} />
              ) : null
            }
          />
        ) : (
          <BorrowerPanel card={card} />
        )}
      </div>

      {view === "officer" && <MlPanel ml={card.ml_assessment} />}
      {view === "officer" && gstin && <WhatIfPanel gstin={gstin} />}
      {view === "borrower" && (
        <RecommendationsPanel
          items={card.improvement_recommendations}
          path={card.path_to_next_band}
        />
      )}

      <StrengthsRisks
        strengths={card.top_strengths}
        risks={card.top_risks}
      />

      <section>
        <h2 className="text-sm font-semibold text-ink-900 mb-3">
          Why each dimension scored what it did
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {card.dimensions.map((d) => (
            <DimensionCard key={d.key} dim={d} />
          ))}
        </div>
      </section>

      <DataFreshness card={card} />
    </div>
  );
}

function ViewToggle({
  view,
  onChange,
}: {
  view: View;
  onChange: (v: View) => void;
}) {
  return (
    <div className="flex items-center gap-1 rounded-xl border border-ink-200 bg-white p-1 text-xs">
      {(
        [
          ["officer", "Credit officer view"],
          ["borrower", "Borrower view"],
        ] as const
      ).map(([k, label]) => (
        <button
          key={k}
          onClick={() => onChange(k)}
          className={clsx(
            "px-2.5 py-1 rounded-lg transition",
            view === k
              ? "bg-brand-600 text-white"
              : "text-ink-600 hover:bg-ink-50",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

const BAND_PLAIN: Record<string, string> = {
  A: "Your business signals look strong — you would typically qualify for credit on good terms.",
  B: "Your business signals are sound — you would typically qualify for credit at standard terms.",
  C: "Your profile is borderline — a lender would likely review it manually before deciding.",
  D: "Your current signals would make credit difficult — the points below show what to improve.",
};

function BorrowerPanel({ card }: { card: HealthCard }) {
  return (
    <section className="card p-6">
      <h2 className="text-sm font-semibold text-ink-900">
        What this means for your business
      </h2>
      <p className="mt-2 text-sm text-ink-700">{BAND_PLAIN[card.risk_band]}</p>
      <div className="mt-4 rounded-xl border border-ink-100 bg-ink-50/40 p-3">
        <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-1.5">
          Your data rights
        </div>
        <ul className="space-y-1 text-[11px] text-ink-600">
          <li>
            ✓ Score built only from sources you chose to share — withhold one
            and that dimension is simply not scored.
          </li>
          <li>
            ✓ You can revoke consent at any time from the{" "}
            <Link to="/consent-log" className="text-brand-700 underline">
              consent log
            </Link>{" "}
            — further data access is blocked immediately.
          </li>
          <li>
            ✓ Every access is recorded in an audit trail, and your consent
            artefact is downloadable — data use is purpose-limited and
            time-bound.
          </li>
        </ul>
      </div>
    </section>
  );
}

function CardSkeleton() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      <div className="card p-6 animate-pulse">
        <div className="h-6 w-1/3 bg-ink-100 rounded" />
        <div className="h-3 w-1/2 bg-ink-100 rounded mt-2" />
        <div className="h-32 w-full bg-ink-100 rounded mt-6" />
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="card p-6 h-64 bg-white animate-pulse" />
        <div className="card p-6 h-64 bg-white animate-pulse" />
      </div>
    </div>
  );
}
