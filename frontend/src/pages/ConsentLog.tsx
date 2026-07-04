import { useEffect, useState } from "react";
import { api } from "../api";
import type { ConsentLogEntry } from "../types";

export default function ConsentLogPage() {
  const [entries, setEntries] = useState<ConsentLogEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.consentLog().then(setEntries).catch((e) => setError(String(e)));
  }

  useEffect(refresh, []);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 space-y-4">
      <header className="flex items-baseline justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-ink-500">
            Compliance
          </div>
          <h1 className="mt-1 text-2xl font-display font-semibold text-ink-900">
            Consent audit log
          </h1>
          <p className="mt-1 text-sm text-ink-600">
            Every data-pull is backed by a registered consent handle. This log
            shows every artefact issued, its scope and its lifecycle status.
          </p>
        </div>
        <button
          onClick={refresh}
          className="btn-ghost !py-1 !px-2.5 text-xs border border-ink-200 rounded-lg"
        >
          ↻ Refresh
        </button>
      </header>

      {error && (
        <div className="card p-4 border-red-200 bg-red-50 text-red-700 text-sm">
          {error}
        </div>
      )}

      {!entries ? (
        <div className="text-sm text-ink-500">Loading…</div>
      ) : entries.length === 0 ? (
        <div className="card p-6 text-sm text-ink-500">
          No consent grants recorded in this session yet.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-ink-500 border-b border-ink-100 bg-ink-50/40">
                <th className="px-4 py-2 font-medium">Handle</th>
                <th className="px-4 py-2 font-medium">MSME</th>
                <th className="px-4 py-2 font-medium">Sources</th>
                <th className="px-4 py-2 font-medium">Granted</th>
                <th className="px-4 py-2 font-medium">Expires</th>
                <th className="px-4 py-2 font-medium">Status</th>
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
