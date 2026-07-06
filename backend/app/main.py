"""FastAPI entry point for the MSME Financial Health Card API.

Routes:
  GET  /health                     — liveness
  GET  /api/msme                   — list demo enterprises
  POST /api/consent                — issue a consent grant (registered + enforced)
  POST /api/consent/{id}/revoke    — revoke a grant
  GET  /api/msme/{gstin}/data-pack — normalized data pulled from all sources
  GET  /api/msme/{gstin}/health-card — full scored Financial Health Card
  GET  /api/portfolio              — cached 30-MSME book
  POST /api/portfolio/refresh      — invalidate + rebuild the book

Data endpoints accept `?consent=<handle>`; a supplied handle must be valid
(unknown/revoked/expired → 403). Without one, the registry auto-issues a demo
grant — see `app.consent` for why that fallback exists.

CORS is wide-open in dev because the Vite frontend runs on a different port.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from datetime import datetime

from . import applications as apps_store
from . import audit
from . import consent as consent_store
from . import ecosystem
from . import personas
from . import stress as stress_mod
from . import watchlist as watchlist_store
from .compliance import CHECKLIST
from .consent import ConsentError
from .impact import compute_impact
from .portfolio import build_portfolio, invalidate
from .schemas import (
    ApplyRequest,
    AuditEntry,
    ComplianceItem,
    ConsentArtefact,
    ConsentGrant,
    ConsentLogEntry,
    ConsentRequest,
    DataPack,
    HealthCard,
    ImpactSummary,
    LoanApplication,
    MsmeSummary,
    OcenLoanRequest,
    OcenLoanResponse,
    PortfolioSummary,
    SanctionLetter,
    StressResult,
    StressScenario,
    UliPullRequest,
    UliPullResponse,
    WatchlistAction,
    WatchlistActionRequest,
    WhatIfRequest,
    WhatIfResponse,
)
from .scoring.engine import build_data_pack, score_data_pack, score_gstin, what_if  # noqa: F401

app = FastAPI(
    title="MSME Financial Health Card",
    version="0.1.0",
    description=(
        "AI/ML-driven credit assessment for NTC/NTB MSMEs, aggregating GST, "
        "Account Aggregator, EPFO and UPI signals over a consent-first, "
        "ULI/OCEN-ready connector layer."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _warm_caches() -> None:
    """Train the PD model and build the portfolio at boot so first requests are fast."""
    from .ml import get_model
    get_model()          # trains ~500 samples in <1s
    build_portfolio()    # scores 30 MSMEs and caches summary


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/msme", response_model=list[MsmeSummary])
def list_msmes() -> list[MsmeSummary]:
    # Only the 5 hand-authored demo personas show on the landing tiles;
    # the 25 sampled book members live in the portfolio view.
    return personas.list_summaries()


@app.get("/api/portfolio", response_model=PortfolioSummary)
def get_portfolio() -> PortfolioSummary:
    return build_portfolio()


@app.post("/api/portfolio/refresh", response_model=PortfolioSummary)
def refresh_portfolio() -> PortfolioSummary:
    """Drop the cached book and re-score all 30 MSMEs."""
    invalidate()
    return build_portfolio()


@app.post("/api/portfolio/stress", response_model=StressResult)
def stress_portfolio(scenario: StressScenario) -> StressResult:
    """Shock the whole book at feature level and report the band migration.

    Use a preset by sending {"key": "revenue_shock"} etc., or send custom
    shock values directly.
    """
    preset = stress_mod.PRESETS.get(scenario.key)
    if preset is not None and scenario == StressScenario(key=scenario.key, label=scenario.label):
        scenario = preset
    return stress_mod.run_stress(scenario)


@app.get("/api/portfolio/stress/presets", response_model=list[StressScenario])
def stress_presets() -> list[StressScenario]:
    return list(stress_mod.PRESETS.values())


@app.post("/api/portfolio/{gstin}/action", response_model=WatchlistAction)
def watchlist_action(gstin: str, req: WatchlistActionRequest) -> WatchlistAction:
    """Record an officer action against a watch-listed borrower."""
    if personas.get_persona(gstin) is None:
        raise _not_found(gstin)
    return watchlist_store.record_action(gstin, req.action, req.note)


@app.get("/api/portfolio/actions", response_model=list[WatchlistAction])
def watchlist_actions(gstin: str | None = None) -> list[WatchlistAction]:
    return (
        watchlist_store.actions_for(gstin)
        if gstin else watchlist_store.all_actions()
    )


@app.post("/api/consent", response_model=ConsentGrant)
def request_consent(req: ConsentRequest) -> ConsentGrant:
    """Issue a consent grant and register it for downstream validation.

    Real AA / GSTN consent goes PENDING → borrower approves → GRANTED; the
    demo grants immediately but keeps the artefact real: the handle is stored,
    checked (GSTIN match, status, expiry) on every data pull, and revocable.
    """
    if personas.get_persona(req.gstin) is None:
        raise HTTPException(status_code=404, detail="MSME not found")
    return consent_store.issue(req.gstin, req.sources)


@app.post("/api/consent/{consent_id}/revoke", response_model=ConsentGrant)
def revoke_consent(consent_id: str) -> ConsentGrant:
    grant = consent_store.revoke(consent_id)
    if grant is None:
        raise HTTPException(status_code=404, detail="Unknown consent handle")
    audit.record(
        "POST /api/consent/{id}/revoke", grant.gstin, consent_id,
        "ALLOWED", "grant revoked by borrower",
    )
    return grant


@app.get("/api/consent/{consent_id}/artefact", response_model=ConsentArtefact)
def consent_artefact(consent_id: str) -> JSONResponse:
    """Downloadable ReBIT-inspired consent-artefact JSON."""
    grant = consent_store.get(consent_id)
    if grant is None:
        raise HTTPException(status_code=404, detail="Unknown consent handle")
    artefact = ConsentArtefact(artefact=grant)
    return JSONResponse(
        content=artefact.model_dump(mode="json"),
        headers={
            "Content-Disposition": f'attachment; filename="consent-{consent_id}.json"',
        },
    )


def _not_found(gstin: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=(
            f"Unknown GSTIN {gstin} — this demo scores only its registered "
            "synthetic MSMEs (5 demo personas + the sampled portfolio book)."
        ),
    )


def _audited_pull(endpoint: str, gstin: str, consent: str | None, fn):
    """Run a consent-gated pull, recording ALLOWED/DENIED in the audit trail."""
    try:
        result = fn()
    except KeyError:
        raise _not_found(gstin)
    except ConsentError as e:
        audit.record(endpoint, gstin, consent, "DENIED", str(e))
        raise HTTPException(status_code=403, detail=str(e)) from e
    sources = "all consented sources"
    pack = result if isinstance(result, DataPack) else None
    if pack is not None and pack.sources_excluded:
        sources = "consented sources (excluded: " + ", ".join(pack.sources_excluded) + ")"
    audit.record(endpoint, gstin, consent, "ALLOWED", sources)
    return result


def _sim_date(sim_months: int):
    """Anchor date for a simulated future pull. Clamped 0-3 months out."""
    from datetime import date as _d

    n = max(0, min(3, sim_months))
    if n == 0:
        return None
    today = _d.today()
    y, m = today.year, today.month + n
    while m > 12:
        m -= 12
        y += 1
    return _d(y, m, 1)


@app.get("/api/msme/{gstin}/data-pack", response_model=DataPack)
def get_data_pack(gstin: str, consent: str | None = None, sim: int = 0) -> DataPack:
    return _audited_pull(
        "GET /api/msme/{gstin}/data-pack", gstin, consent,
        lambda: build_data_pack(gstin, consent, as_of=_sim_date(sim)),
    )


@app.get("/api/msme/{gstin}/health-card", response_model=HealthCard)
def get_health_card(gstin: str, consent: str | None = None, sim: int = 0) -> HealthCard:
    """`sim=N` (0-3) simulates a fresh consented pull N months from now —
    the score-history chart gains a real observed point per pull."""
    return _audited_pull(
        "GET /api/msme/{gstin}/health-card", gstin, consent,
        lambda: score_gstin(gstin, consent, as_of=_sim_date(sim)),
    )


@app.post("/api/msme/{gstin}/what-if", response_model=WhatIfResponse)
def what_if_endpoint(
    gstin: str,
    req: WhatIfRequest,
    consent: str | None = None,
) -> WhatIfResponse:
    """Sensitivity simulator — officer moves a lever, sees the score/decision
    respond. Nothing is persisted."""
    try:
        return what_if(gstin, req, consent)
    except KeyError:
        raise _not_found(gstin)
    except ConsentError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# ─── Loan applications + sanction letters ────────────────────────────────────


@app.post("/api/msme/{gstin}/apply", response_model=LoanApplication)
def apply(
    gstin: str,
    req: ApplyRequest,
    consent: str | None = None,
) -> LoanApplication:
    try:
        card = score_gstin(gstin, consent)
    except KeyError:
        raise _not_found(gstin)
    except ConsentError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    app_obj, _letter = apps_store.apply_for_credit(card.enterprise, card, req)
    return app_obj


@app.get("/api/applications", response_model=list[LoanApplication])
def list_apps() -> list[LoanApplication]:
    return apps_store.list_applications()


@app.get("/api/applications/{application_id}", response_model=LoanApplication)
def get_app(application_id: str) -> LoanApplication:
    a = apps_store.get_application(application_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Unknown application")
    return a


@app.get("/api/applications/{application_id}/sanction", response_model=SanctionLetter)
def sanction_for(application_id: str) -> SanctionLetter:
    letter = apps_store.letter_for_application(application_id)
    if letter is None:
        raise HTTPException(
            status_code=404,
            detail="No sanction letter — application not in SANCTIONED state",
        )
    return letter


# ─── Before/after impact dashboard ───────────────────────────────────────────


@app.get("/api/impact", response_model=ImpactSummary)
def impact() -> ImpactSummary:
    return compute_impact()


# ─── ULI / OCEN simulated flow ───────────────────────────────────────────────


@app.post("/api/uli/pull", response_model=UliPullResponse)
def uli_pull(req: UliPullRequest) -> UliPullResponse:
    try:
        pack = build_data_pack(req.gstin)
        card = score_data_pack(pack)
        audit.record(
            "POST /api/uli/pull", req.gstin, pack.aa.consent_handle,
            "ALLOWED", f"ULI pull by LSP {req.lsp_id}",
        )
    except KeyError:
        pack = None
        card = None
    return ecosystem.simulate_uli_pull(req, card, pack)


@app.post("/api/ocen/loan-request", response_model=OcenLoanResponse)
def ocen_loan(req: OcenLoanRequest) -> OcenLoanResponse:
    try:
        card = score_gstin(req.gstin)
    except KeyError:
        raise _not_found(req.gstin)
    app_obj, _letter = apps_store.apply_for_credit(
        card.enterprise, card,
        ApplyRequest(amount_paise=req.amount_paise, tenor_months=req.tenor_months),
        channel="OCEN",
    )
    return ecosystem.simulate_ocen_loan(req, card, app_obj.application_id)


# ─── Compliance checklist ────────────────────────────────────────────────────


@app.get("/api/compliance", response_model=list[ComplianceItem])
def compliance_checklist() -> list[ComplianceItem]:
    """RBI Digital Lending Guidelines checklist with honest statuses."""
    return CHECKLIST


# ─── Audit trails ────────────────────────────────────────────────────────────


@app.get("/api/audit/log", response_model=list[AuditEntry])
def audit_log() -> list[AuditEntry]:
    """Every data access this session — endpoint, handle, ALLOWED/DENIED."""
    return audit.log()


@app.get("/api/consent/log", response_model=list[ConsentLogEntry])
def consent_log() -> list[ConsentLogEntry]:
    now = datetime.utcnow()
    entries: list[ConsentLogEntry] = []
    for grant in consent_store._by_id.values():  # noqa: SLF001 — demo introspection
        persona = personas.get_persona(grant.gstin)
        status = grant.status
        if status == "GRANTED" and grant.expires_at < now:
            status = "EXPIRED"
        entries.append(ConsentLogEntry(
            consent_id=grant.consent_id,
            gstin=grant.gstin,
            trade_name=persona.trade_name if persona else grant.gstin,
            sources=grant.sources,
            granted_at=grant.granted_at,
            expires_at=grant.expires_at,
            status=status,  # type: ignore[arg-type]
        ))
    return sorted(entries, key=lambda e: e.granted_at, reverse=True)
