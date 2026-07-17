# Blue Hulk — Finance/Trading/Crypto Facebook Agent

Blue Hulk is Hulk's sibling agent, scoped to the same topics (stock market, trading,
cryptocurrency) but built for **Facebook** instead of Threads: longer-form storytelling, stronger
CTAs, trader experience/war-stories, market-condition commentary, and trading psychology content,
plus the ability to generate poster/graphic versions of posts via Canva.

## Status

🚧 **In progress.** Creator research on trading-focused Facebook pages (including
`facebook.com/rowxer`, `facebook.com/HumbledTrader`, the creators named in
[directionsmag's top-crypto-traders-on-Facebook article](https://www.directionsmag.com/crypto/top-crypto-traders-facebook),
plus independently discovered pages) is running and will populate `persona/`, `playbook/`,
`templates/`, and `config/` the same way it did for Hulk.

## What's already here

- [`design/poster-style-guide.md`](./design/poster-style-guide.md) — Blue Hulk's poster-generation
  capability via Canva, including a locked visual style spec and workflow. This works today,
  independent of the text-content research still in progress.

## Planned structure (mirrors `../hulk/`)

| Path | Purpose |
|---|---|
| `persona/blue-hulk-system-prompt.md` | Identity, voice, scope, operating rules |
| `playbook/creator-research.md` | Raw findings on the Facebook creators studied |
| `playbook/content-playbook.md` | Distilled hooks, storytelling frameworks, CTA styles |
| `templates/` | Fill-in-the-blank post templates |
| `config/topics.yaml` | Topic allow/deny guard |
| `scripts/` | Draft generation + Facebook Graph API posting script |
