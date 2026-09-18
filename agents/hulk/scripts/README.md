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
| `auto` | `make_poster.py` renders a PNG from the listing row (brand colours, price, specs, WhatsApp band) | ✅ yes |
| `canva` | Generated in a Claude session via the Canva connector, then pasted into the sheet's `Image URL` | ❌ needs a session |
| `sheet` | Whatever is in the row's `Image URL` (your own photography) | ✅ yes |
| `none` | No image — Threads only, Instagram gets skipped | ✅ yes |

```bash
python make_poster.py HE-001                    # -> posters/senang-homes-HE-001.png
python make_poster.py HE-001 --open-size 1080x1080
```

In `auto` mode, a row that already has an `Image URL` always wins — a real photo beats a
generated poster, so the generator only fills gaps.

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
