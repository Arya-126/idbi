import type {
  AuditEntry,
  ComplianceItem,
  ConsentGrant,
  ConsentLogEntry,
  ConsentSource,
  DataPackLite,
  HealthCard,
  ImpactSummary,
  LoanApplication,
  MsmeSummary,
  OcenLoanResponse,
  PortfolioSummary,
  SanctionLetter,
  StressResult,
  StressScenario,
  UliPullResponse,
  WatchlistAction,
  WatchlistActionKind,
  WhatIfRequest,
  WhatIfResponse,
} from "./types";

// Trim a trailing slash so `VITE_API_URL=https://backend.onrender.com/api/`
// doesn't produce a double slash when concatenated with `/msme` etc.
export const BASE = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

function withConsent(url: string, consent?: string): string {
  return consent ? `${url}?consent=${encodeURIComponent(consent)}` : url;
}

export const api = {
  listMsmes: () => req<MsmeSummary[]>("/msme"),
  healthCard: (gstin: string, consent?: string, simMonths = 0) =>
    req<HealthCard>(
      withConsent(`/msme/${gstin}/health-card`, consent) +
        (simMonths > 0
          ? `${consent ? "&" : "?"}sim=${simMonths}`
          : ""),
    ),
  dataPack: (gstin: string, consent?: string) =>
    req<DataPackLite>(withConsent(`/msme/${gstin}/data-pack`, consent)),
  portfolio: () => req<PortfolioSummary>("/portfolio"),
  refreshPortfolio: () =>
    req<PortfolioSummary>("/portfolio/refresh", { method: "POST" }),
  requestConsent: (gstin: string, sources: ConsentSource[]) =>
    req<ConsentGrant>("/consent", {
      method: "POST",
      body: JSON.stringify({ gstin, sources }),
    }),
  revokeConsent: (consentId: string) =>
    req<ConsentGrant>(`/consent/${encodeURIComponent(consentId)}/revoke`, {
      method: "POST",
    }),
  impact: () => req<ImpactSummary>("/impact"),
  uliPull: (gstin: string, product = "WORKING_CAPITAL") =>
    req<UliPullResponse>("/uli/pull", {
      method: "POST",
      body: JSON.stringify({ gstin, product }),
    }),
  ocenLoan: (gstin: string, amount_paise: number, tenor_months: number) =>
    req<OcenLoanResponse>("/ocen/loan-request", {
      method: "POST",
      body: JSON.stringify({ gstin, amount_paise, tenor_months }),
    }),
  applyForCredit: (gstin: string, consent?: string, amount_paise?: number, tenor_months?: number) =>
    req<LoanApplication>(withConsent(`/msme/${gstin}/apply`, consent), {
      method: "POST",
      body: JSON.stringify({ amount_paise, tenor_months }),
    }),
  whatIf: (gstin: string, body: WhatIfRequest, consent?: string) =>
    req<WhatIfResponse>(withConsent(`/msme/${gstin}/what-if`, consent), {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listApplications: () => req<LoanApplication[]>("/applications"),
  getApplication: (id: string) => req<LoanApplication>(`/applications/${id}`),
  sanctionLetter: (id: string) =>
    req<SanctionLetter>(`/applications/${id}/sanction`),
  consentLog: () => req<ConsentLogEntry[]>("/consent/log"),
  auditLog: () => req<AuditEntry[]>("/audit/log"),
  compliance: () => req<ComplianceItem[]>("/compliance"),
  stressPresets: () => req<StressScenario[]>("/portfolio/stress/presets"),
  runStress: (scenario: Partial<StressScenario> & { key: string; label: string }) =>
    req<StressResult>("/portfolio/stress", {
      method: "POST",
      body: JSON.stringify(scenario),
    }),
  watchlistAction: (gstin: string, action: WatchlistActionKind, note: string) =>
    req<WatchlistAction>(`/portfolio/${gstin}/action`, {
      method: "POST",
      body: JSON.stringify({ action, note }),
    }),
  watchlistActions: (gstin?: string) =>
    req<WatchlistAction[]>(
      gstin ? `/portfolio/actions?gstin=${encodeURIComponent(gstin)}` : "/portfolio/actions",
    ),
};

// Direct download URL for the ReBIT-style consent-artefact JSON.
export function consentArtefactUrl(consentId: string): string {
  return `${BASE}/consent/${encodeURIComponent(consentId)}/artefact`;
}

// The consent handle survives the Consent → HealthCard hop via sessionStorage.
export function storeConsent(gstin: string, consentId: string) {
  sessionStorage.setItem(`consent:${gstin}`, consentId);
}

export function storedConsent(gstin: string): string | undefined {
  return sessionStorage.getItem(`consent:${gstin}`) ?? undefined;
}

export function clearConsent(gstin: string) {
  sessionStorage.removeItem(`consent:${gstin}`);
}
