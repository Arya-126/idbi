# Gap Analysis & Feature Enhancement Opportunities

## What the organizer explicitly asked for vs what's built

### ✅ Fully Covered

| Expected Outcome (verbatim) | What's Built |
|---|---|
| "aggregates alternate data (GST, UPI, AA, EPFO, etc.)" | 4/4 core sources implemented with connector protocols |
| "computes a multidimensional financial health score" | 6-dimension scorecard + composite 0–1000 + risk bands |
| "visualizes strengths and risks" | Radar chart, factor cards, top-3 strengths/risks, officer/borrower views |
| "enables near real-time credit assessment" | On-demand scoring, sub-second health card generation |
| "expands onboarding of credit-invisible MSMEs" | NTC/NTB personas scored + approved, portfolio KPI tracks count |
| "improving portfolio quality" | Watchlist, PD monitoring, band/sector/recommendation mix |

### ⚠️ Partially Covered → ✅ NOW FULLY COVERED

| Expected Outcome | Previous State | Current State |
|---|---|---|
| "integrates with ULI/OCEN/AA ecosystems" | AA only; ULI/OCEN were protocol seams | ✅ **NOW COVERED** — `ecosystem.py` simulates full ULI pull (`POST /api/uli/pull`) and OCEN loan request (`POST /api/ocen/loan-request`) with realistic multi-hop timelines (LSP→ULI→AA→FIP→Bank→LSP). Frontend `Ecosystem.tsx` page renders the trace timeline + decision. |
| "etc." in data sources | Only GST/UPI/AA/EPFO | ⚠️ Still only 4 core sources. No ITR/MCA/utility connector added. However, the connector-protocol design makes adding a 5th trivial. |

### ❌ Not Covered → Status Update

| Implied Need | Previous Status | Current Status |
|---|---|---|
| **Before/after comparison** — "high rejection rates" implies measuring improvement | Not built | ✅ **NOW COVERED** — `impact.py` computes traditional-bank-only verdicts (bureau+scale+vintage gates) vs alternate-data verdicts. `GET /api/impact` returns `ImpactSummary` with metrics (approval coverage lift, NTC/NTB included, exposure unlocked, PD trade-off). Frontend `Impact.tsx` page visualizes the comparison with rescued-row table. |
| **Loan application workflow** — "credit decisioning" implies end-to-end flow | Not built | ✅ **NOW COVERED** — `applications.py` provides full apply→sanction flow. `POST /api/msme/{gstin}/apply` creates `LoanApplication` (SANCTIONED/UNDER_REVIEW/REJECTED). `SanctionLetter` generated with EMI calc, processing fee, covenants. Frontend: `ApplyButton.tsx` on health card, `SanctionLetter.tsx` page with `window.print()` for PDF export. |
| **Audit trail** — regulatory context demands it | Explainability only, no persistent log | ✅ **NOW COVERED** — `GET /api/consent/log` returns all consent grants with status (GRANTED/REVOKED/EXPIRED). Frontend `ConsentLog.tsx` page shows handle, MSME, sources, grant/expiry dates, status with refresh button. |

---

## Features That Would Strengthen the Submission

### 🔴 HIGH IMPACT — Directly addresses judge questions

#### 1. Before/After Impact Dashboard
> ✅ **IMPLEMENTED**

**What was built**: `impact.py` + `Impact.tsx` — traditional scoring simulation (reject NTC, thin-vintage, low-turnover, proprietorship gates) vs. alternate-data scoring. Shows 4 KPI metrics (approval coverage lift, NTC/NTB onboarded, exposure unlocked, PD trade-off). Includes a table of "rescued" MSMEs that traditional banks would reject but alternate-data approves.

**Files**: [impact.py](file:///d:/Anantha/Academic/Projects/idbi/backend/app/impact.py) · [Impact.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/pages/Impact.tsx) · `GET /api/impact`

#### 2. ULI/OCEN Simulated Flow
> ✅ **IMPLEMENTED**

**What was built**: `ecosystem.py` + `Ecosystem.tsx` — simulates both ULI pull (8-step LSP→ULI→AA→FIP→Bank trace with realistic latencies) and OCEN loan request (5-step LSP→OCEN→Bank→sanction flow). Returns timeline events with actor, action, detail, latency. Maps to SANCTIONED/REFERRED/REJECTED.

**Files**: [ecosystem.py](file:///d:/Anantha/Academic/Projects/idbi/backend/app/ecosystem.py) · [Ecosystem.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/pages/Ecosystem.tsx) · `POST /api/uli/pull` · `POST /api/ocen/loan-request`

#### 3. Actionable Credit Improvement Recommendations
> ✅ **IMPLEMENTED**

**What was built**: Backend generates `improvement_recommendations` in the HealthCard (via `engine.py`). Each recommendation has `action`, `detail`, `dimension_key`, `est_score_uplift_pts`, and `time_horizon_months`. Frontend `RecommendationsPanel.tsx` renders ranked suggestions with dimension badges and estimated point uplift.

**Files**: [RecommendationsPanel.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/components/RecommendationsPanel.tsx) · `schemas.py:Recommendation` · `engine.py`

#### 4. Loan Application & Sanction Letter
> ✅ **IMPLEMENTED**

**What was built**: `applications.py` — full lifecycle: `POST /api/msme/{gstin}/apply` → `LoanApplication` (auto-sanction if APPROVE, UNDER_REVIEW if REFER, REJECTED if DECLINE). `SanctionLetter` with EMI formula, processing fee (0.5%), 5 covenants, validity (30 days). Frontend: `ApplyButton.tsx` (on DecisionPanel), `SanctionLetter.tsx` page with `window.print()` for PDF. `WhatsAppToaster.tsx` fires simulated WhatsApp notifications on sanction/review/decline.

**Files**: [applications.py](file:///d:/Anantha/Academic/Projects/idbi/backend/app/applications.py) · [ApplyButton.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/components/ApplyButton.tsx) · [SanctionLetter.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/pages/SanctionLetter.tsx)

---

### 🟡 MEDIUM IMPACT — Differentiators that wow judges

#### 5. Sector Benchmarking
> ✅ **IMPLEMENTED**

**What was built**: `DimensionCard.tsx` now shows `peer_percentile` for each dimension — "Top 25% of sector", "Behind the sector median — Xth percentile", etc. Percentile is computed from the portfolio data and included in the `DimensionScore` schema.

**Files**: [DimensionCard.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/components/DimensionCard.tsx) (lines 22–35, 63–65, 106–117)

#### 6. Time-Series Score Trend (Historical View)
> ✅ **IMPLEMENTED**

**What was built**: Backend `_score_history()` in `engine.py` computes sliding-window composite scores. `ScoreHistoryChart.tsx` (Recharts `ComposedChart`) renders area+line chart with band reference lines (A/B/C thresholds), trend delta, and tooltip showing composite + band per month.

**Files**: [ScoreHistoryChart.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/components/ScoreHistoryChart.tsx) · `engine.py:_score_history()` · `schemas.py:ScoreHistoryPoint`

#### 7. Cash-Flow Based Limit Workings
> ✅ **IMPLEMENTED**

**What was built**: `decision.py` emits `limit_workings` (list of `LimitStep` objects with `label`, `amount_paise`, `detail`). `DecisionPanel.tsx` renders limit derivation steps showing the math: monthly surplus → multiplier → cap → final limit.

**Files**: [DecisionPanel.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/components/DecisionPanel.tsx) (lines 51–80) · `decision.py` · `schemas.py:LimitStep`

#### 8. Early Warning System (EWS)
> ❌ **NOT IMPLEMENTED**

No EWS-specific column, badges, or trend-based flags in the portfolio table. The watchlist flagging exists (based on recommendation + ML PD > 20%), but there is no score-trend-based deterioration detection or trigger-based alerts. The `score_history` data exists in the backend but isn't used for portfolio-level EWS.

#### 9. PDF / Report Export
> ✅ **IMPLEMENTED**

**What was built**: Both `HealthCard.tsx` and `SanctionLetter.tsx` have `window.print()` buttons. `styles.css` includes `@media print` rules for clean printable output. Covers health card PDF and sanction letter PDF.

**Files**: [HealthCard.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/pages/HealthCard.tsx) (line 62) · [SanctionLetter.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/pages/SanctionLetter.tsx) (line 57) · [styles.css](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/styles.css) (line 53)

---

### 🟢 LOW IMPACT — Nice-to-haves

#### 10. Multi-language Support (Hindi/English toggle)
> ✅ **IMPLEMENTED**

**What was built**: `i18n.tsx` provides `LangProvider` context with `en`/`hi` dictionary (~25 key translations covering nav, consent flow, credit decisions, borrower panel). Persisted in `localStorage`. `useLang()` hook with `t()` translation function.

**Files**: [i18n.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/i18n.tsx)

#### 11. ITR Connector (5th data source)
> ❌ **NOT IMPLEMENTED**

No ITR connector, schema, or scoring changes found. Still 4 sources only.

#### 12. WhatsApp Notification Simulation
> ✅ **IMPLEMENTED**

**What was built**: `WhatsAppToaster.tsx` — animated bottom-right toast with WhatsApp branding (green glyph, "IDBI Bank via WhatsApp"), auto-dismiss after 6s. Fired on: sanction issued, sent to underwriter, application declined. Tone-based styling (good/warn/bad).

**Files**: [WhatsAppToaster.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/components/WhatsAppToaster.tsx) · [ApplyButton.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/components/ApplyButton.tsx)

#### 13. Consent Audit Log Page
> ✅ **IMPLEMENTED**

**What was built**: `GET /api/consent/log` returns all consent artefacts with handle, MSME, sources, granted/expires dates, and status (GRANTED/REVOKED/EXPIRED). Frontend `ConsentLog.tsx` renders a compliance table with refresh button.

**Files**: [ConsentLog.tsx](file:///d:/Anantha/Academic/Projects/idbi/frontend/src/pages/ConsentLog.tsx) · `main.py:consent_log()`

---

## Updated Summary

| # | Feature | Previous | Current | Status |
|---|---|---|---|---|
| 1 | Before/After Impact Dashboard | ❌ | ✅ | `impact.py` + `Impact.tsx` |
| 2 | ULI/OCEN Simulated Flow | ❌ | ✅ | `ecosystem.py` + `Ecosystem.tsx` |
| 3 | Actionable Recommendations | ❌ | ✅ | `RecommendationsPanel.tsx` + backend |
| 4 | Loan Application + Sanction Letter | ❌ | ✅ | `applications.py` + `SanctionLetter.tsx` |
| 5 | Sector Benchmarking | ❌ | ✅ | `peer_percentile` in `DimensionCard.tsx` |
| 6 | Score Trend (Historical) | ❌ | ✅ | `ScoreHistoryChart.tsx` + `_score_history()` |
| 7 | Limit Workings | ❌ | ✅ | `limit_workings` in `DecisionPanel.tsx` |
| 8 | Early Warning System (EWS) | ❌ | ❌ | Not implemented |
| 9 | PDF / Report Export | ❌ | ✅ | `window.print()` + `@media print` |
| 10 | Hindi/English (i18n) | ❌ | ✅ | `i18n.tsx` with `LangProvider` |
| 11 | ITR Connector (5th source) | ❌ | ❌ | Not implemented |
| 12 | WhatsApp Notification | ❌ | ✅ | `WhatsAppToaster.tsx` |
| 13 | Consent Audit Log | ❌ | ✅ | `ConsentLog.tsx` + `GET /api/consent/log` |

**Result: 11 of 13 gaps are now covered. Only EWS (#8) and ITR Connector (#11) remain unimplemented.**
