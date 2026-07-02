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
from datetime import datetime

from . import personas
from .ml_data import sample_persona
from .personas import Persona
from .schemas import (
    PortfolioBucket,
    PortfolioEntry,
    PortfolioSummary,
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
    card = score_gstin(p.gstin)

    # Watch-list rules
    reasons: list[str] = []
    if card.decision.recommendation == "DECLINE":
        reasons.append("Rulebook declines")
    if card.ml_assessment.probability_of_default > 0.20:
        reasons.append(f"ML PD {card.ml_assessment.probability_of_default * 100:.0f}%")
    if card.decision.recommendation == "REFER":
        reasons.append("Referred for underwriter review")

    demo_gstins = {p.gstin for p in personas.PERSONAS[:5]}

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
    )


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
    global _summary
    _summary = None
