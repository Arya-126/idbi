# MSME Financial Health Card

AI/ML-driven credit assessment for New-to-Credit and New-to-Bank MSMEs, built
for the Financial Inclusion / Digital Lending / Credit Decisioning track.

Aggregates GST returns, Account Aggregator bank data, EPFO payroll and UPI
transaction signals into a multidimensional health score with factor-level
explainability and an approve / refer / decline recommendation.

## Quick start

```bash
# Backend — FastAPI on :8000
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend — Vite on :5173 (in a second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and pick any MSME to walk the flow:
**portfolio → consent → data pull → Financial Health Card**.
Interactive API docs at http://localhost:8000/docs.

## What's inside

- **6 scored dimensions** — Revenue Health, Cash-Flow Strength, Digital
  Transaction Vitality, Compliance Discipline, Employment Stability,
  Obligation & Leverage. Weights sum to 1.0; every dimension breaks down into
  human-readable factors with signed point contributions, and trends are
  computed from real time series (filing-rate, balance and EMI trajectories).
- **ML second opinion** — a `HistGradientBoostingClassifier` (scikit-learn)
  trained at startup on 500 synthetic MSMEs predicts a 12-month probability
  of default, with an 80/20 holdout AUC reported on the card. Local
  explanations via counterfactual deltas — top-3 drivers raising PD, top-3
  supports holding it down. Shown alongside the rulebook with a structured
  "agrees" / "disagrees" chip so underwriters can flag divergences. Advisory
  only — the approve / refer / decline decision comes from the rulebook alone.
- **Enforced consent flow** — `POST /api/consent` registers a grant; data
  endpoints validate the `?consent=` handle (unknown / revoked / expired →
  403); grants are revocable via `POST /api/consent/{id}/revoke`. The consent
  page performs a real data pull and shows actual record counts per source.
  Mock GSTN / AA / EPFO / UPI adapters sit behind per-rail protocols — AA
  consent-first today, ULI / OCEN-ready by design.
- **Two audiences, one card** — a credit-officer view (decision panel, ML
  panel, factor detail) and a plain-language borrower view ("what this means
  for your business, what to improve"), toggled on the card.
- **Portfolio dashboard** — `/portfolio` view for the credit officer: 30
  MSMEs (5 demos + 25 sampled), avg score / PD / exposure KPIs, band /
  sector / recommendation mixes, a filterable watch-list, an NTC/NTB filter
  with per-row badges, and a one-click re-score of the whole book.
- **NTC/NTB modeled, bureau-free by design** — no bureau connector exists
  anywhere; NTC firms carry no live EMIs, NTB firms bank elsewhere and are
  visible only through the AA rail.
- **5 demo personas** — established manufacturer (Band A), micro retailer
  (Band B), distressed trader (Band D), NTC+NTB IT-services startup banking
  with another bank (Band A — the inclusion story), NTB micro exporter
  (Band B).
- **Explainable decision** — recommended limit, tenor, ROI plus a rationale
  string, all derived from features not learned weights.

See [`CLAUDE.md`](CLAUDE.md) for the design principles, domain glossary and
architecture.

## Repo layout

```
backend/
  requirements.txt
  app/
    schemas.py             # all Pydantic models
    personas.py            # persona registry + synthetic data generator
    consent.py             # consent registry: issue / validate / revoke
    connectors/            # Identity / GST / AA / EPFO / UPI adapters (mock + protocol)
    scoring/               # features → dimensions → decision → engine
    ml.py                  # PD model, holdout AUC, counterfactual explainer
    ml_data.py             # population sampler + ground-truth default simulator
    portfolio.py           # 30-MSME book, cached summary, refresh
    main.py                # FastAPI surface

frontend/
  package.json, vite.config.ts, tailwind.config.js
  src/
    pages/                 # Landing, Consent, HealthCard, Portfolio
    components/            # HealthHeader, ScoreDial, DimensionRadar, MlPanel, ...
    api.ts, types.ts, utils/format.ts

.claude/launch.json        # `preview_start backend` / `preview_start frontend`
CLAUDE.md                  # design/contribution guide for Claude Code
```

## Disclaimer

All data is synthetic. Score is advisory only — final credit decision rests
with the underwriter.