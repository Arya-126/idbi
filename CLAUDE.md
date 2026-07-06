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
- **Consent-first data flows.** Consent is enforced, not decorative: `POST /api/consent` registers a ReBIT/DEPA-shaped grant (purpose code, FI types, data life, simulated content-hash signature) in the in-memory registry (`app/consent.py`); data endpoints validate a supplied `?consent=` handle (unknown / revoked / expired → 403, surfaced in the UI as a blocked-state card with a re-consent CTA); grants are revocable live from the consent-log page. **Source scoping is enforced**: a rail the borrower unchecks is never fetched — its dimension greys out ("not shared") and the composite renormalizes over the remaining weights. Every pull (allowed or denied) lands in the access audit trail (`app/audit.py`, second tab on the consent-log page); the artefact JSON is downloadable per grant. One documented demo exception: pulls without a handle auto-issue a grant ("consent on file") so deep links and the startup portfolio build work — production would reject instead. Never design a flow that assumes scraping or unconsented access.
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
- `backend/app/consent.py` — in-memory consent registry: issue (with ReBIT-style artefact fields + simulated signature), validate (GSTIN match / status / expiry), revoke, and a documented demo fallback that auto-issues a grant when a pull arrives without a handle.
- `backend/app/audit.py` — in-memory data-access audit trail: every pull records endpoint, GSTIN, consent handle and ALLOWED/DENIED outcome; served at `GET /api/audit/log`.
- `backend/app/compliance.py` — the RBI Digital Lending Guidelines checklist data (`/compliance` page): each requirement graded IMPLEMENTED / SIMULATED / PRODUCTION_PLAN, honestly.
- `backend/app/stress.py` — portfolio stress tests: feature-level shocks (turnover −%, extra bounces, EMI +%) re-scored through the full scorecard for all 30 firms; presets + custom scenarios; returns band-migration matrix, exposure-at-risk, worst-hit list.
- `backend/app/watchlist.py` — watch-list action registry (ACKNOWLEDGE / REQUEST_REPULL / SCHEDULE_REVIEW with notes), surfaced as a drawer on the portfolio book.
- `backend/app/snapshots.py` — observed score snapshots (JSON file, gitignored): every real scoring run records (gstin, period, score, band); `_score_history` overlays observed points (solid dots) on the reconstructed approximation (hollow dots).
- `backend/app/connectors/` — thin adapters implementing `IdentityConnector` / `GstConnector` / `AaConnector` / `EpfoConnector` / `UpiConnector` / `BureauConnector` protocols; `ConnectorSet` (in `base.py`) is typed against the protocols so the engine never imports mock classes. Mock impls dispatch to `personas.build_data_pack`; the mock AA connector rejects unknown/revoked/expired consent handles. The bureau stub is the "bureau-if-available" plug-in made real: NTC personas return NO-HIT (the card shows "no bureau file · scored on alternate data"), others get a plausible synthetic file — **display-only, never scored**. Real impls would call GSTN / AA / EPFO / NPCI / bureaus.
- `backend/app/scoring/` — feature engineering (`features.py`, including time-series trend features: filing-timeliness trend, balance trajectory, EMI trajectory), the six dimension scorers with factor decomposition and stable adverse-action-style reason codes (`dimensions.REASON_CODES` — e.g. CF-02 = bounce incidents, never renumber), composite/decision logic (`decision.py` — composite renormalizes over consented dimensions; top strengths/risks ranked by contribution × dimension weight), and the orchestrator (`engine.py`: consent-scoped pack building, unconsented-dimension masking, the `what_if` sensitivity simulator, observed-history overlay, `as_of` simulated future pulls). Weights live in `dimensions.WEIGHTS` — adjust in one place.
- `backend/app/main.py` — FastAPI app: consent (`/api/consent`, revoke, `/api/consent/log`), data (`/api/msme/{gstin}/data-pack` and `/health-card`), portfolio (`/api/portfolio` + refresh), impact (`/api/impact`), ULI/OCEN sim (`/api/uli/pull`, `/api/ocen/loan-request`), applications (`/api/msme/{gstin}/apply`, `/api/applications`, `/sanction`). `startup` hook trains the ML model and pre-builds the portfolio cache so first requests are fast.
- `backend/app/scoring/recommendations.py` — actionable "do X → gain ~Y pts" suggestions, where Y is **computed** by applying the behavioural change to the borrower's own `Features` and re-running the scorecard (composite pts on the 0-1000 scale, not hand-tuned constants). Also builds `path_to_next_band`: the greedy stack of actions that reaches the next band, with an honest `achievable` flag when they fall short.
- `backend/app/scoring/benchmarks.py` — per-sector percentile tables built once from the portfolio at startup; `benchmark=False` on the bootstrap pass avoids recursion.
- `backend/app/impact.py` — before/after comparator: runs each portfolio member through a "traditional bureau-only" rule (reject NTC / short vintage / sub-scale / proprietorship-under-threshold) and reports the coverage, exposure and NTC/NTB inclusion lift. The PD-lift metric is **computed** (avg ML PD of the traditional-approved book vs the alternate-approved book — currently the traditional book is *riskier*, since bureau gates approve distressed-but-established firms) and the exposure metric carries a methodology footnote. Also builds the inclusion dashboard (`InclusionSlice`: NTC/NTB vs established on identical metrics).
- `backend/app/ecosystem.py` — ULI and OCEN request simulators; returns a timeline of hops (LSP → ULI → Bank → AA → FIP → back) alongside the health card / sanction the request produced. Every hop's detail carries real facts from the request (actual consent handle, actual record counts, skipped hops for unconsented rails); only the latencies are synthetic (jittered per run). OCEN REJECTED still returns its application_id — an auditable record.
- `backend/app/applications.py` — in-memory loan-application registry + sanction-letter issuer; EMI/covenants derived from the decision terms; each sanction carries a Key Fact Statement (APR incl. fees, total cost of credit, cooling-off, grievance + LSP disclosure) per the RBI Digital Lending Guidelines.
- `backend/app/ml_data.py` — synthetic-population sampler + ground-truth default simulator. Same generator serves both ML training and the portfolio "book" view. NTC sampled firms carry no EMIs (no credit history by definition); ~40% of the book is NTB.
- `backend/app/ml.py` — `PdModel`: scikit-learn `HistGradientBoostingClassifier` wrapped in `CalibratedClassifierCV` (Platt/sigmoid — isotonic overfits at n=500), with a canonical 18-feature vector, **monotonic constraints** on every direction-known feature (the model provably cannot learn "more bounces is safer"), 80/20 holdout AUC + Brier surfaced on the card, local counterfactual explainer (drivers / supports), and a version hash. Training runs each sampled persona through the **full production feature pipeline** (the old train/serve skew is gone); the trained artifact persists under gitignored `backend/.model_cache/` keyed by the version hash — cold boot ~7s, warm boot ~0.3s.
- `backend/app/portfolio.py` — assembles the 30-MSME book (5 demos + 25 sampled), scores each, and caches summary metrics (band mix, sector mix, recommendation mix, exposure, watchlist, flag-based NTC/NTB count, ML-divergence count, concentration guardrails — sector/single-name caps + HHI with breach flags — and vintage cohorts). Cache is dropped via `POST /api/portfolio/refresh`.
- `frontend/src/pages/` — routes: `Landing` (portfolio picker) → `Consent` (source-by-source consent flow with real `/data-pack` pull; unchecked sources are enforced server-side) → `HealthCard` (scored card with print/PDF, Apply CTA, officer/borrower toggle, what-if sliders, "pull today / +N mo" simulated-fresh-pull control, blocked-state card on 403; consent handle rides via sessionStorage), `Portfolio` (book view — filters incl. "ML disagrees", guardrails + vintage panels, stress-test panel, watch-list action drawer), `Impact` (before/after vs bureau-only lender + inclusion dashboard), `Ecosystem` (ULI/OCEN wire-timeline simulator), `SanctionLetter` (printable letter with KFS block), `ConsentLog` (two tabs: grants — with revoke + artefact download — and the data-access audit trail), `Compliance` (RBI DLG checklist).
- `frontend/src/components/` — `HealthHeader` (bureau chip), `ScoreDial`, `DimensionRadar`, `DimensionCard` (peer-percentile chip, reason-code chips, grey-out for unconsented), `DecisionPanel`, `StrengthsRisks`, `MlPanel` (calibrated/monotonic badges, AUC + Brier), `WhatIfPanel` (officer sensitivity sliders), `DataFreshness`, `RecommendationsPanel` (computed uplifts + path-to-next-band banner), `ScoreHistoryChart` (solid dots = observed runs, hollow = reconstructed), `ApplyButton`, `DemoGuide` (9-step scripted judge tour with per-step honesty notes), `WhatsAppToaster`.
- `frontend/src/api.ts` — thin fetch client covering every endpoint; base URL comes from `VITE_API_URL` (build-time), falling back to `/api` for the dev proxy. `types.ts` mirrors backend schemas (kept in sync manually). The UI is English-only (a Hindi i18n layer existed briefly and was removed by request).

## Scoring Model Design (initial direction)

Dimensions (each 0–100, weighted into composite):

1. **Revenue Health** — GST turnover level, growth trend, seasonality (GSTR-1/3B)
2. **Cash-Flow Strength** — AA bank data: inflow/outflow ratio, balance volatility, bounce/return incidents
3. **Digital Transaction Vitality** — UPI velocity, customer-count diversity, ticket-size distribution
4. **Compliance Discipline** — GST filing timeliness, EPFO deposit regularity (ITR filing is a planned production signal — no ITR connector exists in the demo)
5. **Employment Stability** — EPFO headcount trend, salary payment regularity
6. **Obligation & Leverage** — existing EMIs/obligations inferred from bank-statement debits only. The **bureau connector is a display-only stub** ("bureau if available"): it proves the plug-in seam with running code (NTC → NO-HIT chip on the card) but is never read by any scorer — the pitch remains scoring the bureau-less.

Composite → risk bands (e.g., A/B/C/D) → decision recommendation (approve / refer / decline) with suggested limit derived from cash-flow surplus.

**In parallel, an ML "second opinion":** a Platt-calibrated, monotonicity-constrained `HistGradientBoostingClassifier` trained at first boot on ~500 synthetic MSMEs (ground-truth default outcomes from a hidden logistic simulator over the persona knobs) predicts a 12-month probability of default from the same 18 observable features, with 80/20 holdout AUC **and Brier score** reported on the card. Training features come from the full production pipeline (data-pack → feature extraction), so there is no train/serve skew; the artifact persists under `.model_cache/` keyed by the version hash. Local explanations come from counterfactual deltas — replace each feature with its population median and measure the PD change. Top-3 up = drivers; top-3 down = supports. The card carries a structured `agrees_with_rulebook` flag, and the portfolio surfaces the divergence queue ("ML disagrees" filter) so an underwriter can work the divergent cases. **The ML PD is advisory only — the approve/refer/decline decision, limit and tenor come from the rule-based scorecard alone (champion/challenger framing). If a judge asks whether the model affects the decision, the honest answer is no, by design.**

**Known ML honesty caveats (state them, don't hide them):** training labels come from a hand-authored simulator over the same knobs that generate the features, so the model has no real-world validity — the calibration and holdout metrics are internally consistent, not externally validated. Monotonic constraints and Platt calibration are governance mechanics demonstrated on synthetic data, not evidence of production readiness (that needs real-outcome backtesting — see the /compliance page's PRODUCTION_PLAN rows).

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
- `GET /api/msme/{gstin}/data-pack?consent=&sim=` — normalized GST + AA + EPFO + UPI, scoped to the grant's sources (bad handle → 403); `sim=1..3` regenerates as a fresh pull N months out
- `GET /api/msme/{gstin}/health-card?consent=&sim=` — full scored card + ML PD (bad handle → 403)
- `POST /api/msme/{gstin}/what-if` — sensitivity simulator: feature overrides → new composite/band/decision/PD deltas
- `GET /api/consent/{id}/artefact` — downloadable ReBIT-inspired consent-artefact JSON
- `GET /api/audit/log` — data-access audit trail (every pull, ALLOWED/DENIED)
- `GET /api/compliance` — RBI Digital Lending Guidelines checklist
- `GET /api/portfolio` — 30-MSME book with band/sector/recommendation mix, trend + EWS flags, watch-list, divergence count, concentration guardrails, vintage cohorts (cached at startup)
- `POST /api/portfolio/refresh` — invalidate + re-score the book
- `POST /api/portfolio/stress` + `GET /api/portfolio/stress/presets` — shock the book, get the band-migration report
- `POST /api/portfolio/{gstin}/action` + `GET /api/portfolio/actions` — watch-list action workflow
- `GET /api/impact` — before/after comparison vs a bureau-only lender + inclusion dashboard
- `POST /api/uli/pull` — simulated ULI health-card pull; returns event timeline + card
- `POST /api/ocen/loan-request` — simulated OCEN loan draft against an existing card
- `POST /api/msme/{gstin}/apply` — create loan application (auto-sanction + KFS if APPROVE)
- `GET /api/applications` / `/{id}` / `/{id}/sanction` — application + sanction-letter retrieval
- `GET /api/consent/log` — every consent artefact issued this session
- Interactive docs at `/docs`

**CI** — `.github/workflows/ci.yml`: backend job (ruff + persona smoke-test), frontend job (`npm run build`, which type-checks via `tsc`). Runs on push/PR.

**Sanity checks:**
```
# Score every persona in one shot:
cd backend && python -c "from app.scoring.engine import score_gstin; from app.personas import PERSONAS; [print(f'{p.trade_name:22} → {score_gstin(p.gstin).composite_score}/{score_gstin(p.gstin).risk_band}') for p in PERSONAS]"
```

**Preview launcher** — `.claude/launch.json` defines `backend` (port 8000) and `frontend` (port 5173). Use `preview_start` in Claude Code to run either.

## Deployment (Render)

`render.yaml` is a Render Blueprint defining both services (deploy via Render dashboard → New → Blueprint). Gotchas already encoded in that file's comments — keep them true:

- Backend must bind `0.0.0.0:$PORT` in production (the local `127.0.0.1:8000` command is dev-only).
- Frontend is a static site with an SPA rewrite rule (`/* → /index.html`) so client-side routes survive refresh/deep-link.
- `VITE_API_URL` (must include the `/api` suffix) is baked in at **build** time — changing it requires a frontend redeploy, not a restart. If the backend's public URL changes, update it in `render.yaml`.
- Backend CORS is wide-open (`allow_origins=["*"]`) — acceptable for the demo, noted as a production concern.

## Known Demo Limitations (state them if asked — never hide them)

- **Deterministic mock data**: connectors dispatch to a GSTIN-seeded generator, so pulling the same GSTIN twice on the same day yields identical data. Mitigations that keep the demo honest: the **what-if simulator** (officer moves a lever, everything re-scores live) and the **`sim=` fresh-pull control** (regenerates the pack at a later anchor month — clearly labelled as simulated regeneration, not real new data).
- **Score history is a hybrid**: solid dots are observed recorded scoring runs (persisted in `.snapshots.json`); hollow dots are reconstructed by windowed re-scoring of today's pack. The chart tooltip says which is which.
- **ULI/OCEN timelines**: hop details carry real facts (consent handle, record counts, score); the latencies are the one synthetic element, jittered per run.
- **NTC/NTB is modeled, not sourced**: personas carry explicit `is_ntc`/`is_ntb` flags (NTC = young + no live loans, NTB = banks elsewhere via AA) rather than a customer-master lookup — though the bureau stub now makes the NTC NO-HIT visible on the card.
- **`types.ts` mirrors `schemas.py` manually** — no OpenAPI codegen; when backend schemas change, update the frontend types in the same commit.
- **In-memory state**: consent registry, applications, watch-list actions and audit trail reset on restart (the ML model cache and score snapshots persist to gitignored files). Note for Render: free-tier instances lose even those files on redeploy.

## What NOT to Do

- Don't add real credentials, real API keys for GSTN/AA sandboxes, or real personal/business data to the repo.
- Don't build auth/RBAC/audit-trail plumbing beyond what the demo needs — mention it in docs instead.
- Don't chase model accuracy at the cost of explainability or demo clarity.
- Don't invent data sources beyond the consented-rails story (no scraping, no social-media signals) — it undermines the regulatory pitch.
