#!/usr/bin/env python3
"""Writes the "Compare homes by price per sqft" reel (format: profiles/senang-homes/formats/animated-explainer.yaml).

    python tools/align.py && python tools/build.py

One object for the whole film: a comparison sheet with two drawn floor plans. Frame 0 already shows both
homes, their prices and "RM ??? psf" (the thumbnail question); the formula builds as the voice names it,
each psf counts up with its bar, sticky notes pin on for the checks, and the sheet drops away for the end
card. Times are absolute seconds from assets/vo/*.words.json + LINES.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMP = ROOT / "compositions"
W, H, FILM = 1080, 1920, 52.4
LINES = {"vo01": 0.30, "vo02": 5.90, "vo03": 11.00, "vo04": 17.90,
         "vo05": 25.00, "vo06": 32.00, "vo07": 37.90, "vo08": 46.20}
CLOSE = 45.15   # sheet leaves, end card starts

FOREST, IVORY, PEACH, TERRA, ORANGE, BEIGE, MUTED = (
    "#142E2B", "#F3F0E7", "#FFAA78", "#9A3418", "#F87947", "#E5DED0", "#5B6B66")
ORANGE_TEXT = "#B5531C"

FONTS = """
@font-face { font-family: "Outfit"; src: url("assets/fonts/Outfit-Regular.ttf"); font-weight: 400; }
@font-face { font-family: "Outfit"; src: url("assets/fonts/Outfit-Medium.ttf"); font-weight: 500; }
@font-face { font-family: "Outfit"; src: url("assets/fonts/Outfit-SemiBold.ttf"); font-weight: 600; }
@font-face { font-family: "Gelasio"; src: url("assets/fonts/Gelasio-MediumItalic.ttf"); font-weight: 500; font-style: italic; }
@font-face { font-family: "Caveat"; src: url("assets/fonts/Caveat.ttf"); font-weight: 400 700; }
"""

JS_HELPERS = """
    const tl = gsap.timeline({ paused: true });
    const words = (sel, t, gap = 0.07) => tl.fromTo(sel + " .hw", { opacity: 0, filter: "blur(10px)" },
      { opacity: 1, filter: "blur(0px)", duration: 0.18, ease: "power2.out", stagger: gap }, t);
    const sweep = (sel, t, d = 0.45) => tl.fromTo(sel, { scaleX: 0 }, { scaleX: 1, duration: d, ease: "power2.inOut", transformOrigin: "0% 50%" }, t);
    const pop = (sel, t, s = 0.08) => tl.fromTo(sel, { opacity: 0, scale: 0.3 }, { opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.2)", stagger: s }, t);
    const reveal = (sel, t, d = 0.6) => tl.fromTo(sel, { clipPath: "inset(-10% 100% -10% 0)" }, { clipPath: "inset(-10% 0% -10% 0)", duration: d, ease: "power2.inOut" }, t);
    const noteIn = (sel, t) => tl.fromTo(sel, { y: -760, rotation: 16 }, { y: 0, rotation: 0, duration: 0.55, ease: "back.out(1.3)" }, t);
    const noteOut = (sel, t) => tl.to(sel, { x: 700, rotation: 25, duration: 0.4, ease: "power3.in" }, t);
    const stamp = (sel, t, shake) => {
      tl.fromTo(sel, { opacity: 0, scale: 1.8, rotation: -26 }, { opacity: 0.92, scale: 1, rotation: -12, duration: 0.2, ease: "power4.out" }, t);
      if (shake) tl.to(shake, { keyframes: [{ x: -7, duration: 0.033 }, { x: 6, duration: 0.033 }, { x: -3, duration: 0.033 }, { x: 0, duration: 0.05 }] }, t + 0.18);
    };
    const strike = (sel, t) => tl.fromTo(sel, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power2.inOut", transformOrigin: "0% 50%" }, t);
    const draw = (sel, t, d = 1.0) => tl.fromTo(sel, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: d, ease: "power2.inOut" }, t);
    const pulse = (sel, t, s = 1.08) => tl.to(sel, { keyframes: [{ scale: s, duration: 0.14, ease: "power2.out" }, { scale: 1, duration: 0.3, ease: "power2.inOut" }] }, t);
    const count = (sel, to, t, d) => tl.fromTo(sel, { textContent: 0 }, { textContent: to, duration: d, ease: "power2.out", snap: { textContent: 1 }, immediateRender: false }, t);
"""

CSS = FONTS + f"""
.ground {{ position: absolute; inset: 0; background: {FOREST}; }}
.hw {{ display: inline-block; }}
"""


def sp(text: str) -> str:
    return " ".join(f'<span class="hw">{w}</span>' for w in text.split())


# ---------------------------------------------------------------- the comparison sheet (0 -> CLOSE + 0.6)
# sheet: x 120..960, y 480..1150 (840 x 670); all coordinates below are sheet-local.
COLS = {"a": 210, "b": 630}        # column centres
PLANS = {"a": (110, 360, 200, 160), "b": (507, 324, 245, 196)}   # x, y, w, h — area ratio 1.5 = 1,200 / 800
BARS = {"a": 300, "b": 240}        # psf bar widths, ratio 750 : 600


def column(k: str, label: str, price: str, size: str) -> str:
    c = COLS[k]
    x, y, w, h = PLANS[k]
    return f"""
      <div class="lab" id="{k}-lab" style="left:{c - 200}px">{label}<span class="ul" id="{k}-ul"></span></div>
      <div class="price" id="{k}-price" style="left:{c - 200}px"><span class="pv">{price}<span class="hl" id="{k}-phl"></span></span></div>
      <div class="pill" id="{k}-nett" style="left:{c + 74}px">nett</div>
      <div class="size" id="{k}-size" style="left:{x}px;width:{w}px;top:{y + h - 60}px"><span class="pv">{size}<span class="hl" id="{k}-shl"></span><span class="sul" id="{k}-sul"></span></span></div>
      <div class="psf" id="{k}-psf" style="left:{c - 200}px">RM<span id="{k}-n" class="num">???</span> psf</div>
      <div class="bar" id="{k}-bar" style="left:{c - BARS[k] // 2}px;width:{BARS[k]}px"></div>"""


def plan_svg() -> str:
    out = []
    for k, (x, y, w, h) in PLANS.items():
        # outline + two interior walls in the top half (labels sit in the bottom half)
        wx = x + int(w * 0.62)
        wy = y + int(h * 0.48)
        out.append(f'<g id="{k}-plan"><rect x="{x}" y="{y}" width="{w}" height="{h}" class="wall" pathLength="1"/>'
                   f'<path d="M{wx} {y} V{wy} H{x + w}" class="wall in" pathLength="1"/>'
                   f'<path d="M{x} {wy + 8} H{x + int(w * 0.30)}" class="wall in" pathLength="1"/></g>')
    return "".join(out)


SHEET = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; }}
    {CSS}
    .sheet-wrap {{ position: absolute; left: 120px; top: 480px; width: 840px; height: 670px; }}
    .sheet {{ position: absolute; inset: 0; background: {IVORY}; color: {FOREST}; box-shadow: 0 24px 48px rgba(0,0,0,.35); }}
    .hdr {{ position: absolute; left: 0; right: 0; top: 24px; text-align: center; font: 600 28px Outfit; letter-spacing: .14em; }}
    .rule {{ position: absolute; left: 40px; right: 40px; height: 0; border-top: 3px dotted #B9B2A3; }}
    .formula {{ position: absolute; left: 0; right: 0; top: 92px; text-align: center; font: 600 42px Outfit; white-space: nowrap; }}
    .formula .f {{ display: inline-block; opacity: .18; }}
    .formula .op {{ color: {ORANGE_TEXT}; margin: 0 6px; }}
    .lab {{ position: absolute; top: 186px; width: 400px; text-align: center; font: 600 28px Outfit; letter-spacing: .16em; color: {MUTED}; }}
    .lab .ul {{ position: absolute; left: 140px; right: 140px; bottom: -6px; height: 5px; background: {ORANGE}; }}
    .price {{ position: absolute; top: 222px; width: 400px; text-align: center; font: 600 46px Outfit; }}
    .pv {{ position: relative; display: inline-block; }}
    .hl {{ position: absolute; left: -10px; right: -10px; top: 4px; bottom: -2px; background: #FFD84D; opacity: .55; mix-blend-mode: multiply; }}
    .sul {{ position: absolute; left: 0; right: 0; bottom: -6px; height: 5px; background: {ORANGE}; }}
    .pill {{ position: absolute; top: 180px; padding: 0 10px; height: 38px; line-height: 36px; border-radius: 19px;
            background: {ORANGE}; color: {FOREST}; font: 600 28px Outfit; }}
    .size {{ position: absolute; text-align: center; font: 600 34px Outfit; line-height: 48px; }}
    svg.plans {{ position: absolute; left: 0; top: 0; width: 840px; height: 670px; overflow: visible; }}
    .wall {{ fill: none; stroke: {FOREST}; stroke-width: 6; stroke-dasharray: 1; stroke-dashoffset: 0; stroke-linejoin: miter; }}
    .wall.in {{ stroke-width: 4; }}
    .lot {{ position: absolute; left: 468px; top: 286px; width: 324px; height: 250px; border: 4px dashed {ORANGE_TEXT}; }}
    .lotlab {{ position: absolute; left: 480px; top: 288px; font: 600 28px Outfit; letter-spacing: .1em; color: {ORANGE_TEXT}; }}
    .lotlab .was {{ position: absolute; left: -6px; right: -6px; top: 50%; height: 5px; background: {TERRA}; border-radius: 3px; }}
    .psf {{ position: absolute; top: 548px; width: 400px; text-align: center; font: 600 42px Outfit; }}
    .psf .num {{ display: inline-block; min-width: 72px; }}
    .bar {{ position: absolute; top: 610px; height: 24px; background: {FOREST}; border-radius: 3px; }}
    #b-bar {{ background: {ORANGE}; }}
    .tick {{ position: absolute; left: 760px; top: 548px; width: 52px; height: 52px; border-radius: 26px; background: {ORANGE};
             color: {FOREST}; font: 600 34px/52px Outfit; text-align: center; }}
    .note-wrap {{ position: absolute; left: 660px; top: 246px; width: 300px; height: 220px; }}
    .note {{ position: absolute; inset: 0; background: {PEACH}; transform: rotate(4deg); padding: 18px 22px;
            box-shadow: 0 10px 18px rgba(0,0,0,.25); font: 600 44px/1.02 Caveat; color: {FOREST}; }}
    .note .ln {{ display: block; position: relative; width: fit-content; }}
    .note .x {{ position: absolute; left: -4px; right: -4px; top: 52%; height: 5px; background: {TERRA}; border-radius: 3px; }}
    .wstamp {{ position: absolute; left: 14px; top: 124px; padding: 4px 14px; border: 7px solid {TERRA};
              color: {TERRA}; font: 600 36px/1 Outfit; letter-spacing: .04em; mix-blend-mode: multiply; white-space: nowrap; }}
  </style>
  <div id="root" data-composition-id="sheet" data-width="{W}" data-height="{H}">
    <div class="ground"></div>
    <div class="sheet-wrap" id="s-paper"><div class="sheet">
      <div class="hdr">PRICE PER SQFT · ILLUSTRATION</div>
      <div class="rule" style="top:74px"></div>
      <div class="formula"><span class="f" id="f1">Price</span><span class="f op" id="f2">÷</span><span class="f" id="f3">built-up sqft</span><span class="f op" id="f4">=</span><span class="f" id="f5">psf</span></div>
      <div class="rule" style="top:166px"></div>
      <svg class="plans" viewBox="0 0 840 670">{plan_svg()}</svg>
      <div class="lot" id="lot"></div>
      <div class="lotlab" id="lotlab">LAND<span class="was" id="lot-was"></span></div>
      {column("a", "HOME A", "RM600,000", "800 sqft")}
      {column("b", "HOME B", "RM720,000", "1,200 sqft")}
      <div class="tick" id="b-tick">✓</div>
    </div></div>
    <div class="clip" id="n1c" data-start="28.30" data-duration="4.15" data-track-index="0"><div class="note-wrap" id="n1" data-layout-allow-occlusion><div class="note">
      <span class="ln" id="n1-a">Like with like:</span><span class="ln" id="n1-b">same area,</span><span class="ln" id="n1-c">similar homes</span></div></div></div>
    <div class="clip" id="n2c" data-start="32.00" data-duration="6.35" data-track-index="0"><div class="note-wrap" id="n2" data-layout-allow-occlusion><div class="note">
      <span class="ln">Land area</span><span class="ln">or built-up?</span><div class="wstamp" id="n2-stamp">DON'T MIX</div></div></div></div>
    <div class="clip" id="n3c" data-start="37.90" data-duration="3.90" data-track-index="0"><div class="note-wrap" id="n3" data-layout-allow-occlusion><div class="note">
      <span class="ln">Nett price =</span><span class="ln">the price</span><span class="ln" id="n3-b">minus rebates</span></div></div></div>
    <div class="clip" id="n4c" data-start="41.30" data-duration="4.30" data-track-index="0"><div class="note-wrap" id="n4" data-layout-allow-occlusion><div class="note">
      <span class="ln" id="n4-a">Transacted ✓</span><span class="ln" id="n4-b">nearby</span><span class="ln" id="n4-c">asking only<span class="x" id="n4-x"></span></span></div></div></div>
  </div>
  <script>
    {JS_HELPERS}
    // resting states (frame 0 = thumbnail: both homes, prices, plans and "RM ??? psf")
    // hook
    pulse("#a-plan", 0.34, 1.05); pulse("#b-plan", 0.64, 1.05);   // "Two homes"
    sweep("#b-phl", 1.48, 0.5);                                    // "pricier"
    pulse("#b-price", 2.85);                                       // "better deal"
    pulse("#a-psf", 3.91, 1.12); pulse("#b-psf", 4.05, 1.12);      // "one number"
    // formula
    tl.to("#f1", {{ opacity: 1, duration: 0.25 }}, 5.94);           // "Price"
    tl.to("#f5", {{ opacity: 1, duration: 0.25 }}, 6.30);           // "per square foot"
    tl.to("#f2", {{ opacity: 1, duration: 0.2 }}, 7.49); pop("#f2", 7.49);   // "Divide"
    tl.to("#f3", {{ opacity: 1, duration: 0.25 }}, 8.75);           // "built-up size"
    tl.to("#a-plan .wall, #b-plan .wall", {{ keyframes: [{{ stroke: "{ORANGE}", duration: 0.2 }}, {{ stroke: "{ORANGE}", duration: 0.6 }}, {{ stroke: "{FOREST}", duration: 0.3 }}] }}, 8.75);
    tl.to("#f4", {{ opacity: 1, duration: 0.2 }}, 9.67); pop("#f4", 9.67);   // "square feet"
    // home A
    sweep("#a-ul", 11.06, 0.35);                                   // "Home A"
    sweep("#a-phl", 11.78, 0.5);                                   // "six hundred thousand"
    sweep("#a-shl", 13.15, 0.5);                                   // "eight hundred"
    count("#a-n", 750, 15.15, 1.0); tl.fromTo("#a-bar", {{ scaleX: 0, transformOrigin: "0% 50%" }}, {{ scaleX: 1, duration: 1.0, ease: "power2.out" }}, 15.15);   // "750"
    // home B
    sweep("#b-ul", 17.96, 0.35);                                   // "Home B"
    pulse("#b-price", 18.78);                                      // "720,000" (already highlighted)
    sweep("#b-shl", 20.66, 0.5);                                   // "twelve hundred"
    count("#b-n", 600, 22.74, 0.9); tl.fromTo("#b-bar", {{ scaleX: 0, transformOrigin: "0% 50%" }}, {{ scaleX: 1, duration: 0.9, ease: "power2.out" }}, 22.74);   // "600"
    // B costs more, less per sqft
    pulse("#b-price", 25.51);                                      // "costs more"
    pulse("#b-psf", 27.65, 1.12); pop("#b-tick", 27.65);           // "costs less"
    noteIn("#n1", 28.36);                                          // "Compare like with like"
    reveal("#n1-b", 29.58, 0.45); reveal("#n1-c", 30.30, 0.5);     // "same area", "similar homes"
    // landed
    noteOut("#n1", 32.0); noteIn("#n2", 32.05);                    // "Landed home?"
    stamp("#n2-stamp", 33.11, "#n2");                              // "Don't mix"
    reveal("#lot", 33.73, 0.6); pop("#lotlab", 33.85);             // "land area"
    pulse("#b-plan", 34.52, 1.05); sweep("#b-sul", 34.52, 0.4);    // "built-up area"
    strike("#lot-was", 35.62); tl.to("#lot", {{ opacity: 0, duration: 0.4 }}, 35.75);   // "Use the same"
    sweep("#a-sul", 36.33, 0.4);                                   // "measure for both"
    // new launch: nett, transacted
    noteOut("#n2", 37.9); noteIn("#n3", 37.94);                    // "New launch?"
    pop("#a-nett, #b-nett", 39.13, 0.1);                           // "nett price"
    reveal("#n3-b", 40.15, 0.5);                                   // "rebates"
    noteOut("#n3", 41.3); noteIn("#n4", 41.35);                    // "Then check"
    reveal("#n4-a", 41.70, 0.5);                                   // "transacted"
    reveal("#n4-b", 42.89, 0.4);                                   // "nearby"
    reveal("#n4-c", 43.59, 0.4); strike("#n4-x", 44.17);           // "not just asking"
    // close: the sheet drops away
    tl.to("#s-paper", {{ y: 2000, rotation: 9, duration: 0.45, ease: "power3.in" }}, {CLOSE});
    tl.to("#n4", {{ y: 2100, rotation: -14, duration: 0.45, ease: "power3.in" }}, {CLOSE + 0.03});
    window.__timelines["sheet"] = tl;
  </script>
</template>
"""

# ---------------------------------------------------------------- headlines (one clip per beat)
HEADS = [  # (start, end, line a, line b)
    (0.0, 5.9, "Two homes", "which costs less?"),
    (5.9, 11.0, "Price per sqft", "the one number"),
    (11.0, 17.9, "Home A", "RM750 per sqft"),
    (17.9, 25.0, "Home B", "RM600 per sqft"),
    (25.0, 32.0, "B costs more", "less per sqft"),
    (32.0, 37.9, "Landed home?", "same measure"),
    (37.9, CLOSE, "New launch?", "use real prices"),
]


def heads_file() -> str:
    groups, js = [], []
    for i, (s, e, a, b) in enumerate(HEADS):
        groups.append(f'<div class="hg clip" id="h{i}" data-start="{s}" data-duration="{e - s:.2f}" data-track-index="0">'
                      f'<div class="label">Comparing homes</div><div class="a">{sp(a)}</div><div class="b">{sp(b)}</div></div>')
        if i:  # frame 0 is the thumbnail: the first headline is already on screen
            js.append(f'words("#h{i}", {s + 0.05:.2f});')
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; pointer-events: none; }}
    {FONTS}
    .hw {{ display: inline-block; }}
    .hg {{ position: absolute; left: 75px; top: 205px; width: 930px; }}
    .label {{ font: 500 28px Outfit; letter-spacing: .16em; color: {PEACH}; text-transform: uppercase; }}
    .a {{ margin-top: 12px; font: 600 84px/1 Outfit; letter-spacing: -0.01em; color: {IVORY}; }}
    .b {{ font: italic 500 72px/1.15 Gelasio; color: {PEACH}; margin-top: 6px; }}
  </style>
  <div id="root" data-composition-id="heads" data-width="{W}" data-height="{H}">
    {''.join(groups)}
  </div>
  <script>
    {JS_HELPERS}
    {chr(10).join('    ' + j for j in js)}
    window.__timelines["heads"] = tl;
  </script>
</template>
"""


# ---------------------------------------------------------------- end card (CLOSE -> FILM, local time)
def close_file() -> str:
    t = lambda abs_t: f"{abs_t - CLOSE:.2f}"
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    {CSS}
    .label {{ position: absolute; left: 75px; top: 205px; font: 500 28px Outfit; letter-spacing: .16em; color: {PEACH}; text-transform: uppercase; }}
    .head {{ position: absolute; left: 75px; top: 257px; width: 930px; }}
    .a {{ font: 600 84px/1 Outfit; letter-spacing: -0.01em; color: {IVORY}; }}
    .b {{ font: italic 500 72px/1.15 Gelasio; color: {PEACH}; margin-top: 6px; }}
  </style>
  <div id="root" data-composition-id="close" data-width="{W}" data-height="{H}">
    <div class="label">Comparing homes</div>
    <div class="head" id="c-head"><div class="a">{sp("Compare per sqft")}</div><div class="b">{sp("not by price alone")}</div></div>
    <div id="c-list" style="position:absolute;left:75px;top:520px;font:500 40px/1.5 Outfit;color:{IVORY}">
      <div class="li">Price ÷ built-up sqft</div><div class="li">Like with like</div><div class="li">Same size measure</div><div class="li">Nett, transacted prices</div></div>
    <div id="c-cta" style="position:absolute;left:75px;top:860px;width:760px;height:130px;background:{ORANGE};display:flex;align-items:center;padding-left:40px;font:600 62px Outfit;color:{FOREST}"><span id="c-ctat" style="display:inline-block">Comment "COMPARE"</span></div>
    <img id="c-logo" src="assets/horizontal-reverse.svg" style="position:absolute;left:62px;top:1030px;width:500px;height:100px" alt="Senang Homes"/>
  </div>
  <script>
    {JS_HELPERS}
    words("#c-head", 0.3);
    tl.fromTo("#c-list .li", {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "expo.out", stagger: 0.15 }}, 0.6);
    reveal("#c-cta", {t(46.22)}, 0.45);                            // "Comment"
    tl.fromTo("#c-ctat", {{ scale: 1 }}, {{ keyframes: [{{ scale: 1.1, duration: 0.12, ease: "power2.out" }}, {{ scale: 1, duration: 0.3, ease: "power2.inOut" }}] }}, {t(46.69)});  // "COMPARE"
    tl.fromTo("#c-logo", {{ opacity: 0, x: -70 }}, {{ opacity: 1, x: 0, duration: 0.6, ease: "expo.out" }}, {t(47.8)});
    window.__timelines["close"] = tl;
  </script>
</template>
"""


# ---------------------------------------------------------------- captions
def caption_groups():
    groups = []
    for vid, s in LINES.items():
        words = json.loads((ROOT / f"assets/vo/{vid}.words.json").read_text())
        cur = []
        for i, w in enumerate(words):
            text = w["text"]
            cur.append((text, s + w["start"], s + w["end"]))
            nxt = words[i + 1] if i + 1 < len(words) else None
            pause = nxt is not None and nxt["start"] - w["end"] >= 0.15
            if text[-1] in ".?!:," and len(cur) >= 2 or len(cur) == 5 or pause or nxt is None:
                if len(cur) == 1 and groups and groups[-1][2][-1][2] > s:
                    prev = groups.pop(); cur = prev[2] + cur
                groups.append((cur[0][1], cur[-1][2], cur))
                cur = []
    return groups


def captions_file() -> str:
    groups = caption_groups()
    html, js = [], []
    for gi, (gs, ge, words) in enumerate(groups):
        end = max(ge + 0.15, gs + 0.6)
        if gi + 1 < len(groups):
            end = min(end, groups[gi + 1][0])
        spans = "".join(f'<span class="w" id="cw{gi}-{wi}">{t}</span> ' for wi, (t, _, _) in enumerate(words))
        html.append(f'<div class="g clip" id="cg{gi}" data-start="{gs:.2f}" data-duration="{end - gs:.2f}" data-track-index="0">{spans.strip()}</div>')
        for wi, (_, ws, _) in enumerate(words):
            js.append(f'tl.set("#cw{gi}-{wi}", {{ color: "{PEACH}" }}, {ws:.2f}); tl.set("#cw{gi}-{wi}", {{ color: "{IVORY}" }}, {min(end, words[wi + 1][1] if wi + 1 < len(words) else end):.2f});')
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; pointer-events: none; }}
    {FONTS}
    .g {{ position: absolute; left: 90px; right: 90px; top: 1205px; text-align: center; font: 600 54px/1.15 Outfit; color: {IVORY}; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
    {chr(10).join('    ' + h for h in html)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join('    ' + j for j in js)}
    window.__timelines["captions"] = tl;
  </script>
</template>
"""


# ---------------------------------------------------------------- sound (no music bed: HeyGen catalog sign-in unavailable)
SFX = [  # (absolute start, file, volume, duration)
    (7.49, "click-soft", 0.28, 0.36), (9.67, "click-soft", 0.28, 0.36),
    (15.15, "typing", 0.16, 0.45), (22.74, "typing", 0.16, 0.45), (27.65, "pop", 0.25, 0.4),
    (28.36, "whoosh-short", 0.22, 0.57), (32.05, "whoosh", 0.22, 0.57), (33.11, "impact-bass-1", 0.30, 1.2),
    (37.94, "whoosh-short", 0.22, 0.57), (39.13, "pop", 0.22, 0.4), (41.35, "whoosh", 0.22, 0.57),
    (44.17, "click-soft", 0.26, 0.36), (CLOSE, "whoosh", 0.25, 0.57), (46.69, "impact-bass-2", 0.28, 1.5),
]


def index_file() -> str:
    hosts = [
        f'      <div id="sheet" data-composition-id="sheet" data-composition-src="compositions/sheet.html" data-start="0" data-duration="{CLOSE + 0.6:.2f}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>',
        f'      <div id="heads" data-composition-id="heads" data-composition-src="compositions/heads.html" data-start="0" data-duration="{CLOSE:.2f}" data-track-index="2" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:3"></div>',
        f'      <div id="close" data-composition-id="close" data-composition-src="compositions/close.html" data-start="{CLOSE}" data-duration="{FILM - CLOSE:.2f}" data-track-index="3" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:2"></div>',
        f'      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{FILM}" data-track-index="4" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:5"></div>',
    ]
    audio = [f'      <audio id="{vid}" class="clip" src="assets/vo/{vid}.wav" data-start="{s}" data-track-index="{10 + i}" data-volume="1"></audio>'
             for i, (vid, s) in enumerate(LINES.items())]
    for i, (t, name, vol, dur) in enumerate(SFX):
        ms = ' data-media-start="0.44"' if name == "typing" else ""
        audio.append(f'      <audio id="sfx{i:02d}" class="clip" src="assets/sfx/{name}.mp3" data-start="{t:.2f}" data-duration="{dur}"{ms} data-track-index="{30 + i}" data-volume="{vol}"></audio>')
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: {FOREST}; }}
      #root {{ position: relative; width: 100%; height: 100%; background: {FOREST}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{FILM}" data-width="{W}" data-height="{H}">
{chr(10).join(hosts)}
{chr(10).join(audio)}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""


if __name__ == "__main__":
    COMP.mkdir(exist_ok=True)
    (COMP / "sheet.html").write_text(SHEET, encoding="utf-8")
    (COMP / "heads.html").write_text(heads_file(), encoding="utf-8")
    (COMP / "close.html").write_text(close_file(), encoding="utf-8")
    (COMP / "captions.html").write_text(captions_file(), encoding="utf-8")
    (ROOT / "index.html").write_text(index_file(), encoding="utf-8")
    print(f"wrote sheet/heads/close/captions ({len(caption_groups())} caption groups), {len(SFX)} sfx, index.html")
