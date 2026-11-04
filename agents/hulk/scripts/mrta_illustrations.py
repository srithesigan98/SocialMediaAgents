#!/usr/bin/env python3
"""Draws the explainer diagrams for the MRTA/MLTA carousel (campaigns/mrta-mlta.yaml) into
profiles/senang-homes/campaigns/mrta-mlta/. Each PNG is sized to the slot it fills in
magazine.py and drawn in that slide's colours. Re-run after changing any number here.

    python mrta_illustrations.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

import magazine as mg

OUT = Path(__file__).resolve().parent.parent / "profiles/senang-homes/campaigns/mrta-mlta"
S = 2  # draw at 2x, downscale = antialiased shapes

# The worked example used everywhere: RM500K, 30 years, 3% a year -> ~RM380K left at year 10.
LOAN, YEARS, RATE, EXAMPLE_YEAR = 500_000, 30, 0.03, 10
DARK_PANEL = "#1F3F3B"


def balance(t: float) -> float:
    """Share of the loan still owed after t years (standard amortisation)."""
    g = 1 + RATE
    return (g ** YEARS - g ** t) / (g ** YEARS - 1)


class Canvas:
    """PIL drawing in 1x coordinates on a 2x canvas."""
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w * S, h * S), bg)  # RGB + RGBA draw = alpha blends
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def _p(self, pts):
        return [v * S for v in pts]

    def line(self, pts, fill, width):
        self.d.line(self._p(pts), fill=fill, width=width * S, joint="curve")

    def dashed(self, x0, y0, x1, y1, fill, width, dash=14):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) // dash)
        for i in range(0, n, 2):
            a, b = i / n, min(1, (i + 1) / n)
            self.line([x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b], fill, width)

    def poly(self, pts, fill):
        flat = [v for p in pts for v in (p if isinstance(p, tuple) else (p,))]
        self.d.polygon(self._p(flat), fill=fill)

    def rect(self, box, fill, r=0):
        self.d.rounded_rectangle(self._p(box), r * S, fill=fill)

    def circle(self, cx, cy, r, fill=None):
        self.d.ellipse(self._p([cx - r, cy - r, cx + r, cy + r]), fill=fill)

    def text(self, xy, s, path, size, fill, anchor="la"):
        self.d.text(self._p(xy), s, font=mg.font(path, size * S), fill=fill, anchor=anchor)

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        self.img.resize((self.w, self.h), Image.LANCZOS).save(OUT / name)
        print(OUT / name)


# ---------------------------------------------------------------- icons (centre, size)
def house(c, cx, cy, s, fill, door):
    c.poly([cx - s * .62, cy - s * .05, cx, cy - s * .6, cx + s * .62, cy - s * .05], fill)
    c.rect([cx - s * .45, cy - s * .1, cx + s * .45, cy + s * .5], fill)
    c.rect([cx - s * .12, cy + s * .12, cx + s * .12, cy + s * .5], door)


def shield(c, cx, cy, s, fill, mark):
    c.poly([cx - s * .5, cy - s * .45, cx, cy - s * .6, cx + s * .5, cy - s * .45,
            cx + s * .45, cy + s * .1, cx, cy + s * .6, cx - s * .45, cy + s * .1], fill)
    c.line([cx - s * .2, cy, cx - s * .04, cy + s * .17, cx + s * .24, cy - s * .18], mark, max(3, int(s * .09)))


def bank(c, cx, cy, s, fill, bg):
    c.poly([cx - s * .6, cy - s * .2, cx, cy - s * .58, cx + s * .6, cy - s * .2], fill)
    for i in range(4):
        x = cx - s * .42 + i * s * .28
        c.rect([x - s * .07, cy - s * .12, x + s * .07, cy + s * .38], fill)
    c.rect([cx - s * .6, cy + s * .42, cx + s * .6, cy + s * .55], fill)


# ---------------------------------------------------------------- illustrations
def cover():
    """Full-bleed cover: level vs reducing cover. The lower half sits under the text gradient."""
    c = Canvas(1080, 1350, mg.FOREST)
    x0, x1, top, base = 110, 970, 300, 640
    curve = [(x0 + (x1 - x0) * t / YEARS, base - (base - top) * balance(t)) for t in range(YEARS + 1)]
    c.poly([(x0, top), (x1, top), *curve[::-1]], (255, 170, 120, 120))
    c.line([x0, base, x1, base], "#3A5651", 3)
    c.line([v for p in curve for v in p], mg.IVORY, 9)
    c.line([x0, top, x1, top], mg.PEACH, 9)
    c.circle(x1, top, 14, mg.PEACH)
    c.circle(x1, base, 14, mg.IVORY)
    c.text((x0, top - 72), "MLTA", mg.SEMI, 40, mg.PEACH)
    c.text((x0 + 128, top - 64), "cover stays level", mg.REG, 30, mg.PEACH)
    c.text((x0 + 20, base - 120), "MRTA", mg.SEMI, 40, mg.IVORY)
    c.text((x0 + 20, base - 72), "cover reduces", mg.REG, 30, mg.IVORY)
    c.save("cover.png")


def flow():
    """Slide 2: what happens on a claim."""
    c = Canvas(956, 590, DARK_PANEL)
    steps = [(shield, "Insurer pays", "the claim"), (bank, "The bank", "settles the loan"),
             (house, "Your family", "keeps the home")]
    xs = [170, 478, 786]
    c.text((478, 70), "IF YOU PASS AWAY OR BECOME TPD", mg.MED, 22, mg.PEACH, "mm")
    for i, ((icon, a, b), x) in enumerate(zip(steps, xs)):
        c.circle(x, 250, 105, mg.FOREST)
        icon(c, x, 252, 120, mg.PEACH if i == 2 else mg.IVORY, mg.FOREST)
        c.text((x, 410), a, mg.SEMI, 34, mg.IVORY, "mm")
        c.text((x, 454), b, mg.REG, 28, "#B9C4BE", "mm")
        if i < 2:
            ax = x + 125
            c.line([ax, 250, ax + 38, 250], mg.ORANGE, 6)
            c.poly([ax + 38, 236, ax + 58, 250, ax + 38, 264], mg.ORANGE)
    c.save("flow.png")


def chart():
    """Chart slide: cover over the loan term, with the example year marked."""
    c = Canvas(956, 720, mg.BEIGE)
    x0, x1, top, base = 150, 900, 110, 590
    X = lambda t: x0 + (x1 - x0) * t / YEARS
    Y = lambda frac: base - (base - top) * frac
    for frac, lab in ((1, "RM500K"), (.5, "RM250K"), (0, "RM0")):
        c.line([x0, Y(frac), x1, Y(frac)], "#CFC6B5", 2)
        c.text((x0 - 18, Y(frac)), lab, mg.MED, 22, "#5B6B66", "rm")
    for t in (0, 10, 20, 30):
        c.text((X(t), base + 34), f"Year {t}", mg.MED, 22, "#5B6B66", "mm")
    curve = [(X(t), Y(balance(t))) for t in range(YEARS + 1)]
    c.poly([(x0, top), (x1, top), *curve[::-1]], (248, 121, 71, 70))
    c.line([v for p in curve for v in p], mg.FOREST, 8)
    c.line([x0, top, x1, top], mg.ORANGE, 8)
    ex, ey = X(EXAMPLE_YEAR), Y(balance(EXAMPLE_YEAR))
    c.dashed(ex, top, ex, base, mg.TERRA, 3)
    c.circle(ex, ey, 13, mg.FOREST)
    c.circle(ex, top, 13, mg.ORANGE)
    left = round(LOAN * balance(EXAMPLE_YEAR) / 1000)
    c.text((ex - 20, ey + 24), f"MRTA ~RM{left}K", mg.SEMI, 26, mg.FOREST, "ra")
    c.text((ex + 22, top - 40), "MLTA RM500K", mg.SEMI, 26, mg.ORANGE)
    c.text((X(22), Y(.84)), "The gap", mg.SEMI, 30, mg.TERRA, "mm")
    c.text((X(22), Y(.84) + 38), "goes to your family", mg.REG, 26, mg.TERRA, "mm")
    c.text((478, 685), "Illustration: RM500K loan, 30 years, 3% a year", mg.REG, 22, "#5B6B66", "mm")
    c.save("chart.png")


def split():
    """Big-number slide arch: how an RM500K MLTA payout splits at the example year."""
    w, h = 428, 716
    c = Canvas(w, h, mg.BEIGE)
    left = round(LOAN * balance(EXAMPLE_YEAR) / 1000)
    shield(c, w / 2, 150, 110, mg.FOREST, mg.BEIGE)
    c.text((w / 2, 245), "MLTA pays RM500K", mg.SEMI, 26, mg.FOREST, "mm")
    bx0, bx1, by0, by1 = 84, w - 84, 285, 665
    cut = by0 + (by1 - by0) * (1 - left / 500)
    c.rect([bx0, by0, bx1, cut], mg.ORANGE)
    c.rect([bx0, cut, bx1, by1], mg.FOREST)
    c.text((w / 2, (by0 + cut) / 2 - 16), f"RM{500 - left}K", mg.SEMI, 34, mg.FOREST, "mm")
    c.text((w / 2, (by0 + cut) / 2 + 20), "to your family", mg.REG, 22, mg.FOREST, "mm")
    c.text((w / 2, (cut + by1) / 2 - 18), f"RM{left}K", mg.SEMI, 40, mg.IVORY, "mm")
    c.text((w / 2, (cut + by1) / 2 + 24), "to the bank", mg.REG, 24, mg.IVORY, "mm")
    c.save("split.png")


def refinance():
    """'Pick by your plans' slide: what refinancing does to each."""
    c = Canvas(956, 300, DARK_PANEL)
    x0, x1, rx = 190, 900, 430
    c.text((x0, 42), "Year 0", mg.MED, 20, "#B9C4BE", "lm")
    c.text((x1, 42), "Year 30", mg.MED, 20, "#B9C4BE", "rm")
    c.dashed(rx, 70, rx, 270, mg.PEACH, 3)
    c.text((rx, 42), "You refinance", mg.SEMI, 22, mg.PEACH, "mm")
    c.text((40, 135), "MRTA", mg.SEMI, 30, mg.IVORY, "lm")
    c.rect([x0, 122, rx, 148], mg.IVORY, 13)
    c.line([rx + 22, 120, rx + 50, 150], mg.ORANGE, 6)
    c.line([rx + 50, 120, rx + 22, 150], mg.ORANGE, 6)
    c.text((rx + 72, 135), "Cover ends", mg.REG, 26, "#B9C4BE", "lm")
    c.text((40, 225), "MLTA", mg.SEMI, 30, mg.PEACH, "lm")
    c.rect([x0, 212, x1 - 24, 238], mg.PEACH, 13)
    c.poly([x1 - 30, 200, x1, 225, x1 - 30, 250], mg.PEACH)
    c.text((rx + 72, 188), "Many plans move with you", mg.REG, 24, mg.PEACH, "lm")
    c.save("refinance.png")


if __name__ == "__main__":
    cover(); flow(); chart(); split(); refinance()
