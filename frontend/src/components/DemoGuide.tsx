import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import clsx from "clsx";
import { api } from "../api";

// Scripted judge tour: 9 steps, each a deep link + talking point + an
// "if asked" honesty note. Pure frontend; state in localStorage so the
// drawer survives navigation. Toggle via the floating button or ?demo=1.

interface Step {
  title: string;
  route: (gstin: string | null) => string;
  say: string;
  ifAsked: string;
}

const STEPS: Step[] = [
  {
    title: "Landing — the problem",
    route: () => "/",
    say: "Banks reject viable MSMEs they cannot see. Five synthetic personas cover the spectrum — including an NTC startup with zero bureau history.",
    ifAsked: "All data is synthetic and deterministic per GSTIN; no real businesses.",
  },
  {
    title: "Consent — AA-style, enforced",
    route: (g) => (g ? `/consent/${g}` : "/"),
    say: "Source-by-source consent. Uncheck EPFO and that dimension is never fetched and greys out — scope is enforced, not decorative.",
    ifAsked: "The per-source reveal animation is staged; the data pull itself is one real consented request.",
  },
  {
    title: "Health Card — six dimensions",
    route: (g) => (g ? `/msme/${g}` : "/portfolio"),
    say: "Composite 0-1000 from six weighted dimensions, every factor coded (adverse-action style). Note the 'no bureau file' chip — that firm is fully scored anyway.",
    ifAsked: "Weights are policy choices in one dict; bands map to approve/refer/decline plus hard gates on bounces/DSCR.",
  },
  {
    title: "What-if + ML second opinion",
    route: (g) => (g ? `/msme/${g}` : "/portfolio"),
    say: "Move a lever — score, band, decision and ML PD respond live. The ML is calibrated, monotonicity-constrained, and advisory-only: the rulebook decides.",
    ifAsked: "Trained on 500 synthetic firms through the full production feature pipeline; AUC/Brier on a 20% holdout are on the panel. No real-world validity claimed.",
  },
  {
    title: "Borrower view",
    route: (g) => (g ? `/msme/${g}` : "/portfolio"),
    say: "Same card, borrower language: what the band means, a computed path to the next band, data rights.",
    ifAsked: "Recommendation uplifts are computed by re-running the scorecard with the improved behaviour, not hardcoded.",
  },
  {
    title: "Apply → Sanction + KFS",
    route: (g) => (g ? `/msme/${g}` : "/portfolio"),
    say: "Approve flows straight through to a sanction letter with a Key Fact Statement — APR, total cost of credit, cooling-off — per the RBI Digital Lending Guidelines.",
    ifAsked: "EMI/fee math is real; covenants are static demo text.",
  },
  {
    title: "Portfolio — quality + guardrails",
    route: () => "/portfolio",
    say: "30-firm book: band mix, EWS flags, concentration guardrails with live breaches, vintage cohorts, an 'ML disagrees' review queue, and a one-click stress test that re-scores everyone.",
    ifAsked: "Trend column is reconstructed from windowed re-scoring of today's data, not stored history — we say so.",
  },
  {
    title: "Impact — inclusion evidence",
    route: () => "/impact",
    say: "Versus a bureau-only lender: more firms served AND a lower-PD approved book — computed from the same 30 firms, not estimated.",
    ifAsked: "The traditional lender is a 4-rule heuristic (NTC / vintage / scale / entity type); its rules are printed at the bottom of the page.",
  },
  {
    title: "Rails + governance",
    route: () => "/ecosystem",
    say: "ULI/OCEN wire timelines carry real record counts and the real consent handle. Consent log shows every grant, every access, revocation live, downloadable ReBIT-style artefact — and the compliance page grades ourselves honestly.",
    ifAsked: "ULI/OCEN are simulators — protocol seams ready, no live integration claimed. Latencies are the one synthetic element of the timeline.",
  },
];

export default function DemoGuide() {
  const loc = useLocation();
  const [open, setOpen] = useState<boolean>(() => {
    if (new URLSearchParams(window.location.search).has("demo")) return true;
    return localStorage.getItem("demoGuideOpen") === "1";
  });
  const [step, setStep] = useState<number>(() =>
    Number(localStorage.getItem("demoGuideStep") || 0),
  );
  const [firstGstin, setFirstGstin] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem("demoGuideOpen", open ? "1" : "0");
  }, [open]);
  useEffect(() => {
    localStorage.setItem("demoGuideStep", String(step));
  }, [step]);
  useEffect(() => {
    api
      .listMsmes()
      .then((list) => setFirstGstin(list[1]?.gstin ?? list[0]?.gstin ?? null))
      .catch(() => {});
  }, []);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-30 rounded-full bg-brand-600 text-white shadow-lg px-4 py-2 text-xs font-medium hover:bg-brand-700 print:hidden"
        title="Open the scripted judge tour"
      >
        ▶ Demo tour
      </button>
    );
  }

  const s = STEPS[step];
  const target = s.route(firstGstin);
  const onTarget = loc.pathname === target.split("?")[0];

  return (
    <aside className="fixed bottom-4 right-4 z-30 w-96 max-w-[calc(100vw-2rem)] card shadow-2xl border-brand-200 p-4 print:hidden">
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider text-ink-500">
          Demo tour · step {step + 1} of {STEPS.length}
        </div>
        <button
          onClick={() => setOpen(false)}
          className="text-ink-400 hover:text-ink-700 text-sm"
        >
          ✕
        </button>
      </div>

      <div className="mt-1 flex gap-1">
        {STEPS.map((_, i) => (
          <button
            key={i}
            onClick={() => setStep(i)}
            className={clsx(
              "h-1.5 flex-1 rounded-full transition",
              i === step ? "bg-brand-600" : i < step ? "bg-brand-300" : "bg-ink-100",
            )}
            title={STEPS[i].title}
          />
        ))}
      </div>

      <h3 className="mt-3 text-sm font-semibold text-ink-900">{s.title}</h3>
      <p className="mt-1.5 text-xs text-ink-700 leading-snug">{s.say}</p>
      <p className="mt-2 text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5 leading-snug">
        <span className="font-semibold">If asked:</span> {s.ifAsked}
      </p>

      <div className="mt-3 flex items-center justify-between">
        <button
          onClick={() => setStep(Math.max(0, step - 1))}
          disabled={step === 0}
          className="btn-ghost !py-1 !px-2.5 text-xs border border-ink-200 rounded-lg disabled:opacity-40"
        >
          ← Back
        </button>
        <Link
          to={target}
          className={clsx(
            "text-xs px-3 py-1 rounded-lg border",
            onTarget
              ? "border-ink-200 text-ink-500"
              : "border-brand-300 bg-brand-50 text-brand-800 font-medium",
          )}
        >
          {onTarget ? "You're here" : "Go to this step →"}
        </Link>
        <button
          onClick={() => setStep(Math.min(STEPS.length - 1, step + 1))}
          disabled={step === STEPS.length - 1}
          className="btn-ghost !py-1 !px-2.5 text-xs border border-ink-200 rounded-lg disabled:opacity-40"
        >
          Next →
        </button>
      </div>
    </aside>
  );
}
