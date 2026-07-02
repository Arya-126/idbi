"""Composite score, risk band, and credit decision.

The composite is the weighted sum of dimension scores (0-100 each), rescaled to
a familiar 0-1000 range so it reads like a bureau score. Risk bands and the
lending recommendation follow directly from the composite plus a few hard
gates on the underlying features (bounces, DSCR).
"""

from __future__ import annotations

from ..schemas import Decision, DimensionScore
from .features import Features, fmt_paise_short, L_PAISE


def compute_composite(dimensions: list[DimensionScore]) -> int:
    weighted = sum(d.score * d.weight for d in dimensions)
    return round(weighted * 10)  # → 0-1000


def risk_band(composite: int) -> str:
    if composite >= 750:
        return "A"
    if composite >= 600:
        return "B"
    if composite >= 450:
        return "C"
    return "D"


def _suggested_limit(band: str, features: Features) -> int:
    """A share of annual turnover, tempered by cash surplus.

    Cap on band-multiplier × avg monthly turnover; also cap at 18× monthly
    net surplus so we never issue a limit the borrower can't service.
    """
    turnover_multiplier = {"A": 3.0, "B": 2.0, "C": 1.0, "D": 0.0}[band]
    turnover_cap = int(features.avg_monthly_turnover_paise * turnover_multiplier)
    surplus = max(0, features.monthly_surplus_paise)
    surplus_cap = surplus * 18
    return min(turnover_cap, surplus_cap) if surplus_cap else turnover_cap


def _hard_gates(features: Features) -> list[str]:
    """Return blocking reasons that force REFER regardless of composite."""
    gates: list[str] = []
    if features.bounce_count >= 4:
        gates.append(f"{features.bounce_count} bounce incidents in the last 12 months")
    if features.dscr_proxy is not None and features.dscr_proxy < 1.0:
        gates.append(f"DSCR proxy {features.dscr_proxy:.1f}× — cash flow does not cover existing EMIs")
    if features.inflow_outflow_ratio and features.inflow_outflow_ratio < 0.95:
        gates.append("Net outflow exceeds inflow across the last 12 months")
    return gates


def decide(composite: int, band: str, features: Features) -> Decision:
    gates = _hard_gates(features)

    if band == "D" or len(gates) >= 2:
        return Decision(
            recommendation="DECLINE",
            suggested_limit_paise=0,
            suggested_tenor_months=0,
            suggested_roi_pct=0.0,
            rationale=(
                "Composite risk profile does not meet lending criteria. "
                + (f"Blocking factors: {'; '.join(gates)}." if gates else
                   "Cash-flow and compliance signals are insufficient.")
            ),
        )

    if band == "C" or gates:
        limit = _suggested_limit("C", features)
        return Decision(
            recommendation="REFER",
            suggested_limit_paise=limit,
            suggested_tenor_months=18,
            suggested_roi_pct=14.5,
            rationale=(
                "Marginal profile — recommend underwriter review. "
                + (f"Concerns: {'; '.join(gates)}." if gates else
                   "Consider requiring collateral or co-applicant.")
            ),
        )

    if band == "B":
        limit = _suggested_limit("B", features)
        return Decision(
            recommendation="APPROVE",
            suggested_limit_paise=limit,
            suggested_tenor_months=24,
            suggested_roi_pct=12.5,
            rationale=(
                "Sound profile with balanced signals. "
                f"Suggested limit ~{fmt_paise_short(limit)} at 12.5% p.a. over 24 months, "
                "reviewable after 6 months of good repayment."
            ),
        )

    # Band A
    limit = _suggested_limit("A", features)
    return Decision(
        recommendation="APPROVE",
        suggested_limit_paise=limit,
        suggested_tenor_months=36,
        suggested_roi_pct=10.5,
        rationale=(
            "Strong profile across cash-flow, compliance and revenue signals. "
            f"Suggested limit ~{fmt_paise_short(limit)} at 10.5% p.a. over 36 months, "
            "eligible for straight-through processing."
        ),
    )


def pick_top_strengths(dimensions: list[DimensionScore], n: int = 3) -> list[str]:
    factors = [
        (f, d) for d in dimensions for f in d.factors if f.kind.value == "STRENGTH"
    ]
    factors.sort(key=lambda x: x[0].contribution, reverse=True)
    return [f"{f.name} — {f.detail}" for f, _ in factors[:n]]


def pick_top_risks(dimensions: list[DimensionScore], n: int = 3) -> list[str]:
    factors = [
        (f, d) for d in dimensions for f in d.factors if f.kind.value == "RISK"
    ]
    factors.sort(key=lambda x: x[0].contribution)  # most negative first
    return [f"{f.name} — {f.detail}" for f, _ in factors[:n]]
