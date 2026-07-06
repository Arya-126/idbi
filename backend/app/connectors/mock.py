"""Mock connectors backed by the persona registry.

Each mock returns exactly the shape a real connector would, so downstream
feature engineering and scoring never see the difference. The persona layer
owns synthetic-data generation; connectors are thin dispatchers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .. import personas
from ..consent import ConsentError, require_active
from ..schemas import (
    AaProfile,
    BureauSummary,
    EnterpriseIdentity,
    EpfoProfile,
    GstProfile,
    UpiProfile,
)
from .base import ConnectorError, ConnectorSet


def _pack_or_raise(gstin: str):
    pack = personas.build_data_pack(gstin)
    if pack is None:
        raise ConnectorError(f"No persona registered for GSTIN {gstin}")
    return pack


@dataclass
class MockIdentityConnector:
    def fetch(self, gstin: str) -> EnterpriseIdentity:
        persona = personas.get_persona(gstin)
        if persona is None:
            raise ConnectorError(f"No persona registered for GSTIN {gstin}")
        return personas.identity_for(persona)


@dataclass
class MockGstConnector:
    def fetch(self, gstin: str) -> GstProfile:
        return _pack_or_raise(gstin).gst


@dataclass
class MockAaConnector:
    def fetch(self, consent_handle: str, gstin: str) -> AaProfile:
        # Like a real FIU→AA call, the handle must be a live registered grant.
        try:
            require_active(consent_handle, gstin)
        except ConsentError as e:
            raise ConnectorError(f"AA consent rejected: {e}") from e
        return _pack_or_raise(gstin).aa


@dataclass
class MockEpfoConnector:
    def fetch(self, gstin: str) -> EpfoProfile:
        return _pack_or_raise(gstin).epfo


@dataclass
class MockUpiConnector:
    def fetch(self, gstin: str) -> UpiProfile:
        return _pack_or_raise(gstin).upi


@dataclass
class MockBureauConnector:
    """Bureau-if-available stub. NTC personas return NO-HIT (that's the whole
    point); others get a deterministic synthetic file. Display-only — no
    scorer reads this."""

    def fetch(self, pan: str, gstin: str) -> BureauSummary:
        persona = personas.get_persona(gstin)
        if persona is None:
            raise ConnectorError(f"No persona registered for GSTIN {gstin}")
        if persona.is_ntc:
            return BureauSummary(
                hit=False,
                note="No bureau file found — scored entirely on alternate data",
            )
        # Plausible synthetic score: correlated with the same behavior knobs
        # that drive the persona's real health, plus a small PAN-seeded wobble
        # so it doesn't look derived from our own composite.
        wobble = int.from_bytes(hashlib.sha256(pan.encode()).digest()[:1], "big") % 40
        score = int(
            810
            - persona.bounce_incidents_12m * 35
            - (1 - persona.filing_discipline) * 180
            - max(0.0, -persona.growth_yoy) * 120
            + wobble
        )
        score = max(350, min(850, score))
        tradelines = 1 + (1 if persona.monthly_emi_lakhs > 0 else 0) + wobble % 2
        return BureauSummary(
            hit=True,
            score=score,
            live_tradelines=tradelines,
            note="Bureau file exists — shown for context only, not scored",
        )


def build_default_connectors() -> ConnectorSet:
    return ConnectorSet(
        identity=MockIdentityConnector(),
        gst=MockGstConnector(),
        aa=MockAaConnector(),
        epfo=MockEpfoConnector(),
        upi=MockUpiConnector(),
        bureau=MockBureauConnector(),
    )
