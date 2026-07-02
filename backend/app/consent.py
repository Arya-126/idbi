"""In-memory consent registry — issue, validate, revoke.

Demo stand-in for an AA consent-artefact store. Grants are held in process
memory (lost on restart), but the lifecycle is real: handles are persisted
when issued, validated (existence, GSTIN match, status, expiry) on every
data pull, and revocable via the API.

Demo fallback: when a data pull arrives without a consent handle (e.g. a
deep link into a health card, or the portfolio build at startup), we
auto-issue a grant rather than failing — modelling "consent already on file
from onboarding". Production would reject instead; the fallback is the one
deliberate departure from a strict consent-first flow.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from .schemas import ConsentGrant, ConsentSource


class ConsentError(Exception):
    """Raised when a consent handle is unknown, mismatched, revoked or expired."""


_by_id: dict[str, ConsentGrant] = {}
_latest_by_gstin: dict[str, ConsentGrant] = {}


def issue(gstin: str, sources: list[ConsentSource], ttl_days: int = 30) -> ConsentGrant:
    """Create and register an immediately-GRANTED consent handle.

    Real AA consent goes PENDING → (borrower approves) → GRANTED; the demo
    skips the approval wait but keeps the artefact and its lifecycle.
    """
    granted = datetime.utcnow()
    grant = ConsentGrant(
        consent_id=f"CH-{uuid4().hex[:12].upper()}",
        gstin=gstin,
        sources=sources or list(ConsentSource),
        granted_at=granted,
        expires_at=granted + timedelta(days=ttl_days),
        status="GRANTED",
    )
    _by_id[grant.consent_id] = grant
    _latest_by_gstin[gstin] = grant
    return grant


def get(consent_id: str) -> ConsentGrant | None:
    return _by_id.get(consent_id)


def revoke(consent_id: str) -> ConsentGrant | None:
    """Mark a grant REVOKED. Returns the updated grant, or None if unknown."""
    grant = _by_id.get(consent_id)
    if grant is None:
        return None
    updated = grant.model_copy(update={"status": "REVOKED"})
    _by_id[consent_id] = updated
    if _latest_by_gstin.get(grant.gstin) is grant:
        _latest_by_gstin[grant.gstin] = updated
    return updated


def _check_active(grant: ConsentGrant, gstin: str) -> None:
    if grant.gstin != gstin:
        raise ConsentError("Consent handle was issued for a different GSTIN")
    if grant.status == "REVOKED":
        raise ConsentError("Consent has been revoked by the borrower")
    if grant.status != "GRANTED":
        raise ConsentError("Consent is not in GRANTED state")
    if datetime.utcnow() > grant.expires_at:
        raise ConsentError("Consent handle has expired")


def require_active(consent_id: str, gstin: str) -> ConsentGrant:
    """Validate an existing handle or raise ConsentError."""
    grant = _by_id.get(consent_id)
    if grant is None:
        raise ConsentError(f"Unknown consent handle: {consent_id}")
    _check_active(grant, gstin)
    return grant


def resolve(gstin: str, consent_id: str | None = None) -> ConsentGrant:
    """Return an active grant for `gstin`.

    - If a handle is supplied it MUST be valid — unknown/revoked/expired
      handles raise ConsentError rather than silently falling back.
    - Without a handle, reuse the latest active grant for the GSTIN, or
      auto-issue one (demo fallback documented in the module docstring).
    """
    if consent_id:
        return require_active(consent_id, gstin)

    existing = _latest_by_gstin.get(gstin)
    if existing is not None:
        try:
            _check_active(existing, gstin)
            return existing
        except ConsentError:
            pass  # stale — fall through to a fresh demo grant
    return issue(gstin, list(ConsentSource))
