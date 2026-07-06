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
  code: string; // stable adverse-action-style reason code, e.g. "CF-02"
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
  consented: boolean; // false = source withheld; excluded from composite
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
  // Composite-score gain (0-1000 scale), computed by re-running the scorecard.
  est_score_uplift_pts: number;
  time_horizon_months: number;
}

export interface PathToNextBand {
  current_band: RiskBand;
  target_band: "A" | "B" | "C";
  achievable: boolean;
  projected_score: number;
  uplift_pts: number;
  actions: string[];
  time_horizon_months: number;
}

export interface ScoreHistoryPoint {
  period: string;
  composite_score: number;
  risk_band: RiskBand;
  observed: boolean; // true = real recorded run; false = reconstructed
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
  holdout_brier: number | null;
  calibration: string;
  monotonic_constraints: boolean;
  agrees_with_rulebook: boolean;
  summary: string;
}

export interface BureauSummary {
  hit: boolean;
  score: number | null;
  live_tradelines: number;
  note: string;
}

export interface HealthCard {
  enterprise: EnterpriseIdentity;
  bureau: BureauSummary | null;
  composite_score: number;
  risk_band: RiskBand;
  dimensions: DimensionScore[];
  top_strengths: string[];
  top_risks: string[];
  decision: Decision;
  ml_assessment: MlAssessment;
  improvement_recommendations: ImprovementRecommendation[];
  path_to_next_band: PathToNextBand | null;
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
  ml_divergent: boolean;
  vintage_months: number;
}

export interface SectorExposure {
  sector: string;
  exposure_paise: number;
  share: number;
  breach: boolean;
}

export interface ConcentrationSummary {
  hhi: number;
  sector_cap: number;
  single_name_cap: number;
  top_sector: string;
  top_sector_share: number;
  single_name_max: string;
  single_name_max_share: number;
  sector_exposures: SectorExposure[];
  breaches: string[];
}

export interface VintageCohort {
  key: string;
  label: string;
  count: number;
  avg_score: number;
  approval_rate: number;
  avg_pd: number;
}

export interface PortfolioSummary {
  total_msmes: number;
  avg_composite_score: number;
  avg_pd: number;
  total_exposure_paise: number;
  ntc_ntb_count: number;
  watchlist_count: number;
  ml_divergent_count: number;
  band_distribution: PortfolioBucket[];
  sector_mix: PortfolioBucket[];
  recommendation_mix: PortfolioBucket[];
  concentration: ConcentrationSummary | null;
  vintage_cohorts: VintageCohort[];
  entries: PortfolioEntry[];
  generated_at: string;
}

// ─── Portfolio stress test ─────────────────────────────────────────────────

export interface StressScenario {
  key: string;
  label: string;
  turnover_shock_pct: number;
  extra_bounces: number;
  emi_increase_pct: number;
}

export interface BandMigrationCell {
  from_band: RiskBand;
  to_band: RiskBand;
  count: number;
}

export interface StressedEntry {
  gstin: string;
  trade_name: string;
  band_before: RiskBand;
  band_after: RiskBand;
  score_before: number;
  score_after: number;
  recommendation_before: Recommendation;
  recommendation_after: Recommendation;
  exposure_paise: number;
}

export interface StressResult {
  scenario: StressScenario;
  avg_score_before: number;
  avg_score_after: number;
  downgraded: number;
  decisions_worsened: number;
  exposure_at_risk_paise: number;
  migrations: BandMigrationCell[];
  worst_hit: StressedEntry[];
  generated_at: string;
}

// ─── Watch-list actions ────────────────────────────────────────────────────

export type WatchlistActionKind =
  | "ACKNOWLEDGE"
  | "REQUEST_REPULL"
  | "SCHEDULE_REVIEW";

export interface WatchlistAction {
  action_id: string;
  gstin: string;
  trade_name: string;
  action: WatchlistActionKind;
  note: string;
  created_at: string;
}

export interface ConsentGrant {
  consent_id: string;
  gstin: string;
  sources: ConsentSource[];
  granted_at: string;
  expires_at: string;
  status: ConsentStatus;
  // ReBIT/DEPA-inspired artefact fields
  purpose_code: string;
  purpose_text: string;
  fi_types: string[];
  fetch_type: "ONETIME" | "PERIODIC";
  frequency: string;
  data_life_days: number;
  fi_data_range_months: number;
  artefact_signature: string;
}

export interface AuditEntry {
  timestamp: string;
  endpoint: string;
  gstin: string;
  consent_id: string | null;
  outcome: "ALLOWED" | "DENIED";
  detail: string;
}

export interface ComplianceItem {
  requirement: string;
  status: "IMPLEMENTED" | "SIMULATED" | "PRODUCTION_PLAN";
  evidence: string;
  link: string | null;
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

// ─── What-if sensitivity simulator ─────────────────────────────────────────

export interface WhatIfRequest {
  gst_filing_on_time_pct?: number;
  bounce_count?: number;
  turnover_growth_pct?: number;
  balance_buffer_months?: number;
  upi_unique_payers?: number;
}

export interface WhatIfResponse {
  current: Record<string, number>;
  base_composite: number;
  base_band: RiskBand;
  base_recommendation: Recommendation;
  base_pd: number;
  new_composite: number;
  new_band: RiskBand;
  new_recommendation: Recommendation;
  new_pd: number;
  delta_pts: number;
  changed: string[];
}

// ─── Impact dashboard ──────────────────────────────────────────────────────

export interface ImpactMetric {
  key: string;
  label: string;
  traditional: string;
  alternate: string;
  lift: string;
  positive: boolean;
  note: string | null;
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

export interface InclusionSlice {
  key: string;
  label: string;
  count: number;
  approval_rate: number;
  avg_score: number;
  avg_pd: number;
  avg_limit_paise: number;
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
  inclusion: InclusionSlice[];
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

export interface KeyFactStatement {
  apr_pct: number;
  total_interest_paise: number;
  processing_fee_paise: number;
  total_cost_of_credit_paise: number;
  monthly_emi_paise: number;
  number_of_emis: number;
  cooling_off_days: number;
  grievance_officer: string;
  lsp_disclosure: string;
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
  kfs: KeyFactStatement | null;
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
