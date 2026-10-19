#!/usr/bin/env python3
"""Turn sheet data into SenangHomes posters — the content side; editorial.py owns the layout.

    python make_poster.py khaya-residences-772 --profile senang-homes

Every number on a poster comes from the sheet row (or, for carousels, the campaign brief) —
nothing is estimated or invented here. Layout, palette and typography follow the SenangHomes
brand brief and live in editorial.py so every post type stays one consistent series.
"""
from __future__ import annotations

import argparse
import re
import zlib
from pathlib import Path

from dotenv import load_dotenv

import common
import editorial


def group_digits(value: str) -> str:
    """RM 480000 -> RM 480,000. Formatting only — the number itself is never changed."""
    return re.sub(r"\d{4,}", lambda m: f"{int(m.group()):,}", value)


_GENERIC_TITLE_WORDS = {"the", "one", "m", "a", "an"}


def trigger_word(title: str) -> str:
    """Pick a short, on-theme comment-trigger word from the project name (e.g. "The Lantern
    Bangsar" -> "LANTERN") — a themed keyword tied to the property reads as more specific/
    memorable than a generic instruction, and pairs with reply_bot.py's WhatsApp auto-reply the
    same way a comment-triggered auto-DM would. Skips generic leading words/bare numbers."""
    words = [w.strip("()'\".,") for w in title.split() if w.strip("()'\".,")]
    for w in words:
        if w.lower() not in _GENERIC_TITLE_WORDS and not w.isdigit():
            return w.upper()
    return words[0].upper() if words else "THIS"


def area_of(listing: dict) -> str:
    """'Jalan Tun Razak (Next to TRX), KL' -> 'Jalan Tun Razak' — bracketed sheet notes are fine
    in a caption, clutter in a headline or footer."""
    return re.sub(r"\s*\(.*?\)", "", common._extract_area(listing.get("location", ""))).strip()


def money(v: float) -> str:
    return f"RM{v / 1e6:.2f}M" if v >= 1e6 else f"RM{v / 1000:,.0f}K"


def listing_facts(listing: dict) -> dict[str, tuple[str, str]]:
    """Every hard number the sheet row supports, as key -> (value, label). Only computed from
    sheet fields; a missing field just means that fact is skipped, never guessed."""
    n = common.parse_number
    price, size = n(listing.get("price", "")), n(listing.get("size", ""))
    instalment, rent = n(listing.get("monthly_instalment", "")), n(listing.get("monthly_rental_estimate", ""))
    facts = {}
    if price and size:
        facts["psf"] = (f"RM{price / size:,.0f}", "PER SQFT")
    if price and rent:
        facts["yield"] = (f"{rent * 12 / price * 100:.1f}%", "RENTAL YIELD")
    if instalment and rent and rent > instalment:
        facts["gap"] = (f"RM{rent - instalment:,.0f}", "RENT VS INSTALMENT")
    if price:
        facts["price"] = (money(price), "PRICE")
    if listing.get("tenure"):
        facts["tenure"] = (listing["tenure"].split("(")[0].strip().title(), "TENURE")
    if listing.get("expected_vp"):
        facts["vp"] = (listing["expected_vp"], "COMPLETION")
    return facts


def hook_choice(listing: dict) -> tuple[str, str]:
    """(fact key, sentence-case headline). Rotates between the strongest angles, keyed on the
    listing's ref so different listings lead with different facts. Deterministic."""
    facts, area = listing_facts(listing), area_of(listing)
    options = []
    if "gap" in facts:
        options.append(("gap", f"Rent covers the instalment, with {facts['gap'][0]} to spare"))
    if "yield" in facts:
        options.append(("yield", f"{facts['yield'][0]} rental yield in {area}"))
    if "psf" in facts:
        options.append(("psf", f"{facts['psf'][0]} per sqft in {area}"))
    # Only short rebate lines make a headline; long sheet text reads as noise at headline size.
    if listing.get("highlight") and len(listing["highlight"]) <= 32:
        options.append(("highlight", listing["highlight"]))
    if not options:
        return "", f"New homes in {area}" if area else listing.get("title", "")
    return options[zlib.crc32(listing.get("ref", "").encode()) % len(options)]


def hook_text(listing: dict) -> str:
    return hook_choice(listing)[1]


def listing_copy(listing: dict, hook_key: str) -> list[str]:
    """Short supporting sentences, each built only from sheet fields; ordered by importance so
    the layout can drop from the end if space runs out."""
    f = listing_facts(listing)
    out = []
    if "price" in f:
        psf = f" — about {f['psf'][0]} per sqft" if "psf" in f and hook_key != "psf" else ""
        out.append(f"Priced at {f['price'][0]}{psf}.")
    inst, rent = listing.get("monthly_instalment"), listing.get("monthly_rental_estimate")
    if inst and rent and hook_key != "gap":
        out.append(f"Instalment from {group_digits(inst).replace('.00', '')} a month; "
                   f"estimated rent {group_digits(rent).replace('.00', '')}.")
    elif "yield" in f and hook_key != "yield":
        out.append(f"Estimated rental yield {f['yield'][0]}.")
    if hook_key in ("gap", "yield"):
        out.append("Rent is an estimate based on current listed rents.")
    if listing.get("highlight") and hook_key != "highlight" and len(listing["highlight"]) <= 60:
        out.append(listing["highlight"].rstrip(".") + ".")
    details = [x for x in (f.get("tenure", ("",))[0], f"completion {f['vp'][0]}" if "vp" in f else "") if x]
    if details:
        out.append(". ".join(d[0].upper() + d[1:] for d in details) + ".")
    return out


def listing_poster(cfg: dict, listing: dict) -> editorial.Poster:
    """Single-listing information poster."""
    key, hook = hook_choice(listing)
    area = area_of(listing)
    size = f"{listing['size']} sqft" if listing.get("size") else ""
    return editorial.Poster(
        "info",
        label=" · ".join(x for x in (area, size) if x),
        headline=hook,
        photo=listing.get("photo_url", "") or listing.get("image_url", ""),
        copy=listing_copy(listing, key),
        cta=f'Comment "{trigger_word(listing.get("title", ""))}" for full details',
        location=area or "Kuala Lumpur",
    )


listing_canvas = listing_poster  # weekly_posts.py recap: .corner("2/9") then .save_png()


def render(cfg: dict, listing: dict, out_path: Path | None = None) -> Path:
    out_path = out_path or common.POSTERS_DIR / f"{cfg['_profile']}-{listing['ref']}.png"
    return listing_poster(cfg, listing).save_png(out_path)


def render_video(cfg: dict, listing: dict, out_path: Path | None = None) -> Path:
    """Same poster as an MP4 — only the photo slowly pushes in inside its frame."""
    out_path = out_path or common.POSTERS_DIR / f"{cfg['_profile']}-{listing['ref']}.mp4"
    return listing_poster(cfg, listing).save_mp4(out_path)


def render_area(cfg: dict, stat: dict, photo_url: str, out_path: Path | None = None) -> Path:
    """One area's slide in a market-comparison carousel."""
    area = re.sub(r"\s*\(.*?\)", "", stat["area"]).strip()
    poster = editorial.Poster(
        "info", label="Area guide", headline=f"{area}, at RM{stat['avg_price_per_sqft']:,} per sqft",
        photo=photo_url, location=area,
        copy=[f"Listings range from RM{stat['min_price_per_sqft']:,} to RM{stat['max_price_per_sqft']:,} "
              f"per sqft across {stat['project_count']} project(s).",
              "Average of the units we currently list in this area."],
    )
    if out_path is None:
        slug = re.sub(r"[^a-z0-9]+", "-", stat["area"].lower()).strip("-")
        out_path = common.POSTERS_DIR / f"{cfg['_profile']}-area-{slug}.png"
    return poster.save_png(out_path)


def public_url(cfg: dict, path: Path) -> str | None:
    """Turn a rendered poster into the public URL the Meta APIs require, if one is configured."""
    base = (cfg.get("poster", {}).get("public_base_url") or "").rstrip("/")
    return f"{base}/{path.name}" if base else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref")
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    load_dotenv(common.HERE / ".env")
    cfg = common.load_config(args.profile)
    path = render(cfg, common.find_listing(cfg, args.ref))
    print(f"Wrote {path}")
    url = public_url(cfg, path)
    print(f"Public URL: {url}" if url else
          "No poster.public_base_url set — upload this file somewhere public before posting.")


if __name__ == "__main__":
    main()
