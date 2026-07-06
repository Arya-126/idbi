"""Actionable improvement recommendations for the borrower view.

Every suggestion is quantified by actually applying the behavioural change to
the borrower's own `Features` (via `dataclasses.replace`) and re-running the
scorecard — the "+N pts" a borrower sees is the true composite delta on the
0-1000 scale, not a hand-calibrated constant.

The same machinery stacks recommendations greedily (biggest uplift first) to
answer "what would it take to reach the next band?" — surfaced on the card as
`path_to_next_band`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from ..schemas import PathToNextBand, Recommendation
from .features import Features


# Band thresholds mirror decision.risk_band — the next band up from each.
_NEXT_BAND: dict[str, tuple[str, int]] = {
    "D": ("C", 450),
    "C": ("B", 600),
    "B": ("A", 750),
}


@dataclass(frozen=True)
class _Rule:
    dimension_key: str
    action: str
    detail: Callable[[Features, int], str]  # (features, computed uplift) → text
    applies: Callable[[Features], bool]
    transform: Callable[[Features], Features]
    time_horizon_months: int


def _composite_of(features: Features) -> int:
    # Local import: dimensions ← features, and decision ← features; neither
    # imports recommendations, so this stays cycle-free.
    from .decision import compute_composite
    from .dimensions import score_all_dimensions

    return compute_composite(score_all_dimensions(features))


_RULES: list[_Rule] = [
    _Rule(
        dimension_key="compliance",
        action="File your next GST returns by the due date",
        detail=lambda f, up: (
            f"You've filed on time {f.gst_filing_on_time_pct:.0%} of months. "
            f"A 95% on-time record is worth ~{up} pts on your 1000-point score."
        ),
        applies=lambda f: f.gst_filing_on_time_pct < 0.90,
        transform=lambda f: replace(
            f, gst_filing_on_time_pct=0.95, gst_avg_delay_days=0.0
        ),
        time_horizon_months=6,
    ),
    _Rule(
        dimension_key="compliance",
        action="Deposit EPFO contributions on the 15th of each month",
        detail=lambda f, up: (
            f"PF deposits land on time {(f.epfo_filing_on_time_pct or 0):.0%} of "
            f"months. Consistent deposits lift Compliance and Employment "
            f"Stability together — ~{up} pts."
        ),
        applies=lambda f: f.epfo_active and (f.epfo_filing_on_time_pct or 0) < 0.90,
        transform=lambda f: replace(f, epfo_filing_on_time_pct=0.95),
        time_horizon_months=6,
    ),
    _Rule(
        dimension_key="cash_flow",
        action="Maintain a zero-bounce buffer in your current account",
        detail=lambda f, up: (
            f"You've had {f.bounce_count} return(s) in 12 months. Six clean "
            f"months recovers ~{up} pts."
        ),
        applies=lambda f: f.bounce_count > 0,
        transform=lambda f: replace(f, bounce_count=0),
        time_horizon_months=6,
    ),
    _Rule(
        dimension_key="cash_flow",
        action="Hold at least 1 month of operating expenses in the bank",
        detail=lambda f, up: (
            f"Your average balance covers less than a month of outflows. A "
            f"1-month buffer is worth ~{up} pts and clears liquidity flags."
        ),
        applies=lambda f: (
            f.monthly_outflow_paise > 0
            and f.avg_daily_balance_paise / f.monthly_outflow_paise < 1.0
        ),
        transform=lambda f: replace(
            f,
            avg_daily_balance_paise=f.monthly_outflow_paise,
            min_balance_paise=max(f.min_balance_paise, f.monthly_outflow_paise // 5),
        ),
        time_horizon_months=3,
    ),
    _Rule(
        dimension_key="obligation_leverage",
        action="Improve debt-service coverage to ≥ 1.5×",
        detail=lambda f, up: (
            f"Current DSCR is {(f.dscr_proxy or 0):.1f}×. Consolidating "
            f"high-cost debt or lifting monthly surplus to reach 1.5× is "
            f"worth ~{up} pts."
        ),
        applies=lambda f: f.dscr_proxy is not None and f.dscr_proxy < 1.5,
        transform=lambda f: replace(f, dscr_proxy=1.5),
        time_horizon_months=9,
    ),
    _Rule(
        dimension_key="revenue_health",
        action="Return to positive turnover growth over the next 2 quarters",
        detail=lambda f, up: (
            f"Turnover is trending down. Even flat growth (0%) recovers "
            f"~{up} pts; focus on retaining top customers first."
        ),
        applies=lambda f: (
            f.turnover_growth_pct is not None and f.turnover_growth_pct < 0
        ),
        transform=lambda f: replace(f, turnover_growth_pct=0.0),
        time_horizon_months=6,
    ),
    _Rule(
        dimension_key="digital_vitality",
        action="Grow your unique UPI customer count above 100/month",
        detail=lambda f, up: (
            f"You currently see ~{f.upi_unique_payers} unique payers/mo. A "
            f"wider payer base signals a diversified customer mix — ~{up} pts."
        ),
        applies=lambda f: (
            f.upi_unique_payers < 100 and f.upi_monthly_inflow_paise > 0
        ),
        transform=lambda f: replace(f, upi_unique_payers=120),
        time_horizon_months=6,
    ),
]

_MIN_UPLIFT_PTS = 3  # drop suggestions that barely move the composite


def build_recommendations(
    features: Features,
) -> tuple[list[Recommendation], PathToNextBand | None]:
    """Quantified recommendations + the greedy path to the next band."""
    from .decision import risk_band

    base_composite = _composite_of(features)

    scored: list[tuple[_Rule, int]] = []
    for rule in _RULES:
        if not rule.applies(features):
            continue
        uplift = _composite_of(rule.transform(features)) - base_composite
        if uplift >= _MIN_UPLIFT_PTS:
            scored.append((rule, uplift))
    scored.sort(key=lambda x: x[1], reverse=True)

    recs = [
        Recommendation(
            dimension_key=rule.dimension_key,
            action=rule.action,
            detail=rule.detail(features, uplift),
            est_score_uplift_pts=uplift,
            time_horizon_months=rule.time_horizon_months,
        )
        for rule, uplift in scored[:5]
    ]

    # ── Path to the next band: stack the winning rules cumulatively ────────
    band = risk_band(base_composite)
    path: PathToNextBand | None = None
    if band in _NEXT_BAND and scored:
        target_band, threshold = _NEXT_BAND[band]
        current = features
        composite = base_composite
        actions: list[str] = []
        horizon = 0
        for rule, _ in scored:
            current = rule.transform(current)
            new_composite = _composite_of(current)
            if new_composite <= composite:
                continue  # stacking made it redundant — skip, keep going
            composite = new_composite
            actions.append(rule.action)
            horizon = max(horizon, rule.time_horizon_months)
            if composite >= threshold:
                break
        if actions:
            path = PathToNextBand(
                current_band=band,  # type: ignore[arg-type]
                target_band=target_band,  # type: ignore[arg-type]
                achievable=composite >= threshold,
                projected_score=composite,
                uplift_pts=composite - base_composite,
                actions=actions,
                time_horizon_months=horizon,
            )
    return recs, path
