# Hulk — Finance/Trading/Crypto Threads Agent

Hulk is a Threads (threads.net) content agent scoped **exclusively** to finance, trading, the
stock market, and cryptocurrency. It never posts about, or drifts into, unrelated topics.

## Folder guide

| Path | Purpose |
|---|---|
| [`persona/hulk-system-prompt.md`](./persona/hulk-system-prompt.md) | Hulk's identity, voice, scope boundaries, and operating rules. This is the system prompt to load when running Hulk. |
| [`playbook/creator-research.md`](./playbook/creator-research.md) | Pass-1 raw research findings (6 creators) on the Threads accounts Hulk's style was reverse-engineered from. |
| [`playbook/creator-research-pass2.md`](./playbook/creator-research-pass2.md) | Pass-2 raw research findings (11 more creators, 17 total) — broadened/validated the pattern library. |
| [`playbook/content-playbook.md`](./playbook/content-playbook.md) | The distilled, actionable playbook: hook patterns, content frameworks, topic pillars, CTA styles. |
| [`templates/`](./templates) | One markdown template per content framework, ready to fill in for a new post. |
| [`config/topics.yaml`](./config/topics.yaml) | Machine-readable allow/deny list of topics, used to guard generated content. |
| [`scripts/`](./scripts) | Draft-generation and Threads-posting scripts. |

## Research basis

Hulk's style is reverse-engineered from analysis of 17 Threads accounts across two research
passes (see `playbook/creator-research.md` and `playbook/creator-research-pass2.md` for full
breakdowns, including which findings are verified vs. inferred):

**Pass 1 (user-supplied handles):**
- `@stocktwits_top` (proxied via `@stocktwits` / `@stocktwitsindia` — exact handle unconfirmed)
- `@cryptokaleo`
- `@ringgitsidehustle`
- `@movanniish`
- `@hormozi` (analyzed for hook/format/framework technique only — not a finance source)

`@zerobull` was requested but no matching account could be located; it's excluded from the
research base.

**Pass 2 (independently discovered — top/viral finance-trading-crypto Threads creators):**
`@hyperstocks`, `@investments`, `@13finance`, `@your.richbff` (Vivian Tu), `@cryptobacker`,
`@kylascan` (Kyla Scanlon), `@benzinga`, `@kobeissiletter` (The Kobeissi Letter),
`@humphreytalks` (Humphrey Yang), `@cryptowendyo` (Wendy O), `@bitcoin.daily` (Josh Molnar).

## Quick start

1. Read `persona/hulk-system-prompt.md` — this is what defines Hulk's voice and boundaries.
2. Pick a framework from `playbook/content-playbook.md` (or a template in `templates/`) that
   fits the post you want.
3. Generate a draft: see [`scripts/README.md`](./scripts/README.md) for `generate_draft.py`
   usage.
4. Review the draft, then post it — manually, or via `post_to_threads.py` once Threads API
   credentials are configured.
