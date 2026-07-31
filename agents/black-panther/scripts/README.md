# Black Panther Scripts

## Setup

```bash
cd agents/black-panther/scripts
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys (see "Getting Instagram credentials" below)
```

## `daily_post.py` — fully automatic daily posting (GitHub Actions)

Generates one Instagram feed post (caption + poster) and publishes it — no human review. Reads
creds from environment vars or `.env`.

```bash
python daily_post.py --dry-run   # generate + render only (safe test, needs ANTHROPIC_API_KEY)
python daily_post.py             # generate + POST today's post
```

### Duty rule

**Post once a day, every post with a poster.** Instagram has no text-only post type, so unlike
Blue Hulk/Hulk there's no fallback branch — if the poster can't be rendered or pushed, the run
skips posting entirely for that day rather than publishing something broken, and prints a `NOTE:`
line so a missed day is never silent.

Claude picks the day's topic from `../config/topics.yaml` (same finance/trading/crypto scope as
Hulk and Blue Hulk) and writes the caption and the poster's four text slots (top label / headline
/ body / footer) in one call, so both share the same hook — see
`../persona/black-panther-system-prompt.md` for voice and caption structure, and
[`../../design/poster-style-guide.md`](../../design/poster-style-guide.md) for the locked poster
style (shared with Hulk/Blue Hulk).

**Unlike Facebook, the Instagram Graph API requires a publicly reachable image URL — it won't
accept a local file upload** (same constraint as Threads). The rendered PNG
(`posted_assets/black-panther-poster.png`, overwritten daily) is committed and pushed to this
repo, and its `raw.githubusercontent.com` URL is what actually gets posted — including the
fetchability-poll fix already proven on Hulk's Threads pipeline (raw GitHub URLs can lag a few
seconds behind a fresh push).

Preview a poster anytime without touching Instagram or git:
```bash
python render_poster.py "BTC — testing resistance" "Most traders blow up the same way" \
  "Position size kills more accounts than bad ideas." "What's your leverage lesson?"
```

**Scheduled in the cloud** via [`.github/workflows/black-panther-daily.yml`](../../../.github/workflows/black-panther-daily.yml)
(runs daily at 13:00 UTC = 9pm Malaysia; change the `cron:` to reschedule). To activate:

1. This workflow only runs the schedule from the repo's **default branch** — merge this branch into `main` first.
2. Add three **repository secrets** (GitHub → Settings → Secrets and variables → Actions → New repository secret):
   - `ANTHROPIC_API_KEY_3` — a dedicated Anthropic key for Black Panther (kept separate from Blue Hulk's/Hulk's keys for billing clarity, same pattern as Hulk's `ANTHROPIC_API_KEY_2`)
   - `IG_USER_ID` — your Instagram Business Account ID (see below for how to get it)
   - `IG_ACCESS_TOKEN` — a Page access token with the Instagram scopes added (see below)
3. The workflow needs `contents: write` permission to commit the poster PNG and post log — already set in the workflow file.
4. Test it immediately via **Actions tab → Black Panther daily post → Run workflow**, then check your Instagram feed.

## `collect_metrics.py` — performance dashboard data

Every `daily_post.py` publish is logged to `metrics/post_log.jsonl` (post id, date, topic hint).
`collect_metrics.py` reads that log, calls the Graph API for each post's current
`like_count`/`comments_count` (no extra permission needed beyond publishing) plus best-effort
impressions/reach/saved via Insights (metric availability varies by account — silently degrades
to `null` rather than failing), and appends a timestamped snapshot per post to
`metrics/history.jsonl`, then commits and pushes both files.

```bash
python collect_metrics.py   # needs IG_ACCESS_TOKEN in .env
```

Scheduled in the cloud via [`.github/workflows/metrics-collect.yml`](../../../.github/workflows/metrics-collect.yml)
(runs once daily, after the day's post has had a few hours to accrue engagement) — reuses the
same `IG_ACCESS_TOKEN` secret already wired for `daily_post.py`, no new secrets needed.

## Getting Instagram credentials (`IG_USER_ID`, `IG_ACCESS_TOKEN`)

Instagram posting rides on the **same Meta app and Facebook Page setup already created for Blue
Hulk** — you're extending it, not starting over. The Instagram Graph API is free.

1. **Your Instagram account must be a Business or Creator account** (not Personal) — check in the
   Instagram app: Settings → Account type and tools → switch if needed.
2. **Link it to a Facebook Page.** In the Instagram app: Settings → Account → Linked accounts →
   Facebook, and connect it to the same Page you use for Blue Hulk (or a different Page — either
   works, as long as it's a Page you're admin on and the app you created earlier can access).
3. **Add the Instagram scopes to your existing Meta app.** Go back to
   [Graph API Explorer](https://developers.facebook.com/tools/explorer), select the same app you
   used for Blue Hulk, click **Generate Access Token**, and this time grant these permissions —
   your existing `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, **plus**:
   - `instagram_basic`
   - `instagram_content_publish`
4. **Exchange for a long-lived user token, then a Page token** — identical steps to Blue Hulk's
   setup (see its README's "Getting Facebook credentials" section for the exact `GET` calls):
   short-lived token → `oauth/access_token?grant_type=fb_exchange_token` → long-lived user token →
   `/me/accounts` → Page token. **This new Page token now covers both Facebook and Instagram
   posting** — you can reuse the same value for `FB_PAGE_ACCESS_TOKEN` and `IG_ACCESS_TOKEN` if
   you want one token instead of two, or keep Blue Hulk's token as-is and use this new one only
   for `IG_ACCESS_TOKEN`.
5. **Get your Instagram Business Account ID:**

   ```
   GET https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token={PAGE_TOKEN}
   ```

   The response's `instagram_business_account.id` is your `IG_USER_ID`.
6. Put that `id` → `IG_USER_ID` and the Page token → `IG_ACCESS_TOKEN` in `.env`.
7. **Test**: `python daily_post.py --dry-run` first (no credentials needed for the render-only
   path beyond `ANTHROPIC_API_KEY`), then `python daily_post.py` for a real post — check your
   Instagram feed, then delete it if it was just a test.

**App Review note:** same as Blue Hulk — as long as the app only posts to your own linked
Instagram account, Development Mode is enough, no App Review needed.

**Security:** the Page token is a credential — keep it only in `.env` (gitignored), never in
committed files or chat. If it leaks, invalidate it in the app dashboard and regenerate.

## Notes

- `drafts/` is gitignored so preview renders don't clutter the repo.
- `posted_assets/black-panther-poster.png` is **not** gitignored — `daily_post.py` commits it
  deliberately so the Instagram Graph API has a public URL to fetch the image from.
- TikTok is **not** covered here — it stays on Buffer (see `agents/black-panther/README.md`)
  since TikTok's Content Posting API requires a heavier app-review/business-verification process
  than Meta's.
