import type {
  ConsentGrant,
  ConsentSource,
  DataPackLite,
  HealthCard,
  MsmeSummary,
  PortfolioSummary,
} from "./types";

const BASE = "/api";

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
