# Hulk Estate 🏠 — Real-estate Threads + Instagram agent

Hulk Estate is the real-estate arm of Hulk. It reads your property spreadsheet, posts **two
marketing posts a day** to Threads and Instagram, and **auto-responds to every comment** with a
prefilled WhatsApp closing link for that exact property.

It is a **separate agent from Hulk**, on purpose: Hulk's persona and
[`config/topics.yaml`](../hulk/config/topics.yaml) scope it *exclusively* to
finance/trading/crypto and explicitly deny everything else, so pouring property content into it
would break the voice it was researched and tuned for. Hulk Estate reuses the same machinery
(Claude drafting → review → Threads Graph API) against a different account, persona and sheet.
Hulk itself is untouched.

## Folder guide

| Path | Purpose |
|---|---|
| [`persona/hulk-estate-system-prompt.md`](./persona/hulk-estate-system-prompt.md) | Voice, scope, and the hard rules — never invent a fact, never guarantee returns, always keep the CTA line. |
| [`config/agent.yaml`](./config/agent.yaml) | Everything you tune: spreadsheet source + column mapping, schedule, WhatsApp number and prefill, reply intents. |
| [`config/listings.example.csv`](./config/listings.example.csv) | The expected sheet shape. Replace with (or map to) your own. |
| [`templates/`](./templates) | Four post frameworks: price anchor, yield math, location first, quick spec drop. |
| [`scripts/`](./scripts) | The runnable pieces — see [`scripts/README.md`](./scripts/README.md). |

## The loop

```
your spreadsheet
      │
      ▼
 pick_listings()          least-recently-posted active rows, cooldown_days apart
      │
      ▼
 generate_property_post   Claude + persona + framework, facts strictly from the row
      │                   CTA line with wa.me/<number>?text=<prefilled, per property>
      ▼
 daily_posts.py           publish → Threads (text or image) + Instagram (needs an image)
      │                   records post ids in state/posted.json
      ▼
 reply_bot.py             reads comments on those posts
                          keyword intent → per-property reply
                          Instagram: DM + public reply · Threads: public reply
                          state/replied.json prevents double-replies
```

## Quick start

```bash
cd scripts
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # add API keys
# edit ../config/agent.yaml: listings source/columns, whatsapp.number
python daily_posts.py --dry-run    # see two drafts, publish nothing
python reply_bot.py --dry-run      # see what it would reply
```

Then cron the two posting times and the reply poller — commands in
[`scripts/README.md`](./scripts/README.md).

## Platform limits worth knowing before you rely on this

- **Threads has no DM API.** No tool — this one, ManyChat, or a self-hosted one — can auto-DM
  someone who comments on a Thread. Hulk Estate replies publicly under the comment with the
  WhatsApp link, which is the closest thing the platform permits.
- **Instagram private replies** (the real DM) are allowed once per comment and only within
  **7 days** of that comment.
- **Instagram posts need an image.** Rows with no `Image URL` are posted to Threads only.
- Meta tokens expire every 60 days and need refreshing.
