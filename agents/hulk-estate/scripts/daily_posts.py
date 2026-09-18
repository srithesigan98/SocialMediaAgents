#!/usr/bin/env python3
"""Draft and publish today's property posts from the spreadsheet.

    python daily_posts.py --dry-run          # draft only, print, publish nothing
    python daily_posts.py                    # draft, ask y/N, then publish
    python daily_posts.py --yes              # unattended (for cron) — no confirmation
    python daily_posts.py --count 1 --platform threads

Picks the least-recently-posted active listings that are out of cooldown, drafts a post for
each with generate_property_post, publishes, and records the post id in state/posted.json so
the reply bot knows which posts to watch.
"""
from __future__ import annotations

import argparse
import sys
import traceback

from dotenv import load_dotenv

import common
import generate_property_post as drafter
import platforms


def publish(platform: str, text: str, listing: dict) -> str | None:
    image_url = listing.get("image_url") or None
    if platform == "threads":
        return platforms.threads_publish(text, image_url=image_url)
    if platform == "instagram":
        if not image_url:
            print(f"  ! instagram skipped for {listing['ref']}: Instagram requires an image, "
                  f"and this row has no Image URL.")
            return None
        return platforms.instagram_publish(text, image_url)
    raise ValueError(platform)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=None, help="How many listings (default: config posts_per_day)")
    parser.add_argument("--platform", action="append", choices=["threads", "instagram"],
                        help="Override configured platforms; repeatable")
    parser.add_argument("--framework", choices=drafter.frameworks(), default=None)
    parser.add_argument("--dry-run", action="store_true", help="Draft and print only")
    parser.add_argument("--yes", action="store_true", help="Publish without confirmation (cron)")
    args = parser.parse_args()

    load_dotenv(drafter.HERE / ".env")
    cfg = common.load_config()

    count = args.count if args.count is not None else int(cfg["schedule"]["posts_per_day"])
    platform_list = args.platform or cfg["schedule"]["platforms"]

    listings = common.pick_listings(cfg, count)
    if not listings:
        print("Nothing to post: every active listing is still inside its cooldown window.")
        return

    failures = 0
    for listing in listings:
        print(f"\n=== {listing['ref']} — {listing.get('title', '')} ===")
        for platform in platform_list:
            try:
                text = drafter.generate(listing, args.framework, platform, cfg)
            except Exception as exc:  # drafting failure shouldn't kill the whole run
                failures += 1
                print(f"  ! draft failed for {platform}: {exc}")
                continue

            print(f"--- {platform} ({len(text)} chars) ---\n{text}\n")
            drafter.save_draft(text, listing, platform, args.framework)

            if args.dry_run:
                continue
            if not args.yes and input(f"Publish to {platform}? [y/N] ").strip().lower() != "y":
                print("  skipped.")
                continue
            try:
                post_id = publish(platform, text, listing)
            except Exception:
                failures += 1
                print(f"  ! publish to {platform} failed:\n{traceback.format_exc()}")
                continue
            if post_id:
                common.mark_posted(listing["ref"], platform, post_id)
                print(f"  published to {platform}: {post_id}")

    if failures:
        sys.exit(f"\nFinished with {failures} failure(s) — see above.")


if __name__ == "__main__":
    main()
