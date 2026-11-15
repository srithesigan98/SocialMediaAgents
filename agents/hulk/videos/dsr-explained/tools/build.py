#!/usr/bin/env python3
"""Writes the "Why banks reject home loans: your DSR" reel (format: profiles/senang-homes/formats/animated-explainer.yaml).

    python tools/align.py && python tools/build.py

One object for the whole film: a balance scale on an ivory sheet, monthly debts on the left pan, net income on
the right. Frame 0 already shows the loaded scale tipping toward the debts with "DSR ??%" (the thumbnail
question). The debts clear and re-stack one by one as the voice names them, the beam tips with every block,
the DSR counts up with its meter, sticky notes pin on for the card rule and the fixes, and the same home ends
at 44%. Times are absolute seconds from assets/vo/*.words.json + LINES.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMP = ROOT / "compositions"
W, H, FILM = 1080, 1920, 57.4
LINES = {"vo01": 0.30, "vo02": 6.50, "vo03": 13.90, "vo04": 22.80, "vo05": 28.70,
         "vo06": 35.00, "vo07": 39.90, "vo08": 45.40, "vo09": 51.30}
CLOSE = 50.6    # sheet leaves, end card starts

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
    const pulse = (sel, t, s = 1.08) => tl.to(sel, { keyframes: [{ scale: s, duration: 0.14, ease: "power2.out" }, { scale: 1, duration: 0.3, ease: "power2.inOut" }] }, t);
    const count = (sel, from, to, t, d) => tl.fromTo(sel, { textContent: from }, { textContent: to, duration: d, ease: "power2.out", snap: { textContent: 1 }, immediateRender: false }, t);
"""

CSS = FONTS + f"""
.ground {{ position: absolute; inset: 0; background: {FOREST}; }}
.hw {{ display: inline-block; }}
"""


def sp(text: str) -> str:
    return " ".join(f'<span class="hw">{w}</span>' for w in text.split())


# ---------------------------------------------------------------- the balance scale (0 -> CLOSE + 0.6)
# sheet: x 120..960, y 480..1150 (840 x 670); coordinates below are sheet-local.
# beam pivot (420, 230), half-length L = 255; pans hang from (165, 230) and (675, 230); pan floor at y 430.
L = 255
BLOCK_H = 44
DEBTS = [  # bottom -> top: (id, label, amount)
    ("car", "Car loan", "RM800"), ("ptp", "PTPTN", "RM200"), ("home", "Home loan", "RM2,000"), ("card", "Card", "RM500")]


def debt_blocks() -> str:
    out = []
    for i, (k, lab, amt) in enumerate(DEBTS):
        top = 430 - BLOCK_H * (i + 1)
        out.append(f'<div class="blk{" card" if k == "card" else ""}" id="b-{k}" style="top:{top}px">'
                   f'<span>{lab}</span><span>{amt}</span></div>')
    return "".join(out)


import math
A0 = (70 - 40) * 0.30
DY0 = L * math.sin(math.radians(A0))
STRINGS = '<svg class="str" viewBox="0 0 300 440"><path d="M150 196 L4 430 M150 196 L296 430"/></svg>'

SCALE = f"""<template>
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
    .tag {{ position: absolute; left: 40px; top: 146px; padding: 0 12px; height: 38px; line-height: 36px; border-radius: 19px;
            background: {ORANGE}; color: {FOREST}; font: 600 28px Outfit; }}
    .beam {{ position: absolute; left: 165px; top: 192px; width: 510px; height: 8px; background: {FOREST}; border-radius: 4px; }}
    .cap {{ position: absolute; left: 406px; top: 182px; width: 28px; height: 28px; border-radius: 14px; background: {ORANGE}; border: 5px solid {FOREST}; }}
    .post {{ position: absolute; left: 413px; top: 206px; width: 14px; height: 226px; background: {FOREST}; }}
    .base {{ position: absolute; left: 350px; top: 428px; width: 140px; height: 16px; background: {FOREST}; border-radius: 8px 8px 0 0; }}
    .pan {{ position: absolute; top: 0; width: 300px; height: 440px; }}
    #epf, #tick, #lim, #leftlab, #left {{ opacity: 0; }}
    .str {{ position: absolute; left: 0; top: 0; width: 300px; height: 440px; overflow: visible; }}
    .str path {{ fill: none; stroke: {MUTED}; stroke-width: 3; }}
    .tray {{ position: absolute; left: 0; top: 430px; width: 300px; height: 10px; background: {FOREST}; border-radius: 0 0 6px 6px; }}
    .blk {{ position: absolute; left: 4px; width: 292px; gap: 14px; height: {BLOCK_H - 2}px; background: {FOREST}; color: {IVORY};
            display: flex; justify-content: space-between; align-items: center; padding: 0 12px; font: 600 28px Outfit; border-radius: 3px; white-space: nowrap; }}
    .blk.card {{ background: {ORANGE}; color: {FOREST}; }}
    .inc {{ position: absolute; left: 4px; top: 318px; width: 292px; height: 110px; background: {PEACH}; color: {FOREST};
            border-radius: 3px; text-align: center; padding-top: 12px; }}
    .inc .l {{ font: 600 28px Outfit; letter-spacing: .12em; }}
    .inc .v {{ position: relative; display: inline-block; font: 600 46px Outfit; margin-top: 2px; }}
    .hl {{ position: absolute; left: -10px; right: -10px; top: 6px; bottom: 0; background: #FFD84D; opacity: .55; mix-blend-mode: multiply; }}
    .ro1 {{ position: absolute; left: 330px; right: 20px; top: 470px; text-align: center; font: 600 34px Outfit; color: {MUTED}; }}
    .ro1 b {{ color: {FOREST}; font-weight: 600; }}
    .ro2 {{ position: absolute; left: 330px; right: 20px; top: 516px; text-align: center; font: 600 60px/1 Outfit; }}
    .ro2 .k {{ position: relative; display: inline-block; }}
    .ro2 .num {{ display: inline-block; min-width: 76px; color: {ORANGE_TEXT}; }}
    .ul {{ position: absolute; left: 0; right: 0; bottom: -8px; height: 6px; background: {ORANGE}; }}
    .meter {{ position: absolute; left: 80px; top: 626px; width: 680px; height: 26px; background: {BEIGE}; border-radius: 3px; }}
    .mfill {{ position: absolute; left: 0; top: 0; width: 680px; height: 26px; background: {ORANGE}; border-radius: 3px; }}
    .left {{ position: absolute; left: 476px; top: 0; width: 204px; height: 26px;
             background: {PEACH}; border-left: 3px solid {FOREST}; }}
    .leftlab {{ position: absolute; right: 80px; top: 588px; font: 600 28px Outfit; color: {FOREST}; }}
    .lim {{ position: absolute; left: 300px; top: 586px; width: 200px; height: 80px; }}
    .lim .bar {{ position: absolute; left: 98px; top: 34px; width: 0; height: 46px; border-left: 4px dashed {FOREST}; }}
    .lim .t {{ position: absolute; left: 0; right: 0; top: 0; text-align: center; font: 600 28px Outfit; letter-spacing: .06em; color: {FOREST}; white-space: nowrap; }}
    .tick {{ position: absolute; left: 730px; top: 516px; width: 60px; height: 60px; border-radius: 30px; background: {ORANGE};
             color: {FOREST}; font: 600 38px/60px Outfit; text-align: center; }}
    .note-wrap {{ position: absolute; left: 650px; top: 290px; width: 300px; height: 180px; }}
    .note {{ position: absolute; inset: 0; background: {PEACH}; transform: rotate(4deg); padding: 14px 20px;
            box-shadow: 0 10px 18px rgba(0,0,0,.25); font: 600 44px/1.0 Caveat; color: {FOREST}; }}
    .note .ln {{ display: block; position: relative; width: fit-content; }}
    .note .sul {{ position: absolute; left: 0; right: 0; bottom: 0; height: 4px; background: {TERRA}; border-radius: 2px; }}
  </style>
  <div id="root" data-composition-id="scale" data-width="{W}" data-height="{H}">
    <div class="ground"></div>
    <div class="sheet-wrap" id="s-paper"><div class="sheet">
      <div class="hdr">DEBT SERVICE RATIO · ILLUSTRATION</div>
      <div class="rule" style="top:74px"></div>
      <div class="formula"><span class="f" id="f1">Monthly debts</span><span class="f op" id="f2">÷</span><span class="f" id="f3">net income</span><span class="f op" id="f4">=</span><span class="f" id="f5">DSR</span></div>
      <div class="tag" id="epf">after EPF &amp; tax</div>
      <div class="post"></div><div class="base"></div>
      <div class="pan" id="lp" style="left:15px">{STRINGS}<div class="tray"></div>{debt_blocks()}</div>
      <div class="pan" id="rp" style="left:525px">{STRINGS}<div class="tray"></div>
        <div class="inc" id="inc"><div class="l">NET INCOME</div><div class="v">RM5,000<span class="hl" id="inc-hl"></span></div></div></div>
      <div class="beam" id="beam"></div><div class="cap"></div>
      <div class="ro1" id="ro1"><b>RM<span id="dn">3,500</span></b> debts ÷ <b>RM5,000</b></div>
      <div class="ro2" id="ro2"><span class="k">DSR <span class="num" id="pn">??</span>%<span class="ul" id="ro-ul"></span></span></div>
      <div class="tick" id="tick">✓</div>
      <div class="lim" id="lim"><div class="t">BANK LIMIT?</div><div class="bar"></div></div>
      <div class="leftlab" id="leftlab">RM1,500 left</div>
      <div class="meter"><div class="mfill" id="mfill"></div><div class="left" id="left"></div></div>
    </div></div>
    <div class="clip" id="n1c" data-start="28.80" data-duration="6.25" data-track-index="0"><div class="note-wrap" id="n1" data-layout-allow-occlusion><div class="note">
      <span class="ln">Paid in full?</span><span class="ln" id="n1-b">It may</span><span class="ln" id="n1-c">still count</span></div></div></div>
    <div class="clip" id="n2c" data-start="40.05" data-duration="5.80" data-track-index="0"><div class="note-wrap" id="n2" data-layout-allow-occlusion><div class="note" style="font-size:40px">
      <span class="ln">Lower it:</span><span class="ln" id="n2-a">cancel spare cards</span><span class="ln" id="n2-b">clear small loans<span class="sul" id="n2-ul"></span></span></div></div></div>
  </div>
  <script>
    {JS_HELPERS}
    const L = {L};
    const th = (dsr) => (dsr - 40) * 0.30;                         // beam angle, + = debts side down
    const tilt = (dsr, t, d = 0.8) => {{
      const a = th(dsr), dy = L * Math.sin(a * Math.PI / 180);
      tl.to("#beam", {{ rotation: -a, duration: d, ease: "back.out(1.4)" }}, t);
      tl.to("#lp", {{ y: dy, duration: d, ease: "back.out(1.4)" }}, t);
      tl.to("#rp", {{ y: -dy, duration: d, ease: "back.out(1.4)" }}, t);
    }};
    const meter = (dsr, t, d = 0.9) => tl.to("#mfill", {{ scaleX: dsr / 100, duration: d, ease: "power2.out" }}, t);
    const debts = (txt, t) => {{ tl.set("#dn", {{ textContent: txt }}, t); pulse("#ro1", t, 1.06); }};
    const drop = (sel, t) => tl.fromTo(sel, {{ y: -380, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.45, ease: "back.out(1.2)", immediateRender: false }}, t);

    // resting state = frame 0 thumbnail: loaded scale tipped to the debts, "DSR ??%"
    // frame 0 rest state (before any tween): beam/pans tipped to 70%, meter empty; tags hidden in CSS
    gsap.set("#beam", {{ rotation: -{A0:.2f} }});
    gsap.set("#lp", {{ y: {DY0:.2f} }});
    gsap.set("#rp", {{ y: -{DY0:.2f} }});
    gsap.set("#mfill", {{ scaleX: 0, transformOrigin: "0% 50%" }});
    // hook
    pulse("#inc", 0.59, 1.06);                                     // "salary"
    pop("#tick", 1.32); tl.to("#tick", {{ opacity: 0, duration: 0.2 }}, 2.2);   // "looks fine"
    tl.to("#beam", {{ keyframes: [{{ rotation: -14, duration: 0.18, ease: "power2.out" }}, {{ rotation: -th(70), duration: 0.5, ease: "back.out(2)" }}] }}, 3.02);
    tl.to("#lp", {{ keyframes: [{{ y: L * Math.sin(14 * Math.PI / 180), duration: 0.18, ease: "power2.out" }}, {{ y: L * Math.sin(th(70) * Math.PI / 180), duration: 0.5, ease: "back.out(2)" }}] }}, 3.02);
    tl.to("#rp", {{ keyframes: [{{ y: -L * Math.sin(14 * Math.PI / 180), duration: 0.18, ease: "power2.out" }}, {{ y: -L * Math.sin(th(70) * Math.PI / 180), duration: 0.5, ease: "back.out(2)" }}] }}, 3.02);   // "say no?"
    pulse("#ro2", 4.42, 1.1);                                      // "one number"
    sweep("#ro-ul", 5.30, 0.4);                                    // "your DSR"
    // formula
    tl.to("#f5, #f4", {{ opacity: 1, duration: 0.25 }}, 6.54);      // "Debt service ratio"
    pulse("#lp .blk", 8.15, 1.05);                                 // "Add up"
    tl.to("#f1", {{ opacity: 1, duration: 0.25 }}, 8.69);           // "monthly debts"
    tl.to("#f2", {{ opacity: 1, duration: 0.2 }}, 9.85); pop("#f2", 9.85);   // "divide"
    tl.to("#f3", {{ opacity: 1, duration: 0.25 }}, 10.75); pulse("#inc", 10.75, 1.06);   // "net income"
    pop("#epf", 11.53);                                            // "after EPF and tax"
    // illustration: the debts clear and re-stack as they are named
    tl.to("#lp .blk", {{ y: -420, opacity: 0, duration: 0.35, ease: "power2.in", stagger: {{ each: 0.05, from: "end" }} }}, 13.94);
    tilt(0, 14.15); debts("0", 14.3);
    tl.to("#epf", {{ opacity: 0, duration: 0.3 }}, 13.94);
    sweep("#inc-hl", 14.87, 0.5);                                  // "RM5,000 net"
    drop("#b-car", 16.72); tilt(16, 17.0); debts("800", 17.24);    // "Car loan, RM800"
    drop("#b-ptp", 18.21); tilt(20, 18.5); debts("1,000", 19.35);  // "PTPTN, RM200"
    drop("#b-home", 20.64); tilt(60, 20.95, 1.0); debts("3,000", 21.41);   // "the new home loan, RM2,000"
    // 60%
    pulse("#ro1", 23.17, 1.08);                                    // "RM3,000 in debts"
    pulse("#inc", 25.57, 1.06);                                    // "divide by RM5,000"
    count("#pn", 0, 60, 26.66, 0.9); meter(60, 26.66);             // "60%"
    pulse("#rp", 27.73, 1.03);                                     // "of your income"
    // card
    noteIn("#n1", 28.86);                                          // "A credit card"
    reveal("#n1-b", 30.30, 0.4); reveal("#n1-c", 30.55, 0.45);     // "may still count"
    drop("#b-card", 31.55); tilt(70, 31.85); debts("3,500", 32.04);   // "Here, RM500 more"
    count("#pn", 60, 70, 33.46, 0.6); meter(70, 33.46, 0.6);       // "now 70%"
    // each bank: its own limit, and what's left
    noteOut("#n1", 35.0);
    pop("#lim", 35.29);                                            // "Each bank"
    tl.to("#lim", {{ x: 60, duration: 0.35, ease: "power2.inOut" }}, 35.55);   // "sets"
    tl.to("#lim", {{ x: -90, duration: 0.4, ease: "power2.inOut" }}, 36.02);    // "its own"
    tl.to("#lim", {{ x: 0, duration: 0.4, ease: "power2.inOut" }}, 36.50);     // "limit"
    reveal("#left", 37.74, 0.5); tl.to("#left", {{ opacity: 1, duration: 0.01 }}, 37.74);   // "check"
    pop("#leftlab", 38.24);                                        // "what's left"
    pulse("#lp .blk", 38.95, 1.05);                                // "after your debts"
    // lower it
    tl.to("#lim, #leftlab, #left", {{ opacity: 0, duration: 0.3 }}, 39.9);
    noteIn("#n2", 40.10);                                          // "To bring it down"
    reveal("#n2-a", 41.09, 0.5); pulse("#b-card", 41.09, 1.08);    // "cancel cards"
    reveal("#n2-b", 42.93, 0.5); pulse("#b-car, #b-ptp", 43.19, 1.08);   // "clear small loans"
    sweep("#n2-ul", 43.82, 0.5);                                   // "before you apply"
    // same home, 44%
    noteOut("#n2", 45.40);
    tl.to("#b-card", {{ x: 520, rotation: 18, opacity: 0, duration: 0.4, ease: "power3.in" }}, 45.6);   // "Cancel that card"
    tilt(60, 46.04); debts("3,000", 46.04); count("#pn", 70, 60, 46.04, 0.4); meter(60, 46.04, 0.4);
    tl.to("#b-car", {{ x: -520, rotation: -16, opacity: 0, duration: 0.4, ease: "power3.in" }}, 46.75);  // "clear the car loan"
    tl.to("#b-ptp, #b-home", {{ y: {BLOCK_H}, duration: 0.3, ease: "power2.in" }}, 47.1);
    tilt(44, 47.26); debts("2,200", 47.26); count("#pn", 60, 44, 47.26, 0.5); meter(44, 47.26, 0.5);
    pulse("#b-home", 48.54, 1.08);                                 // "same home"
    pulse("#ro2", 48.97, 1.12); pop("#tick", 48.97);               // "44%"
    // close: the sheet drops away
    tl.to("#s-paper", {{ y: 2000, rotation: 9, duration: 0.45, ease: "power3.in" }}, {CLOSE});
    window.__timelines["scale"] = tl;
  </script>
</template>
"""

# ---------------------------------------------------------------- headlines (one clip per beat)
HEADS = [  # (start, end, line a, line b)
    (0.0, 6.5, "Bank said no?", "check your DSR"),
    (6.5, 13.9, "Your DSR", "debts ÷ net pay"),
    (13.9, 22.8, "Add the debts", "every month"),
    (22.8, 28.7, "60% of pay", "already committed"),
    (28.7, 35.0, "Card paid?", "it may count"),
    (35.0, 39.9, "Each bank", "sets its own limit"),
    (39.9, 45.4, "Lower it", "before applying"),
    (45.4, CLOSE, "Same home", "now 44%"),
]


def heads_file() -> str:
    groups, js = [], []
    for i, (s, e, a, b) in enumerate(HEADS):
        groups.append(f'<div class="hg clip" id="h{i}" data-start="{s}" data-duration="{e - s:.2f}" data-track-index="0">'
                      f'<div class="label">Home loans</div><div class="a">{sp(a)}</div><div class="b">{sp(b)}</div></div>')
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
    <div class="label">Home loans</div>
    <div class="head" id="c-head"><div class="a">{sp("Know your DSR")}</div><div class="b">{sp("before you apply")}</div></div>
    <div id="c-list" style="position:absolute;left:75px;top:520px;font:500 40px/1.5 Outfit;color:{IVORY}">
      <div class="li">Monthly debts ÷ net income</div><div class="li">Cards can count too</div><div class="li">Each bank sets its own limit</div><div class="li">Clear small debts first</div></div>
    <div id="c-cta" style="position:absolute;left:75px;top:860px;width:760px;height:130px;background:{ORANGE};display:flex;align-items:center;padding-left:40px;font:600 62px Outfit;color:{FOREST}"><span id="c-ctat" style="display:inline-block">Comment "DSR"</span></div>
    <img id="c-logo" src="assets/horizontal-reverse.svg" style="position:absolute;left:62px;top:1030px;width:500px;height:100px" alt="Senang Homes"/>
  </div>
  <script>
    {JS_HELPERS}
    words("#c-head", 0.3);
    tl.fromTo("#c-list .li", {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "expo.out", stagger: 0.15 }}, 0.6);
    reveal("#c-cta", {t(51.32)}, 0.45);                            // "Comment"
    tl.fromTo("#c-ctat", {{ scale: 1 }}, {{ keyframes: [{{ scale: 1.1, duration: 0.12, ease: "power2.out" }}, {{ scale: 1, duration: 0.3, ease: "power2.inOut" }}] }}, {t(51.86)});  // "DSR"
    tl.fromTo("#c-logo", {{ opacity: 0, x: -70 }}, {{ opacity: 1, x: 0, duration: 0.6, ease: "expo.out" }}, {t(53.0)});
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
    (1.32, "pop", 0.22, 0.4), (9.85, "click-soft", 0.28, 0.36), (11.53, "pop", 0.22, 0.4),
    (13.94, "whoosh-short", 0.22, 0.57), (16.72, "whoosh-short", 0.2, 0.57), (18.21, "whoosh-short", 0.2, 0.57),
    (20.64, "whoosh", 0.22, 0.57), (21.05, "impact-bass-1", 0.28, 1.2), (26.66, "typing", 0.16, 0.45),
    (28.86, "whoosh-short", 0.22, 0.57), (31.55, "whoosh", 0.22, 0.57), (31.95, "impact-bass-2", 0.26, 1.2),
    (33.46, "typing", 0.14, 0.4), (35.29, "pop", 0.22, 0.4), (38.24, "click-soft", 0.26, 0.36),
    (40.10, "whoosh-short", 0.22, 0.57), (45.6, "whoosh", 0.22, 0.57), (46.75, "whoosh", 0.22, 0.57),
    (48.97, "pop", 0.25, 0.4), (CLOSE, "whoosh", 0.25, 0.57), (51.86, "impact-bass-2", 0.28, 1.5),
]


def index_file() -> str:
    hosts = [
        f'      <div id="scale" data-composition-id="scale" data-composition-src="compositions/scale.html" data-start="0" data-duration="{CLOSE + 0.6:.2f}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>',
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
    (COMP / "scale.html").write_text(SCALE, encoding="utf-8")
    (COMP / "heads.html").write_text(heads_file(), encoding="utf-8")
    (COMP / "close.html").write_text(close_file(), encoding="utf-8")
    (COMP / "captions.html").write_text(captions_file(), encoding="utf-8")
    (ROOT / "index.html").write_text(index_file(), encoding="utf-8")
    print(f"wrote scale/heads/close/captions ({len(caption_groups())} caption groups), {len(SFX)} sfx, index.html")
