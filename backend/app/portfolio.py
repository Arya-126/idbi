"""Portfolio dashboard — the credit officer's "book" view.

At startup we generate ~25 additional sampled MSMEs, register them alongside
the 5 demo personas (so their health cards are viewable too), and pre-compute
a cached `PortfolioSummary`. The dashboard queries this cached summary — no
per-request scoring of the whole book.

Portfolio quality metrics returned:
  · Band distribution (A/B/C/D)
  · Sector mix
  · Recommendation mix
  · Total exposure = Σ suggested_limit for APPROVED / REFER entries
  · Watchlist = REFER + DECLINE + ML PD>20%
  · NTC/NTB count = flagged NTC (no bureau footprint) or NTB (banks
    elsewhere, data via AA), approved anyway

The summary is cached after the first build; POST /api/portfolio/refresh
invalidates and rebuilds it.
"""

from __future__ import annotations

import random
from collections import Counter
from datetime import date, datetime

from . import personas
from .ml_data import sample_persona
from .personas import Persona
from .schemas import (
    ConcentrationSummary,
    PortfolioBucket,
    PortfolioEntry,
    PortfolioSummary,
    SectorExposure,
    VintageCohort,
)
from .scoring.engine import score_gstin


PORTFOLIO_SIZE = 25   # sampled MSMEs added to the 5 demos
PORTFOLIO_SEED = 20260702


_summary: PortfolioSummary | None = None
_sampled: list[Persona] = []


def _register_sampled_personas(n: int, seed: int) -> list[Persona]:
    """Sample and register n personas so they're addressable by GSTIN.

    Idempotent: the book membership is sampled once per process, so a
    refresh re-scores the same 30 firms instead of growing the registry.
    """
    if _sampled:
        return _sampled
    rng = random.Random(seed)
    for i in range(n):
        while True:
            p = sample_persona(rng, i)
            if p.gstin not in personas.PERSONAS_BY_GSTIN:
                break  # unique GSTIN
        personas.PERSONAS_BY_GSTIN[p.gstin] = p
        _sampled.append(p)
    return _sampled


def _build_entry(p: Persona) -> PortfolioEntry:
    # benchmark=False during portfolio build — the benchmarks themselves are
    # constructed from these calls, so recurring would deadlock.
    card = score_gstin(p.gstin, benchmark=False)

    # Trend from the score history — recent vs earlier window, with a lower
    # bar so young MSMEs (<6 history points) still get a directional read.
    trend = "UNKNOWN"
    hist = card.score_history
    if len(hist) >= 3:
        half = max(1, len(hist) // 3)
        recent = sum(pt.composite_score for pt in hist[-half:]) / half
        earlier = sum(pt.composite_score for pt in hist[:half]) / half
        delta = recent - earlier
        if delta > 15:
            trend = "IMPROVING"
        elif delta < -15:
            trend = "DECLINING"
        else:
            trend = "STABLE"

    # EWS: light-touch triggers derived from the health card itself.
    ews_flags: list[str] = []
    if trend == "DECLINING":
        ews_flags.append("Score trending down")
    if card.ml_assessment.probability_of_default > 0.15:
        ews_flags.append(f"PD elevated ({card.ml_assessment.probability_of_default * 100:.0f}%)")
    for risk in card.top_risks[:2]:
        # Surface the two biggest risk headlines only (trim the "— detail").
        head = risk.split(" — ", 1)[0]
        ews_flags.append(head)
    # Dedupe while preserving order.
    seen = set()
    ews_flags = [f for f in ews_flags if not (f in seen or seen.add(f))]

    # Watch-list rules (unchanged behaviour + trend signal).
    reasons: list[str] = []
    if card.decision.recommendation == "DECLINE":
        reasons.append("Rulebook declines")
    if card.ml_assessment.probability_of_default > 0.20:
        reasons.append(f"ML PD {card.ml_assessment.probability_of_default * 100:.0f}%")
    if card.decision.recommendation == "REFER":
        reasons.append("Referred for underwriter review")
    if trend == "DECLINING":
        reasons.append("Trend declining")

    demo_gstins = {p.gstin for p in personas.PERSONAS[:5]}

    today = date.today()
    vintage_months = max(
        0,
        (today.year - p.incorporation_date.year) * 12
        + (today.month - p.incorporation_date.month),
    )

    return PortfolioEntry(
        gstin=p.gstin,
        trade_name=p.trade_name,
        sector=p.sector,
        sub_sector=p.sub_sector,
        msme_category=p.msme_category,
        registered_city=p.registered_city,
        composite_score=card.composite_score,
        risk_band=card.risk_band,
        recommendation=card.decision.recommendation,
        probability_of_default=card.ml_assessment.probability_of_default,
        monthly_turnover_paise=int(p.monthly_turnover_lakhs * 10_000_000),
        suggested_limit_paise=card.decision.suggested_limit_paise,
        is_demo=p.gstin in demo_gstins,
        is_ntc=p.is_ntc,
        is_ntb=p.is_ntb,
        is_watchlist=len(reasons) > 0,
        watchlist_reason=" · ".join(reasons) if reasons else None,
        trend=trend,  # type: ignore[arg-type]
        ews_flags=ews_flags[:3],
        ml_divergent=not card.ml_assessment.agrees_with_rulebook,
        vintage_months=vintage_months,
    )


def _concentration(entries: list[PortfolioEntry]) -> ConcentrationSummary | None:
    """Diversification guardrails over the live (APPROVE/REFER) exposure."""
    live = [e for e in entries if e.recommendation in ("APPROVE", "REFER")
            and e.suggested_limit_paise > 0]
    total = sum(e.suggested_limit_paise for e in live)
    if total == 0:
        return None

    by_sector: dict[str, int] = {}
    for e in live:
        by_sector[e.sector] = by_sector.get(e.sector, 0) + e.suggested_limit_paise

    sector_cap = 0.25
    single_cap = 0.10
    exposures = sorted(
        (
            SectorExposure(
                sector=s,
                exposure_paise=v,
                share=v / total,
                breach=v / total > sector_cap,
            )
            for s, v in by_sector.items()
        ),
        key=lambda x: -x.exposure_paise,
    )
    hhi = sum(x.share ** 2 for x in exposures)
    biggest = max(live, key=lambda e: e.suggested_limit_paise)
    single_share = biggest.suggested_limit_paise / total

    breaches = [
        f"{x.sector} at {x.share:.0%} of exposure (cap {sector_cap:.0%})"
        for x in exposures if x.breach
    ]
    if single_share > single_cap:
        breaches.append(
            f"{biggest.trade_name} alone is {single_share:.0%} of exposure "
            f"(cap {single_cap:.0%})"
        )

    return ConcentrationSummary(
        hhi=round(hhi, 3),
        top_sector=exposures[0].sector,
        top_sector_share=round(exposures[0].share, 3),
        single_name_max=biggest.trade_name,
        single_name_max_share=round(single_share, 3),
        sector_exposures=exposures,
        breaches=breaches,
    )


_COHORTS: list[tuple[str, str, int, int]] = [
    ("lt1y", "< 1 year", 0, 12),
    ("1to3y", "1–3 years", 12, 36),
    ("3to5y", "3–5 years", 36, 60),
    ("gt5y", "5+ years", 60, 10_000),
]


def _vintage_cohorts(entries: list[PortfolioEntry]) -> list[VintageCohort]:
    """Score/approval/PD by firm age — proves young (credit-invisible) firms
    are scoreable, and shows how quality varies by vintage."""
    out: list[VintageCohort] = []
    for key, label, lo, hi in _COHORTS:
        members = [e for e in entries if lo <= e.vintage_months < hi]
        if not members:
            continue
        out.append(VintageCohort(
            key=key,
            label=label,
            count=len(members),
            avg_score=round(sum(e.composite_score for e in members) / len(members), 1),
            approval_rate=round(
                sum(1 for e in members if e.recommendation == "APPROVE") / len(members), 3,
            ),
            avg_pd=round(
                sum(e.probability_of_default for e in members) / len(members), 4,
            ),
        ))
    return out


def _buckets(counts: Counter, total: int, labels: dict[str, str] | None = None) -> list[PortfolioBucket]:
    out: list[PortfolioBucket] = []
    for k, c in counts.most_common():
        out.append(PortfolioBucket(
            key=k,
            label=(labels or {}).get(k, k),
            count=c,
            share=c / total if total else 0.0,
        ))
    return out


def build_portfolio() -> PortfolioSummary:
    """Build (once) and cache the portfolio summary."""
    global _summary
    if _summary is not None:
        return _summary

    sampled = _register_sampled_personas(PORTFOLIO_SIZE, PORTFOLIO_SEED)

    all_personas = personas.PERSONAS + sampled
    entries = [_build_entry(p) for p in all_personas]
    total = len(entries)

    band_counts = Counter(e.risk_band for e in entries)
    sector_counts = Counter(e.sector for e in entries)
    rec_counts = Counter(e.recommendation for e in entries)

    ntc_ntb = sum(
        1 for e in entries
        if (e.is_ntc or e.is_ntb) and e.recommendation == "APPROVE"
    )

    total_exposure = sum(
        e.suggested_limit_paise for e in entries
        if e.recommendation in ("APPROVE", "REFER")
    )

    avg_score = sum(e.composite_score for e in entries) / total
    avg_pd = sum(e.probability_of_default for e in entries) / total

    _summary = PortfolioSummary(
        total_msmes=total,
        avg_composite_score=avg_score,
        avg_pd=avg_pd,
        total_exposure_paise=total_exposure,
        ntc_ntb_count=ntc_ntb,
        watchlist_count=sum(1 for e in entries if e.is_watchlist),
        ml_divergent_count=sum(1 for e in entries if e.ml_divergent),
        concentration=_concentration(entries),
        vintage_cohorts=_vintage_cohorts(entries),
        band_distribution=_buckets(
            band_counts, total,
            labels={"A": "A · Prime", "B": "B · Standard",
                    "C": "C · Marginal", "D": "D · High risk"},
        ),
        sector_mix=_buckets(sector_counts, total),
        recommendation_mix=_buckets(
            rec_counts, total,
            labels={"APPROVE": "Approve", "REFER": "Refer", "DECLINE": "Decline"},
        ),
        entries=sorted(entries, key=lambda e: (-e.probability_of_default, -e.composite_score)),
        generated_at=datetime.utcnow(),
    )
    return _summary


def invalidate() -> None:
    """Drop the portfolio cache. Also invalidates sector benchmarks — they're
    derived from the portfolio so they must be rebuilt in step."""
    global _summary
    _summary = None
    from .scoring.benchmarks import invalidate as invalidate_bench
    invalidate_bench()
