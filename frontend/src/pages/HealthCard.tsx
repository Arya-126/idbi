import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
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

type View = "officer" | "borrower";

export default function HealthCardPage() {
  const { gstin } = useParams();
  const [card, setCard] = useState<HealthCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("officer");

  useEffect(() => {
    if (!gstin) return;
    setCard(null);
    const consent = storedConsent(gstin);
    api
      .healthCard(gstin, consent)
      .then(setCard)
      .catch((e) => {
        if (consent && String(e).startsWith("Error: 403")) {
          clearConsent(gstin);
          api
            .healthCard(gstin)
            .then(setCard)
            .catch((e2) => setError(String(e2)));
        } else {
          setError(String(e));
        }
      });
  }, [gstin]);

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
      <div className="flex justify-between items-center print:hidden">
        <ViewToggle view={view} onChange={setView} />
        <button
          onClick={() => window.print()}
          className="btn-ghost !py-1 !px-2.5 text-xs border border-ink-200 rounded-lg"
        >
          ⇩ Print / Save PDF
        </button>
      </div>
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
      {view === "borrower" && (
        <RecommendationsPanel items={card.improvement_recommendations} />
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
      <p className="mt-4 text-[11px] text-ink-500">
        Score built only from data you consented to share (GST, bank, EPFO,
        UPI). You can revoke consent at any time.
      </p>
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
