"""Data source connectors.

Each connector wraps a single source (GST, AA, EPFO, UPI) and returns a
normalized schema from `app.schemas`. Mock implementations back a persona
registry; real implementations (not built for the demo) would hit GSTN /
Account Aggregator / EPFO / NPCI endpoints and normalize the response.

The Protocol contract keeps mocks and future real adapters interchangeable.
"""

from .base import (
    ConnectorError,
    ConnectorSet,
    IdentityConnector,
    GstConnector,
    AaConnector,
    EpfoConnector,
    UpiConnector,
)
from .mock import (
    MockIdentityConnector,
    MockGstConnector,
    MockAaConnector,
    MockEpfoConnector,
    MockUpiConnector,
    build_default_connectors,
)

__all__ = [
    "ConnectorError",
    "ConnectorSet",
    "IdentityConnector",
    "GstConnector",
    "AaConnector",
    "EpfoConnector",
    "UpiConnector",
    "MockIdentityConnector",
    "MockGstConnector",
    "MockAaConnector",
    "MockEpfoConnector",
    "MockUpiConnector",
    "build_default_connectors",
]
