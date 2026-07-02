"""Mock connectors backed by the persona registry.

Each mock returns exactly the shape a real connector would, so downstream
feature engineering and scoring never see the difference. The persona layer
owns synthetic-data generation; connectors are thin dispatchers.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import personas
from ..schemas import AaProfile, EpfoProfile, GstProfile, UpiProfile
from .base import ConnectorError


def _pack_or_raise(gstin: str):
    pack = personas.build_data_pack(gstin)
    if pack is None:
        raise ConnectorError(f"No persona registered for GSTIN {gstin}")
    return pack


@dataclass
class MockGstConnector:
    def fetch(self, gstin: str) -> GstProfile:
        return _pack_or_raise(gstin).gst


@dataclass
class MockAaConnector:
    def fetch(self, consent_handle: str, gstin: str) -> AaProfile:
        pack = _pack_or_raise(gstin)
        # Real AA calls would validate the consent handle here. Mock allows any.
        return pack.aa


@dataclass
class MockEpfoConnector:
    def fetch(self, gstin: str) -> EpfoProfile:
        return _pack_or_raise(gstin).epfo


@dataclass
class MockUpiConnector:
    def fetch(self, gstin: str) -> UpiProfile:
        return _pack_or_raise(gstin).upi


@dataclass
class ConnectorSet:
    gst: MockGstConnector
    aa: MockAaConnector
    epfo: MockEpfoConnector
    upi: MockUpiConnector


def build_default_connectors() -> ConnectorSet:
    return ConnectorSet(
        gst=MockGstConnector(),
        aa=MockAaConnector(),
        epfo=MockEpfoConnector(),
        upi=MockUpiConnector(),
    )
