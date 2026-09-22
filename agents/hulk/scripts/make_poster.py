#!/usr/bin/env python3
"""Render a property poster PNG from a listing row — no Canva, no design tool.

    python make_poster.py HE-001 --profile senang-homes
    python make_poster.py HE-001 --open-size 1080x1080

This is the `poster.mode: auto` path. It exists because Instagram refuses to publish a caption
without an image, and a cron job at 09:30 cannot drive the Canva connector. For richer, on-brand
art direction, use `poster.mode: canva` and generate it in a Claude session instead — see
../../design/poster-style-guide.md.

The poster is the listing photo (from the sheet's Image URL column) with a bottom gradient and
four lines over it: location + size, the monthly price, the one-line highlight, and a "comment
the property name" CTA — deliberately no WhatsApp link, ref number or title on the image itself;
that's the hook (viewers have to comment to find out the name), and the rest of the detail lives
in the caption, which already gets every field. No photo URL → falls back to a plain brand-colour
card so the pipeline never breaks on a missing image.
"""
from __future__ import annotations

import argparse
import io
import re
import textwrap
from pathlib import Path

import requests
from dotenv import load_dotenv

import common

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
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


def fetch_photo(url: str, size: tuple[int, int]) -> Image.Image | None:
    """Cover-crop the listing photo to the poster canvas. None on no URL / fetch / decode error
    — a bad or missing photo must never break the daily posting run.

    ponytail: an animated (GIF) source renders as its first frame — the output here is always a
    static PNG, since Instagram/Threads image posts don't play GIFs anyway. True animated/video
    posting would be a different pipeline; add it if that's ever actually requested.
    """
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        photo = Image.open(io.BytesIO(resp.content))
        photo.seek(0)  # first frame if it's a GIF
        photo = photo.convert("RGB")
    except Exception:
        return None
    return ImageOps.fit(photo, size, Image.LANCZOS)


def scrim(size: tuple[int, int]) -> Image.Image:
    """Dark gradient so text stays legible over a photo: a light fade behind the brand tag up
    top, transparent middle so the photo breathes, a stronger fade behind the text stack at the
    bottom."""
    w, h = size
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    top_h = int(h * 0.16)
    for y in range(top_h):
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, int(110 * (1 - y / top_h))))
    bottom_start = int(h * 0.58)
    for y in range(bottom_start, h):
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, int(215 * (y - bottom_start) / (h - bottom_start))))
    return overlay


def render(cfg: dict, listing: dict, out_path: Path | None = None, size=None) -> Path:
    pc = cfg.get("poster", {})
    width, height = size or tuple(pc.get("size", [1080, 1350]))
    bg, accent = pc.get("background", "#0E1A16"), pc.get("accent", "#14B87A")
    fg = pc.get("text", "#F5F7F6")
    margin = int(width * 0.08)
    inner = width - margin * 2

    # photo_url is a raw source photo to composite into the poster (e.g. found via search).
    # image_url means a finished, ready-to-post image and is handled upstream in daily_posts.py's
    # poster_url(), which uses it as-is instead of calling render() at all — the two are
    # deliberately different fields so a bare source photo never gets posted without the price/
    # location/CTA text overlay.
    photo = fetch_photo(listing.get("photo_url", "") or listing.get("image_url", ""), (width, height))
    base = photo if photo else Image.new("RGB", (width, height), bg)
    img = Image.alpha_composite(base.convert("RGBA"), scrim((width, height))).convert("RGB")
    draw = ImageDraw.Draw(img)

    brand = pc.get("brand", cfg.get("name", "")).upper()
    draw.text((margin, margin), brand, font=font(REGULAR, 30), fill=accent)

    # Deliberately minimal and deliberately missing the title/ref/WhatsApp link — the title is
    # withheld on purpose (the CTA asks viewers to comment it), and everything else lives in the
    # caption instead, which already gets every field via generate_property_post.py.
    blocks: list[tuple] = []  # (text, font, fill, gap_after)

    loc_size = "   ·   ".join(filter(None, [
        listing.get("location", ""),
        f"{listing['size']} sqft" if listing.get("size") else "",
    ]))
    if loc_size:
        blocks.append((loc_size, fit_font(draw, loc_size, REGULAR, inner, 34), fg, 20))

    monthly = listing.get("monthly_instalment") or listing.get("price")
    if monthly:
        price_text = f"{group_digits(monthly)}/mo"
        blocks.append((price_text, fit_font(draw, price_text, BOLD, inner, int(width * 0.1)), fg, 22))

    if listing.get("highlight"):
        highlight_font = font(REGULAR, 34)
        chars = max(18, int(inner / draw.textlength("n", font=highlight_font)))
        lines = textwrap.wrap(listing["highlight"], width=chars)[:3]
        for i, line in enumerate(lines):
            blocks.append((line, highlight_font, fg, 10 if i < len(lines) - 1 else 30))

    # Themed comment-trigger word (not the full title) — the pattern validated by watching
    # @therumahouse's reels: a specific keyword tied to the property reads as more particular/
    # memorable than a generic "comment the name" instruction, and doubles as the trigger phrase
    # reply_bot.py's commenters would use.
    cta_text = f'COMMENT "{trigger_word(listing.get("title", ""))}" FOR FULL DETAILS'
    cta_font = fit_font(draw, cta_text, BOLD, inner, 42)
    blocks.append((cta_text, cta_font, accent, 0))

    content_height = sum(f.size + gap for _, f, _, gap in blocks)
    y = max(margin + 70, height - margin - content_height)
    for text, f, fill, gap in blocks:
        draw.text((margin, y), text, font=f, fill=fill)
        y += f.size + gap

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
