# Hulk — Finance/Trading/Crypto Threads Agent

Hulk is a Threads (threads.net) content agent scoped **exclusively** to finance, trading, the
stock market, and cryptocurrency. It never posts about, or drifts into, unrelated topics.

## Folder guide

| Path | Purpose |
|---|---|
| [`persona/hulk-system-prompt.md`](./persona/hulk-system-prompt.md) | Hulk's identity, voice, scope boundaries, and operating rules. This is the system prompt to load when running Hulk. |
| [`playbook/creator-research.md`](./playbook/creator-research.md) | Raw research findings on the Threads creators Hulk's style was reverse-engineered from. |
| [`playbook/content-playbook.md`](./playbook/content-playbook.md) | The distilled, actionable playbook: hook patterns, content frameworks, topic pillars, CTA styles. |
| [`templates/`](./templates) | One markdown template per content framework, ready to fill in for a new post. |
| [`config/topics.yaml`](./config/topics.yaml) | Machine-readable allow/deny list of topics, used to guard generated content. |
| [`scripts/`](./scripts) | Draft-generation and Threads-posting scripts. |

## Research basis

Hulk's style is reverse-engineered from analysis of these Threads accounts (see
`playbook/creator-research.md` for the full breakdown, including which findings are verified
vs. inferred):

- `@stocktwits_top` (proxied via `@stocktwits` / `@stocktwitsindia` — exact handle unconfirmed)
- `@cryptokaleo`
- `@ringgitsidehustle`
- `@movanniish`
- `@hormozi` (analyzed for hook/format/framework technique only — not a finance source)

`@zerobull` was requested but no matching account could be located; it's excluded from the
research base.

## Quick start

1. Read `persona/hulk-system-prompt.md` — this is what defines Hulk's voice and boundaries.
2. Pick a framework from `playbook/content-playbook.md` (or a template in `templates/`) that
   fits the post you want.
3. Generate a draft: see [`scripts/README.md`](./scripts/README.md) for `generate_draft.py`
   usage.
4. Review the draft, then post it — manually, or via `post_to_threads.py` once Threads API
   credentials are configured.
