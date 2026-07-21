# Senang Homes — Social Media Agents v2.0

**Version 2.0** of the SocialMediaAgents suite, specialised for **real estate, the Malaysian property market, condos, and first-time home buyers — mainly in Kuala Lumpur.**

Built for the [Senang Homes](https://www.instagram.com/senanghomes) Instagram brand.

> *"Senang"* = easy / comfortable in Bahasa Malaysia. The whole brand promise — and the tone of every agent here — is making the KL property journey feel *senang* for first-time buyers.

---

## What this is

v1.0 of SocialMediaAgents was built for the gold/forex trading niche (a market-analyst agent + a short-form-content agent). v2.0 keeps the same proven two-agent architecture but re-points every driver, source, hook, and hashtag at the **Kuala Lumpur residential property market**.

Same skeleton, completely re-specialised brain.

| v1.0 (gold/forex) | v2.0 (Senang Homes / KL property) |
|---|---|
| `gold-market-analyst` | `property-market-analyst` |
| `gold-content-creator` | `property-content-creator` |
| XAU/USD, DXY, Fed, real yields | House prices, OPR, BNM, loan rates, developer launches |
| IB / broker conversion | Property lead-gen (viewings, WhatsApp enquiries, referrals) |
| Traders & prop-firm hopefuls | First-time home buyers, young professionals, upgraders in KL |

## The agents

### 1. `property-market-analyst`
Produces evidence-based analysis of the KL / Malaysian property market — what prices are doing, why, and what the schemes, banks, and developers are signalling next. Pulls **current** data (NAPIC, Bank Negara, PropertyGuru, EdgeProp, iProperty, StarProperty, REHDA, Budget announcements) rather than answering from stale memory. Brief mode for quick market updates; deep mode for area reports and buyer outlooks.

→ [`skills/property-market-analyst/SKILL.md`](skills/property-market-analyst/SKILL.md)

### 2. `property-content-creator`
Writes high-engagement short-form video content (Reels, TikTok, Shorts) for first-time home buyers in KL, with the secondary goal of converting viewers into booked viewings and WhatsApp enquiries. Opinionated: strong hooks, one clear takeaway per video, bilingual English/Manglish voice, and value-first lead-gen that never sounds like a hard sell.

→ [`skills/property-content-creator/SKILL.md`](skills/property-content-creator/SKILL.md)

Reference library:
- [`references/hooks-library.md`](skills/property-content-creator/references/hooks-library.md) — 8 hook archetypes for property content
- [`references/lead-gen-patterns.md`](skills/property-content-creator/references/lead-gen-patterns.md) — converting views into viewings without sounding salesy
- [`references/posting-strategy.md`](skills/property-content-creator/references/posting-strategy.md) — cadence, timing, series formats
- [`references/seo-keywords.md`](skills/property-content-creator/references/seo-keywords.md) — Malaysian property hashtag tiers & caption SEO

## How to use

These are [Claude Code skills](https://code.claude.com/docs). Point Claude at this folder (or copy `skills/*` into your `.claude/skills/` directory) and the agents trigger automatically when you ask for a market update or a piece of content. Or invoke them by name.

Typical prompts:
- *"What's the KL condo market doing this month?"* → `property-market-analyst`
- *"Write me a Reel about the RM500k stamp duty exemption"* → `property-content-creator`
- *"Give me a Sunday content plan for first-time buyers"* → `property-content-creator`

## Guardrails baked in

- **No price guarantees or financial advice.** Agents explain the market and the schemes; they don't promise capital gains or tell people to buy.
- **Cite live sources.** Every scheme figure, price level, or rate is sourced and dated — Malaysian property rules (stamp duty, OPR, campaigns) change with every Budget.
- **Honest lead-gen.** Value first; the enquiry/viewing CTA is the natural answer to a problem the content already solved.
