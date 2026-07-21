---
name: property-market-analyst
description: Produce a structured analysis of the Kuala Lumpur / Malaysian residential property market — what prices and demand are doing, the drivers behind them (interest rates, loan approvals, developer launches, government schemes), and what banks, NAPIC, and analysts expect next. Use this skill ANY time the user mentions KL property, condo prices, house prices, the property market, OPR / interest rates for housing, home loans, first-time buyer schemes, stamp duty, developer launches, subsale vs new launch, a specific KL area (KLCC, Mont Kiara, Bangsar, Cheras, Bukit Jalil, Setapak, Sentul, Old Klang Road, etc.), or asks for a market update, area report, or buyer outlook — even casually (e.g. "how's the KL condo market", "is it a good time to buy", "what's happening with property"). Trigger this skill before answering any property-market question that depends on current context, data, or scheme rules, instead of answering from memory. The deliverable is both an in-chat summary and a saved markdown report.
---

# Property Market Analyst — Kuala Lumpur

This skill produces an evidence-based analysis of the KL / Malaysian residential property market — what prices and transaction volumes did, why, and what schemes, banks, and developers signal next — using current data and coverage rather than stale memory.

Malaysian residential property is driven by a small, knowable set of forces (Bank Negara's OPR and loan approval rates, household income and the loan-eligibility gap, developer launch pipelines and overhang, government first-home schemes and stamp-duty policy, and very local supply/demand by area and tenure). Surface-level "property always goes up" answers are common and unhelpful. The job of this skill is to do better: pull current data, identify the actual driver, and triangulate with what NAPIC, the banks, and property portals are saying.

## When to trigger

Trigger on anything property-related where the answer depends on present-day context. If the question is purely conceptual ("what is a strata title?", "how does a S&P agreement work?") this skill is not needed — answer directly. If the question is "how's the market / is it a good time to buy / what's my area doing / where are prices going / what schemes can I use" — this skill triggers.

## Mode selection

There are two output modes. Pick one based on how the user phrased the request, and confirm only if it's genuinely ambiguous.

**Brief mode** — short market update. Triggers on phrases like "quick take", "how's the market", "any update", "what's happening with KL condos", or any casual one-liner. Target length: roughly 300–500 words. Lean.

**Deep mode** — full research breakdown. Triggers on "deep dive", "report", "area report", "outlook", "should I buy in [area]", "research", "analysis", "market review", or any request that explicitly asks for scheme details, multiple drivers, or a forward-looking view. Target length: 1,200–2,000 words.

If unclear, default to brief and offer to expand: "I've put together a quick market update — want me to turn this into a full area report or buyer outlook?"

## Workflow

### 1. Establish the scope and window

Before searching, know what you're analysing:
- **Window:** this month, this quarter, "since the last Budget", year-to-date. If unspecified, default to **the latest available quarter plus the current year's narrative arc** for brief mode, and **the last 12 months plus the current Budget cycle** for deep mode.
- **Geography:** all-Malaysia, Klang Valley, KL only, or a specific area/mukim. Senang Homes is KL-focused — default to **Kuala Lumpur / Klang Valley** unless told otherwise.
- **Segment:** high-rise (condo/serviced apartment) vs landed; new launch (primary) vs subsale (secondary); price band (sub-RM500k first-home band, RM500k–1m, luxury). Default to the **sub-RM500k to RM700k condo band** that Senang Homes' first-time-buyer audience lives in, unless told otherwise.

State the scope and window explicitly in the report.

### 2. Pull current data

Use `WebSearch` (and `WebFetch` where useful) to gather across these layers. Run searches in parallel where possible — property analysis is data-and-coverage-bound, so batching saves real time.

**Layer A — Prices, volumes & supply**
- Median/average transacted prices, transaction volume and value, the Malaysian House Price Index (MHPI), residential overhang and unsold units, rental yields, occupancy.
- Sources: **NAPIC** (National Property Information Centre / JPPH), **EdgeProp**, **PropertyGuru** market reports, **iProperty**, **StarProperty**, **Bank Negara Malaysia** (Financial Stability Review, quarterly bulletins).

**Layer B — Macro & financing drivers (the "why")**
- **OPR** (Bank Negara's Overnight Policy Rate) and its direction, home-loan interest rates (BLR/BR + spread), **loan approval / rejection rates** for housing, household debt-to-income, income growth vs price growth (the affordability gap).
- Sources: **Bank Negara Malaysia** (MPC statements, monthly statistics), **RAM/MARC** commentary, bank economic research (Maybank, CIMB, RHB, Public Bank, Hong Leong), The Edge, The Star, ringgitplus.

**Layer C — Policy & scheme drivers**
- First-home **stamp-duty exemptions** (MOT + loan agreement, price thresholds and expiry), **Budget** housing measures, **EPF Account 2/withdrawal** rules for property, and the active first-buyer schemes:
  - **Skim Rumah Pertamaku / MyFirstHome (SRP)** — up to 100% / no-down-payment financing via Cagamas SRP.
  - **MyHome** subsidy scheme, **PR1MA**, **RUMAWIP / Residensi Wilayah** (KL Federal Territory affordable homes, a key one for Senang Homes' audience), **Rumah Selangorku** (for Selangor/Klang Valley), **SJKP** loan guarantee (self-employed / gig workers), **HOPE** rent-to-own for B40.
- Sources: **KPKT** (Ministry of Housing), **Budget** documents and coverage (PropertyGuru, ringgitplus, RinggitPlus/RDS/legal-firm summaries), **REHDA**, LHDN (stamp duty), KWSP/EPF.

**Layer D — Developer & launch activity**
- New launches and take-up rates in KL/Klang Valley, developer sentiment (REHDA Property Industry Survey), Home Ownership Campaign–style promos, rebates/absorbed-cost packages, hotspot corridors (MRT3 Circle Line, transit-oriented developments).
- Sources: **REHDA**, **EdgeProp**, **StarProperty**, developer newsrooms, The Edge property.

### Search query patterns

Use specific, dated queries — they return better material than vague ones. Examples:

- `NAPIC Malaysia residential property market report [current year] [quarter]`
- `Kuala Lumpur condo price [current year] EdgeProp`
- `Bank Negara OPR decision [current month year] housing loan`
- `Malaysia first time home buyer stamp duty exemption [current year] Budget`
- `RUMAWIP Residensi Wilayah KL application [current year]`
- `residential property overhang Malaysia [current year] REHDA`
- `Klang Valley new launch take-up rate [current year]`
- `Skim Rumah Pertamaku SRP eligibility [current year]`

Always inject the current month/year — Malaysian scheme rules and stamp-duty thresholds change with every Budget, and prior-year figures will mislead. Get the current date from the environment if not stated.

### 3. Triangulate before writing

Don't just stitch headlines together. Before writing, answer these in your own thinking:

- What is the **single most important driver** of the current picture across sources? (e.g., "loan rejection rates, not prices, are the binding constraint for first-time buyers this year.")
- Are prices/demand **rising, flat, or softening**, and is it **broad or area-specific**? KL high-rise and landed often move differently — don't blend them.
- Is there a **gap between headline price and what buyers can actually finance**? The affordability/loan-eligibility gap is frequently the real story in Malaysia.
- What's the **next scheduled catalyst** the buyer should watch (next OPR decision, Budget, scheme expiry date, a big MRT/transit milestone)?
- For a **specific area**: what's the supply pipeline, the transacted-vs-asking gap, and the rental yield? Overhang in one corridor can sit next to tight supply in another.

This triangulation is what separates this skill's output from a portal listicle. Skip it and the report becomes generic.

### 4. Write the report

Use the template below. Adjust depth for brief vs deep mode — same structure, different fill.

## Report template

```markdown
# KL Property Market Analysis — [Date]
**Scope:** [e.g., Kuala Lumpur high-rise, sub-RM500k first-home band]
**Window analysed:** [e.g., Q1 2026 + YTD narrative]
**Mode:** [Brief / Deep]

## Snapshot
- **Median price (segment):** RM XXX,XXX  (per sq ft: RM XXX)
- **Change (window):** +/- X.X% YoY
- **Transaction volume:** [up/down/flat] vs prior period
- **Overhang / unsold:** [level and trend]
- **OPR:** X.XX%  |  **Typical home-loan rate:** ~X.XX%  |  **Loan approval rate:** ~XX%

## What's happening
[2–4 sentences in brief mode, 1–2 paragraphs in deep mode. State the price/demand move, the dominant driver, and how strongly it's supported across sources.]

## Why it's happening
### Financing & macro
[OPR direction, loan approval/rejection rates, affordability gap, income vs price. Cite specific figures and dates.]

### Policy & schemes
[Active first-home schemes and stamp-duty exemptions with thresholds and expiry dates. Flag anything changing this Budget cycle. Name the schemes that fit the buyer's price band.]

### Supply & developers
[Launch pipeline, take-up rates, overhang by segment/area, developer promos. Be specific about corridors.]

## For the first-time buyer
[The practical read: what this means for someone buying their first KL condo now. Which schemes apply, what the real monthly commitment looks like at current rates, what to watch. No buy/don't-buy verdict — give them the map, not the decision.]

## What to watch next
[Next 1–3 dated catalysts: next OPR/MPC meeting, Budget, scheme expiry, transit milestone. Plus any wildcard risks — oversupply in a specific corridor, tightening lending.]

## Area / segment table
| Area / Segment | Median psf | YoY | Rental yield | Notes |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

[Include in deep mode, or brief mode if area-specific.]

## Sources
- [Title](url)
- [Title](url)
...
```

## Source citation discipline

Every non-trivial claim — a price level, a scheme threshold, an OPR figure, a loan approval rate, an overhang number — needs a source link. Group them at the bottom under "Sources".

This matters for two reasons. First, Malaysian property attracts a lot of promotional and outdated commentary; readers should be able to verify. Second, scheme rules (stamp duty exemptions, SRP limits, RUMAWIP eligibility) change with Budgets and expiry dates — the links let the reader confirm the rule still holds when they act on it.

If a source can't be verified or you couldn't fetch it cleanly, say so explicitly rather than fabricating a figure. **Never invent a scheme threshold or an expiry date** — these are the numbers buyers make real financial decisions on.

## Saving the report

After producing the analysis in chat, also save it as a markdown file to the outputs folder. Filename pattern:

```
kl-property-analysis-YYYY-MM-DD-[brief|deep].md
```

Save to the outputs directory the session is using (typically the working directory). Then surface the file path to the user so they can open it.

## What to avoid

- **Don't paraphrase memory.** If you don't have a current source for a price, rate, or scheme rule, search for it. Malaysian property data and scheme thresholds stale fast — every Budget rewrites them.
- **Don't blend segments.** KL condos, serviced apartments, and landed move differently; new-launch and subsale are different markets. Say which one you're talking about.
- **Don't confuse asking price with transacted price.** Portal listings are asking prices; NAPIC and transaction data are what actually changed hands. Note the gap — it's often the story.
- **Don't give buy/sell advice.** This skill explains the market and maps the schemes. It does not tell someone to buy, nor promise capital appreciation. The buyer is an adult making a huge decision — give them the map, not the verdict.
- **Don't skip "what to watch next."** Forward-looking value (next OPR meeting, scheme expiry) is what makes the report worth re-reading.
- **Don't overstate precision.** "KL condo prices are broadly flat with pockets of softening in oversupplied corridors" beats a fake single national percentage.

## Edge cases

**Quiet market / no fresh data.** Malaysian property data is quarterly, not tick-by-tick. If there's no new print, say so and lean on the standing narrative: "No new NAPIC release since [date]; the standing picture is X." Don't invent a move.

**Conflicting signals.** The interesting case: e.g., transacted prices flat but developer launches slowing, or rejection rates up while OPR steady. Show both sides with sources, then note what would resolve it (next quarter's NAPIC, next MPC).

**User asks about a specific area.** ("How's Cheras / Old Klang Road / Sri Petaling?") Narrow scope to that area/mukim, pull local transacted prices, supply pipeline, and rental yield, and structure the report around it — same template.

**User asks "is it a good time to buy?"** Reframe to the affordability/scheme picture: current rate, applicable schemes, the real monthly commitment, and what's expiring. Aggregate what analysts and banks are signalling. Do **not** issue a personal buy/don't-buy verdict — synthesise the inputs and let them decide.

**User asks about a specific scheme.** ("Can I use SRP / RUMAWIP?") Pull the current eligibility rules, income ceilings, price caps, and expiry, cite the official source (KPKT/Cagamas/BNM), and flag anything changing this Budget cycle.
