# Blue Hulk — Finance/Trading/Crypto Facebook Agent

Blue Hulk is Hulk's sibling agent, scoped to the same topics (stock market, trading,
cryptocurrency) but built for **Facebook** instead of Threads: longer-form storytelling, stronger
CTAs, trader experience/war-stories, market-condition commentary, and trading psychology content,
plus the ability to generate poster/graphic versions of posts via Canva.

## Folder guide

| Path | Purpose |
|---|---|
| [`persona/blue-hulk-system-prompt.md`](./persona/blue-hulk-system-prompt.md) | Blue Hulk's identity, voice, storytelling frameworks, CTA rules, and scope boundaries. Research-backed. |
| [`playbook/creator-research.md`](./playbook/creator-research.md) | Raw research findings on 13 trading-focused Facebook creators/pages, with verified/inferred/unknown labeling and sources. |
| [`playbook/copywriting-engine.md`](./playbook/copywriting-engine.md) | Emotional-copywriting training layer: drivers, conversion frameworks (PAS/BAB/open loops/Schwartz), CTA mechanics, human-touch rules, and the ≈1-in-5 Malaysian layer. Binding on every draft. |
| [`../design/poster-style-guide.md`](../design/poster-style-guide.md) | Canva poster-generation workflow and locked visual style spec. |
| `playbook/content-playbook.md` | 🚧 Planned — distilled actionable playbook (like Hulk's). |
| `templates/` | 🚧 Planned — fill-in-the-blank post templates per framework. |
| `config/topics.yaml` | 🚧 Planned — topic allow/deny guard (will mirror Hulk's). |
| `scripts/` | 🚧 Planned — draft generation + Facebook Graph API posting script. |

## Research basis

13 creators/pages analyzed (see `playbook/creator-research.md` for full breakdown and sources):

**User-supplied:**
- `facebook.com/HumbledTrader` (Shay Huang) — strongest verified coverage; source of the
  flagship loss-first confession→lesson framework.
- `facebook.com/rowxer` (Mohd Rozaime Rozelan) — identity confirmed but flagged: a Malaysian
  forex IB/broker-recruitment personal brand, a different content archetype than the rest of the
  set; contributed little to the playbook.
- The [directionsmag top-crypto-traders-on-Facebook article](https://www.directionsmag.com/crypto/top-crypto-traders-facebook)
  — creators researched individually: PrimeXBT, Lesiba Mothupi (Forex Chasers), Jabulani Ngcobo
  (flagged: 2019 fraud conviction — treated as a cautionary example, not a style source), South
  African Forex Traders.

**Independently discovered:** Traders State of Mind (Rande Howell — dedicated trading-psychology
page), Warrior Trading / Ross Cameron (flagged: FTC enforcement action — milestone-arc framework
treated as high-caution), Greg Secker / Learn to Trade (cautionary on sales-CTA tone), Trader
Dale, Desire To Trade (Etienne Crete), Mindfully Trading, Simplifying Day Trading (The Trader
Chick).

## Key research takeaways

- Facebook rewards **multi-paragraph narrative arcs**, not the aphorisms/data-dumps that work on
  Threads.
- **Explicit CTAs are the norm** (free resources, community joins, engagement questions) —
  opposite of the CTA-light Threads pattern.
- Trading psychology lands best in the **lived-experience/peer register** (the loss IS the
  lesson) rather than the clinical/coach register.
- **Discipline and risk management are always the resolution** across every credible creator.
- Engagement per post is modest even for large pages — optimize for consistency, not virality.

## Poster generation

Blue Hulk can turn a post into a branded poster via Canva — see
[`../design/poster-style-guide.md`](../design/poster-style-guide.md). Reference design approved and
saved in the connected Canva account ("High-Contrast Trading Strategy Poster").
