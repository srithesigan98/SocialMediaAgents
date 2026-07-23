#!/usr/bin/env python3
"""Renders a Blue Hulk poster locally with Pillow — no Canva account/API needed.

Matches the locked style spec in ../../design/poster-style-guide.md: dark near-black
background, a single accent color, a subtle decorative candlestick-chart texture, and four
text slots (top label / headline / body lines / footer). Produces a PNG file on disk; the
caller (daily_post.py) uploads that file directly to Facebook — no image hosting required.

Standalone-testable:
    python render_poster.py "BTC — testing resistance" "Most traders blow up the same way" \
        "Position size kills more accounts than bad ideas." "What's your leverage lesson?"
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1350  # matches the style guide's Instagram-portrait spec

BG_COLOR = (11, 15, 18)
ACCENT_COLOR = (63, 185, 80)  # electric green — matches Hulk/Blue Hulk brand green
TEXT_WHITE = (240, 244, 240)
TEXT_MUTED = (150, 165, 160)

MARGIN = 70

_FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]
_FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
]


def _find_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_candlestick_texture(draw: ImageDraw.ImageDraw, seed: int) -> None:
    """Decorative synthetic candlesticks — not real market data, just the locked-spec texture."""
    rng = random.Random(seed)
    n = 26
    usable_w = WIDTH - 2 * MARGIN
    step = usable_w / n
    baseline_y = 230.0
    price = 40.0
    faded = ACCENT_COLOR + (55,)
    for i in range(n):
        x = MARGIN + i * step
        open_p = price
        price += rng.uniform(-9, 9)
        close_p = price
        high = max(open_p, close_p) + rng.uniform(0, 5)
        low = min(open_p, close_p) - rng.uniform(0, 5)
        y_high, y_low = baseline_y - high, baseline_y - low
        y_open, y_close = baseline_y - open_p, baseline_y - close_p
        draw.line([(x + step * 0.4, y_high), (x + step * 0.4, y_low)], fill=faded, width=2)
        top, bottom = sorted([y_open, y_close])
        draw.rectangle([x + step * 0.15, top, x + step * 0.65, max(bottom, top + 3)], fill=faded)


def render_poster(
    top_label: str,
    headline: str,
    body_lines: list[str],
    footer: str,
    out_path: Path,
    seed: int = 0,
) -> Path:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    _draw_candlestick_texture(draw, seed)

    font_label = _find_font(_FONT_CANDIDATES_BOLD, 32)
    font_headline = _find_font(_FONT_CANDIDATES_BOLD, 72)
    font_body = _find_font(_FONT_CANDIDATES_REGULAR, 38)
    font_footer = _find_font(_FONT_CANDIDATES_REGULAR, 28)

    max_width = WIDTH - 2 * MARGIN
    y = 340.0

    draw.text((MARGIN, y), top_label.upper(), font=font_label, fill=ACCENT_COLOR)
    y += 64

    for line in _wrap_text(draw, headline, font_headline, max_width):
        draw.text((MARGIN, y), line, font=font_headline, fill=TEXT_WHITE)
        y += 86
    y += 28

    for body in body_lines:
        for line in _wrap_text(draw, body, font_body, max_width):
            draw.text((MARGIN, y), line, font=font_body, fill=TEXT_MUTED)
            y += 50
        y += 14

    footer_y = HEIGHT - 130
    draw.line([(MARGIN, footer_y - 26), (WIDTH - MARGIN, footer_y - 26)], fill=ACCENT_COLOR, width=2)
    for line in _wrap_text(draw, footer, font_footer, max_width):
        draw.text((MARGIN, footer_y), line, font=font_footer, fill=ACCENT_COLOR)
        footer_y += 38

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    args = sys.argv[1:]
    top_label = args[0] if len(args) > 0 else "Trading Psychology"
    headline = args[1] if len(args) > 1 else "Most traders blow up the same way"
    body = [args[2]] if len(args) > 2 else ["Position size kills more accounts than bad ideas."]
    footer = args[3] if len(args) > 3 else "What's your leverage lesson? Comment below."
    out = render_poster(top_label, headline, body, footer, Path("drafts/poster-preview.png"))
    print(f"Rendered: {out.resolve()}")
