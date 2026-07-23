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

**Rule 3 status — not yet automated in the cloud.** Generating the Canva poster and getting a
publicly reachable image URL for the Graph API requires the **Canva Connect API** (its own OAuth
app + access token, analogous to the Facebook app setup below). `generate_poster()` in
`daily_post.py` is the wired-in hook for this — until `CANVA_ACCESS_TOKEN` and
`CANVA_BRAND_TEMPLATE_ID` secrets are added, poster days fall back to a text-only post (rule 1
still fires) and print a `NOTE:` line in the run log so a missed poster is never silent.

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

To turn poster days from "text-only fallback" into an actual attached poster:

1. Create a **Canva Developer** integration at [canva.com/developers](https://www.canva.com/developers/) and
   enable the **Connect API** with the `design:content:read` and `design:content:write` (autofill/export) scopes.
2. Complete the OAuth flow once to get an access token (Canva tokens are short-lived — for a
   scheduled job you'd store a refresh token and refresh it each run, similar in spirit to the
   Threads 60-day refresh).
3. Note the **brand template ID** for the approved "High-Contrast Trading Strategy Poster"
   (see [`../../design/poster-style-guide.md`](../../design/poster-style-guide.md)).
4. Add `CANVA_ACCESS_TOKEN` and `CANVA_BRAND_TEMPLATE_ID` as repository secrets, add them to the
   workflow's `env:` block, and implement the autofill + export call inside `generate_poster()`
   in `daily_post.py` (the function signature and call site are already wired — it just returns
   `None` today).

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
