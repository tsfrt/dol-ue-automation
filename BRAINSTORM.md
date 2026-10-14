# UI Fraud & Improper Payment Detection — Demo Brainstorm

> **Goal:** A Databricks demo that simulates U.S. states ("member states") submitting unemployment insurance (UI) claims, then detects fraud and improper payments end to end. It uses **Databricks Apps, real-time streaming, Lakebase, DBSQL, Model Serving, and agent automation**.
>
> **Status:** Brainstorm / pre-design. Every number below comes from public DOL and Treasury sources (see [Sources](#12-sources)).

### Decisions log

| Date | Decision | Notes |
|---|---|---|
| 2026-10-09 | **Ingest = Zerobus Ingest** | States push events directly into Unity Catalog Delta tables. No Kafka or Event Hubs to run. See [§8.1](#81-ingest-with-zerobus). |
| 2026-10-09 | **Scope = 10 simulated states** | CA, WA, TX, IL, OH, FL, GA, NY, NJ, PA. Covers all 6 DOL ETA regions and includes border clusters for cross-state scenarios. See [§7.1](#71-the-10-demo-states). |

---

## 1. TL;DR

- **Improper payments are *measured* when money is paid out, but they are *caused* by the information submitted.** Most of that information comes from the **weekly certification** the claimant files to keep getting paid, not from the initial application.

| Where the overpaid dollars come from (PIIA 2025) | Root causes | Share of overpaid $ |
|---|---|---|
| **Weekly certification** (claimant attests each week) | Work Search 36.6% + Benefit Year Earnings 29.4% + Able & Available 5.1% + ES Registration 2.2% | **≈ 73%** |
| **Initial claim / adjudication** | Separation Issues 15.7% + Base Period Wages 3.0% | **≈ 19%** |
| Other | Other Eligibility (includes false identity) 3.1% + All Other 4.9% | ≈ 8% |

- **Improper ≠ fraud.** Most improper payments are *errors*: the claimant misunderstood the rules, the employer responded late, or the agency processed something incorrectly. Fraud is one subset. Identity theft dominated pandemic headlines but is a **small share** of what DOL's quality-control audit (BAM) measures for regular UI.
- **Recommended demo story: "Stop it before the money leaves."** Each stage of the claim gets its own job:
  - **Prevent** at intake: identity checks and fictitious employers.
  - **Detect** at weekly certification: working while claiming and work search, where most of the dollars are.
  - **Hold** at payment: bank-account and mule checks, plus risk-based payment holds.
  - **Recover** afterwards: establish the overpayment and offset it.
- **Other agencies' data is the strongest lever.** In FY24, about 96% of overpaid dollars fell under "Employment" or "Receiving Benefits from Other Sources." Those are only visible by cross-matching new hires, wages, workers' comp, PFML, pensions, death and prison records, and bank verification. See [§6](#6-cross-agency--third-party-signals).
- **Recommended framing:** a **National UI Integrity Hub**. It is modeled on the real Integrity Data Hub (IDH), which NASWA runs with DOL funding. States stream claim, certification, and payment events to the hub. Each state's investigators work their own cases. DOL sees only national aggregates.

---

## 2. Payment side vs. submission side?

**Short answer: it's mostly a submission problem that shows up as a payment problem.**

### 2.1 Why the improper payment rate looks like a "payment" metric
- DOL's **Benefit Accuracy Measurement (BAM)** program samples **paid weeks** (and denied claims) in every state. Investigators then re-adjudicate each sampled week from scratch, contacting the claimant, employers, and third parties.
- The resulting dollar error rate is reported under the Payment Integrity Information Act (PIIA) and published on paymentaccuracy.gov. So the *rate* is expressed in payment terms.
- BAM also records **the cause**, **the party responsible**, and **the point in the claims process where the error could have been caught**. Those fields show the cause is almost always upstream of the payment.

### 2.2 Who is responsible (FY 2024, paymentaccuracy.gov)

| Category | Amount | What it means |
|---|---|---|
| Overpayments **outside** agency control | **$3,084.41M** | The claimant or employer gave inaccurate or missing information |
| Overpayments **within** agency control | **$935.03M** | The agency had, or could have had, the data ($855.93M was *failure to access* available data) |
| Underpayments | $154.54M | |
| Unknown (insufficient documentation) | $461.7M | |

By OMB eligibility element, FY 2024 overpayments (outside + within agency control combined) break down as:
- **Employment:** $2,508M (about 62%)
- **Receiving Benefits from Other Sources:** $1,372M (about 34%)
- **Identity:** $139M (about 3.5%)

### 2.3 Payment-side signals still matter
They are the **enforcement point**, the last chance to stop the money:
- Bank account or routing number shared across many claimants (mule accounts). IDH's **Bank Account Verification (BAV)** service targets this.
- A direct-deposit or address change followed immediately by a payment (account takeover).
- A prepaid debit card versus direct deposit, and ACH return codes.
- A payment issued after the claimant's date of death or during incarceration.
- The same person paid by two states for the same week.

### 2.4 Implication for the demo
- Model the **full event stream**: claim → employer response → weekly certification → payment → cross-match → overpayment.
- Put most detection logic on **submissions and certifications**. Use the **payment** step to apply a *risk-based hold* before the money is released.
- **Due-process constraint (key talking point):** Social Security Act §303(a)(1) requires states to pay benefits "when due." A state can't just auto-deny a flagged claim. It must hold the payment, send notice, run fact-finding, and issue a determination with appeal rights. So the models need **explainable reason codes**, and the agents should *draft* notices for a human to approve, not decide on their own.

---

## 3. How DOL fits into the claim life cycle

### 3.1 The federal-state partnership
- **Legal basis:**
  - **Social Security Act Titles III** (administrative grants), **IX** (Unemployment Trust Fund) and **XII** (state loans).
  - **FUTA**, the federal payroll tax that funds administration.
- **The 53 jurisdictions** (50 states, DC, Puerto Rico, US Virgin Islands):
  - set their own eligibility rules
  - take claims and adjudicate them
  - pay benefits from state accounts in the Treasury's Unemployment Trust Fund
  - collect state UI taxes from employers
- **DOL's Employment & Training Administration, Office of Unemployment Insurance (ETA/OUI), with 6 regional offices, does *not* take, adjudicate, or pay individual regular UI claims.** Its roles:

| DOL role | What it looks like |
|---|---|
| **Funding** | Administrative grants to states from FUTA revenue. Integrity grants: up to $765M in FY 2023 and $783M of ARPA money in FY 2024. |
| **Conformity & compliance** | Makes sure state law and operations meet federal requirements (e.g., "when due," due process, confidentiality under 20 CFR 603). |
| **Guidance** | Unemployment Insurance Program Letters (UIPLs) and ET Handbooks. |
| **Performance oversight** | UI PERFORMS, Core Measures, State Quality Service Plan (SQSP), Integrity Action Plans. |
| **Quality control (BAM)** | Statistically sampled audits of paid and denied claims in every state. This is the source of the national improper payment rate. |
| **Federal reporting** | **ETA 539**: weekly initial and continued claims (due Thursdays, feeds the weekly jobless-claims release).<br>**ETA 227**: quarterly overpayments detected and recovered.<br>**ETA 9050**: first-payment timeliness.<br>States now transmit these through the new **UIRS** system (2026). |
| **Integrity infrastructure** | Funds NASWA's **UI Integrity Center** and **Integrity Data Hub (IDH)**:<br>- Suspicious Actor Repository (SAR)<br>- Multi-State Cross-Match (MSCM)<br>- Identity Verification (IDV)<br>- Bank Account Verification (BAV)<br>- Employer Data Module (EDM)<br>Also funds **NIDVO** (Login.gov plus in-person identity checks at USPS), **SIDES** (employer separation info), and Tiger Teams. |
| **Federal programs** | **UCFE** (federal employees) and **UCX** (ex-military): states act as agents and the federal government reimburses them. **Extended Benefits**: shared cost. Pandemic programs PUA, PEUC and FPUC were federally funded. |
| **Enforcement** | DOL's Office of Inspector General (OIG) investigates and prosecutes fraud, especially organized and interstate schemes. |

### 3.2 Life-cycle map: stage, actors, DOL touchpoint, risk, data

| # | Stage | What happens | Who | DOL / federal touchpoint | Improper / fraud risk | Data a demo can simulate |
|---|---|---|---|---|---|---|
| 0 | Employer registration & wage reporting | Employer registers with the state and files quarterly wage reports | Employer, state tax unit | IDH Employer Data Module | **Fictitious employer** creating fake wages | `employers`, `wage_records` |
| 1 | Separation | Worker loses their job | Worker, employer | — | — | separation date and reason |
| 2 | **Initial claim** | Claimant files online or by phone: identity, employers, separation reason | Claimant | IDH IDV and SAR, NIDVO | **Identity theft**, bots, synthetic identities | `initial_claims` (IP, device, email, phone, bank, form-fill time) |
| 3 | Identity verification | ID proofing; checks against SSA, DMV and similar sources | State, vendor, Login.gov | NIDVO | Identity fraud | ID-check results |
| 4 | **Monetary determination** | Base-period wages → weekly and maximum benefit amounts | State | — | Base Period Wages (3.0%), fake wages | `wage_records` join |
| 5 | Employer notice & response | Employer confirms wages and separation reason | Employer | **SIDES** | Separation misreported, or employer doesn't respond | `employer_responses` |
| 6 | **Non-monetary adjudication** | Decides separation, able & available, and similar issues; fact-finding | State adjudicator | Timeliness measures | **Separation Issues (15.7%)** | determination records |
| 7 | Waiting week | Unpaid first week (in most states) | — | — | — | — |
| 8 | **Weekly certification** | Claimant reports earnings, work-search contacts, able & available, job refusals | Claimant | ETA 539 counts | **Work Search (36.6%)**, **BYE (29.4%)**, **Able & Available (5.1%)**, ES Registration (2.2%) | `weekly_certifications` |
| 9 | **Payment** | Direct deposit or debit card | State, bank | ETA 9050 timeliness ("when due") | Mule accounts, account takeover | `payments` (bank hash, method, change events) |
| 10 | Ongoing cross-matches | New hires (NDNH/SDNH), quarterly wages, prisoners (SSA PUPS via ICON), deaths, multi-state (IDH MSCM, ICON) | State, IDH | IDH, ICON | Working while claiming, incarcerated or deceased claimants, multi-state claiming | `ext_new_hires`, `ext_incarceration`, `ext_death_records`, `ext_multistate` |
| 11 | **Overpayment** | Establish the overpayment → appeal → recover (benefit offset, Treasury Offset Program, state tax refund intercept) | State, Treasury | **ETA 227** | "Pay and chase": recovery is slow and partial | `overpayments`, `recoveries` |
| 12 | Benefit year end | Claim exhausts or expires; 1099-G tax form issued | State | — | 1099-G sent to an identity-theft victim | — |
| 13 | QC & national reporting | BAM sample audit → PIIA rate → paymentaccuracy.gov | State BAM unit, DOL | **BAM, PIIA** | — | `bam_sample` (optional) |

> **Framing caveat:** DOL **does not** receive individual claims in real time. States send aggregate counts (ETA 539, ETA 227) and BAM samples to DOL. States send claim-level data for cross-matching to the **IDH**. A "member states submit claims to a central hub" demo is therefore realistic if it's framed as an **IDH-style integrity hub**, with DOL as a consumer of aggregates and oversight.

---

## 4. Key numbers (verified)

### 4.1 National UI improper payment rates (DOL BAM, PIIA reporting years)

| PIIA year (Jul–Jun) | Outlays | Overpayment rate | Overpaid $ | Underpayment rate | Underpaid $ |
|---|---|---|---|---|---|
| **2025** (Jul 2024–Jun 2025) | $35,983M | **12.65%** | $4,551M | 0.50% | $179M |
| 2024 | $33,753M | 13.97% | $4,715M | 0.45% | $152M |
| 2023 | $26,941M | 14.36% | $3,867M | 0.56% | $151M |
| 2022 | $28,051M | 21.07% | $5,911M | 0.62% | $174M |

### 4.2 Root causes of UI overpayments (share of overpaid dollars)

| Cause | Definition (DOL) | PIIA 2025 | $ (M) | PIIA 2024 | Change |
|---|---|---|---|---|---|
| **Work Search** | Failure to actively seek work | **36.6%** | $1,665.3 | 36.0% | +0.6 |
| **Benefit Year Earnings (BYE)** | Claiming after returning to work; failing to report earnings accurately | **29.4%** | $1,334.3 | 23.8% | **+5.6** |
| **Separation Issues** | Voluntary quit or discharge for cause | **15.7%** | $715.5 | 19.3% | −3.6 |
| Able & Available | Not able to work or not available for work | 5.1% | $231.1 | 6.7% | −1.6 |
| All Other Causes | | 4.9% | $225.2 | 4.6% | +0.3 |
| Other Eligibility | Refusal of work, self-employment, failure to report, citizenship, **false identity** | 3.1% | $138.7 | 2.7% | +0.4 |
| Base Period Wages | Benefit calculation error | 3.0% | $135.2 | 2.9% | +0.1 |
| ES Registration | Failure to register for reemployment services | 2.2% | $101.1 | 3.9% | −1.7 |

> BYE (working while claiming) is the fastest-growing cause, up 5.6 points. It is also the scenario that is **most demonstrable with real-time streaming**: a new-hire record arrives and is joined against active weekly certifications.

### 4.3 paymentaccuracy.gov (program-level, broader scope)
- **Payment accuracy:** FY21 81.1%, FY22 77.8%, FY23 83.5%, FY24 84.1%, **FY25 85.1%** (FY25 outlays $37,679M).
- **Scope:** covers traditional state UI, UCFE, UCX, EB, EUC08, PEUC and FPUC, and counts *unknown* payments. That is likely why it differs from the BAM-only rates above.
- **Reduction target:** FY24 15.0%. Tolerable rate: "not determined."
- **Barriers to prevention it lists:**
  - due-process requirements
  - the need to pay quickly *and* prevent fraud
  - 53 different IT systems
  - fraud that keeps evolving, including identity fraud
  - differing state laws
  - the "when due" requirement
- **IDH adoption (Sept 30, 2023):** all 53 states signed participation agreements. 51 use SAR, 50 use MSCM, 45 use IDV, 40 use BAV.

### 4.4 Useful taxonomy for ground-truth labels
BAM classifies each overpayment by **action code**:
- **10** = Fraud
- **11** = Nonfraud recoverable
- **12** = Nonfraud nonrecoverable

It also records **error cause**, **error responsibility** (claimant, employer, agency, or combinations), and **detection point**. Our synthetic data should use the same label dimensions. The demo can then say "our labels mirror BAM's classification."

---

## 5. Scenario catalog (what to simulate)

Each scenario is injected into synthetic data with a ground-truth label (`is_fraud`, `bam_action_code`, `root_cause`, `responsible_party`) so model precision and recall can be shown.

| # | Scenario | Stage | Root cause | Signals injected into data | Detection approach | Databricks feature |
|---|---|---|---|---|---|---|
| 1 | **Identity-theft / imposter ring** | Initial claim | Identity / Other Eligibility | Many claims sharing a bank account, device ID, IP, phone or address; bursts across 2–3 states; failed or repeated ID checks | Streaming velocity features, graph clustering, ML score | Streaming, Model Serving, GraphFrames |
| 2 | **Synthetic identities / bots** | Initial claim | Identity | Form filled in under 60 seconds, disposable email domains, foreign or VPN IPs, sequential emails | Rules plus ML | Streaming, Model Serving |
| 3 | **Fictitious employer** | Wages / monetary determination | Base Period Wages / fraud | Newly registered employer, wages concentrated in claimants who all file soon after, no tax payments, shared contacts | Graph analysis plus rules | Batch graph, DBSQL |
| 4 | **Working while claiming (BYE)** ⭐ | Weekly certification | **BYE 29.4%** | Claimant certifies $0 earnings while a new-hire record shows a start date, or quarterly wages exist for paid weeks | **Stream-stream join** of new hires against certifications; partial earnings underreported | Real-time streaming, Agent (draft fact-finding) |
| 5 | **Work-search non-compliance** ⭐ | Weekly certification | **Work Search 36.6%** | Contacts that don't exist or can't be verified; the same contact list reused across claimants; the same employer every week; impossible counts | LLM work-search verification agent; rules for duplicates | Agents, `ai_query` |
| 6 | **Separation misreporting** | Adjudication | **Separation 15.7%** | Claimant says "laid off for lack of work"; employer SIDES response says "quit" or "discharged for attendance" | LLM compares the two narratives and flags the conflict for an adjudicator | Agents, Model Serving (LLM) |
| 7 | **Multi-state concurrent claims** | Weekly certification / payment | Fraud | Same SSN or bank account with paid weeks in two states for the same week | Cross-state join at the hub (like MSCM) | Streaming, UC cross-state view |
| 8 | **Incarcerated claimant** | Weekly certification | Able & Available | Certifications filed during a jail-roster date range | Cross-match | Streaming join |
| 9 | **Deceased claimant** | Payment | Identity / fraud | Payments after date of death; recent bank change | Cross-match plus payment hold | Streaming, Lakebase hold queue |
| 10 | **Able & available violation** | Weekly certification | Able & Available 5.1% | Certifying from an out-of-country IP; certifying while in school | Rules plus ML | Streaming |
| 11 | **Account takeover** | Payment | Fraud | Password, email or bank change followed by a payment within 24 hours from a new device | Sequence features | Streaming, Model Serving |
| 12 | **Honest errors (noise)** | Any | BYE, Work Search, etc. | Small earnings underreports, late employer responses, agency miscalculations | Must *not* be routed as fraud. Route to education or a correction instead | Shows precision and fairness |

⭐ = biggest dollar drivers. Make sure the demo spends real time on these, not just identity theft.

---

## 6. Cross-agency & third-party signals

**Why this matters:** in FY 2024, "Receiving Benefits from Other Sources" accounted for about **$1.37B (about 34%)** of UI overpayments by OMB eligibility element, and "Employment" for about **$2.5B (about 62%)**. Both are fundamentally **data-matching problems.** The claimant's own submission can't reveal them; other agencies' data can.

Paymentaccuracy.gov also attributes **$855.93M** of FY 2024 overpayments to the agency's **"failure to access data"** that already existed. Getting existing data into the decision *before payment* is a big part of the opportunity.

### 6.1 Signal catalog

**Federal sources**

| Source | Owner | How states get it today | Signal | Catches | Freshness |
|---|---|---|---|---|---|
| **National Directory of New Hires (NDNH)**: new-hire (W-4), quarterly wage and UI claim files | HHS / Office of Child Support Services | Federal Parent Locator Service. DOL requires it for BAM (since 2007) and Benefit Payment Control (since 2011) | New job start date; wages from multi-state or federal employers; UI claims filed in other states | **BYE / working while claiming**, multi-state claims | New hires within days; wages quarterly |
| **State Directory of New Hires (SDNH)** | State child-support agency | Intrastate feed | Same as NDNH but faster for in-state employers | **BYE** | Daily / weekly |
| **SSA SSN verification** | SSA | Through ICON | Whether the SSN, name and date of birth match | Identity theft, synthetic identity | Real time / batch |
| **SSA Prisoner Update Processing System (PUPS)** | SSA (fed from federal, state and local facilities) | Through ICON | Incarceration dates | Incarcerated claimants (able & available) | Periodic |
| **Death data**: SSA full death file, Treasury **Do Not Pay** | SSA / Treasury Fiscal Service | **Through IDH** (DNP death matches available to about 52 jurisdictions by July 2024) | Date of death | Deceased-identity claims, payments after death | Weekly to daily |
| **Treasury Do Not Pay: Account Verification Service (AVS)** | Treasury Fiscal Service | Through IDH and DNP | Is the bank account open? Does the owner match the claimant? | **Mule accounts**, account takeover, stolen identity paid to a third party | Real time |
| **Treasury Offset Program (TOP)** | Treasury Fiscal Service | State enrollment | *Recovery* (offsets federal tax refunds), not detection | Unrecovered overpayments | Annual cycle |
| **DHS USCIS SAVE** | DHS | Required by SSA §1137 for non-citizen claimants | Work-authorization status | Ineligible non-citizen claims, fake documents | Real time |
| **Federal employing agencies / DoD DMDC** | OPM, federal agencies, DoD | UCFE / UCX claim process | Federal wages and separation reason; active-duty status | False UCFE / UCX claims, claiming while on active duty | Per claim |
| **Login.gov / USPS in-person proofing (NIDVO)** | GSA / USPS (DOL-funded) | DOL NIDVO offering | Verified identity, or failure to verify | Identity theft | Real time |

**Integrity hub and other states**

| Source | Owner | How states get it today | Signal | Catches | Freshness |
|---|---|---|---|---|---|
| **IDH services**: SAR, MSCM, IDV, BAV, foreign IP, suspicious email domains, EDM | NASWA (DOL-funded) | Participation agreement (all 53 jurisdictions) | Known-bad identifiers; same SSN in other states; bank and IP reputation; fictitious-employer indicators | Rings, multi-state, mules, fictitious employers | Near real time |
| **ICON / Interstate Benefits** | NASWA / states | Interstate network | Wage transfers between states; overlapping claims | Multi-state claiming | Daily |

**Sister agencies in the same state**

| Source | Owner | How states get it today | Signal | Catches | Freshness |
|---|---|---|---|---|---|
| **State workers' compensation** | State WC board / insurers | Data-sharing agreement | Temporary total disability benefits for the same weeks | **Benefits from other sources**, not able to work | Weekly / monthly |
| **State paid family & medical leave (PFML)** / disability insurance | State agency | Same state, often the same department | Concurrent leave benefits | **Benefits from other sources** | Weekly |
| **State tax / revenue department** | State revenue | Data-sharing agreement | Income tax withholding, business registration, self-employment income | Fictitious employers, unreported self-employment (BYE) | Quarterly / annual |
| **Secretary of State business registry** | State | Public / API | Does the employer exist? Formation date; registered agent; officers | **Fictitious employer**, fake work-search contacts | Daily |
| **DMV (and AAMVA's license-verification service)** | State DMV / AAMVA | Agreement | Driver's license validity, photo, address | Identity theft, synthetic identity | Real time |
| **Vital records** (state or other states via NAPHSIS EVVE fact-of-death) | State health / NAPHSIS | Agreement | Death records, often faster than SSA | Deceased identities | Daily |
| **State Department of Corrections and county jails** | State / county | Agreement or commercial jail-booking feeds | Booking and release dates (faster than PUPS) | Incarcerated claimants | Near real time |
| **SNAP / TANF / Medicaid** | State human services | Agreement (privacy-gated) | Address, phone, bank and household overlaps; earned income reported to other programs | Rings sharing addresses or banks; unreported earnings | Monthly |
| **State retirement systems** | State | Agreement | Pension start dates and amounts | **Benefits from other sources** (pension offset) | Monthly |

**Financial system, commercial data and feedback signals**

| Source | Owner | How states get it today | Signal | Catches | Freshness |
|---|---|---|---|---|---|
| **Banks / Nacha**: ACH returns (R03, R17 questionable, R23 refused) and the **Nacha Unemployment Benefits Return Opt-In Program** | Financial institutions | ACH returns to the state's paying bank | The bank flags or returns UI deposits it suspects | Mules, identity theft (a **high-quality label**) | Days |
| **FinCEN UI-fraud red flags** (Advisory FIN-2020-A007) | FinCEN | Public advisory. SAR data itself goes mainly to law enforcement and OIG | Patterns to *mirror as features*: many UI deposits to one account, payments from multiple states, rapid cash-out, account name mismatch | Mules, rings | — |
| **Commercial identity and risk data**: document + selfie ID, device fingerprint, IP / VPN reputation, email age, phone line type, SIM swap, credit-header identity age | Vendors | Procurement (many states already use some of these) | Identity risk, device reuse, bot behavior | Identity theft, bots, account takeover | Real time |
| **Commercial employment verification** (e.g., The Work Number) | Equifax | Contract | Current employment and pay | BYE, faster than quarterly wages | Real time |
| **USPS address services**: standardization, commercial mail drops, vacancy, change of address | USPS | Licensed data | Mail-drop or vacant addresses; many claimants at one address | Rings, fictitious employers | Monthly |
| **Employer SIDES responses** | Employers | SIDES | *"Claimant is still employed"* or *"never worked here"* | **Identity theft** (often the first tip-off), BYE | Days |
| **Victim and feedback signals**: 1099-G disputes, identity-theft reports, OIG / National UI Fraud Task Force referrals | Claimants, law enforcement | State intake | Confirmed identity theft or fraud | **Ground-truth labels** for model retraining | Ongoing |

### 6.2 Picks for the demo (simulated feeds)

Not every source is needed. These **8 synthetic feeds** cover the biggest dollar drivers and make good live-demo moments:

1. **New-hire feed (NDNH/SDNH-like):** the real-time BYE story. Joined by stream against active certifications.
2. **Quarterly wage file:** a batch catch-up for BYE, and fictitious-employer analysis.
3. **Other-benefits feed (workers' comp + PFML + pension):** the "benefits from other sources" story (about 34% of FY24 overpaid dollars, and rarely demoed).
4. **Death and incarceration feeds:** simple, unambiguous cross-match hits.
5. **IDH-style hub signals:** suspicious-actor list, cross-state SSN and bank overlap, IP and email reputation.
6. **Bank Account Verification response:** account owner mismatch → hold the payment.
7. **ACH returns / bank opt-in returns:** a feedback loop that produces labels.
8. **Business registry lookup:** used by the work-search and fictitious-employer agents (the LLM agent calls it as a UC function tool).

### 6.3 Databricks angle on inter-agency data
- **Delta Sharing / Databricks Clean Rooms:**
  - Agencies such as state UI, revenue, workers' comp and human services can match records **without copying raw PII** to each other.
  - Example: match on hashed or tokenized SSNs inside a clean room and return only the "hit" flag and dates.
  - This mirrors how DNP returns *match results* rather than raw files.
- **Lakehouse Federation:** query an agency's existing database in place (e.g., a jail roster in Postgres or SQL Server) during an investigation.
- **Unity Catalog:**
  - Tag each source with its **data-use agreement** and allowed purpose.
  - Apply column masks and row filters.
  - Audit every access (required under 20 CFR 603 and computer-matching agreements).
- **Entity resolution:** match claimant identities across feeds with noisy names and addresses. Good use of streaming plus an ML or LLM matching step.

---

## 7. Demo framing options

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. National UI Integrity Hub** ✅ *recommended* | 10 simulated states (see §7.1) stream claim, certification and payment events to a shared hub (IDH-inspired). The hub returns real-time risk scores and cross-state signals. State investigators work their own cases. DOL OUI sees national aggregates. | Matches the "member states submitting" idea. Shows cross-state fraud (rings, multi-state). Mirrors the real IDH plus DOL-oversight model. Natural fit for UC row-level security. | More moving parts |
| B. Single State Workforce Agency | One state's full claim system | Simpler; deep on one workflow | Loses the cross-state story and the DOL angle |
| C. DOL oversight only | Aggregated reporting (ETA 539, ETA 227, BAM) | Easy | Too thin for streaming, Lakebase or agents |

**Personas:**
1. **Claimant:** files a claim or weekly certification in the State Claimant Portal.
2. **State fraud investigator or adjudicator:** works the case queue.
3. **DOL OUI program analyst:** watches the national view and asks Genie questions.
4. **Executive:** cares about "dollars prevented."

### 7.1 The 10 demo states

| DOL ETA region | States | Why they're in the demo |
|---|---|---|
| Region 1 – Boston | **NY, NJ** | NY–NJ–PA commuter belt: realistic **legitimate** interstate claims (worked in one state, live in another) mixed with **multi-state fraud**. Tests whether the model can tell them apart. |
| Region 2 – Philadelphia | **PA** | Completes the NY–NJ–PA cluster; borders OH. |
| Region 3 – Atlanta | **FL, GA** | Border pair for a second cross-state ring scenario; large claim volumes. |
| Region 4 – Dallas | **TX** | One of the largest UI programs; large employer base for fictitious-employer scenarios. |
| Region 5 – Chicago | **IL, OH** | Manufacturing layoff patterns (seasonal and mass layoffs); OH borders PA. |
| Region 6 – San Francisco | **CA, WA** | CA is the largest UI program in the country; WA adds PFML (paid family leave) for the "benefits from other sources" cross-match. |

**Design notes:**
- **Every DOL regional office has at least one state.** The DOL Command Center can filter by ETA region, which is how OUI regional staff actually look at states.
- **State rules vary** and drive the per-state behavior in the generator: max weekly benefit, waiting week, required work-search contacts, PFML availability. Values should come from DOL's annual *Comparison of State Unemployment Insurance Laws*, stored in the `states` reference table, so the agents and rules can reason about each state's requirements.
- **Two border clusters** (NY–NJ–PA–OH and FL–GA) give natural multi-state ring and overlapping-claim scenarios.
- **Unity Catalog row filters per state:** a "PA investigator" sees only PA cases, while hub analysts see all 10. Good live governance moment.
- **Easy to extend:** adding a state is a config row plus a producer instance, nothing more.

---

## 8. Databricks architecture mapping

```
 State systems (simulated, 10)            National UI Integrity Hub (Databricks)                     Consumers
 ─────────────────────────────           ───────────────────────────────────────────                 ─────────
 Claimant Portal (App) ──┐                ┌─ Bronze: raw events (claims, certs, payments,       ┌─ Investigator Workbench (App)
 State producers ×10 ────┼─► Zerobus   ───┤          employer responses, external feeds)        │     ▲   Lakebase case mgmt
 External feeds ─────────┘   Ingest       ├─ Silver: cleaned, entity-resolved, PII-masked     ──┤     │
 (new hire, death, jail)                  ├─ Gold: streaming features (velocity, overlaps,      ├─ DOL Command Center (App + AI/BI + Genie)
                                          │        new-hire hits), risk scores, cases           │
                                          ├─ Model Serving: fraud model + LLM endpoint          └─ Simulator Control Panel (App)
                                          ├─ Agents: triage, work-search, separation, policy
                                          └─ Lakebase: payment holds, cases, online features ◄─► synced tables
```

| Capability | Role in the demo |
|---|---|
| **Synthetic data generator** (Python, Faker / `dbldatagen`) | Builds the 10 states, employers, wage records, claimants, claims, certifications, payments and external feeds. Fraud injection is tunable, with ground-truth labels. Can optionally be seeded from public ETA 539 weekly claims and BAM state rates so volumes and state mix look realistic (scaled down). |
| **Real-time streaming** (Zerobus Ingest → Lakeflow Declarative Pipelines / Structured Streaming real-time mode) | Medallion layers (bronze → silver → gold). Windowed **velocity features** (claims per bank account, device or IP over 1h / 24h / 7d). **Stream-stream join** of new hires against active certifications (BYE). Multi-state overlap detection. Payment-hold decisions in seconds. |
| **Lakebase** (managed Postgres) | Operational store for the apps: claim and certification status, **payment-hold queue**, **investigator case management** (assignment, notes, disposition, notices). **Synced tables** Delta → Lakebase serve low-latency risk scores and online features. Dispositions flow back to the lakehouse as **new training labels** (closed loop). |
| **Model Serving** | **Fraud risk model** (LightGBM or XGBoost, MLflow, registered in UC) with SHAP **reason codes** for due process. Online feature lookup backed by Lakebase. Batch **graph ring detection** (GraphFrames connected components or community scores) feeding the model. **LLM endpoint** (Foundation Model APIs) for agents and `ai_query`. |
| **Agent automation** (Mosaic AI Agent Framework / Agent Bricks, MLflow tracing and evaluation) | **Triage agent:** uses UC function tools (cross-match hits, linked entities, certification history, payment history) to write a case summary, recommend an action and **draft the fact-finding notice**. A human approves.<br>**Work-search verification agent:** are these employer contacts real and plausible?<br>**Separation agent:** compares the claimant's narrative with the employer's SIDES response.<br>**Policy Q&A agent:** retrieval over UIPLs and a sample state claimant handbook.<br>Agents are triggered by Lakeflow Jobs when a high-risk case opens. |
| **DBSQL** (AI/BI dashboards, Genie, `ai_query`) | **National dashboard:** estimated improper payments by root cause and state; ETA 539-style weekly claims; ETA 227-style overpayments established and recovered; **"$ prevented before payment" vs "pay and chase."**<br>**Genie space:** "Which states saw BYE flags rise this month?"<br>`ai_query` for batch classification of narratives. |
| **Databricks Apps** | 1. **State Claimant Portal:** file an initial claim or weekly certification and see the real-time outcome (e.g., "Additional identity verification required").<br>2. **Investigator Workbench:** case queue from Lakebase, entity-link graph, agent summary, approve / hold / release / refer.<br>3. **DOL National Command Center:** embedded AI/BI dashboard plus Genie.<br>4. **Simulator Control Panel:** "Launch an identity-ring attack on states X and Y" or "Spike BYE in state Z." |
| **Unity Catalog governance** | Strong talking point because of UI confidentiality (20 CFR 603):<br>- SSN and bank **column masks**<br>- **row filters by state** (investigators see only their state; DOL sees aggregates and de-identified data)<br>- lineage, audit logs<br>- Delta Sharing / Clean Rooms between states and the hub |

### 8.1 Ingest with Zerobus

**What it is:** Zerobus Ingest (part of Lakeflow Connect) is serverless, push-based ingestion that writes **directly into Unity Catalog managed Delta tables**, with no message bus in between.
- **Interfaces:** gRPC through SDKs (Python, Java, Rust, Go, TypeScript) and a REST API.
- **Formats:** JSON, Protobuf, or Arrow Flight.
- **Per-stream limits:** about 100 MB/s and about 100K records/s.
- **Latency:** about 150 ms to a durable acknowledgment, and about 5 s until rows appear in the table.

**How we use it:**
- **One producer per state.** Each of the 10 simulated states runs its own Python Zerobus SDK client, with gRPC streams per event type:
  - `initial_claims`
  - `employer_responses`
  - `weekly_certifications`
  - `payments`
  - `account_changes`
  
  Every record carries `source_state`. This mirrors the real world, where each state's own system pushes data to a hub like IDH.
- **One service principal per state.** Each state's producer authenticates as its own principal, with write-only access to bronze tables. Unity Catalog audit logs then show exactly which state sent what. That's a strong governance and confidentiality talking point.
- **Protobuf event contracts.** The `.proto` schemas in the repo act as the "state-to-hub interface spec," the same idea as a data-exchange agreement between agencies. Use JSON only for quick prototyping.
- **External feeds also come in through Zerobus:** new hires, hub signals, bank-account verification responses, ACH returns, other-benefits feeds. The quarterly wage file can be a batch load, which is realistic.
- **Claimant Portal (App):** writes single events through the SDK, or REST for simplicity.

**Two paths, so the demo stays honest about latency:**
1. **Decision path (synchronous, under a second).** When the portal submits a claim or certification, it calls the **Model Serving** fraud endpoint directly. Features come from Lakebase, and the response is shown immediately (e.g., "additional identity verification required").
2. **Analytical path (asynchronous, seconds).** The same event lands in bronze through Zerobus within about 5 s. Streaming pipelines then update the velocity and cross-state features, graph clusters, cases and dashboards.

That way the instant claimant decision doesn't depend on table-materialization latency, and features computed by the stream feed back to Lakebase through synced tables.

**Table design:**
- Use **liquid clustering** on bronze tables (e.g., by `source_state` and event date) instead of partitioning. Zerobus limits how many partitions a stream can write to in a short window.
- Keep producers in the **same cloud region** as the workspace.

**Throughput is not a concern.** Even at real-world scale, these 10 states produce well under one stream's capacity.

**Simulator time compression:** the generator should support a configurable clock (e.g., 1 simulated week = 5–10 real minutes) so weekly certification cycles, new-hire arrivals and payments all happen within a live demo.

---

## 9. Demo storyline (about 15 minutes)

1. **"A normal week"** (2 min): claims and certifications stream in from 10 states through Zerobus. The DOL Command Center shows ETA 539-style counts updating live. Most claims are auto-cleared.
2. **"The attack"** (3 min): in the Simulator Control Panel, launch a ring of about 300 claims across **NY, NJ and PA** that share 12 bank accounts and 20 devices. It's hidden among the cluster's normal, legitimate interstate claims.
   - Velocity features spike, the model scores the claims high, and the reason codes are shown.
   - **Payments go into the Lakebase hold queue before release.**
   - The graph view lights up the ring.
3. **"Working while claiming"** (3 min): a new-hire file lands. The stream join flags 40 claimants still certifying $0 earnings. The triage agent drafts BYE fact-finding notices. *"This is 29% of overpaid dollars nationally, and the fastest-growing cause."*
4. **"The investigator"** (4 min): in the Investigator Workbench:
   - Open a case and read the agent's evidence summary and recommended action.
   - Ask a follow-up question.
   - Approve the notice.
   - The disposition is written to Lakebase, synced to the lakehouse, and becomes a new label for retraining.
5. **"The DOL view"** (3 min):
   - Root-cause mix, dollars prevented vs recovered, state comparisons.
   - Ask Genie: *"Which states have the highest work-search overpayment rate?"*
   - Close with: *"Prevent before payment instead of pay and chase."*

---

## 10. Draft synthetic data model

| Table | Key fields | Notes |
|---|---|---|
| `states` | state_code, name, eta_region, wba_max, work_search_required_contacts, waiting_week, has_pfml | 10 demo states (§7.1); rule values from DOL's *Comparison of State UI Laws* |
| `employers` | employer_id, fein, state, naics, registered_date, is_fictitious | Fictitious-employer scenario |
| `wage_records` | employer_id, ssn_hash, year_qtr, wages | Base period; BYE check against quarterly wages |
| `claimants` | claimant_id, ssn_hash, dob, name, address, phone, email, is_synthetic_identity | Mostly real-looking; some stolen or synthetic identities |
| `initial_claims` | claim_id, claimant_id, state, filed_ts, channel, ip, geo, device_id, form_fill_secs, separation_reason, last_employer_id, bank_hash, payment_method, id_check_result | Streaming |
| `employer_responses` | claim_id, employer_id, response_ts, separation_reason_employer, narrative | SIDES-like |
| `weekly_certifications` | cert_id, claim_id, week_ending, earnings_reported, hours, work_search_contacts (array), able_available, refused_work, ip, device_id | Streaming. Biggest root-cause surface |
| `payments` | payment_id, claim_id, week_ending, amount, method, bank_hash, issued_ts, status (held/released) | Streaming; enforcement point |
| `account_changes` | claim_id, change_type (bank/email/phone/password), ts, device_id | Account-takeover scenario |
| `ext_new_hires` | ssn_hash, employer_id, state, hire_date, report_ts | NDNH / SDNH-like feed |
| `ext_death_records`, `ext_incarceration` | ssn_hash, dates | Cross-match feeds |
| `ext_other_benefits` | ssn_hash, source (workers_comp/pfml/pension/ssdi), start_date, end_date, weekly_amount | "Benefits from other sources" cross-match (§6) |
| `ext_hub_signals` | identifier_type (ssn/bank/ip/email/phone/device), identifier_hash, signal (suspicious_actor/multistate/bad_reputation), source_state, ts | IDH-style SAR / MSCM / reputation feed |
| `ext_bank_verification` | bank_hash, claimant_id, account_open, owner_match, ts | BAV / AVS-like response |
| `ext_ach_returns` | payment_id, return_code (R03/R17/R23/opt-in), ts | Bank feedback → labels |
| `ext_business_registry` | fein / business_name, state, formation_date, status, registered_agent | Fictitious-employer and work-search checks (agent tool) |
| `risk_scores` | entity, score, reason_codes, model_version, scored_ts | Gold; synced to Lakebase |
| `cases` *(Lakebase)* | case_id, claim_id, state, risk_type, status, assignee, agent_summary, disposition, bam_action_code | Operational |
| `overpayments` | claim_id, weeks, amount, root_cause, action_code (10/11/12), responsible_party, detection_point, recovered_amt | Mirrors BAM and ETA 227 dimensions |

**Volume:** nationally there are on the order of a few hundred thousand initial claims per week and well over a million continued weeks claimed (confirm against the current DOL weekly claims release). The demo should run **scaled down** (e.g., 1:100) with a configurable fraud injection rate.

---

## 11. Open questions / next decisions

1. **Framing:** confirm Option A (National Integrity Hub), or go with a single state.
2. ~~**Scale:** all 53 jurisdictions, or a curated 5–10 states?~~ ✅ **Decided: 10 states** (§7.1). Still open: confirm the specific 10, and pick the simulated volume and time compression.
3. ~~**Ingest:** Zerobus vs Kafka / Event Hubs?~~ ✅ **Decided: Zerobus Ingest** (§8.1). Still open: Protobuf vs JSON for the first iteration, and the workspace region.
4. **LLM choice** for agents and `ai_query` (a Foundation Model API endpoint).
5. **Pandemic PUA scenario?** It's a great identity-fraud story, but it's a historical, federally funded program measured separately from regular UI.
6. **Seed with public DOL data** (ETA 539 weekly claims by state, BAM state rates) for realism?
7. **Workspace and deployment:** target workspace and catalog names; Databricks Asset Bundles for repeatable deploys?
8. **Cross-agency feeds:** are the 8 simulated feeds in §6.2 the right set? Should a **Clean Rooms** inter-agency matching moment be part of the storyline?
9. **Success metrics to show:**
   - $ prevented before payment
   - precision and recall vs ground truth
   - investigator time saved by agents
   - time-to-hold (seconds)

---

## 12. Sources

- PaymentAccuracy.gov: DOL ETA Federal-State Unemployment Insurance program page — <https://paymentaccuracy.gov/program/dol-employment-training-administration-federal-state-unemplo-f85701dc>
- DOL OUI: UI Improper Payments — <https://oui.doleta.gov/unemploy/improp_pay.asp>
- DOL OUI: UI Improper Payment Rates Summary by PIIA/IPIA Year — <https://oui.doleta.gov/unemploy/improp_payrate.asp>
- DOL OUI: Causes of UI Overpayments (PIIA 2025 pie chart and table) — <https://oui.doleta.gov/unemploy/pdf/Causes_UIOverpayments-PIIA24.pdf>
- DOL OUI: BAM PIIA 2024 Methodology and Program Description — <https://oui.doleta.gov/unemploy/bam/2024/PIIA_2024_Methodology_and_Program_Description.pdf>
- NASWA UI Integrity Center / Integrity Data Hub — <https://www.naswa.org/integrity-center/integrity-data-hub>
- ET Handbook 401, UI Reports Handbook (ETA 539, ETA 227 definitions) — <https://www.dol.gov/sites/dolgov/files/ETA/handbooks/2017/ETHand401_5th.pdf>
- UIPL 15-24, Change 2 (UIRS reporting system transition) — <https://www.dol.gov/agencies/eta/advisories/uipl-15-24-change-2>
- 20 CFR Part 603 (UC confidentiality and disclosure) — <https://www.ecfr.gov/current/title-20/chapter-V/part-603>
- Treasury Do Not Pay: data sources (DMF-Full, Account Verification Service) — <https://fiscal.treasury.gov/payment-integrity/do-not-pay-dnp/data>
- Treasury Do Not Pay: products (DNP access for UI agencies through IDH) — <https://fiscal.treasury.gov/payment-integrity/do-not-pay-dnp/products>
- DOL OIG report on IDH / DNP death-data cross-matches (2025) — <https://oig.dol.gov/public/reports/oa/2025/19-25-005-03-315.pdf>
- UIPL 13-19: NDNH / SDNH cross-match requirements and best practices — <https://www.dol.gov/sites/dolgov/files/ETA/advisories/UIPL/2019/UIPL_13-19_acc.pdf>
- Social Security Act §1137 (Income & Eligibility Verification System; SAVE) — <https://www.ssa.gov/OP_Home/ssact/title11/1137.htm>
- FinCEN Advisory FIN-2020-A007: UI fraud red flags — <https://www.fincen.gov/system/files/advisory/2020-10-13/Advisory%20Unemployment%20Insurance%20COVID%2019%20508%20Final.pdf>
- Nacha Unemployment Benefits Return Opt-In Program — <https://www.nacha.org/content/unemployment-benefits-return-opt-program>
- DOL ETA Regional Offices (states per region) — <https://www.dol.gov/agencies/eta/regions>
- Databricks Zerobus Ingest: overview — <https://docs.databricks.com/aws/en/ingestion/zerobus-overview>
- Databricks Zerobus Ingest: SDK usage — <https://docs.databricks.com/aws/en/ingestion/zerobus-ingest>
- Databricks Zerobus Ingest: message formats (JSON / Protobuf / Arrow) — <https://docs.databricks.com/aws/en/ingestion/zerobus-message-types>
- Databricks Zerobus Ingest: limits and quotas — <https://learn.microsoft.com/en-gb/azure/databricks/ingestion/zerobus-limits>
