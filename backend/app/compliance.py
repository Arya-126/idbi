"""RBI Digital Lending Guidelines (2022) checklist — data for /compliance.

Each row maps a DLG requirement to what this demo actually does about it,
with an honest status: IMPLEMENTED (works in this demo), SIMULATED (the
mechanism exists but the counterparty is mocked), or PRODUCTION_PLAN
(deliberately out of hackathon scope, noted rather than built).
"""

from __future__ import annotations

from .schemas import ComplianceItem


CHECKLIST: list[ComplianceItem] = [
    ComplianceItem(
        requirement="Data collected only with borrower consent, purpose-scoped",
        status="IMPLEMENTED",
        evidence=(
            "Every pull validates a registered consent handle (403 on "
            "unknown/revoked/expired); per-source scope is enforced — an "
            "unshared rail is never fetched and its dimension greys out."
        ),
        link="/consent-log",
    ),
    ComplianceItem(
        requirement="Borrower can revoke consent at any time",
        status="IMPLEMENTED",
        evidence=(
            "Revoke button on the consent log; subsequent pulls with the "
            "revoked handle are rejected and land in the access audit trail."
        ),
        link="/consent-log",
    ),
    ComplianceItem(
        requirement="Auditability of every data access",
        status="IMPLEMENTED",
        evidence=(
            "Access audit trail records endpoint, GSTIN, consent handle and "
            "ALLOWED/DENIED outcome for every data pull this session."
        ),
        link="/consent-log",
    ),
    ComplianceItem(
        requirement="Key Fact Statement (APR, fees, cooling-off) before disbursal",
        status="IMPLEMENTED",
        evidence=(
            "Sanction letters carry a KFS block: APR including processing "
            "fee, total cost of credit, EMI schedule, cooling-off window and "
            "grievance contact."
        ),
        link=None,
    ),
    ComplianceItem(
        requirement="Algorithmic decisions must be explainable",
        status="IMPLEMENTED",
        evidence=(
            "Every dimension decomposes into coded factors (adverse-action "
            "style reason codes); the ML PD is advisory-only with "
            "counterfactual drivers, calibration and monotonic constraints."
        ),
        link=None,
    ),
    ComplianceItem(
        requirement="Consent artefact in a standard, portable format",
        status="SIMULATED",
        evidence=(
            "Downloadable JSON artefact shaped after the ReBIT consent "
            "object (purpose code, FI types, data life, fetch type); the "
            "signature is a simulated content hash, not a JWS."
        ),
        link="/consent-log",
    ),
    ComplianceItem(
        requirement="Data via regulated rails (AA/GSTN/EPFO), no scraping",
        status="SIMULATED",
        evidence=(
            "All four rails sit behind connector protocols mirroring the "
            "real integrations; the demo dispatches to a synthetic-data "
            "generator instead of live endpoints."
        ),
        link=None,
    ),
    ComplianceItem(
        requirement="LSP conduct disclosure (agent of the bank)",
        status="SIMULATED",
        evidence=(
            "KFS carries the LSP disclosure line; the ULI/OCEN simulator "
            "shows the LSP hop explicitly in every wire timeline."
        ),
        link="/ecosystem",
    ),
    ComplianceItem(
        requirement="Data storage: minimal, time-bound, in India",
        status="PRODUCTION_PLAN",
        evidence=(
            "Demo holds everything in process memory and encodes data_life "
            "on the artefact; production needs India-region persistent "
            "storage with data-life-driven purge jobs."
        ),
        link=None,
    ),
    ComplianceItem(
        requirement="Model governance: validation, monitoring, bias review",
        status="PRODUCTION_PLAN",
        evidence=(
            "Demo model is synthetic-trained and advisory-only by design "
            "(champion/challenger); production needs a model-risk framework "
            "with real-outcome backtesting before the ML PD can influence "
            "decisions."
        ),
        link=None,
    ),
]
