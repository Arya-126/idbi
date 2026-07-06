"""In-memory data-access audit trail.

The consent log answers "what grants exist"; this answers "what was actually
pulled, when, under which handle, and was anything denied". Together they are
the auditability story RBI's Digital Lending Guidelines expect.

Process-local like the other registries — production would append to WORM
storage.
"""

from __future__ import annotations

from datetime import datetime

from .schemas import AuditEntry


_entries: list[AuditEntry] = []
_MAX_ENTRIES = 2000  # ring buffer — a demo session never realistically hits this


def record(
    endpoint: str,
    gstin: str,
    consent_id: str | None,
    outcome: str,
    detail: str,
) -> None:
    _entries.append(AuditEntry(
        timestamp=datetime.utcnow(),
        endpoint=endpoint,
        gstin=gstin,
        consent_id=consent_id,
        outcome=outcome,  # type: ignore[arg-type]
        detail=detail,
    ))
    if len(_entries) > _MAX_ENTRIES:
        del _entries[: len(_entries) - _MAX_ENTRIES]


def log() -> list[AuditEntry]:
    return sorted(_entries, key=lambda e: e.timestamp, reverse=True)
