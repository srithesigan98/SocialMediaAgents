#!/usr/bin/env python3
"""Render a property poster PNG from a listing row — locally, with no network and no Canva.

    python make_poster.py HE-001 --profile senang-homes
    python make_poster.py HE-001 --open-size 1080x1080

This is the `poster.mode: auto` path. It exists because Instagram refuses to publish a caption
without an image, and a cron job at 09:30 cannot drive the Canva connector. For richer, on-brand
art direction, use `poster.mode: canva` and generate it in a Claude session instead — see
../../design/poster-style-guide.md.

Layout is deliberately plain and information-first: brand tag, price, title, location, a spec
row, and the highlight. Type sizes auto-fit so a long title never overflows.
"""
from __future__ import annotations

import argparse
import re
import textwrap
from pathlib import Path

from dotenv import load_dotenv

import common

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    raise SystemExit("make_poster.py needs Pillow — run: pip install Pillow")

# DejaVu ships with Pillow, so this works on a bare container with no system fonts installed.
FONT_DIR = Path(ImageFont.__file__).resolve().parent / "fonts"
BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
REGULAR = FONT_DIR / "DejaVuSans.ttf"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:  # no bundled fonts — fall back to the built-in bitmap font
        return ImageFont.load_default()


def fit_font(draw, text: str, path: Path, max_width: int, start: int, minimum: int = 28):
    """Shrink until the line fits the available width."""
    size = start
    while size > minimum:
        f = font(path, size)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 4
    return font(path, minimum)


def group_digits(value: str) -> str:
    """RM 480000 -> RM 480,000. Formatting only — the number itself is never changed."""
    return re.sub(r"\d{4,}", lambda m: f"{int(m.group()):,}", value)


def spec_row(listing: dict) -> str:
    bits = []
    if listing.get("bedrooms"):
        beds = listing["bedrooms"]
        baths = listing.get("bathrooms")
        bits.append(f"{beds}R{baths}B" if baths else f"{beds} rooms")
    if listing.get("size"):
        bits.append(f"{listing['size']} sqft")
    if listing.get("tenure"):
        bits.append(listing["tenure"])
    if listing.get("monthly_instalment"):
        bits.append(f"{listing['monthly_instalment']}/mo")
    return "   ·   ".join(bits)


def render(cfg: dict, listing: dict, out_path: Path | None = None, size=None) -> Path:
    pc = cfg.get("poster", {})
    width, height = size or tuple(pc.get("size", [1080, 1350]))
    bg, accent = pc.get("background", "#0E1A16"), pc.get("accent", "#14B87A")
    fg, muted = pc.get("text", "#F5F7F6"), pc.get("muted", "#8FA39B")
    margin = int(width * 0.08)
    inner = width - margin * 2

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # A single accent bar at the top and a filled CTA band at the bottom frame the type.
    draw.rectangle([0, 0, width, int(height * 0.012)], fill=accent)
    band_top = height - int(height * 0.16)

    # Build the content as measurable blocks first, then centre them in the space between the
    # brand tag and the CTA band — otherwise short listings leave a dead lower third.
    blocks: list[tuple] = []  # (kind, text, font, fill, gap_after)

    deal = (listing.get("deal") or "").upper()
    ptype = (listing.get("type") or "").upper()
    tag = "  ·  ".join(filter(None, [f"FOR {deal}" if deal else "", ptype]))
    if tag:
        blocks.append(("text", tag, font(REGULAR, 28), muted, 26))

    if listing.get("price"):
        price = group_digits(listing["price"])
        blocks.append(("text", price, fit_font(draw, price, BOLD, inner, int(width * 0.115)), fg, 22))

    if listing.get("title"):
        blocks.append(("text", listing["title"], fit_font(draw, listing["title"], BOLD, inner, 58), fg, 14))

    if listing.get("location"):
        blocks.append(("text", listing["location"], font(REGULAR, 36), muted, 40))

    specs = spec_row(listing)
    if specs:
        blocks.append(("rule", "", None, muted, 30))
        blocks.append(("text", specs, fit_font(draw, specs, REGULAR, inner, 34), fg, 40))

    if listing.get("highlight"):
        highlight_font = font(REGULAR, 38)
        chars = max(18, int(inner / draw.textlength("n", font=highlight_font)))
        for line in textwrap.wrap(listing["highlight"], width=chars)[:4]:
            blocks.append(("text", line, highlight_font, accent, 10))

    def block_height(kind, _text, f, *_rest) -> int:
        return 2 if kind == "rule" else f.size

    content_height = sum(block_height(*b) + b[4] for b in blocks)

    top_limit = margin + 70          # under the brand tag
    bottom_limit = band_top - margin
    y = top_limit + max(0, (bottom_limit - top_limit - content_height) // 2)

    brand = pc.get("brand", cfg.get("name", "")).upper()
    draw.text((margin, margin), brand, font=font(REGULAR, 30), fill=accent)

    for kind, text, f, fill, gap in blocks:
        if kind == "rule":
            draw.line([(margin, y), (margin + inner, y)], fill=fill, width=2)
            y += 2 + gap
        else:
            draw.text((margin, y), text, font=f, fill=fill)
            y += f.size + gap

    draw.rectangle([0, band_top, width, height], fill=accent)
    cta_font = fit_font(draw, "WHATSAPP FOR FULL DETAILS", BOLD, inner, 52)
    cta_y = band_top + int(height * 0.035)
    draw.text((margin, cta_y), "WHATSAPP FOR FULL DETAILS", font=cta_font, fill=bg)
    draw.text((margin, cta_y + cta_font.size + 14), f"Ref {listing.get('ref', '')}",
              font=font(REGULAR, 30), fill=bg)

    out_path = out_path or common.POSTERS_DIR / f"{cfg['_profile']}-{listing['ref']}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


def public_url(cfg: dict, path: Path) -> str | None:
    """Turn a rendered poster into the public URL the Meta APIs require, if one is configured."""
    base = (cfg.get("poster", {}).get("public_base_url") or "").rstrip("/")
    return f"{base}/{path.name}" if base else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--open-size", default=None, metavar="WxH", help="Override poster size, e.g. 1080x1080")
    args = parser.parse_args()

    load_dotenv(common.HERE / ".env")
    cfg = common.load_config(args.profile)
    listing = common.find_listing(cfg, args.ref)
    size = tuple(int(n) for n in args.open_size.split("x")) if args.open_size else None
    path = render(cfg, listing, size=size)
    print(f"Wrote {path}")
    url = public_url(cfg, path)
    print(f"Public URL: {url}" if url else
          "No poster.public_base_url set — upload this file somewhere public before posting.")


if __name__ == "__main__":
    main()
