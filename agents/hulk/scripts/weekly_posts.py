#!/usr/bin/env python3
"""The two weekly posts that aren't a single sheet listing.

    python weekly_posts.py --tip --dry-run      # off-sheet buyer tip (campaigns/tips.yaml)
    python weekly_posts.py --recap --dry-run    # carousel of this week's posted listings
    python weekly_posts.py --tip --yes          # unattended (cron)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

import common
import daily_posts
import generate_property_post as drafter
import make_poster
import platforms

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

GENERIC = {"title": "a property", "ref": ""}  # WhatsApp prefill for posts not about one listing


def photo_pool(cfg: dict) -> list[str]:
    """Real project photos to put behind a tip — campaign photos in the repo, then the
    building photos already used for listings."""
    local = sorted(str(p) for p in common.profile_path(cfg, "campaigns").rglob("*.jpg"))
    return local + sorted(set(common.load_photo_overrides(cfg).values()))


def tip_caption(cfg: dict, topic: dict, platform: str) -> str:
    cta = common.cta_line(cfg, GENERIC)
    budget = drafter.LIMITS[platform] - len(cta) - 2
    prompt = "\n".join([
        f"Write one {platform} post for Malaysian home buyers on: {topic['hook']}.",
        "It must only explain and expand these points — no bank rates, laws, prices or market "
        "predictions beyond them, and nothing about a specific project:",
        *topic["bullets"],
        "",
        f"End by inviting people to comment \"{cfg['_tips']['cta_word']}\" for help with their own purchase.",
        f"Aim for about {int(budget * 0.8)} characters (hard maximum {budget}). Do NOT write a "
        "WhatsApp link or phone number — it's appended automatically.",
    ])
    persona = common.profile_path(cfg, cfg["persona"]).read_text(encoding="utf-8")
    resp = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]).messages.create(
        model=drafter.MODEL, max_tokens=800, thinking={"type": "disabled"}, system=persona,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if resp.stop_reason == "max_tokens" or len(text) < 100:
        raise ValueError("Tip caption came back truncated or empty.")
    text = f"{text}\n\n{cta}"
    if len(text) > drafter.LIMITS[platform]:
        raise ValueError(f"Tip caption is {len(text)} chars, over the {platform} limit.")
    return text


def run_tip(cfg: dict, platform_list: list[str], args) -> int:
    tips = yaml.safe_load(common.profile_path(cfg, "campaigns/tips.yaml").read_text(encoding="utf-8"))
    cfg["_tips"] = tips
    posted = common.read_state(cfg, "posted").get("listings", {})
    topics = tips["topics"]
    # Least recently used topic; never-posted ones first, in file order.
    topic = min(topics, key=lambda t: posted.get(f"tip-{t['key']}", {}).get("last_posted", ""))
    pool = photo_pool(cfg)
    photo = pool[topics.index(topic) * 3 % len(pool)] if pool else ""
    print(f"Tip: {topic['hook']}  (photo: {photo})")

    stem = common.POSTERS_DIR / f"{cfg['_profile']}-tip-{topic['key']}"

    def canvas(size=None):
        return make_poster.slide_canvas(cfg, photo, topic["hook"], lines=topic["bullets"],
                                        cta_word=tips["cta_word"], size=size)
    png = canvas().save_png(stem.with_suffix(".png"))
    mp4 = canvas((1080, 1920)).save_mp4(stem.with_suffix(".mp4"))
    image_url, video = (make_poster.public_url(cfg, p) for p in (png, mp4))
    if not args.dry_run:
        daily_posts.commit_poster(png)
        daily_posts.commit_poster(mp4)

    failures = 0
    for platform in platform_list:
        try:
            text = daily_posts.draft(tip_caption, cfg, topic, platform)
        except Exception as exc:
            failures += 1
            print(f"  ! caption failed for {platform}: {exc}")
            continue
        print(f"--- {platform} ({len(text)} chars) ---\n{text}\n")
        if args.dry_run or (not args.yes and input(f"Publish to {platform}? [y/N] ").strip().lower() != "y"):
            continue
        try:
            post_id = daily_posts.publish(cfg, platform, text, image_url, video)
        except Exception as exc:
            failures += 1
            print(f"  ! publish to {platform} failed: {exc}")
            continue
        common.mark_posted(cfg, f"tip-{topic['key']}", platform, post_id)
        print(f"  published to {platform}: {post_id}")
    return failures


def week_listings(cfg: dict) -> list[dict]:
    """Listings posted in the last 7 days, newest first — campaign posts count as their project."""
    listings = common.load_listings(cfg)
    by_ref = {l["ref"]: l for l in listings}
    seen, out = set(), []
    for post in common.recent_posts(cfg):
        if (datetime.now(timezone.utc) - datetime.fromisoformat(post["at"])).days >= 7:
            continue
        ref = post["ref"]
        item = by_ref.get(ref)
        if item is None and ref.startswith("campaign-"):
            name = ref.split("-")[1]
            path = common.profile_path(cfg, f"campaigns/{name}.yaml")
            if path.exists():
                project = yaml.safe_load(path.read_text(encoding="utf-8"))["project"].lower()
                item = next((l for l in listings if common.project_of(l) == project), None)
        if item and common.project_of(item) not in seen:
            seen.add(common.project_of(item))
            out.append(item)
    return out


def recap_caption(items: list[dict], platform: str, cfg: dict) -> str:
    """Built straight from sheet data, no model: a recap is a list of facts, and this keeps
    every number exactly as posted."""
    cta = common.cta_line(cfg, GENERIC)
    head = "This week at Senang Homes 👇 swipe through\n"
    lines = []
    for i, item in enumerate(items, 1):
        facts = make_poster.listing_facts(item)
        fact = facts.get("yield") or facts.get("psf") or facts.get("price")
        area = common._extract_area(item.get("location", ""))
        lines.append(f"{i}. {item['title']}, {area}" + (f" — {fact[0]} {fact[1].lower()}" if fact else ""))
    tail = "\nComment the project name for full details."
    while lines:
        text = "\n".join([head, *lines, tail, "", cta])
        if len(text) <= drafter.LIMITS[platform]:
            return text
        lines.pop()  # drop the oldest until it fits
    return "\n".join([head, tail, "", cta])


def run_recap(cfg: dict, platform_list: list[str], args) -> int:
    items = week_listings(cfg)[:9]  # cover + 9 = Meta's 10-slide carousel limit
    if not items:
        print("Nothing posted this week — no recap.")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    total = len(items) + 1
    cover = make_poster.render_slide(
        cfg, items[0].get("photo_url", ""), "This week at Senang Homes",
        common.POSTERS_DIR / f"{cfg['_profile']}-recap-{stamp}-0.png",
        lines=[f"{len(items)} projects · swipe >>"], page=1, total=total)
    paths = [cover]
    for i, item in enumerate(items, 2):  # re-rendered so the whole carousel has the new style
        c = make_poster.listing_canvas(cfg, item)
        c.corner(f"{i}/{total}")
        paths.append(c.save_png(common.POSTERS_DIR / f"{cfg['_profile']}-recap-{stamp}-{i - 1}.png"))
    urls = [make_poster.public_url(cfg, p) for p in paths]
    if not args.dry_run:
        for p in paths:
            daily_posts.commit_poster(p)
    print(f"Recap: {', '.join(i['title'] for i in items)}")

    failures = 0
    for platform in platform_list:
        text = recap_caption(items, platform, cfg)
        print(f"--- {platform} ({len(text)} chars, {len(paths)} slides) ---\n{text}\n")
        if args.dry_run or (not args.yes and input(f"Publish to {platform}? [y/N] ").strip().lower() != "y"):
            continue
        publish = platforms.threads_publish_carousel if platform == "threads" else platforms.instagram_publish_carousel
        try:
            post_id = publish(cfg, text, urls)
        except Exception as exc:
            failures += 1
            print(f"  ! publish to {platform} failed: {exc}")
            continue
        common.mark_posted(cfg, f"recap-{stamp}", platform, post_id)
        print(f"  published recap to {platform}: {post_id}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    kind = parser.add_mutually_exclusive_group(required=True)
    kind.add_argument("--tip", action="store_true")
    kind.add_argument("--recap", action="store_true")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--platform", action="append", choices=["threads", "instagram"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    load_dotenv(drafter.HERE / ".env")
    cfg = common.load_config(args.profile)
    platform_list = args.platform or cfg["schedule"]["platforms"]
    failures = (run_tip if args.tip else run_recap)(cfg, platform_list, args)
    if failures:
        sys.exit(f"Finished with {failures} failure(s).")


if __name__ == "__main__":
    main()
