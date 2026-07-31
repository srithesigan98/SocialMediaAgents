#!/usr/bin/env python3
"""Renders a Black Panther poster locally with Pillow — no Canva account/API needed.

Matches the locked style spec in ../../design/poster-style-guide.md (shared with Hulk/Blue Hulk):
dark near-black background, a single accent color, a subtle decorative candlestick-chart
texture, and four text slots (top label / headline / body lines / footer). Produces a PNG file
on disk; the caller (daily_post.py) commits it to the repo and posts the resulting raw
GitHub URL to Instagram, since the Instagram Graph API requires a publicly reachable image URL
and does not accept local file uploads.

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


# --- Striker Zones poster variant --------------------------------------------------------
# Mimics the real "Striker Zones 2.1 Pro" TradingView indicator's look (light theme, teal
# entry/SL risk box, orange/green TP labels) instead of the generic dark candlestick poster
# above. Levels are ALWAYS synthetic/illustrative (see compute_illustrative_levels) — this
# poster must never present fabricated numbers as a real live signal.

STRIKER_BG = (227, 229, 231)
STRIKER_TEXT_DARK = (28, 31, 34)
STRIKER_MUTED = (110, 116, 122)
STRIKER_GRID_LINE = (70, 72, 74)
STRIKER_CANDLE_UP_FILL = (255, 255, 255)
STRIKER_CANDLE_DOWN_FILL = (35, 37, 39)
STRIKER_TRAIL_COLOR = (0, 150, 136)
STRIKER_ZONE_FILL = (0, 150, 136, 60)
STRIKER_ENTRY_COLOR = (0, 105, 92)
STRIKER_SL_COLOR = (211, 47, 47)
STRIKER_TP1_COLOR = (245, 166, 35)
STRIKER_TP2_COLOR = (46, 204, 113)
STRIKER_TP3_COLOR = (27, 122, 68)

_STRIKER_SYMBOLS = [
    {"label": "XAU/USD", "base_range": (3900, 4300), "decimals": 2},
    {"label": "BTC/USD", "base_range": (58000, 95000), "decimals": 2},
    {"label": "EUR/USD", "base_range": (1.02, 1.15), "decimals": 4},
    {"label": "US30", "base_range": (38000, 46000), "decimals": 1},
]


def compute_illustrative_levels(seed: int) -> dict:
    """Synthetic, illustrative-only price levels for the Striker Zones poster — never real
    market data. Mirrors the real indicator's rough TP spacing (~1R / ~2R / ~3.3R from entry)."""
    rng = random.Random(seed)
    sym = _STRIKER_SYMBOLS[seed % len(_STRIKER_SYMBOLS)]
    lo, hi = sym["base_range"]
    entry = rng.uniform(lo, hi)
    risk_unit = entry * rng.uniform(0.003, 0.006)
    d = sym["decimals"]
    return {
        "symbol_label": sym["label"],
        "entry": round(entry, d),
        "sl": round(entry - risk_unit, d),
        "tp1": round(entry + risk_unit * 1.0, d),
        "tp2": round(entry + risk_unit * 2.0, d),
        "tp3": round(entry + risk_unit * 3.33, d),
        "decimals": d,
    }


def _fmt_price(value: float, decimals: int) -> str:
    return f"{value:,.{decimals}f}"


def _draw_price_pill(
    draw: ImageDraw.ImageDraw,
    y: float,
    text: str,
    fill_color: tuple,
    font: ImageFont.FreeTypeFont,
    line_from_x: float,
    pill_h: int = 50,
) -> None:
    tw = draw.textlength(text, font=font)
    pill_w = tw + 48
    x2 = WIDTH - MARGIN
    x1 = x2 - pill_w
    draw.line([(line_from_x, y), (x1, y)], fill=STRIKER_GRID_LINE, width=1)
    draw.rounded_rectangle([x1, y - pill_h / 2, x2, y + pill_h / 2], radius=pill_h / 2, fill=fill_color)
    th = font.size
    draw.text((x1 + (pill_w - tw) / 2, y - th / 2 - 2), text, font=font, fill=(255, 255, 255))


def render_striker_poster(
    symbol_label: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float,
    tp3: float,
    decimals: int,
    out_path: Path,
    seed: int = 0,
) -> Path:
    img = Image.new("RGB", (WIDTH, HEIGHT), STRIKER_BG)
    draw = ImageDraw.Draw(img, "RGBA")

    font_brand = _find_font(_FONT_CANDIDATES_BOLD, 30)
    font_symbol = _find_font(_FONT_CANDIDATES_BOLD, 52)
    font_muted = _find_font(_FONT_CANDIDATES_REGULAR, 24)
    font_pill = _find_font(_FONT_CANDIDATES_BOLD, 24)
    font_footer_muted = _find_font(_FONT_CANDIDATES_REGULAR, 22)
    font_footer_cta = _find_font(_FONT_CANDIDATES_BOLD, 30)

    draw.text((MARGIN, 66), "STRIKER ZONES", font=font_brand, fill=STRIKER_ENTRY_COLOR)
    draw.text((MARGIN, 108), symbol_label, font=font_symbol, fill=STRIKER_TEXT_DARK)
    draw.text((MARGIN, 178), "Illustrative example setup — not a live signal", font=font_muted, fill=STRIKER_MUTED)

    chart_top, chart_bottom = 240, HEIGHT - 190
    price_pad = (tp3 - sl) * 0.10
    price_min, price_max = sl - price_pad, tp3 + price_pad

    def price_to_y(price: float) -> float:
        frac = (price - price_min) / (price_max - price_min)
        return chart_bottom - frac * (chart_bottom - chart_top)

    # Synthetic candlestick rally from near SL up toward Entry, with a breakout tail toward TP1.
    rng = random.Random(seed)
    n = 16
    chart_left, chart_right = MARGIN, WIDTH * 0.42
    step = (chart_right - chart_left) / n
    trail_points = []
    price = sl + (entry - sl) * 0.15
    for i in range(n):
        x = chart_left + i * step
        open_p = price
        drift = (entry - sl) / n * rng.uniform(0.6, 1.6)
        if i >= n - 3:
            drift += (tp1 - entry) / 3 * rng.uniform(0.5, 1.1)  # breakout tail near the end
        price = open_p + drift
        close_p = price
        high = max(open_p, close_p) + abs(drift) * rng.uniform(0.05, 0.3)
        low = min(open_p, close_p) - abs(drift) * rng.uniform(0.05, 0.3)
        y_open, y_close = price_to_y(open_p), price_to_y(close_p)
        y_high, y_low = price_to_y(high), price_to_y(low)
        cx = x + step * 0.4
        draw.line([(cx, y_high), (cx, y_low)], fill=(40, 40, 40), width=2)
        top, bottom = sorted([y_open, y_close])
        fill = STRIKER_CANDLE_UP_FILL if close_p >= open_p else STRIKER_CANDLE_DOWN_FILL
        draw.rectangle([x + step * 0.15, top, x + step * 0.65, max(bottom, top + 4)], fill=fill, outline=(40, 40, 40))
        trail_points.append((cx, min(y_open, y_close) - 6))
    if len(trail_points) > 1:
        draw.line(trail_points, fill=STRIKER_TRAIL_COLOR, width=3)

    # Entry -> SL risk zone (shaded box) + leader-line price pills.
    zone_left = WIDTH * 0.34
    draw.rectangle([zone_left, price_to_y(entry), WIDTH - MARGIN, price_to_y(sl)], fill=STRIKER_ZONE_FILL)
    draw.rectangle(
        [zone_left, price_to_y(entry), WIDTH - MARGIN, price_to_y(sl)],
        outline=STRIKER_ENTRY_COLOR, width=2,
    )

    _draw_price_pill(draw, price_to_y(tp3), f"TP Striker 3 : {_fmt_price(tp3, decimals)}", STRIKER_TP3_COLOR, font_pill, chart_left)
    _draw_price_pill(draw, price_to_y(tp2), f"TP Striker 2 : {_fmt_price(tp2, decimals)}", STRIKER_TP2_COLOR, font_pill, chart_left)
    _draw_price_pill(draw, price_to_y(tp1), f"TP Striker 1 : {_fmt_price(tp1, decimals)}", STRIKER_TP1_COLOR, font_pill, chart_left)
    _draw_price_pill(draw, price_to_y(entry), f"ENTRY : {_fmt_price(entry, decimals)}", STRIKER_ENTRY_COLOR, font_pill, zone_left)
    _draw_price_pill(draw, price_to_y(sl), f"SL : {_fmt_price(sl, decimals)}", STRIKER_SL_COLOR, font_pill, zone_left)

    footer_y = HEIGHT - 150
    draw.line([(MARGIN, footer_y), (WIDTH - MARGIN, footer_y)], fill=STRIKER_ENTRY_COLOR, width=2)
    draw.text((MARGIN, footer_y + 20), "Join Striker Zones", font=font_footer_cta, fill=STRIKER_ENTRY_COLOR)
    draw.text((MARGIN, footer_y + 60), "t.me/strikerzonesadmin_bot", font=font_footer_cta, fill=STRIKER_TEXT_DARK)
    draw.text(
        (MARGIN, footer_y + 102),
        "Illustrative example only — not a live signal or trade call.",
        font=font_footer_muted, fill=STRIKER_MUTED,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    args = sys.argv[1:]
    top_label = args[0] if len(args) > 0 else "Trading Psychology"
    headline = args[1] if len(args) > 1 else "Most traders blow up the same way"
    body = [args[2]] if len(args) > 2 else ["Position size kills more accounts than bad ideas."]
    footer = args[3] if len(args) > 3 else "What's your leverage lesson?"
    out = render_poster(top_label, headline, body, footer, Path("drafts/poster-preview.png"))
    print(f"Rendered: {out.resolve()}")
