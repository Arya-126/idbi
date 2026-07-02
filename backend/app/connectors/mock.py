"""Mock connectors backed by the persona registry.

Each mock returns exactly the shape a real connector would, so downstream
feature engineering and scoring never see the difference. The persona layer
owns synthetic-data generation; connectors are thin dispatchers.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import personas
from ..consent import ConsentError, require_active
from ..schemas import (
    AaProfile,
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


def build_default_connectors() -> ConnectorSet:
    return ConnectorSet(
        identity=MockIdentityConnector(),
        gst=MockGstConnector(),
        aa=MockAaConnector(),
        epfo=MockEpfoConnector(),
        upi=MockUpiConnector(),
    )
