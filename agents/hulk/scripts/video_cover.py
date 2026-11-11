#!/usr/bin/env python3
"""Topic thumbnail for an animated explainer reel (formats/animated-explainer.yaml), in the brand theme.

    python video_cover.py --title "Costs on top of the price" --hook "the real bill for a RM500K home" \
        --frame keyframe.png --out posters/senang-homes-video-hidden-costs-cover.png

1080x1920. Everything that matters sits inside the 3:4 band Instagram's grid shows (y 240-1680):
label, the topic as a big title, the hook in the italic accent, a still from the video on a tilted
card, and the logo. Used as the Instagram reel cover_url and prepended as the video's first frame
(Threads has no cover parameter).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
LOGO = HERE.parent / "profiles/senang-homes/brand/png/horizontal-reverse@2x.png"
W, H, M = 1080, 1920, 75
FOREST, IVORY, PEACH, ORANGE = "#142E2B", "#F3F0E7", "#FFAA78", "#F87947"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def wrap(d: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        test = f"{cur} {w}".strip()
        if d.textlength(test, font=f) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def fit(d, text, name, hi, lo, width, max_lines):
    for size in range(hi, lo - 1, -4):
        f = font(name, size)
        lines = wrap(d, text, f, width)
        if len(lines) <= max_lines:
            return f, lines
    f = font(name, lo)
    return f, wrap(d, text, f, width)[:max_lines]


def spaced(d, xy, text, f, fill, tracking):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + f.size * tracking


def make_cover(title: str, hook: str, frame: Path, out: Path, label: str = "SENANG HOMES · BEFORE YOU BUY") -> Path:
    img = Image.new("RGB", (W, H), FOREST)
    d = ImageDraw.Draw(img)
    y = 285
    spaced(d, (M, y), label, font("Outfit-Medium.ttf", 32), PEACH, 0.14)
    y += 64
    tf, tlines = fit(d, title, "Outfit-SemiBold.ttf", 132, 84, W - 2 * M, 3)
    for line in tlines:
        d.text((M, y), line, font=tf, fill=IVORY)
        y += int(tf.size * 1.02)
    hf, hlines = fit(d, hook, "Gelasio-MediumItalic.ttf", 72, 54, W - 2 * M, 1)
    if d.textlength(hlines[0], font=hf) > W - 2 * M or len(wrap(d, hook, hf, W - 2 * M)) > 1:
        hf, hlines = fit(d, hook, "Gelasio-MediumItalic.ttf", 72, 52, W - 2 * M, 2)
    y += 8
    for line in hlines:
        d.text((M, y), line, font=hf, fill=PEACH)
        y += int(hf.size * 1.18)

    # A still from the video, cropped to its stage, on a tilted card with a soft shadow.
    still = Image.open(frame).convert("RGB").resize((W, H))
    stage = still.crop((110, 420, 970, 1180))
    top = y + 46
    room = 1560 - top
    card_w = min(860, int(room * stage.width / stage.height))
    card = stage.resize((card_w, int(card_w * stage.height / stage.width)), Image.LANCZOS)
    shadow = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((40, 52, card.width + 40, card.height + 52), fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18)).rotate(-2.5, expand=True, resample=Image.BICUBIC)
    rot = card.convert("RGBA").rotate(-2.5, expand=True, resample=Image.BICUBIC)
    x = (W - rot.width) // 2
    img.paste(shadow, (x - 40, top - 30), shadow)
    img.paste(rot, (x, top), rot)

    tag_f = font("Outfit-SemiBold.ttf", 34)
    tag = "60-SEC EXPLAINER"
    tw = int(d.textlength(tag, font=tag_f)) + 84
    d.rectangle((M, top - 34, M + tw, top + 30), fill=ORANGE)
    d.polygon([(M + 22, top - 16), (M + 22, top + 12), (M + 46, top - 2)], fill=FOREST)   # play mark
    d.text((M + 60, top - 26), tag, font=tag_f, fill=FOREST)

    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        lw = 440
        logo = logo.resize((lw, int(lw * logo.height / logo.width)), Image.LANCZOS)
        img.paste(logo, (M - 10, 1590), logo)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--title", required=True)
    ap.add_argument("--hook", required=True)
    ap.add_argument("--frame", required=True, type=Path, help="a still from the video (1080x1920)")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    print(make_cover(a.title, a.hook, a.frame, a.out))
