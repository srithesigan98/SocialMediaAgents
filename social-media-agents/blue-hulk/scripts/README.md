# Blue Hulk Scripts

## Setup

```bash
cd social-media-agents/blue-hulk/scripts
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
