"""ULI / OCEN simulated round-trips.

Real ULI (RBI's Unified Lending Interface) and OCEN (Open Credit Enablement
Network) integrations require sandbox onboarding and long-lived MoUs — out of
scope for a hackathon. Instead we simulate the wire protocol: an LSP (Loan
Service Provider) calls our endpoint, we walk the same hops a real request
would (LSP → OCEN/ULI → Bank → AA → FIP → back), and return a timeline the UI
can render alongside the actual health card / decision the request produced.

The synthetic latencies are meant to feel realistic: AA consent + FIP fetches
dominate; bank scoring is fast. Real numbers vary by rail.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from .schemas import (
    HealthCard,
    OcenLoanRequest,
    OcenLoanResponse,
    UliEvent,
    UliPullRequest,
    UliPullResponse,
)


def _trace_id() -> str:
    return f"TR-{uuid4().hex[:12].upper()}"


def simulate_uli_pull(req: UliPullRequest, card: HealthCard | None) -> UliPullResponse:
    trace_id = _trace_id()
    events: list[UliEvent] = [
        UliEvent(step=1, actor="LSP", action="POST /uli/pull",
                 detail=f"LSP {req.lsp_id} requests health card for GSTIN {req.gstin} · product={req.product}",
                 latency_ms=8, ok=True),
        UliEvent(step=2, actor="ULI", action="Consent artefact lookup",
                 detail="Verify AA consent handle on file for this GSTIN",
                 latency_ms=42, ok=True),
        UliEvent(step=3, actor="ULI", action="Route to source rails",
                 detail="Fan-out: GSTN · EPFO · NPCI · AA (deposit + credit lines)",
                 latency_ms=15, ok=True),
        UliEvent(step=4, actor="FIP", action="GSTN — GSTR-1 / GSTR-3B pull",
                 detail="24 months of returns",
                 latency_ms=180, ok=True),
        UliEvent(step=5, actor="AA", action="Bank statement pull via FIP",
                 detail="12 months of AA-normalized deposit txns",
                 latency_ms=320, ok=True),
        UliEvent(step=6, actor="FIP", action="EPFO establishment fetch",
                 detail="Employer contributions + headcount trend",
                 latency_ms=90, ok=True),
        UliEvent(step=7, actor="BANK", action="Compute health card",
                 detail="Feature engineering · 6 dims · composite + PD",
                 latency_ms=45,
                 ok=card is not None),
        UliEvent(step=8, actor="LSP", action="200 OK — health card returned",
                 detail=(f"Band {card.risk_band} · composite {card.composite_score} · "
                         f"PD {card.ml_assessment.probability_of_default * 100:.1f}%")
                        if card else "No card produced",
                 latency_ms=6,
                 ok=card is not None),
    ]
    return UliPullResponse(
        trace_id=trace_id,
        events=events,
        health_card=card,
        total_latency_ms=sum(e.latency_ms for e in events),
    )


def simulate_ocen_loan(
    req: OcenLoanRequest,
    card: HealthCard,
    application_id: str,
) -> OcenLoanResponse:
    """OCEN-style loan draft against an existing health card."""
    trace_id = _trace_id()

    # Map rulebook recommendation → OCEN decision code.
    if card.decision.recommendation == "APPROVE":
        decision = "SANCTIONED"
        sanctioned = min(req.amount_paise, card.decision.suggested_limit_paise)
        roi = card.decision.suggested_roi_pct
        tenor = min(req.tenor_months, card.decision.suggested_tenor_months)
    elif card.decision.recommendation == "REFER":
        decision = "REFERRED"
        sanctioned = 0
        roi = card.decision.suggested_roi_pct
        tenor = req.tenor_months
    else:
        decision = "REJECTED"
        sanctioned = 0
        roi = 0.0
        tenor = 0

    events: list[UliEvent] = [
        UliEvent(step=1, actor="LSP", action="POST /ocen/loan-request",
                 detail=f"Request ₹{req.amount_paise / 1_00_00_000:.1f}L / {req.tenor_months}mo",
                 latency_ms=8, ok=True),
        UliEvent(step=2, actor="OCEN", action="Validate LSP + rate contract",
                 detail=f"LSP {req.lsp_id} authorized for term-loan disbursal",
                 latency_ms=22, ok=True),
        UliEvent(step=3, actor="BANK", action="Underwrite against health card",
                 detail=f"Band {card.risk_band} · limit {_fmt(card.decision.suggested_limit_paise)}",
                 latency_ms=40, ok=True),
        UliEvent(step=4, actor="BANK", action=f"Emit {decision}",
                 detail=(f"Sanction ₹{sanctioned / 1_00_000:.1f}L @ {roi}% for {tenor} months"
                         if decision == "SANCTIONED"
                         else "Referred to human underwriter"
                              if decision == "REFERRED"
                              else "Rejected"),
                 latency_ms=6,
                 ok=decision != "REJECTED"),
        UliEvent(step=5, actor="LSP", action="Deliver terms to borrower",
                 detail="Terms visible in LSP app; borrower e-signs to disburse",
                 latency_ms=12, ok=True),
    ]

    return OcenLoanResponse(
        trace_id=trace_id,
        events=events,
        decision=decision,  # type: ignore[arg-type]
        sanctioned_amount_paise=sanctioned,
        tenor_months=tenor,
        roi_pct=roi,
        application_id=application_id if decision != "REJECTED" else None,
    )


def _fmt(p: int) -> str:
    if abs(p) >= 1_00_00_000_00:  # crore in paise
        return f"₹{p / 1_00_00_000_00:.2f} Cr"
    if abs(p) >= 1_00_000_00:
        return f"₹{p / 1_00_000_00:.1f} L"
    return f"₹{p / 100:.0f}"
