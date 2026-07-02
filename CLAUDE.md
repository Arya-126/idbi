# CLAUDE.md

This file provides guidance to Claude Code when working on this repository.

## Project Overview

**MSME Financial Health Card** — an AI/ML-driven credit assessment platform built for a bank hackathon (Track 03: Financial Inclusion / Digital Lending / Credit Decisioning).

### The Problem

Banks evaluate MSME (Micro, Small & Medium Enterprise) credit using traditional financial documents (audited statements, ITRs, bank statements) that New-to-Credit (NTC) and New-to-Bank (NTB) enterprises often lack or maintain poorly. Rich alternate data exists — GST filings, UPI transaction flows, Account Aggregator data, EPFO records — but there is no unified framework to assess it. The result: high rejection rates, missed viable borrowers, poor portfolio diversification, and slow financial-inclusion progress.

### What We're Building

A platform that:

1. **Aggregates alternate data** — GST returns, UPI transaction patterns, Account Aggregator (AA) bank data, EPFO payroll records, utility payments, etc.
2. **Computes a multidimensional financial health score** — not a single opaque number, but scored dimensions (e.g., revenue consistency, cash-flow health, compliance discipline, payroll stability, growth trajectory, sector risk).
3. **Visualizes strengths and risks** — a "Financial Health Card" UI that a credit officer (and the MSME itself) can read at a glance, with explainability for every score component.
4. **Integrates with ULI / OCEN / AA ecosystems** — designed around India's digital public infrastructure rails for lending.
5. **Enables near-real-time credit assessment** — score on demand from live/recent data pulls, not stale documents.
6. **Expands onboarding of credit-invisible MSMEs while improving portfolio quality** — the score must be usable for approve/refer/decline decisioning and portfolio monitoring.

## Domain Glossary

Claude should know these terms; they appear throughout the project:

| Term | Meaning |
|------|---------|
| MSME | Micro, Small & Medium Enterprises (India); classified by investment + turnover under the MSMED Act / Udyam registration |
| NTC / NTB | New-to-Credit (no credit bureau history) / New-to-Bank (no relationship with this bank) |
| GST / GSTN | Goods & Services Tax network — monthly/quarterly filings (GSTR-1 sales, GSTR-3B summary) are a proxy for revenue and compliance |
| UPI | Unified Payments Interface — real-time payments; merchant UPI inflows proxy daily business turnover |
| AA | Account Aggregator framework (RBI, ReBIT FI schemas) — consent-based sharing of bank statements and financial data via FIP → AA → FIU flow |
| EPFO | Employees' Provident Fund Organisation — payroll contribution records proxy employee count and salary regularity |
| ULI | Unified Lending Interface (RBI) — plug-and-play API rail for lenders to pull consented borrower data |
| OCEN | Open Credit Enablement Network — standard APIs connecting loan service providers (LSPs) with lenders for cash-flow-based lending |
| Udyam | Government MSME registration; number encodes enterprise category |
| ITR | Income Tax Return |
| CIBIL/Bureau | Traditional credit bureau score — often absent for NTC, which is the whole point of this project |

## Guiding Principles

- **Explainability is non-negotiable.** Every score must decompose into named factors with human-readable reasons. Prefer interpretable models (gradient boosting + SHAP, scorecards) over black boxes. RBI/regulatory expectations for lending models demand this.
- **Consent-first data flows.** All data pulls are modeled as consent-driven (AA consent artefacts, GST OTP consent). Never design a flow that assumes scraping or unconsented access.
- **Mock the rails, keep the contracts real.** For the hackathon we simulate GST/AA/EPFO/UPI responses, but mock APIs must follow the real schemas (ReBIT FI data schema for AA, GSTN API shapes) so integration is a swap, not a rewrite.
- **Score dimensions over a single number.** The headline score is derived from dimension scores; the card visualizes the dimensions.
- **Demo-ready over production-ready.** This is a hackathon: prioritize a compelling end-to-end demo (onboard → consent → data pull → score → health card → lending decision) with realistic synthetic data. Note production concerns in comments/docs rather than building them.

## Proposed Architecture

```
┌─────────────┐   ┌──────────────────┐   ┌───────────────┐
│  Frontend    │──▶│  Backend API      │──▶│  Scoring Engine │
│  (React)     │   │  (FastAPI)        │   │  (ML pipeline)  │
└─────────────┘   └──────────────────┘   └───────────────┘
                          │
                ┌─────────┴──────────┐
                │  Data Connectors    │  ← mock adapters, real schemas
                │  GST · AA · EPFO ·  │
                │  UPI · Bureau       │
                └────────────────────┘
```

- `backend/app/schemas.py` — all Pydantic models: enterprise identity, per-source normalized shapes (GST/AA/EPFO/UPI), and HealthCard output.
- `backend/app/personas.py` — 5 synthetic MSME "personas" (Sharma Textiles, Kirana Bazaar, Kumar Enterprises, NewGen Tech, Meera Handicrafts) and the deterministic data generator that turns persona knobs into realistic GST/AA/EPFO/UPI payloads seeded by GSTIN.
- `backend/app/connectors/` — thin adapters implementing `GstConnector` / `AaConnector` / `EpfoConnector` / `UpiConnector` protocols. Mock impls dispatch to `personas.build_data_pack`; real impls would call GSTN / AA / EPFO / NPCI.
- `backend/app/scoring/` — feature engineering (`features.py`), the six dimension scorers with factor decomposition (`dimensions.py`), composite/decision logic (`decision.py`), and the orchestrator that assembles a `HealthCard` (`engine.py`). Weights live in `dimensions.WEIGHTS` — adjust in one place.
- `backend/app/main.py` — FastAPI app: `/api/msme`, `/api/consent`, `/api/msme/{gstin}/data-pack`, `/api/msme/{gstin}/health-card`.
- `frontend/src/pages/` — three-step user flow: `Landing` (portfolio picker) → `Consent` (source-by-source consent flow) → `HealthCard` (full scored card).
- `frontend/src/components/` — `HealthHeader`, `ScoreDial` (custom SVG dial), `DimensionRadar` (Recharts), `DimensionCard`, `DecisionPanel`, `StrengthsRisks`, `DataFreshness`.
- `frontend/src/api.ts` — thin fetch client; `types.ts` mirrors backend schemas (kept in sync manually).

## Scoring Model Design (initial direction)

Dimensions (each 0–100, weighted into composite):

1. **Revenue Health** — GST turnover level, growth trend, seasonality (GSTR-1/3B)
2. **Cash-Flow Strength** — AA bank data: inflow/outflow ratio, balance volatility, bounce/return incidents
3. **Digital Transaction Vitality** — UPI velocity, customer-count diversity, ticket-size distribution
4. **Compliance Discipline** — GST filing timeliness, EPFO deposit regularity, ITR filing
5. **Employment Stability** — EPFO headcount trend, salary payment regularity
6. **Obligation & Leverage** — existing EMIs/obligations visible in bank statements; bureau data if available

Composite → risk bands (e.g., A/B/C/D) → decision recommendation (approve / refer / decline) with suggested limit derived from cash-flow surplus.

## Conventions

- Python: type hints everywhere, Pydantic models for all API and connector payloads, `ruff` for lint/format.
- Frontend: functional components, TypeScript, Tailwind for styling; charts with Recharts.
- All monetary values in INR, stored as integers (paise) or `Decimal` — never floats.
- Dates: ISO 8601 strings at API boundaries, timezone-aware `datetime` internally (IST context).
- Synthetic data must be clearly synthetic (fake GSTINs following the real format checksum-free, names like "Sharma Textiles Pvt Ltd") — never use real business identifiers.
- Each connector returns a normalized internal schema; feature engineering never touches raw source payloads directly.

## Commands

**Backend** (FastAPI, from `backend/`):
```
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend** (Vite + React, from `frontend/`):
```
npm install
npm run dev            # http://localhost:5173, proxies /api → :8000
npm run build          # production build (also runs `tsc`)
```

**API surface** (all under `http://localhost:8000`):
- `GET /health` — liveness
- `GET /api/msme` — list demo MSMEs
- `POST /api/consent` — mock consent handle
- `GET /api/msme/{gstin}/data-pack` — normalized GST + AA + EPFO + UPI
- `GET /api/msme/{gstin}/health-card` — full scored card
- Interactive docs at `/docs`

**Sanity checks:**
```
# Score every persona in one shot:
cd backend && python -c "from app.scoring.engine import score_gstin; from app.personas import PERSONAS; [print(f'{p.trade_name:22} → {score_gstin(p.gstin).composite_score}/{score_gstin(p.gstin).risk_band}') for p in PERSONAS]"
```

**Preview launcher** — `.claude/launch.json` defines `backend` (port 8000) and `frontend` (port 5173). Use `preview_start` in Claude Code to run either.

## What NOT to Do

- Don't add real credentials, real API keys for GSTN/AA sandboxes, or real personal/business data to the repo.
- Don't build auth/RBAC/audit-trail plumbing beyond what the demo needs — mention it in docs instead.
- Don't chase model accuracy at the cost of explainability or demo clarity.
- Don't invent data sources beyond the consented-rails story (no scraping, no social-media signals) — it undermines the regulatory pitch.
