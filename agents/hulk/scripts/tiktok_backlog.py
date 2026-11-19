#!/usr/bin/env python3
"""Post the next item of profiles/<profile>/tiktok_queue.yaml to TikTok (runs in GitHub Actions).

    python tiktok_backlog.py --profile senang-homes --dry-run
    python tiktok_backlog.py --profile senang-homes          # Sun/Mon/Wed/Thu/Sat 20:30 MYT

The queue holds every post published on Instagram/Threads before TikTok was added
(build_tiktok_queue.py): carousels as TikTok photo carousels, everything else as 9:16 videos with
a cover frame and music. Tue/Fri belong to the new animated videos (post_video.py), so this fills
the other five days, oldest post first.

Every item must clear tiktok_guard first (no prices or money amounts, TikTok Community Guidelines).
An item that fails is recorded as tiktok_skipped with the reasons and never re-checked; the run moves
on to the next item. If the check itself can't run, nothing is posted and the run fails (retried later).
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
import tiktok_guard

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

    def record(ref: str, platform: str, post_id: str) -> None:
        # Appended without touching last_posted (common.mark_posted would), so a TikTok entry doesn't
        # push the listing out of the Instagram/Threads rotation.
        history.setdefault(ref, {}).setdefault("posts", []).append(
            {"platform": platform, "post_id": post_id, "at": common.now_utc().isoformat()})
        common.write_state(cfg, "posted", state)

    for item in [i for i in queue if not done(i["ref"])]:
        media = [common.POSTERS_DIR / f for f in item.get("images") or [item["file"]]]
        try:
            found = tiktok_guard.problems(item["caption"], media)
        except tiktok_guard.CheckError as exc:
            sys.exit(f"Guideline check unavailable, nothing posted: {exc}")
        if found:
            print(f"- {item['ref']}: held back from TikTok\n    " + "\n    ".join(found))
            if not args.dry_run:
                record(item["ref"], "tiktok_skipped", "; ".join(found)[:500])
            continue

        urls = [make_poster.public_url(cfg, m) for m in media]
        print(f"{item['ref']}: cleared\n  " + "\n  ".join(urls) + f"\n---\n{item['caption']}\n")
        if args.dry_run:
            return
        try:
            if item.get("images"):   # carousels go out as TikTok photo carousels
                title = next((line.strip() for line in item["caption"].splitlines() if line.strip()), "")
                post_id = platforms.tiktok_publish_carousel(cfg, item["caption"], urls, title=title)
            else:
                post_id = platforms.tiktok_publish_video(
                    cfg, item["caption"], urls[0], ai_generated=item.get("ai_generated", False))
            platform = "tiktok"
        except Exception as exc:
            # Recorded anyway so the next run moves on instead of retrying one broken item forever.
            platform, post_id = "tiktok_failed", str(exc)[:300]
        record(item["ref"], platform, post_id)
        if platform != "tiktok":
            sys.exit(f"TikTok failed for {item['ref']}: {post_id}")
        print(f"  published to tiktok: {post_id}")
        return
    print("Nothing to post: every queued post is on TikTok or held back by the guideline check.")


if __name__ == "__main__":
    main()
