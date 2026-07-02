// Types mirroring backend/app/schemas.py — kept in sync manually because
// the demo doesn't wire an OpenAPI codegen. If the backend schemas change,
// update here too.

export type MsmeCategory = "MICRO" | "SMALL" | "MEDIUM";
export type EntityType = "PROPRIETORSHIP" | "PARTNERSHIP" | "LLP" | "PVT_LTD";
export type RiskBand = "A" | "B" | "C" | "D";
export type Recommendation = "APPROVE" | "REFER" | "DECLINE";
export type Trend = "IMPROVING" | "STABLE" | "DECLINING" | "UNKNOWN";
export type FactorKind = "STRENGTH" | "RISK" | "NEUTRAL";
export type ConsentSource = "GST" | "AA" | "EPFO" | "UPI";
export type ConsentStatus = "PENDING" | "GRANTED" | "REVOKED";

export interface MsmeSummary {
  gstin: string;
  trade_name: string;
  sector: string;
  sub_sector: string;
  msme_category: MsmeCategory;
  registered_city: string;
  tagline: string;
}

export interface EnterpriseIdentity {
  gstin: string;
  udyam_number: string | null;
  pan: string;
  legal_name: string;
  trade_name: string;
  incorporation_date: string;
  entity_type: EntityType;
  sector: string;
  sub_sector: string;
  msme_category: MsmeCategory;
  registered_state: string;
  registered_city: string;
}

export interface Factor {
  name: string;
  detail: string;
  contribution: number;
  kind: FactorKind;
}

export interface DimensionScore {
  key: string;
  label: string;
  score: number;
  weight: number;
  trend: Trend;
  factors: Factor[];
  summary: string;
}

export interface Decision {
  recommendation: Recommendation;
  suggested_limit_paise: number;
  suggested_tenor_months: number;
  suggested_roi_pct: number;
  rationale: string;
}

export interface MlDriver {
  feature_key: string;
  feature_label: string;
  contribution: number;
  detail: string;
}

export interface MlAssessment {
  probability_of_default: number;
  confidence: "high" | "medium" | "low";
  drivers: MlDriver[];
  supports: MlDriver[];
  model_version: string;
  trained_on_n_samples: number;
  summary: string;
}

export interface HealthCard {
  enterprise: EnterpriseIdentity;
  composite_score: number;
  risk_band: RiskBand;
  dimensions: DimensionScore[];
  top_strengths: string[];
  top_risks: string[];
  decision: Decision;
  ml_assessment: MlAssessment;
  generated_at: string;
  data_freshness: Record<string, string>;
  disclaimer: string;
}

export interface PortfolioBucket {
  key: string;
  label: string;
  count: number;
  share: number;
}

export interface PortfolioEntry {
  gstin: string;
  trade_name: string;
  sector: string;
  sub_sector: string;
  msme_category: MsmeCategory;
  registered_city: string;
  composite_score: number;
  risk_band: RiskBand;
  recommendation: Recommendation;
  probability_of_default: number;
  monthly_turnover_paise: number;
  suggested_limit_paise: number;
  is_demo: boolean;
  is_watchlist: boolean;
  watchlist_reason: string | null;
}

export interface PortfolioSummary {
  total_msmes: number;
  avg_composite_score: number;
  avg_pd: number;
  total_exposure_paise: number;
  ntc_ntb_count: number;
  watchlist_count: number;
  band_distribution: PortfolioBucket[];
  sector_mix: PortfolioBucket[];
  recommendation_mix: PortfolioBucket[];
  entries: PortfolioEntry[];
  generated_at: string;
}

export interface ConsentGrant {
  consent_id: string;
  gstin: string;
  sources: ConsentSource[];
  granted_at: string;
  expires_at: string;
  status: ConsentStatus;
}
