# CLAUDE.md

This file provides guidance to Claude Code when working on this repository.

## Project Overview

**MSME Financial Health Card** — an AI/ML-driven credit assessment platform built for a bank hackathon (Track 03: Financial Inclusion / Digital Lending / Credit Decisioning).

### The Problem

Banks evaluate MSME (Micro, Small & Medium Enterprise) credit using traditional financial documents (audited statements, ITRs, bank statements) that New-to-Credit (NTC) and New-to-Bank (NTB) enterprises often lack or maintain poorly. Rich alternate data exists — GST filings, UPI transaction flows, Account Aggregator data, EPFO records — but there is no unified framework to assess it. The result: high rejection rates, missed viable borrowers, poor portfolio diversification, and slow financial-inclusion progress.

### What We're Building

A platform that:

1. **Aggregates alternate data** — GST returns, UPI transaction patterns, Account Aggregator (AA) bank data, EPFO payroll records. (Utility payments appear as categorized transactions inside the AA bank data — they are not a separately connected or scored source. Bureau and ITR connectors are deliberately absent; the demo is bureau-free by design.)
2. **Computes a multidimensional financial health score** — not a single opaque number, but scored dimensions (e.g., revenue consistency, cash-flow health, compliance discipline, payroll stability, growth trajectory, sector risk).
3. **Visualizes strengths and risks** — a "Financial Health Card" UI that a credit officer (and the MSME itself, via the borrower-view toggle) can read at a glance, with explainability for every score component.
4. **Designed for ULI / OCEN / AA ecosystems** — an AA-style consent flow is implemented and enforced (grants registered, validated on every pull, expirable, revocable); ULI/OCEN integration is a connector-seam story (protocol contracts ready for real adapters), not a wire-level API contract in the demo. Pitch it as "AA consent-first, ULI/OCEN-ready" — never claim live ULI/OCEN integration.
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

- **Explainability is non-negotiable.** Every score must decompose into named factors with human-readable reasons. Prefer interpretable models (gradient boosting with local counterfactual attribution — the demo's explainer; SHAP is the production upgrade — plus scorecards) over black boxes. RBI/regulatory expectations for lending models demand this.
- **Consent-first data flows.** Consent is enforced, not decorative: `POST /api/consent` registers a grant in the in-memory registry (`app/consent.py`); data endpoints validate a supplied `?consent=` handle (unknown / revoked / expired → 403); grants are revocable via `POST /api/consent/{id}/revoke`. One documented demo exception: pulls without a handle auto-issue a grant ("consent on file") so deep links and the startup portfolio build work — production would reject instead. Never design a flow that assumes scraping or unconsented access.
- **Mock the rails, keep the contracts practical.** For the hackathon we simulate GST/AA/EPFO/UPI responses behind per-rail connector protocols. The normalized internal schemas are *inspired by* the real ones (the AA shape loosely follows the ReBIT FI deposit schema; GST is a normalized monthly summary, not raw GSTR-1/3B payloads). A real integration means writing a raw-payload normalization adapter behind the existing protocol — downstream code doesn't change, but it is adapter work, not a pure wiring swap. Don't claim field-level ReBIT/GSTN fidelity.
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
                │  Data Connectors    │  ← mock adapters behind protocols
                │  Identity · GST ·   │
                │  AA · EPFO · UPI    │
                └────────────────────┘
```

- `backend/app/schemas.py` — all Pydantic models: enterprise identity, per-source normalized shapes (GST/AA/EPFO/UPI), and HealthCard output.
- `backend/app/personas.py` — 5 synthetic MSME "personas" (Sharma Textiles, Kirana Bazaar, Kumar Enterprises, NewGen Tech, Meera Handicrafts) and the deterministic data generator that turns persona knobs into realistic GST/AA/EPFO/UPI payloads seeded by GSTIN. `TODAY` is dynamic (`date.today()`), so freshness stays current on any demo day; the NTC persona's incorporation date is anchored relative to `TODAY` so its "10-month-old" story never ages out. Personas carry `is_ntc` / `is_ntb` flags (NTB personas bank with other banks — their data arrives via the AA rail).
- `backend/app/consent.py` — in-memory consent registry: issue, validate (GSTIN match / status / expiry), revoke, and a documented demo fallback that auto-issues a grant when a pull arrives without a handle.
- `backend/app/connectors/` — thin adapters implementing `IdentityConnector` / `GstConnector` / `AaConnector` / `EpfoConnector` / `UpiConnector` protocols; `ConnectorSet` (in `base.py`) is typed against the protocols so the engine never imports mock classes. Mock impls dispatch to `personas.build_data_pack`; the mock AA connector rejects unknown/revoked/expired consent handles. Real impls would call GSTN / AA / EPFO / NPCI.
- `backend/app/scoring/` — feature engineering (`features.py`, including time-series trend features: filing-timeliness trend, balance trajectory, EMI trajectory), the six dimension scorers with factor decomposition (`dimensions.py`), composite/decision logic (`decision.py` — top strengths/risks ranked by contribution × dimension weight), and the orchestrator that assembles a `HealthCard` (`engine.py`). Weights live in `dimensions.WEIGHTS` — adjust in one place.
- `backend/app/main.py` — FastAPI app: consent (`/api/consent`, revoke, `/api/consent/log`), data (`/api/msme/{gstin}/data-pack` and `/health-card`), portfolio (`/api/portfolio` + refresh), impact (`/api/impact`), ULI/OCEN sim (`/api/uli/pull`, `/api/ocen/loan-request`), applications (`/api/msme/{gstin}/apply`, `/api/applications`, `/sanction`). `startup` hook trains the ML model and pre-builds the portfolio cache so first requests are fast.
- `backend/app/scoring/recommendations.py` — actionable "do X → gain ~Y pts" suggestions per dimension, surfaced in the borrower view.
- `backend/app/scoring/benchmarks.py` — per-sector percentile tables built once from the portfolio at startup; `benchmark=False` on the bootstrap pass avoids recursion.
- `backend/app/impact.py` — before/after comparator: runs each portfolio member through a "traditional bureau-only" rule (reject NTC / short vintage / sub-scale / proprietorship-under-threshold) and reports the coverage, exposure and NTC/NTB inclusion lift.
- `backend/app/ecosystem.py` — ULI and OCEN request simulators; returns a timeline of hops (LSP → ULI → Bank → AA → FIP → back) alongside the health card / sanction the request produced.
- `backend/app/applications.py` — in-memory loan-application registry + sanction-letter issuer; EMI/covenants derived from the decision terms.
- `backend/app/ml_data.py` — synthetic-population sampler + ground-truth default simulator. Same generator serves both ML training and the portfolio "book" view. NTC sampled firms carry no EMIs (no credit history by definition); ~40% of the book is NTB.
- `backend/app/ml.py` — `PdModel` (scikit-learn `HistGradientBoostingClassifier`) with a canonical 18-feature vector, an 80/20 holdout AUC computed at train time (surfaced on the card), local counterfactual explainer (drivers / supports), and version hash. Training uses a fast persona-to-features shortcut; scoring uses production features from the connectors — a known, documented train/serve skew (see the docstring in `ml.py`).
- `backend/app/portfolio.py` — assembles the 30-MSME book (5 demos + 25 sampled), scores each, and caches summary metrics (band mix, sector mix, recommendation mix, exposure, watchlist, flag-based NTC/NTB count). Cache is dropped via `POST /api/portfolio/refresh`.
- `frontend/src/pages/` — routes: `Landing` (portfolio picker) → `Consent` (source-by-source consent flow with real `/data-pack` pull) → `HealthCard` (scored card with print/PDF button + Apply CTA; officer/borrower view toggle; consent handle rides via sessionStorage), `Portfolio` (book view — NTC/NTB filter, trend column, EWS badges, re-score), `Impact` (before/after vs bureau-only lender), `Ecosystem` (ULI/OCEN wire-timeline simulator), `SanctionLetter` (printable letter after Apply), `ConsentLog` (compliance audit view of every consent artefact).
- `frontend/src/components/` — `HealthHeader`, `ScoreDial`, `DimensionRadar`, `DimensionCard` (peer-percentile chip), `DecisionPanel` (limit workings toggle + apply button slot), `StrengthsRisks`, `MlPanel`, `DataFreshness`, `RecommendationsPanel`, `ScoreHistoryChart`, `ApplyButton`, `WhatsAppToaster` (borrower notification toasts fired at consent / sanction / decline events).
- `frontend/src/i18n.tsx` — tiny EN / हिं dictionary + `LangProvider`; nav labels swap live, mechanism ready for wider borrower-facing translation.
- `frontend/src/api.ts` — thin fetch client covering every endpoint; `types.ts` mirrors backend schemas (kept in sync manually).

## Scoring Model Design (initial direction)

Dimensions (each 0–100, weighted into composite):

1. **Revenue Health** — GST turnover level, growth trend, seasonality (GSTR-1/3B)
2. **Cash-Flow Strength** — AA bank data: inflow/outflow ratio, balance volatility, bounce/return incidents
3. **Digital Transaction Vitality** — UPI velocity, customer-count diversity, ticket-size distribution
4. **Compliance Discipline** — GST filing timeliness, EPFO deposit regularity (ITR filing is a planned production signal — no ITR connector exists in the demo)
5. **Employment Stability** — EPFO headcount trend, salary payment regularity
6. **Obligation & Leverage** — existing EMIs/obligations inferred from bank-statement debits only. There is no bureau connector anywhere — deliberately, since the pitch is scoring the bureau-less; a bureau adapter ("bureau if available") is a production add-on behind the same connector pattern.

Composite → risk bands (e.g., A/B/C/D) → decision recommendation (approve / refer / decline) with suggested limit derived from cash-flow surplus.

**In parallel, an ML "second opinion":** a `HistGradientBoostingClassifier` trained at startup on ~500 synthetic MSMEs (with ground-truth default outcomes from a hidden logistic simulator over the persona knobs) predicts a 12-month probability of default from the same 18 observable features, with an 80/20 holdout AUC reported on the card. Local explanations come from counterfactual deltas — replace each feature with its population median and measure the PD change. Top-3 up = drivers; top-3 down = supports. The card carries a structured `agrees_with_rulebook` flag so an underwriter can spot divergent cases. **The ML PD is advisory only — the approve/refer/decline decision, limit and tenor come from the rule-based scorecard alone (champion/challenger framing). If a judge asks whether the model affects the decision, the honest answer is no, by design.**

**Known ML honesty caveats (state them, don't hide them):** training labels come from a hand-authored simulator over the same knobs that generate the features, so the model has no real-world validity or calibration; the model is retrained in-process at every boot and never persisted; training features are analytic approximations while scoring features come from generated series (train/serve skew, documented in `ml.py`).

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
- `POST /api/consent` — issue + register a consent grant (enforced downstream)
- `POST /api/consent/{id}/revoke` — revoke a grant
- `GET /api/msme/{gstin}/data-pack?consent=` — normalized GST + AA + EPFO + UPI (bad handle → 403)
- `GET /api/msme/{gstin}/health-card?consent=` — full scored card + ML PD (bad handle → 403)
- `GET /api/portfolio` — 30-MSME book with band/sector/recommendation mix, trend + EWS flags, watch-list (cached at startup)
- `POST /api/portfolio/refresh` — invalidate + re-score the book
- `GET /api/impact` — before/after comparison vs a bureau-only lender
- `POST /api/uli/pull` — simulated ULI health-card pull; returns event timeline + card
- `POST /api/ocen/loan-request` — simulated OCEN loan draft against an existing card
- `POST /api/msme/{gstin}/apply` — create loan application (auto-sanction if APPROVE)
- `GET /api/applications` / `/{id}` / `/{id}/sanction` — application + sanction-letter retrieval
- `GET /api/consent/log` — every consent artefact issued this session
- Interactive docs at `/docs`

**Sanity checks:**
```
# Score every persona in one shot:
cd backend && python -c "from app.scoring.engine import score_gstin; from app.personas import PERSONAS; [print(f'{p.trade_name:22} → {score_gstin(p.gstin).composite_score}/{score_gstin(p.gstin).risk_band}') for p in PERSONAS]"
```

**Preview launcher** — `.claude/launch.json` defines `backend` (port 8000) and `frontend` (port 5173). Use `preview_start` in Claude Code to run either.

## Known Demo Limitations (state them if asked — never hide them)

- **Deterministic mock data**: connectors dispatch to a GSTIN-seeded generator, so pulling the same GSTIN twice on the same day yields identical data — there is no way to demo a fresh pull changing a score. The on-demand compute path is real; the "live" data is simulated.
- **Portfolio quality is a snapshot**, not a time series: the book shows band/sector/recommendation mix, exposure and a watch-list, and can be re-scored on demand, but there is no before/after trend or watch-list action workflow.
- **NTC/NTB is modeled, not sourced**: personas carry explicit `is_ntc`/`is_ntb` flags (NTC = young + no live loans, NTB = banks elsewhere via AA) rather than a bureau-hit / customer-master lookup.
- **`types.ts` mirrors `schemas.py` manually** — no OpenAPI codegen; when backend schemas change, update the frontend types in the same commit.

## What NOT to Do

- Don't add real credentials, real API keys for GSTN/AA sandboxes, or real personal/business data to the repo.
- Don't build auth/RBAC/audit-trail plumbing beyond what the demo needs — mention it in docs instead.
- Don't chase model accuracy at the cost of explainability or demo clarity.
- Don't invent data sources beyond the consented-rails story (no scraping, no social-media signals) — it undermines the regulatory pitch.
