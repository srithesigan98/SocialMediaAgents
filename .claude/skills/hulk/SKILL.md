---
name: hulk
description: Hulk — the Threads + Instagram content agent, run per brand profile. `senang-homes` posts real-estate listings from a spreadsheet (two a day) with generated poster images and auto-replies to commenters with a WhatsApp closing link; `tansri-millionaires` posts finance/trading/crypto. Use when the user wants to post or draft property listings or finance content, set up or run the daily posting schedule, generate a property poster, pull property details out of Google Drive into the listings sheet, or handle comments on those posts.
---

# Hulk

One posting engine, several brands. Everything lives in `agents/hulk/`.

| Profile | Brand | Scope | Content source |
|---|---|---|---|
| `senang-homes` | Senang Homes | real estate, Threads + Instagram | the listings spreadsheet |
| `tansri-millionaires` | TanSri \| Millionaires | finance/trading/crypto, Threads | a topic you give it |

**Always know which profile you're on**, and never mix them: the finance persona and its
`config/topics.yaml` explicitly deny property content, and the property persona denies trading
content. Pass `--profile` on every script call.

## Before doing anything

Read the profile's `agents/hulk/profiles/<profile>/profile.yaml`, then the persona and playbook
it points at.

## Drafting a property post by hand

Load the listing row, pick a framework from `profiles/senang-homes/templates/`, follow
`profiles/senang-homes/persona.md`. Non-negotiable:

- **Every fact comes from the row.** No estimated prices, no invented features, no flattering
  rounding. A missing field is dropped, not guessed.
- **No guarantees** about appreciation, rental occupancy, or loan approval.
- **No invented scarcity** ("last unit", "today only") unless a sheet column says so.
- The post **ends with the CTA line verbatim**, carrying that property's wa.me link.
- Threads ≤ 500 characters; Instagram caption ≤ ~800.

## Running the scripts

From `agents/hulk/scripts/` (venv + `.env` set up — see its README):

| Task | Command |
|---|---|
| Check the sheet loads | `python -c "import common; c=common.load_config('senang-homes'); print([l['ref'] for l in common.active_listings(c)])"` |
| Render a poster | `python make_poster.py HE-001 --profile senang-homes` |
| Draft one post | `python generate_property_post.py HE-001 --framework yield_math` |
| Today's two posts, no publishing | `python daily_posts.py --profile senang-homes --dry-run` |
| Today's two posts, with confirmation | `python daily_posts.py --profile senang-homes` |
| Answer new comments | `python reply_bot.py --profile senang-homes --dry-run` then without `--dry-run` |
| Finance post (reviewed flow) | `python generate_draft.py "<topic>"` then `post_to_threads.py` |

Always run `--dry-run` first and show the user the drafts before anything is published.

## Images

Three routes, chosen by `poster.mode` in the profile:

- **`auto`** — `make_poster.py` renders a PNG locally. Use this for scheduled posting; it is the
  only mode that works inside cron.
- **`canva`** — you generate it in this session with the Canva connector, using the locked style
  spec in `agents/design/poster-style-guide.md` as the base of the `generate-design` query, with
  the property's price, title, location and highlight swapped into the content slots. Export it,
  then paste the resulting URL into that row's `Image URL` column so the poster survives past
  this session.
- **`sheet`** — the row already has real photography. Always prefer this when it exists; a real
  photo of the property outperforms any generated poster.

Meta accepts only a **publicly reachable URL** for images, never a file upload — so a locally
rendered poster is unusable until `poster.public_base_url` points at wherever those files are
hosted. Say this plainly rather than letting a post silently go out text-only.

## Google Drive property details

When the property data is in Drive rather than a clean sheet, you do the ingestion — the scripts
can't, and a folder of documents and photos needs judgement. Read the Drive files with the Drive
connector, extract one row per property matching the `listings.columns` headers, and write them
into the listings CSV (or tell the user what to paste into their Google Sheet). Never invent a
field that isn't in the source documents; leave it blank instead.

## Platform limits to state plainly if asked

- Threads has no DM API — commenters get a **public** reply with the WhatsApp link. No tool can
  auto-DM on Threads.
- Instagram private replies (DMs) are one per comment, within 7 days of it, and need App Review
  to reach anyone outside the app's testers.
- Instagram cannot publish a caption without an image.

## Never

- Post without the user having seen the draft, unless they explicitly set up unattended cron.
- Put credentials, tokens, or the WhatsApp number into a committed file — those go in `.env`.
- Blend the two profiles' content, personas, or credentials.
