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
    HealthCard,
    MlAssessment,
    MlDriver as MlDriverSchema,
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


def score_data_pack(pack: DataPack) -> HealthCard:
    from ..ml import get_model  # deferred: heavy import (numpy/sklearn)

    features = extract_features(pack)
    dimensions = score_all_dimensions(features)
    composite = compute_composite(dimensions)
    band = risk_band(composite)
    decision = decide(composite, band, features)
    strengths = pick_top_strengths(dimensions)
    risks = pick_top_risks(dimensions)

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
        generated_at=datetime.utcnow(),
        data_freshness=freshness_dates,
    )


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


def score_gstin(gstin: str, consent_handle: str | None = None) -> HealthCard:
    pack = build_data_pack(gstin, consent_handle)
    return score_data_pack(pack)
