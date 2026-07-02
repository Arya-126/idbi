"""Synthetic training/portfolio data generator.

Two purposes served from one place:

1. **ML training** — sample a diverse population of MSMEs across sectors,
   sizes and financial-health profiles, assign each a ground-truth default
   probability from a logistic function of the persona knobs, sample a binary
   outcome, and hand the (feature_vector, defaulted) pairs to the model.

2. **Portfolio dashboard** — the same generator (with a different seed) also
   produces the "book" of MSMEs the credit officer sees on `/portfolio`, so
   band-mix and watch-list numbers are demo-plausible without hand-authoring
   dozens of profiles.

The two use-cases share the sampler so the ML model is trained on the same
kind of population it later sees in production.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date

from .personas import TODAY, Persona
from .schemas import EntityType, MsmeCategory


# ─── Sampling ranges ────────────────────────────────────────────────────────


SECTORS: list[tuple[str, list[str]]] = [
    ("Manufacturing", ["Textiles & Apparel", "Auto Components", "Food Processing",
                       "Handicrafts & Export", "Chemicals & Pharma"]),
    ("Retail Trade", ["Grocery & FMCG", "Apparel Retail", "Electronics Retail",
                      "Pharmacy Retail"]),
    ("Wholesale Trade", ["Building Materials", "Agri Commodities",
                         "Consumer Goods Distribution"]),
    ("Services", ["IT Services", "Logistics & Transport", "Hospitality",
                  "Business Services", "Healthcare Clinic"]),
]

STATES: list[tuple[str, list[str]]] = [
    ("Maharashtra", ["Mumbai", "Pune", "Nagpur", "Nashik", "Bhiwandi"]),
    ("Karnataka", ["Bengaluru", "Mysuru", "Mangaluru", "Hubballi"]),
    ("Uttar Pradesh", ["Lucknow", "Kanpur", "Noida", "Varanasi"]),
    ("Delhi", ["New Delhi"]),
    ("Gujarat", ["Ahmedabad", "Surat", "Vadodara", "Rajkot"]),
    ("Tamil Nadu", ["Chennai", "Coimbatore", "Madurai"]),
    ("West Bengal", ["Kolkata", "Howrah"]),
    ("Telangana", ["Hyderabad"]),
]


FIRST_NAMES = [
    "Sharma", "Kumar", "Patel", "Reddy", "Iyer", "Mehta", "Rao", "Gupta",
    "Chopra", "Bose", "Nair", "Menon", "Shetty", "Joshi", "Sinha", "Verma",
    "Kapoor", "Bhatia", "Malhotra", "Trivedi",
]
BUSINESS_TYPES = [
    "Traders", "Enterprises", "Industries", "Ventures", "Solutions",
    "Exports", "Manufacturing Co.", "Retail", "Services", "Distributors",
    "Textiles", "Foods", "Logistics", "Systems",
]


# ─── Random persona sampler ─────────────────────────────────────────────────


def _random_gstin(state_code: str, pan: str, rng: random.Random) -> str:
    """15-char GSTIN: 2-digit state + 10-char PAN + entity + Z + checksum."""
    entity = rng.choice("123456789A")
    checksum = rng.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{state_code}{pan}{entity}Z{checksum}"


def _random_pan(rng: random.Random) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    return (
        "".join(rng.choices(letters, k=3))
        + rng.choice("PCFHATB")  # 4th char = entity type indicator
        + rng.choices(letters, k=1)[0]
        + "".join(rng.choices(digits, k=4))
        + rng.choices(letters, k=1)[0]
    )


STATE_CODES = {
    "Maharashtra": "27", "Karnataka": "29", "Uttar Pradesh": "09",
    "Delhi": "07", "Gujarat": "24", "Tamil Nadu": "33",
    "West Bengal": "19", "Telangana": "36",
}


def sample_persona(rng: random.Random, idx: int) -> Persona:
    """Draw a persona from a joint distribution over knobs."""

    # Category and rough scale
    category = rng.choices(
        [MsmeCategory.MICRO, MsmeCategory.SMALL, MsmeCategory.MEDIUM],
        weights=[6, 3, 1],
    )[0]
    if category == MsmeCategory.MICRO:
        turnover = max(0.5, rng.lognormvariate(math.log(4), 0.6))  # ₹0.5-15L/mo
        employees = rng.randint(1, 9)
        wage = rng.uniform(0.12, 0.28)
    elif category == MsmeCategory.SMALL:
        turnover = max(8, rng.lognormvariate(math.log(25), 0.5))  # ₹8-80L/mo
        employees = rng.randint(8, 60)
        wage = rng.uniform(0.20, 0.45)
    else:
        turnover = max(60, rng.lognormvariate(math.log(120), 0.4))
        employees = rng.randint(50, 200)
        wage = rng.uniform(0.30, 0.65)

    # Sector
    sector, sub_sectors = rng.choice(SECTORS)
    sub_sector = rng.choice(sub_sectors)

    # State/city
    state, cities = rng.choice(STATES)
    city = rng.choice(cities)

    # Age
    age_months = rng.choice([
        rng.randint(6, 24),      # young
        rng.randint(24, 72),     # mid
        rng.randint(72, 180),    # established
    ])
    incorp = _months_before(TODAY, age_months)

    # New-to-Credit: young firms with no bureau footprint. By definition they
    # carry no live loans, so their EMI burden is forced to zero below.
    is_ntc = age_months < 18

    # Entity type
    if category == MsmeCategory.MEDIUM or (category == MsmeCategory.SMALL and rng.random() < 0.4):
        etype = rng.choices(
            [EntityType.PVT_LTD, EntityType.LLP, EntityType.PARTNERSHIP],
            weights=[5, 2, 3],
        )[0]
    else:
        etype = rng.choices(
            [EntityType.PROPRIETORSHIP, EntityType.PARTNERSHIP, EntityType.LLP],
            weights=[7, 2, 1],
        )[0]

    # Behavior knobs — draw as a health cluster so profiles feel coherent
    health_cluster = rng.choices(
        ["prime", "standard", "watch", "distress"],
        weights=[3, 5, 3, 2],
    )[0]

    if health_cluster == "prime":
        filing = rng.uniform(0.92, 1.0)
        ratio = rng.uniform(1.08, 1.30)
        volatility = rng.uniform(0.10, 0.25)
        bounces = 0 if rng.random() < 0.85 else 1
        salary_reg = rng.uniform(0.92, 1.0)
        emi_burden = rng.uniform(0.0, 0.10) * turnover / 5
        growth = rng.uniform(0.05, 0.35)
    elif health_cluster == "standard":
        filing = rng.uniform(0.78, 0.94)
        ratio = rng.uniform(1.02, 1.12)
        volatility = rng.uniform(0.18, 0.35)
        bounces = rng.choices([0, 1, 2], weights=[6, 3, 1])[0]
        salary_reg = rng.uniform(0.82, 0.95)
        emi_burden = rng.uniform(0.05, 0.20) * turnover / 5
        growth = rng.uniform(-0.02, 0.18)
    elif health_cluster == "watch":
        filing = rng.uniform(0.60, 0.82)
        ratio = rng.uniform(0.96, 1.05)
        volatility = rng.uniform(0.28, 0.50)
        bounces = rng.choices([1, 2, 3], weights=[4, 4, 2])[0]
        salary_reg = rng.uniform(0.70, 0.88)
        emi_burden = rng.uniform(0.10, 0.28) * turnover / 5
        growth = rng.uniform(-0.10, 0.08)
    else:  # distress
        filing = rng.uniform(0.35, 0.65)
        ratio = rng.uniform(0.85, 0.98)
        volatility = rng.uniform(0.35, 0.65)
        bounces = rng.choices([2, 3, 4, 5, 6], weights=[2, 3, 3, 2, 1])[0]
        salary_reg = rng.uniform(0.45, 0.72)
        emi_burden = rng.uniform(0.15, 0.40) * turnover / 5
        growth = rng.uniform(-0.25, 0.02)

    if is_ntc:
        emi_burden = 0.0  # no credit history → no EMIs visible in bank data

    # New-to-Bank: ~40% of the book banks elsewhere; their statements arrive
    # through the AA rail rather than an in-house relationship.
    is_ntb = rng.random() < 0.40
    if is_ntb:
        bank_name, ifsc_prefix, vpa_suffix = rng.choice([
            ("HDFC Bank", "HDFC0", "@hdfcbank"),
            ("State Bank of India", "SBIN0", "@sbi"),
            ("Canara Bank", "CNRB0", "@cnrb"),
            ("Bank of Baroda", "BARB0", "@barodampay"),
        ])
    else:
        bank_name, ifsc_prefix, vpa_suffix = ("IDBI Bank", "IBKL0", "@idbi")

    # EPFO coverage: driven by employee count with some slack
    if employees >= 20:
        epfo_active = rng.random() < 0.92
    elif employees >= 10:
        epfo_active = rng.random() < 0.55
    else:
        epfo_active = rng.random() < 0.15

    # UPI activity: correlates with sector + turnover
    if sector == "Retail Trade":
        upi_share = rng.uniform(0.55, 0.90)
        payers = int(turnover * rng.uniform(30, 90))
        p2m = rng.uniform(0.75, 0.95)
    elif sector == "Services":
        upi_share = rng.uniform(0.15, 0.45)
        payers = int(turnover * rng.uniform(3, 15))
        p2m = rng.uniform(0.20, 0.55)
    elif sector == "Wholesale Trade":
        upi_share = rng.uniform(0.20, 0.45)
        payers = int(turnover * rng.uniform(2, 10))
        p2m = rng.uniform(0.25, 0.55)
    else:  # Manufacturing
        upi_share = rng.uniform(0.25, 0.60)
        payers = int(turnover * rng.uniform(5, 25))
        p2m = rng.uniform(0.30, 0.65)

    # Identity strings
    name = rng.choice(FIRST_NAMES)
    biz = rng.choice(BUSINESS_TYPES)
    if etype == EntityType.PVT_LTD:
        legal = f"{name} {biz} Private Limited"
        trade = f"{name} {biz.split()[0]}"
    elif etype == EntityType.LLP:
        legal = f"{name} {biz} LLP"
        trade = f"{name} {biz.split()[0]}"
    else:
        legal = f"{name} {biz}"
        trade = legal

    pan = _random_pan(rng)
    gstin = _random_gstin(STATE_CODES[state], pan, rng)

    return Persona(
        gstin=gstin,
        pan=pan,
        udyam_number=f"UDYAM-{state[:2].upper()}-{rng.randint(1, 30):02d}-{rng.randint(1000000, 9999999)}",
        legal_name=legal,
        trade_name=trade,
        entity_type=etype,
        sector=sector,
        sub_sector=sub_sector,
        msme_category=category,
        registered_state=state,
        registered_city=city,
        incorporation_date=incorp,
        tagline=f"{health_cluster.title()} — {sub_sector.lower()}",
        monthly_turnover_lakhs=turnover,
        growth_yoy=growth,
        seasonality_amplitude=rng.uniform(0.05, 0.35),
        seasonality_peak_month=rng.randint(1, 12),
        filing_discipline=filing,
        avg_bank_balance_lakhs=turnover * rng.uniform(0.25, 0.65),
        inflow_outflow_ratio=ratio,
        balance_volatility=volatility,
        bounce_incidents_12m=bounces,
        monthly_emi_lakhs=emi_burden,
        upi_inflow_lakhs=turnover * upi_share,
        upi_unique_payers=max(5, payers),
        upi_p2m_share=p2m,
        upi_growth_yoy=growth + rng.uniform(-0.05, 0.15),
        epfo_active=epfo_active,
        employee_count=employees,
        monthly_wage_per_employee_lakhs=wage,
        salary_regularity=salary_reg,
        bank_name=bank_name,
        ifsc_prefix=ifsc_prefix,
        vpa_suffix=vpa_suffix,
        is_ntc=is_ntc,
        is_ntb=is_ntb,
    )


def _months_before(anchor: date, n: int) -> date:
    y, m = anchor.year, anchor.month - n
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


# ─── Ground-truth default simulator ─────────────────────────────────────────


def true_default_probability(persona: Persona) -> float:
    """Ground-truth PD as a logistic function of persona knobs.

    This is the model *the world* uses to decide who defaults; the ML model
    we train has to learn to approximate this from the observable features
    derived from GST/AA/EPFO/UPI data. It is not exposed to the API.
    """
    # Signals that increase PD:
    filing_lag = max(0.0, 1.0 - persona.filing_discipline) * 3.0
    bounce_load = persona.bounce_incidents_12m * 0.35
    ratio_stress = max(0.0, 1.05 - persona.inflow_outflow_ratio) * 12.0
    volatility_hit = max(0.0, persona.balance_volatility - 0.25) * 2.5
    emi_burden = min(
        1.0, persona.monthly_emi_lakhs / max(persona.monthly_turnover_lakhs, 0.1)
    )
    leverage_hit = max(0.0, emi_burden - 0.10) * 6.0
    salary_lag = max(0.0, 0.9 - persona.salary_regularity) * 2.5
    decline_hit = max(0.0, -persona.growth_yoy) * 2.5

    # Signals that decrease PD:
    scale_bonus = min(1.5, math.log10(max(persona.monthly_turnover_lakhs, 1)) * 0.6)
    growth_bonus = max(0.0, persona.growth_yoy) * 1.5
    breadth_bonus = min(1.0, math.log10(max(persona.upi_unique_payers, 1)) * 0.25)
    epfo_bonus = 0.35 if persona.epfo_active else 0.0

    logit = (
        -2.0
        + 1.4 * filing_lag
        + 1.2 * bounce_load
        + 1.3 * ratio_stress
        + 1.5 * volatility_hit
        + 1.3 * leverage_hit
        + 1.4 * salary_lag
        + 1.2 * decline_hit
        - scale_bonus
        - growth_bonus
        - breadth_bonus
        - epfo_bonus
    )
    return 1.0 / (1.0 + math.exp(-logit))


def sample_default(persona: Persona, rng: random.Random) -> bool:
    return rng.random() < true_default_probability(persona)


# ─── Bulk generators ─────────────────────────────────────────────────────────


@dataclass
class SampledMsme:
    persona: Persona
    defaulted: bool
    true_pd: float


def sample_population(n: int, seed: int) -> list[SampledMsme]:
    rng = random.Random(seed)
    out: list[SampledMsme] = []
    for i in range(n):
        p = sample_persona(rng, i)
        pd = true_default_probability(p)
        out.append(SampledMsme(persona=p, defaulted=rng.random() < pd, true_pd=pd))
    return out
