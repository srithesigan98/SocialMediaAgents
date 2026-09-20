# Black Panther 🐾

**Instagram + TikTok posting agent** for TanSri | Millionaires (@tan_srithesigan).

- **Role:** Posting
- **Platforms:** Instagram (self-hosted) · TikTok (via Buffer)
- **Status:** ✅ Instagram built (daily feed posts, fully automatic) · 🟡 TikTok stub (needs Buffer channel connected — see below)
- **Skill:** [`.claude/skills/black-panther/SKILL.md`](../../.claude/skills/black-panther/SKILL.md) (still governs the manual/Buffer posting flow for one-off or TikTok posts)
- **Scripts:** [`scripts/`](./scripts) (daily_post.py / collect_metrics.py — mirrors Hulk/Blue Hulk's architecture)

## Task
Two paths, split by what each platform's API actually allows:

1. **Instagram — fully automatic, self-hosted.** `scripts/daily_post.py` posts one feed post a
   day (Claude-written caption + a Pillow-rendered poster) straight to Instagram via the Graph
   API, using the same Meta app already set up for Blue Hulk. See
   [`scripts/README.md`](./scripts/README.md) for setup and duty rules.
2. **TikTok — via Buffer, still a stub.** TikTok's Content Posting API requires a heavier
   app-review/business-verification process than Meta's, so this stays on Buffer for now (see
   "Go live" below) rather than a self-hosted script.

## Abilities
- Draft platform-ready posts (from an idea, script, or Watcher rebuild)
- Curiosity-led captions + mixed hashtag sets (niche + geo + broad)
- Instagram: fully automatic daily posting (see `scripts/`)
- TikTok: queue / schedule via Buffer, once connected
- Confirm channel, time, and post text (for anything not automated)

## Go live (TikTok, via Buffer)
1. Connect a TikTok channel in **Buffer** (note: the free Buffer plan caps at 3 channels —
   Facebook and Threads already use 2, so this needs either an upgrade or freeing a slot).
2. Wire the skill's post step to Buffer `list_channels` / `create_post`.
3. Test with a single scheduled post before enabling the queue.

Feeds from: ♻️ Repurposer · 👁️ The Watcher (hooks/rebuilds) · 🎨 Canva (graphics).
