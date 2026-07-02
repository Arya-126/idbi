import type {
  ConsentGrant,
  ConsentSource,
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

export const api = {
  listMsmes: () => req<MsmeSummary[]>("/msme"),
  healthCard: (gstin: string) => req<HealthCard>(`/msme/${gstin}/health-card`),
  portfolio: () => req<PortfolioSummary>("/portfolio"),
  requestConsent: (gstin: string, sources: ConsentSource[]) =>
    req<ConsentGrant>("/consent", {
      method: "POST",
      body: JSON.stringify({ gstin, sources }),
    }),
};
