#!/usr/bin/env python3
"""Post the next ready animated video from profiles/<profile>/video_plan.yaml (runs in GitHub Actions).

    python post_video.py --profile senang-homes --dry-run
    python post_video.py --profile senang-homes --yes        # what the Tue/Fri workflow runs

Picks the earliest calendar entry with status "ready" whose date has arrived (Malaysia time) and that
hasn't been posted, reads its project's post.yaml (video URL, topic cover, captions), publishes to
the profile's video_platforms (Threads, Instagram Reel with the cover as cover_url, TikTok through
Buffer) and marks it "posted" in the plan. Producing
the video (script, render, cover, upload) happens earlier — see formats/animated-explainer.yaml.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

import common
import make_poster
import platforms

HERE = Path(__file__).resolve().parent
MYT = timezone(timedelta(hours=8))


def due_entry(plan: dict, posted: dict, today: str) -> dict | None:
    entries = [e for month in plan.get("calendar", {}).values() for e in month]
    ready = [e for e in entries if e.get("status") == "ready" and str(e["date"]) <= today
             and f"video-{e['slug']}" not in posted]
    return min(ready, key=lambda e: str(e["date"])) if ready else None


def mark_plan_posted(plan_path: Path, slug: str) -> None:
    text = plan_path.read_text(encoding="utf-8")
    pattern = re.compile(r"(slug: " + re.escape(slug) + r",[^}]*?status: )ready\}", re.S)
    new, n = pattern.subn(r"\1posted}", text, count=1)
    if n:
        plan_path.write_text(new, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="senang-homes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    load_dotenv(HERE / ".env")
    cfg = common.load_config(args.profile)
    plan_path = common.profile_path(cfg, "video_plan.yaml")
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    posted = common.read_state(cfg, "posted").get("listings", {})
    today = datetime.now(MYT).date().isoformat()
    entry = due_entry(plan, posted, today)
    if entry is None:
        print(f"No ready video due on or before {today}.")
        return

    post = yaml.safe_load((HERE.parent / entry["project"] / "post.yaml").read_text(encoding="utf-8"))
    ref = f"video-{entry['slug']}"
    cover = make_poster.public_url(cfg, common.POSTERS_DIR / post["cover"])
    cta = common.cta_line(cfg, {"title": "a property", "ref": ""})
    print(f"Video: {entry['title']} ({entry['date']})\n  video {post['video_url']}\n  cover {cover}")

    failures, done = 0, 0
    for platform in cfg.get("video_platforms") or cfg["schedule"]["platforms"]:
        if platform == "tiktok" and not all(os.environ.get(cfg["credentials"][k], "").strip()
                                            for k in ("buffer_api_key", "tiktok_channel_id")):
            print("--- tiktok skipped: Buffer API key / TikTok channel id not set ---\n")
            continue
        caption = post["captions"].get(platform) or post["captions"]["instagram"]  # TikTok reuses IG's
        text = caption.rstrip() + "\n\n" + cta
        print(f"--- {platform} ({len(text)} chars) ---\n{text}\n")
        if args.dry_run or (not args.yes and input(f"Publish to {platform}? [y/N] ").strip().lower() != "y"):
            continue
        try:
            if platform == "threads":
                pid = platforms.threads_publish_video(cfg, text, post["video_url"])
            elif platform == "tiktok":
                pid = platforms.tiktok_publish_video(cfg, text, post["video_url"])
            else:
                pid = platforms.instagram_publish_reel(cfg, text, post["video_url"], cover_url=cover)
        except Exception as exc:
            failures += 1
            print(f"  ! {platform} failed: {str(exc)[:300]}")
            continue
        common.mark_posted(cfg, ref, platform, pid)
        done += 1
        print(f"  published to {platform}: {pid}")
    if done:  # never post the same video twice, even if one platform failed
        mark_plan_posted(plan_path, entry["slug"])
    if failures:
        sys.exit(f"Finished with {failures} failure(s).")


if __name__ == "__main__":
    main()
