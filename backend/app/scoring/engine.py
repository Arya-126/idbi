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

from datetime import datetime

from ..connectors import ConnectorError, ConnectorSet, build_default_connectors
from ..consent import resolve as resolve_consent
from ..schemas import (
    DataPack,
    DimensionScore,
    HealthCard,
    MlAssessment,
    MlDriver as MlDriverSchema,
    ScoreHistoryPoint,
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


def build_data_pack(gstin: str, consent_handle: str | None = None) -> DataPack:
    """Pull every source through its connector and assemble a DataPack.

    A supplied consent handle is validated (unknown/revoked/expired → error);
    without one, the registry reuses or auto-issues a demo grant (see
    `app.consent`). In production this is also where per-source fetches get
    parallelized and retries/circuit-breakers live.
    """
    conn = _default_connectors()
    try:
        identity = conn.identity.fetch(gstin)
    except ConnectorError as e:
        raise KeyError(f"Unknown GSTIN: {gstin}") from e

    grant = resolve_consent(gstin, consent_handle)

    return DataPack(
        identity=identity,
        gst=conn.gst.fetch(gstin),
        aa=conn.aa.fetch(grant.consent_id, gstin),
        epfo=conn.epfo.fetch(gstin),
        upi=conn.upi.fetch(gstin),
        fetched_at=datetime.utcnow(),
    )


def score_data_pack(pack: DataPack, *, benchmark: bool = True) -> HealthCard:
    from ..ml import get_model  # deferred: heavy import (numpy/sklearn)

    features = extract_features(pack)
    dimensions = score_all_dimensions(features)
    composite = compute_composite(dimensions)
    band = risk_band(composite)
    decision = decide(composite, band, features)
    strengths = pick_top_strengths(dimensions)
    risks = pick_top_risks(dimensions)
    recommendations = build_recommendations(features)
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

    return HealthCard(
        enterprise=pack.identity,
        composite_score=composite,
        risk_band=band,
        dimensions=dimensions,
        top_strengths=strengths,
        top_risks=risks,
        decision=decision,
        ml_assessment=ml_assessment,
        improvement_recommendations=recommendations,
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
        )
        f = extract_features(truncated)
        dims = score_all_dimensions(f)
        comp = compute_composite(dims)
        band = risk_band(comp)
        points.append(ScoreHistoryPoint(
            period=f"{anchor[0]:04d}-{anchor[1]:02d}",
            composite_score=comp,
            risk_band=band,
        ))
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


def score_gstin(
    gstin: str,
    consent_handle: str | None = None,
    *,
    benchmark: bool = True,
) -> HealthCard:
    """Score by GSTIN.

    Pass benchmark=False when scoring the population from inside
    `benchmarks._build_benchmarks` to break the potential recursion between
    peer-percentile lookup and its own construction.
    """
    pack = build_data_pack(gstin, consent_handle)
    return score_data_pack(pack, benchmark=benchmark)
