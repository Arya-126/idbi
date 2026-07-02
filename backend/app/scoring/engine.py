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

from ..connectors import build_default_connectors
from ..connectors.mock import ConnectorSet
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


def build_data_pack(gstin: str, consent_handle: str = "MOCK-CONSENT") -> DataPack:
    """Pull every source through its connector and assemble a DataPack.

    In production this is where consent handles get validated, per-source
    fetches get parallelized, and retries/circuit-breakers live.
    """
    from ..personas import build_data_pack as persona_pack  # deferred: mock owns identity

    identity_pack = persona_pack(gstin)
    if identity_pack is None:
        raise KeyError(f"Unknown GSTIN: {gstin}")

    conn = _default_connectors()
    return DataPack(
        identity=identity_pack.identity,
        gst=conn.gst.fetch(gstin),
        aa=conn.aa.fetch(consent_handle, gstin),
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

    ml = get_model().predict(features)
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
        trained_on_n_samples=500,
        summary=_ml_summary(ml.probability_of_default, decision.recommendation),
    )

    freshness = {
        "GST": pack.gst.returns[-1].period + "-01" if pack.gst.returns else "n/a",
        "AA": pack.aa.linked_accounts[0].as_of.isoformat()
        if pack.aa.linked_accounts else "n/a",
        "EPFO": pack.epfo.monthly[-1].period + "-01" if pack.epfo.monthly else "n/a",
        "UPI": pack.upi.monthly[-1].period + "-01" if pack.upi.monthly else "n/a",
    }
    from datetime import date as _date

    def _to_date(s: str) -> _date:
        if s == "n/a":
            return _date.today()
        return _date.fromisoformat(s)

    freshness_dates = {k: _to_date(v) for k, v in freshness.items()}

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


def _ml_summary(pd: float, recommendation: str) -> str:
    """One-liner comparing ML to rulebook so the officer sees agreement/discord."""
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
    return f"{prefix} — predicts {risk_label} default risk ({pd * 100:.1f}%)."


def score_gstin(gstin: str, consent_handle: str = "MOCK-CONSENT") -> HealthCard:
    pack = build_data_pack(gstin, consent_handle)
    return score_data_pack(pack)
