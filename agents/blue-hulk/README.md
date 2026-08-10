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
| [`playbook/content-playbook.md`](./playbook/content-playbook.md) | Distilled actionable playbook: hooks, storytelling frameworks, weekly content mix, CTA ladder, visuals, expectations. |
| [`templates/`](./templates) | Seven fill-in-the-blank templates: loss-confession→lesson (flagship), numbered-step recap, origin-story arc, third-party war story, market-condition read, milestone arc (gated ⚠️), and the Malaysian post voice. |
| [`config/topics.yaml`](./config/topics.yaml) | Topic allow/deny guard (mirrors Hulk's, plus research-driven denials: broker-recruitment content, scarcity mechanics). |
| [`scripts/`](./scripts) | Draft generation (`generate_draft.py`) and Facebook Page posting (`post_to_facebook.py`, text + image). Credential setup guide in [`scripts/README.md`](./scripts/README.md). |

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

## Daily duty rules (automated)

Blue Hulk posts to Facebook automatically every day via
[`scripts/daily_post.py`](./scripts/daily_post.py), scheduled by
[`.github/workflows/blue-hulk-daily.yml`](../../.github/workflows/blue-hulk-daily.yml). Three
standing rules, all deterministic by date (no state file needed):

1. **Post every day** — non-negotiable; the other two rules never cause a day to be skipped.
2. **1 in every 4 posts is a Striker Zones post** — topic from
   [`config/striker_zones_topics.yaml`](./config/striker_zones_topics.yaml), CTA always linking
   to `https://t.me/strikerzonesadmin_bot`.
3. **1 in every 2 posts carries a poster** related to the post — rendered locally with Pillow
   (`render_poster.py`), not Canva (bumped from 1-in-3 on 2026-08-10; see
   [`playbook/content-playbook.md`](./playbook/content-playbook.md) "Performance review" for
   why). Fully automated in the headless daily job; if rendering ever fails, that day posts
   text-only with a note in the run log.

See [`scripts/README.md`](./scripts/README.md) for setup, activation, and the manual test flags
(`--force-striker`, `--force-poster`).
