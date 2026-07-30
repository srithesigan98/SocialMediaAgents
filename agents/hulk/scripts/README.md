# Hulk Scripts

## Setup

```bash
cd agents/hulk/scripts
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

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

Generates one on-brand post and publishes it — no human review. Reads creds from environment
vars or `.env`.

```bash
python daily_post.py --dry-run          # generate + print only (safe test, needs ANTHROPIC_API_KEY)
python daily_post.py                    # generate + POST today's framework per the duty rules below
python daily_post.py --dry-run --force-framework listicle_breakdown   # preview a specific framework
```

### Daily duty rules

1. **Post every day.** The scheduled workflow always publishes something — this rule never yields
   to the other two.
2. **Rotates deterministically through the 8 content frameworks** in
   [`../templates/`](../templates) (`audience_question`, `call_reasoning_risk`,
   `confession_lesson`, `contrarian_reframe`, `historical_compounding_reveal`,
   `listicle_breakdown`, `progress_reveal`, `standalone_aphorism`) so the feed doesn't repeat the
   same shape two days running. The topic itself is chosen by Claude from the allowed topic
   pillars in `../config/topics.yaml` — there's no fixed topic pool like Blue Hulk's, since Hulk's
   scope is broader (any in-lane finance/trading/crypto angle).
3. **Poster days are content-driven, not a fixed ratio.** Per the persona's own guidance
   (`../persona/hulk-system-prompt.md`), a poster is attached only when that day's framework is
   `listicle_breakdown`, `standalone_aphorism`, or `historical_compounding_reveal` — the three
   framework types the research found are actually screenshot-worthy. That's 3 of the 8 rotation
   slots, so roughly 1 in 3 days in practice.

Both rules run off ONE deterministic day counter (`date.today().toordinal()`), so which framework
(and whether a poster attaches) is reproducible and never drifts.

**Rule 3 status — fully automated, no Canva account needed, but with one extra step Blue Hulk
doesn't need.** `generate_poster()` in `daily_post.py` asks Claude to split the day's post into
four slots (top label / headline / body / footer), then
[`render_poster.py`](./render_poster.py) draws the poster locally with Pillow, matching the
locked style spec in [`../../design/poster-style-guide.md`](../../design/poster-style-guide.md).
**Unlike Facebook, the Threads API requires a publicly reachable image URL — it won't accept a
local file upload** — so the rendered PNG (`posted_assets/hulk-poster.png`, overwritten each
poster day) is committed and pushed to this repo, and its `raw.githubusercontent.com` URL is what
actually gets posted. If rendering or the git push ever fails for any reason, rule 1 always wins:
it falls back to a text-only post and prints a `NOTE:` line so a missed poster is never silent.

Preview a poster anytime without touching Threads or git:
```bash
python render_poster.py "BTC — testing resistance" "Most traders blow up the same way" \
  "Position size kills more accounts than bad ideas." "What's your leverage lesson?"
```

**Scheduled in the cloud** via [`.github/workflows/hulk-daily.yml`](../../../.github/workflows/hulk-daily.yml)
(runs daily at 12:45 UTC = 8:45pm Malaysia, 15 minutes after Blue Hulk's Facebook post; change the
`cron:` to reschedule). To activate:

1. This workflow only runs the schedule from the repo's **default branch** — merge this branch into `main` first.
2. Add three **repository secrets** (GitHub → Settings → Secrets and variables → Actions → New repository secret):
   - `ANTHROPIC_API_KEY` — same key used by Blue Hulk's workflow, for drafting
   - `THREADS_USER_ID` — `28866026592987310`
   - `THREADS_ACCESS_TOKEN` — your current 60-day long-lived Threads token (see below for how to get one)
3. The workflow needs `contents: write` permission to commit the poster PNG — already set in the
   workflow file, but double-check under Settings → Actions → General → Workflow permissions that
   "Read and write permissions" isn't overridden to read-only at the repo level.
4. Test it immediately via **Actions tab → Hulk daily post → Run workflow** (the `workflow_dispatch` button), then check your Threads profile.

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

## Notes

- `drafts/` is gitignored so review notes and generated text don't clutter the repo.
- `posted_assets/hulk-poster.png` is **not** gitignored — `daily_post.py` commits it deliberately
  so the Threads API has a public URL to fetch the image from.
