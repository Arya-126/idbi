"""Per-dimension scorers.

Each dimension is a factor-decomposed scorecard: base 50 + signed contributions
from named factors, clamped to [0, 100]. Every factor has a human-readable
"detail" string so the frontend can render "why did this score what it did"
without any extra queries.

Weights across the six dimensions sum to 1.0. Adjust weights in one place.
"""

from __future__ import annotations

from typing import Callable

from ..schemas import DataPack, DimensionScore, Factor, FactorKind
from .features import Features, fmt_paise_short, fmt_pct, L_PAISE


# Weights sum to 1.0. Cash-flow gets the biggest slice — it's the strongest
# demonstrated signal for MSME repayment behaviour.
WEIGHTS: dict[str, float] = {
    "revenue_health": 0.20,
    "cash_flow": 0.22,
    "digital_vitality": 0.15,
    "compliance": 0.15,
    "employment": 0.12,
    "obligation_leverage": 0.16,
}


def _clamp(x: int) -> int:
    return max(0, min(100, x))


def _trend(pct: float | None, up_th: float = 0.05, down_th: float = -0.05) -> str:
    if pct is None:
        return "UNKNOWN"
    if pct > up_th:
        return "IMPROVING"
    if pct < down_th:
        return "DECLINING"
    return "STABLE"


def _mk(
    key: str,
    label: str,
    factors: list[Factor],
    trend: str,
    summary: str,
) -> DimensionScore:
    base = 50 + sum(f.contribution for f in factors)
    return DimensionScore(
        key=key,
        label=label,
        score=_clamp(base),
        weight=WEIGHTS[key],
        trend=trend,
        factors=factors,
        summary=summary,
    )


# ─── 1. Revenue Health ────────────────────────────────────────────────────


def score_revenue_health(f: Features) -> DimensionScore:
    factors: list[Factor] = []
    avg_l = f.avg_monthly_turnover_paise / L_PAISE

    if avg_l >= 30:
        factors.append(Factor(
            name="Turnover scale",
            detail=f"Avg {fmt_paise_short(f.avg_monthly_turnover_paise)}/mo — established scale",
            contribution=30, kind=FactorKind.STRENGTH,
        ))
    elif avg_l >= 15:
        factors.append(Factor(
            name="Turnover scale",
            detail=f"Avg {fmt_paise_short(f.avg_monthly_turnover_paise)}/mo — solid mid-scale",
            contribution=20, kind=FactorKind.STRENGTH,
        ))
    elif avg_l >= 5:
        factors.append(Factor(
            name="Turnover scale",
            detail=f"Avg {fmt_paise_short(f.avg_monthly_turnover_paise)}/mo — micro scale",
            contribution=10, kind=FactorKind.NEUTRAL,
        ))
    else:
        factors.append(Factor(
            name="Turnover scale",
            detail=f"Avg {fmt_paise_short(f.avg_monthly_turnover_paise)}/mo — very small base",
            contribution=-5, kind=FactorKind.RISK,
        ))

    g = f.turnover_growth_pct
    if g is None:
        factors.append(Factor(
            name="Growth trajectory",
            detail=f"Only {f.months_of_gst_history} months of filings — trend not yet reliable",
            contribution=0, kind=FactorKind.NEUTRAL,
        ))
    elif g > 0.15:
        factors.append(Factor(
            name="Growth trajectory",
            detail=f"Turnover growing {fmt_pct(g)} vs earlier period",
            contribution=20, kind=FactorKind.STRENGTH,
        ))
    elif g > 0.0:
        factors.append(Factor(
            name="Growth trajectory",
            detail=f"Modest growth of {fmt_pct(g)}",
            contribution=8, kind=FactorKind.STRENGTH,
        ))
    elif g > -0.05:
        factors.append(Factor(
            name="Growth trajectory",
            detail=f"Flat turnover ({fmt_pct(g)})",
            contribution=0, kind=FactorKind.NEUTRAL,
        ))
    elif g > -0.15:
        factors.append(Factor(
            name="Growth trajectory",
            detail=f"Turnover declining {fmt_pct(g)}",
            contribution=-15, kind=FactorKind.RISK,
        ))
    else:
        factors.append(Factor(
            name="Growth trajectory",
            detail=f"Steep decline {fmt_pct(g)}",
            contribution=-25, kind=FactorKind.RISK,
        ))

    cov = f.turnover_cov
    if cov < 0.15:
        factors.append(Factor(
            name="Revenue consistency",
            detail=f"Low volatility (CoV {cov:.0%})",
            contribution=12, kind=FactorKind.STRENGTH,
        ))
    elif cov < 0.30:
        factors.append(Factor(
            name="Revenue consistency",
            detail=f"Moderate volatility (CoV {cov:.0%})",
            contribution=3, kind=FactorKind.NEUTRAL,
        ))
    else:
        factors.append(Factor(
            name="Revenue consistency",
            detail=f"High volatility (CoV {cov:.0%}) — seasonal or lumpy",
            contribution=-10, kind=FactorKind.RISK,
        ))

    trend = _trend(f.turnover_growth_pct)
    summary = f"{fmt_paise_short(f.avg_monthly_turnover_paise)}/mo, trend {trend.lower()}."
    return _mk("revenue_health", "Revenue Health", factors, trend, summary)


# ─── 2. Cash-Flow Strength ────────────────────────────────────────────────


def score_cash_flow(f: Features) -> DimensionScore:
    factors: list[Factor] = []

    r = f.inflow_outflow_ratio
    if r >= 1.15:
        factors.append(Factor(
            name="Inflow/outflow ratio",
            detail=f"{r:.2f}× — comfortably cash-positive",
            contribution=22, kind=FactorKind.STRENGTH,
        ))
    elif r >= 1.05:
        factors.append(Factor(
            name="Inflow/outflow ratio",
            detail=f"{r:.2f}× — modest surplus",
            contribution=10, kind=FactorKind.STRENGTH,
        ))
    elif r >= 0.98:
        factors.append(Factor(
            name="Inflow/outflow ratio",
            detail=f"{r:.2f}× — near break-even",
            contribution=-5, kind=FactorKind.NEUTRAL,
        ))
    else:
        factors.append(Factor(
            name="Inflow/outflow ratio",
            detail=f"{r:.2f}× — outflows exceed inflows",
            contribution=-25, kind=FactorKind.RISK,
        ))

    if f.bounce_count == 0:
        factors.append(Factor(
            name="Bounces / returns",
            detail="Zero bounces or ACH returns in the last 12 months",
            contribution=18, kind=FactorKind.STRENGTH,
        ))
    elif f.bounce_count <= 2:
        factors.append(Factor(
            name="Bounces / returns",
            detail=f"{f.bounce_count} bounces in 12m — occasional stress",
            contribution=-8, kind=FactorKind.RISK,
        ))
    else:
        factors.append(Factor(
            name="Bounces / returns",
            detail=f"{f.bounce_count} bounces in 12m — recurring liquidity stress",
            contribution=-25, kind=FactorKind.RISK,
        ))

    # Balance buffer vs outflow — how many months of expenses on hand
    if f.monthly_outflow_paise > 0:
        buffer_months = f.avg_daily_balance_paise / f.monthly_outflow_paise
    else:
        buffer_months = 0.0
    if buffer_months >= 2.0:
        factors.append(Factor(
            name="Balance buffer",
            detail=f"~{buffer_months:.1f} months of expenses in bank",
            contribution=15, kind=FactorKind.STRENGTH,
        ))
    elif buffer_months >= 1.0:
        factors.append(Factor(
            name="Balance buffer",
            detail=f"~{buffer_months:.1f} months of expenses in bank",
            contribution=5, kind=FactorKind.NEUTRAL,
        ))
    else:
        factors.append(Factor(
            name="Balance buffer",
            detail=f"Only ~{buffer_months:.1f} months of expenses in bank — thin buffer",
            contribution=-10, kind=FactorKind.RISK,
        ))

    trend = "IMPROVING" if r >= 1.10 else "STABLE" if r >= 1.0 else "DECLINING"
    summary = (
        f"{fmt_paise_short(f.monthly_surplus_paise)}/mo net surplus, "
        f"{f.bounce_count} bounces."
    )
    return _mk("cash_flow", "Cash-Flow Strength", factors, trend, summary)


# ─── 3. Digital Transaction Vitality ──────────────────────────────────────


def score_digital_vitality(f: Features) -> DimensionScore:
    factors: list[Factor] = []
    inflow_l = f.upi_monthly_inflow_paise / L_PAISE

    if inflow_l >= 10:
        factors.append(Factor(
            name="UPI volume",
            detail=f"{fmt_paise_short(f.upi_monthly_inflow_paise)}/mo UPI inflow",
            contribution=22, kind=FactorKind.STRENGTH,
        ))
    elif inflow_l >= 3:
        factors.append(Factor(
            name="UPI volume",
            detail=f"{fmt_paise_short(f.upi_monthly_inflow_paise)}/mo UPI inflow",
            contribution=12, kind=FactorKind.STRENGTH,
        ))
    elif inflow_l >= 0.5:
        factors.append(Factor(
            name="UPI volume",
            detail=f"{fmt_paise_short(f.upi_monthly_inflow_paise)}/mo — modest digital footprint",
            contribution=2, kind=FactorKind.NEUTRAL,
        ))
    else:
        factors.append(Factor(
            name="UPI volume",
            detail="Negligible UPI activity — mostly non-digital receipts",
            contribution=-8, kind=FactorKind.RISK,
        ))

    if f.upi_unique_payers >= 500:
        factors.append(Factor(
            name="Customer breadth",
            detail=f"{f.upi_unique_payers} unique payers/mo — diversified customer base",
            contribution=15, kind=FactorKind.STRENGTH,
        ))
    elif f.upi_unique_payers >= 100:
        factors.append(Factor(
            name="Customer breadth",
            detail=f"{f.upi_unique_payers} unique payers/mo",
            contribution=8, kind=FactorKind.STRENGTH,
        ))
    elif f.upi_unique_payers >= 25:
        factors.append(Factor(
            name="Customer breadth",
            detail=f"{f.upi_unique_payers} unique payers/mo — concentrated customer base",
            contribution=0, kind=FactorKind.NEUTRAL,
        ))
    else:
        factors.append(Factor(
            name="Customer breadth",
            detail=f"Only {f.upi_unique_payers} unique payers/mo — concentration risk",
            contribution=-10, kind=FactorKind.RISK,
        ))

    if f.upi_growth_pct is not None:
        if f.upi_growth_pct > 0.20:
            factors.append(Factor(
                name="Digital adoption trend",
                detail=f"UPI receipts growing {fmt_pct(f.upi_growth_pct)}",
                contribution=10, kind=FactorKind.STRENGTH,
            ))
        elif f.upi_growth_pct > 0:
            factors.append(Factor(
                name="Digital adoption trend",
                detail=f"UPI receipts modestly up {fmt_pct(f.upi_growth_pct)}",
                contribution=3, kind=FactorKind.NEUTRAL,
            ))
        else:
            factors.append(Factor(
                name="Digital adoption trend",
                detail=f"UPI receipts flat/declining {fmt_pct(f.upi_growth_pct)}",
                contribution=-8, kind=FactorKind.RISK,
            ))

    trend = _trend(f.upi_growth_pct, up_th=0.05, down_th=-0.05)
    summary = (
        f"{fmt_paise_short(f.upi_monthly_inflow_paise)}/mo across "
        f"{f.upi_unique_payers} payers."
    )
    return _mk("digital_vitality", "Digital Transaction Vitality", factors, trend, summary)


# ─── 4. Compliance Discipline ─────────────────────────────────────────────


def score_compliance(f: Features) -> DimensionScore:
    factors: list[Factor] = []
    pct = f.gst_filing_on_time_pct

    if pct >= 0.90:
        factors.append(Factor(
            name="GST filing timeliness",
            detail=f"{pct:.0%} of returns filed on time",
            contribution=30, kind=FactorKind.STRENGTH,
        ))
    elif pct >= 0.75:
        factors.append(Factor(
            name="GST filing timeliness",
            detail=f"{pct:.0%} on time — mostly disciplined",
            contribution=12, kind=FactorKind.STRENGTH,
        ))
    elif pct >= 0.60:
        factors.append(Factor(
            name="GST filing timeliness",
            detail=f"{pct:.0%} on time — mixed record",
            contribution=-8, kind=FactorKind.RISK,
        ))
    else:
        factors.append(Factor(
            name="GST filing timeliness",
            detail=f"Only {pct:.0%} on time — persistent lateness",
            contribution=-25, kind=FactorKind.RISK,
        ))

    if f.gst_avg_delay_days > 20:
        factors.append(Factor(
            name="Filing delay severity",
            detail=f"Avg late filings delayed {f.gst_avg_delay_days:.0f} days",
            contribution=-8, kind=FactorKind.RISK,
        ))

    if f.epfo_active:
        epfo_pct = f.epfo_filing_on_time_pct or 0
        if epfo_pct >= 0.90:
            factors.append(Factor(
                name="EPFO deposit discipline",
                detail=f"{epfo_pct:.0%} of PF deposits on time",
                contribution=15, kind=FactorKind.STRENGTH,
            ))
        elif epfo_pct >= 0.75:
            factors.append(Factor(
                name="EPFO deposit discipline",
                detail=f"{epfo_pct:.0%} of PF deposits on time",
                contribution=3, kind=FactorKind.NEUTRAL,
            ))
        else:
            factors.append(Factor(
                name="EPFO deposit discipline",
                detail=f"Only {epfo_pct:.0%} PF deposits on time",
                contribution=-12, kind=FactorKind.RISK,
            ))
    else:
        factors.append(Factor(
            name="EPFO coverage",
            detail="Not covered by EPFO — small workforce or informal",
            contribution=0, kind=FactorKind.NEUTRAL,
        ))

    trend = "STABLE"
    summary = f"GST {pct:.0%} on time" + (
        f", EPFO {(f.epfo_filing_on_time_pct or 0):.0%} on time" if f.epfo_active else ""
    )
    return _mk("compliance", "Compliance Discipline", factors, trend, summary)


# ─── 5. Employment Stability ──────────────────────────────────────────────


def score_employment(f: Features) -> DimensionScore:
    factors: list[Factor] = []

    if not f.epfo_active:
        factors.append(Factor(
            name="EPFO coverage",
            detail="Below EPFO threshold (typically <20 employees)",
            contribution=0, kind=FactorKind.NEUTRAL,
        ))
        factors.append(Factor(
            name="Employment signal",
            detail="Formal employment signal unavailable for this profile",
            contribution=0, kind=FactorKind.NEUTRAL,
        ))
        return _mk(
            "employment", "Employment Stability", factors, "UNKNOWN",
            "EPFO not applicable — small workforce or informal.",
        )

    factors.append(Factor(
        name="EPFO coverage",
        detail=f"Active EPFO establishment with {f.latest_headcount} employees",
        contribution=10, kind=FactorKind.STRENGTH,
    ))

    trend_pct = f.headcount_trend_pct
    if trend_pct is not None:
        if trend_pct > 0.05:
            factors.append(Factor(
                name="Headcount trend",
                detail=f"Workforce growing {fmt_pct(trend_pct)}",
                contribution=20, kind=FactorKind.STRENGTH,
            ))
        elif trend_pct > -0.05:
            factors.append(Factor(
                name="Headcount trend",
                detail=f"Workforce stable ({fmt_pct(trend_pct)})",
                contribution=8, kind=FactorKind.NEUTRAL,
            ))
        else:
            factors.append(Factor(
                name="Headcount trend",
                detail=f"Workforce shrinking {fmt_pct(trend_pct)}",
                contribution=-15, kind=FactorKind.RISK,
            ))
    else:
        factors.append(Factor(
            name="Headcount trend",
            detail="Short EPFO history — trend not yet meaningful",
            contribution=0, kind=FactorKind.NEUTRAL,
        ))

    epfo_pct = f.epfo_filing_on_time_pct or 0
    if epfo_pct >= 0.90:
        factors.append(Factor(
            name="Salary regularity",
            detail=f"Wages / PF paid on time {epfo_pct:.0%} of months",
            contribution=20, kind=FactorKind.STRENGTH,
        ))
    elif epfo_pct >= 0.75:
        factors.append(Factor(
            name="Salary regularity",
            detail=f"Wages paid on time {epfo_pct:.0%} of months",
            contribution=5, kind=FactorKind.NEUTRAL,
        ))
    else:
        factors.append(Factor(
            name="Salary regularity",
            detail=f"Irregular wage payments ({epfo_pct:.0%} on time)",
            contribution=-20, kind=FactorKind.RISK,
        ))

    trend = _trend(trend_pct)
    summary = f"{f.latest_headcount} employees, trend {trend.lower()}."
    return _mk("employment", "Employment Stability", factors, trend, summary)


# ─── 6. Obligation & Leverage ─────────────────────────────────────────────


def score_obligation_leverage(f: Features) -> DimensionScore:
    factors: list[Factor] = []

    if f.monthly_emi_paise == 0:
        factors.append(Factor(
            name="Existing debt burden",
            detail="No existing EMI obligations detected in bank data",
            contribution=15, kind=FactorKind.STRENGTH,
        ))
        # Being unlevered is good, but so is having debt-service history.
        factors.append(Factor(
            name="Repayment track record",
            detail="No prior loan history to observe — NTC uplift relies on cash-flow signals",
            contribution=-5, kind=FactorKind.NEUTRAL,
        ))
        trend = "UNKNOWN"
        summary = "Unlevered — no existing debt service."
        return _mk("obligation_leverage", "Obligation & Leverage", factors, trend, summary)

    # EMI-to-turnover ratio
    if f.avg_monthly_turnover_paise > 0:
        ratio_pct = f.monthly_emi_paise / f.avg_monthly_turnover_paise
    else:
        ratio_pct = 1.0
    if ratio_pct < 0.05:
        factors.append(Factor(
            name="EMI-to-turnover",
            detail=f"EMI is {ratio_pct:.0%} of monthly turnover — very light",
            contribution=15, kind=FactorKind.STRENGTH,
        ))
    elif ratio_pct < 0.15:
        factors.append(Factor(
            name="EMI-to-turnover",
            detail=f"EMI is {ratio_pct:.0%} of monthly turnover — comfortable",
            contribution=8, kind=FactorKind.STRENGTH,
        ))
    elif ratio_pct < 0.30:
        factors.append(Factor(
            name="EMI-to-turnover",
            detail=f"EMI is {ratio_pct:.0%} of monthly turnover — moderate",
            contribution=-5, kind=FactorKind.NEUTRAL,
        ))
    else:
        factors.append(Factor(
            name="EMI-to-turnover",
            detail=f"EMI is {ratio_pct:.0%} of monthly turnover — heavy",
            contribution=-20, kind=FactorKind.RISK,
        ))

    # DSCR proxy
    dscr = f.dscr_proxy or 0
    if dscr >= 2.5:
        factors.append(Factor(
            name="Debt-service coverage",
            detail=f"DSCR proxy {dscr:.1f}× — strong repayment capacity",
            contribution=25, kind=FactorKind.STRENGTH,
        ))
    elif dscr >= 1.5:
        factors.append(Factor(
            name="Debt-service coverage",
            detail=f"DSCR proxy {dscr:.1f}× — adequate cover",
            contribution=10, kind=FactorKind.STRENGTH,
        ))
    elif dscr >= 1.2:
        factors.append(Factor(
            name="Debt-service coverage",
            detail=f"DSCR proxy {dscr:.1f}× — thin cover",
            contribution=-8, kind=FactorKind.NEUTRAL,
        ))
    elif dscr >= 1.0:
        factors.append(Factor(
            name="Debt-service coverage",
            detail=f"DSCR proxy {dscr:.1f}× — barely servicing debt",
            contribution=-20, kind=FactorKind.RISK,
        ))
    else:
        factors.append(Factor(
            name="Debt-service coverage",
            detail=f"DSCR proxy {dscr:.1f}× — cash flow does not cover EMIs",
            contribution=-35, kind=FactorKind.RISK,
        ))

    trend = "STABLE"
    summary = f"EMI {fmt_paise_short(f.monthly_emi_paise)}/mo, DSCR {dscr:.1f}×."
    return _mk("obligation_leverage", "Obligation & Leverage", factors, trend, summary)


ALL_SCORERS: list[Callable[[Features], DimensionScore]] = [
    score_revenue_health,
    score_cash_flow,
    score_digital_vitality,
    score_compliance,
    score_employment,
    score_obligation_leverage,
]


def score_all_dimensions(f: Features) -> list[DimensionScore]:
    return [s(f) for s in ALL_SCORERS]
