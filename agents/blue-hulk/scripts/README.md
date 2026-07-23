# Blue Hulk Scripts

## Setup

```bash
cd agents/blue-hulk/scripts
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys (see "Getting Facebook credentials" below)
```

## `generate_draft.py` — draft a post

Uses Claude, grounded in the persona, content playbook, copywriting engine, and topic guard.
Requires `ANTHROPIC_API_KEY` in `.env`.

```bash
python generate_draft.py "recovering after a losing streak"
python generate_draft.py "quiet market week" --framework market_condition_read
python generate_draft.py "EPF vs trading account" --framework malaysian_post
```

Drafts are saved to `drafts/` (gitignored) for review — this script never posts anything.

## `post_to_facebook.py` — publish a reviewed draft

```bash
python post_to_facebook.py --file drafts/20260717-120000.md
python post_to_facebook.py --file drafts/20260717-120000.md --image poster.png
python post_to_facebook.py --text "Caption" --image-url https://example.com/poster.png
```

Text posts go to `/{page-id}/feed`; image posts go to `/{page-id}/photos`. Unlike Threads, the
Facebook Graph API accepts **local file uploads** (`--image`), so a Canva-exported poster PNG
attaches directly with no hosting step. Always asks `y/N` confirmation and prints the exact text
first.

## `daily_post.py` — fully automatic daily posting (GitHub Actions)

Generates one on-brand post and publishes it — no human review. Reads creds from environment
vars or `.env`.

```bash
python daily_post.py --dry-run          # generate + print only (safe test, needs ANTHROPIC_API_KEY)
python daily_post.py                    # generate + POST today's topic per the duty rules below
python daily_post.py --dry-run --force-striker   # preview a Striker Zones post regardless of date
python daily_post.py --dry-run --force-poster    # preview a poster-day post regardless of date
```

### Daily duty rules

1. **Post every day.** The scheduled workflow always publishes something — this rule never yields
   to the other two.
2. **1 out of every 4 posts is a Striker Zones post** — topic drawn from
   [`../config/striker_zones_topics.yaml`](../config/striker_zones_topics.yaml), and the post's
   final line is always a CTA linking to **https://t.me/strikerzonesadmin_bot** (verbatim; the
   script appends it as a safety net if the model ever omits it).
3. **1 out of every 3 posts carries a Canva poster** related to that post's content.

All three run off one deterministic day counter (`date.today().toordinal()`), so rules 2 and 3
land on predictable, non-overlapping-by-default days (`% 4 == 0` and `% 3 == 0`) without any
state file to maintain.

**Rule 3 status — wired, needs credentials + field-name check.** `generate_poster()` in
`daily_post.py` calls the Canva Connect API (autofill the brand template, poll, export PNG,
poll) using a refresh token it exchanges for a fresh access token every run — Canva access
tokens only last ~4 hours, useless to store directly for a daily job. Until the four `CANVA_*`
secrets below are set, poster days fall back to a text-only post (rule 1 still fires) and print
a `NOTE:` line in the run log so a missed poster is never silent.

**One placeholder to fix before it will actually work:** the autofill call sends
`{"post_text": {"type": "text", "text": ...}}` — `post_text` is a guess, not yet confirmed
against the real field name(s) in the "High-Contrast Trading Strategy Poster" brand template.
Call `GET /v1/brand-templates/{CANVA_BRAND_TEMPLATE_ID}/dataset` (with a valid access token) to
see the template's actual field names, then update the `data=` mapping in `generate_poster()`
to match.

**Scheduled in the cloud** via [`.github/workflows/blue-hulk-daily.yml`](../../../.github/workflows/blue-hulk-daily.yml)
(runs daily at 12:30 UTC = 8:30pm Malaysia; change the `cron:` to reschedule). To activate:

1. This workflow only runs the schedule from the repo's **default branch** — merge this branch into `main` first.
2. Add three **repository secrets** (GitHub → Settings → Secrets and variables → Actions → New repository secret):
   - `ANTHROPIC_API_KEY` — for drafting
   - `FB_PAGE_ID` — `1020053851202106`
   - `FB_PAGE_ACCESS_TOKEN` — your **permanent** Page token
3. Test it immediately via **Actions tab → Blue Hulk daily post → Run workflow** (the `workflow_dispatch` button), then check your Page.

Because the Page token is non-expiring, this keeps posting indefinitely with no maintenance.

### Automating Canva posters (rule 3)

1. Create a **Canva Developer** integration at [canva.com/developers](https://www.canva.com/developers/)
   → **Your integrations → Create an integration**. Note the app's the actual dashboard —
   `canva.dev/docs/...` links are documentation only, not where you create anything.
2. On **Credentials**: copy the **Client ID**, click **Generate secret**, copy the **Client
   Secret** immediately (shown once).
3. On **Scopes**, enable at least: `design:content:read`, `design:content:write`,
   `brandtemplate:content:read`, `brandtemplate:meta:read` — these are all `generate_poster()`
   actually calls. Enabling extra scopes (e.g. `folder:read`, `profile:read`) is harmless, but
   `get_canva_token.py` only *requests* the four above — requesting a scope your integration
   hasn't enabled makes Canva reject the whole login with `invalid_scope`.
4. On **Authorized redirects**, add `http://127.0.0.1:8888/callback` — Canva rejects the word
   `localhost` and requires the literal IP `127.0.0.1`. It's just a value you type in and save,
   not a link to click; nothing is listening on that port until step 5.
5. Run the one-time OAuth helper locally (needs `CANVA_CLIENT_ID` / `CANVA_CLIENT_SECRET` in
   `.env`, or it'll prompt):
   ```bash
   python get_canva_token.py
   ```
   It opens your browser for a one-time login/approve, catches the redirect, and prints
   `CANVA_CLIENT_ID`, `CANVA_CLIENT_SECRET`, and — the one that matters — `CANVA_REFRESH_TOKEN`.
6. Find the **brand template ID** for the approved "High-Contrast Trading Strategy Poster"
   (see [`../../design/poster-style-guide.md`](../../design/poster-style-guide.md)) by listing
   your templates:
   ```bash
   python inspect_canva_template.py
   ```
   Copy the `id` matching that template — that's `CANVA_BRAND_TEMPLATE_ID`.
7. Confirm the template's **real autofill field name(s)** (the current `generate_poster()` code
   guesses `"post_text"`, which is very likely wrong):
   ```bash
   python inspect_canva_template.py <that-id>
   ```
   Update the `data=` mapping inside `generate_poster()` in `daily_post.py` to use the field
   name(s) it prints.
8. Add all four as **repository secrets**: `CANVA_CLIENT_ID`, `CANVA_CLIENT_SECRET`,
   `CANVA_REFRESH_TOKEN`, `CANVA_BRAND_TEMPLATE_ID`. (Do **not** store a raw access token — it
   expires in ~4 hours; `generate_poster()` derives one from the refresh token every run.)
9. Test end-to-end (still local, no Facebook post) with:
   ```bash
   python daily_post.py --dry-run --force-poster
   ```
   This calls the real Canva autofill + export flow and prints the poster image URL, but skips
   publishing to Facebook.

## Getting Facebook credentials (`FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`)

One-time setup at [developers.facebook.com](https://developers.facebook.com):

1. **Create the Facebook Page** (facebook.com → Pages → Create) if it doesn't exist. Your
   personal account must be an admin.
2. **Register as a developer** at developers.facebook.com with the same Facebook account.
3. **Create an app**: My Apps → Create App → choose the **Business** type (or the "Manage
   everything on your Page" use case in the newer flow). Note the App ID and App Secret
   (App settings → Basic).
4. **Generate a short-lived token**: open the [Graph API Explorer](https://developers.facebook.com/tools/explorer),
   select your app, click "Generate Access Token", and grant these permissions when prompted:
   `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`.
5. **Exchange it for a long-lived user token** (short tokens die in ~1 hour):

   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id={APP_ID}
     &client_secret={APP_SECRET}
     &fb_exchange_token={SHORT_LIVED_TOKEN}
   ```

6. **Get the Page ID and a non-expiring Page token**: call `/me/accounts` with the long-lived
   user token — the response lists your Pages with each Page's `id` and `access_token`. A Page
   token obtained from a long-lived user token does not expire.
7. Put the Page `id` in `FB_PAGE_ID` and the Page `access_token` in `FB_PAGE_ACCESS_TOKEN`
   in `.env`.
8. **Test** with a private/unpublished check first if you like:
   `python post_to_facebook.py --text "test post"` — then delete it from the Page.

**App Review note:** as long as the app only posts to your own Page (where you're the admin),
Development Mode is enough — no App Review needed. Review only becomes necessary if other
users' Pages would use the app.

**Security:** the App Secret and Page token are credentials — keep them only in `.env` (which
is gitignored), never in committed files or chat logs. If a token leaks, invalidate it in the
app dashboard and regenerate.
