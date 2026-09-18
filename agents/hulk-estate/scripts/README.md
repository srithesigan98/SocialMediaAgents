# Hulk Estate scripts

## Setup

```bash
cd agents/hulk-estate/scripts
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # fill in keys
```

Then point `../config/agent.yaml` at your spreadsheet and set your WhatsApp number.

## Connecting your spreadsheet

Three options — set `listings.source` in `../config/agent.yaml`:

| `source` | What to set | Notes |
|---|---|---|
| `csv` | `path:` relative to `config/` | Simplest. Export your sheet as CSV. |
| `xlsx` | `path:` relative to `config/` | Needs `openpyxl`. Reads the first worksheet. |
| `gsheet` | `url:` (or `LISTINGS_URL` in `.env`) | Paste the normal Google Sheets link — the script converts it to a CSV export URL itself. The sheet must be readable without login: **Share → Anyone with the link (Viewer)**, or **File → Share → Publish to web → CSV**. |

Then map your column headers under `listings.columns`. Matching ignores case, spaces and
punctuation, so `Monthly Instalment`, `monthly_instalment` and `MONTHLY INSTALMENT` all work.
Only `ref` is required — it's the unique key used for post rotation, for the reply bot's
lookup, and inside the WhatsApp prefill message. Leave any column you don't have as `""`.

Check it before you post anything:

```bash
python -c "import common; c=common.load_config(); [print(l['ref'], '|', l.get('title')) for l in common.active_listings(c)]"
```

## `daily_posts.py` — the two posts a day

Picks the least-recently-posted active listings that are out of `cooldown_days`, drafts a post
for each with Claude, and publishes.

```bash
python daily_posts.py --dry-run      # draft + print, publish nothing  ← start here
python daily_posts.py                # ask y/N before each publish
python daily_posts.py --yes          # unattended, for cron
python daily_posts.py --count 1 --platform threads
```

Published post ids go to `state/posted.json` — that's how the reply bot knows which posts to
watch, so don't delete it.

### Scheduling the two daily posts

`crontab -e`, with the times from `schedule.times` in `agent.yaml`:

```cron
30 9  * * * cd /path/to/SocialMediaAgents/agents/hulk-estate/scripts && venv/bin/python daily_posts.py --count 1 --yes >> state/cron.log 2>&1
30 19 * * * cd /path/to/SocialMediaAgents/agents/hulk-estate/scripts && venv/bin/python daily_posts.py --count 1 --yes >> state/cron.log 2>&1
```

Run it with `--dry-run` for a few days first. `--yes` publishes with no human in the loop.

## `reply_bot.py` — auto-respond to every comment

```bash
python reply_bot.py --dry-run     # show what it would send
python reply_bot.py               # send once
python reply_bot.py --watch 300   # poll every 5 minutes
```

Reads comments on every post recorded in `state/posted.json` within `replies.lookback_days`,
picks a reply template by keyword intent (`price` / `loan` / `viewing` / `availability` /
`default` — all editable in `agent.yaml`), fills in that property's details and the WhatsApp
link, and sends. Answered comments are recorded in `state/replied.json`, so it never
double-replies.

As a cron job:

```cron
*/5 * * * * cd /path/to/.../scripts && venv/bin/python reply_bot.py >> state/cron.log 2>&1
```

### What each platform actually allows

- **Instagram** — sends a genuine **DM** to the commenter (Meta's "private reply"), plus an
  optional public reply. This is the ManyChat behaviour. Meta's limits: one private reply per
  comment, and only within **7 days** of the comment.
- **Threads** — Meta ships **no public DM API** for Threads, so nobody, including ManyChat, can
  auto-DM a Threads commenter. The bot posts a **public reply** under the comment with the
  WhatsApp link instead. That's the ceiling of what the platform permits today.

Instagram posting also requires an image — `instagram_publish` cannot post a caption alone, so
rows with an empty `Image URL` are skipped for Instagram (and posted to Threads normally).

## Credentials

- **Threads**: the setup walkthrough in [`../../hulk/scripts/README.md`](../../hulk/scripts/README.md)
  applies verbatim — just run it against your real-estate Threads account and add the
  `threads_manage_replies` scope so the reply bot can read and answer comments.
- **Instagram**: Meta app → **Instagram** product → Instagram API with Instagram Login. Your
  account must be a **Professional** (Business or Creator) account. Generate a long-lived token
  with the four `instagram_business_*` scopes listed in `.env.example`. Publishing to your own
  account works in development mode; `instagram_business_manage_messages` needs App Review
  before it works for accounts outside your testers, so add yourself as a tester first.
- Tokens expire (60 days) and must be refreshed — same `refresh_access_token` call as Hulk's.

## A note on "OpenReply" / self-hosted reply tools

You don't need one here. A self-hosted reply tool still has to authenticate to the exact same
Meta Graph endpoints this repo calls directly — it would add a server to host, a second token
store, and a webhook endpoint, without unlocking anything Meta doesn't already allow (in
particular, it cannot DM on Threads either). `reply_bot.py` polls instead of taking webhooks,
which means replies land within your poll interval rather than instantly; if you later want
instant replies, the upgrade is a Meta webhook subscription pointed at a small endpoint that
calls `send()` in this same file — not a different product.
