# Manual Verification Guide — MSME Financial Health Card

> **Pre-requisite**: Start both backend and frontend:
> ```bash
> # Terminal 1 — backend
> cd backend
> .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
>
> # Terminal 2 — frontend
> cd frontend
> npm install
> npm run dev
> ```
> Open **http://localhost:5173** in your browser.

---

## 1. Alternate Data Aggregation

### 1.1 GST data ingestion
1. On the landing page, click any MSME (e.g., **Sharma Textiles**)
2. On the Consent page, ensure **GST Returns** is listed with "GSTR-1 & GSTR-3B filings, last 24 months"
3. Click **"Grant consent & fetch data"**
4. Watch the GST source turn green with a count like **"✓ 24 returns"**
5. ✅ If you see "24 returns" → GST ingestion verified

### 1.2 UPI data ingestion
1. Same consent flow — check that **UPI Transaction Signal** is listed
2. After granting, it should show **"✓ 12 months"**
3. ✅ If count appears → UPI ingestion verified

### 1.3 AA (Account Aggregator) data ingestion
1. Same consent flow — check **Bank Statements (Account Aggregator)** is listed
2. After granting, it should show something like **"✓ 210 bank txns"**
3. ✅ If bank txn count appears → AA ingestion verified

### 1.4 EPFO data ingestion
1. Same consent flow — check **EPFO Payroll** is listed
2. After granting, it should show **"✓ 12 months"** (or "not covered" for non-EPFO MSMEs)
3. ✅ If count or "not covered" appears → EPFO ingestion verified

### 1.5 Additional data sources (ITR, MCA, utility)
- **NOT implemented** — no manual verification needed. Skip this item.

### 1.6 Unified borrower profile
1. After consent, you'll auto-navigate to the **Health Card** page
2. The card shows the enterprise name, GSTIN, sector, and scores from ALL sources on a single page
3. ✅ If one unified card appears with data from GST + AA + EPFO + UPI → verified

---

## 2. AI/ML-Driven Credit Decisioning

### 2.1 ML model used (not just rule-based)
1. On the **Health Card** page (credit officer view), scroll down
2. Look for the **"ML second opinion"** panel
3. It should show: **Probability of Default**, **Confidence** (high/medium/low), **Model version**, **Holdout AUC**, and **Drivers / Supports**
4. ✅ If the ML panel renders with PD + AUC + drivers/supports → ML verified

### 2.2 NTC (New-to-Credit) handling
1. From the landing page, pick **NewGen Tech** (the NTC+NTB persona)
2. Grant consent → view Health Card
3. Check the **Obligation & Leverage** dimension — it should say something like *"No existing EMI obligations detected"*
4. Despite zero credit history, the card should show **Band A, APPROVE**
5. ✅ If a credit-invisible MSME gets scored and approved → NTC handling verified

### 2.3 NTB (New-to-Bank) handling
1. Same **NewGen Tech** persona — on the data-pack level, the AA bank data should come from a **different bank** (e.g., HDFC Bank, not IDBI Bank)
2. On the **Portfolio** page (`/portfolio`), filter by **NTC/NTB** tab — the entry should have an **NTB badge**
3. Also try **Meera Handicrafts** — she is NTB (banks elsewhere, data via AA)
4. ✅ If NTB badge appears and the MSME is still scored → NTB handling verified

### 2.4 Reduces rejection rates for viable borrowers
1. Go to the **Portfolio** page (`/portfolio`)
2. Look at the **"Financial inclusion"** KPI card — it shows **NTC/NTB approved count** (e.g., "12 NTC/NTB approved")
3. Click the **NTC/NTB** filter tab — you should see multiple NTC/NTB MSMEs with **"Approve"** recommendation
4. ✅ If NTC/NTB firms are approved despite no bureau history → reduced rejection verified

### 2.5 Identifies creditworthy MSMEs traditional scoring would miss
1. Same as above — **NewGen Tech** (NTC+NTB) gets Band A, APPROVE
2. A traditional bank would **reject** this firm (no bureau record, no relationship)
3. ✅ This is verified by the NewGen Tech approval itself

---

## 3. Multidimensional Financial Health Score

### 3.1 Composite financial health score
1. On any Health Card, look at the **top header area** — you should see a large score (0–1000) and a **risk band** (A/B/C/D)
2. The score dial (circular SVG gauge) should show the composite number
3. ✅ If you see the composite score + band → verified

### 3.2 Multidimensional coverage
1. On the Health Card, find the **"Dimension breakdown"** section
2. A **radar chart** should show 6 axes:
   - Revenue Health
   - Cash-Flow Strength
   - Digital Transaction Vitality
   - Compliance Discipline
   - Employment Stability
   - Obligation & Leverage
3. ✅ If radar chart shows all 6 labeled dimensions → verified

### 3.3 Each dimension individually scored and explainable
1. Scroll down to the section **"Why each dimension scored what it did"**
2. You should see **6 cards**, each showing:
   - Dimension name + score (e.g., "Revenue Health: 92/100")
   - Trend indicator (IMPROVING / STABLE / DECLINING)
   - List of **named factors** with signed contributions (e.g., "+30 Turnover scale", "-10 High volatility")
3. Click/expand each card — every factor should have a human-readable **detail** string
4. ✅ If all 6 dimension cards render with factors → verified

### 3.4 Transparent and interpretable methodology
1. Check the dimension cards — scores are **base 50 + factor contributions** (transparent math)
2. Check the **ML panel** — it shows drivers/supports with actual feature values
3. Check the **"agrees / disagrees"** chip comparing ML vs. rulebook
4. ✅ If you can trace how the score was calculated from factors → verified

### 3.5 Sector benchmarking (peer percentiles)
1. On any Health Card, check the **dimension cards**
2. Each card should show a **peer percentile** label like "Top 25% of Manufacturing MSMEs" or "Behind the sector median — Xth percentile"
3. The percentile badge uses color coding: green (top 25%), neutral (25–75%), red (bottom 25%)
4. ✅ If dimension cards show peer percentile labels → verified

### 3.6 Score history / trend chart
1. On the Health Card, look for the **"Composite score, last X months"** section
2. A **line+area chart** should show the score trend with:
   - Band reference lines (A/B/C thresholds as dashed lines)
   - Start→End score delta (e.g., "680 → 752 (+72)")
   - Hover tooltip showing period + composite + band
3. ✅ If the score history chart renders with multiple data points → verified

---

## 4. Visualization of Strengths & Risks

### 4.1 Visual Financial Health Card
1. After granting consent for any MSME, you land on the **Health Card page**
2. Verify it contains: score dial, radar chart, dimension cards, decision panel, ML panel, data freshness footer
3. ✅ If the full card renders with all sections → verified

### 4.2 Strengths highlighted
1. On the Health Card, find the **"Top strengths"** section (green/positive items)
2. You should see up to 3 items, e.g.:
   - "Turnover scale — Avg ₹35.4L/mo — established scale"
   - "GST filing timeliness — 96% of returns filed on time"
3. ✅ If strengths section shows labelled items → verified

### 4.3 Risks highlighted
1. Find the **"Top risks"** section (red/negative items)
2. For Sharma Textiles you might see: "Digital adoption trend — UPI receipts flat/declining"
3. For Kumar Enterprises (distressed) you'll see 3 clear risks
4. ✅ If risks section shows labelled items → verified

### 4.4 Dashboard intuitive for credit officer
1. Toggle the **"Credit officer view / Borrower view"** button (top-right of the Health Card)
2. In **credit officer view**: decision panel (APPROVE/REFER/DECLINE + limit + tenor + ROI), ML panel, factor detail
3. In **borrower view**: plain-language summary ("What this means for your business"), improvement tips
4. Go to **`/portfolio`** — verify you see KPI cards, band/sector/recommendation charts, sortable table, NTC/NTB filter, re-score button
5. ✅ If both views work + portfolio dashboard is usable → verified

### 4.5 Cash-flow based limit workings
1. On the Health Card (credit officer view), look at the **Decision Panel**
2. Below the limit amount, there should be a **"Limit derivation"** section showing step-by-step math:
   - Monthly surplus → multiplier → cap → final limit
   - Each step shows label + amount + detail text
3. ✅ If limit derivation steps are visible in the decision panel → verified

### 4.6 Actionable improvement recommendations
1. On the Health Card, switch to **Borrower view**
2. Look for the **"Improve your score"** section
3. Each recommendation should show:
   - Dimension badge (colored pill, e.g., "Revenue", "Compliance")
   - Action text (e.g., "File your next 3 GST returns on time")
   - Estimated uplift ("+X pts")
   - Time horizon ("Effect visible in ~Y months")
4. ✅ If ranked recommendations with uplift estimates appear → verified

### 4.7 PDF / print export
1. On the Health Card, look for a **"Print"** or **"↓"** button (top-right area)
2. Click it — the browser print dialog should open
3. The `@media print` CSS should clean up the output (hide nav, full-width)
4. ✅ If print dialog opens with clean layout → verified

---

## 5. Ecosystem Integration

### 5.1 ULI integration (simulated)
1. Navigate to the **ULI/OCEN** page (should be in the top nav or at **`/ecosystem`**)
2. Select an MSME and trigger a **ULI pull**
3. A **trace timeline** should appear showing 8 steps:
   - LSP → POST /uli/pull (8ms)
   - ULI → Consent artefact lookup (42ms)
   - ULI → Route to source rails (15ms)
   - FIP → GSTN pull (180ms)
   - AA → Bank statement pull (320ms)
   - FIP → EPFO fetch (90ms)
   - BANK → Compute health card (45ms)
   - LSP → 200 OK health card returned (6ms)
4. Total latency should be ~700ms. Each step shows actor, action, detail, and latency.
5. ✅ If timeline renders with 8 steps and a health card result → ULI integration verified

### 5.2 OCEN integration (simulated)
1. On the same **Ecosystem** page, trigger an **OCEN loan request**
2. A trace timeline should appear showing 5 steps:
   - LSP → POST /ocen/loan-request
   - OCEN → Validate LSP + rate contract
   - BANK → Underwrite against health card
   - BANK → Emit SANCTIONED/REFERRED/REJECTED
   - LSP → Deliver terms to borrower
3. The result should show decision, sanctioned amount, tenor, ROI
4. ✅ If OCEN timeline renders with decision + terms → OCEN integration verified

### 5.3 AA (Account Aggregator) framework
1. On the **Consent page**, verify the flow:
   - Sources listed with checkboxes (GST, AA, EPFO, UPI)
   - Click **"Grant consent & fetch data"**
   - Watch stages: "Requesting consent…" → "Consent granted ✓" → "Pulling data…" → sources turn green one-by-one → "Opening health card…"
2. Note the text at the bottom: **"Consent handle expires in 30 days. Revocable at any time."**
3. Verify in the API docs (`http://localhost:8000/docs`):
   - `POST /api/consent` — issues a handle
   - `POST /api/consent/{id}/revoke` — revokes it
   - Data endpoints return **403** with a revoked handle
4. ✅ If consent flow works end-to-end with handle validation → AA integration verified

### 5.4 Standards-compliant data exchange
1. Check the consent page — it's consent-based, not scraping
2. Check `http://localhost:8000/docs` — RESTful API with Pydantic schemas
3. The borrower view on the Health Card says: *"Score built only from data you consented to share"*
4. ✅ If consent-based + API-driven → verified

---

## 6. Near Real-Time Credit Assessment

### 6.1 Near real-time scoring
1. Pick any MSME → grant consent → observe how fast the Health Card loads
2. It should appear in **< 2 seconds** (no batch job, no waiting)
3. ✅ If the card renders near-instantly → verified

### 6.2 Process new MSME application quickly
1. Try a different MSME (e.g., switch from Sharma Textiles to Kirana Bazaar)
2. Consent → Health Card should load fast again
3. ✅ If new MSME scores quickly → verified

### 6.3 Live/streaming data refresh
- **PARTIAL** — the portfolio has a **"↻ Re-score book"** button on `/portfolio`
- Click it — it should re-score all 30 MSMEs and refresh the page
- However: same GSTIN on the same day = same mock data (deterministic)
- ✅ Verify the re-score button works; note the limitation in your presentation

---

## 7. Financial Inclusion Impact

### 7.1 Expands onboarding of credit-invisible MSMEs
1. Go to **`/portfolio`**
2. Look at the **"Financial inclusion"** KPI card — shows count like **"12 NTC/NTB approved"**
3. Click the **NTC/NTB** filter tab — see the list of approved credit-invisible firms
4. ✅ If the KPI shows a positive number + filtered list appears → verified

### 7.2 Portfolio diversification
1. On the **Portfolio** page, check the **3 distribution panels**:
   - **Risk band mix** — should show A/B/C/D distribution (not all in one band)
   - **Recommendation mix** — should show Approve/Refer/Decline split
   - **Sector mix** — should show multiple sectors (Manufacturing, Retail, Services, Wholesale)
2. ✅ If distributions show variety across bands, sectors, and decisions → verified

### 7.3 Portfolio quality
1. Check the **"Avg PD (ML)"** KPI card — should show the portfolio-level PD
2. Check the **"Watch-list"** filter — flags REFER + DECLINE + high-PD entries
3. Watchlist entries show reasons (e.g., "ML PD 65%", "Rulebook declines")
4. ✅ If watchlist + avg PD KPIs are visible → verified

### 7.4 Before/After Impact Dashboard
1. Navigate to the **Impact** page (should be in the top nav or at **`/impact`**)
2. Verify you see **4 comparison KPI cards**:
   - **Approval coverage** — Traditional vs Alternate (e.g., "33% → 87%, +4 MSMEs served")
   - **NTC/NTB firms onboarded** — Traditional "0" vs Alternate showing count
   - **Portfolio exposure** — Traditional vs Alternate with unlocked amount
   - **Portfolio PD** — Honest trade-off showing the higher PD from including riskier NTC borrowers
3. Below the KPIs, a **"Rescued MSMEs"** table should show firms that traditional banks would reject but the alternate-data system approves/refers:
   - Columns: MSME name, sector, turnover, NTC/NTB badges, traditional verdict (REJECT + reason), alternate verdict (APPROVE/REFER), alternate limit, PD
4. ✅ If impact dashboard shows before/after comparison with rescued-row table → verified

---

## 8. Cross-Cutting / Implicit Outcomes

### 8.1 Data privacy and consent mechanisms
1. The entire flow starts with an **explicit consent step** (Consent page)
2. The consent handle has a **30-day expiry**
3. Grants are **revocable** (`POST /api/consent/{id}/revoke`)
4. Borrower view states: *"Score built only from data you consented to share. You can revoke consent at any time."*
5. ✅ If consent is enforced + revocable → verified

### 8.2 Scalable to large MSME volumes
1. The portfolio already scores **30 MSMEs** at startup
2. The architecture is **stateless API + connector protocols** — swapping mock for real is adapter work
3. ✅ Verified by architecture; for demo, the 30-MSME portfolio is sufficient

### 8.3 Handles incomplete/noisy data gracefully
1. Pick **Kirana Bazaar** (micro retailer) — EPFO should say **"not covered"** (below EPFO threshold)
2. The Employment dimension should still score (shows "EPFO not applicable — small workforce or informal")
3. All other dimensions still compute despite missing EPFO signal
4. ✅ If a partial-data MSME still gets a full card → verified

### 8.4 Audit trail / explainability for regulatory compliance
1. On the Health Card, verify:
   - Every dimension has **named factors with detail strings** (traceable reasoning)
   - ML panel shows **model version hash** and **holdout AUC** (model governance)
   - **"Agrees / Disagrees with rulebook"** chip (champion/challenger auditing)
   - **Drivers and supports** with actual feature values (local explainability)
2. ✅ If all of the above are visible on the card → verified

### 8.5 Consent audit log
1. Navigate to the **Consent log** page (in the top nav or at **`/consent-log`**)
2. The page should show a **compliance table** with columns:
   - Handle (consent ID, truncated)
   - MSME (trade name + GSTIN)
   - Sources (pill badges for GST, AA, EPFO, UPI)
   - Granted (date/time)
   - Expires (date)
   - Status (GRANTED / REVOKED / EXPIRED)
3. Click the **"↻ Refresh"** button — the table should re-fetch
4. If you previously granted consent to multiple MSMEs, multiple rows should appear
5. ✅ If the consent log table renders with artefact details → verified

---

## 9. End-to-End Loan Journey (NEW)

### 9.1 Apply for credit
1. On any Health Card (credit officer view), find the **"Apply for credit →"** button in the Decision Panel
2. Click it — the application should be submitted to `POST /api/msme/{gstin}/apply`
3. If the recommendation is **APPROVE**: a **WhatsApp toast** should pop up saying "Sanction issued 🎉" and you should navigate to the **Sanction Letter** page
4. If the recommendation is **REFER**: toast says "Sent to underwriter" and you navigate to the application page
5. If **DECLINE**: toast says "Application declined" in red
6. ✅ If the apply button works and toast fires → verified

### 9.2 Sanction letter
1. After a successful application (SANCTIONED), you land on the **Sanction Letter** page
2. Verify the letter contains:
   - Reference number and date
   - Enterprise name, GSTIN
   - Sanctioned amount, tenor, ROI
   - **Monthly EMI** (calculated with standard EMI formula)
   - **Processing fee** (0.5% of sanctioned amount)
   - **5 covenants** (e.g., "Route 60% of GST turnover through the bank")
   - **Validity** (30 days)
3. There should be a **"Print / Download"** button — click it to verify `window.print()` opens the print dialog
4. ✅ If the sanction letter renders with complete terms + EMI + covenants → verified

### 9.3 WhatsApp notification simulation
1. Trigger any application via the "Apply for credit" button
2. Watch the **bottom-right corner** — a WhatsApp-branded toast should slide in:
   - Green WhatsApp icon
   - "IDBI Bank via WhatsApp" header
   - Tone-appropriate message (green for sanction, amber for referral, red for decline)
3. The toast should **auto-dismiss after 6 seconds**
4. ✅ If the toast appears with WhatsApp branding and auto-dismisses → verified

### 9.4 Multi-language support (Hindi/English)
1. Look for a **language toggle** in the navigation (EN / HI or similar)
2. Switch to **Hindi** — key labels should change:
   - "Portfolio" → "पोर्टफोलियो"
   - "Grant consent & fetch data" → "सहमति दें और डेटा प्राप्त करें"
   - "Credit officer view" → "क्रेडिट ऑफिसर दृश्य"
   - "Apply for credit →" → "क्रेडिट के लिए आवेदन करें →"
3. Switch back to **English** — labels should revert
4. Refresh the page — the language preference should be **persisted** (stored in localStorage)
5. ✅ If Hindi/English toggle works and persists → verified

---

## Quick Walkthrough Checklist (TL;DR)

| # | What to do | What to see | ✅ |
|---|---|---|---|
| 1 | Pick Sharma Textiles → Consent → Health Card | 24 GST returns, 210 AA txns, 12 EPFO months, 12 UPI months, full card | ☐ |
| 2 | Check ML panel on Health Card | PD, AUC, drivers/supports, agrees chip | ☐ |
| 3 | Pick NewGen Tech → same flow | Band A APPROVE despite NTC+NTB | ☐ |
| 4 | Check radar chart on any card | 6 dimensions visible | ☐ |
| 5 | Check dimension cards | Factors with contributions + detail text + peer percentile | ☐ |
| 6 | Check strengths/risks section | Top-3 strengths + top-3 risks listed | ☐ |
| 7 | Toggle officer ↔ borrower view | Different panels appear; borrower has recommendations | ☐ |
| 8 | Check limit workings in decision panel | Step-by-step limit derivation math | ☐ |
| 9 | Check score history chart | Line chart with band reference lines + trend delta | ☐ |
| 10 | Go to /portfolio | 30 MSMEs, KPIs, band/sector/rec charts | ☐ |
| 11 | Click NTC/NTB filter | NTC/NTB entries with badges | ☐ |
| 12 | Click watchlist filter | Flagged entries with reasons | ☐ |
| 13 | Click "Re-score book" | Portfolio refreshes | ☐ |
| 14 | Go to /impact | Before/after comparison, rescued MSMEs table | ☐ |
| 15 | Go to /ecosystem | ULI pull timeline (8 steps) + OCEN loan flow (5 steps) | ☐ |
| 16 | Click "Apply for credit" on a Health Card | WhatsApp toast, navigate to sanction letter | ☐ |
| 17 | Check sanction letter page | Amount, EMI, covenants, print button | ☐ |
| 18 | Go to /consent-log | Consent artefacts table with status | ☐ |
| 19 | Toggle language EN ↔ HI | Key labels switch to Hindi and back | ☐ |
| 20 | Click print on Health Card | Browser print dialog opens, clean layout | ☐ |
| 21 | Pick Kumar Enterprises | Band D, DECLINE, PD 99%, hard-gate risks | ☐ |
| 22 | Pick Kirana Bazaar | EPFO "not covered", still scores all 6 dims | ☐ |
