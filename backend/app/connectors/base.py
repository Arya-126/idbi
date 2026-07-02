"""Connector protocols — one per external data rail.

These are the contracts a real GSTN / AA / EPFO / NPCI adapter would satisfy.
The mock implementations in `.mock` share the same shape, so swapping to real
integrations is a wiring change, not a rewrite.
"""

from __future__ import annotations

from typing import Protocol

from ..schemas import AaProfile, EpfoProfile, GstProfile, UpiProfile


class ConnectorError(RuntimeError):
    """Raised when a source could not be reached or returned invalid data."""


class GstConnector(Protocol):
    def fetch(self, gstin: str) -> GstProfile: ...


class AaConnector(Protocol):
    def fetch(self, consent_handle: str, gstin: str) -> AaProfile: ...


class EpfoConnector(Protocol):
    def fetch(self, gstin: str) -> EpfoProfile: ...


class UpiConnector(Protocol):
    def fetch(self, gstin: str) -> UpiProfile: ...
