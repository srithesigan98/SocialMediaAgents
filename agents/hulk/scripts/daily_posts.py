#!/usr/bin/env python3
"""Draft and publish today's property posts from the spreadsheet, with a poster image.

    python daily_posts.py --dry-run                      # draft + render poster, publish nothing
    python daily_posts.py                                # draft, ask y/N, then publish
    python daily_posts.py --yes                          # unattended (for cron)
    python daily_posts.py --profile senang-homes --count 1 --platform threads

Picks the least-recently-posted active listings that are out of cooldown, drafts a post for
each with generate_property_post, publishes, and records the post id in state/posted.json so
the reply bot knows which posts to watch.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

import common
import generate_area_post as area_drafter
import generate_property_post as drafter
import make_poster
import platforms

# Windows consoles default to cp1252; make emoji/curly-quote output (e.g. the WhatsApp CTA) safe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def commit_poster(path: Path) -> None:
    """Commit + push the rendered poster before we try to attach it, so its
    raw.githubusercontent.com URL is actually live by the time Meta's servers fetch it. Mirrors
    the pattern in agents/blue-hulk/scripts/daily_post.py's log_publish(). A failure here must
    never kill the run — it just means posting falls back to text-only, same as an unset
    poster.public_base_url."""
    repo_root = common.AGENT_DIR.parent.parent
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        subprocess.run(["git", "add", str(path)], cwd=repo_root, check=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"hulk: poster for {path.stem}"],
            cwd=repo_root, capture_output=True, text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            raise RuntimeError(f"git commit failed: {commit.stdout}\n{commit.stderr}")
        if commit.returncode == 0:
            subprocess.run(["git", "push", "origin", branch], cwd=repo_root, check=True)
    except Exception as e:
        print(f"  ! could not commit poster to git: {e}")


def poster_url(cfg: dict, listing: dict, dry_run: bool = False) -> str | None:
    """Resolve the image for this post, per the profile's poster.mode.

    Meta requires a PUBLICLY reachable URL for both Threads and Instagram images — neither API
    accepts a file upload — so a locally rendered poster is only usable once poster.
    public_base_url points at wherever those files are served from.
    """
    mode = cfg.get("poster", {}).get("mode", "sheet")
    sheet_url = listing.get("image_url") or None

    if mode == "none":
        return None
    if mode in ("sheet", "canva"):
        # canva posters are generated in a Claude session and pasted into the sheet's Image URL
        # column, so both modes read the same place at posting time.
        return sheet_url
    if mode == "auto":
        if sheet_url:
            return sheet_url  # a hand-made image in the sheet always wins over a generated one
        path = make_poster.render(cfg, listing)
        url = make_poster.public_url(cfg, path)
        if url and not dry_run:
            commit_poster(path)  # must be live at the URL before we try to attach it
        elif not url:
            print(f"  ! poster rendered to {path} but poster.public_base_url is empty, "
                  f"so it can't be attached — posting text-only.")
        return url
    raise ValueError(f"Unknown poster.mode: {mode!r}")


def publish(cfg: dict, platform: str, text: str, image_url: str | None) -> str | None:
    if platform == "threads":
        return platforms.threads_publish(cfg, text, image_url=image_url)
    if platform == "instagram":
        if not image_url:
            print("  ! instagram skipped: Instagram cannot publish a caption without an image.")
            return None
        return platforms.instagram_publish(cfg, text, image_url)
    raise ValueError(platform)


def run_area_post(cfg: dict, platform_list: list[str], args) -> None:
    """Draft + publish an area/market-comparison carousel — real building photos from 2+ areas
    side by side (carousels get meaningfully more engagement than a single image), with the
    price/sqft + lifestyle analysis as the shared caption. See generate_area_post.py."""
    stats = area_drafter.pick_areas(cfg, args.area_count)
    if not stats:
        print("Nothing to post: not enough listings with parseable price/sqft data per area.")
        return
    print("Comparing: " + ", ".join(s["area"] for s in stats))

    photos = area_drafter.area_photo_urls(cfg, stats)
    if len(photos) < 2:
        print(f"  ! only {len(photos)} area photo(s) found (need >=2 for a carousel) — skipping.")
        return

    failures = 0
    for platform in platform_list:
        try:
            text = area_drafter.generate(stats, platform, cfg)
        except Exception as exc:
            failures += 1
            print(f"  ! draft failed for {platform}: {exc}")
            continue

        print(f"--- {platform} ({len(text)} chars, {len(photos)} photos) ---\n{text}\n")
        area_drafter.save_draft(cfg, text, stats, platform)

        if args.dry_run:
            continue
        if not args.yes and input(f"Publish carousel to {platform}? [y/N] ").strip().lower() != "y":
            print("  skipped.")
            continue
        try:
            if platform == "threads":
                post_id = platforms.threads_publish_carousel(cfg, text, photos)
            elif platform == "instagram":
                post_id = platforms.instagram_publish_carousel(cfg, text, photos)
            else:
                raise ValueError(platform)
        except Exception:
            failures += 1
            print(f"  ! publish to {platform} failed:\n{traceback.format_exc()}")
            continue
        print(f"  published carousel to {platform}: {post_id}")

    if failures:
        sys.exit(f"\nFinished with {failures} failure(s) — see above.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=None, help="Hulk profile (default: HULK_PROFILE or senang-homes)")
    parser.add_argument("--count", type=int, default=None, help="How many listings (default: profile posts_per_day)")
    parser.add_argument("--platform", action="append", choices=["threads", "instagram"],
                        help="Override configured platforms; repeatable")
    parser.add_argument("--framework", default=None)
    parser.add_argument("--area-post", action="store_true",
                        help="Post an area/market price-per-sqft comparison (carousel) instead of single listings")
    parser.add_argument("--area-count", type=int, default=2, help="How many areas to compare, with --area-post")
    parser.add_argument("--dry-run", action="store_true", help="Draft and print only")
    parser.add_argument("--yes", action="store_true", help="Publish without confirmation (cron)")
    args = parser.parse_args()

    load_dotenv(drafter.HERE / ".env")
    cfg = common.load_config(args.profile)
    if args.framework and args.framework not in drafter.frameworks(cfg):
        sys.exit(f"Unknown framework. Options: {', '.join(drafter.frameworks(cfg))}")
    print(f"Profile: {cfg['_profile']} ({cfg.get('name', '')})")

    platform_list = args.platform or cfg["schedule"]["platforms"]

    if args.area_post:
        run_area_post(cfg, platform_list, args)
        return

    count = args.count if args.count is not None else int(cfg["schedule"]["posts_per_day"])
    listings = common.pick_listings(cfg, count)
    if not listings:
        print("Nothing to post: every active listing is still inside its cooldown window.")
        return

    failures = 0
    for listing in listings:
        print(f"\n=== {listing['ref']} — {listing.get('title', '')} ===")
        try:
            image_url = poster_url(cfg, listing, dry_run=args.dry_run)
        except Exception:
            failures += 1
            print(f"  ! poster generation failed:\n{traceback.format_exc()}")
            image_url = None
        if image_url:
            print(f"  image: {image_url}")

        for platform in platform_list:
            try:
                text = drafter.generate(listing, args.framework, platform, cfg)
            except Exception as exc:  # drafting failure shouldn't kill the whole run
                failures += 1
                print(f"  ! draft failed for {platform}: {exc}")
                continue

            print(f"--- {platform} ({len(text)} chars) ---\n{text}\n")
            drafter.save_draft(cfg, text, listing, platform, args.framework)

            if args.dry_run:
                continue
            if not args.yes and input(f"Publish to {platform}? [y/N] ").strip().lower() != "y":
                print("  skipped.")
                continue
            try:
                post_id = publish(cfg, platform, text, image_url)
            except Exception:
                failures += 1
                print(f"  ! publish to {platform} failed:\n{traceback.format_exc()}")
                continue
            if post_id:
                common.mark_posted(cfg, listing["ref"], platform, post_id)
                print(f"  published to {platform}: {post_id}")

    if failures:
        sys.exit(f"\nFinished with {failures} failure(s) — see above.")


if __name__ == "__main__":
    main()
