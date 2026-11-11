#!/usr/bin/env python3
"""Writes the "Costs on top of the price" reel (format: profiles/senang-homes/formats/animated-explainer.yaml).

    python tools/build.py

One object for the whole film: a receipt under a printer slot. Each cost prints as the voice names it,
a rolling odometer keeps the running total, sticky notes pin on for the asides, and the receipt drops
away for the end card. Times are absolute seconds from assets/vo/*.words.json + LINES.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMP = ROOT / "compositions"
W, H, FILM = 1080, 1920, 52.0
LINES = {"vo01": 0.30, "vo02": 6.20, "vo03": 13.10, "vo04": 20.00,
         "vo05": 25.40, "vo06": 32.70, "vo07": 39.30, "vo08": 45.00}
CLOSE = 44.9   # receipt leaves, end card starts

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
    const print = (sel, t) => tl.fromTo(sel, { clipPath: "inset(0 0 100% 0)", y: -10 }, { clipPath: "inset(0 0 0% 0)", y: 0, duration: 0.35, ease: "power2.out" }, t);
    const noteIn = (sel, t) => tl.fromTo(sel, { y: -760, rotation: 16 }, { y: 0, rotation: 0, duration: 0.55, ease: "back.out(1.3)" }, t);
    const noteOut = (sel, t) => tl.to(sel, { x: 700, rotation: 25, duration: 0.4, ease: "power3.in" }, t);
    const stamp = (sel, t, shake) => {
      tl.fromTo(sel, { opacity: 0, scale: 1.8, rotation: -26 }, { opacity: 0.92, scale: 1, rotation: -12, duration: 0.2, ease: "power4.out" }, t);
      if (shake) tl.to(shake, { keyframes: [{ x: -7, duration: 0.033 }, { x: 6, duration: 0.033 }, { x: -3, duration: 0.033 }, { x: 0, duration: 0.05 }] }, t + 0.18);
    };
    const strike = (sel, t) => tl.fromTo(sel, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power2.inOut", transformOrigin: "0% 50%" }, t);
    const count = (sel, to, t, d) => tl.fromTo(sel, { textContent: 0 }, { textContent: to, duration: d, ease: "power2.out", snap: { textContent: 1 } }, t);
"""

CSS = FONTS + f"""
.ground {{ position: absolute; inset: 0; background: {FOREST}; }}
.hw {{ display: inline-block; }}
.ch {{ display: inline-block; white-space: pre; }}
"""


def sp(text: str) -> str:
    return " ".join(f'<span class="hw">{w}</span>' for w in text.split())


# ---------------------------------------------------------------- the receipt (0 -> CLOSE + 0.5)
LH = 58   # odometer line height (px)
TOTAL_DIGITS = 5   # ##,###


def odometer() -> str:
    cols = []
    for i in range(TOTAL_DIGITS):
        strip = "".join(f"<div>{d}</div>" for d in range(10))
        cols.append(f'<span class="dg"><span class="strip" id="tot-d{i}">{strip}</span></span>')
        if i == 1:
            cols.append('<span class="comma">,</span>')
    return f'<span class="odo" id="tot" data-layout-allow-overflow>RM{"".join(cols)}</span>'


def row(rid: str, top: int, label: str, value: str, extra: str = "") -> str:
    return (f'<div class="row" id="{rid}" style="top:{top}px"><span class="k">{label}</span>'
            f'<span class="v" id="{rid}-v">{value}</span>{extra}</div>')


def waived(rid: str) -> str:
    return f'<span class="now" id="{rid}-now">RM0</span>'


ZIG = ", ".join(f"{i * 5}% {100 if i % 2 == 0 else 97.6}%" for i in range(21))
RECEIPT = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; }}
    {CSS}
    .slot {{ position: absolute; left: 150px; top: 446px; width: 780px; height: 34px; background: #0B1D1A;
            border-radius: 17px; box-shadow: inset 0 -6px 0 #2B4A45; }}
    .paper-wrap {{ position: absolute; left: 190px; top: 466px; width: 700px; height: 694px; }}
    .paper {{ position: absolute; inset: 0; background: {IVORY}; color: {FOREST};
             clip-path: polygon(0 0, 100% 0, 100% 97.6%, {ZIG}, 0 97.6%);
             box-shadow: 0 24px 48px rgba(0,0,0,.35); }}
    .hdr {{ position: absolute; left: 0; right: 0; top: 30px; text-align: center; font: 600 28px Outfit; letter-spacing: .14em; }}
    .rule {{ position: absolute; left: 40px; right: 40px; height: 0; border-top: 3px dotted #B9B2A3; }}
    .row {{ position: absolute; left: 40px; right: 40px; display: flex; justify-content: space-between; align-items: baseline; }}
    .row .k {{ font: 400 30px Outfit; color: #3F504C; }}
    .row .v {{ font: 600 32px Outfit; color: {FOREST}; position: relative; }}
    .split {{ position: absolute; left: 40px; right: 40px; top: 214px; height: 40px; display: flex; font: 600 28px Outfit; }}
    .split .b {{ flex: 0 0 90%; background: {FOREST}; color: {IVORY}; display: flex; align-items: center; padding-left: 14px; }}
    .split .y {{ flex: 1; background: {ORANGE}; color: {FOREST}; display: flex; align-items: center; justify-content: center; }}
    .scale {{ position: absolute; left: 40px; top: 382px; font: italic 500 28px Gelasio; color: {MUTED}; }}
    .total {{ position: absolute; left: 40px; right: 40px; top: 566px; display: flex; justify-content: space-between; align-items: center; }}
    .total .k {{ font: 600 30px Outfit; }}
    .odo {{ font: 600 48px/{LH}px Outfit; color: {FOREST}; display: inline-flex; align-items: flex-start; height: {LH}px; }}
    .dg {{ display: inline-block; width: 29px; text-align: center; height: {LH}px; overflow: hidden; font-variant-numeric: tabular-nums; }}
    .strip {{ display: block; }}
    .strip div {{ height: {LH}px; }}
    .comma {{ display: inline-block; width: 13px; }}
    .foot {{ position: absolute; left: 40px; top: 638px; font: 400 28px Outfit; color: {MUTED}; }}
    .hl {{ position: absolute; left: -10px; right: -10px; top: 2px; bottom: -4px; background: #FFD84D; opacity: .55; mix-blend-mode: multiply; }}
    .was {{ position: absolute; left: -6px; right: -6px; top: 50%; height: 6px; background: {TERRA}; border-radius: 3px; }}
    .now {{ position: absolute; right: 150px; top: 0; color: {ORANGE_TEXT}; font: 600 32px Outfit; }}
    .note-wrap {{ position: absolute; left: 680px; top: 300px; width: 300px; height: 210px; }}
    .note {{ position: absolute; inset: 0; background: {PEACH}; transform: rotate(4deg); padding: 20px 22px;
            box-shadow: 0 10px 18px rgba(0,0,0,.25); font: 600 42px/1 Caveat; color: {FOREST}; }}
    .wstamp {{ position: absolute; left: 52px; top: 118px; padding: 4px 16px; border: 7px solid {ORANGE_TEXT};
              color: {ORANGE_TEXT}; font: 600 46px/1 Outfit; letter-spacing: .08em; mix-blend-mode: multiply; }}
  </style>
  <div id="root" data-composition-id="receipt" data-width="{W}" data-height="{H}">
    <div class="ground"></div>
    <div class="paper-wrap" id="r-paper"><div class="paper">
      <div class="hdr">HOME PURCHASE · ILLUSTRATION</div>
      <div class="rule" style="top:82px"></div>
      {row("r0", 96, "Home price", f'RM500,000<span class="hl" id="r0-hl"></span>')}
      <div class="rule" style="top:152px"></div>
      {row("r1", 166, "Down payment (10%)", "RM50,000")}
      <div class="split" id="r1-split"><span class="b" id="r1-b">Bank lends 90%</span><span class="y" id="r1-y">10%</span></div>
      {row("r2", 272, "Legal fee: sale agreement", f'RM6,250<span class="hl" id="r2-hl"></span>')}
      {row("r3", 330, "Legal fee: loan", f'RM5,625<span class="hl" id="r3-hl"></span>')}
      <div class="scale" id="r-scale">Scale: 1.25% of the first RM500K</div>
      {row("r4", 430, "Stamp duty: transfer", 'RM9,000<span class="was" id="r4-was"></span>', waived("r4"))}
      {row("r5", 488, "Stamp duty: loan (0.5%)", 'RM2,250<span class="was" id="r5-was"></span>', waived("r5"))}
      <div class="rule" id="r-rule2" style="top:548px;border-top:3px dashed {FOREST}"></div>
      <div class="total" id="r-total"><span class="k">On top of the loan</span>{odometer()}</div>
      <div class="foot" id="r-foot">Fees before SST &amp; disbursements</div>
    </div></div>
    <div class="slot" id="r-slot"></div>
    <div class="clip" id="n1c" data-start="28.2" data-duration="4.9" data-track-index="0"><div class="note-wrap" id="n1" data-layout-allow-occlusion><div class="note">+ furnishing<br>+ renovation<br>+ utility deposits</div></div></div>
    <div class="clip" id="n2c" data-start="32.65" data-duration="7.05" data-track-index="0"><div class="note-wrap" id="n2" data-layout-allow-occlusion><div class="note">First home,<br>RM500K or less?<div style="font-size:29px;margin-top:4px;white-space:nowrap">*if eligible, to 2027</div><div class="wstamp" id="n2-stamp" style="top:150px;font-size:40px">WAIVED*</div></div></div></div>
    <div class="clip" id="n3c" data-start="41.95" data-duration="3.55" data-track-index="0"><div class="note-wrap" id="n3" data-layout-allow-occlusion><div class="note">Ask: are legal<br>fees included?</div></div></div>
  </div>
  <script>
    {JS_HELPERS}
    const odo = (value, t) => {{
      const s = String(value).padStart({TOTAL_DIGITS}, "0");
      for (let i = 0; i < {TOTAL_DIGITS}; i++)
        tl.to("#tot-d" + i, {{ y: -Number(s[i]) * {LH}, duration: 0.7, ease: "power3.inOut" }}, t + i * 0.06);
    }};
    // resting states
    tl.set("#tot [id^=tot-d]", {{ y: 0 }}, 0);
    // hook: the price, then "not all you'll pay"
    sweep("#r0-hl", 1.0, 0.5);                                     // "RM500,000"
    tl.to("#r-slot", {{ keyframes: [{{ y: -3, duration: 0.05 }}, {{ y: 2, duration: 0.05 }}, {{ y: 0, duration: 0.06 }}] }}, 2.86);   // "not all"
    print("#r-rule2", 3.98);                                       // "what goes on top"
    // down payment
    print("#r1", 7.1); print("#r-total", 11.0);                     // "down payment"
    reveal("#r1-b", 8.9, 0.6); pop("#r1-y", 10.3);                 // "90%" ... "bring 10"
    odo(50000, 11.25);                                             // "50,000"
    // legal fees
    print("#r2", 14.85); print("#r3", 15.6);                       // "sale agreement", "loan"
    reveal("#r-scale", 16.6, 0.6);                                 // "fixed scale"
    odo(61875, 17.8);                                              // "about 12,000"
    // stamp duty
    print("#r4", 20.3); odo(70875, 21.3);                          // "stamp duty", "9,000"
    print("#r5", 23.25); odo(73125, 24.0);                         // "half a percent"
    // the total, then moving-in costs
    tl.to("#r-total", {{ keyframes: [{{ scale: 1.06, duration: 0.15, ease: "power2.out" }}, {{ scale: 1, duration: 0.3 }}] }}, 25.9);  // "RM73,000"
    reveal("#r-foot", 26.4, 0.6);
    noteIn("#n1", 28.3);                                           // "Then furnishing"
    // first home: stamp duties waived if you qualify
    noteOut("#n1", 32.6); noteIn("#n2", 32.7);                     // "First home"
    stamp("#n2-stamp", 37.8, "#n2");                               // "waived"
    strike("#r4-was", 37.85); strike("#r5-was", 37.95);
    pop("#r4-now", 38.05); pop("#r5-now", 38.15);
    odo(61875, 38.3);
    // packages
    noteOut("#n2", 39.2);
    sweep("#r2-hl", 40.55, 0.45); sweep("#r3-hl", 40.75, 0.45);    // "cover your legal fees"
    noteIn("#n3", 42.0);                                           // "Ask what the package includes"
    // close: the receipt drops away
    tl.to("#r-paper", {{ y: 2000, rotation: 9, duration: 0.45, ease: "power3.in" }}, {CLOSE});
    tl.to("#n3", {{ y: 2100, rotation: -14, duration: 0.45, ease: "power3.in" }}, {CLOSE + 0.03});
    tl.to("#r-slot", {{ opacity: 0, duration: 0.3 }}, {CLOSE});
    window.__timelines["receipt"] = tl;
  </script>
</template>
"""

# ---------------------------------------------------------------- headlines (one clip per beat)
HEADS = [  # (start, end, line a, line b)
    (0.0, 6.2, "RM500K home?", "here's the real bill"),
    (6.2, 13.1, "Down payment", "usually 10%"),
    (13.1, 20.0, "Legal fees", "on a fixed scale"),
    (20.0, 25.4, "Stamp duty", "transfer + loan"),
    (25.4, 32.7, "Before move-in", "over RM73K"),
    (32.7, 39.3, "First home?", "may be waived"),
    (39.3, CLOSE, "New launch?", "check the package"),
]


def heads_file() -> str:
    groups, js = [], []
    for i, (s, e, a, b) in enumerate(HEADS):
        groups.append(f'<div class="hg clip" id="h{i}" data-start="{s}" data-duration="{e - s:.2f}" data-track-index="0">'
                      f'<div class="label">Before you buy</div><div class="a">{sp(a)}</div><div class="b">{sp(b)}</div></div>')
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
    <div class="label">Before you buy</div>
    <div class="head" id="c-head"><div class="a">{sp("Know the real bill")}</div><div class="b">{sp("before you book")}</div></div>
    <div id="c-list" style="position:absolute;left:75px;top:520px;font:500 40px/1.5 Outfit;color:{IVORY}">
      <div class="li">Down payment</div><div class="li">Legal fees</div><div class="li">Stamp duty</div><div class="li">Moving-in costs</div></div>
    <div id="c-cta" style="position:absolute;left:75px;top:860px;width:760px;height:130px;background:{ORANGE};display:flex;align-items:center;padding-left:40px;font:600 62px Outfit;color:{FOREST}"><span id="c-ctat" style="display:inline-block">Comment "COST"</span></div>
    <img id="c-logo" src="assets/horizontal-reverse.svg" style="position:absolute;left:62px;top:1030px;width:500px;height:100px" alt="Senang Homes"/>
  </div>
  <script>
    {JS_HELPERS}
    words("#c-head", 0.3);
    tl.fromTo("#c-list .li", {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "expo.out", stagger: 0.15 }}, 0.6);
    reveal("#c-cta", {t(45.0)}, 0.45);                             // "Comment"
    tl.fromTo("#c-ctat", {{ scale: 1 }}, {{ keyframes: [{{ scale: 1.12, duration: 0.12, ease: "power2.out" }}, {{ scale: 1, duration: 0.3, ease: "power2.inOut" }}] }}, {t(45.48)});  // "COST"
    tl.fromTo("#c-logo", {{ opacity: 0, x: -70 }}, {{ opacity: 1, x: 0, duration: 0.6, ease: "expo.out" }}, {t(46.6)});
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


# ---------------------------------------------------------------- sound
SFX = [  # (absolute start, file, volume, duration)
    (7.10, "typing", 0.16, 0.45), (14.85, "typing", 0.16, 0.45), (15.60, "click-soft", 0.28, 0.36),
    (20.30, "typing", 0.16, 0.45), (23.25, "click-soft", 0.28, 0.36),
    (28.30, "whoosh-short", 0.22, 0.57), (32.70, "whoosh", 0.22, 0.57), (37.80, "impact-bass-1", 0.30, 1.2),
    (42.00, "whoosh-short", 0.22, 0.57), (CLOSE, "whoosh", 0.25, 0.57), (45.48, "impact-bass-2", 0.28, 1.5),
]


def index_file() -> str:
    hosts = [
        f'      <div id="receipt" data-composition-id="receipt" data-composition-src="compositions/receipt.html" data-start="0" data-duration="{CLOSE + 0.6:.2f}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>',
        f'      <div id="heads" data-composition-id="heads" data-composition-src="compositions/heads.html" data-start="0" data-duration="{CLOSE:.2f}" data-track-index="2" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:3"></div>',
        f'      <div id="close" data-composition-id="close" data-composition-src="compositions/close.html" data-start="{CLOSE}" data-duration="{FILM - CLOSE:.2f}" data-track-index="3" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:2"></div>',
        f'      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{FILM}" data-track-index="4" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:5"></div>',
    ]
    audio = [f'      <audio id="{vid}" class="clip" src="assets/vo/{vid}.wav" data-start="{s}" data-track-index="{10 + i}" data-volume="1"></audio>'
             for i, (vid, s) in enumerate(LINES.items())]
    audio.append(f'      <audio id="bgm" class="clip" src="assets/bgm/track.mp3" data-start="0" data-duration="{FILM}" data-track-index="20" data-volume="0.14" data-fade-in="0.3" data-fade-out="2.5"></audio>')
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
    (COMP / "receipt.html").write_text(RECEIPT, encoding="utf-8")
    (COMP / "heads.html").write_text(heads_file(), encoding="utf-8")
    (COMP / "close.html").write_text(close_file(), encoding="utf-8")
    (COMP / "captions.html").write_text(captions_file(), encoding="utf-8")
    (ROOT / "index.html").write_text(index_file(), encoding="utf-8")
    print(f"wrote receipt/heads/close/captions ({len(caption_groups())} caption groups), {len(SFX)} sfx, index.html")
