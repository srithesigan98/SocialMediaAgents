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
import subprocess
import textwrap
import zlib
from pathlib import Path

import requests
from dotenv import load_dotenv

import common

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError:  # pragma: no cover
    raise SystemExit("make_poster.py needs Pillow — run: pip install Pillow")

# Bundled here rather than assumed to ship with Pillow — pip wheels don't actually include
# DejaVu (confirmed: Path(ImageFont.__file__).parent / "fonts" doesn't exist on a plain pip
# install), so font() was silently falling back to PIL's ~10px default bitmap font for every
# size requested, on every poster ever rendered. Bundling real files here works identically on
# any machine or CI runner regardless of what fonts happen to be installed system-wide.
FONT_DIR = Path(__file__).resolve().parent / "fonts"
BOLD = FONT_DIR / "OpenSans-Bold.ttf"
REGULAR = FONT_DIR / "OpenSans-Regular.ttf"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    # No silent fallback to PIL's tiny fixed-size default bitmap font — that failure mode is
    # exactly what shipped every poster so far with near-invisible text (see FONT_DIR above).
    return ImageFont.truetype(str(path), size)


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


def listing_facts(listing: dict) -> dict[str, tuple[str, str]]:
    """Every hard number the sheet row supports, as key -> (value, label) — the data that goes
    on the poster itself so it reads at a glance. Only computed from sheet fields; a missing
    field just means that fact is skipped, never guessed."""
    n = common.parse_number
    price, size = n(listing.get("price", "")), n(listing.get("size", ""))
    instalment, rent = n(listing.get("monthly_instalment", "")), n(listing.get("monthly_rental_estimate", ""))
    facts = {}
    if price and size:
        facts["psf"] = (f"RM{price / size:,.0f}", "PER SQFT")
    if price and rent:
        facts["yield"] = (f"{rent * 12 / price * 100:.1f}%", "RENTAL YIELD")
    if instalment and rent and rent > instalment:
        facts["gap"] = (f"+RM{rent - instalment:,.0f}", "RENT VS INSTALMENT")
    if price:
        facts["price"] = (f"RM{price / 1e6:.2f}M" if price >= 1e6 else f"RM{price / 1000:,.0f}K", "PRICE")
    if listing.get("tenure"):
        facts["tenure"] = (listing["tenure"].split("(")[0].strip().upper(), "TENURE")
    if listing.get("expected_vp"):
        facts["vp"] = (listing["expected_vp"].upper(), "COMPLETION")
    return facts


def hook_choice(listing: dict) -> tuple[str, str]:
    """(fact key, headline) for the big hook. Rotates between the strongest available angles,
    keyed on the listing's ref so different listings lead with different facts — every poster
    shouldn't scream the same "rental gap" line. Deterministic, so re-renders don't change."""
    facts = listing_facts(listing)
    # Brackets are sheet notes ("Jalan Tun Razak (Next to TRX)") — fine in a caption, clutter
    # in a 4-word headline.
    area = re.sub(r"\s*\(.*?\)", "", common._extract_area(listing.get("location", ""))).upper()
    options = []
    if "gap" in facts:
        options.append(("gap", f"RENT COVERS INSTALMENT +RM{facts['gap'][0][3:]}/MO"))
    if "yield" in facts:
        options.append(("yield", f"{facts['yield'][0]} RENTAL YIELD IN {area}"))
    if "psf" in facts:
        options.append(("psf", f"{facts['psf'][0]}/SQFT IN {area}"))
    # Only short rebate lines make a headline; long sheet text ("15% (Partial Furnished) / 11%
    # (Fully Furnished).") reads as noise at headline size — it still shows as a perk below.
    if listing.get("highlight") and len(listing["highlight"]) <= 32:
        options.append(("highlight", listing["highlight"]))
    if not options:
        return "", facts.get("price", ("", ""))[0] or listing.get("location", "")
    return options[zlib.crc32(listing.get("ref", "").encode()) % len(options)]


def hook_text(listing: dict) -> str:
    return hook_choice(listing)[1]


def stat_tiles(listing: dict, hook_key: str) -> list[tuple[str, str]]:
    """Up to 3 supporting numbers for the tile row — whatever the hook isn't already shouting."""
    facts = listing_facts(listing)
    order = ["psf", "yield", "gap", "price", "tenure", "vp"]
    return [facts[k] for k in order if k in facts and k != hook_key][:3]


def fit_hook(draw, text: str, max_width: int, max_height: int, start: int, minimum: int = 48):
    """Largest bold size (down from `start`) whose word-wrapped text fits both max_width and
    max_height, capped at 4 lines — the hook is meant to dominate the poster, so it should be
    as big as the available space allows, not just legible."""
    size = start
    while size > minimum:
        f = font(BOLD, size)
        chars = max(6, int(max_width / draw.textlength("M", font=f)))
        # No [:4] slice here: slicing silently dropped the end of long hooks ("...GET AN
        # UNBLOCKED" with "KL VIEW" lost) — too many lines must shrink the font instead.
        lines = textwrap.wrap(text, width=chars, break_long_words=False, break_on_hyphens=False)
        line_h = size + 14
        if (len(lines) <= 4 and len(lines) * line_h <= max_height
                and all(draw.textlength(l, font=f) <= max_width for l in lines)):
            return lines, f
        size -= 6
    f = font(BOLD, minimum)
    chars = max(6, int(max_width / draw.textlength("M", font=f)))
    return textwrap.wrap(text, width=chars, break_long_words=False, break_on_hyphens=False), f


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
        if Path(url).is_file():  # campaign photos live in the repo, not at a URL
            photo = ImageOps.exif_transpose(Image.open(url))
        else:
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


ZOOM = 1.12  # photo kept this much larger than the frame so the video can push in without edges


def _ease(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3  # ease-out cubic: fast start, soft landing


class Canvas:
    """One poster, kept as separate layers — photo, brand, hook headline, detail stack — so the
    same design renders both as a still PNG and as an animated MP4 (photo slowly pushes in,
    headline and details slide up into place)."""

    def __init__(self, cfg: dict, photo_url: str, size=None):
        pc = cfg.get("poster", {})
        self.width, self.height = size or tuple(pc.get("size", [1080, 1350]))
        self.accent = pc.get("accent", "#14B87A")
        self.fg = pc.get("text", "#F5F7F6")
        self.headline = pc.get("headline", "#FFD400")
        self.margin = int(self.width * 0.08)
        self.inner = self.width - self.margin * 2
        big = (int(self.width * ZOOM), int(self.height * ZOOM))
        self.photo = fetch_photo(photo_url, big) or Image.new("RGB", big, pc.get("background", "#0E1A16"))
        self.scrim = scrim((self.width, self.height))
        self.layers = {k: Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
                       for k in ("brand", "hook", "details")}
        self.draw = ImageDraw.Draw(self.layers["details"])  # also what fit_font() measures with
        brand = pc.get("brand", cfg.get("name", "")).upper()
        ImageDraw.Draw(self.layers["brand"]).text(
            (self.margin, self.margin), brand, font=font(BOLD, 34), fill=self.accent,
            stroke_width=2, stroke_fill="#000000")

    def corner(self, text: str) -> None:
        cf = font(BOLD, 30)
        d = ImageDraw.Draw(self.layers["brand"])
        d.text((self.width - self.margin - d.textlength(text, font=cf), self.margin), text,
               font=cf, fill=self.fg, stroke_width=2, stroke_fill="#000000")

    def compose(self, hook: str, blocks: list[tuple]) -> None:
        """Hook headline sized to fill the space above `blocks`, then the detail stack."""
        w, h, m = self.width, self.height, self.margin
        content_height = sum(_block_height(b) for b in blocks)
        bottom_y = max(m + 70, h - m - content_height)

        # Detail panel: fades in from transparent so the photo flows into it, no hard edge.
        d = ImageDraw.Draw(self.layers["details"])
        fade_top = bottom_y - 140
        for y in range(max(fade_top, 0), h):
            a = 175 if y >= bottom_y - 30 else int(175 * (y - fade_top) / 110)
            d.line([(0, y), (w, y)], fill=(0, 0, 0, max(a, 0)))
        y = bottom_y
        for block in blocks:
            text, f, fill, gap = block
            if isinstance(text, list):
                _draw_tiles(d, text, f, fill, self.fg, m, y, self.inner)
            else:
                d.text((m, y), text, font=f, fill=fill)
            y += _block_height(block)

        hook_top, hook_bottom = m + 90, bottom_y - 150
        if not hook or hook_bottom <= hook_top:
            return
        lines, hf = fit_hook(self.draw, hook.upper(), self.inner, hook_bottom - hook_top,
                             start=int(w * 0.14))
        line_h = hf.size + 10
        top = hook_bottom - len(lines) * line_h  # bottom-aligned: sits just above the details
        layer = self.layers["hook"]
        # Soft shadow (blurred dark copy) + black outline: yellow reads on bright sky and
        # dark interiors alike, with no solid band hiding the photo.
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for i, line in enumerate(lines):
            sd.text((m + 6, top + i * line_h + 8), line, font=hf, fill=(0, 0, 0, 200))
        layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
        hd = ImageDraw.Draw(layer)
        for i, line in enumerate(lines):
            hd.text((m, top + i * line_h), line, font=hf, fill=self.headline,
                    stroke_width=max(3, hf.size // 28), stroke_fill="#000000")

    def _frame(self, zoom: float, alphas: dict, offsets: dict) -> Image.Image:
        """zoom 0 = whole oversized photo (widest), 1 = pushed in to the frame size."""
        pw, ph = self.photo.size
        cw, ch = pw - (pw - self.width) * zoom, ph - (ph - self.height) * zoom
        x0, y0 = (pw - cw) / 2, (ph - ch) / 2
        img = self.photo.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch)))
        img = img.resize((self.width, self.height), Image.LANCZOS).convert("RGBA")
        img.alpha_composite(self.scrim)
        for name in ("brand", "hook", "details"):
            a, dy = alphas.get(name, 1.0), offsets.get(name, 0)
            if a <= 0:
                continue
            layer = self.layers[name]
            if a < 1:
                layer = layer.copy()
                layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(layer, (0, int(dy)))
        return img.convert("RGB")

    def save_png(self, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._frame(0.0, {}, {}).save(out_path, "PNG")
        return out_path

    def save_mp4(self, out_path: Path, seconds: float = 7.0, fps: int = 30) -> Path:
        """Photo pushes in over the whole clip; brand fades in, hook slides up (0.25-0.95s),
        details follow (0.9-1.5s), then it holds so there's time to read."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{self.width}x{self.height}", "-r", str(fps), "-i", "-",
               "-c:v", "libx264", "-preset", "medium", "-crf", "26", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for n in range(int(seconds * fps)):
            t = n / fps
            hook_p, det_p = _ease((t - 0.25) / 0.7), _ease((t - 0.9) / 0.6)
            frame = self._frame(
                zoom=t / seconds,
                alphas={"brand": _ease(t / 0.4), "hook": hook_p, "details": det_p},
                offsets={"hook": 70 * (1 - hook_p), "details": 40 * (1 - det_p)},
            )
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed to encode the poster video")
        return out_path


# A block whose text is a list of (value, label) pairs is a stat-tile row: big accent number
# over a small label, in outlined boxes — how the poster shows several data points at a glance.
TILE_GAP, TILE_PAD, TILE_LABEL = 18, 22, 22


def _block_height(block: tuple) -> int:
    text, f, _, gap = block
    extra = TILE_PAD * 2 + TILE_LABEL + 8 if isinstance(text, list) else 0
    return f.size + extra + gap


def tile_block(draw, tiles: list[tuple[str, str]], inner: int, accent: str, gap: int = 26) -> tuple:
    tile_w = (inner - TILE_GAP * (len(tiles) - 1)) // len(tiles)
    longest = max((v for v, _ in tiles), key=len)
    return (tiles, fit_font(draw, longest, BOLD, tile_w - 24, 56), accent, gap)


def _draw_tiles(draw, tiles, value_font, accent, fg, x0: int, y: int, inner: int) -> None:
    tile_w = (inner - TILE_GAP * (len(tiles) - 1)) // len(tiles)
    tile_h = value_font.size + TILE_PAD * 2 + TILE_LABEL + 8
    label_font = font(REGULAR, TILE_LABEL)
    for i, (value, label) in enumerate(tiles):
        x = x0 + i * (tile_w + TILE_GAP)
        draw.rounded_rectangle([x, y, x + tile_w, y + tile_h], radius=18,
                               fill="#0E1A16", outline=accent, width=3)
        cx = x + tile_w // 2
        draw.text((cx, y + TILE_PAD), value, font=value_font, fill=accent, anchor="ma")
        draw.text((cx, y + TILE_PAD + value_font.size + 8), label, font=label_font, fill=fg, anchor="ma")


def render(cfg: dict, listing: dict, out_path: Path | None = None, size=None) -> Path:
    out_path = out_path or common.POSTERS_DIR / f"{cfg['_profile']}-{listing['ref']}.png"
    return listing_canvas(cfg, listing, size).save_png(out_path)


def render_video(cfg: dict, listing: dict, out_path: Path | None = None) -> Path:
    """The same poster, animated, in 9:16 for Reels/Threads video — the layout re-flows for the
    taller frame on its own since everything is sized from the available space."""
    out_path = out_path or common.POSTERS_DIR / f"{cfg['_profile']}-{listing['ref']}.mp4"
    return listing_canvas(cfg, listing, (1080, 1920)).save_mp4(out_path)


def listing_canvas(cfg: dict, listing: dict, size=None) -> Canvas:
    # photo_url is a raw source photo to composite into the poster (e.g. found via search).
    # image_url means a finished, ready-to-post image and is handled upstream in daily_posts.py's
    # poster_url(), which uses it as-is instead of calling render() at all — the two are
    # deliberately different fields so a bare source photo never gets posted without the price/
    # location/CTA text overlay.
    c = Canvas(cfg, listing.get("photo_url", "") or listing.get("image_url", ""), size)
    draw, width, inner, fg, accent = c.draw, c.width, c.inner, c.fg, c.accent

    # Deliberately minimal and deliberately missing the title/ref/WhatsApp link — the title is
    # withheld on purpose (the CTA asks viewers to comment it), and everything else lives in the
    # caption instead, which already gets every field via generate_property_post.py.
    # Built before the hook headline below so the hook can be sized to whatever vertical space
    # is actually left, instead of risking an overlap with a fixed position.
    blocks: list[tuple] = []  # (text, font, fill, gap_after)

    loc_size = "   ·   ".join(filter(None, [
        listing.get("location", ""),
        f"{listing['size']} sqft" if listing.get("size") else "",
    ]))
    if loc_size:
        blocks.append((loc_size, fit_font(draw, loc_size, REGULAR, inner, 34), fg, 20))

    monthly = listing.get("monthly_instalment") or listing.get("price")
    if monthly:
        price_text = f"{group_digits(monthly).replace('.00', '')}/mo"
        blocks.append((price_text, fit_font(draw, price_text, BOLD, inner, int(width * 0.085)), fg, 22))

    hook_key, hook = hook_choice(listing)
    tiles = stat_tiles(listing, hook_key)
    if tiles:
        blocks.append(tile_block(draw, tiles, inner, c.headline))

    # "What's the best thing about it" — rebate and freebies, skipped if the hook already says it.
    perks = [p for p in (listing.get("highlight"), listing.get("legal_fees_freebies")) if p and p != hook]
    if perks:
        perk_font = font(REGULAR, 30)
        chars = max(18, int(inner / draw.textlength("n", font=perk_font)))
        lines = []
        for perk in perks:  # one bullet per perk; Open Sans has no ✓ glyph, • it is
            wrapped = textwrap.wrap(perk, width=chars - 2, break_long_words=False, break_on_hyphens=False)
            lines += ["• " + wrapped[0]] + ["   " + w for w in wrapped[1:]]
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1].rstrip(" ,.(") + "…"
        for i, line in enumerate(lines):
            blocks.append((line, perk_font, fg, 8 if i < len(lines) - 1 else 26))

    # Themed comment-trigger word (not the full title) — the pattern validated by watching
    # @therumahouse's reels: a specific keyword tied to the property reads as more particular/
    # memorable than a generic "comment the name" instruction, and doubles as the trigger phrase
    # reply_bot.py's commenters would use.
    cta_text = f'COMMENT "{trigger_word(listing.get("title", ""))}" FOR FULL DETAILS'
    cta_font = fit_font(draw, cta_text, BOLD, inner, 42)
    blocks.append((cta_text, cta_font, accent, 0))

    c.compose(hook, blocks)
    return c


def render_area(cfg: dict, stat: dict, photo_url: str, out_path: Path | None = None, size=None) -> Path:
    """One area's slide in a market-comparison carousel — same visual language as render(), but
    the hook is the area's price/sqft (the fact these posts are actually about) instead of a
    listing's rental gap, and there's no per-listing comment-trigger CTA since a carousel slide
    isn't tied to one specific unit."""
    c = Canvas(cfg, photo_url, size)
    area_line = stat["area"].upper()
    tiles = [
        (f"RM{stat['min_price_per_sqft']:,}", "LOWEST /SQFT"),
        (f"RM{stat['max_price_per_sqft']:,}", "HIGHEST /SQFT"),
        (str(stat["listing_count"]), "UNITS LISTED"),
    ]
    c.compose(f"RM{stat['avg_price_per_sqft']:,}/sqft average", [
        (area_line, fit_font(c.draw, area_line, BOLD, c.inner, 46), c.fg, 22),
        tile_block(c.draw, tiles, c.inner, c.headline, gap=0),
    ])
    if out_path is None:
        slug = re.sub(r"[^a-z0-9]+", "-", stat["area"].lower()).strip("-")
        out_path = common.POSTERS_DIR / f"{cfg['_profile']}-area-{slug}.png"
    return c.save_png(out_path)


def render_slide(cfg: dict, photo: str, hook: str, out_path: Path, tiles=(), lines=(),
                 cta_word: str | None = None, page: int = 0, total: int = 0) -> Path:
    """One slide of a feature carousel (see campaign_post.py): photo + big hook + optional stat
    tiles, bullet lines and comment-trigger CTA — same visual language as render()."""
    return slide_canvas(cfg, photo, hook, tiles, lines, cta_word, page, total).save_png(out_path)


def slide_canvas(cfg: dict, photo: str, hook: str, tiles=(), lines=(), cta_word: str | None = None,
                 page: int = 0, total: int = 0, size=None) -> Canvas:
    c = Canvas(cfg, photo, size)
    if total:
        c.corner(f"{page}/{total}")
    blocks: list[tuple] = []
    if tiles:
        blocks.append(tile_block(c.draw, [tuple(t) for t in tiles], c.inner, c.headline))
    for i, line in enumerate(lines):
        blocks.append((line, fit_font(c.draw, line, REGULAR, c.inner, 34), c.fg,
                       10 if i < len(lines) - 1 else 26))
    if cta_word:
        cta = f'COMMENT "{cta_word}" FOR FULL DETAILS'
        blocks.append((cta, fit_font(c.draw, cta, BOLD, c.inner, 42), c.accent, 0))
    c.compose(hook, blocks)
    return c


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
