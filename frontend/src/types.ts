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
  peer_percentile: number | null;
}

export interface LimitStep {
  label: string;
  value_paise: number;
  note: string;
}

export interface Decision {
  recommendation: Recommendation;
  suggested_limit_paise: number;
  suggested_tenor_months: number;
  suggested_roi_pct: number;
  rationale: string;
  limit_workings: LimitStep[];
}

export interface ImprovementRecommendation {
  dimension_key: string;
  action: string;
  detail: string;
  est_score_uplift_pts: number;
  time_horizon_months: number;
}

export interface ScoreHistoryPoint {
  period: string;
  composite_score: number;
  risk_band: RiskBand;
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
  holdout_auc: number | null;
  agrees_with_rulebook: boolean;
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
  improvement_recommendations: ImprovementRecommendation[];
  score_history: ScoreHistoryPoint[];
  generated_at: string;
  data_freshness: Record<string, string | null>; // null = source not available
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
  is_ntc: boolean;
  is_ntb: boolean;
  is_watchlist: boolean;
  watchlist_reason: string | null;
  trend: Trend;
  ews_flags: string[];
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

// Slim view of the backend DataPack — only what the consent page needs to
// show real per-source pull results.
export interface DataPackLite {
  gst: { returns: unknown[] };
  aa: { linked_accounts: { transactions: unknown[] }[] };
  epfo: { active: boolean; monthly: unknown[] };
  upi: { monthly: unknown[] };
  fetched_at: string;
}

// ─── Impact dashboard ──────────────────────────────────────────────────────

export interface ImpactMetric {
  key: string;
  label: string;
  traditional: string;
  alternate: string;
  lift: string;
  positive: boolean;
}

export interface ImpactRow {
  gstin: string;
  trade_name: string;
  sector: string;
  monthly_turnover_paise: number;
  is_ntc: boolean;
  is_ntb: boolean;
  traditional_verdict: "APPROVE" | "REJECT";
  traditional_reason: string;
  alternate_verdict: Recommendation;
  alternate_limit_paise: number;
  probability_of_default: number;
}

export interface ImpactSummary {
  total_msmes: number;
  traditional_approvals: number;
  alternate_approvals: number;
  additional_msmes_served: number;
  ntc_ntb_included: number;
  additional_exposure_paise: number;
  estimated_default_rate_lift_pp: number;
  metrics: ImpactMetric[];
  rescued_rows: ImpactRow[];
  generated_at: string;
}

// ─── ULI / OCEN simulated flow ─────────────────────────────────────────────

export type UliActor = "LSP" | "OCEN" | "ULI" | "BANK" | "AA" | "FIP" | "BORROWER";

export interface UliEvent {
  step: number;
  actor: UliActor;
  action: string;
  detail: string;
  latency_ms: number;
  ok: boolean;
}

export interface UliPullResponse {
  trace_id: string;
  events: UliEvent[];
  health_card: HealthCard | null;
  total_latency_ms: number;
}

export interface OcenLoanResponse {
  trace_id: string;
  events: UliEvent[];
  decision: "SANCTIONED" | "REFERRED" | "REJECTED";
  sanctioned_amount_paise: number;
  tenor_months: number;
  roi_pct: number;
  application_id: string | null;
}

// ─── Loan applications + sanction letters ──────────────────────────────────

export type ApplicationStatus =
  | "DRAFT"
  | "SANCTIONED"
  | "UNDER_REVIEW"
  | "REJECTED";

export interface LoanApplication {
  application_id: string;
  gstin: string;
  trade_name: string;
  amount_paise: number;
  tenor_months: number;
  roi_pct: number;
  status: ApplicationStatus;
  created_at: string;
  channel: "DIRECT" | "ULI" | "OCEN";
  rationale: string;
}

export interface SanctionLetter {
  letter_id: string;
  application_id: string;
  enterprise: EnterpriseIdentity;
  amount_paise: number;
  tenor_months: number;
  roi_pct: number;
  processing_fee_paise: number;
  monthly_emi_paise: number;
  covenants: string[];
  issued_at: string;
  valid_until: string;
  bank_name: string;
  reference_number: string;
}

// ─── Consent audit log ─────────────────────────────────────────────────────

export interface ConsentLogEntry {
  consent_id: string;
  gstin: string;
  trade_name: string;
  sources: ConsentSource[];
  granted_at: string;
  expires_at: string;
  status: ConsentStatus | "EXPIRED";
}
