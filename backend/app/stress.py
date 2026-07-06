"""Portfolio stress testing — shock the book, re-score, report the migration.

Shocks are applied at the feature level (turnover down, bounces up, EMI up),
then every book member runs back through the same dimension scorers and
decision logic. No generator changes, nothing persisted — it answers "what
does a 20% revenue shock do to my band mix and exposure?" live.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from . import personas
from .portfolio import build_portfolio
from .schemas import (
    BandMigrationCell,
    StressResult,
    StressScenario,
    StressedEntry,
)
from .scoring.decision import compute_composite, decide, risk_band
from .scoring.dimensions import score_all_dimensions
from .scoring.engine import build_data_pack, _mask_unconsented
from .scoring.features import Features, extract_features


PRESETS: dict[str, StressScenario] = {
    "revenue_shock": StressScenario(
        key="revenue_shock", label="Revenue −20%", turnover_shock_pct=-0.20,
    ),
    "liquidity_stress": StressScenario(
        key="liquidity_stress", label="Liquidity stress (+2 bounces)", extra_bounces=2,
    ),
    "rate_stress": StressScenario(
        key="rate_stress", label="EMI burden +25%", emi_increase_pct=0.25,
    ),
    "combined": StressScenario(
        key="combined", label="Combined downturn",
        turnover_shock_pct=-0.15, extra_bounces=1, emi_increase_pct=0.15,
    ),
}


def _shock(f: Features, s: StressScenario) -> Features:
    """Apply the scenario to one borrower's features, keeping the derived
    quantities (ratio, surplus, DSCR) internally consistent."""
    scale = 1.0 + s.turnover_shock_pct

    new_inflow = int(f.monthly_inflow_paise * scale)
    new_surplus = new_inflow - f.monthly_outflow_paise
    new_ratio = (new_inflow / f.monthly_outflow_paise) if f.monthly_outflow_paise else 0.0

    new_emi = int(f.monthly_emi_paise * (1.0 + s.emi_increase_pct))
    new_dscr = ((new_surplus + new_emi) / new_emi) if new_emi > 0 else None

    return replace(
        f,
        avg_monthly_turnover_paise=int(f.avg_monthly_turnover_paise * scale),
        latest_3m_turnover_paise=int(f.latest_3m_turnover_paise * scale),
        oldest_3m_turnover_paise=int(f.oldest_3m_turnover_paise * scale),
        monthly_inflow_paise=new_inflow,
        monthly_surplus_paise=new_surplus,
        inflow_outflow_ratio=new_ratio,
        bounce_count=f.bounce_count + s.extra_bounces,
        monthly_emi_paise=new_emi,
        dscr_proxy=new_dscr,
        upi_monthly_inflow_paise=int(f.upi_monthly_inflow_paise * scale),
    )


_BAND_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
_REC_ORDER = {"APPROVE": 0, "REFER": 1, "DECLINE": 2}


def run_stress(scenario: StressScenario) -> StressResult:
    book = build_portfolio()

    migrations: dict[tuple[str, str], int] = {}
    stressed: list[StressedEntry] = []
    downgraded = 0
    worsened = 0
    exposure_at_risk = 0
    before_scores: list[int] = []
    after_scores: list[int] = []

    for entry in book.entries:
        persona = personas.get_persona(entry.gstin)
        if persona is None:
            continue
        pack = build_data_pack(entry.gstin)
        f = _shock(extract_features(pack), scenario)
        dims = _mask_unconsented(score_all_dimensions(f), pack.sources_excluded)
        comp = compute_composite(dims)
        band = risk_band(comp)
        rec = decide(comp, band, f).recommendation

        before_scores.append(entry.composite_score)
        after_scores.append(comp)

        if band != entry.risk_band:
            migrations[(entry.risk_band, band)] = migrations.get((entry.risk_band, band), 0) + 1
        if _BAND_ORDER[band] > _BAND_ORDER[entry.risk_band]:
            downgraded += 1
        if _REC_ORDER[rec] > _REC_ORDER[entry.recommendation]:
            worsened += 1
            exposure_at_risk += entry.suggested_limit_paise

        stressed.append(StressedEntry(
            gstin=entry.gstin,
            trade_name=entry.trade_name,
            band_before=entry.risk_band,
            band_after=band,  # type: ignore[arg-type]
            score_before=entry.composite_score,
            score_after=comp,
            recommendation_before=entry.recommendation,
            recommendation_after=rec,  # type: ignore[arg-type]
            exposure_paise=entry.suggested_limit_paise,
        ))

    stressed.sort(key=lambda e: e.score_after - e.score_before)
    n = max(1, len(before_scores))

    return StressResult(
        scenario=scenario,
        avg_score_before=round(sum(before_scores) / n, 1),
        avg_score_after=round(sum(after_scores) / n, 1),
        downgraded=downgraded,
        decisions_worsened=worsened,
        exposure_at_risk_paise=exposure_at_risk,
        migrations=[
            BandMigrationCell(from_band=fb, to_band=tb, count=c)  # type: ignore[arg-type]
            for (fb, tb), c in sorted(migrations.items())
        ],
        worst_hit=stressed[:10],
        generated_at=datetime.utcnow(),
    )
