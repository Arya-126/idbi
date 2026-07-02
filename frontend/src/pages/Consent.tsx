import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import clsx from "clsx";
import { api } from "../api";
import type { ConsentSource } from "../types";

const SOURCES: {
  key: ConsentSource;
  label: string;
  blurb: string;
  icon: string;
}[] = [
  {
    key: "GST",
    label: "GST Returns",
    blurb: "GSTR-1 & GSTR-3B filings, last 24 months",
    icon: "🧾",
  },
  {
    key: "AA",
    label: "Bank Statements (Account Aggregator)",
    blurb: "Current / savings txns via consented AA flow",
    icon: "🏦",
  },
  {
    key: "EPFO",
    label: "EPFO Payroll",
    blurb: "Employer contributions, headcount trend",
    icon: "👥",
  },
  {
    key: "UPI",
    label: "UPI Transaction Signal",
    blurb: "Merchant UPI receipts, customer breadth",
    icon: "⚡",
  },
];

type Stage =
  | "PROMPT"
  | "REQUESTING"
  | "GRANTED"
  | "FETCHING"
  | "READY"
  | "ERROR";

export default function ConsentPage() {
  const { gstin } = useParams();
  const navigate = useNavigate();
  const [stage, setStage] = useState<Stage>("PROMPT");
  const [chosen, setChosen] = useState<Set<ConsentSource>>(
    new Set(SOURCES.map((s) => s.key)),
  );
  const [fetchedSources, setFetchedSources] = useState<Set<ConsentSource>>(
    new Set(),
  );
  const [error, setError] = useState<string | null>(null);

  function toggle(key: ConsentSource) {
    const next = new Set(chosen);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setChosen(next);
  }

  async function grant() {
    if (!gstin) return;
    setStage("REQUESTING");
    try {
      await api.requestConsent(gstin, Array.from(chosen));
      setStage("GRANTED");
      await sleep(600);
      setStage("FETCHING");
      // Simulated per-source pull for demo texture
      for (const s of SOURCES) {
        if (chosen.has(s.key)) {
          await sleep(500 + Math.random() * 400);
          setFetchedSources((cur) => new Set(cur).add(s.key));
        }
      }
      setStage("READY");
      await sleep(500);
      navigate(`/msme/${gstin}`);
    } catch (e) {
      setError(String(e));
      setStage("ERROR");
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-14">
      <div className="mb-8">
        <div className="text-[11px] uppercase tracking-wider text-ink-500">
          Step 1 of 2 — Data access
        </div>
        <h1 className="mt-1 text-2xl font-display font-semibold text-ink-900">
          Grant consent to score this MSME
        </h1>
        <p className="mt-2 text-sm text-ink-600">
          Data is pulled via consent-first rails (Account Aggregator, GSTN API,
          EPFO extract, UPI acquirer feed). In production the borrower approves
          in-app; here we simulate that approval instantly.
        </p>
      </div>

      <div className="card p-2">
        {SOURCES.map((s) => (
          <SourceRow
            key={s.key}
            source={s}
            checked={chosen.has(s.key)}
            fetched={fetchedSources.has(s.key)}
            stage={stage}
            onToggle={() => toggle(s.key)}
          />
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between gap-4">
        <div className="text-xs text-ink-500">
          Consent handle expires in 30 days. Revocable at any time by the
          borrower.
        </div>
        <button
          onClick={grant}
          disabled={stage !== "PROMPT" || chosen.size === 0}
          className={clsx(
            "btn-primary",
            stage !== "PROMPT" && "opacity-70 cursor-not-allowed",
          )}
        >
          {stage === "PROMPT" && "Grant consent & fetch data"}
          {stage === "REQUESTING" && "Requesting consent…"}
          {stage === "GRANTED" && "Consent granted ✓"}
          {stage === "FETCHING" && "Pulling data…"}
          {stage === "READY" && "Opening health card…"}
          {stage === "ERROR" && "Retry"}
        </button>
      </div>

      {error && (
        <div className="mt-4 card p-3 border-red-200 bg-red-50 text-red-700 text-sm">
          {error}
        </div>
      )}
    </div>
  );
}

function SourceRow({
  source,
  checked,
  fetched,
  stage,
  onToggle,
}: {
  source: (typeof SOURCES)[number];
  checked: boolean;
  fetched: boolean;
  stage: Stage;
  onToggle: () => void;
}) {
  const active = stage === "FETCHING" && checked && !fetched;
  return (
    <button
      type="button"
      onClick={stage === "PROMPT" ? onToggle : undefined}
      className={clsx(
        "w-full flex items-center gap-4 p-4 rounded-xl text-left",
        "transition",
        checked ? "bg-brand-50/60" : "hover:bg-ink-50",
        stage !== "PROMPT" && "cursor-default",
      )}
    >
      <div className="text-2xl">{source.icon}</div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-ink-900">{source.label}</div>
        <div className="text-xs text-ink-500 truncate">{source.blurb}</div>
      </div>
      <div className="text-xs">
        {stage === "PROMPT" ? (
          <span
            className={clsx(
              "pill border",
              checked
                ? "bg-brand-600 text-white border-brand-600"
                : "bg-white text-ink-500 border-ink-200",
            )}
          >
            {checked ? "Included" : "Excluded"}
          </span>
        ) : !checked ? (
          <span className="pill bg-ink-100 text-ink-500 border border-ink-200">
            Skipped
          </span>
        ) : fetched ? (
          <span className="pill bg-emerald-100 text-emerald-700 border border-emerald-200">
            ✓ Fetched
          </span>
        ) : active ? (
          <span className="pill bg-brand-100 text-brand-700 border border-brand-200">
            <span className="inline-block h-2 w-2 rounded-full bg-brand-500 animate-pulse mr-1" />
            Fetching…
          </span>
        ) : (
          <span className="pill bg-ink-50 text-ink-500 border border-ink-200">
            Queued
          </span>
        )}
      </div>
    </button>
  );
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
