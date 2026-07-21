# Agents

One folder per agent. Each folder documents the agent; the runnable skill lives
under `.claude/skills/<name>/` so Claude Code can load it.

| Agent | Folder | Skill | Role | Platform(s) | Status |
|---|---|---|---|---|---|
| 🟢 Hulk | [`hulk/`](hulk) | — (external) | Posting | Threads | External |
| 🔵 Blue Hulk | [`blue-hulk/`](blue-hulk) | — (external) | Posting | Facebook | External |
| 🐾 Black Panther | [`black-panther/`](black-panther) | `.claude/skills/black-panther` | Posting | Instagram · TikTok | 🟡 Stub |
| ♻️ Repurposer | [`repurposer/`](repurposer) | `.claude/skills/repurposer` | 1 → many | All | 🟡 Stub |
| 👁️ The Watcher | [`the-watcher/`](the-watcher) | `.claude/skills/the-watcher` | Video review | TikTok · IG · FB · YT | ✅ Built |

See [`../docs/growth-system.md`](../docs/growth-system.md) for how these fit the
2026 Social Media Growth System, and the build roadmap for what's next
(Analytics agent, Red Hulk / YouTube Shorts).
