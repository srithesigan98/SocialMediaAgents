#!/usr/bin/env python3
"""Feature-carousel posts for a focus project, driven by profiles/<profile>/campaigns/<name>.yaml.

    python campaign_post.py khaya --dry-run     # render slides + draft captions, publish nothing
    python campaign_post.py khaya               # ...then ask y/N per platform
    python campaign_post.py khaya --yes         # unattended (cron)

Slides use repo-local photos next to the yaml; {placeholders} in slide text are filled from the
live sheet rows for the campaign's project. The caption may only use the yaml's `facts` list and
those sheet numbers — the brief is the source of truth, nothing gets invented.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

import requests
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


def money(v: float) -> str:
    return f"RM{v / 1e6:.2f}M" if v >= 1e6 else f"RM{v / 1000:,.0f}K"


def sheet_data(cfg: dict, project: str) -> tuple[dict, list[dict]]:
    rows = [l for l in common.active_listings(cfg) if common.project_of(l) == project.lower()]
    if not rows:
        raise SystemExit(f"No active sheet rows for project {project!r}.")
    n = common.parse_number
    prices = [p for p in (n(r.get("price", "")) for r in rows) if p]
    sizes = [s for s in (n(r.get("size", "")) for r in rows) if s]
    psfs = [p for p in (common.price_per_sqft(r) for r in rows) if p]
    rebates = Counter(r["highlight"] for r in rows if r.get("highlight"))
    return {
        "from_price": money(min(prices)) if prices else "",
        "psf_min": f"RM{min(psfs):,.0f}" if psfs else "",
        "psf_max": f"RM{max(psfs):,.0f}" if psfs else "",
        "min_size": f"{min(sizes):,.0f}" if sizes else "",
        "unit_count": str(len({r.get("unit_type") for r in rows if r.get("unit_type")})),
        "rebate": rebates.most_common(1)[0][0] if rebates else "",
    }, rows


def render_slides(cfg: dict, name: str, camp: dict, data: dict) -> list:
    folder = common.profile_path(cfg, f"campaigns/{name}")
    slides = camp["slides"]
    paths = []
    for i, s in enumerate(slides, 1):
        fill = lambda t: t.format(**data)  # noqa: E731
        paths.append(make_poster.render_slide(
            cfg, str(folder / s["photo"]), fill(s["hook"]),
            common.POSTERS_DIR / f"{cfg['_profile']}-campaign-{name}-{i}.png",
            tiles=[[fill(v), l] for v, l in s.get("tiles", [])],
            lines=[fill(l) for l in s.get("lines", []) if fill(l).strip("• ")],
            cta_word=camp.get("trigger_word") if s.get("cta") else None,
            page=i, total=len(slides),
        ))
    return paths


def caption(cfg: dict, camp: dict, data: dict, rows: list[dict], platform: str,
            angle: str | None = None) -> str:
    """Carousel caption, or — with `angle` — a Reel caption. Reel captions leave price out: the
    videos carry their own burned-in "from" price, and quoting a different one beside it reads
    as a mistake."""
    cta = common.cta_line(cfg, rows[0])
    budget = drafter.LIMITS[platform] - len(cta) - 2
    what = f"a Reel ({angle})" if angle else "a swipe-through carousel"
    price_line = [] if angle else [
        f"- Prices from {data['from_price']}, from {data['psf_min']}/sqft, {data['rebate']}"]
    prompt = "\n".join([
        f"Write one {platform} caption for {what} about {camp['project']}.",
        "Use ONLY these facts — no other claims about the project. Keep each fact's strength "
        "exactly as written: 'near' stays 'near' (never 'steps from' / 'next door'), and never "
        "link two facts with 'so'/'because' unless the fact itself says so. Copy unit types, names "
        "and numbers exactly — the video's own subject (e.g. 'Unit B') must never be merged into "
        "another fact such as which types suit Airbnb:",
        *[f"- {f}" for f in camp["facts"]],
        *price_line,
        "",
        "Open with a one-line hook that restates ONE listed fact (no new framing such as 'zero "
        "restrictions', 'guaranteed', 'Airbnb-titled'), then the strongest 4-6 facts as short "
        "lines. Tell people to "
        f"comment \"{camp['trigger_word']}\" for the full details.",
        f"Aim for about {int(budget * 0.8)} characters (hard maximum {budget}). Do NOT write a "
        "WhatsApp link or phone number — it's appended automatically.",
    ])
    persona = common.profile_path(cfg, cfg["persona"]).read_text(encoding="utf-8")
    resp = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]).messages.create(
        model=drafter.MODEL, max_tokens=800, thinking={"type": "disabled"}, system=persona,
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "max_tokens":
        raise ValueError("Caption was cut off (max_tokens).")
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if len(text) < 100:
        raise ValueError(f"Caption came back too short ({len(text)} chars).")
    text = f"{text}\n\n{cta}"
    if len(text) > drafter.LIMITS[platform]:
        raise ValueError(f"Caption is {len(text)} chars, over the {platform} limit.")
    return text


def last_posted(cfg: dict, keys) -> str:
    posted = common.read_state(cfg, "posted").get("listings", {})
    return max((posted[k]["last_posted"] for k in keys if k in posted), default="")


def reel_key(name: str, reel: dict) -> str:
    return f"campaign-{name}-reel-{reel['file']}"


def post_reel(cfg, name, camp, data, rows, platform_list, args) -> int:
    posted = common.read_state(cfg, "posted").get("listings", {})
    reel = next((r for r in camp["reels"] if reel_key(name, r) not in posted), None)
    if reel is None:
        print("All reels already posted.")
        return 0
    url = f"{camp['reel_base_url'].rstrip('/')}/{reel['file']}"
    print(f"Reel: {reel['file']} ({url})")
    failures = 0
    for platform in platform_list:
        try:
            text = daily_posts.draft(caption, cfg, camp, data, rows, platform, reel["angle"])
        except Exception as exc:
            failures += 1
            print(f"  ! caption failed for {platform}: {exc}")
            continue
        print(f"--- {platform} reel ({len(text)} chars) ---\n{text}\n")
        if args.dry_run or (not args.yes and input(f"Publish reel to {platform}? [y/N] ").strip().lower() != "y"):
            continue
        publish = platforms.threads_publish_video if platform == "threads" else platforms.instagram_publish_reel
        try:
            post_id = publish(cfg, text, url)
        except Exception as exc:
            failures += 1
            print(f"  ! publish to {platform} failed: {exc}")
            continue
        common.mark_posted(cfg, reel_key(name, reel), platform, post_id)
        print(f"  published reel to {platform}: {post_id}")
    return failures


def post_next(cfg, name, camp, data, rows, platform_list, args) -> int:
    """The daily focus-project slot: alternate reels and single-unit posts, whichever went out
    less recently; units only once the reels run out."""
    reels_left = [r for r in camp.get("reels", [])
                  if reel_key(name, r) not in common.read_state(cfg, "posted").get("listings", {})]
    last_reel = last_posted(cfg, [reel_key(name, r) for r in camp.get("reels", [])])
    last_unit = last_posted(cfg, [r["ref"] for r in rows])
    if reels_left and last_reel <= last_unit:
        url = f"{camp['reel_base_url'].rstrip('/')}/{reels_left[0]['file']}"
        try:
            reachable = requests.head(url, allow_redirects=True, timeout=20).ok
        except requests.RequestException:
            reachable = False
        if reachable:
            return post_reel(cfg, name, camp, data, rows, platform_list, args)
        print(f"  ! reel not reachable at {url} — posting a unit instead so the slot isn't lost.")
    # Least-recently-posted unit, ignoring the normal cooldown — the campaign deliberately
    # cycles this project's units faster than the general rotation would.
    posted = common.read_state(cfg, "posted").get("listings", {})
    unit = min(rows, key=lambda r: posted.get(r["ref"], {}).get("last_posted", ""))
    return daily_posts.post_listing(cfg, unit, platform_list, args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--platform", action="append", choices=["threads", "instagram"])
    parser.add_argument("--reel", action="store_true", help="Post the next unposted reel")
    parser.add_argument("--next", action="store_true",
                        help="Scheduled slot: next reel or single-unit post, alternating")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    load_dotenv(drafter.HERE / ".env")
    cfg = common.load_config(args.profile)
    camp = yaml.safe_load(common.profile_path(cfg, f"campaigns/{args.campaign}.yaml").read_text(encoding="utf-8"))
    data, rows = sheet_data(cfg, camp["project"])
    platform_list = args.platform or cfg["schedule"]["platforms"]
    if args.reel or args.next:
        run = post_reel if args.reel else post_next
        failures = run(cfg, args.campaign, camp, data, rows, platform_list, args)
        if failures:
            sys.exit(f"Finished with {failures} failure(s).")
        return

    paths = render_slides(cfg, args.campaign, camp, data)
    print(f"Rendered {len(paths)} slides: {paths[0].parent}")

    urls = []
    for p in paths:
        url = make_poster.public_url(cfg, p)
        if url and not args.dry_run:
            daily_posts.commit_poster(p)
        urls.append(url)

    failures = 0
    for platform in platform_list:
        try:
            text = daily_posts.draft(caption, cfg, camp, data, rows, platform)
        except Exception as exc:
            failures += 1
            print(f"  ! caption failed for {platform}: {exc}")
            continue
        print(f"--- {platform} ({len(text)} chars, {len(paths)} slides) ---\n{text}\n")
        if args.dry_run:
            continue
        if not args.yes and input(f"Publish carousel to {platform}? [y/N] ").strip().lower() != "y":
            continue
        publish = platforms.threads_publish_carousel if platform == "threads" else platforms.instagram_publish_carousel
        try:
            post_id = publish(cfg, text, urls)
        except Exception as exc:
            failures += 1
            print(f"  ! publish to {platform} failed: {exc}")
            continue
        common.mark_posted(cfg, f"campaign-{args.campaign}", platform, post_id)
        print(f"  published carousel to {platform}: {post_id}")

    if failures:
        sys.exit(f"Finished with {failures} failure(s).")


if __name__ == "__main__":
    main()
