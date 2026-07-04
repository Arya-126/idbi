# Verifiable Outcomes — MSME Financial Health Card

[x verified by antigravity]-[x manualy verified ]

## 1. Alternate Data Aggregation

- [x]-[x] Ingests **GST** data (filings, turnover, compliance history) — `GstConnector` protocol + `MockGstConnector` → 24mo GSTR returns via `personas.py`; scored in `score_revenue_health`, `score_compliance`
- [x]-[x] Ingests **UPI** transaction data (inflows, outflows, patterns) — `UpiConnector` protocol + `MockUpiConnector` → 12mo UPI aggregates; scored in `score_digital_vitality`
- [x]-[x] Ingests **Account Aggregator (AA)** data (bank statements, FIP data) — `AaConnector` protocol + `MockAaConnector` (validates consent handle); 12mo bank txns; scored in `score_cash_flow`, `score_obligation_leverage`
- [x]-[x] Ingests **EPFO** data (employee count, compliance, growth trends) — `EpfoConnector` protocol + `MockEpfoConnector` → 12mo EPFO monthly records; scored in `score_employment`, `score_compliance`
- [ ]-[ ] Supports additional alternate data sources (e.g., ITR, MCA, utility bills) — **NOT implemented**. CLAUDE.md explicitly notes: "Bureau and ITR connectors are deliberately absent". No MCA/utility connectors exist. Utility payments appear only as categorized txns inside AA bank data.
- [x]-[x] Data from multiple sources is **unified into a single borrower profile** — `DataPack` schema in `schemas.py` unifies identity + GST + AA + EPFO + UPI into one Pydantic model; `build_data_pack()` in `engine.py` assembles it

## 2. AI/ML-Driven Credit Decisioning

- [x]-[x] Uses **AI/ML models** (not just rule-based) for credit assessment — `PdModel` in `ml.py`: `HistGradientBoostingClassifier` trained on 500 synthetic MSMEs, 18-feature vector, counterfactual explainer. ML PD is advisory alongside the rulebook.
- [x]-[x] Handles **New-to-Credit (NTC)** enterprises with no prior credit history — Personas carry `is_ntc=True` flag (e.g., NewGen Tech); NTC firms have zero EMI, no credit bureau; scoring handles gracefully via Obligation & Leverage dimension ("+15 no existing debt burden")
- [x]-[x] Handles **New-to-Bank (NTB)** enterprises with no relationship with the bank — Personas carry `is_ntb=True` flag; NTB firms bank elsewhere, data arrives via AA rail; `MockAaConnector` uses different bank names for NTB personas
- [x]-[x] Reduces **rejection rates** for viable borrowers vs. traditional methods — Demonstrated via the NTC/NTB persona (NewGen Tech) scoring Band A despite zero bureau history; portfolio dashboard shows `ntc_ntb_count` of approved NTC/NTB firms
- [x]-[x] Demonstrates ability to **identify creditworthy MSMEs** that traditional scoring would miss — Same as above: NewGen Tech (NTC+NTB) gets APPROVE with strong cash-flow/compliance signals despite being credit-invisible

## 3. Multidimensional Financial Health Score

- [x]-[x] Computes a **composite financial health score** (not a single metric) — `compute_composite()` in `decision.py`: weighted sum of 6 dimension scores (0-100 each), scaled to 0-1000; mapped to risk bands A/B/C/D
- [x]-[x] Score is **multidimensional** — covers multiple axes — 6 dimensions: Revenue Health (0.20), Cash-Flow Strength (0.22), Digital Transaction Vitality (0.15), Compliance Discipline (0.15), Employment Stability (0.12), Obligation & Leverage (0.16)
- [x]-[x] Each dimension is individually scored and explainable — Every dimension breaks down into named `Factor` objects with `contribution`, `kind` (STRENGTH/RISK/NEUTRAL), and `detail` string; rendered per-dimension in `DimensionCard.tsx`
- [x]-[x] Score methodology is **transparent and interpretable** (not a black box) — Base-50 + signed factor contributions, clamped [0,100]; ML uses counterfactual explanations (not SHAP); `agrees_with_rulebook` flag surfaces divergences
- [x]-[x] **Sector benchmarking** — each dimension shows `peer_percentile` (e.g., "Top 25% of Manufacturing MSMEs"), computed from the portfolio. Rendered in `DimensionCard.tsx` with percentile labels and narrative text. ✅ Verified: dimension cards show "TOP 10% IN SECTOR", "MEDIAN FOR SECTOR", "TOP 14% IN SECTOR" etc.
- [x]-[x] **Score history / trend chart** — `_score_history()` in `engine.py` computes sliding-window composites; `ScoreHistoryChart.tsx` renders area+line chart with band reference lines (A/B/C thresholds) and trend delta. ✅ Verified: "COMPOSITE SCORE, LAST 7 MONTHS" chart with 876→874 (−2), dashed A/B/C bands.

## 4. Visualization of Strengths & Risks

- [x]-[x] Visual **Financial Health Card** output per MSME — Full `HealthCard.tsx` page with `HealthHeader`, `ScoreDial` (SVG), `DimensionRadar` (Recharts radar chart), `DimensionCard`, `DecisionPanel`, `MlPanel`, `DataFreshness`
- [x]-[x] Clearly highlights **strengths** — `StrengthsRisks` component renders top-3 strengths from `pick_top_strengths()` (ranked by contribution × weight)
- [x]-[x] Clearly highlights **risks** — Same component renders top-3 risks from `pick_top_risks()`; each factor tagged as STRENGTH/RISK/NEUTRAL with FactorKind enum
- [x]-[x] Dashboard/UI is intuitive for a credit officer to act on — Credit officer / borrower view toggle; `DecisionPanel` shows recommendation + limit + tenor + ROI + rationale; `Portfolio.tsx` has KPIs, filters, re-score button
- [x]-[x] **Cash-flow based limit workings** — `DecisionPanel.tsx` renders `limit_workings` (list of `LimitStep` objects) showing the math behind the suggested limit: monthly surplus → multiplier → cap → final limit. Computed in `decision.py`. ✅ Verified: "How did we get this limit?" expands to show Avg turnover ₹35.4L → Turnover cap ₹1.06Cr → Surplus ₹4.1L → Surplus cap ₹73.9L → Suggested ₹73.9L.
- [x]-[x] **Actionable improvement recommendations** — `RecommendationsPanel.tsx` renders ranked improvement tips with dimension badges, estimated score uplift ("+X pts"), time horizon, and detail text. Generated by backend `engine.py` in `improvement_recommendations`. ✅ Verified: Kumar Enterprises shows 5 recommendations (Obligation +18pts, Compliance +15pts, Cash Flow +15pts, Revenue +15pts, Compliance +10pts).
- [x]-[x] **PDF / print export** — `HealthCard.tsx` and `SanctionLetter.tsx` both have `window.print()` buttons. `styles.css` includes `@media print` rules for clean printable output. ✅ Verified: "⇩ Print / Save PDF" button visible on both Health Card and Sanction Letter pages.

## 5. Ecosystem Integration

- [x]-[x] Integration with **ULI (Unified Lending Interface)** — **NOW IMPLEMENTED** as simulated flow. `ecosystem.py` + `POST /api/uli/pull` simulates 8-step ULI pull (LSP→ULI→AA→FIP→Bank→LSP) with realistic latencies. `Ecosystem.tsx` renders the trace timeline alongside the health card result. ✅ Verified: 8-step trace with 706ms total, returned Band A · 874 · PD 0.7%.
- [x]-[x] Integration with **OCEN (Open Credit Enablement Network)** — **NOW IMPLEMENTED** as simulated flow. `ecosystem.py` + `POST /api/ocen/loan-request` simulates 5-step OCEN loan request (LSP→OCEN→Bank→sanction→LSP). Maps to SANCTIONED/REFERRED/REJECTED with terms. ✅ Verified: 5-step trace, SANCTIONED ₹15.0L · 24mo · 10.5%.
- [x]-[x] Integration with **AA (Account Aggregator)** framework — Implemented as a consent-first flow: `consent.py` (issue/validate/revoke), `MockAaConnector` validates consent handles, `Consent.tsx` UI performs real data pull with handle. AA consent lifecycle is functional.
- [x]-[x] Demonstrates standards-compliant data exchange (consent-based, API-driven) — Consent-based: `POST /api/consent`, handle validated on every `/data-pack` and `/health-card` call (403 on bad handle); API-driven: RESTful FastAPI surface with Pydantic schemas

## 6. Near Real-Time Credit Assessment

- [x]-[x] Credit assessment is generated in **near real-time** (not batch/offline) — `GET /api/msme/{gstin}/health-card` scores on demand: connectors → DataPack → Features → 6 dimensions → composite → ML PD → HealthCard, all in a single synchronous request
- [x]-[x] System can process a new MSME application and return a health card quickly — ML model pre-trained at startup; health card generation is sub-second for any registered GSTIN
- [ ]-[ ] Supports **live/streaming data** refresh (not just one-time snapshot) — **PARTIAL**. Portfolio has `POST /api/portfolio/refresh` to re-score the book, but underlying data is deterministic mock (same GSTIN same day = identical data). No streaming/webhook data refresh. CLAUDE.md admits: "pulling the same GSTIN twice on the same day yields identical data".

## 7. Financial Inclusion Impact

- [x]-[x] Expands onboarding of **credit-invisible MSMEs** (measurable increase) — Portfolio dashboard shows `ntc_ntb_count` KPI ("NTC/NTB approved"); NTC/NTB filter on the book table; NewGen Tech (NTC+NTB) scores Band A
- [x]-[x] Improves **portfolio diversification** (wider segment coverage) — Portfolio shows `sector_mix` (multiple sectors), `band_distribution` (A/B/C/D spread), `recommendation_mix`; 30 MSMEs across diverse sectors
- [x]-[x] Improves **portfolio quality** (lower NPA risk with alternate data signals) — Watchlist flagging (REFER + DECLINE + ML PD>20%); avg PD KPI; DSCR proxy and bounce checks as hard gates for decline
- [x]-[x] Demonstrates **faster financial inclusion** compared to status quo — **NOW IMPLEMENTED** via Before/After Impact Dashboard. `impact.py` runs all 30 MSMEs through a traditional-bank-only scoring (bureau+scale+vintage gates) and compares vs alternate-data verdicts. `GET /api/impact` returns `ImpactSummary` with approval coverage lift, NTC/NTB included, exposure unlocked, PD trade-off. `Impact.tsx` page visualizes the comparison with a rescued-row table. ✅ Verified: Approval 33%→70%, NTC/NTB 0→12, Exposure +₹2.61Cr, 17 rescued MSMEs.

## 8. Cross-Cutting / Implicit Outcomes

- [x]-[x] Data **privacy and consent** mechanisms are in place (AA consent framework) — Full consent lifecycle: `POST /api/consent` (issue), validate (GSTIN match + status + expiry), `POST /api/consent/{id}/revoke`; consent page in frontend; borrower view notes "data you consented to share"
- [x]-[x] Solution is **scalable** to large MSME volumes — Architecture is connector-protocol + feature-engineering + scoring pipeline; stateless API; portfolio supports sampled synthetic population (currently 30, easily expandable). Production scaling concerns noted in docs.
- [x]-[x] Handles **incomplete/noisy data** gracefully — Scoring handles missing data: `epfo_active=False` → neutral scores; `turnover_growth_pct=None` → "trend not yet reliable"; `dscr_proxy=None` → unlevered treatment; EPFO-inactive personas still score all 6 dimensions
- [x]-[x] Provides **audit trail / explainability** for regulatory compliance — Every dimension decomposes into factors with human-readable `detail` strings; ML provides counterfactual drivers/supports; `agrees_with_rulebook` flag; `model_version` hash; `holdout_auc` reported. **Consent audit log** now implemented: `GET /api/consent/log` + `ConsentLog.tsx` page shows all consent artefacts with status.

## 9. End-to-End Loan Journey (NEW)

- [x]-[x] **Loan application flow** — `POST /api/msme/{gstin}/apply` creates a `LoanApplication` (SANCTIONED/UNDER_REVIEW/REJECTED). `ApplyButton.tsx` on the Health Card decision panel triggers the flow. `applications.py` handles the lifecycle. ✅ Verified: "Apply for credit →" button on Sharma Textiles → auto-navigates to sanction letter page.
- [x]-[x] **Sanction letter** — Auto-generated for SANCTIONED applications with EMI formula, processing fee (0.5%), 5 covenants, 30-day validity. `SanctionLetter.tsx` page renders it with `window.print()` for PDF. `/api/applications/{id}/sanction` endpoint. ✅ Verified: Full letter with ₹73.9L, 36mo, 10.50%, EMI ₹2.4L/mo, fee ₹37.0K, valid until 3/8/2026, Print button.
- [x]-[x] **WhatsApp notification simulation** — `WhatsAppToaster.tsx` fires animated toast bubbles on sanction/review/decline events. WhatsApp-branded with "IDBI Bank via WhatsApp" and auto-dismiss after 6s. ✅ Verified: Green WhatsApp toast "Sanction issued 🎉 — Sharma Textiles: ₹73.9L · 36 months" in bottom-right.
- [x]-[x] **Consent audit log** — `GET /api/consent/log` lists all consent artefacts (handle, MSME, sources, granted/expires, status). `ConsentLog.tsx` renders a compliance table with refresh button. ✅ Verified: 30+ consent entries with handle IDs, MSME names, GST/AA/EPFO/UPI source pills, dates, GRANTED status.
- [x]-[x] **Multi-language support** — `i18n.tsx` provides Hindi/English toggle via `LangProvider` context with ~25 key translations covering nav, consent flow, credit decisions, borrower panel. Persisted in `localStorage`. ✅ Verified: Nav switches to ऑनबोर्डिंग/पोर्टफोलियो/प्रभाव/यूएलआई/ओसीईएन/सहमति लॉग and back to English.
