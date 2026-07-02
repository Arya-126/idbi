"""Feature engineering — pure functions over the normalized DataPack.

Every scoring dimension pulls from features here. Keeping this layer separate
means you can inspect the numeric intermediate for any factor without wading
through the scoring rules, and swap the persona-backed connectors for real
ones without touching downstream logic.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from ..schemas import DataPack


L_PAISE = 10_000_000  # ₹1 lakh in paise


@dataclass
class Features:
    # Revenue (from GST)
    months_of_gst_history: int
    avg_monthly_turnover_paise: int
    latest_3m_turnover_paise: int
    oldest_3m_turnover_paise: int
    turnover_growth_pct: float | None  # None if history too short
    turnover_cov: float  # coefficient of variation

    # Compliance
    gst_filing_on_time_pct: float
    gst_avg_delay_days: float
    epfo_filing_on_time_pct: float | None

    # Cash-flow (from AA)
    monthly_inflow_paise: int
    monthly_outflow_paise: int
    inflow_outflow_ratio: float
    avg_daily_balance_paise: int
    min_balance_paise: int
    bounce_count: int
    monthly_emi_paise: int

    # DSCR proxy: (monthly cash surplus + EMI) / EMI
    dscr_proxy: float | None  # None if no EMI (unlevered)
    monthly_surplus_paise: int

    # Digital vitality (from UPI)
    upi_monthly_inflow_paise: int
    upi_unique_payers: int
    upi_p2m_share: float
    upi_growth_pct: float | None

    # Employment (from EPFO)
    epfo_active: bool
    latest_headcount: int
    headcount_trend_pct: float | None  # None if too short or inactive
    monthly_wage_bill_paise: int


def _pct(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return (a - b) / b


def _cov(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0:
        return 0.0
    return statistics.pstdev(values) / mean


def extract_features(pack: DataPack) -> Features:
    # ─── GST-derived ─────────────────────────────────────────────────────
    returns = pack.gst.returns
    turnovers = [r.outward_taxable_paise for r in returns]
    n_gst = len(turnovers)
    avg_turnover = int(statistics.fmean(turnovers)) if turnovers else 0
    latest_3 = int(statistics.fmean(turnovers[-3:])) if n_gst >= 3 else avg_turnover
    oldest_3 = int(statistics.fmean(turnovers[:3])) if n_gst >= 3 else avg_turnover

    # Growth: prefer YoY (latest 3 vs same 3 a year ago) if history >= 15 months,
    # else use latest-vs-oldest window.
    if n_gst >= 15:
        yoy_recent = statistics.fmean(turnovers[-3:])
        yoy_old = statistics.fmean(turnovers[-15:-12])
        growth_pct = _pct(yoy_recent, yoy_old)
    elif n_gst >= 6:
        growth_pct = _pct(float(latest_3), float(oldest_3))
    else:
        growth_pct = None

    turnover_cov = _cov([float(t) for t in turnovers])
    total_returns = max(1, len(returns))
    filed_on_time = sum(1 for r in returns if r.filed_on_time)
    gst_on_time_pct = filed_on_time / total_returns
    gst_avg_delay = statistics.fmean(
        [r.filing_delay_days for r in returns if not r.filed_on_time]
    ) if any(not r.filed_on_time for r in returns) else 0.0

    # ─── EPFO ────────────────────────────────────────────────────────────
    epfo_active = pack.epfo.active
    epfo_on_time_pct: float | None = None
    latest_headcount = 0
    headcount_trend_pct: float | None = None
    monthly_wage_bill = 0
    if epfo_active and pack.epfo.monthly:
        monthly = pack.epfo.monthly
        epfo_on_time_pct = sum(1 for m in monthly if m.filed_on_time) / len(monthly)
        latest_headcount = monthly[-1].total_employees
        monthly_wage_bill = int(statistics.fmean([m.total_wages_paise for m in monthly]))
        if len(monthly) >= 6:
            recent = statistics.fmean([m.total_employees for m in monthly[-3:]])
            earlier = statistics.fmean([m.total_employees for m in monthly[:3]])
            headcount_trend_pct = _pct(recent, earlier)

    # ─── AA (bank) ────────────────────────────────────────────────────────
    account = pack.aa.linked_accounts[0] if pack.aa.linked_accounts else None
    inflow = outflow = 0
    daily_balance_avg = 0
    min_balance = 0
    bounce_count = 0
    monthly_emi = 0

    if account:
        txns = account.transactions
        credits = [t.amount_paise for t in txns if t.amount_paise > 0]
        debits = [-t.amount_paise for t in txns if t.amount_paise < 0]
        n_months = max(
            1, len({(t.date.year, t.date.month) for t in txns})
        )
        inflow = sum(credits) // n_months
        outflow = sum(debits) // n_months
        balances = [t.balance_paise for t in txns]
        daily_balance_avg = int(statistics.fmean(balances)) if balances else 0
        min_balance = min(balances) if balances else 0
        bounce_count = account.bounce_incidents
        emi_debits = [-t.amount_paise for t in txns if t.category.value == "EMI"]
        monthly_emi = sum(emi_debits) // n_months if emi_debits else 0

    ratio = (inflow / outflow) if outflow else 0.0
    surplus = inflow - outflow  # per month
    if monthly_emi > 0:
        # DSCR = (surplus + EMI) / EMI = (EBITDA proxy) / debt service
        dscr = (surplus + monthly_emi) / monthly_emi
    else:
        dscr = None

    # ─── UPI ──────────────────────────────────────────────────────────────
    upi_monthly = pack.upi.monthly
    upi_inflow = 0
    upi_payers = 0
    upi_p2m = 0.0
    upi_growth: float | None = None
    if upi_monthly:
        upi_inflow = int(statistics.fmean([m.inflow_paise for m in upi_monthly]))
        upi_payers = int(statistics.fmean([m.unique_payers for m in upi_monthly]))
        upi_p2m = statistics.fmean([m.p2m_share for m in upi_monthly])
        if len(upi_monthly) >= 6:
            recent = statistics.fmean([m.inflow_paise for m in upi_monthly[-3:]])
            earlier = statistics.fmean([m.inflow_paise for m in upi_monthly[:3]])
            upi_growth = _pct(recent, earlier)

    return Features(
        months_of_gst_history=n_gst,
        avg_monthly_turnover_paise=avg_turnover,
        latest_3m_turnover_paise=latest_3,
        oldest_3m_turnover_paise=oldest_3,
        turnover_growth_pct=growth_pct,
        turnover_cov=turnover_cov,
        gst_filing_on_time_pct=gst_on_time_pct,
        gst_avg_delay_days=gst_avg_delay,
        epfo_filing_on_time_pct=epfo_on_time_pct,
        monthly_inflow_paise=inflow,
        monthly_outflow_paise=outflow,
        inflow_outflow_ratio=ratio,
        avg_daily_balance_paise=daily_balance_avg,
        min_balance_paise=min_balance,
        bounce_count=bounce_count,
        monthly_emi_paise=monthly_emi,
        dscr_proxy=dscr,
        monthly_surplus_paise=surplus,
        upi_monthly_inflow_paise=upi_inflow,
        upi_unique_payers=upi_payers,
        upi_p2m_share=upi_p2m,
        upi_growth_pct=upi_growth,
        epfo_active=epfo_active,
        latest_headcount=latest_headcount,
        headcount_trend_pct=headcount_trend_pct,
        monthly_wage_bill_paise=monthly_wage_bill,
    )


# ─── Human-readable formatters ────────────────────────────────────────────


def fmt_paise_short(p: int) -> str:
    """₹1,23,45,678 → '₹1.23 Cr', ₹4,20,000 → '₹4.2 L', ₹35,000 → '₹35K'."""
    rupees = p / 100
    if rupees >= 10_000_000:
        return f"₹{rupees / 10_000_000:.2f} Cr"
    if rupees >= 100_000:
        return f"₹{rupees / 100_000:.1f} L"
    if rupees >= 1000:
        return f"₹{rupees / 1000:.1f}K"
    return f"₹{rupees:.0f}"


def fmt_pct(x: float | None, digits: int = 1) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:+.{digits}f}%"
