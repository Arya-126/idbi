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


class DimensionScore(BaseModel):
    key: str  # snake_case id
    label: str  # display name
    score: int = Field(ge=0, le=100)
    weight: float  # 0..1, sums to 1 across all dimensions
    trend: Literal["IMPROVING", "STABLE", "DECLINING", "UNKNOWN"]
    factors: list[Factor]
    summary: str  # one-liner


class Decision(BaseModel):
    recommendation: Literal["APPROVE", "REFER", "DECLINE"]
    suggested_limit_paise: int
    suggested_tenor_months: int
    suggested_roi_pct: float
    rationale: str


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
    agrees_with_rulebook: bool
    summary: str  # one-line agreement/disagreement with the rulebook decision


class HealthCard(BaseModel):
    enterprise: EnterpriseIdentity
    composite_score: int = Field(ge=0, le=1000)
    risk_band: Literal["A", "B", "C", "D"]
    dimensions: list[DimensionScore]
    top_strengths: list[str]
    top_risks: list[str]
    decision: Decision
    ml_assessment: MlAssessment
    generated_at: datetime
    data_freshness: dict[str, date | None]  # None = source not available
    disclaimer: str = (
        "Score generated from consented alternate data over an Account "
        "Aggregator-style consent flow (ULI/OCEN-ready connector seams). "
        "Advisory only — final credit decision rests with the underwriter."
    )


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
    consent_id: str
    gstin: str
    sources: list[ConsentSource]
    granted_at: datetime
    expires_at: datetime
    status: Literal["PENDING", "GRANTED", "REVOKED"]


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
    band_distribution: list[PortfolioBucket]
    sector_mix: list[PortfolioBucket]
    recommendation_mix: list[PortfolioBucket]
    entries: list[PortfolioEntry]
    generated_at: datetime
