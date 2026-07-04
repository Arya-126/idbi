"""Composite score, risk band, and credit decision.

The composite is the weighted sum of dimension scores (0-100 each), rescaled to
a familiar 0-1000 range so it reads like a bureau score. Risk bands and the
lending recommendation follow directly from the composite plus a few hard
gates on the underlying features (bounces, DSCR).
"""

from __future__ import annotations

from ..schemas import Decision, DimensionScore, LimitStep
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


def _suggested_limit(band: str, features: Features) -> tuple[int, list[LimitStep]]:
    """A share of annual turnover, tempered by cash surplus.

    Two caps:
      · Turnover cap: band multiplier × avg monthly turnover (A=3×, B=2×, C=1×).
      · Surplus cap: 18 months of net monthly cash surplus — never issue a
        limit the borrower's own cash flow can't service.

    Returns the limit AND the ordered steps that produced it, so the UI can
    render the same math the credit officer would walk through.
    """
    turnover_multiplier = {"A": 3.0, "B": 2.0, "C": 1.0, "D": 0.0}[band]
    turnover_cap = int(features.avg_monthly_turnover_paise * turnover_multiplier)
    surplus = max(0, features.monthly_surplus_paise)
    surplus_cap = surplus * 18
    final = min(turnover_cap, surplus_cap) if surplus_cap else turnover_cap
    binding = "surplus" if surplus_cap and surplus_cap < turnover_cap else "turnover"

    steps: list[LimitStep] = [
        LimitStep(
            label="Avg monthly turnover",
            value_paise=features.avg_monthly_turnover_paise,
            note="From GST outward taxable value, last 24 months",
        ),
        LimitStep(
            label=f"Turnover cap ({turnover_multiplier:g}× · band {band})",
            value_paise=turnover_cap,
            note=f"Band {band} caps at {turnover_multiplier:g}× monthly turnover",
        ),
        LimitStep(
            label="Monthly cash surplus",
            value_paise=surplus,
            note="Inflow − outflow from Account Aggregator bank data",
        ),
        LimitStep(
            label="Surplus cap (18× surplus)",
            value_paise=surplus_cap,
            note="Ensures 18 months of cash flow covers any drawdown",
        ),
        LimitStep(
            label="Suggested limit",
            value_paise=final,
            note=f"min of the two caps — {binding} cap is binding",
        ),
    ]
    return final, steps


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
            limit_workings=[],
        )

    if band == "C" or gates:
        limit, workings = _suggested_limit("C", features)
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
            limit_workings=workings,
        )

    if band == "B":
        limit, workings = _suggested_limit("B", features)
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
            limit_workings=workings,
        )

    # Band A
    limit, workings = _suggested_limit("A", features)
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
        limit_workings=workings,
    )


# Factors are ranked by contribution × dimension weight, so a +20 factor in a
# 0.12-weight dimension doesn't outrank a +15 factor in a 0.22-weight one.


def pick_top_strengths(dimensions: list[DimensionScore], n: int = 3) -> list[str]:
    factors = [
        (f, d) for d in dimensions for f in d.factors if f.kind.value == "STRENGTH"
    ]
    factors.sort(key=lambda x: x[0].contribution * x[1].weight, reverse=True)
    return [f"{f.name} — {f.detail}" for f, _ in factors[:n]]


def pick_top_risks(dimensions: list[DimensionScore], n: int = 3) -> list[str]:
    factors = [
        (f, d) for d in dimensions for f in d.factors if f.kind.value == "RISK"
    ]
    factors.sort(key=lambda x: x[0].contribution * x[1].weight)  # most negative first
    return [f"{f.name} — {f.detail}" for f, _ in factors[:n]]
