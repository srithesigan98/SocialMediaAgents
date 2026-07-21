# SocialMediaAgents

Automated social-media agents.

## Agents

Each agent has its own folder under [`agents/`](agents) (docs + assets); the
runnable skills live under `.claude/skills/`.

- **Hulk** 🟢 — Threads posting agent → [`agents/hulk`](agents/hulk)
- **Blue Hulk** 🔵 — Facebook posting agent → [`agents/blue-hulk`](agents/blue-hulk)
- **Black Panther** 🐾 — Instagram + TikTok posting agent (stub) → [`agents/black-panther`](agents/black-panther)
- **Repurposer** ♻️ — one video → platform-tailored variants (stub) → [`agents/repurposer`](agents/repurposer)
- **The Watcher** 👁️ — short-form video review agent (built) → [`agents/the-watcher`](agents/the-watcher)

The full operating map is in [`docs/growth-system.md`](docs/growth-system.md) —
the 2026 Social Media Growth System with each branch tagged by agent, coverage
gaps, a build roadmap, and filled forex/gold audience research.

---

## The Watcher

Watches a social video (TikTok, Instagram Reels, Facebook, YouTube Shorts, or a
local file), then returns a **full performance review** benchmarked against top
trading/finance creators — plus a **shot-by-shot rebuild** so Sri Thesigan
(@tan_srithesigan) can recreate it as higher-view content.

It's built on the [`claude-video`](https://github.com/bradautomates/claude-video)
`/watch` skill (MIT), vendored into `.claude/skills/watch/`, which downloads the
video with `yt-dlp`, extracts frames with `ffmpeg`, and transcribes audio with
Whisper. The Watcher layers a trading-content review rubric and replication
playbook on top of it.

### What it gives you
For each video: a snapshot, an 8-point scorecard (`/40` + verdict), a hook
autopsy, what's working, what's killing views, and a ready-to-shoot rebuild
(3 rewritten hooks, tightened 21–34s script, caption + hashtags, visual plan,
CTA, and a named repeatable format). Multiple URLs → per-video reviews plus a
"patterns across your account" summary.

### Setup
Install the runtime deps once per environment (the web container is ephemeral,
so re-run it in a fresh session):

```bash
bash setup.sh
```

That installs `yt-dlp` + `ffmpeg`. Whisper transcription is optional — add
`GROQ_API_KEY` or `OPENAI_API_KEY` to `~/.config/watch/.env` only if you need to
review videos that have no captions. Frames + captions work without a key.

### Usage
In a Claude Code session in this repo:

```
/the-watcher https://www.tiktok.com/@tan_srithesigan/video/1234567890
/the-watcher https://youtube.com/shorts/abc123 focus on the hook and captions
/the-watcher ./my-reel.mp4
```

Give it several URLs to get a cross-account pattern review.

> Platform note: `yt-dlp` handles public TikTok/IG/Facebook posts, but those
> platforms rate-limit and change often. If a download fails, The Watcher will
> say so and ask you to upload the file directly or paste the video's first
> spoken line, on-screen text, length, and current metrics — then review from
> that. It never fabricates frames, transcripts, or numbers.

### Layout
```
.claude/skills/
  watch/                     # vendored claude-video /watch skill (MIT)
  the-watcher/SKILL.md       # The Watcher orchestrator
agents/the-watcher/
  review-rubric.md           # 8-dimension scoring rubric
  benchmarks.md              # 2026 short-form benchmarks (retention, hooks, captions…)
  replication-playbook.md    # how to rebuild a video for more views
setup.sh                     # installs yt-dlp + ffmpeg
```

The Watcher's benchmarks are drawn from public creator-performance data
(Feedspot, Traders Union, Socialync, OpusClip, Levitate Media, Kapwing);
sources are listed at the bottom of `agents/the-watcher/benchmarks.md`.
