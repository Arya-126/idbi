import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { api } from "../api";
import type { MsmeSummary } from "../types";

export default function LandingPage() {
  const [msmes, setMsmes] = useState<MsmeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listMsmes()
      .then(setMsmes)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-6 py-12">
      <Hero />
      <section className="mt-14">
        <div className="flex items-baseline justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-ink-900">
              Demo portfolio — pick an MSME
            </h2>
            <p className="text-sm text-ink-500">
              Each profile is stitched together from synthetic GST, AA, EPFO and UPI
              data. Scores update as underlying signals shift.
            </p>
          </div>
        </div>
        {error && (
          <div className="card p-4 border-red-200 bg-red-50 text-red-700 text-sm">
            Couldn't reach the backend at <code>/api</code>. Is <code>uvicorn</code>{" "}
            running on :8000? <br />
            <span className="opacity-70">{error}</span>
          </div>
        )}
        {!msmes && !error && <SkeletonGrid />}
        {msmes && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {msmes.map((m) => (
              <MsmeTile key={m.gstin} m={m} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Hero() {
  return (
    <section className="grid md:grid-cols-[1.4fr_1fr] gap-8 items-center">
      <div>
        <div className="inline-flex items-center gap-2 pill bg-brand-50 text-brand-700 border border-brand-200">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
          Track 03 · Financial Inclusion · Digital Lending
        </div>
        <h1 className="mt-4 text-3xl md:text-4xl font-display font-semibold tracking-tight text-ink-900 leading-tight">
          Underwrite the{" "}
          <span className="text-brand-600">credit-invisible</span>{" "}
          MSME.
        </h1>
        <p className="mt-3 text-ink-600 max-w-2xl">
          A multidimensional financial health score for New-to-Credit and
          New-to-Bank enterprises, built on consented alternate data —{" "}
          GST returns, Account Aggregator bank data, EPFO payroll and UPI
          transaction signals. Every factor is explainable; every decision is
          auditable.
        </p>
        <div className="mt-6 flex flex-wrap gap-2 text-xs">
          {[
            "6 scored dimensions",
            "Factor-level explainability",
            "Near real-time",
            "ULI / OCEN / AA-native",
            "NTC / NTB inclusion",
          ].map((t) => (
            <span key={t} className="pill bg-white border border-ink-200 text-ink-600">
              {t}
            </span>
          ))}
        </div>
      </div>
      <HeroCard />
    </section>
  );
}

function HeroCard() {
  return (
    <div className="card p-6 relative overflow-hidden">
      <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-brand-100 blur-3xl opacity-70" />
      <div className="relative">
        <div className="text-[11px] uppercase tracking-wider text-ink-500">
          What one card holds
        </div>
        <ul className="mt-3 space-y-2 text-sm">
          {[
            ["GST", "24 months of returns · filing discipline"],
            ["AA", "12 months of bank txns · DSCR proxy"],
            ["EPFO", "Headcount trend · salary regularity"],
            ["UPI", "Volume · breadth · P2M share"],
          ].map(([src, blurb]) => (
            <li key={src} className="flex items-start gap-3">
              <span className="mt-0.5 pill bg-brand-50 text-brand-700 border border-brand-200 min-w-12 justify-center">
                {src}
              </span>
              <span className="text-ink-600">{blurb}</span>
            </li>
          ))}
        </ul>
        <div className="mt-5 border-t border-ink-100 pt-4 text-xs text-ink-500">
          → Composite 0–1000 · Band A/B/C/D · Approve · Refer · Decline
        </div>
      </div>
    </div>
  );
}

function MsmeTile({ m }: { m: MsmeSummary }) {
  return (
    <Link
      to={`/consent/${m.gstin}`}
      className={clsx(
        "card p-5 group hover:shadow-pop hover:-translate-y-0.5 transition",
        "border-ink-100 hover:border-brand-200",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-ink-900 group-hover:text-brand-700">
            {m.trade_name}
          </div>
          <div className="text-xs text-ink-500 mt-0.5">
            {m.sector} · {m.sub_sector}
          </div>
        </div>
        <span
          className={clsx(
            "pill border",
            m.msme_category === "MICRO"
              ? "bg-ink-50 border-ink-200 text-ink-600"
              : m.msme_category === "SMALL"
                ? "bg-brand-50 border-brand-200 text-brand-700"
                : "bg-emerald-50 border-emerald-200 text-emerald-700",
          )}
        >
          {m.msme_category}
        </span>
      </div>
      <p className="mt-3 text-sm text-ink-600">{m.tagline}</p>
      <div className="mt-4 flex items-center justify-between text-xs">
        <span className="text-ink-500">📍 {m.registered_city}</span>
        <span className="text-brand-600 font-medium group-hover:translate-x-0.5 transition">
          Score this MSME →
        </span>
      </div>
    </Link>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="card p-5 animate-pulse">
          <div className="h-4 w-1/2 bg-ink-100 rounded" />
          <div className="h-3 w-2/3 bg-ink-100 rounded mt-2" />
          <div className="h-3 w-full bg-ink-100 rounded mt-4" />
          <div className="h-3 w-4/5 bg-ink-100 rounded mt-1.5" />
        </div>
      ))}
    </div>
  );
}
