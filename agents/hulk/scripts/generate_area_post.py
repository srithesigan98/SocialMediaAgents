#!/usr/bin/env python3
"""Draft an area/market-comparison post from aggregate listing data, instead of one property —
"which area fits your budget/lifestyle", using real price/sqft stats computed across the active
sheet (see common.area_stats()). Complements generate_property_post.py's single-listing posts.

    python generate_area_post.py                              # auto-picks 2 areas to compare
    python generate_area_post.py --areas Bangsar,Seputeh --platform instagram
    python generate_area_post.py --count 3

Drafts are written to drafts/ for review. This script never posts anything.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

import common
import generate_property_post as drafter  # reuses its LIMITS/HERE/DRAFTS_DIR conventions
import make_poster

# Windows consoles default to cp1252; make emoji/curly-quote output (e.g. the WhatsApp CTA) safe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL = "claude-sonnet-5"


def area_block(stats: list[dict]) -> str:
    lines = []
    for s in stats:
        projects = ", ".join(s["projects"][:3]) + ("..." if len(s["projects"]) > 3 else "")
        lines.append(
            f"- {s['area']}: {s['listing_count']} unit(s) across {s['project_count']} "
            f"project(s) ({projects}), RM {s['avg_price_per_sqft']}/sqft average "
            f"(range RM {s['min_price_per_sqft']}-{s['max_price_per_sqft']}/sqft)"
        )
    return "\n".join(lines)


def build_prompt(stats: list[dict], platform: str, cta: str) -> str:
    budget = drafter.LIMITS[platform] - len(cta) - 2
    per_area = budget // (len(stats) + 1)  # +1 leaves room for a short shared intro line
    parts = [
        "Write one social post comparing these Kuala Lumpur areas by price-per-sqft, framed "
        "around how the price tier and area character translate into lifestyle — who each area "
        "actually suits (e.g. young professional vs family, quiet vs nightlife-heavy, CBD-close "
        "vs suburban) — not just a bare numbers table. Use ONLY the facts below for numbers; you "
        "may reference well-established, widely-known general character of these specific Kuala "
        "Lumpur neighbourhoods (e.g. Bangsar's dining/nightlife scene, Mont Kiara's expat/"
        "international-school density, Seputeh's quieter established-residential feel) but never "
        "invent a specific amenity, distance, or fact that isn't in the data below or genuinely "
        "well-known.",
        "",
        area_block(stats),
        "",
        f"Platform: {platform}. STRICT limit: {budget} characters total for your text (the CTA is "
        f"appended separately, don't write one). Count your characters as you go. With "
        f"{len(stats)} areas, budget about {per_area} characters per area plus a one-sentence "
        f"intro — a post that runs over this limit gets rejected outright, so write short and "
        f"plain rather than risk going over. Prefer trimming detail on the LAST area over cutting "
        f"it entirely.",
    ]
    return "\n".join(parts)


def generate(stats: list[dict], platform: str, cfg: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")

    persona = common.profile_path(cfg, cfg["persona"]).read_text(encoding="utf-8")
    number = re.sub(r"\D", "", str(cfg["whatsapp"]["number"]))
    cta = cfg["whatsapp"]["cta_template"].format(link=f"https://wa.me/{number}")

    # See generate_property_post.py's generate() for why thinking is disabled here.
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        thinking={"type": "disabled"},
        system=persona,
        messages=[{"role": "user", "content": build_prompt(stats, platform, cta)}],
    )
    if response.stop_reason == "max_tokens":
        # See generate_property_post.py's generate() for why this check exists.
        raise ValueError("Draft was cut off mid-generation (hit max_tokens) — treating as a bad response.")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if len(text) < 100:
        raise ValueError(f"Draft came back too short ({len(text)} chars) — treating as a bad response.")

    # Always appended in code — see generate_property_post.py's generate() for why.
    text = f"{text}\n\n{cta}"
    if len(text) > drafter.LIMITS[platform]:
        raise ValueError(f"Draft is {len(text)} chars, over the {platform} limit of {drafter.LIMITS[platform]}.")
    return text


def pick_areas(cfg: dict, count: int) -> list[dict]:
    """Prefer a spread across the price range (a budget area vs a premium one) rather than random
    picks, so a comparison is actually meaningfully different rather than two similarly-priced
    areas restating the same point."""
    stats = [s for s in common.area_stats(cfg) if s["listing_count"] >= 2]
    if not stats:
        return []
    stats.sort(key=lambda s: s["avg_price_per_sqft"])
    if len(stats) <= count:
        return stats
    step = (len(stats) - 1) / (count - 1) if count > 1 else 0
    return [stats[round(i * step)] for i in range(count)]


def area_posters(cfg: dict, stats: list[dict]) -> list[Path]:
    """Render one composited poster per compared area (its first project with a photo) — the
    big RM/sqft hook overlaid on a real building photo, same visual language as the
    single-listing posters. Areas with no project photo available are skipped."""
    overrides = common.load_photo_overrides(cfg)
    paths = []
    for s in stats:
        photo_url = next((overrides[p] for p in s["projects"] if p in overrides), None)
        if photo_url:
            paths.append(make_poster.render_area(cfg, s, photo_url))
    return paths


def save_draft(cfg: dict, text: str, stats: list[dict], platform: str) -> Path:
    drafter.DRAFTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    areas_note = ", ".join(s["area"] for s in stats)
    path = drafter.DRAFTS_DIR / f"{stamp}-{cfg['_profile']}-area-{platform}.md"
    path.write_text(
        f"<!-- profile: {cfg['_profile']} -->\n<!-- areas: {areas_note} -->\n"
        f"<!-- platform: {platform} -->\n\n{text}\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--areas", help="Comma-separated area names to compare (default: auto-pick)")
    parser.add_argument("--count", type=int, default=2, help="How many areas to compare (default 2)")
    parser.add_argument("--platform", choices=sorted(drafter.LIMITS), default="threads")
    args = parser.parse_args()

    load_dotenv(drafter.HERE / ".env")
    cfg = common.load_config(args.profile)

    if args.areas:
        wanted = {a.strip().lower() for a in args.areas.split(",")}
        stats = [s for s in common.area_stats(cfg) if s["area"].lower() in wanted]
    else:
        stats = pick_areas(cfg, args.count)

    if not stats:
        sys.exit("No areas with enough price/sqft data to compare.")

    text = generate(stats, args.platform, cfg)
    path = save_draft(cfg, text, stats, args.platform)
    posters = area_posters(cfg, stats)

    print(text)
    print(f"\nSaved to {path}")
    print(f"Carousel posters ({len(posters)}): "
          + (", ".join(str(p) for p in posters) if posters else "none found"))


if __name__ == "__main__":
    main()
