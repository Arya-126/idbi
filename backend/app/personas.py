"""Synthetic MSME personas + deterministic data generation.

Each persona is a set of "knobs" (turnover level, growth, filing discipline,
bounce rate, headcount trend, UPI velocity, etc.). Given a persona, we generate
24 months of GST returns, 12 months of AA bank transactions, 12 months of EPFO
records, and 12 months of UPI aggregates — all seeded by GSTIN so the score is
stable across API calls.

All identifiers (GSTIN, PAN, VPA, IFSC, establishment id) follow real formats
but are obviously fake — safe to display in demos.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date, datetime

from .schemas import (
    AaProfile,
    BankAccount,
    BankTxn,
    BankTxnCategory,
    DataPack,
    EnterpriseIdentity,
    EntityType,
    EpfoMonth,
    EpfoProfile,
    GstMonthlyReturn,
    GstProfile,
    MsmeCategory,
    MsmeSummary,
    UpiMonth,
    UpiProfile,
)

# Reference "today" for data generation. Dynamic so freshness stays current
# on any demo day; determinism comes from GSTIN-seeded RNGs (same GSTIN on the
# same day always yields identical data — months simply roll forward with the
# calendar).
TODAY = date.today()

# Convenience: ₹1 lakh in paise = 1e5 rupees × 100 paise = 1e7 paise
L_PAISE = 10_000_000  # one lakh in paise
K_PAISE = 100_000  # one thousand in paise


# ─── Persona knobs ──────────────────────────────────────────────────────────


@dataclass
class Persona:
    # Identity
    gstin: str
    pan: str
    udyam_number: str | None
    legal_name: str
    trade_name: str
    entity_type: EntityType
    sector: str
    sub_sector: str
    msme_category: MsmeCategory
    registered_state: str
    registered_city: str
    incorporation_date: date
    tagline: str  # short demo-facing headline

    # GST behaviour
    monthly_turnover_lakhs: float  # base turnover
    growth_yoy: float  # e.g. 0.18 = +18%
    seasonality_amplitude: float  # 0..0.5, added to monthly multiplier
    seasonality_peak_month: int  # 1..12
    filing_discipline: float  # 0..1 probability filed on time

    # AA (bank) behaviour
    avg_bank_balance_lakhs: float
    inflow_outflow_ratio: float  # >1 = net positive
    balance_volatility: float  # 0..1 (coeff of variation)
    bounce_incidents_12m: int
    monthly_emi_lakhs: float  # existing debt service

    # UPI behaviour
    upi_inflow_lakhs: float
    upi_unique_payers: int
    upi_p2m_share: float  # 0..1
    upi_growth_yoy: float

    # EPFO / employment
    epfo_active: bool
    employee_count: int
    monthly_wage_per_employee_lakhs: float  # ₹L/employee/mo
    salary_regularity: float  # 0..1

    # Bank account cosmetic
    bank_name: str = "IDBI Bank"
    ifsc_prefix: str = "IBKL0"
    vpa_suffix: str = "@idbi"

    # Inclusion flags
    is_ntc: bool = False  # New-to-Credit: no bureau footprint, no live loans
    is_ntb: bool = False  # New-to-Bank: banks elsewhere; data still flows via AA


def _rel_month_start(months_back: int, day: int = 4) -> date:
    """A date `months_back` months before TODAY — for age-anchored personas."""
    y, m = TODAY.year, TODAY.month - months_back
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, day)


# ─── Persona registry ───────────────────────────────────────────────────────


PERSONAS: list[Persona] = [
    Persona(
        gstin="27AAKCS1234A1Z5",
        pan="AAKCS1234A",
        udyam_number="UDYAM-MH-01-0012345",
        legal_name="Sharma Textiles Private Limited",
        trade_name="Sharma Textiles",
        entity_type=EntityType.PVT_LTD,
        sector="Manufacturing",
        sub_sector="Textiles & Apparel",
        msme_category=MsmeCategory.SMALL,
        registered_state="Maharashtra",
        registered_city="Bhiwandi",
        incorporation_date=date(2018, 4, 12),
        tagline="Established textile SME, disciplined filer, steady growth",
        monthly_turnover_lakhs=42.0,
        growth_yoy=0.18,
        seasonality_amplitude=0.12,
        seasonality_peak_month=10,
        filing_discipline=0.96,
        avg_bank_balance_lakhs=18.0,
        inflow_outflow_ratio=1.12,
        balance_volatility=0.18,
        bounce_incidents_12m=0,
        monthly_emi_lakhs=1.8,
        upi_inflow_lakhs=28.0,
        upi_unique_payers=340,
        upi_p2m_share=0.42,
        upi_growth_yoy=0.22,
        epfo_active=True,
        employee_count=34,
        monthly_wage_per_employee_lakhs=0.28,
        salary_regularity=0.98,
    ),
    Persona(
        gstin="29AAKPB4321B1Z8",
        pan="AAKPB4321B",
        udyam_number="UDYAM-KA-03-0098765",
        legal_name="Kirana Bazaar",
        trade_name="Kirana Bazaar",
        entity_type=EntityType.PROPRIETORSHIP,
        sector="Retail Trade",
        sub_sector="Grocery & FMCG",
        msme_category=MsmeCategory.MICRO,
        registered_state="Karnataka",
        registered_city="Bengaluru",
        incorporation_date=date(2022, 6, 3),
        tagline="Micro retail store, heavy UPI-consumer flow",
        monthly_turnover_lakhs=8.0,
        growth_yoy=0.12,
        seasonality_amplitude=0.08,
        seasonality_peak_month=11,
        filing_discipline=0.83,
        avg_bank_balance_lakhs=2.4,
        inflow_outflow_ratio=1.08,
        balance_volatility=0.28,
        bounce_incidents_12m=1,
        monthly_emi_lakhs=0.22,
        upi_inflow_lakhs=6.2,
        upi_unique_payers=1180,
        upi_p2m_share=0.88,
        upi_growth_yoy=0.35,
        epfo_active=False,
        employee_count=3,
        monthly_wage_per_employee_lakhs=0.18,
        salary_regularity=0.90,
    ),
    Persona(
        gstin="09AAFPK5678C1Z2",
        pan="AAFPK5678C",
        udyam_number="UDYAM-UP-14-0034567",
        legal_name="Kumar Enterprises",
        trade_name="Kumar Enterprises",
        entity_type=EntityType.PARTNERSHIP,
        sector="Wholesale Trade",
        sub_sector="Building Materials",
        msme_category=MsmeCategory.SMALL,
        registered_state="Uttar Pradesh",
        registered_city="Kanpur",
        incorporation_date=date(2019, 8, 20),
        tagline="Trading firm with irregular filings and cash-flow stress",
        monthly_turnover_lakhs=18.0,
        growth_yoy=-0.08,
        seasonality_amplitude=0.06,
        seasonality_peak_month=3,
        filing_discipline=0.52,
        avg_bank_balance_lakhs=3.0,
        inflow_outflow_ratio=0.94,
        balance_volatility=0.42,
        bounce_incidents_12m=4,
        monthly_emi_lakhs=2.1,
        upi_inflow_lakhs=5.0,
        upi_unique_payers=90,
        upi_p2m_share=0.35,
        upi_growth_yoy=-0.05,
        epfo_active=True,
        employee_count=7,
        monthly_wage_per_employee_lakhs=0.22,
        salary_regularity=0.68,
    ),
    Persona(
        gstin="07AAJCN2468D1Z0",
        pan="AAJCN2468D",
        udyam_number="UDYAM-DL-04-0045678",
        legal_name="NewGen Tech Services LLP",
        trade_name="NewGen Tech",
        entity_type=EntityType.LLP,
        sector="Services",
        sub_sector="IT Services",
        msme_category=MsmeCategory.MICRO,
        registered_state="Delhi",
        registered_city="New Delhi",
        # Anchored to TODAY so the "10-month-old" story never ages out.
        incorporation_date=_rel_month_start(10),
        tagline="10-month-old NTC startup — no bureau history, strong signals",
        monthly_turnover_lakhs=14.0,
        growth_yoy=0.45,
        seasonality_amplitude=0.04,
        seasonality_peak_month=3,
        filing_discipline=1.0,
        avg_bank_balance_lakhs=6.0,
        inflow_outflow_ratio=1.22,
        balance_volatility=0.20,
        bounce_incidents_12m=0,
        monthly_emi_lakhs=0.0,
        upi_inflow_lakhs=1.2,
        upi_unique_payers=42,
        upi_p2m_share=0.15,
        upi_growth_yoy=0.60,
        epfo_active=True,
        employee_count=12,
        monthly_wage_per_employee_lakhs=0.75,
        salary_regularity=1.0,
        # NTC and NTB: no bureau footprint, and banks elsewhere — the AA rail
        # is what lets this bank see its cash flows at all.
        bank_name="HDFC Bank",
        ifsc_prefix="HDFC0",
        vpa_suffix="@hdfcbank",
        is_ntc=True,
        is_ntb=True,
    ),
    Persona(
        gstin="24AAMPH9876E1Z7",
        pan="AAMPH9876E",
        udyam_number="UDYAM-GJ-08-0056789",
        legal_name="Meera Handicrafts",
        trade_name="Meera Handicrafts",
        entity_type=EntityType.PROPRIETORSHIP,
        sector="Manufacturing",
        sub_sector="Handicrafts & Export",
        msme_category=MsmeCategory.MICRO,
        registered_state="Gujarat",
        registered_city="Ahmedabad",
        incorporation_date=date(2021, 11, 15),
        tagline="Micro exporter, seasonal, disciplined filer",
        monthly_turnover_lakhs=5.5,
        growth_yoy=0.06,
        seasonality_amplitude=0.35,
        seasonality_peak_month=10,
        filing_discipline=0.90,
        avg_bank_balance_lakhs=1.8,
        inflow_outflow_ratio=1.06,
        balance_volatility=0.36,
        bounce_incidents_12m=0,
        monthly_emi_lakhs=0.18,
        upi_inflow_lakhs=0.8,
        upi_unique_payers=55,
        upi_p2m_share=0.30,
        upi_growth_yoy=0.10,
        epfo_active=False,
        employee_count=4,
        monthly_wage_per_employee_lakhs=0.20,
        salary_regularity=0.95,
        # NTB: existing relationship with another bank, consented via AA.
        bank_name="Bank of Baroda",
        ifsc_prefix="BARB0",
        vpa_suffix="@barodampay",
        is_ntb=True,
    ),
]


PERSONAS_BY_GSTIN: dict[str, Persona] = {p.gstin: p for p in PERSONAS}


def list_summaries() -> list[MsmeSummary]:
    return [
        MsmeSummary(
            gstin=p.gstin,
            trade_name=p.trade_name,
            sector=p.sector,
            sub_sector=p.sub_sector,
            msme_category=p.msme_category,
            registered_city=p.registered_city,
            tagline=p.tagline,
        )
        for p in PERSONAS
    ]


def get_persona(gstin: str) -> Persona | None:
    return PERSONAS_BY_GSTIN.get(gstin)


def identity_for(persona: Persona) -> EnterpriseIdentity:
    return EnterpriseIdentity(
        gstin=persona.gstin,
        udyam_number=persona.udyam_number,
        pan=persona.pan,
        legal_name=persona.legal_name,
        trade_name=persona.trade_name,
        incorporation_date=persona.incorporation_date,
        entity_type=persona.entity_type,
        sector=persona.sector,
        sub_sector=persona.sub_sector,
        msme_category=persona.msme_category,
        registered_state=persona.registered_state,
        registered_city=persona.registered_city,
    )


# ─── Generators ─────────────────────────────────────────────────────────────


def _seed(gstin: str) -> int:
    h = hashlib.sha256(gstin.encode()).digest()
    return int.from_bytes(h[:4], "big")


def _period(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _months_ago(anchor: date, n: int) -> date:
    """Return the first day of the month `n` months before `anchor`."""
    y, m = anchor.year, anchor.month - n
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def _months_between(a: date, b: date) -> int:
    """Whole months from `a` to `b`, floored at 0."""
    return max(0, (b.year - a.year) * 12 + (b.month - a.month))


def _seasonality(month: int, peak_month: int, amplitude: float) -> float:
    """Return a multiplier around 1.0 with cosine seasonality."""
    import math

    phase = (month - peak_month) / 12.0 * 2 * math.pi
    return 1.0 + amplitude * math.cos(phase)


def _yoy_multiplier(months_back: int, yoy_growth: float) -> float:
    """Apply YoY growth backwards: older months have lower turnover."""
    return (1.0 + yoy_growth) ** (-months_back / 12.0)


def _gen_gst_returns(
    persona: Persona, rng: random.Random, anchor: date = TODAY
) -> list[GstMonthlyReturn]:
    returns: list[GstMonthlyReturn] = []
    vintage = _months_between(persona.incorporation_date, anchor)
    n_months = min(24, max(1, vintage))
    for i in range(n_months):
        m_date = _months_ago(anchor, n_months - i)  # oldest → newest
        months_back = n_months - i
        mult = _seasonality(
            m_date.month, persona.seasonality_peak_month, persona.seasonality_amplitude
        ) * _yoy_multiplier(months_back, persona.growth_yoy)
        noise = rng.uniform(0.92, 1.08)
        outward = int(persona.monthly_turnover_lakhs * L_PAISE * mult * noise)
        inward = int(outward * rng.uniform(0.55, 0.72))
        net_tax = int((outward - inward) * 0.18 * rng.uniform(0.85, 1.0))
        on_time = rng.random() < persona.filing_discipline
        delay = 0 if on_time else rng.randint(3, 42)
        returns.append(
            GstMonthlyReturn(
                period=_period(m_date),
                outward_taxable_paise=outward,
                inward_taxable_paise=inward,
                net_tax_paid_paise=max(0, net_tax),
                filed_on_time=on_time,
                filing_delay_days=delay,
            )
        )
    return returns


def _gen_bank_account(
    persona: Persona, rng: random.Random, anchor: date = TODAY
) -> BankAccount:
    balance = int(persona.avg_bank_balance_lakhs * L_PAISE)
    account_id = f"ACC{rng.randint(10**9, 10**10 - 1)}"
    ifsc = f"{persona.ifsc_prefix}{rng.randint(100000, 999999):06d}"

    txns: list[BankTxn] = []
    bounce_budget = persona.bounce_incidents_12m
    n_months = min(12, max(1, _months_between(persona.incorporation_date, anchor)))

    for month_back in range(n_months, 0, -1):  # oldest first
        m_date = _months_ago(anchor, month_back)
        seasonal = _seasonality(
            m_date.month, persona.seasonality_peak_month, persona.seasonality_amplitude
        ) * _yoy_multiplier(month_back, persona.growth_yoy)
        month_revenue = persona.monthly_turnover_lakhs * L_PAISE * seasonal
        month_outflow_total = month_revenue / persona.inflow_outflow_ratio

        # Revenue inflows: 4-8 txns
        n_rev = rng.randint(4, 8)
        rev_shares = _split(1.0, n_rev, rng)
        for k, share in enumerate(rev_shares):
            day = rng.randint(1, 27)
            amt = int(month_revenue * share)
            balance += amt
            mode = rng.choices(["UPI", "NEFT", "IMPS", "RTGS"], weights=[5, 3, 2, 1])[0]
            txns.append(
                BankTxn(
                    txn_id=f"T{rng.randint(10**11, 10**12 - 1)}",
                    date=date(m_date.year, m_date.month, day),
                    amount_paise=amt,
                    mode=mode,
                    narration=f"NEFT INWARD/INV-{rng.randint(1000,9999)}/{persona.trade_name[:12].upper()}",
                    balance_paise=balance,
                    category=BankTxnCategory.REVENUE,
                )
            )

        # Purchases: 5-9 txns, ~ (total - salary - emi - tax - util - misc)
        salary_out = int(
            persona.employee_count
            * persona.monthly_wage_per_employee_lakhs
            * L_PAISE
            * rng.uniform(0.9, 1.05)
        )
        emi_out = int(persona.monthly_emi_lakhs * L_PAISE)
        tax_out = int(month_revenue * 0.03 * rng.uniform(0.7, 1.3))
        util_out = int(month_revenue * 0.015 * rng.uniform(0.5, 1.5))
        remaining_outflow = max(
            0, int(month_outflow_total) - salary_out - emi_out - tax_out - util_out
        )
        n_pur = rng.randint(5, 9)
        pur_shares = _split(1.0, n_pur, rng)
        for share in pur_shares:
            day = rng.randint(1, 28)
            amt = int(remaining_outflow * share)
            balance -= amt
            mode = rng.choices(["NEFT", "RTGS", "UPI", "ACH"], weights=[4, 2, 3, 1])[0]
            txns.append(
                BankTxn(
                    txn_id=f"T{rng.randint(10**11, 10**12 - 1)}",
                    date=date(m_date.year, m_date.month, day),
                    amount_paise=-amt,
                    mode=mode,
                    narration=f"{mode} DR SUPPLIER PMT/{rng.randint(1000,9999)}",
                    balance_paise=balance,
                    category=BankTxnCategory.PURCHASE,
                )
            )

        # Salary
        if persona.employee_count > 0:
            paid = rng.random() < persona.salary_regularity
            if paid:
                day = rng.randint(26, 28)
                balance -= salary_out
                txns.append(
                    BankTxn(
                        txn_id=f"T{rng.randint(10**11, 10**12 - 1)}",
                        date=date(m_date.year, m_date.month, min(day, 28)),
                        amount_paise=-salary_out,
                        mode="NEFT",
                        narration=f"SALARY BULK/{persona.employee_count} EMP",
                        balance_paise=balance,
                        category=BankTxnCategory.SALARY,
                    )
                )

        # EMI
        if emi_out > 0:
            day = 5
            balance -= emi_out
            txns.append(
                BankTxn(
                    txn_id=f"T{rng.randint(10**11, 10**12 - 1)}",
                    date=date(m_date.year, m_date.month, day),
                    amount_paise=-emi_out,
                    mode="ACH",
                    narration=f"ACH DR LOAN EMI/{persona.bank_name.upper()}",
                    balance_paise=balance,
                    category=BankTxnCategory.EMI,
                )
            )

        # Tax
        if tax_out > 0:
            balance -= tax_out
            txns.append(
                BankTxn(
                    txn_id=f"T{rng.randint(10**11, 10**12 - 1)}",
                    date=date(m_date.year, m_date.month, 20),
                    amount_paise=-tax_out,
                    mode="NEFT",
                    narration="GST CHALLAN PAYMENT",
                    balance_paise=balance,
                    category=BankTxnCategory.TAX,
                )
            )

        # Utility
        if util_out > 0:
            balance -= util_out
            txns.append(
                BankTxn(
                    txn_id=f"T{rng.randint(10**11, 10**12 - 1)}",
                    date=date(m_date.year, m_date.month, 12),
                    amount_paise=-util_out,
                    mode="ACH",
                    narration="ELECTRICITY BILL",
                    balance_paise=balance,
                    category=BankTxnCategory.UTILITY,
                )
            )

        # Bounce injection
        if bounce_budget > 0 and rng.random() < (bounce_budget / 12.0):
            bounce_budget -= 1
            amt = int(month_revenue * rng.uniform(0.02, 0.05))
            balance -= amt
            txns.append(
                BankTxn(
                    txn_id=f"T{rng.randint(10**11, 10**12 - 1)}",
                    date=date(m_date.year, m_date.month, rng.randint(1, 28)),
                    amount_paise=-amt,
                    mode="CHEQUE",
                    narration="CHQ RETURN CHARGES/INSUF FUNDS",
                    balance_paise=balance,
                    category=BankTxnCategory.OTHER,
                )
            )

        # Add volatility jitter to closing balance
        jitter = int(balance * persona.balance_volatility * rng.uniform(-0.15, 0.15))
        balance += jitter

    txns.sort(key=lambda t: t.date)
    account_type = "CURRENT" if persona.entity_type != EntityType.PROPRIETORSHIP else "SAVINGS"

    return BankAccount(
        account_id=account_id,
        bank_name=persona.bank_name,
        ifsc=ifsc,
        account_type=account_type,
        current_balance_paise=balance,
        as_of=anchor,
        transactions=txns,
        bounce_incidents=persona.bounce_incidents_12m,
    )


def _split(total: float, n: int, rng: random.Random) -> list[float]:
    """Split `total` into `n` positive shares that sum to it."""
    cuts = sorted(rng.uniform(0, total) for _ in range(n - 1))
    shares = []
    prev = 0.0
    for c in cuts:
        shares.append(c - prev)
        prev = c
    shares.append(total - prev)
    return shares


def _gen_epfo(
    persona: Persona, rng: random.Random, anchor: date = TODAY
) -> EpfoProfile:
    if not persona.epfo_active:
        return EpfoProfile(
            establishment_id=f"MHBAN{rng.randint(1000000, 9999999)}",
            active=False,
            monthly=[],
        )

    monthly: list[EpfoMonth] = []
    base_count = persona.employee_count
    n_months = min(12, max(1, _months_between(persona.incorporation_date, anchor)))
    for month_back in range(n_months, 0, -1):
        m_date = _months_ago(anchor, month_back)
        # Employees grow slightly over time (recent > old)
        emp = max(
            1,
            int(base_count * (1 - 0.005 * month_back) * rng.uniform(0.95, 1.02)),
        )
        wages = int(emp * persona.monthly_wage_per_employee_lakhs * L_PAISE * rng.uniform(0.97, 1.03))
        emp_share = int(wages * 0.12)
        emr_share = int(wages * 0.13)
        on_time = rng.random() < persona.salary_regularity
        monthly.append(
            EpfoMonth(
                period=_period(m_date),
                total_employees=emp,
                total_wages_paise=wages,
                employer_share_paise=emr_share,
                employee_share_paise=emp_share,
                filed_on_time=on_time,
            )
        )
    return EpfoProfile(
        establishment_id=f"MHBAN{rng.randint(1000000, 9999999)}",
        active=True,
        monthly=monthly,
    )


def _gen_upi(
    persona: Persona, rng: random.Random, anchor: date = TODAY
) -> UpiProfile:
    monthly: list[UpiMonth] = []
    n_months = min(12, max(1, _months_between(persona.incorporation_date, anchor)))
    for month_back in range(n_months, 0, -1):
        m_date = _months_ago(anchor, month_back)
        seasonal = _seasonality(
            m_date.month, persona.seasonality_peak_month, persona.seasonality_amplitude
        ) * _yoy_multiplier(month_back, persona.upi_growth_yoy)
        inflow = int(persona.upi_inflow_lakhs * L_PAISE * seasonal * rng.uniform(0.9, 1.1))
        outflow = int(inflow * rng.uniform(0.3, 0.55))
        inbound_count = int(persona.upi_unique_payers * rng.uniform(1.2, 3.0))
        outbound_count = int(inbound_count * rng.uniform(0.15, 0.4))
        payers = int(persona.upi_unique_payers * rng.uniform(0.9, 1.05))
        monthly.append(
            UpiMonth(
                period=_period(m_date),
                inflow_paise=inflow,
                outflow_paise=outflow,
                inbound_count=inbound_count,
                outbound_count=outbound_count,
                unique_payers=payers,
                p2m_share=max(0.0, min(1.0, persona.upi_p2m_share + rng.uniform(-0.05, 0.05))),
            )
        )
    vpa = f"{persona.trade_name.lower().replace(' ', '')[:14]}{persona.vpa_suffix}"
    return UpiProfile(vpa=vpa, monthly=monthly)


def build_data_pack(gstin: str, as_of: date | None = None) -> DataPack | None:
    """Generate the full synthetic pack, anchored at `as_of` (default today).

    A non-default `as_of` simulates a *fresh consented pull on a later date*:
    the anchor month shifts and the seed mixes in the anchor, so the data
    plausibly evolves (same persona behaviour knobs, new realization). Used
    by the "simulate next month" demo control — real rails obviously don't
    take an as_of.
    """
    persona = get_persona(gstin)
    if not persona:
        return None
    anchor = as_of or TODAY
    seed_key = gstin if anchor == TODAY else f"{gstin}|{anchor.isoformat()[:7]}"
    rng = random.Random(_seed(seed_key))
    identity = identity_for(persona)
    gst = GstProfile(
        gstin=persona.gstin,
        registration_date=persona.incorporation_date,
        filing_status="ACTIVE",
        returns=_gen_gst_returns(persona, rng, anchor),
    )
    account = _gen_bank_account(persona, rng, anchor)
    aa = AaProfile(
        consent_handle=f"CH-{rng.randint(10**11, 10**12 - 1)}",
        linked_accounts=[account],
    )
    epfo = _gen_epfo(persona, rng, anchor)
    upi = _gen_upi(persona, rng, anchor)

    return DataPack(
        identity=identity,
        gst=gst,
        aa=aa,
        epfo=epfo,
        upi=upi,
        fetched_at=datetime.combine(anchor, datetime.min.time()),
    )
