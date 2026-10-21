#!/usr/bin/env python3
"""Premium editorial carousel style — every SenangHomes carousel renders in this.

Forest green / warm ivory backgrounds alternating slide to slide, Outfit SemiBold headlines with
a contrasting italic-serif second phrase (terracotta on light, peach on dark), small uppercase
labels, flat panels, numbered markers, oversized numbers, arch-cropped photos, a tilted orange
sticker on the cover, and a takeaway under a thin rule on every slide. 1080x1350, 62px margins.

Each slide is a dict (usually from a campaign yaml):
    layout   cover | statement | bignumber | arch | photo | list | compare | checklist
    label, headline, italic, body, takeaway, photo, items, number, caption, compare,
    sticker, subtitle, cta, dark (override the light/dark alternation)

Single posts keep editorial.py's cream style; this is carousels only. Fonts: Outfit (OFL) and
Gelasio Italic standing in for Georgia Italic (metric-compatible, freely redistributable).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

import editorial
from editorial import load_photo, logo, spaced, spaced_width, wrap

F = editorial.FONTS
SEMI, MED, REG, ITAL = (F / "Outfit-SemiBold.ttf", F / "Outfit-Medium.ttf",
                        F / "Outfit-Regular.ttf", F / "Gelasio-MediumItalic.ttf")
FOREST, IVORY, TERRA = "#142E2B", "#F3F0E7", "#B94321"
PEACH, ORANGE, BEIGE = "#FFAA78", "#F87947", "#E5DED0"

W, H, M = 1080, 1350, 62
INNER = W - 2 * M
LABEL_Y, HEAD_Y = 150, 190
RULE_Y, ZONE_BOTTOM = 1176, 1136

THEMES = {
    False: dict(bg=IVORY, ink=FOREST, accent=TERRA, muted="#5B6B66", panel=BEIGE, rule="#C9C1B1", dark=False),
    True: dict(bg=FOREST, ink=IVORY, accent=PEACH, muted="#B9C4BE", panel="#1F3F3B", rule="#3A5651", dark=True),
}


def font(path: Path, size: int):
    return editorial.font(path, size)


def headline_lines(d, head: str, ital: str, width: int, hi: int, lo: int, max_lines: int):
    """Two-part headline at the largest size in [lo, hi] that fits max_lines in total."""
    for s in range(hi, lo - 1, -4):
        a = wrap(d, head, font(SEMI, s), width) if head else []
        b = wrap(d, ital, font(ITAL, int(s * 1.02)), width) if ital else []
        if len(a) + len(b) <= max_lines:
            return a, b, s
    return wrap(d, head, font(SEMI, lo), width), wrap(d, ital, font(ITAL, lo), width), lo


class Slide:
    def __init__(self, spec: dict, *, series: str, page: int, total: int, photo_dir: Path | None = None):
        self.s = spec
        self.series, self.page, self.total = series, page, total
        self.layout = spec.get("layout", "statement")
        dark = spec.get("dark")
        self.t = THEMES[page % 2 == 0 if dark is None else bool(dark)]
        src = spec.get("photo", "")
        if src and photo_dir and not str(src).startswith("http") and not Path(src).is_absolute():
            src = str(photo_dir / src)
        self.photo = load_photo(src) if src else None

    # ------------------------------------------------------------ shared chrome
    def _header(self, img, d, ink, dark):
        badge = logo("badge", dark=dark, height=44)
        img.paste(badge, (M, 46), badge)
        f = font(MED, 19)
        spaced(d, (M + badge.width + 14, 58), self.series.upper(), f, ink, 0.16)
        pt = f"{self.page:02d} / {self.total:02d}"
        spaced(d, (W - M - spaced_width(d, pt, f, 0.12), 58), pt, f, ink, 0.12)

    def _cue(self, d, y, ink, accent):
        last = self.page == self.total
        text = "SAVE + SHARE" if last else "SWIPE"
        f = font(MED, 19)
        x = W - M - spaced_width(d, text, f, 0.16) - (0 if last else 58)
        spaced(d, (x, y), text, f, accent if last else ink, 0.16)
        if not last:
            ax, mid = W - M - 44, y + 12
            d.line([(ax, mid), (ax + 44, mid)], fill=ORANGE, width=3)
            d.line([(ax + 32, mid - 9), (ax + 44, mid), (ax + 32, mid + 9)], fill=ORANGE, width=3)

    def _bottom(self, d, t):
        d.line([(M, RULE_Y), (W - M, RULE_Y)], fill=t["rule"], width=2)
        if self.s.get("takeaway"):
            f = font(REG, 26)
            for i, line in enumerate(wrap(d, self.s["takeaway"], f, INNER - 230)[:2]):
                d.text((M, RULE_Y + 22 + i * 34), line, font=f, fill=t["ink"])
        self._cue(d, RULE_Y + 26, t["ink"], t["accent"])

    def _top(self, d, t, hi=96, lo=70, max_lines=4, width=INNER) -> int:
        """Category label, two-part headline, body. Returns the y where this content ends."""
        if self.s.get("label"):
            spaced(d, (M, LABEL_Y), self.s["label"].upper(), font(MED, 19), t["accent"], 0.16)
        a, b, s = headline_lines(d, self.s.get("headline", ""), self.s.get("italic", ""), width, hi, lo, max_lines)
        y = HEAD_Y
        for line in a:
            d.text((M, y), line, font=font(SEMI, s), fill=t["ink"])
            y += s
        for line in b:
            d.text((M, y), line, font=font(ITAL, int(s * 1.02)), fill=t["accent"])
            y += int(s * 1.06)
        if self.s.get("body"):
            y += 18
            f = font(REG, 30)
            for line in wrap(d, self.s["body"], f, width):
                d.text((M, y), line, font=f, fill=t["muted"])
                y += 40
        return y

    # ------------------------------------------------------------ visual helpers
    def _fit(self, box):
        x0, y0, x1, y1 = box
        return ImageOps.fit(self.photo, (int(x1 - x0), int(y1 - y0)), Image.LANCZOS)

    def _arch(self, img, box):
        """Photo cropped into an architectural arch: rounded top, straight bottom."""
        x0, y0, x1, y1 = [int(v) for v in box]
        w, h = x1 - x0, y1 - y0
        mask = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([0, 0, w, w], fill=255)
        md.rectangle([0, w // 2, w, h], fill=255)
        img.paste(self._fit(box), (x0, y0), mask)

    def render(self) -> Image.Image:
        if self.layout == "cover":
            return self._cover()
        t = self.t
        img = Image.new("RGB", (W, H), t["bg"])
        d = ImageDraw.Draw(img)
        self._header(img, d, t["ink"], t["dark"])
        getattr(self, f"_layout_{self.layout}")(img, d, t)
        self._bottom(d, t)
        return img

    # ------------------------------------------------------------ layouts
    def _fill_below(self, img, top: int) -> bool:
        """Optional photo filling the space left under a slide's content, so no slide is left
        half-empty. Skipped when there's too little room to read as an image."""
        if self.photo is None or ZONE_BOTTOM - top < 220:
            return False
        box = (M, top, W - M, ZONE_BOTTOM)
        img.paste(self._fit(box), box[:2])
        return True

    def _layout_statement(self, img, d, t):
        y = self._top(d, t, hi=104, lo=76, max_lines=5)
        if self._fill_below(img, y + 44):
            return
        if self.s.get("number"):  # optional oversized figure anchoring the statement
            d.text((M - 6, max(y + 30, 760)), self.s["number"], font=font(SEMI, 200), fill=t["accent"])

    def _layout_bignumber(self, img, d, t):
        y = self._top(d, t, hi=88, lo=64, max_lines=3)
        top = y + 40
        num_w = INNER // 2 + 30 if self.photo is not None else INNER
        num, size = self.s.get("number", ""), 330
        while size > 120 and d.textlength(num, font=font(SEMI, size)) > num_w:
            size -= 10
        d.text((M - 8, top - size * 0.12), num, font=font(SEMI, size), fill=t["accent"])
        cy, f = top + int(size * 0.95), font(REG, 32)
        for line in wrap(d, self.s.get("caption", ""), f, num_w - 20)[:4]:
            d.text((M, cy), line, font=f, fill=t["ink"])
            cy += 42
        if self.photo is not None:
            self._arch(img, (M + num_w + 20, top, W - M, ZONE_BOTTOM))

    def _layout_arch(self, img, d, t):
        y = self._top(d, t, hi=92, lo=68, max_lines=3)
        top = y + 36
        if self.photo is None:
            d.rectangle([M, top, W - M, ZONE_BOTTOM], fill=t["panel"])
            return
        w = min(INNER, int((ZONE_BOTTOM - top) * 0.82))
        self._arch(img, (M, top, M + w, ZONE_BOTTOM))
        if self.s.get("aside"):  # short note beside the arch
            f, ay = font(REG, 30), top + 40
            for line in wrap(d, self.s["aside"], f, INNER - w - 40):
                d.text((M + w + 40, ay), line, font=f, fill=t["ink"])
                ay += 40

    def _layout_photo(self, img, d, t):
        y = self._top(d, t, hi=92, lo=68, max_lines=3)
        box = (M, y + 34, W - M, ZONE_BOTTOM)
        if self.photo is not None:
            img.paste(self._fit(box), box[:2])
        else:
            d.rectangle(box, fill=t["panel"])

    def _layout_list(self, img, d, t):
        y = self._top(d, t, hi=90, lo=64, max_lines=3)
        items = self.s.get("items", [])[:5]
        if not items:
            return
        top, gap = y + 36, 16
        row_h = min(170, (ZONE_BOTTOM - top - gap * (len(items) - 1)) // len(items))
        if self.photo is not None:  # compact rows, photo takes the rest
            row_h = 118
        tf, lf = font(SEMI, 32), font(REG, 26)
        for i, it in enumerate(items):
            title, line = (it.get("title", ""), it.get("line", "")) if isinstance(it, dict) else (it, "")
            ry = top + i * (row_h + gap)
            d.rectangle([M, ry, W - M, ry + row_h], fill=t["panel"])
            r, cx, cy = 24, M + 50, ry + row_h // 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ORANGE)
            d.text((cx, cy), f"{i + 1:02d}", font=font(SEMI, 22), fill=FOREST, anchor="mm")
            tx = M + 100
            if line:
                d.text((tx, cy - 36), wrap(d, title, tf, INNER - 130)[0], font=tf, fill=t["ink"])
                d.text((tx, cy + 6), wrap(d, line, lf, INNER - 130)[0], font=lf, fill=t["muted"])
            else:
                d.text((tx, cy), title, font=tf, fill=t["ink"], anchor="lm")
        self._fill_below(img, top + len(items) * (row_h + gap) + 14)

    def _layout_compare(self, img, d, t):
        y = self._top(d, t, hi=90, lo=64, max_lines=3)
        panels = self.s.get("compare", [])[:2]
        top, gap = y + 40, 64
        pw = (INNER - gap) // 2
        bottom = top + 330 if self.photo is not None else ZONE_BOTTOM
        for i, p in enumerate(panels):
            x = M + i * (pw + gap)
            d.rectangle([x, top, x + pw, bottom], fill=t["panel"])
            spaced(d, (x + 32, top + 34), p.get("label", "").upper(), font(MED, 18), t["accent"], 0.14)
            vf = font(SEMI, 64)
            while d.textlength(p.get("value", ""), font=vf) > pw - 64 and vf.size > 36:
                vf = font(SEMI, vf.size - 4)
            d.text((x + 32, top + 80), p.get("value", ""), font=vf, fill=t["ink"])
            ly, lf = top + 80 + vf.size + 30, font(REG, 27)
            for line in p.get("lines", []):
                for wl in wrap(d, line, lf, pw - 64):
                    d.text((x + 32, ly), wl, font=lf, fill=t["muted"])
                    ly += 36
                ly += 10
        self._fill_below(img, bottom + 30)
        if len(panels) == 2:  # simple arrow between the two panels
            mx, my = M + pw + gap // 2, (top + bottom) // 2
            d.ellipse([mx - 26, my - 26, mx + 26, my + 26], fill=ORANGE)
            d.line([(mx - 11, my), (mx + 11, my)], fill=FOREST, width=3)
            d.line([(mx + 3, my - 8), (mx + 11, my), (mx + 3, my + 8)], fill=FOREST, width=3)

    def _layout_checklist(self, img, d, t):
        y = self._top(d, t, hi=90, lo=64, max_lines=3)
        items = self.s.get("items", [])[:7]
        cta = self.s.get("cta", "")
        cta_h = 110 if cta else 0
        top = y + 30
        row_h = min(86, (ZONE_BOTTOM - cta_h - 24 - top) // max(len(items), 1))
        f = font(REG, 30)
        for i, it in enumerate(items):
            ry = top + i * row_h
            cx, cy, r = M + 20, ry + row_h // 2, 18
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ORANGE, width=3)
            d.line([(cx - 8, cy + 1), (cx - 2, cy + 7), (cx + 9, cy - 6)], fill=ORANGE, width=3)
            text = it if isinstance(it, str) else it.get("title", "")
            d.text((M + 58, cy), wrap(d, text, f, INNER - 60)[0], font=f, fill=t["ink"], anchor="lm")
            if i < len(items) - 1:
                d.line([(M + 58, ry + row_h), (W - M, ry + row_h)], fill=t["rule"], width=1)
        if cta:
            py = ZONE_BOTTOM - cta_h
            d.rectangle([M, py, W - M, ZONE_BOTTOM], fill=PEACH if t["dark"] else TERRA)
            d.text((W // 2, py + cta_h // 2), cta, font=font(SEMI, 34),
                   fill=FOREST if t["dark"] else IVORY, anchor="mm")

    # ------------------------------------------------------------ cover
    def _cover(self) -> Image.Image:
        img = Image.new("RGB", (W, H), FOREST)
        if self.photo is not None:
            img.paste(ImageOps.fit(self.photo, (W, H), Image.LANCZOS), (0, 0))
        # dark-green gradient: light behind the header, deep at the bottom behind the text
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for y in range(H):
            a = 150 * (1 - y / 230) if y < 230 else min(238, 238 * max(0, (y - 430) / 620))
            od.line([(0, y), (W, y)], fill=(20, 46, 43, int(a)))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(img)
        self._header(img, d, IVORY, True)

        a, b, s = headline_lines(d, self.s.get("headline", ""), self.s.get("italic", ""), INNER, 100, 76, 4)
        sub = wrap(d, self.s.get("subtitle", ""), font(REG, 32), INNER) if self.s.get("subtitle") else []
        block = len(a) * s + len(b) * int(s * 1.06) + (24 + len(sub) * 42 if sub else 0) + 50
        y = RULE_Y - 40 - block
        if self.s.get("label"):
            spaced(d, (M, y), self.s["label"].upper(), font(MED, 19), PEACH, 0.16)
        y += 50
        for line in a:
            d.text((M, y), line, font=font(SEMI, s), fill=IVORY)
            y += s
        for line in b:
            d.text((M, y), line, font=font(ITAL, int(s * 1.02)), fill=PEACH)
            y += int(s * 1.06)
        for i, line in enumerate(sub):
            d.text((M, y + 24 + i * 42), line, font=font(REG, 32), fill=BEIGE)
        if self.s.get("sticker"):
            self._sticker(img, self.s["sticker"])
        d.line([(M, RULE_Y), (W - M, RULE_Y)], fill="#5A7570", width=2)
        self._cue(d, RULE_Y + 26, IVORY, PEACH)
        return img

    def _sticker(self, img, text):
        """Small orange circular sticker, tilted — one short message, a focal point only."""
        r = 118
        st = Image.new("RGBA", (r * 2 + 8, r * 2 + 8), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.ellipse([4, 4, r * 2 + 4, r * 2 + 4], fill=ORANGE)
        f, lh = font(SEMI, 34), 38
        lines = wrap(sd, text, f, int(r * 1.5))[:3]
        y0 = r + 4 - len(lines) * lh // 2
        for i, line in enumerate(lines):
            sd.text((r + 4, y0 + i * lh + lh // 2), line, font=f, fill=FOREST, anchor="mm")
        st = st.rotate(12, resample=Image.BICUBIC, expand=True)
        img.paste(st, (W - M - st.width + 10, 150), st)


def _fill(v, fill):
    if isinstance(v, str):
        return fill(v)
    if isinstance(v, list):
        return [_fill(x, fill) for x in v]
    if isinstance(v, dict):
        return {k: _fill(x, fill) for k, x in v.items()}
    return v


def render_carousel(slides: list[dict], *, series: str, out_prefix: Path, photo_dir: Path | None = None,
                    fill=lambda s: s) -> list[Path]:
    """Render every slide spec to `<out_prefix>-<n>.png`; `fill` formats {placeholders}."""
    total, paths = len(slides), []
    for i, spec in enumerate(slides, 1):
        spec = {k: _fill(v, fill) for k, v in spec.items()}
        p = out_prefix.parent / f"{out_prefix.name}-{i}.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        Slide(spec, series=series, page=i, total=total, photo_dir=photo_dir).render().save(p, "PNG")
        paths.append(p)
    return paths
