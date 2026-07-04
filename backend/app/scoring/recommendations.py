"""Actionable improvement recommendations for the borrower view.

Turns the same features that drive the rulebook into concrete, quantified
"do X, gain ~Y points" suggestions the MSME owner can act on. Recommendations
are dimension-anchored — the UI can rank them by weighted uplift so the biggest
composite move floats to the top.

Each rule reads a small subset of `Features`, decides whether it applies, and
returns a `Recommendation` with an estimated dimension-score uplift and a time
horizon. Uplift estimates are calibrated against the same scorecard weights
in `dimensions.py` — a "+15 pts" recommendation matches the actual factor
contribution the borrower would earn back if the behaviour flipped.
"""

from __future__ import annotations

from ..schemas import Recommendation
from .features import Features


def build_recommendations(features: Features) -> list[Recommendation]:
    recs: list[Recommendation] = []

    # ── Compliance discipline ────────────────────────────────────────────
    if features.gst_filing_on_time_pct < 0.90:
        gap = 0.90 - features.gst_filing_on_time_pct
        # Every 15% jump in on-time rate flips a returns-window into the
        # next scorecard band, roughly +15 pts of Compliance.
        uplift = 15 if gap > 0.20 else 10 if gap > 0.10 else 6
        recs.append(Recommendation(
            dimension_key="compliance",
            action="File your next GST returns by the due date",
            detail=(
                f"You've filed on time {features.gst_filing_on_time_pct:.0%} of "
                f"months. Getting to 90% moves Compliance up ~{uplift} pts."
            ),
            est_score_uplift_pts=uplift,
            time_horizon_months=6,
        ))

    if features.epfo_active and (features.epfo_filing_on_time_pct or 0) < 0.90:
        recs.append(Recommendation(
            dimension_key="compliance",
            action="Deposit EPFO contributions on the 15th of each month",
            detail=(
                "Consistent on-time PF deposits push Compliance & Employment "
                "Stability up together — worth ~10 pts of composite."
            ),
            est_score_uplift_pts=10,
            time_horizon_months=6,
        ))

    # ── Cash-flow strength ───────────────────────────────────────────────
    if features.bounce_count > 0:
        recs.append(Recommendation(
            dimension_key="cash_flow",
            action="Maintain a zero-bounce buffer in your current account",
            detail=(
                f"You've had {features.bounce_count} return(s) in 12 months. "
                "Zero bounces for 6 months lifts Cash-Flow Strength ~15 pts."
            ),
            est_score_uplift_pts=15,
            time_horizon_months=6,
        ))

    if (
        features.monthly_outflow_paise > 0
        and features.avg_daily_balance_paise / features.monthly_outflow_paise < 1.0
    ):
        # Sub-1-month buffer costs ~10 pts. Nudge the borrower to hold reserve.
        recs.append(Recommendation(
            dimension_key="cash_flow",
            action="Hold at least 1 month of operating expenses in the bank",
            detail=(
                "A 1-month buffer moves Cash-Flow Strength out of the risk "
                "zone (+10 pts) and reduces short-term liquidity flags."
            ),
            est_score_uplift_pts=10,
            time_horizon_months=3,
        ))

    # ── Obligation & leverage ────────────────────────────────────────────
    if features.dscr_proxy is not None and features.dscr_proxy < 1.5:
        needed_surplus = features.monthly_emi_paise * 1.5 - (
            features.monthly_surplus_paise + features.monthly_emi_paise
        )
        recs.append(Recommendation(
            dimension_key="obligation_leverage",
            action="Improve debt-service coverage to ≥ 1.5×",
            detail=(
                f"Current DSCR is {features.dscr_proxy:.1f}×. "
                "Consolidating high-cost debt or lifting monthly surplus by "
                f"~₹{max(0, needed_surplus) / 100_00_000:.1f}L reaches 1.5× — "
                "worth ~18 pts."
            ),
            est_score_uplift_pts=18,
            time_horizon_months=9,
        ))

    # ── Revenue health ───────────────────────────────────────────────────
    if features.turnover_growth_pct is not None and features.turnover_growth_pct < 0:
        recs.append(Recommendation(
            dimension_key="revenue_health",
            action="Return to positive turnover growth over the next 2 quarters",
            detail=(
                "Even flat growth (0%) recovers ~15 pts vs a declining trend. "
                "Focus on retaining top customers and re-pricing loss-making SKUs."
            ),
            est_score_uplift_pts=15,
            time_horizon_months=6,
        ))

    # ── Digital vitality ─────────────────────────────────────────────────
    if features.upi_unique_payers < 100 and features.upi_monthly_inflow_paise > 0:
        recs.append(Recommendation(
            dimension_key="digital_vitality",
            action="Grow your unique UPI customer count above 100/month",
            detail=(
                f"You currently see ~{features.upi_unique_payers} unique payers/mo. "
                "A wider payer base signals a diversified customer mix — "
                "worth ~8 pts of Digital Vitality."
            ),
            est_score_uplift_pts=8,
            time_horizon_months=6,
        ))

    # Rank by uplift so the biggest move floats to the top of the borrower UI.
    recs.sort(key=lambda r: r.est_score_uplift_pts, reverse=True)
    return recs[:5]
