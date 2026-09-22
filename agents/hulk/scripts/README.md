# Hulk Scripts

Hulk runs **per profile**. A profile is one brand: its persona, templates, schedule,
spreadsheet and credential names, in `../profiles/<name>/profile.yaml`.

| Profile | What it posts | Flow |
|---|---|---|
| `tansri-millionaires` | finance / trading / crypto, by topic | `generate_draft.py` → review → `post_to_threads.py` |
| `senang-homes` | real-estate listings from a spreadsheet, 2×/day, with posters and WhatsApp auto-reply | `daily_posts.py` + `reply_bot.py` |

Every property script takes `--profile`; the default comes from `HULK_PROFILE` in `.env`.
State files are namespaced per profile, so the two brands never share a posting rotation or a
replied-to list.


## Setup

```bash
cd agents/hulk/scripts
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

Then set up whichever profile you're running — the finance scripts are next, the real-estate
profile is documented under **Real estate** further down.

## `generate_draft.py` — draft a post

Uses Claude, grounded in `../persona/hulk-system-prompt.md`, `../playbook/content-playbook.md`,
and `../config/topics.yaml`, to draft a Threads post. Requires `ANTHROPIC_API_KEY` in `.env`.

```bash
python generate_draft.py "BTC just broke a 3-month resistance level"
python generate_draft.py "risk management after a losing streak" --framework standalone_aphorism
```

Drafts are saved to `drafts/` (gitignored) for review — this script never posts anything.

## `post_to_threads.py` — publish a reviewed draft

Publishes text to Threads via the Meta Threads Graph API. Requires `THREADS_USER_ID` and
`THREADS_ACCESS_TOKEN` in `.env` — you need a Meta developer app with Threads API access to
generate these (see https://developers.facebook.com/docs/threads); this script does not handle
that OAuth setup.

```bash
python post_to_threads.py --file drafts/20260716-120000.md
python post_to_threads.py --text "Quick post text"
python post_to_threads.py --file drafts/20260716-120000.md --image-url https://example.com/poster.png
```

Always asks for a `y/N` confirmation before publishing, and prints the exact text first.
`--image-url` attaches an image (e.g. a Canva poster exported per
`../../design/poster-style-guide.md`) — must be a publicly reachable URL, since the Threads API
doesn't accept local file uploads.

## `daily_post.py` — fully automatic daily posting (GitHub Actions)

Generates one on-brand post per slot and publishes it — no human review. Reads creds from
environment vars or `.env`.

```bash
python daily_post.py --slot 0 --dry-run          # generate + print only (safe test, needs ANTHROPIC_API_KEY)
python daily_post.py --slot 0                    # generate + POST that slot's content per the duty rules below
python daily_post.py --slot 1 --dry-run --force-framework listicle_breakdown   # preview a specific framework
python daily_post.py --slot 0 --dry-run --force-striker                       # preview the Striker Zones branch
```

### Daily duty rules

1. **Post 3 times a day, no matter what.** Slots 0/1/2 correspond to 9am / 2pm / 8pm Malaysia
   (`SLOT_HOURS_UTC` in `daily_post.py`) — the scheduled workflow fires one run per slot and
   always publishes something. This rule never yields to the other two.
2. **Every post carries a poster graphic.** No selective gating by framework anymore — all three
   daily posts get one.
3. **1 out of every 3 days is a Striker Zones day** — on that day, the **first post (slot 0)** is
   drawn from [`../config/striker_zones_topics.yaml`](../config/striker_zones_topics.yaml), and
   its final line is always a CTA linking to **https://t.me/strikerzonesadmin_bot** (verbatim; the
   script appends it as a safety net if the model ever omits it). Slots 1 and 2 that day still run
   the normal framework rotation.

Non-Striker slots rotate deterministically through the 8 content frameworks in
[`../templates/`](../templates) (`audience_question`, `call_reasoning_risk`, `confession_lesson`,
`contrarian_reframe`, `historical_compounding_reveal`, `listicle_breakdown`, `progress_reveal`,
`standalone_aphorism`), keyed off a global counter (`day_index * 3 + slot_index`) so the feed
doesn't repeat the same shape run after run. The topic itself is chosen by Claude from the allowed
topic pillars in `../config/topics.yaml` — there's no fixed topic pool for these slots, since
Hulk's scope is broader than Striker Zones (any in-lane finance/trading/crypto angle). Everything
runs off ONE deterministic day counter (`date.today().toordinal()`), so which framework applies to
a given day+slot, and which day is a Striker Zones day, is reproducible and never drifts.

**Poster generation — fully automated, no Canva account needed, but with one extra step Blue Hulk
doesn't need.** `generate_poster()` in `daily_post.py` asks Claude to split each post into four
slots (top label / headline / body / footer), then [`render_poster.py`](./render_poster.py) draws
the poster locally with Pillow, matching the locked style spec in
[`../../design/poster-style-guide.md`](../../design/poster-style-guide.md).
**Unlike Facebook, the Threads API requires a publicly reachable image URL — it won't accept a
local file upload** — so the rendered PNG (`posted_assets/hulk-poster-slot{N}.png`, overwritten
each time that slot posts) is committed and pushed to this repo, and its
`raw.githubusercontent.com` URL is what actually gets posted. If rendering or the git push ever
fails for any reason, rule 1 always wins: it falls back to a text-only post and prints a `NOTE:`
line so a missed poster is never silent.

Preview a poster anytime without touching Threads or git:
```bash
python render_poster.py "BTC — testing resistance" "Most traders blow up the same way" \
  "Position size kills more accounts than bad ideas." "What's your leverage lesson?"
```

**The Striker Zones slot gets a different poster style.** `render_poster.py` also has
`render_striker_poster()`, which mirrors the real
[Striker Zones 2.1 Pro TradingView indicator](https://www.tradingview.com/script/txqFnkJH-Striker-Zones-2-1-Pro-Scalp-Intraday/)'s
look — light background, a teal shaded entry→SL risk box, and orange/mint/dark-green TP1/TP2/TP3
pill labels — instead of the generic dark candlestick poster used everywhere else.
`compute_illustrative_levels()` generates the price levels; they are **always synthetic**
(seeded by day+slot, rotating through XAU/USD, BTC/USD, EUR/USD, US30) and the poster prints
"Illustrative example — not a live signal" twice, since this automation has no live market feed
and must never present fabricated numbers as a real signal. Preview it directly:
```bash
python -c "
from pathlib import Path
from render_poster import render_striker_poster, compute_illustrative_levels
l = compute_illustrative_levels(seed=0)
render_striker_poster(l['symbol_label'], l['entry'], l['sl'], l['tp1'], l['tp2'], l['tp3'], l['decimals'], Path('drafts/striker-preview.png'), seed=0)
"
```

**Scheduled in the cloud** via [`.github/workflows/hulk-daily.yml`](../../../.github/workflows/hulk-daily.yml)
— 3 cron entries (01:00 / 06:00 / 12:00 UTC = 9am / 2pm / 8pm Malaysia), each mapped back to its
slot number via `github.event.schedule` in the workflow's "Determine slot" step. Change the
`cron:` lines to reschedule, but keep `SLOT_HOURS_UTC` in `daily_post.py` in sync with them. To
activate:

1. This workflow only runs the schedule from the repo's **default branch** — merge this branch into `main` first.
2. Add three **repository secrets** (GitHub → Settings → Secrets and variables → Actions → New repository secret):
   - `ANTHROPIC_API_KEY_2` — a separate Anthropic key dedicated to Hulk (kept distinct from Blue
     Hulk's `ANTHROPIC_API_KEY` secret so usage/billing can be told apart between the two agents)
   - `THREADS_USER_ID` — `28866026592987310`
   - `THREADS_ACCESS_TOKEN` — your current 60-day long-lived Threads token (see below for how to get one)
3. The workflow needs `contents: write` permission to commit each post's poster PNG — already set
   in the workflow file, but double-check under Settings → Actions → General → Workflow
   permissions that "Read and write permissions" isn't overridden to read-only at the repo level.
4. Test it immediately via **Actions tab → Hulk daily post → Run workflow** (the `workflow_dispatch` button — pick a slot, and optionally force Striker/a framework), then check your Threads profile.

**Token expiry — the one thing this needs that Blue Hulk doesn't:** Threads long-lived tokens
expire after 60 days (Facebook Page tokens don't). Roughly every ~50 days, refresh it:

```
GET https://graph.threads.net/refresh_access_token
  ?grant_type=th_refresh_token
  &access_token={CURRENT_LONG_LIVED_TOKEN}
```

Take the new `access_token` from the response and update the `THREADS_ACCESS_TOKEN` repository
secret with it (Settings → Secrets and variables → Actions → click the secret → Update). This step
isn't automated — there's no secret-rotation script in this repo yet.

## Getting Threads credentials (`THREADS_USER_ID`, `THREADS_ACCESS_TOKEN`)

One-time setup at [developers.facebook.com](https://developers.facebook.com). The Threads API is
**free** — posting costs nothing (only `generate_draft.py`'s `ANTHROPIC_API_KEY` is a paid,
separate service). Meta relabels dashboard menus often; the **token endpoints below are stable**,
so rely on those if the UI differs.

1. **Have a Threads account** you post from (the one linked to your Instagram is fine).
2. **Register as a developer** at developers.facebook.com with the same Meta account.
3. **Create an app**: My Apps → Create app → choose the **"Access the Threads API"** use case.
   This adds the Threads product. Note the **Threads App ID** and **Threads App Secret** (under
   the use case's settings / App settings → Basic).
4. **Configure the use case** — add these permissions:
   - `threads_basic` and `threads_content_publish` (required to post).
   - Optionally add `threads_manage_insights` + `threads_manage_replies` now, so the future
     Analytics + reply-drafter agents (the council's engagement loop) can read metrics and
     surface comments without re-doing this setup.

   Set a **Redirect Callback URI** (any HTTPS URL you control; `https://localhost/` works for
   manual copy-paste of the returned code).
5. **Add yourself as a tester**: in the app's Threads settings / Roles, add your Threads account,
   then open the **Threads app → Settings → Account → Website permissions** and accept the
   invite. Development Mode + you-as-tester is enough to post to your **own** account — no App
   Review needed. (Review is only required to post on *other* people's accounts.)
6. **Generate a short-lived token**: use the app's Threads **"Generate access token"** button for
   your account (grant the scopes above), or run the OAuth flow at
   `https://threads.net/oauth/authorize`.
7. **Exchange it for a long-lived (60-day) token** (short tokens die in ~1 hour):

   ```
   GET https://graph.threads.net/access_token
     ?grant_type=th_exchange_token
     &client_secret={THREADS_APP_SECRET}
     &access_token={SHORT_LIVED_TOKEN}
   ```

8. **Get your Threads user id**:

   ```
   GET https://graph.threads.net/v1.0/me?fields=id,username&access_token={LONG_LIVED_TOKEN}
   ```

9. Put `id` → `THREADS_USER_ID` and the long-lived token → `THREADS_ACCESS_TOKEN` in `.env`.
10. **Refresh before it expires** (60-day tokens are renewable):

    ```
    GET https://graph.threads.net/refresh_access_token
      ?grant_type=th_refresh_token
      &access_token={LONG_LIVED_TOKEN}
    ```

11. **Test**: `python post_to_threads.py --text "test post"` → confirm `y` → then delete it from
    Threads.

**Security:** the App Secret and access token are credentials — keep them only in `.env` (which is
gitignored), never in committed files or chat. If a token leaks, invalidate it in the app
dashboard and regenerate.

## `collect_metrics.py` — performance dashboard data

Every `daily_post.py` publish is logged to `metrics/post_log.jsonl` (post id, date, slot,
Striker/framework flags). `collect_metrics.py` reads that log, calls the Threads Insights API for
each post's current views/likes/replies/reposts/quotes, and appends a timestamped snapshot per
post to `metrics/history.jsonl`, then commits and pushes both files. This is what the performance
dashboard reads.

```bash
python collect_metrics.py   # needs THREADS_ACCESS_TOKEN in .env
```

Insights requires the `threads_manage_insights` permission on the token — if that scope wasn't
granted when the token was generated, every snapshot will just carry `null` values instead of
failing the run. Scheduled in the cloud via
[`.github/workflows/metrics-collect.yml`](../../../.github/workflows/metrics-collect.yml) (runs
once daily, after all 3 of the day's posting slots) — reuses the same `THREADS_ACCESS_TOKEN`
secret already wired for `daily_post.py`, no new secrets needed.

## Notes

- `generate_draft.py` / `post_to_threads.py` never auto-post — they are the reviewed,
  human-in-the-loop flow for `tansri-millionaires`.
- `drafts/`, `state/` and `posters/` are gitignored so generated content doesn't clutter the repo.

---

# Real estate — the `senang-homes` profile

Same Hulk, same venv, same `.env`; a different profile in
[`../profiles/senang-homes/`](../profiles/senang-homes/). Tune it in `profile.yaml`.

## 1. Connect your spreadsheet

Set `listings.source` in `../profiles/senang-homes/profile.yaml`:

| `source` | What to set | Notes |
|---|---|---|
| `csv` | `path:` relative to the profile folder | Simplest. Export your sheet as CSV. |
| `xlsx` | `path:` relative to the profile folder | Needs `openpyxl`. Reads the first worksheet. |
| `gsheet` | `url:` (or `SENANG_HOMES_LISTINGS_URL` in `.env`) | Paste the normal Google Sheets link — the script converts it to a CSV export URL itself. The sheet must be readable without login: **Share → Anyone with the link (Viewer)**, or **File → Share → Publish to web → CSV**. |

Then map your column headers under `listings.columns`. Matching ignores case, spaces and
punctuation, so `Monthly Instalment`, `monthly_instalment` and `MONTHLY INSTALMENT` all work.
Only `ref` is required — it keys the posting rotation, the reply bot's lookup, and the WhatsApp
prefill. Leave any column you don't have as `""`.

**Google Drive**: if your property details live in Drive as documents, photos or a mixed folder
rather than one clean sheet, don't point the scripts at Drive — ask Claude in a session in this
repo to read the Drive files and write them into the listings sheet. Claude has the Drive
connector; cron does not, and a half-structured folder needs judgement to turn into rows.

Check it loads before posting anything:

```bash
python -c "import common; c=common.load_config('senang-homes'); [print(l['ref'],'|',l.get('title')) for l in common.active_listings(c)]"
```

## 2. Posters — `make_poster.py`

Instagram **cannot publish a caption without an image**, so every property post needs one.
`poster.mode` in `profile.yaml` picks where it comes from:

| mode | Image source | Works in cron? |
|---|---|---|
| `auto` | `make_poster.py` composites the listing's photo with location/price/highlight text and a "comment the property name" CTA — deliberately minimal, no WhatsApp link or ref number on the image itself | ✅ yes |
| `canva` | Generated in a Claude session via the Canva connector, then pasted into the sheet's `Image URL` | ❌ needs a session |
| `sheet` | Whatever is in the row's `Image URL` (your own photography) — posted **as-is**, bypassing `make_poster.py` entirely | ✅ yes |
| `none` | No image — Threads only, Instagram gets skipped | ✅ yes |

```bash
python make_poster.py HE-001                    # -> posters/senang-homes-HE-001.png
python make_poster.py HE-001 --open-size 1080x1080
```

**Two different "image" fields, on purpose:**
- `image_url` (mapped from your sheet's Image URL column, if you have one) means a **finished,
  ready-to-post image** — `daily_posts.py` uses it as-is on Threads/Instagram and never calls
  `make_poster.py` at all.
- `photo_url` means a **raw source photo to composite into the poster** — `make_poster.py` uses
  it as the background for the price/location/highlight text overlay. This is what a plain
  building photo (e.g. found via search) should feed, so it never gets posted bare with no price
  or CTA on it.

If your sheet has no Image URL column at all (common for project-listing sheets), add
`agents/hulk/profiles/<profile>/photo_overrides.csv` with two columns, `title,photo_url` — one
row per project name, pointing at a real photo (the developer's own marketing render is the most
reliable source). `common.load_listings()` fills `photo_url` from this file automatically when
a row's title matches, so every unit-type row under the same project shares one photo without
repeating the URL per row. In `auto` mode, a row that already has a real `Image URL` from the
sheet always wins over this override — the override only fills gaps.

### Hosting posters (required before they can be attached)

Meta's APIs accept **only a publicly reachable URL** for images — neither Threads nor Instagram
takes a file upload. So a locally rendered poster must be served from somewhere public, and
`poster.public_base_url` must point at it. Any static host works: an S3 or Cloudflare R2 bucket
with public read, a small VPS/nginx directory, Netlify/Vercel static hosting, or a public GitHub
repo served through its raw URL. Set `public_base_url` to the folder those files land in and the
script will build the final URL by filename.

Until it's set, `daily_posts.py` still renders the poster and still posts — text-only on
Threads, and it skips Instagram — and tells you why.

## 3. `daily_posts.py` — the two posts a day

Picks the least-recently-posted active listings out of `cooldown_days`, resolves a poster,
drafts with Claude, and publishes.

```bash
python daily_posts.py --dry-run      # draft + render poster, publish nothing   ← start here
python daily_posts.py                # ask y/N before each publish
python daily_posts.py --yes          # unattended, for cron
python daily_posts.py --count 1 --platform threads
```

Published post ids go to `state/senang-homes-posted.json` — that's how the reply bot knows which
posts to watch, so don't delete it.

### Scheduling

`crontab -e`, matching `schedule.times` in `profile.yaml`:

```cron
30 9  * * * cd /path/to/SocialMediaAgents/agents/hulk/scripts && venv/bin/python daily_posts.py --profile senang-homes --count 1 --yes >> state/cron.log 2>&1
30 19 * * * cd /path/to/SocialMediaAgents/agents/hulk/scripts && venv/bin/python daily_posts.py --profile senang-homes --count 1 --yes >> state/cron.log 2>&1
*/5 *  * * * cd /path/to/SocialMediaAgents/agents/hulk/scripts && venv/bin/python reply_bot.py   --profile senang-homes >> state/cron.log 2>&1
```

Run `--dry-run` for a few days first — `--yes` publishes with no human in the loop.

## 4. `reply_bot.py` — auto-respond with the WhatsApp link

```bash
python reply_bot.py --dry-run     # show what it would send
python reply_bot.py               # send once
python reply_bot.py --watch 300   # poll every 5 minutes
```

Reads comments on every post in `state/senang-homes-posted.json` within `replies.lookback_days`,
picks a template by keyword intent (`price` / `loan` / `viewing` / `availability` / `default` —
all editable in `profile.yaml`, and matched on whole words so "rm" doesn't fire on "warm"),
fills in that property's details and its WhatsApp link, and sends. Answered comments are recorded
in `state/senang-homes-replied.json`, so nobody gets replied to twice.

### What each platform actually allows

- **Instagram** — a genuine **DM** to the commenter (Meta's "private reply"), plus an optional
  public reply. This is the ManyChat behaviour. Meta's limits: one private reply per comment,
  and only within **7 days** of that comment.
- **Threads** — Meta ships **no public DM API** for Threads, so nobody, including ManyChat, can
  auto-DM a Threads commenter. The bot posts a **public reply** under the comment carrying the
  WhatsApp link instead. That is the ceiling of what the platform permits today.

## 5. Instagram credentials for Senang Homes

The Threads walkthrough above applies to the Senang Homes Threads account too — just add the
`threads_manage_replies` scope and store the values as `SENANG_THREADS_*`.

For Instagram, use **Instagram API with Instagram Login**:

1. The account must be a **Professional** (Business or Creator) account: Instagram → Settings →
   Account type and tools → Switch to professional account.
2. In a Meta developer app, add the **Instagram** product and choose **Instagram API with
   Instagram Login**. This flow authenticates against Instagram directly, so the Instagram
   account does **not** need to be linked to a Facebook Page, and does not need to sit under the
   same Facebook account that owns the developer app.
3. Request scopes: `instagram_business_basic`, `instagram_business_content_publish`,
   `instagram_business_manage_comments`, `instagram_business_manage_messages`.
4. Add the account as a tester and run Business Login to get a token; exchange it for a
   long-lived (60-day) one and store as `SENANG_IG_USER_ID` / `SENANG_IG_ACCESS_TOKEN`.
5. `instagram_business_manage_messages` (the DM auto-reply) needs **App Review** before it works
   for anyone outside your app's testers — publishing and comment replies do not.

## A note on "OpenReply" / self-hosted reply tools

You don't need one. A self-hosted reply tool authenticates to the exact same Meta endpoints this
repo already calls — it adds a server to host, a second token store and a webhook endpoint
without unlocking anything Meta doesn't already allow (in particular, it cannot DM on Threads
either). `reply_bot.py` polls rather than taking webhooks, so replies land within your poll
interval instead of instantly. If you later want instant replies, the upgrade is a Meta webhook
subscription pointed at a small endpoint that calls `send()` in that same file — not a different
product.
