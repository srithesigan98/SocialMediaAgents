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

- Nothing here auto-posts on a schedule. If you want scheduled posting later, wrap
  `post_to_threads.py` in a cron job / scheduler once you're comfortable with the review flow.
- `drafts/` is gitignored so review notes and generated text don't clutter the repo.
