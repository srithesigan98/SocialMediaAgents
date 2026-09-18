# Hulk — Threads + Instagram content agent

Hulk posts as one brand at a time, selected by **profile**. A profile bundles a persona,
templates, a schedule, a content source and its own credentials, so one engine serves several
accounts without ever mixing their voices or their tokens.

| Profile | Brand | Scope | Platforms |
|---|---|---|---|
| `tansri-millionaires` | TanSri \| Millionaires | finance, trading, stock market, crypto — **exclusively**; it never drifts into unrelated topics | Threads |
| `senang-homes` | Senang Homes | real-estate listings, drawn from a property spreadsheet | Threads + Instagram |

Run anything against a profile with `--profile <name>`; the default comes from `HULK_PROFILE`
in `scripts/.env`.

```bash
cd scripts
python daily_posts.py --profile senang-homes --dry-run   # two property posts + posters
python generate_draft.py "BTC broke resistance"          # finance, reviewed flow
```

## Profiles

### `tansri-millionaires` — finance (the original Hulk)

Persona, playbook, templates and topic guard are the researched originals, unchanged, in
`persona/`, `playbook/`, `templates/` and `config/topics.yaml`. Its flow is still
`generate_draft.py` → human review → `post_to_threads.py`. Nothing about it auto-posts.

### `senang-homes` — real estate

Spreadsheet-driven. Twice a day it picks the least-recently-posted active listing, drafts a post
from that row, generates a poster image, publishes to Threads and Instagram, and then
auto-replies to every commenter with a WhatsApp link prefilled with that property's reference.

```
your spreadsheet (CSV / XLSX / Google Sheet)
      │
      ▼
 pick_listings()          least-recently-posted active rows, cooldown_days apart
      │
      ▼
 make_poster.py           brand-coloured PNG from the row  (or Canva, or your own photo)
      │
      ▼
 generate_property_post   Claude + persona + framework, facts strictly from the row
      │                   CTA line with wa.me/<number>?text=<prefilled, per property>
      ▼
 daily_posts.py           publish → Threads + Instagram, record post ids
      │
      ▼
 reply_bot.py             comments → keyword intent → per-property reply
                          Instagram: DM + public reply · Threads: public reply
```

Everything tunable lives in [`profiles/senang-homes/profile.yaml`](./profiles/senang-homes/profile.yaml):
sheet source and column mapping, poster mode and brand colours, schedule and cooldown, the
WhatsApp number and prefill, and the reply intents.

**Platform limits worth knowing before you rely on it:**

- **Threads has no DM API.** No tool — this one, ManyChat, or a self-hosted one — can auto-DM
  someone who comments on a Thread. Hulk replies publicly with the WhatsApp link instead.
- **Instagram private replies** (real DMs) are one per comment, within **7 days** of it, and the
  `instagram_business_manage_messages` scope needs App Review to reach non-testers.
- **Instagram posts need an image**, and Meta accepts only a **public URL** — never a file
  upload. Generated posters must be hosted somewhere public first
  (see [`scripts/README.md`](./scripts/README.md)).
- Meta tokens expire every 60 days and need refreshing.

## Folder guide

| Path | Purpose |
|---|---|
| [`profiles/`](./profiles) | One folder per brand: `profile.yaml` plus, for `senang-homes`, its own persona, playbook and templates. |
| [`persona/hulk-system-prompt.md`](./persona/hulk-system-prompt.md) | The **finance** persona (`tansri-millionaires`) — identity, voice, scope boundaries, operating rules. |
| [`playbook/creator-research.md`](./playbook/creator-research.md) | Pass-1 raw research findings (6 creators) on the Threads accounts Hulk's style was reverse-engineered from. |
| [`playbook/creator-research-pass2.md`](./playbook/creator-research-pass2.md) | Pass-2 raw research findings (11 more creators, 17 total) — broadened/validated the pattern library. |
| [`playbook/content-playbook.md`](./playbook/content-playbook.md) | The distilled, actionable playbook: hook patterns, content frameworks, topic pillars, CTA styles. |
| [`templates/`](./templates) | One markdown template per content framework, ready to fill in for a new post. |
| [`config/topics.yaml`](./config/topics.yaml) | Machine-readable allow/deny list of topics, used to guard generated content. |
| [`scripts/`](./scripts) | The shared engine: drafting, poster rendering, publishing, and the comment auto-reply bot. |
| [`../design/poster-style-guide.md`](../design/poster-style-guide.md) | Shared (with Blue Hulk) Canva poster workflow — Hulk attaches posters selectively to listicle/aphorism/historical-reveal posts. |

## Research basis (the `tansri-millionaires` profile)

Hulk's finance style is reverse-engineered from analysis of 17 Threads accounts across two research
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
