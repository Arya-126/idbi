import type {
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
  UliPullResponse,
} from "./types";

const BASE = import.meta.env.VITE_API_URL || "/api";

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, {
    headers: { "Content-Type": "application/json" }
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
  healthCard: (gstin: string, consent?: string) =>
    req<HealthCard>(withConsent(`/msme/${gstin}/health-card`, consent)),
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
  listApplications: () => req<LoanApplication[]>("/applications"),
  getApplication: (id: string) => req<LoanApplication>(`/applications/${id}`),
  sanctionLetter: (id: string) =>
    req<SanctionLetter>(`/applications/${id}/sanction`),
  consentLog: () => req<ConsentLogEntry[]>("/consent/log"),
};

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
