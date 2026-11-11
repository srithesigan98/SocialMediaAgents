#!/usr/bin/env python3
"""Post the next item of profiles/<profile>/tiktok_queue.yaml to TikTok (runs in GitHub Actions).

    python tiktok_backlog.py --profile senang-homes --dry-run
    python tiktok_backlog.py --profile senang-homes          # Sun/Mon/Wed/Thu/Sat 20:30 MYT

The queue holds every post published on Instagram/Threads before TikTok was added, already
rendered as 9:16 videos with a cover frame and music (build_tiktok_queue.py). Tue/Fri belong to
the new animated videos (post_video.py), so this fills the other five days, oldest post first.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

import common
import make_poster
import platforms

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="senang-homes")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_dotenv(HERE / ".env")
    cfg = common.load_config(args.profile)
    queue = yaml.safe_load(common.profile_path(cfg, "tiktok_queue.yaml").read_text(encoding="utf-8")) or []
    state = common.read_state(cfg, "posted")
    history = state.setdefault("listings", {})

    def done(ref: str) -> bool:
        return any(p["platform"].startswith("tiktok") for p in history.get(ref, {}).get("posts", []))

    item = next((i for i in queue if not done(i["ref"])), None)
    if item is None:
        print("TikTok queue is empty: every earlier post is on TikTok.")
        return

    url = make_poster.public_url(cfg, common.POSTERS_DIR / item["file"])
    print(f"{item['ref']} ({sum(not done(i['ref']) for i in queue)} left)\n  video {url}\n---\n{item['caption']}\n")
    if args.dry_run:
        return
    try:
        platform, post_id = "tiktok", platforms.tiktok_publish_video(
            cfg, item["caption"], url, ai_generated=item.get("ai_generated", False))
    except Exception as exc:
        # Recorded anyway so tomorrow moves on instead of retrying one broken item forever.
        platform, post_id = "tiktok_failed", str(exc)[:300]
    # Appended without touching last_posted (common.mark_posted would), so a TikTok repost doesn't
    # push the listing out of the Instagram/Threads rotation.
    history.setdefault(item["ref"], {}).setdefault("posts", []).append(
        {"platform": platform, "post_id": post_id, "at": common.now_utc().isoformat()})
    common.write_state(cfg, "posted", state)
    if platform != "tiktok":
        sys.exit(f"TikTok failed for {item['ref']}: {post_id}")
    print(f"  published to tiktok: {post_id}")


if __name__ == "__main__":
    main()
