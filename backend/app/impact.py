"""Before/after impact — what a bureau-only lender would decide vs. us.

Runs the portfolio through a "traditional" verdict function (bureau-only,
no NTC, no thin vintage, minimum-scale gates) and compares it against the
alternate-data decisions we already produce. Gives judges a defensible answer
to "how much better is this than what banks do today?".

The traditional rules are intentionally simple and conservative — they model
the lender who rejects because they can't see rather than because they've
studied the borrower. That's the exact "credit-invisible" problem statement.
"""

from __future__ import annotations

from datetime import date, datetime

from . import personas
from .personas import Persona
from .portfolio import build_portfolio
from .schemas import (
    ImpactMetric,
    ImpactRow,
    ImpactSummary,
    InclusionSlice,
    PortfolioEntry,
)


def _inclusion_slice(key: str, label: str, members: list[PortfolioEntry]) -> InclusionSlice:
    n = len(members)
    approved = [e for e in members if e.recommendation == "APPROVE"]
    return InclusionSlice(
        key=key,
        label=label,
        count=n,
        approval_rate=round(len(approved) / n, 3) if n else 0.0,
        avg_score=round(sum(e.composite_score for e in members) / n, 1) if n else 0.0,
        avg_pd=round(sum(e.probability_of_default for e in members) / n, 4) if n else 0.0,
        avg_limit_paise=(
            sum(e.suggested_limit_paise for e in approved) // len(approved)
            if approved else 0
        ),
    )


_TRADITIONAL_MIN_TURNOVER_LAKHS = 12.0    # informal below this
_TRADITIONAL_MIN_AGE_MONTHS = 24          # thin-file cutoff


def _months_between(a: date, b: date) -> int:
    return max(0, (b.year - a.year) * 12 + (b.month - a.month))


def _traditional_verdict(persona: Persona) -> tuple[str, str]:
    """Return (APPROVE | REJECT, one-line reason).

    Traditional-bank heuristic:
      · Reject NTC (no bureau footprint → no file to score)
      · Reject if vintage < 24 months (thin-file cutoff)
      · Reject if turnover < ₹12L/mo (informal, no audited financials)
      · Reject if proprietorship AND turnover < ₹20L/mo (KYC + informal)
      · Otherwise approve
    """
    if persona.is_ntc:
        return "REJECT", "No credit bureau history (NTC)"
    age = _months_between(persona.incorporation_date, date.today())
    if age < _TRADITIONAL_MIN_AGE_MONTHS:
        return "REJECT", f"Vintage only {age} months — below thin-file cutoff"
    if persona.monthly_turnover_lakhs < _TRADITIONAL_MIN_TURNOVER_LAKHS:
        return "REJECT", "Turnover below informal-enterprise cutoff"
    if (
        persona.entity_type.value == "PROPRIETORSHIP"
        and persona.monthly_turnover_lakhs < 20.0
    ):
        return "REJECT", "Proprietorship below KYC financials threshold"
    return "APPROVE", "Clears bureau + scale + vintage gates"


def _fmt_pct(a: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{a / total * 100:.0f}%"


def _fmt_paise(p: int) -> str:
    rupees = p / 100
    if abs(rupees) >= 1_00_00_000:
        return f"₹{rupees / 1_00_00_000:.2f} Cr"
    if abs(rupees) >= 1_00_000:
        return f"₹{rupees / 1_00_000:.1f} L"
    return f"₹{rupees:.0f}"


def compute_impact() -> ImpactSummary:
    portfolio = build_portfolio()
    entries: list[PortfolioEntry] = portfolio.entries

    trad_approvals = 0
    alt_approvals = 0
    additional = 0
    additional_exposure = 0
    ntc_ntb_included = 0
    rescued: list[ImpactRow] = []
    # Verdict per entry, computed once and reused below (exposure + PD metrics).
    verdicts: dict[str, tuple[str, str]] = {}
    trad_book_pds: list[float] = []
    alt_book_pds: list[float] = []

    for e in entries:
        persona = personas.get_persona(e.gstin)
        if persona is None:
            continue
        trad, reason = _traditional_verdict(persona)
        verdicts[e.gstin] = (trad, reason)
        if trad == "APPROVE":
            trad_approvals += 1
            trad_book_pds.append(e.probability_of_default)
        if e.recommendation == "APPROVE":
            alt_approvals += 1
            alt_book_pds.append(e.probability_of_default)
        # "Rescued" — traditional would reject but alternate approves / refers.
        if trad == "REJECT" and e.recommendation in ("APPROVE", "REFER"):
            additional += 1
            additional_exposure += e.suggested_limit_paise
            if e.is_ntc or e.is_ntb:
                ntc_ntb_included += 1
            rescued.append(ImpactRow(
                gstin=e.gstin,
                trade_name=e.trade_name,
                sector=e.sector,
                monthly_turnover_paise=e.monthly_turnover_paise,
                is_ntc=e.is_ntc,
                is_ntb=e.is_ntb,
                traditional_verdict="REJECT",
                traditional_reason=reason,
                alternate_verdict=e.recommendation,
                alternate_limit_paise=e.suggested_limit_paise,
                probability_of_default=e.probability_of_default,
            ))

    total = len(entries)
    # PD of each approved book, computed from the scored cards — not estimated.
    # Including previously invisible borrowers usually lifts the average PD;
    # the honest pitch is "we take a measured amount of extra risk to serve
    # N more viable firms", so the sign is reported either way.
    trad_avg_pd = sum(trad_book_pds) / len(trad_book_pds) if trad_book_pds else 0.0
    alt_avg_pd = sum(alt_book_pds) / len(alt_book_pds) if alt_book_pds else 0.0
    pd_lift_pp = (alt_avg_pd - trad_avg_pd) * 100

    metrics = [
        ImpactMetric(
            key="coverage",
            label="Approval coverage",
            traditional=_fmt_pct(trad_approvals, total),
            alternate=_fmt_pct(alt_approvals, total),
            lift=f"+{alt_approvals - trad_approvals} MSMEs served",
            positive=True,
        ),
        ImpactMetric(
            key="ntc_included",
            label="NTC/NTB firms onboarded",
            traditional="0",
            alternate=str(ntc_ntb_included),
            lift=f"+{ntc_ntb_included} previously credit-invisible",
            positive=True,
        ),
        ImpactMetric(
            key="exposure",
            label="Portfolio exposure",
            traditional=_fmt_paise(
                sum(
                    e.suggested_limit_paise for e in entries
                    if verdicts.get(e.gstin, ("REJECT", ""))[0] == "APPROVE"
                    and e.recommendation == "APPROVE"
                )
            ),
            alternate=_fmt_paise(portfolio.total_exposure_paise),
            lift=f"+{_fmt_paise(additional_exposure)} unlocked",
            positive=True,
            note=(
                "Both sides priced at this system's suggested limits — a bureau "
                "lender's own limits are unknowable for the demo book."
            ),
        ),
        ImpactMetric(
            key="pd_lift",
            label="Avg PD of approved book",
            traditional=f"{trad_avg_pd * 100:.1f}%",
            alternate=f"{alt_avg_pd * 100:.1f}%",
            lift=(
                f"{pd_lift_pp:+.1f} pp accepted for {additional} more borrowers"
                if pd_lift_pp > 0
                else f"{pd_lift_pp:+.1f} pp — broader book, no extra risk"
            ),
            positive=pd_lift_pp <= 0,
            note="Computed from ML PDs of each approved subset of the book.",
        ),
    ]

    # Inclusion dashboard: the credit-invisible cut vs the established cut,
    # on identical metrics — the single-number KPI replaced with evidence.
    invisible = [e for e in entries if e.is_ntc or e.is_ntb]
    established = [e for e in entries if not (e.is_ntc or e.is_ntb)]
    inclusion = [
        _inclusion_slice("ntc_ntb", "Credit-invisible (NTC/NTB)", invisible),
        _inclusion_slice("established", "Established borrowers", established),
    ]

    return ImpactSummary(
        total_msmes=total,
        traditional_approvals=trad_approvals,
        alternate_approvals=alt_approvals,
        additional_msmes_served=additional,
        ntc_ntb_included=ntc_ntb_included,
        additional_exposure_paise=additional_exposure,
        estimated_default_rate_lift_pp=round(pd_lift_pp, 2),
        metrics=metrics,
        inclusion=inclusion,
        rescued_rows=sorted(rescued, key=lambda r: -r.alternate_limit_paise),
        generated_at=datetime.utcnow(),
    )
