"""Scoring orchestrator.

Ties the pieces together:

    Connectors (GST + AA + EPFO + UPI)
        → normalized DataPack
        → Features
        → 6 DimensionScores
        → composite + risk band + Decision
        → HealthCard

Callers use `score_gstin(gstin)` for the end-to-end path or
`score_data_pack(pack)` when they already have a DataPack (e.g. tests).
"""

from __future__ import annotations

from datetime import date, datetime

from ..connectors import ConnectorError, ConnectorSet, build_default_connectors
from ..consent import resolve as resolve_consent
from ..schemas import (
    AaProfile,
    ConsentSource,
    DataPack,
    DimensionScore,
    EpfoProfile,
    Factor,
    FactorKind,
    GstProfile,
    HealthCard,
    MlAssessment,
    MlDriver as MlDriverSchema,
    ScoreHistoryPoint,
    UpiProfile,
)
from .decision import (
    compute_composite,
    decide,
    pick_top_risks,
    pick_top_strengths,
    risk_band,
)
from .dimensions import score_all_dimensions
from .features import extract_features
from .recommendations import build_recommendations


_DEFAULT: ConnectorSet | None = None


def _default_connectors() -> ConnectorSet:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = build_default_connectors()
    return _DEFAULT


def build_data_pack(
    gstin: str,
    consent_handle: str | None = None,
    as_of: date | None = None,
) -> DataPack:
    """Pull every consented source through its connector and assemble a DataPack.

    A supplied consent handle is validated (unknown/revoked/expired → error);
    without one, the registry reuses or auto-issues a demo grant (see
    `app.consent`). The grant's `sources` list is enforced: a rail the
    borrower did not consent to is never fetched — its slot in the pack is an
    empty placeholder and the source is listed in `sources_excluded`.

    `as_of` (simulation-only): a future anchor date regenerates the pack as a
    fresh pull on that date. This bypasses the connector protocols — real
    rails have no as_of — but consent validation and source scoping apply
    identically. Powers the "simulate next month" demo control.

    In production this is also where per-source fetches get parallelized and
    retries/circuit-breakers live.
    """
    conn = _default_connectors()
    try:
        identity = conn.identity.fetch(gstin)
    except ConnectorError as e:
        raise KeyError(f"Unknown GSTIN: {gstin}") from e

    grant = resolve_consent(gstin, consent_handle)
    granted = set(grant.sources)
    excluded = [s.value for s in ConsentSource if s not in granted]

    sim = as_of is not None and as_of != date.today()
    if sim:
        from .. import personas as personas_mod

        raw = personas_mod.build_data_pack(gstin, as_of=as_of)
        if raw is None:
            raise KeyError(f"Unknown GSTIN: {gstin}")

    gst = (
        (raw.gst if sim else conn.gst.fetch(gstin))
        if ConsentSource.GST in granted
        else GstProfile(
            gstin=gstin,
            registration_date=identity.incorporation_date,
            filing_status="ACTIVE",
            returns=[],
        )
    )
    aa = (
        (raw.aa if sim else conn.aa.fetch(grant.consent_id, gstin))
        if ConsentSource.AA in granted
        else AaProfile(consent_handle=grant.consent_id, linked_accounts=[])
    )
    epfo = (
        (raw.epfo if sim else conn.epfo.fetch(gstin))
        if ConsentSource.EPFO in granted
        else EpfoProfile(establishment_id="", active=False, monthly=[])
    )
    upi = (
        (raw.upi if sim else conn.upi.fetch(gstin))
        if ConsentSource.UPI in granted
        else UpiProfile(vpa="", monthly=[])
    )

    # Bureau-if-available: display-only context, never scored. (In production
    # a bureau pull needs its own consent leg; the demo treats it as part of
    # the application's standing instructions.)
    try:
        bureau = conn.bureau.fetch(identity.pan, gstin)
    except ConnectorError:
        bureau = None

    return DataPack(
        identity=identity,
        gst=gst,
        aa=aa,
        epfo=epfo,
        upi=upi,
        # Simulated pulls keep the anchor date — snapshots must land on the
        # simulated period, not today's.
        fetched_at=raw.fetched_at if sim else datetime.utcnow(),
        sources_excluded=excluded,
        bureau=bureau,
    )


# Which dimension goes dark when a source is withheld. Compliance follows GST
# (its dominant factor); the EPFO sliver it loses is reflected via the EPFO
# coverage factor rather than blanking the whole dimension.
_SOURCE_DIMENSIONS: dict[str, list[str]] = {
    "GST": ["revenue_health", "compliance"],
    "AA": ["cash_flow", "obligation_leverage"],
    "UPI": ["digital_vitality"],
    "EPFO": ["employment"],
}


def _mask_unconsented(
    dimensions: list[DimensionScore], excluded_sources: list[str]
) -> list[DimensionScore]:
    dark = {
        dim for src in excluded_sources for dim in _SOURCE_DIMENSIONS.get(src, [])
    }
    if not dark:
        return dimensions
    out: list[DimensionScore] = []
    for d in dimensions:
        if d.key in dark:
            out.append(d.model_copy(update={
                "score": 0,
                "trend": "UNKNOWN",
                "consented": False,
                "factors": [Factor(
                    name="Not consented",
                    detail="Borrower did not share this data source — dimension excluded from the composite",
                    contribution=0,
                    kind=FactorKind.NEUTRAL,
                    code="NC-01",
                )],
                "summary": "Not scored — source not consented.",
            }))
        else:
            out.append(d)
    return out


def score_data_pack(pack: DataPack, *, benchmark: bool = True) -> HealthCard:
    from ..ml import get_model  # deferred: heavy import (numpy/sklearn)

    features = extract_features(pack)
    dimensions = score_all_dimensions(features)
    dimensions = _mask_unconsented(dimensions, pack.sources_excluded)
    composite = compute_composite(dimensions)
    band = risk_band(composite)
    decision = decide(composite, band, features)
    strengths = pick_top_strengths(dimensions)
    risks = pick_top_risks(dimensions)
    recommendations, path_to_next_band = build_recommendations(features)
    dimensions = _attach_peer_percentiles(pack.identity.sector, dimensions) if benchmark else dimensions
    # Score history is independent of the benchmark table — always compute it,
    # so the portfolio's trend column has data even during the benchmark-free
    # bootstrap pass.
    history = _score_history(pack, dimensions)

    model = get_model()
    ml = model.predict(features)
    agrees, summary = _ml_alignment(ml.probability_of_default, decision.recommendation)
    ml_assessment = MlAssessment(
        probability_of_default=ml.probability_of_default,
        confidence=ml.confidence,
        drivers=[
            MlDriverSchema(
                feature_key=d.feature_key,
                feature_label=d.feature_label,
                contribution=d.contribution,
                detail=d.detail,
            )
            for d in ml.drivers
        ],
        supports=[
            MlDriverSchema(
                feature_key=d.feature_key,
                feature_label=d.feature_label,
                contribution=d.contribution,
                detail=d.detail,
            )
            for d in ml.supports
        ],
        model_version=ml.model_version,
        trained_on_n_samples=model.trained_on_n,
        holdout_auc=model.holdout_auc,
        holdout_brier=model.holdout_brier,
        agrees_with_rulebook=agrees,
        summary=summary,
    )

    from datetime import date as _date

    def _period_date(period: str | None) -> _date | None:
        return _date.fromisoformat(period + "-01") if period else None

    # None = source absent — the UI renders "n/a" rather than a fake date.
    freshness_dates: dict[str, _date | None] = {
        "GST": _period_date(pack.gst.returns[-1].period if pack.gst.returns else None),
        "AA": pack.aa.linked_accounts[0].as_of if pack.aa.linked_accounts else None,
        "EPFO": _period_date(pack.epfo.monthly[-1].period if pack.epfo.monthly else None),
        "UPI": _period_date(pack.upi.monthly[-1].period if pack.upi.monthly else None),
    }

    # Record this scoring run as an observed history point (keyed by the
    # pack's anchor month, so simulated future pulls land on future periods).
    from .. import snapshots
    snapshots.record(
        pack.identity.gstin,
        pack.fetched_at.strftime("%Y-%m"),
        composite,
        band,
    )

    return HealthCard(
        enterprise=pack.identity,
        bureau=pack.bureau,
        composite_score=composite,
        risk_band=band,
        dimensions=dimensions,
        top_strengths=strengths,
        top_risks=risks,
        decision=decision,
        ml_assessment=ml_assessment,
        improvement_recommendations=recommendations,
        path_to_next_band=path_to_next_band,
        score_history=history,
        generated_at=datetime.utcnow(),
        data_freshness=freshness_dates,
    )


def _attach_peer_percentiles(sector: str, dimensions: list[DimensionScore]) -> list[DimensionScore]:
    """Rebuild each DimensionScore with `peer_percentile` filled in.

    Failure to build benchmarks (e.g. during a bootstrap where portfolio isn't
    ready) should be non-fatal — return the dimensions untouched.
    """
    from .benchmarks import get_benchmarks

    try:
        bench = get_benchmarks()
    except Exception:
        return dimensions

    out: list[DimensionScore] = []
    for d in dimensions:
        if not d.consented:
            out.append(d)  # a 0 from withheld consent is not a peer rank
            continue
        pct = bench.percentile(sector, d.key, d.score)
        out.append(d.model_copy(update={"peer_percentile": pct}))
    return out


def _score_history(pack: DataPack, dimensions: list[DimensionScore]) -> list[ScoreHistoryPoint]:
    """Reconstruct 6 sliding-window snapshots of the composite score.

    Real time-series scoring would replay historical data pulls. Here we
    approximate: for each anchor month k months back (k=6,5,4,3,2,1,0), take
    the subset of the current DataPack whose periods are older than that
    anchor, re-run feature extraction on the truncated pack, and emit the
    resulting composite/band.
    """
    from ..schemas import (
        AaProfile, BankAccount, DataPack as DP, EpfoProfile,
        GstProfile, UpiProfile,
    )
    from .dimensions import score_all_dimensions
    from .features import extract_features

    def _period_le(period: str, anchor_ym: tuple[int, int]) -> bool:
        y, m = int(period[:4]), int(period[5:7])
        return (y, m) <= anchor_ym

    def _sub(y: int, m: int, months_back: int) -> tuple[int, int]:
        y2, m2 = y, m - months_back
        while m2 <= 0:
            m2 += 12
            y2 -= 1
        return y2, m2

    from .. import snapshots

    latest_period = pack.gst.returns[-1].period if pack.gst.returns else None
    if not latest_period:
        return []

    y, m = int(latest_period[:4]), int(latest_period[5:7])
    points: list[ScoreHistoryPoint] = []
    for months_back in range(6, -1, -1):
        anchor = _sub(y, m, months_back)
        gst_returns = [r for r in pack.gst.returns if _period_le(r.period, anchor)]
        epfo_monthly = [em for em in pack.epfo.monthly if _period_le(em.period, anchor)]
        upi_monthly = [um for um in pack.upi.monthly if _period_le(um.period, anchor)]
        # AA txns: keep those whose date is on or before the anchor month end.
        anchor_month_end = _month_end(anchor[0], anchor[1])
        aa_accounts: list[BankAccount] = []
        for acc in pack.aa.linked_accounts:
            txns_kept = [t for t in acc.transactions if t.date <= anchor_month_end]
            aa_accounts.append(acc.model_copy(update={
                "transactions": txns_kept,
                "as_of": anchor_month_end,
            }))
        if not gst_returns:
            continue  # skip windows with no data
        truncated = DP(
            identity=pack.identity,
            gst=GstProfile(
                gstin=pack.gst.gstin,
                registration_date=pack.gst.registration_date,
                filing_status=pack.gst.filing_status,
                returns=gst_returns,
            ),
            aa=AaProfile(consent_handle=pack.aa.consent_handle, linked_accounts=aa_accounts),
            epfo=EpfoProfile(
                establishment_id=pack.epfo.establishment_id,
                active=pack.epfo.active,
                monthly=epfo_monthly,
            ),
            upi=UpiProfile(vpa=pack.upi.vpa, monthly=upi_monthly),
            fetched_at=pack.fetched_at,
            sources_excluded=pack.sources_excluded,
        )
        f = extract_features(truncated)
        dims = _mask_unconsented(score_all_dimensions(f), pack.sources_excluded)
        comp = compute_composite(dims)
        band = risk_band(comp)
        points.append(ScoreHistoryPoint(
            period=f"{anchor[0]:04d}-{anchor[1]:02d}",
            composite_score=comp,
            risk_band=band,
        ))

    # Overlay OBSERVED points — real recorded scoring runs beat the
    # reconstructed approximation wherever both exist, and observed periods
    # outside the reconstruction window (e.g. simulated future pulls) are
    # appended so the chart shows the whole known trajectory.
    obs = snapshots.observed(pack.identity.gstin)
    if obs:
        by_period = {p.period: p for p in points}
        for period, (score, band_) in obs.items():
            by_period[period] = ScoreHistoryPoint(
                period=period,
                composite_score=score,
                risk_band=band_,  # type: ignore[arg-type]
                observed=True,
            )
        points = [by_period[k] for k in sorted(by_period)][-10:]
    return points


def _month_end(y: int, m: int):
    from calendar import monthrange
    from datetime import date as _date
    return _date(y, m, monthrange(y, m)[1])


def _ml_alignment(pd: float, recommendation: str) -> tuple[bool, str]:
    """Agreement flag + one-liner comparing ML to rulebook.

    The boolean travels on the API contract (`agrees_with_rulebook`) so the
    UI never has to infer agreement from the summary wording.
    """
    if pd < 0.05:
        risk_label = "very low"
    elif pd < 0.12:
        risk_label = "low"
    elif pd < 0.25:
        risk_label = "moderate"
    elif pd < 0.45:
        risk_label = "elevated"
    else:
        risk_label = "high"

    aligned = (
        (recommendation == "APPROVE" and pd < 0.20)
        or (recommendation == "REFER" and 0.10 <= pd <= 0.45)
        or (recommendation == "DECLINE" and pd > 0.25)
    )
    prefix = "Model agrees" if aligned else "Model disagrees"
    return aligned, f"{prefix} — predicts {risk_label} default risk ({pd * 100:.1f}%)."


def what_if(gstin: str, req, consent_handle: str | None = None):
    """Sensitivity simulator: apply officer-chosen overrides to the borrower's
    real features and re-run scorecard + decision + ML. Nothing is persisted —
    this answers "what moves the needle" live on the card."""
    from dataclasses import replace

    from ..ml import get_model
    from ..schemas import WhatIfResponse

    pack = build_data_pack(gstin, consent_handle)
    features = extract_features(pack)

    def _score(f):
        dims = _mask_unconsented(score_all_dimensions(f), pack.sources_excluded)
        comp = compute_composite(dims)
        band = risk_band(comp)
        rec = decide(comp, band, f).recommendation
        pd_ = get_model().predict(f).probability_of_default
        return comp, band, rec, pd_

    base_comp, base_band, base_rec, base_pd = _score(features)

    changed: list[str] = []
    new_f = features
    if req.gst_filing_on_time_pct is not None:
        new_f = replace(new_f, gst_filing_on_time_pct=req.gst_filing_on_time_pct,
                        gst_avg_delay_days=0.0 if req.gst_filing_on_time_pct >= 0.95
                        else new_f.gst_avg_delay_days)
        changed.append(f"GST on-time → {req.gst_filing_on_time_pct:.0%}")
    if req.bounce_count is not None:
        new_f = replace(new_f, bounce_count=req.bounce_count)
        changed.append(f"bounces → {req.bounce_count}")
    if req.turnover_growth_pct is not None:
        new_f = replace(new_f, turnover_growth_pct=req.turnover_growth_pct)
        changed.append(f"growth → {req.turnover_growth_pct:+.0%}")
    if req.balance_buffer_months is not None and new_f.monthly_outflow_paise > 0:
        new_f = replace(
            new_f,
            avg_daily_balance_paise=int(req.balance_buffer_months * new_f.monthly_outflow_paise),
        )
        changed.append(f"balance buffer → {req.balance_buffer_months:.1f} mo")
    if req.upi_unique_payers is not None:
        new_f = replace(new_f, upi_unique_payers=req.upi_unique_payers)
        changed.append(f"UPI payers → {req.upi_unique_payers}")

    new_comp, new_band, new_rec, new_pd = _score(new_f) if changed else (
        base_comp, base_band, base_rec, base_pd
    )

    buffer_months = (
        features.avg_daily_balance_paise / features.monthly_outflow_paise
        if features.monthly_outflow_paise > 0 else 0.0
    )
    return WhatIfResponse(
        current={
            "gst_filing_on_time_pct": features.gst_filing_on_time_pct,
            "bounce_count": float(features.bounce_count),
            "turnover_growth_pct": features.turnover_growth_pct or 0.0,
            "balance_buffer_months": round(buffer_months, 2),
            "upi_unique_payers": float(features.upi_unique_payers),
        },
        base_composite=base_comp,
        base_band=base_band,  # type: ignore[arg-type]
        base_recommendation=base_rec,  # type: ignore[arg-type]
        base_pd=base_pd,
        new_composite=new_comp,
        new_band=new_band,  # type: ignore[arg-type]
        new_recommendation=new_rec,  # type: ignore[arg-type]
        new_pd=new_pd,
        delta_pts=new_comp - base_comp,
        changed=changed,
    )


def score_gstin(
    gstin: str,
    consent_handle: str | None = None,
    *,
    benchmark: bool = True,
    as_of: date | None = None,
) -> HealthCard:
    """Score by GSTIN.

    Pass benchmark=False when scoring the population from inside
    `benchmarks._build_benchmarks` to break the potential recursion between
    peer-percentile lookup and its own construction. `as_of` simulates a
    fresh pull on a later date (see build_data_pack).
    """
    pack = build_data_pack(gstin, consent_handle, as_of=as_of)
    return score_data_pack(pack, benchmark=benchmark)
