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
from ..schemas import DataPack, HealthCard
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
    features = extract_features(pack)
    dimensions = score_all_dimensions(features)
    composite = compute_composite(dimensions)
    band = risk_band(composite)
    decision = decide(composite, band, features)
    strengths = pick_top_strengths(dimensions)
    risks = pick_top_risks(dimensions)

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
        generated_at=datetime.utcnow(),
        data_freshness=freshness_dates,
    )


def score_gstin(gstin: str, consent_handle: str = "MOCK-CONSENT") -> HealthCard:
    pack = build_data_pack(gstin, consent_handle)
    return score_data_pack(pack)
