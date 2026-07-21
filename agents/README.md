# Agents

One folder per agent. The posting agents (Hulk, Blue Hulk) carry their full
implementation — persona, playbook, templates, config, scripts. The
skill-based agents (Black Panther, Repurposer, The Watcher) document behavior
here and keep their runnable skill under `.claude/skills/<name>/`.

| Agent | Folder | Skill | Role | Platform(s) | Status |
|---|---|---|---|---|---|
| 🟢 Hulk | [`hulk/`](hulk) | — (scripts in folder) | Content + posting | Threads | ✅ Built |
| 🔵 Blue Hulk | [`blue-hulk/`](blue-hulk) | — (scripts in folder) | Content + posting | Facebook | ✅ Built |
| 🐾 Black Panther | [`black-panther/`](black-panther) | `.claude/skills/black-panther` | Posting | Instagram · TikTok | 🟡 Stub |
| ♻️ Repurposer | [`repurposer/`](repurposer) | `.claude/skills/repurposer` | 1 → many | All | 🟡 Stub |
| 👁️ The Watcher | [`the-watcher/`](the-watcher) | `.claude/skills/the-watcher` | Video review | TikTok · IG · FB · YT | ✅ Built |

**Shared:** [`design/`](design) — Canva poster style guide used by Hulk and Blue Hulk.

See [`../docs/growth-system.md`](../docs/growth-system.md) for how these fit the
2026 Social Media Growth System, and the build roadmap for what's next
(Analytics agent, Red Hulk / YouTube Shorts).
