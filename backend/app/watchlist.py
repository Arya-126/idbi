"""Watch-list action workflow — turns EWS flags into recorded officer actions.

Mirrors the applications registry pattern: in-memory, process-local. An
action is an auditable statement that a human looked at a flagged borrower
and did something (acknowledged, asked for a fresh consented pull, scheduled
a review call).
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from . import personas
from .schemas import WatchlistAction


_actions: list[WatchlistAction] = []


def record_action(gstin: str, action: str, note: str) -> WatchlistAction:
    persona = personas.get_persona(gstin)
    entry = WatchlistAction(
        action_id=f"WL-{uuid4().hex[:8].upper()}",
        gstin=gstin,
        trade_name=persona.trade_name if persona else gstin,
        action=action,  # type: ignore[arg-type]
        note=note,
        created_at=datetime.utcnow(),
    )
    _actions.append(entry)
    return entry


def actions_for(gstin: str) -> list[WatchlistAction]:
    return sorted(
        (a for a in _actions if a.gstin == gstin),
        key=lambda a: a.created_at,
        reverse=True,
    )


def all_actions() -> list[WatchlistAction]:
    return sorted(_actions, key=lambda a: a.created_at, reverse=True)
