"""FastAPI entry point for the MSME Financial Health Card API.

Routes:
  GET  /health                     — liveness
  GET  /api/msme                   — list demo enterprises
  POST /api/consent                — start (mocked) consent flow
  GET  /api/msme/{gstin}/data-pack — normalized data pulled from all sources
  GET  /api/msme/{gstin}/health-card — full scored Financial Health Card

CORS is wide-open in dev because the Vite frontend runs on a different port.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import personas
from .schemas import (
    ConsentGrant,
    ConsentRequest,
    ConsentSource,
    DataPack,
    HealthCard,
    MsmeSummary,
)
from .scoring.engine import build_data_pack, score_data_pack, score_gstin

app = FastAPI(
    title="MSME Financial Health Card",
    version="0.1.0",
    description=(
        "AI/ML-driven credit assessment for NTC/NTB MSMEs, aggregating GST, "
        "Account Aggregator, EPFO and UPI signals via ULI/OCEN/AA rails."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/msme", response_model=list[MsmeSummary])
def list_msmes() -> list[MsmeSummary]:
    return personas.list_summaries()


@app.post("/api/consent", response_model=ConsentGrant)
def request_consent(req: ConsentRequest) -> ConsentGrant:
    """Mock consent flow.

    Real AA / GSTN consent artefacts have TTLs, revocation semantics, and
    per-source scope. For the demo we return an immediately-granted handle so
    the UI can proceed to data pull. Production would return PENDING first,
    poll for the borrower's approval, and then GRANTED.
    """
    if personas.get_persona(req.gstin) is None:
        raise HTTPException(status_code=404, detail="MSME not found")

    granted = datetime.utcnow()
    expires = granted + timedelta(days=30)
    return ConsentGrant(
        consent_id=f"CH-{uuid4().hex[:12].upper()}",
        gstin=req.gstin,
        sources=req.sources or list(ConsentSource),
        granted_at=granted,
        expires_at=expires,
        status="GRANTED",
    )


@app.get("/api/msme/{gstin}/data-pack", response_model=DataPack)
def get_data_pack(gstin: str) -> DataPack:
    try:
        return build_data_pack(gstin)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/msme/{gstin}/health-card", response_model=HealthCard)
def get_health_card(gstin: str) -> HealthCard:
    try:
        return score_gstin(gstin)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
