# The Watcher 👁️

**Short-form video review agent** for TanSri | Millionaires (@tan_srithesigan).

- **Role:** Video review + rebuild
- **Platforms:** TikTok · Instagram · Facebook · YouTube (+ local files)
- **Status:** ✅ Built & runnable
- **Skill:** [`.claude/skills/the-watcher/SKILL.md`](../../.claude/skills/the-watcher/SKILL.md)

## Task
Watches a video, then returns a full performance review benchmarked against top
trading/finance creators — plus a shot-by-shot rebuild so Sri can recreate it as
higher-view content.

## How it works
Built on the vendored [`watch`](../../.claude/skills/watch) skill
(from [bradautomates/claude-video](https://github.com/bradautomates/claude-video), MIT):
downloads with `yt-dlp`, extracts frames with `ffmpeg`, transcribes with Whisper.
The Watcher layers a trading-content rubric and replication playbook on top.

**Pipeline:** Watch → Score → Review → Rebuild

## Files in this folder
- [`review-rubric.md`](review-rubric.md) — 8-dimension scorecard (/40 + verdict bands)
- [`benchmarks.md`](benchmarks.md) — 2026 short-form benchmarks (retention, hooks, captions…)
- [`replication-playbook.md`](replication-playbook.md) — how to rebuild a video for more views

## Setup & usage
```bash
bash setup.sh        # installs yt-dlp + ffmpeg (re-run per web session)
```
```
/the-watcher https://www.tiktok.com/@tan_srithesigan/video/1234567890
/the-watcher ./my-reel.mp4 focus on the hook and captions
```
Optional: add `GROQ_API_KEY` or `OPENAI_API_KEY` to `~/.config/watch/.env` to
transcribe caption-less videos.

Feeds: ♻️ Repurposer and the posting agents (hooks, scripts, rebuild briefs).
