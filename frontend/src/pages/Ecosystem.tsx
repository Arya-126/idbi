import { useState } from "react";
import clsx from "clsx";
import { api } from "../api";
import type { OcenLoanResponse, UliActor, UliEvent, UliPullResponse } from "../types";
import { paiseToInr } from "../utils/format";

type Tab = "uli" | "ocen";

const DEMO_GSTINS = [
  { gstin: "27AAKCS1234A1Z5", name: "Sharma Textiles" },
  { gstin: "29AAKPB4321B1Z8", name: "Kirana Bazaar" },
  { gstin: "09AAFPK5678C1Z2", name: "Kumar Enterprises" },
  { gstin: "07AAJCN2468D1Z0", name: "NewGen Tech (NTC)" },
  { gstin: "24AAMPH9876E1Z7", name: "Meera Handicrafts" },
];

export default function EcosystemPage() {
  const [tab, setTab] = useState<Tab>("uli");
  const [gstin, setGstin] = useState(DEMO_GSTINS[0].gstin);
  const [amount, setAmount] = useState("15");
  const [tenor, setTenor] = useState("24");
  const [pull, setPull] = useState<UliPullResponse | null>(null);
  const [loan, setLoan] = useState<OcenLoanResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      if (tab === "uli") {
        setPull(null);
        setPull(await api.uliPull(gstin));
      } else {
        setLoan(null);
        const amt_paise = Math.round(parseFloat(amount) * 1_00_000_00);
        setLoan(await api.ocenLoan(gstin, amt_paise, parseInt(tenor)));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 space-y-6">
      <header>
        <div className="text-[11px] uppercase tracking-wider text-ink-500">
          Ecosystem integration
        </div>
        <h1 className="mt-1 text-2xl font-display font-semibold text-ink-900">
          ULI · OCEN simulated flow
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          Play back what happens when a Loan Service Provider (LSP) calls this
          bank via RBI's Unified Lending Interface or the OCEN loan protocol.
          Real integrations use these exact hops; the wire is mocked, the
          contracts aren't.
        </p>
      </header>

      <section className="card p-6 space-y-4">
        <div className="flex items-center gap-1 rounded-xl border border-ink-200 bg-ink-50/60 p-1 text-xs w-fit">
          {[
            ["uli", "ULI · pull health card"],
            ["ocen", "OCEN · loan request"],
          ].map(([k, label]) => (
            <button
              key={k}
              onClick={() => setTab(k as Tab)}
              className={clsx(
                "px-3 py-1.5 rounded-lg transition",
                tab === k ? "bg-white shadow-sm text-ink-900 font-medium" : "text-ink-500 hover:text-ink-800",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="grid gap-3 md:grid-cols-4 items-end">
          <label className="text-xs col-span-2">
            <div className="text-[10px] uppercase text-ink-500 tracking-wider mb-1">GSTIN</div>
            <select
              value={gstin}
              onChange={(e) => setGstin(e.target.value)}
              className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm"
            >
              {DEMO_GSTINS.map((m) => (
                <option key={m.gstin} value={m.gstin}>
                  {m.name} — {m.gstin}
                </option>
              ))}
            </select>
          </label>
          {tab === "ocen" && (
            <>
              <label className="text-xs">
                <div className="text-[10px] uppercase text-ink-500 tracking-wider mb-1">Amount (₹L)</div>
                <input
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm"
                />
              </label>
              <label className="text-xs">
                <div className="text-[10px] uppercase text-ink-500 tracking-wider mb-1">Tenor (mo)</div>
                <input
                  value={tenor}
                  onChange={(e) => setTenor(e.target.value)}
                  className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm"
                />
              </label>
            </>
          )}
        </div>

        <button onClick={run} disabled={busy} className="btn-primary">
          {busy
            ? "Simulating…"
            : tab === "uli"
              ? "Simulate ULI pull →"
              : "Simulate OCEN loan request →"}
        </button>
        {error && (
          <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded p-2">
            {error}
          </div>
        )}
      </section>

      {tab === "uli" && pull && (
        <section className="card p-6">
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-sm font-semibold text-ink-900">Trace</h2>
            <span className="text-[11px] text-ink-500 font-mono">
              {pull.trace_id} · {pull.total_latency_ms} ms total
            </span>
          </div>
          <Timeline events={pull.events} />
          {pull.health_card && (
            <div className="mt-4 rounded-xl border border-brand-200 bg-brand-50/40 p-3 text-xs">
              <div className="text-[10px] uppercase text-brand-700 tracking-wider">
                Returned health card
              </div>
              <div className="mt-1 flex items-baseline gap-3">
                <span className="text-lg font-display font-semibold text-ink-900">
                  {pull.health_card.composite_score}
                </span>
                <span className="text-ink-500">
                  Band {pull.health_card.risk_band} · PD{" "}
                  {(pull.health_card.ml_assessment.probability_of_default * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          )}
        </section>
      )}

      {tab === "ocen" && loan && (
        <section className="card p-6">
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-sm font-semibold text-ink-900">Trace</h2>
            <span className="text-[11px] text-ink-500 font-mono">{loan.trace_id}</span>
          </div>
          <Timeline events={loan.events} />
          <div
            className={clsx(
              "mt-4 rounded-xl border p-3 text-xs",
              loan.decision === "SANCTIONED"
                ? "border-brand-200 bg-brand-50/50"
                : loan.decision === "REFERRED"
                  ? "border-amber-200 bg-amber-50/50"
                  : "border-red-200 bg-red-50/50",
            )}
          >
            <div className="text-[10px] uppercase tracking-wider text-ink-500">
              Decision
            </div>
            <div className="mt-1 flex items-baseline gap-3">
              <span className="text-lg font-display font-semibold text-ink-900">
                {loan.decision}
              </span>
              {loan.decision === "SANCTIONED" && (
                <span className="text-ink-600">
                  {paiseToInr(loan.sanctioned_amount_paise)} · {loan.tenor_months} mo · {loan.roi_pct}%
                </span>
              )}
              {loan.application_id && (
                <span className="text-[10px] font-mono text-ink-500">
                  {loan.application_id}
                </span>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

const ACTOR_STYLE: Record<UliActor, string> = {
  LSP: "bg-violet-100 text-violet-700",
  OCEN: "bg-fuchsia-100 text-fuchsia-700",
  ULI: "bg-brand-100 text-brand-700",
  BANK: "bg-emerald-100 text-emerald-700",
  AA: "bg-sky-100 text-sky-700",
  FIP: "bg-amber-100 text-amber-700",
  BORROWER: "bg-ink-100 text-ink-700",
};

function Timeline({ events }: { events: UliEvent[] }) {
  return (
    <ol className="space-y-2">
      {events.map((e) => (
        <li
          key={e.step}
          className={clsx(
            "grid grid-cols-[auto_auto_1fr_auto] items-center gap-3 rounded-lg border border-ink-100 p-2.5 text-xs",
            !e.ok && "border-red-200 bg-red-50/40",
          )}
        >
          <span className="w-6 text-center text-ink-400 font-mono">{e.step}</span>
          <span
            className={
              "pill text-[10px] " + (ACTOR_STYLE[e.actor] ?? "bg-ink-100 text-ink-700")
            }
          >
            {e.actor}
          </span>
          <div className="min-w-0">
            <div className="font-semibold text-ink-900 truncate">{e.action}</div>
            <div className="text-[11px] text-ink-500">{e.detail}</div>
          </div>
          <span className="text-[10px] font-mono text-ink-500 shrink-0">
            {e.latency_ms}ms
          </span>
        </li>
      ))}
    </ol>
  );
}
