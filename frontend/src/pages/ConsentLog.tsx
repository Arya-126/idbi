import { useEffect, useState } from "react";
import clsx from "clsx";
import { api, consentArtefactUrl } from "../api";
import type { AuditEntry, ConsentLogEntry } from "../types";

type Tab = "grants" | "access";

export default function ConsentLogPage() {
  const [tab, setTab] = useState<Tab>("grants");
  const [entries, setEntries] = useState<ConsentLogEntry[] | null>(null);
  const [accesses, setAccesses] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);

  function refresh() {
    api.consentLog().then(setEntries).catch((e) => setError(String(e)));
    api.auditLog().then(setAccesses).catch((e) => setError(String(e)));
  }

  useEffect(refresh, []);

  function revoke(consentId: string) {
    setRevoking(consentId);
    api
      .revokeConsent(consentId)
      .then(refresh)
      .catch((e) => setError(String(e)))
      .finally(() => setRevoking(null));
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 space-y-4">
      <header className="flex items-baseline justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-ink-500">
            Compliance
          </div>
          <h1 className="mt-1 text-2xl font-display font-semibold text-ink-900">
            Consent &amp; access audit
          </h1>
          <p className="mt-1 text-sm text-ink-600">
            Every grant issued this session, and every data pull made against
            one — including denied attempts after revocation or expiry.
          </p>
        </div>
        <button
          onClick={refresh}
          className="btn-ghost !py-1 !px-2.5 text-xs border border-ink-200 rounded-lg"
        >
          ↻ Refresh
        </button>
      </header>

      <div className="flex items-center gap-1 rounded-xl border border-ink-200 bg-white p-1 text-xs w-fit">
        {(
          [
            ["grants", `Consent grants${entries ? ` (${entries.length})` : ""}`],
            ["access", `Data access${accesses ? ` (${accesses.length})` : ""}`],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={clsx(
              "px-2.5 py-1 rounded-lg transition",
              tab === k ? "bg-brand-600 text-white" : "text-ink-600 hover:bg-ink-50",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="card p-4 border-red-200 bg-red-50 text-red-700 text-sm">
          {error}
        </div>
      )}

      {tab === "grants" ? (
        <GrantsTable entries={entries} revoking={revoking} onRevoke={revoke} />
      ) : (
        <AccessTable accesses={accesses} />
      )}
    </div>
  );
}

function GrantsTable({
  entries,
  revoking,
  onRevoke,
}: {
  entries: ConsentLogEntry[] | null;
  revoking: string | null;
  onRevoke: (id: string) => void;
}) {
  if (!entries) return <div className="text-sm text-ink-500">Loading…</div>;
  if (entries.length === 0) {
    return (
      <div className="card p-6 text-sm text-ink-500">
        No consent grants recorded in this session yet.
      </div>
    );
  }
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-wider text-ink-500 border-b border-ink-100 bg-ink-50/40">
              <th className="px-4 py-2 font-medium">Handle</th>
              <th className="px-4 py-2 font-medium">MSME</th>
              <th className="px-4 py-2 font-medium">Sources</th>
              <th className="px-4 py-2 font-medium">Granted</th>
              <th className="px-4 py-2 font-medium">Expires</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.consent_id} className="border-b border-ink-100 last:border-b-0">
                <td className="px-4 py-2.5 font-mono text-[10px] text-ink-700 truncate max-w-40">
                  {e.consent_id}
                </td>
                <td className="px-4 py-2.5">
                  <div className="text-ink-900 text-sm">{e.trade_name}</div>
                  <div className="text-[10px] text-ink-500 font-mono">{e.gstin}</div>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {e.sources.map((s) => (
                      <span
                        key={s}
                        className="pill bg-brand-50 text-brand-700 border border-brand-200 text-[9px]"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-2.5 text-xs text-ink-600">
                  {new Date(e.granted_at).toLocaleString("en-IN")}
                </td>
                <td className="px-4 py-2.5 text-xs text-ink-600">
                  {new Date(e.expires_at).toLocaleDateString("en-IN")}
                </td>
                <td className="px-4 py-2.5">
                  <span className={"pill text-[10px] " + statusStyle(e.status)}>
                    {e.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap">
                  <a
                    href={consentArtefactUrl(e.consent_id)}
                    download
                    className="text-[10px] font-medium text-brand-700 border border-brand-200 rounded-lg px-2 py-1 hover:bg-brand-50 mr-1.5"
                    title="Download the ReBIT-inspired consent-artefact JSON (purpose code, FI types, data life, simulated signature)"
                  >
                    ⇩ Artefact
                  </a>
                  {e.status === "GRANTED" && (
                    <button
                      onClick={() => onRevoke(e.consent_id)}
                      disabled={revoking === e.consent_id}
                      className="text-[10px] font-medium text-red-600 border border-red-200 rounded-lg px-2 py-1 hover:bg-red-50 disabled:opacity-50"
                      title="Borrower withdraws this grant — subsequent pulls with this handle return 403"
                    >
                      {revoking === e.consent_id ? "Revoking…" : "Revoke"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AccessTable({ accesses }: { accesses: AuditEntry[] | null }) {
  if (!accesses) return <div className="text-sm text-ink-500">Loading…</div>;
  if (accesses.length === 0) {
    return (
      <div className="card p-6 text-sm text-ink-500">
        No data accesses recorded in this session yet.
      </div>
    );
  }
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-wider text-ink-500 border-b border-ink-100 bg-ink-50/40">
              <th className="px-4 py-2 font-medium">When</th>
              <th className="px-4 py-2 font-medium">Endpoint</th>
              <th className="px-4 py-2 font-medium">GSTIN</th>
              <th className="px-4 py-2 font-medium">Consent handle</th>
              <th className="px-4 py-2 font-medium">Outcome</th>
              <th className="px-4 py-2 font-medium">Detail</th>
            </tr>
          </thead>
          <tbody>
            {accesses.map((a, i) => (
              <tr key={i} className="border-b border-ink-100 last:border-b-0">
                <td className="px-4 py-2 text-xs text-ink-600 whitespace-nowrap">
                  {new Date(a.timestamp).toLocaleTimeString("en-IN")}
                </td>
                <td className="px-4 py-2 font-mono text-[10px] text-ink-700">
                  {a.endpoint}
                </td>
                <td className="px-4 py-2 font-mono text-[10px] text-ink-700">
                  {a.gstin}
                </td>
                <td className="px-4 py-2 font-mono text-[10px] text-ink-500 truncate max-w-36">
                  {a.consent_id ?? "on-file (demo fallback)"}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={clsx(
                      "pill text-[10px] border",
                      a.outcome === "ALLOWED"
                        ? "bg-brand-100 text-brand-700 border-brand-200"
                        : "bg-red-100 text-red-700 border-red-200",
                    )}
                  >
                    {a.outcome}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-ink-600">{a.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function statusStyle(s: string): string {
  switch (s) {
    case "GRANTED":
      return "bg-brand-100 text-brand-700 border border-brand-200";
    case "REVOKED":
      return "bg-red-100 text-red-700 border border-red-200";
    case "EXPIRED":
      return "bg-ink-100 text-ink-500 border border-ink-200";
    default:
      return "bg-amber-100 text-amber-700 border border-amber-200";
  }
}
