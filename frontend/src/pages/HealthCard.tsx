import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import type { HealthCard } from "../types";
import HealthHeader from "../components/HealthHeader";
import DimensionRadar from "../components/DimensionRadar";
import DimensionCard from "../components/DimensionCard";
import DecisionPanel from "../components/DecisionPanel";
import StrengthsRisks from "../components/StrengthsRisks";
import DataFreshness from "../components/DataFreshness";

export default function HealthCardPage() {
  const { gstin } = useParams();
  const [card, setCard] = useState<HealthCard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!gstin) return;
    setCard(null);
    api
      .healthCard(gstin)
      .then(setCard)
      .catch((e) => setError(String(e)));
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
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
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
        </section>
        <DecisionPanel decision={card.decision} band={card.risk_band} />
      </div>

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
