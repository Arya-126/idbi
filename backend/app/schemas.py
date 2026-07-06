"""Pydantic schemas — the normalized vocabulary the whole app speaks.

Three layers:
  1. Enterprise identity (Udyam + GSTIN + PAN + sector)
  2. Normalized data from each source (GST, AA, EPFO, UPI)
  3. Financial Health Card output — dimensions, factors, decision.

Money is INR paise (int). Dates are ISO 8601 at the API boundary.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ─── Enterprise identity ────────────────────────────────────────────────────


class MsmeCategory(str, Enum):
    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"


class EntityType(str, Enum):
    PROPRIETORSHIP = "PROPRIETORSHIP"
    PARTNERSHIP = "PARTNERSHIP"
    LLP = "LLP"
    PVT_LTD = "PVT_LTD"


class EnterpriseIdentity(BaseModel):
    gstin: str
    udyam_number: str | None = None
    pan: str
    legal_name: str
    trade_name: str
    incorporation_date: date
    entity_type: EntityType
    sector: str
    sub_sector: str
    msme_category: MsmeCategory
    registered_state: str
    registered_city: str


# ─── GST normalized ─────────────────────────────────────────────────────────


class GstMonthlyReturn(BaseModel):
    period: str  # "YYYY-MM"
    outward_taxable_paise: int
    inward_taxable_paise: int
    net_tax_paid_paise: int
    filed_on_time: bool
    filing_delay_days: int  # 0 if on time


class GstProfile(BaseModel):
    gstin: str
    registration_date: date
    filing_status: Literal["ACTIVE", "SUSPENDED", "CANCELLED"]
    returns: list[GstMonthlyReturn]  # last 24 months


# ─── Account Aggregator (AA) normalized ─────────────────────────────────────
# Loosely follows ReBIT FI data schema shape for deposit accounts.


class BankTxnCategory(str, Enum):
    REVENUE = "REVENUE"
    PURCHASE = "PURCHASE"
    SALARY = "SALARY"
    EMI = "EMI"
    TAX = "TAX"
    UTILITY = "UTILITY"
    TRANSFER = "TRANSFER"
    CASH = "CASH"
    OTHER = "OTHER"


class BankTxn(BaseModel):
    txn_id: str
    date: date
    amount_paise: int  # signed: positive = credit, negative = debit
    mode: Literal["UPI", "IMPS", "NEFT", "RTGS", "CHEQUE", "CASH", "ACH", "CARD"]
    narration: str
    balance_paise: int
    category: BankTxnCategory


class BankAccount(BaseModel):
    account_id: str
    bank_name: str
    ifsc: str
    account_type: Literal["SAVINGS", "CURRENT", "OD", "CC"]
    current_balance_paise: int
    as_of: date
    transactions: list[BankTxn]  # last 12 months
    bounce_incidents: int  # returned cheques / failed ACH last 12m


class AaProfile(BaseModel):
    consent_handle: str
    linked_accounts: list[BankAccount]


# ─── EPFO normalized ────────────────────────────────────────────────────────


class EpfoMonth(BaseModel):
    period: str
    total_employees: int
    total_wages_paise: int
    employer_share_paise: int
    employee_share_paise: int
    filed_on_time: bool


class EpfoProfile(BaseModel):
    establishment_id: str
    active: bool
    monthly: list[EpfoMonth]  # empty list = no EPFO coverage


# ─── UPI normalized ─────────────────────────────────────────────────────────


class UpiMonth(BaseModel):
    period: str
    inflow_paise: int
    outflow_paise: int
    inbound_count: int
    outbound_count: int
    unique_payers: int
    p2m_share: float  # 0..1


class UpiProfile(BaseModel):
    vpa: str
    monthly: list[UpiMonth]


# ─── Consolidated data pack ─────────────────────────────────────────────────


class DataPack(BaseModel):
    identity: EnterpriseIdentity
    gst: GstProfile
    aa: AaProfile
    epfo: EpfoProfile
    upi: UpiProfile
    fetched_at: datetime
    # Sources the consent grant did NOT cover — those profiles above are
    # empty placeholders, never fetched from the connector.
    sources_excluded: list[str] = []
    # Bureau-if-available context. Never scored — carried for display only.
    bureau: BureauSummary | None = None


# ─── Bureau (display-only stub) ─────────────────────────────────────────────


class BureauSummary(BaseModel):
    """Bureau-if-available: shown on the card for context, NEVER scored.

    The whole pitch is scoring the bureau-less; this stub proves the "bureau
    as a plug-in, not a rewrite" architecture claim with running code.
    """
    hit: bool                       # False = no file found (the NTC story)
    score: int | None = None        # synthetic 300-900 when hit
    live_tradelines: int = 0
    note: str = ""


# ─── Health Card output ─────────────────────────────────────────────────────


class FactorKind(str, Enum):
    STRENGTH = "STRENGTH"
    RISK = "RISK"
    NEUTRAL = "NEUTRAL"


class Factor(BaseModel):
    """One human-readable reason inside a dimension score."""

    name: str
    detail: str  # e.g. "₹42L monthly turnover, +18% YoY"
    contribution: int  # signed points, roughly -30..+30
    kind: FactorKind
    # Stable adverse-action-style reason code (e.g. "CF-02"). Every decline
    # traces to coded reasons — the regulatory-decisioning convention.
    code: str = ""


class DimensionScore(BaseModel):
    key: str  # snake_case id
    label: str  # display name
    score: int = Field(ge=0, le=100)
    weight: float  # 0..1, sums to 1 across all dimensions
    trend: Literal["IMPROVING", "STABLE", "DECLINING", "UNKNOWN"]
    factors: list[Factor]
    summary: str  # one-liner
    # Percentile vs same-sector peers in the portfolio (0..100). None when the
    # sector has fewer than a handful of peers to benchmark against.
    peer_percentile: int | None = None
    # False when the borrower withheld consent for this dimension's source —
    # the dimension is excluded from the composite (weights renormalize over
    # the consented ones) and the card greys it out.
    consented: bool = True


class LimitStep(BaseModel):
    """One line in the limit-derivation workings shown on the UI."""
    label: str
    value_paise: int
    note: str


class Decision(BaseModel):
    recommendation: Literal["APPROVE", "REFER", "DECLINE"]
    suggested_limit_paise: int
    suggested_tenor_months: int
    suggested_roi_pct: float
    rationale: str
    limit_workings: list[LimitStep] = []


class MlDriver(BaseModel):
    feature_key: str
    feature_label: str
    contribution: float  # signed PD delta vs population median
    detail: str          # human-readable current value


class MlAssessment(BaseModel):
    # `model_version` collides with Pydantic's default `model_` protected
    # namespace; disable it explicitly rather than rename the public field.
    model_config = ConfigDict(protected_namespaces=())

    probability_of_default: float = Field(ge=0.0, le=1.0)
    confidence: Literal["high", "medium", "low"]
    drivers: list[MlDriver]   # push PD up
    supports: list[MlDriver]  # pull PD down
    model_version: str
    trained_on_n_samples: int
    holdout_auc: float | None = None  # AUC on the 20% holdout at train time
    # Brier score on the same holdout — probability quality, lower is better.
    holdout_brier: float | None = None
    calibration: str = "sigmoid"  # Platt-scaled probabilities
    monotonic_constraints: bool = True  # direction-enforced features
    agrees_with_rulebook: bool
    summary: str  # one-line agreement/disagreement with the rulebook decision


class Recommendation(BaseModel):
    """A specific improvement suggestion for the MSME owner."""
    dimension_key: str          # which dimension this lifts
    action: str                  # short imperative title
    detail: str                  # human explanation
    # Composite-score gain (0-1000 scale) if actioned — computed by applying
    # the change to the borrower's features and re-running the scorecard,
    # not a hand-calibrated constant.
    est_score_uplift_pts: int
    time_horizon_months: int     # how long to see the effect


class PathToNextBand(BaseModel):
    """Greedy stack of recommendations that reaches the next risk band.

    Built by applying the quantified recommendations in descending-uplift
    order to the borrower's own features and re-scoring after each one.
    """
    current_band: Literal["A", "B", "C", "D"]
    target_band: Literal["A", "B", "C"]
    achievable: bool             # False if even all actions fall short
    projected_score: int         # composite after applying the listed actions
    uplift_pts: int              # projected_score − current composite
    actions: list[str]           # recommendation titles, in application order
    time_horizon_months: int     # max horizon among the actions used


class ScoreHistoryPoint(BaseModel):
    period: str          # "YYYY-MM"
    composite_score: int
    risk_band: Literal["A", "B", "C", "D"]
    # True = a real recorded scoring run for this period; False = the
    # reconstructed approximation (windowed re-score of today's pack).
    observed: bool = False


class HealthCard(BaseModel):
    enterprise: EnterpriseIdentity
    # Display-only bureau context ("no file found" is the NTC proof point).
    bureau: BureauSummary | None = None
    composite_score: int = Field(ge=0, le=1000)
    risk_band: Literal["A", "B", "C", "D"]
    dimensions: list[DimensionScore]
    top_strengths: list[str]
    top_risks: list[str]
    decision: Decision
    ml_assessment: MlAssessment
    improvement_recommendations: list[Recommendation] = []
    # None when already Band A (nothing above it) or no quantified
    # recommendations apply.
    path_to_next_band: PathToNextBand | None = None
    score_history: list[ScoreHistoryPoint] = []
    generated_at: datetime
    data_freshness: dict[str, date | None]  # None = source not available
    disclaimer: str = (
        "Score generated from consented alternate data over an Account "
        "Aggregator-style consent flow (ULI/OCEN-ready connector seams). "
        "Advisory only — final credit decision rests with the underwriter."
    )


# ─── What-if sensitivity simulator ──────────────────────────────────────────


class WhatIfRequest(BaseModel):
    """Officer-adjustable levers. None = keep the borrower's actual value."""
    gst_filing_on_time_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    bounce_count: int | None = Field(default=None, ge=0, le=12)
    turnover_growth_pct: float | None = Field(default=None, ge=-0.5, le=0.5)
    # Average balance expressed in months of operating outflow.
    balance_buffer_months: float | None = Field(default=None, ge=0.0, le=6.0)
    upi_unique_payers: int | None = Field(default=None, ge=0, le=5000)


class WhatIfResponse(BaseModel):
    # The borrower's actual lever values, so the UI can seat the sliders.
    current: dict[str, float]
    base_composite: int
    base_band: Literal["A", "B", "C", "D"]
    base_recommendation: Literal["APPROVE", "REFER", "DECLINE"]
    base_pd: float
    new_composite: int
    new_band: Literal["A", "B", "C", "D"]
    new_recommendation: Literal["APPROVE", "REFER", "DECLINE"]
    new_pd: float
    delta_pts: int
    changed: list[str]  # human-readable overrides applied


# ─── Consent flow (mocked) ──────────────────────────────────────────────────


class ConsentSource(str, Enum):
    GST = "GST"
    AA = "AA"
    EPFO = "EPFO"
    UPI = "UPI"


class ConsentRequest(BaseModel):
    gstin: str
    sources: list[ConsentSource]


class ConsentGrant(BaseModel):
    """Consent artefact, shaped after the DEPA/ReBIT consent-object fields.

    The signature is a sha256 content hash labelled SIMULATED — a real AA
    artefact carries a detached JWS signature from the Account Aggregator.
    """
    consent_id: str
    gstin: str
    sources: list[ConsentSource]
    granted_at: datetime
    expires_at: datetime
    status: Literal["PENDING", "GRANTED", "REVOKED"]
    # ── ReBIT/DEPA-inspired artefact fields ────────────────────────────────
    purpose_code: str = "101"
    purpose_text: str = "Credit underwriting of MSME working-capital facility"
    fi_types: list[str] = []          # ReBIT-style FI type tags per source
    fetch_type: Literal["ONETIME", "PERIODIC"] = "PERIODIC"
    frequency: str = "MONTHLY"
    data_life_days: int = 90          # how long the FIU may retain the data
    fi_data_range_months: int = 24    # how far back the pull may reach
    artefact_signature: str = ""      # SIMULATED sha256 content hash


class ConsentArtefact(BaseModel):
    """Downloadable consent-artefact document (JSON)."""
    schema_version: str = "rebit-inspired-v1"
    artefact: ConsentGrant
    disclaimer: str = (
        "Demo artefact. Field layout is inspired by the ReBIT consent object; "
        "the signature is a simulated content hash, not a JWS."
    )


class AuditEntry(BaseModel):
    """One data-access event — every pull, tied to its consent handle."""
    timestamp: datetime
    endpoint: str                      # e.g. "GET /api/msme/{gstin}/health-card"
    gstin: str
    consent_id: str | None             # None = handle-less demo-fallback pull
    outcome: Literal["ALLOWED", "DENIED"]
    detail: str                        # sources touched, or the denial reason


# ─── MSME summary (for the picker) ──────────────────────────────────────────


class MsmeSummary(BaseModel):
    gstin: str
    trade_name: str
    sector: str
    sub_sector: str
    msme_category: MsmeCategory
    registered_city: str
    tagline: str  # short demo-facing label


# ─── Portfolio dashboard ────────────────────────────────────────────────────


class PortfolioEntry(BaseModel):
    gstin: str
    trade_name: str
    sector: str
    sub_sector: str
    msme_category: MsmeCategory
    registered_city: str
    composite_score: int
    risk_band: Literal["A", "B", "C", "D"]
    recommendation: Literal["APPROVE", "REFER", "DECLINE"]
    probability_of_default: float
    monthly_turnover_paise: int
    suggested_limit_paise: int
    is_demo: bool  # true for the 5 hand-authored personas
    is_ntc: bool   # New-to-Credit: no bureau footprint (young firm, no live loans)
    is_ntb: bool   # New-to-Bank: banks elsewhere; data arrives via the AA rail
    is_watchlist: bool
    watchlist_reason: str | None = None
    # Recent-vs-earlier direction across GST turnover + filing timeliness.
    trend: Literal["IMPROVING", "STABLE", "DECLINING", "UNKNOWN"] = "UNKNOWN"
    # Early-warning triggers surfaced on the officer's book view.
    ews_flags: list[str] = []
    # Champion/challenger: True when the advisory ML PD disagrees with the
    # rulebook decision — the underwriter's review queue.
    ml_divergent: bool = False
    # Firm age in months (from incorporation) — drives the vintage cohorts.
    vintage_months: int = 0


class SectorExposure(BaseModel):
    sector: str
    exposure_paise: int
    share: float          # of total exposure
    breach: bool          # share > sector cap


class ConcentrationSummary(BaseModel):
    """Diversification guardrails over the approved/referred book."""
    hhi: float                      # Herfindahl–Hirschman index over sector shares (0-1)
    sector_cap: float = 0.25        # policy: no sector above 25% of exposure
    single_name_cap: float = 0.10   # policy: no borrower above 10% of exposure
    top_sector: str
    top_sector_share: float
    single_name_max: str            # trade name of the largest exposure
    single_name_max_share: float
    sector_exposures: list[SectorExposure]
    breaches: list[str]             # human-readable guardrail breaches


class VintageCohort(BaseModel):
    key: str          # "lt1y" | "1to3y" | "3to5y" | "gt5y"
    label: str
    count: int
    avg_score: float
    approval_rate: float
    avg_pd: float


class PortfolioBucket(BaseModel):
    key: str
    label: str
    count: int
    share: float  # 0..1


class PortfolioSummary(BaseModel):
    total_msmes: int
    avg_composite_score: float
    avg_pd: float
    total_exposure_paise: int  # sum of suggested limits (approved only)
    ntc_ntb_count: int  # MSMEs approved despite no bureau footprint
    watchlist_count: int
    ml_divergent_count: int = 0  # champion/challenger review queue size
    band_distribution: list[PortfolioBucket]
    sector_mix: list[PortfolioBucket]
    recommendation_mix: list[PortfolioBucket]
    concentration: ConcentrationSummary | None = None
    vintage_cohorts: list[VintageCohort] = []
    entries: list[PortfolioEntry]
    generated_at: datetime


# ─── Before/after impact dashboard ──────────────────────────────────────────


class ImpactRow(BaseModel):
    """One before/after row: what a bureau-only lender would say vs. what
    this system says."""
    gstin: str
    trade_name: str
    sector: str
    monthly_turnover_paise: int
    is_ntc: bool
    is_ntb: bool
    traditional_verdict: Literal["APPROVE", "REJECT"]
    traditional_reason: str
    alternate_verdict: Literal["APPROVE", "REFER", "DECLINE"]
    alternate_limit_paise: int
    probability_of_default: float


class ImpactMetric(BaseModel):
    key: str
    label: str
    traditional: str  # rendered value
    alternate: str
    lift: str  # human-readable direction / delta
    positive: bool  # tint the delta green vs red
    note: str | None = None  # methodology footnote shown under the metric


class InclusionSlice(BaseModel):
    """One cut of the book for the inclusion dashboard — NTC/NTB vs
    established, compared on equal metrics."""
    key: str
    label: str
    count: int
    approval_rate: float
    avg_score: float
    avg_pd: float
    avg_limit_paise: int   # among approved members of the slice


class ImpactSummary(BaseModel):
    total_msmes: int
    traditional_approvals: int
    alternate_approvals: int
    additional_msmes_served: int  # alternate approves that traditional rejects
    ntc_ntb_included: int
    additional_exposure_paise: int
    estimated_default_rate_lift_pp: float  # extra portfolio risk taken on
    metrics: list[ImpactMetric]
    inclusion: list[InclusionSlice] = []
    rescued_rows: list[ImpactRow]  # alternate = APPROVE / REFER, traditional = REJECT
    generated_at: datetime


# ─── ULI / OCEN simulated flow ──────────────────────────────────────────────


class UliEvent(BaseModel):
    step: int
    actor: Literal["LSP", "OCEN", "ULI", "BANK", "AA", "FIP", "BORROWER"]
    action: str        # e.g. "POST /uli/pull"
    detail: str        # short human blurb
    latency_ms: int
    ok: bool


class UliPullRequest(BaseModel):
    gstin: str
    lsp_id: str = "LSP-DEMO-01"
    product: Literal["WORKING_CAPITAL", "TERM_LOAN", "INVOICE_DISCOUNTING"] = (
        "WORKING_CAPITAL"
    )


class UliPullResponse(BaseModel):
    trace_id: str
    events: list[UliEvent]
    health_card: HealthCard | None
    total_latency_ms: int


class OcenLoanRequest(BaseModel):
    gstin: str
    amount_paise: int
    tenor_months: int
    lsp_id: str = "LSP-DEMO-01"


class OcenLoanResponse(BaseModel):
    trace_id: str
    events: list[UliEvent]
    decision: Literal["SANCTIONED", "REFERRED", "REJECTED"]
    sanctioned_amount_paise: int
    tenor_months: int
    roi_pct: float
    # Always present — a REJECTED application is still an auditable record.
    application_id: str | None


class ComplianceItem(BaseModel):
    """One row of the RBI Digital Lending Guidelines checklist."""
    requirement: str
    status: Literal["IMPLEMENTED", "SIMULATED", "PRODUCTION_PLAN"]
    evidence: str          # what in this demo proves / would prove it
    link: str | None = None  # frontend route that demonstrates it


# ─── Portfolio stress test ───────────────────────────────────────────────────


class StressScenario(BaseModel):
    """Feature-level shocks applied to every book member before re-scoring."""
    key: str = "custom"
    label: str = "Custom scenario"
    turnover_shock_pct: float = Field(default=0.0, ge=-0.6, le=0.0)  # e.g. -0.20
    extra_bounces: int = Field(default=0, ge=0, le=6)
    emi_increase_pct: float = Field(default=0.0, ge=0.0, le=1.0)     # e.g. +0.25


class BandMigrationCell(BaseModel):
    from_band: Literal["A", "B", "C", "D"]
    to_band: Literal["A", "B", "C", "D"]
    count: int


class StressedEntry(BaseModel):
    gstin: str
    trade_name: str
    band_before: Literal["A", "B", "C", "D"]
    band_after: Literal["A", "B", "C", "D"]
    score_before: int
    score_after: int
    recommendation_before: Literal["APPROVE", "REFER", "DECLINE"]
    recommendation_after: Literal["APPROVE", "REFER", "DECLINE"]
    exposure_paise: int


class StressResult(BaseModel):
    scenario: StressScenario
    avg_score_before: float
    avg_score_after: float
    downgraded: int                     # band worsened
    decisions_worsened: int             # APPROVE→REFER/DECLINE or REFER→DECLINE
    exposure_at_risk_paise: int         # limits of entries whose decision worsened
    migrations: list[BandMigrationCell] # only non-diagonal cells
    worst_hit: list[StressedEntry]      # sorted by score drop, top 10
    generated_at: datetime


# ─── Watch-list action workflow ──────────────────────────────────────────────


class WatchlistActionRequest(BaseModel):
    action: Literal["ACKNOWLEDGE", "REQUEST_REPULL", "SCHEDULE_REVIEW"]
    note: str = ""


class WatchlistAction(BaseModel):
    action_id: str
    gstin: str
    trade_name: str
    action: Literal["ACKNOWLEDGE", "REQUEST_REPULL", "SCHEDULE_REVIEW"]
    note: str
    created_at: datetime


# ─── Loan applications + sanction letters ───────────────────────────────────


class LoanApplication(BaseModel):
    application_id: str
    gstin: str
    trade_name: str
    amount_paise: int
    tenor_months: int
    roi_pct: float
    status: Literal["DRAFT", "SANCTIONED", "UNDER_REVIEW", "REJECTED"]
    created_at: datetime
    channel: Literal["DIRECT", "ULI", "OCEN"] = "DIRECT"
    rationale: str


class ApplyRequest(BaseModel):
    # Optional overrides — defaults come from the recommended decision.
    amount_paise: int | None = None
    tenor_months: int | None = None


class KeyFactStatement(BaseModel):
    """RBI Digital Lending Guidelines mandate a KFS with the all-in cost of
    credit before disbursal. Computed from the sanction terms."""
    apr_pct: float                      # annualized all-in rate incl. fees
    total_interest_paise: int
    processing_fee_paise: int
    total_cost_of_credit_paise: int     # interest + fees
    monthly_emi_paise: int
    number_of_emis: int
    cooling_off_days: int = 3           # exit window per DLG 2022
    grievance_officer: str = "grievance.msme@bank.example (placeholder)"
    lsp_disclosure: str = (
        "Where this loan is intermediated by a Loan Service Provider, the "
        "LSP acts as the bank's agent; all recovery happens through the bank."
    )


class SanctionLetter(BaseModel):
    letter_id: str
    application_id: str
    enterprise: EnterpriseIdentity
    amount_paise: int
    tenor_months: int
    roi_pct: float
    processing_fee_paise: int
    monthly_emi_paise: int
    covenants: list[str]
    issued_at: datetime
    valid_until: datetime
    bank_name: str = "IDBI Bank"
    reference_number: str  # SL-YYYYMMDD-XXXX
    kfs: KeyFactStatement | None = None


# ─── Consent audit log ──────────────────────────────────────────────────────


class ConsentLogEntry(BaseModel):
    consent_id: str
    gstin: str
    trade_name: str
    sources: list[ConsentSource]
    granted_at: datetime
    expires_at: datetime
    status: Literal["PENDING", "GRANTED", "REVOKED", "EXPIRED"]
