"""In-memory loan applications + sanction letter registry.

Sits at the tail of the demo flow: onboard → consent → score → **apply →
sanction**. Applications are created from a health-card decision, auto-
sanctioned when the rulebook says APPROVE, else marked UNDER_REVIEW (REFER)
or REJECTED (DECLINE). Sanction letters are rendered from the same terms
the decision panel showed the officer.

State is process-local; lost on restart. Enough for a hackathon demo, and
mirrored on the frontend as a stateful list.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from .schemas import (
    ApplyRequest,
    EnterpriseIdentity,
    HealthCard,
    LoanApplication,
    SanctionLetter,
)


_apps_by_id: dict[str, LoanApplication] = {}
_apps_by_gstin: dict[str, list[str]] = {}
_letters_by_id: dict[str, SanctionLetter] = {}


def _emi_paise(principal: int, roi_pct: float, tenor_months: int) -> int:
    """Standard EMI formula. Integer paise."""
    if principal == 0 or tenor_months == 0:
        return 0
    r = (roi_pct / 100) / 12
    if r == 0:
        return principal // tenor_months
    n = tenor_months
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return int(round(emi))


def _make_application(
    identity: EnterpriseIdentity,
    card: HealthCard,
    amount_paise: int,
    tenor_months: int,
    channel: str = "DIRECT",
) -> LoanApplication:
    if card.decision.recommendation == "APPROVE":
        status = "SANCTIONED"
        rationale = (
            f"Straight-through approval — Band {card.risk_band} · composite "
            f"{card.composite_score} · ML PD "
            f"{card.ml_assessment.probability_of_default * 100:.1f}%."
        )
    elif card.decision.recommendation == "REFER":
        status = "UNDER_REVIEW"
        rationale = "Marginal profile — routed to underwriter queue."
    else:
        status = "REJECTED"
        rationale = "Rulebook declines — cash-flow / compliance signals insufficient."

    app = LoanApplication(
        application_id=f"APP-{uuid4().hex[:10].upper()}",
        gstin=identity.gstin,
        trade_name=identity.trade_name,
        amount_paise=amount_paise,
        tenor_months=tenor_months,
        roi_pct=card.decision.suggested_roi_pct,
        status=status,  # type: ignore[arg-type]
        created_at=datetime.utcnow(),
        channel=channel,  # type: ignore[arg-type]
        rationale=rationale,
    )
    _apps_by_id[app.application_id] = app
    _apps_by_gstin.setdefault(identity.gstin, []).append(app.application_id)
    return app


def apply_for_credit(
    identity: EnterpriseIdentity,
    card: HealthCard,
    req: ApplyRequest,
    channel: str = "DIRECT",
) -> tuple[LoanApplication, SanctionLetter | None]:
    """Create an application, and if approved a sanction letter too."""
    amount = req.amount_paise or card.decision.suggested_limit_paise
    tenor = req.tenor_months or card.decision.suggested_tenor_months
    if tenor == 0:
        tenor = 24  # sane default for the sanction letter EMI math if REFER
    app = _make_application(identity, card, amount, tenor, channel)
    letter = _issue_letter(identity, card, app) if app.status == "SANCTIONED" else None
    return app, letter


def _issue_letter(
    identity: EnterpriseIdentity,
    card: HealthCard,
    app: LoanApplication,
) -> SanctionLetter:
    now = datetime.utcnow()
    processing_fee = int(app.amount_paise * 0.005)  # 0.5%
    monthly_emi = _emi_paise(app.amount_paise, app.roi_pct, app.tenor_months)

    covenants = [
        f"Utilize the facility for working-capital / business purposes only.",
        f"Maintain a minimum DSCR of 1.5× during the tenor.",
        f"Route at least 60% of GST turnover through the sanctioning bank.",
        f"Furnish quarterly GST + bank statement extracts via consented AA pull.",
        f"Any bounce or default triggers immediate limit review.",
    ]

    letter = SanctionLetter(
        letter_id=f"SL-{now.strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}",
        application_id=app.application_id,
        enterprise=identity,
        amount_paise=app.amount_paise,
        tenor_months=app.tenor_months,
        roi_pct=app.roi_pct,
        processing_fee_paise=processing_fee,
        monthly_emi_paise=monthly_emi,
        covenants=covenants,
        issued_at=now,
        valid_until=now + timedelta(days=30),
        reference_number=f"IDBI-MSME-{app.application_id[-6:]}",
    )
    _letters_by_id[letter.letter_id] = letter
    return letter


def get_application(application_id: str) -> LoanApplication | None:
    return _apps_by_id.get(application_id)


def list_applications() -> list[LoanApplication]:
    return sorted(_apps_by_id.values(), key=lambda a: a.created_at, reverse=True)


def letter_for_application(application_id: str) -> SanctionLetter | None:
    for letter in _letters_by_id.values():
        if letter.application_id == application_id:
            return letter
    return None
