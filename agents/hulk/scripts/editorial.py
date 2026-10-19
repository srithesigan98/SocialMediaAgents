#!/usr/bin/env python3
"""SenangHomes editorial poster system — the house style every post renders in.

Implements the brand brief (refined property-magazine look): 1080x1350, 75px safe area, warm
cream paper, forest-green serif headline in sentence case, real photo in a clean rectangle,
short sans copy, thin gold rules, and the fixed header / footer system. Four layouts:

    info       label + headline + photo + short copy (+ optional CTA)   — single listings
    cover      big curiosity headline + photo + swipe cue               — carousel slide 1
    checklist  label + headline + photo band + 3-4 gold-icon rows        — tips, "at a glance"
    closing    forest-green reverse: cream headline + gold CTA panel      — last carousel slide

Every layout shares the same header (SENANG HOMES wordmark + gold divider) and footer
("SENANG HOMES / <LOCATION>" left, "02 / 08" right on carousels), so a series reads as one
campaign. A poster renders as a flat PNG, or as an MP4 where only the photo slowly pushes in
inside its frame — the layout itself never moves.
"""
from __future__ import annotations

import io
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FONTS = Path(__file__).resolve().parent / "fonts"
SERIF = FONTS / "Gelasio-SemiBold.ttf"      # Georgia-metric-compatible editorial serif
SANS = FONTS / "OpenSans-Regular.ttf"       # stands in for Segoe UI
SANS_SEMI = FONTS / "OpenSans-SemiBold.ttf"

CREAM, FOREST, GOLD = "#F5F1E7", "#183E35", "#B28B53"
GREY_GREEN, STONE, SAGE = "#607369", "#DEDCCB", "#BDCEC0"

W, H, M = 1080, 1350, 75          # canvas + safe margin
INNER = W - 2 * M
HEADER_Y, DIVIDER_Y = 72, 130
LABEL_Y = 162
HEADLINE_TOP = 212
VISUAL_BOTTOM = 990
COPY_TOP, COPY_BOTTOM = 1020, 1200
FOOTER_RULE_Y, FOOTER_Y = 1236, 1262

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def load_photo(src: str) -> Image.Image | None:
    """Repo path or URL -> RGB image; None if missing/unreachable (layout still renders)."""
    if not src:
        return None
    try:
        if Path(src).is_file():
            img = Image.open(src)
        else:
            r = requests.get(src, timeout=15, headers={"User-Agent": BROWSER_UA})
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
        img.seek(0)
        return ImageOps.exif_transpose(img).convert("RGB")
    except Exception:
        return None


def spaced(draw, xy, text, f, fill, tracking: float = 0.12) -> int:
    """Letter-spaced uppercase text (labels, wordmark, footer). Returns the end x."""
    x, y = xy
    gap = f.size * tracking
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + gap
    return int(x - gap)


def spaced_width(draw, text, f, tracking: float = 0.12) -> float:
    return sum(draw.textlength(ch, font=f) for ch in text) + f.size * tracking * (len(text) - 1)


def wrap(draw, text: str, f, width: int) -> list[str]:
    """Greedy word wrap by real pixel width — never splits a word."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=f) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit_headline(draw, text: str, width: int, max_lines: int = 3, hi: int = 105, lo: int = 80):
    """Largest serif size in the brief's 80-105px band that fits in max_lines; below 80 only
    as a last resort for an over-long headline (better small than clipped)."""
    for size in list(range(hi, lo - 1, -3)) + list(range(lo - 4, 55, -4)):
        f = font(SERIF, size)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines:
            return lines, f
    return wrap(draw, text, font(SERIF, 56), width), font(SERIF, 56)


def paper(size=(W, H), color=CREAM) -> Image.Image:
    """Cream with a very faint warm grain — texture you feel more than see."""
    base = Image.new("RGB", size, color)
    grain = Image.effect_noise(size, 22).filter(ImageFilter.GaussianBlur(0.6)).convert("RGB")
    return Image.blend(base, Image.blend(base, grain, 0.5), 0.06)


BRAND = Path(__file__).resolve().parent.parent / "profiles" / "senang-homes" / "brand"


def logo(kind: str, dark: bool, height: int) -> Image.Image:
    """Official SenangHomes logo (design L3, chimney) as RGBA at `height` px. Light posters use
    the green-orange colourway; the forest-green closing slide uses the cream 'reverse'."""
    img = Image.open(BRAND / f"logo-{kind}-{'reverse' if dark else 'green-orange'}.png").convert("RGBA")
    return img.resize((round(img.width * height / img.height), height), Image.LANCZOS)


def page_text(page: int, total: int) -> str:
    return f"{page:02d} / {total:02d}" if total else ""


class Poster:
    """One poster. Build with the layout fields, then save_png() or save_mp4()."""

    def __init__(self, kind: str = "info", *, label: str = "", headline: str = "", photo: str = "",
                 copy: list[str] | tuple = (), cta: str = "", items: list | tuple = (),
                 location: str = "KUALA LUMPUR", page: int = 0, total: int = 0, swipe: bool = False):
        self.kind, self.label, self.headline, self.cta = kind, label, headline, cta
        self.copy, self.items = [c for c in copy if c], list(items)
        self.location, self.page, self.total, self.swipe = location, page, total, swipe
        self.photo = load_photo(photo)
        self._static: Image.Image | None = None
        self._photo_box: tuple[int, int, int, int] | None = None

    def corner(self, text: str) -> None:
        """'3/9' -> carousel pagination in the footer."""
        p, t = text.split("/")
        self.page, self.total = int(p), int(t)
        self._static = None

    # ------------------------------------------------------------------ layout
    def _layout(self) -> Image.Image:
        dark = self.kind == "closing"
        bg, ink = (FOREST, CREAM) if dark else (CREAM, FOREST)
        img = paper(color=bg) if not dark else Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)

        # A. header — identical on every poster
        # Official logo (L3 chimney): the badge with the name beside it. The stacked lockup's
        # name would be ~10px at header height, so the header sets the same badge + name side
        # by side at a readable size; the full stacked logo closes every carousel.
        badge = logo("badge", dark=dark, height=62)
        img.paste(badge, (M, HEADER_Y - 8), badge)
        spaced(d, (M + badge.width + 18, HEADER_Y + 4), "SENANG HOMES", font(SANS_SEMI, 30), ink, 0.22)
        d.line([(M, DIVIDER_Y), (W - M, DIVIDER_Y)], fill=GOLD, width=2)

        # B. section label
        y = LABEL_Y
        if self.label:
            spaced(d, (M, y), self.label.upper(), font(SANS_SEMI, 24), GOLD, 0.14)
        y = HEADLINE_TOP

        if dark:
            self._closing(img, d)
        else:
            # C. headline
            hi = 105 if self.kind == "cover" else 96
            lines, hf = fit_headline(d, self.headline, INNER, hi=hi)
            lh = int(hf.size * 1.08)
            for line in lines:
                d.text((M, y), line, font=hf, fill=FOREST)
                y += lh
            visual_top = max(440, y + 28)

            if self.kind == "checklist":
                self._checklist(img, d, visual_top)
            else:
                # E. copy measured first so the photo takes whatever height is left
                copy_lines, cf, cta_f = self._fit_copy(d)
                copy_h = self._copy_height(copy_lines, cf, cta_f)
                visual_bottom = min(VISUAL_BOTTOM, COPY_BOTTOM - copy_h - 30) if copy_h else VISUAL_BOTTOM + 120
                if self.kind == "cover" and self.swipe:
                    visual_bottom = min(visual_bottom, 1170)
                self._photo_box = (M, visual_top, W - M, visual_bottom)
                cy = visual_bottom + 30
                for line in copy_lines:
                    d.text((M, cy), line, font=cf, fill=FOREST)
                    cy += int(cf.size * 1.3)
                if self.cta:
                    cy += 8
                    d.line([(M, cy + cta_f.size // 2 + 2), (M + 34, cy + cta_f.size // 2 + 2)], fill=GOLD, width=2)
                    d.text((M + 48, cy), self.cta, font=cta_f, fill=FOREST)
                if self.kind == "cover" and self.swipe:
                    self._swipe_cue(d, visual_bottom + 40)

        # G. footer — identical on every poster
        d.line([(M, FOOTER_RULE_Y), (W - M, FOOTER_RULE_Y)], fill=GOLD, width=1)
        ff = font(SANS, 21)
        spaced(d, (M, FOOTER_Y), f"SENANG HOMES / {self.location.upper()}",
               ff, CREAM if dark else GREY_GREEN, 0.1)
        if self.total:
            pt = page_text(self.page, self.total)
            spaced(d, (W - M - spaced_width(d, pt, ff, 0.1), FOOTER_Y), pt, ff,
                   CREAM if dark else GREY_GREEN, 0.1)
        return img

    def _fit_copy(self, d):
        """Copy at 34px, stepping down to 30 if needed; paragraphs past the zone are dropped
        from the end rather than squeezed (the caption carries the full detail anyway)."""
        cta_f = font(SANS_SEMI, 30)
        budget = COPY_BOTTOM - COPY_TOP + (0 if self.cta else 40)
        for size in (34, 32, 30):
            cf = font(SANS, size)
            paras = list(self.copy)
            while True:
                lines = [ln for p in paras for ln in wrap(d, p, cf, INNER)]
                if self._copy_height(lines, cf, cta_f) <= budget or not paras:
                    break
                paras.pop()
            if paras == list(self.copy):
                return lines, cf, cta_f
        return lines, cf, cta_f

    def _copy_height(self, lines, cf, cta_f) -> int:
        h = len(lines) * int(cf.size * 1.3)
        if self.cta:
            h += 8 + cta_f.size + 8
        return h

    def _swipe_cue(self, d, y):
        f = font(SANS, 24)
        x = spaced(d, (M, y), "SWIPE", f, GREY_GREEN, 0.14) + 16
        mid = y + f.size // 2 + 4
        d.line([(x, mid), (x + 46, mid)], fill=GOLD, width=2)
        d.line([(x + 36, mid - 8), (x + 46, mid), (x + 36, mid + 8)], fill=GOLD, width=2)

    def _checklist(self, img, d, top):
        """Optional short photo band, then 3-4 aligned rows: gold outline icon, short heading,
        one explanatory line."""
        rows = self.items[:4]
        row_h = 128 if len(rows) <= 3 else 112
        rows_h = len(rows) * row_h
        band_bottom = COPY_BOTTOM + 20 - rows_h - 24
        if self.photo is not None and band_bottom - top >= 160:
            self._photo_box = (M, top, W - M, band_bottom)
            y = band_bottom + 34
        else:
            y = top + 10
        hf, lf = font(SANS_SEMI, 32), font(SANS, 29)
        for item in rows:
            title, line = (item.get("title", ""), item.get("line", "")) if isinstance(item, dict) else (item, "")
            cx, cy, r = M + 22, y + 22, 21
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD, width=2)
            d.line([(cx - 9, cy + 1), (cx - 2, cy + 8), (cx + 10, cy - 7)], fill=GOLD, width=2)
            d.text((M + 66, y), title, font=hf, fill=FOREST)
            if line:
                d.text((M + 66, y + 44), wrap(d, line, lf, INNER - 66)[0], font=lf, fill=GREY_GREEN)
            y += row_h

    def _closing(self, img, d):
        """Forest-green reverse: cream headline, the official stacked logo as the closing
        mark, and one call to action in a gold rounded panel."""
        lines, hf = fit_headline(d, self.headline, INNER, hi=100)
        y = 300
        for line in lines:
            d.text((M, y), line, font=hf, fill=CREAM)
            y += int(hf.size * 1.08)
        mark = logo("stacked", dark=True, height=300)
        top = y + 40
        img.paste(mark, ((W - mark.width) // 2, top), mark)
        base = top + mark.height
        if self.copy:
            cf = font(SANS, 32)
            cy = base + 50
            for line in [ln for p in self.copy for ln in wrap(d, p, cf, INNER)][:2]:
                d.text((M, cy), line, font=cf, fill=STONE)
                cy += int(cf.size * 1.3)
        if self.cta:
            pf = font(SANS_SEMI, 34)
            plines = wrap(d, self.cta, pf, INNER - 80)
            ph = len(plines) * int(pf.size * 1.3) + 56
            top = 1200 - ph
            d.rounded_rectangle([M, top, W - M, 1200], radius=28, fill=GOLD)
            ty = top + 28
            for line in plines:
                d.text((W // 2, ty), line, font=pf, fill=FOREST, anchor="ma")
                ty += int(pf.size * 1.3)

    @staticmethod
    def _placeholder(img, box) -> None:
        """No usable photo: a soft sage panel with a restrained gold skyline — clearly an
        illustration, never passed off as the listing, and never an empty frame."""
        d = ImageDraw.Draw(img)
        x0, y0, x1, y1 = box
        d.rectangle(box, fill=SAGE)
        base = y1 - (y1 - y0) // 4
        d.line([(x0 + 60, base), (x1 - 60, base)], fill=GOLD, width=2)
        cx, unit = (x0 + x1) // 2, (x1 - x0) // 14
        heights = [2.2, 3.4, 2.6, 4.6, 3.0, 2.0, 3.8, 2.4]
        x = cx - unit * len(heights) // 2
        for h in heights:
            top = base - int(h * unit * 0.9)
            d.rectangle([x + 6, top, x + unit - 6, base], outline=GOLD, width=2)
            x += unit

    # ------------------------------------------------------------------ output
    def _frame(self, zoom: float = 0.0) -> Image.Image:
        if self._static is None:
            self._static = self._layout()
            if self.photo is None and self._photo_box:
                self._placeholder(self._static, self._photo_box)
        img = self._static.copy()
        if self.photo is not None and self._photo_box:
            x0, y0, x1, y1 = self._photo_box
            bw, bh = x1 - x0, y1 - y0
            scale = 1 + 0.08 * zoom  # gentle push-in, inside the frame only
            big = ImageOps.fit(self.photo, (int(bw * scale), int(bh * scale)), Image.LANCZOS)
            ox, oy = (big.width - bw) // 2, (big.height - bh) // 2
            img.paste(big.crop((ox, oy, ox + bw, oy + bh)), (x0, y0))
        return img

    def save_png(self, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._frame(0.0).save(out_path, "PNG")
        return out_path

    def save_mp4(self, out_path: Path, seconds: float = 7.0, fps: int = 30) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = int(seconds * fps)
        for i in range(n):
            t = i / (n - 1)
            proc.stdin.write(self._frame(t * t * (3 - 2 * t)).tobytes())  # smoothstep
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed to encode the poster video")
        return out_path
