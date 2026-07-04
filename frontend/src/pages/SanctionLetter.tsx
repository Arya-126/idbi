import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import type { LoanApplication, SanctionLetter } from "../types";
import { paiseToInr } from "../utils/format";

export default function SanctionLetterPage() {
  const { applicationId } = useParams();
  const [app, setApp] = useState<LoanApplication | null>(null);
  const [letter, setLetter] = useState<SanctionLetter | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!applicationId) return;
    api
      .getApplication(applicationId)
      .then(async (a) => {
        setApp(a);
        if (a.status === "SANCTIONED") {
          try {
            setLetter(await api.sanctionLetter(a.application_id));
          } catch (e) {
            setError(String(e));
          }
        }
      })
      .catch((e) => setError(String(e)));
  }, [applicationId]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-14 card p-4 border-red-200 bg-red-50 text-red-700 text-sm">
        {error}
      </div>
    );
  }

  if (!app) return <div className="mx-auto max-w-4xl px-6 py-8 text-sm text-ink-500">Loading application…</div>;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 space-y-6" id="printable-card">
      <div className="flex items-baseline justify-between print:hidden">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-ink-500">
            Application {app.application_id}
          </div>
          <h1 className="text-2xl font-display font-semibold text-ink-900">
            {app.status === "SANCTIONED"
              ? "Sanction Letter"
              : app.status === "UNDER_REVIEW"
                ? "Under Review"
                : "Rejected"}
          </h1>
        </div>
        {letter && (
          <button
            onClick={() => window.print()}
            className="btn-primary"
          >
            ⇩ Print / Save PDF
          </button>
        )}
      </div>

      {app.status !== "SANCTIONED" && (
        <div className="card p-6">
          <div
            className={
              "text-sm font-semibold " +
              (app.status === "UNDER_REVIEW" ? "text-amber-700" : "text-red-700")
            }
          >
            {app.status === "UNDER_REVIEW"
              ? "Referred to underwriter"
              : "Application declined"}
          </div>
          <p className="mt-2 text-sm text-ink-700">{app.rationale}</p>
        </div>
      )}

      {letter && (
        <article className="card p-10 leading-relaxed">
          <header className="border-b border-ink-100 pb-5 mb-6">
            <div className="flex items-baseline justify-between">
              <div>
                <div className="text-sm font-semibold text-brand-700">
                  {letter.bank_name}
                </div>
                <div className="text-[11px] text-ink-500">
                  MSME lending · sanction letter
                </div>
              </div>
              <div className="text-right text-xs text-ink-600">
                <div>
                  Ref: <span className="font-mono">{letter.reference_number}</span>
                </div>
                <div>
                  Letter: <span className="font-mono">{letter.letter_id}</span>
                </div>
                <div>Issued: {new Date(letter.issued_at).toLocaleDateString("en-IN")}</div>
              </div>
            </div>
          </header>

          <p className="text-sm text-ink-800">
            <span className="font-semibold">{letter.enterprise.legal_name}</span>
            <br />
            {letter.enterprise.registered_city}, {letter.enterprise.registered_state}
            <br />
            GSTIN: <span className="font-mono">{letter.enterprise.gstin}</span>
          </p>

          <p className="mt-6 text-sm text-ink-800">Dear Sir / Madam,</p>

          <p className="mt-4 text-sm text-ink-800">
            We are pleased to convey the sanction of a working-capital credit
            facility in favour of{" "}
            <span className="font-semibold">{letter.enterprise.trade_name}</span>,
            based on the alternate-data assessment carried out over the
            consented GST, Account Aggregator, EPFO and UPI signals shared
            with this bank.
          </p>

          <section className="mt-6 grid gap-3 grid-cols-2 md:grid-cols-4">
            <Cell label="Sanctioned amount" value={paiseToInr(letter.amount_paise)} emphasize />
            <Cell label="Tenor" value={`${letter.tenor_months} months`} />
            <Cell label="Interest rate" value={`${letter.roi_pct.toFixed(2)}% p.a.`} />
            <Cell label="Processing fee" value={paiseToInr(letter.processing_fee_paise)} />
            <Cell label="Indicative EMI" value={`${paiseToInr(letter.monthly_emi_paise)}/mo`} emphasize />
            <Cell label="Offer valid until" value={new Date(letter.valid_until).toLocaleDateString("en-IN")} />
          </section>

          <section className="mt-6">
            <div className="text-[11px] uppercase tracking-wider text-ink-500 mb-2">
              Covenants
            </div>
            <ul className="list-decimal ml-5 space-y-1.5 text-sm text-ink-800">
              {letter.covenants.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </section>

          <p className="mt-8 text-sm text-ink-800">
            Kindly acknowledge acceptance of the terms above within 15 days.
            On acceptance, the facility will be disbursed to the operating
            account you have linked via the Account Aggregator consent flow.
          </p>

          <p className="mt-8 text-sm text-ink-800">
            Yours sincerely,
            <br />
            <span className="font-semibold">Head, MSME Digital Lending</span>
            <br />
            {letter.bank_name}
          </p>

          <p className="mt-8 text-[10px] text-ink-400 italic">
            This is a demo sanction letter generated from synthetic data. No
            legal offer of credit is being made.
          </p>
        </article>
      )}
    </div>
  );
}

function Cell({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: string;
  emphasize?: boolean;
}) {
  return (
    <div className="rounded-lg border border-ink-100 bg-ink-50/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-ink-500">
        {label}
      </div>
      <div
        className={
          "mt-0.5 font-display font-semibold " +
          (emphasize ? "text-lg text-brand-700" : "text-sm text-ink-900")
        }
      >
        {value}
      </div>
    </div>
  );
}
