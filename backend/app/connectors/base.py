"""Connector protocols — one per external data rail.

These are the contracts a real GSTN / AA / EPFO / NPCI adapter would satisfy.
The mock implementations in `.mock` share the same shape, so swapping to real
integrations is a wiring change, not a rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..schemas import (
    AaProfile,
    EnterpriseIdentity,
    EpfoProfile,
    GstProfile,
    UpiProfile,
)


class ConnectorError(RuntimeError):
    """Raised when a source could not be reached or returned invalid data."""


class IdentityConnector(Protocol):
    """Udyam / GSTN identity lookup — who is this GSTIN?"""

    def fetch(self, gstin: str) -> EnterpriseIdentity: ...


class GstConnector(Protocol):
    def fetch(self, gstin: str) -> GstProfile: ...


class AaConnector(Protocol):
    def fetch(self, consent_handle: str, gstin: str) -> AaProfile: ...


class EpfoConnector(Protocol):
    def fetch(self, gstin: str) -> EpfoProfile: ...


class UpiConnector(Protocol):
    def fetch(self, gstin: str) -> UpiProfile: ...


@dataclass
class ConnectorSet:
    """The full rail bundle the scoring engine depends on.

    Typed against the protocols so swapping mocks for real adapters is a
    change to the factory that builds this set, not to the engine.
    """

    identity: IdentityConnector
    gst: GstConnector
    aa: AaConnector
    epfo: EpfoConnector
    upi: UpiConnector
