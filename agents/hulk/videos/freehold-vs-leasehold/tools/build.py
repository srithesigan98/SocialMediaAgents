#!/usr/bin/env python3
"""Writes the "Freehold vs leasehold" reel (format: profiles/senang-homes/formats/animated-explainer.yaml).

    python tools/align.py && python tools/build.py

One object for the whole film: a land title on an ivory sheet. A FREEHOLD | LEASEHOLD switch sits on top,
a lease clock (ring + years left) on the left, four fields on the right (tenure, term, at the end, bank loan),
and a consent stamp / price tag along the bottom. Frame 0 already shows the switch on LEASEHOLD with a full
99-year ring and "?" in the fields (the thumbnail question). The switch flips as the voice names each tenure,
the ring runs out and comes back, the fields fill in, the ring drains to 35 years and the loan bar shrinks,
the consent stamp lands, and the close ticks the three things to check. Times are absolute seconds from
assets/vo/*.words.json + LINES, looked up by word with at().
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMP = ROOT / "compositions"
W, H = 1080, 1920
LINES = {"vo01": 0.30, "vo02": 6.10, "vo03": 12.70, "vo04": 17.50, "vo05": 23.50,
         "vo06": 28.20, "vo07": 34.80, "vo08": 41.40, "vo09": 46.90, "vo10": 52.70}
CLOSE = 52.0    # sheet leaves, end card starts
FILM = 59.8

FOREST, IVORY, PEACH, TERRA, ORANGE, BEIGE, MUTED = (
    "#142E2B", "#F3F0E7", "#FFAA78", "#9A3418", "#F87947", "#E5DED0", "#5B6B66")
ORANGE_TEXT = "#B5531C"

WORDS = {vid: json.loads((ROOT / f"assets/vo/{vid}.words.json").read_text()) for vid in LINES}


def at(vid: str, word: str, n: int = 0) -> float:
    """Absolute start of the n-th word in line vid that starts with `word` (case-insensitive, quotes ignored)."""
    hits = [w for w in WORDS[vid] if w["text"].strip('"').lower().startswith(word.lower())]
    return round(LINES[vid] + hits[n]["start"], 2)


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
    const reveal = (sel, t, d = 0.6) => tl.fromTo(sel, { clipPath: "inset(-10% 100% -10% 0)" }, { clipPath: "inset(-10% 0% -10% 0)", duration: d, ease: "power2.inOut", immediateRender: false }, t);
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


# ---------------------------------------------------------------- the land title (0 -> CLOSE + 0.6)
# sheet: x 120..960, y 480..1150 (840 x 670); coordinates below are sheet-local.
R = 128
C = 2 * 3.141592653589793 * R   # ring circumference (dash length)
# ring radius; ring centre (170, 170) inside a 340 x 340 svg at (40, 196)
ROWS = [("r1", "TENURE", "v1", "Leasehold"), ("r2", "TERM", "v2", "?"),
        ("r3", "AT THE END", "v3", "?"), ("r4", "BANK LOAN", "v4", "?")]


def rows() -> str:
    out = []
    for i, (rid, lab, vid, val) in enumerate(ROWS):
        top = 186 + 86 * i
        body = (f'<span id="v3a">{val}</span> <span style="position:relative"><span id="v3b"></span>'
                f'<span class="hl" id="v3hl" style="left:-6px;right:-6px;transform:scaleX(0)"></span></span>') if vid == "v3" else val
        out.append(f'<div class="row" id="{rid}" style="top:{top}px"><div class="rl">{lab}</div>'
                   f'<div class="rv" id="{vid}">{body}</div></div>')
    return "".join(out)


TITLE = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; }}
    {CSS}
    .sheet-wrap {{ position: absolute; left: 120px; top: 480px; width: 840px; height: 670px; }}
    .sheet {{ position: absolute; inset: 0; background: {IVORY}; color: {FOREST}; box-shadow: 0 24px 48px rgba(0,0,0,.35); }}
    .hdr {{ position: absolute; left: 0; right: 0; top: 24px; text-align: center; font: 600 28px Outfit; letter-spacing: .14em; }}
    .rule {{ position: absolute; left: 40px; right: 40px; height: 0; border-top: 3px dotted #B9B2A3; }}
    .tog {{ position: absolute; left: 120px; top: 94px; width: 600px; height: 66px; border: 3px solid {FOREST}; border-radius: 33px; overflow: hidden; }}
    .slider {{ position: absolute; left: 0; top: 0; width: 297px; height: 60px; background: {ORANGE}; border-radius: 30px; }}
    .tl {{ position: absolute; top: 0; width: 297px; height: 60px; line-height: 60px; text-align: center; font: 600 30px Outfit; letter-spacing: .1em; }}
    .clock {{ position: absolute; left: 40px; top: 196px; width: 340px; height: 340px; }}
    .clock svg {{ position: absolute; inset: 0; overflow: visible; }}
    .clock circle {{ fill: none; stroke-width: 26; }}
    .cn {{ position: absolute; left: 0; right: 0; top: 104px; text-align: center; font: 600 112px/1 Outfit; }}
    .cn .num {{ color: {ORANGE_TEXT}; }}
    .cinf {{ position: absolute; left: 0; right: 0; top: 92px; text-align: center; font: 600 128px/1 Outfit; color: {FOREST}; opacity: 0; }}
    .cl {{ position: absolute; left: 0; right: 0; top: 226px; text-align: center; font: 500 28px Outfit; color: {MUTED}; }}
    .row {{ position: absolute; left: 420px; width: 380px; height: 90px; }}
    .rl {{ font: 500 28px Outfit; letter-spacing: .12em; color: {MUTED}; }}
    .rv {{ position: relative; font: 600 38px/1.15 Outfit; color: {FOREST}; white-space: nowrap; }}
    .hl {{ position: absolute; top: 6px; bottom: 0; background: #FFD84D; opacity: .55; mix-blend-mode: multiply; }}
    .bar {{ position: absolute; left: 0; top: 44px; width: 380px; height: 30px; background: {BEIGE}; border-radius: 3px; opacity: 0; }}
    .bfill {{ position: absolute; left: 0; top: 0; width: 380px; height: 30px; background: {ORANGE}; border-radius: 3px; }}
    .bsub {{ position: absolute; left: 0; top: 82px; font: 600 28px Outfit; color: {ORANGE_TEXT}; white-space: nowrap; opacity: 0; }}
    .renew {{ position: absolute; left: 236px; top: 470px; width: 56px; height: 56px; border-radius: 28px; background: {ORANGE};
              font: 600 38px/56px Outfit; text-align: center; color: {FOREST}; opacity: 0; }}
    .price {{ position: absolute; left: 40px; top: 586px; height: 60px; padding: 0 22px; border-radius: 30px; background: {FOREST}; color: {IVORY};
              font: 600 30px/60px Outfit; white-space: nowrap; }}
    .price .dn {{ display: inline-block; color: {PEACH}; }}
    .stamp {{ position: absolute; left: 388px; top: 590px; padding: 4px 12px; border: 5px solid {TERRA}; border-radius: 8px; color: {TERRA};
              font: 600 28px Outfit; letter-spacing: .06em; white-space: nowrap; transform: rotate(-8deg); opacity: 0; }}
    .wk {{ position: absolute; left: 690px; top: 584px; font: 600 28px/1.1 Outfit; color: {TERRA}; white-space: nowrap; opacity: 0; }}
    .tick {{ position: absolute; width: 56px; height: 56px; border-radius: 28px; background: {ORANGE}; color: {FOREST};
             font: 600 36px/56px Outfit; text-align: center; opacity: 0; }}
    .note-wrap {{ position: absolute; left: 650px; top: 290px; width: 300px; height: 180px; }}
    .note {{ position: absolute; inset: 0; background: {PEACH}; transform: rotate(4deg); padding: 14px 20px;
            box-shadow: 0 10px 18px rgba(0,0,0,.25); font: 600 44px/1.0 Caveat; color: {FOREST}; }}
    .note .ln {{ display: block; position: relative; width: fit-content; }}
    .note .sul {{ position: absolute; left: 0; right: 0; bottom: 0; height: 4px; background: {TERRA}; border-radius: 2px; }}
  </style>
  <div id="root" data-composition-id="title" data-width="{W}" data-height="{H}">
    <div class="ground"></div>
    <div class="sheet-wrap" id="s-paper"><div class="sheet">
      <div class="hdr" id="hdr">LAND TITLE · ILLUSTRATION</div>
      <div class="rule" style="top:74px"></div>
      <div class="tog" id="tog"><div class="slider" id="slider"></div>
        <div class="tl" id="t-fh" style="left:0">FREEHOLD</div><div class="tl" id="t-lh" style="left:297px">LEASEHOLD</div></div>
      <div class="clock" id="clock">
        <svg viewBox="0 0 340 340"><circle cx="170" cy="170" r="{R}" stroke="{BEIGE}"/>
          <circle id="ring" cx="170" cy="170" r="{R}" stroke="{ORANGE}" stroke-dasharray="{C:.2f} {C:.2f}" transform="rotate(-90 170 170)"/>
          <circle id="ring-fh" cx="170" cy="170" r="{R}" stroke="{FOREST}" opacity="0"/></svg>
        <div class="cn" id="cn"><span class="num" id="cnum">99</span></div>
        <div class="cinf" id="cinf" data-layout-allow-overlap>∞</div>
        <div class="cl" id="cl">years left</div>
      </div>
      <div class="renew" id="renew">↻</div>
      {rows()}
      <div class="bar" id="bar" style="left:420px;top:488px"><div class="bfill" id="bfill"></div></div>
      <div class="bsub" id="bsub" style="left:420px;top:524px">less, or shorter</div>
      <div class="price" id="price">PRICE · often lower <span class="dn" id="pdn">↓</span></div>
      <div class="stamp" id="stamp">STATE CONSENT</div>
      <div class="wk" id="wk">+ weeks,<br/>or months</div>
      <div class="tick" id="k1" style="left:770px;top:218px">✓</div>
      <div class="tick" id="k2" style="left:316px;top:200px">✓</div>
      <div class="tick" id="k3" style="left:636px;top:536px">✓</div>
    </div></div>
    <div class="clip" id="n1c" data-start="{at('vo04', 'Renewal') - 0.05:.2f}" data-duration="{LINES['vo05'] - at('vo04', 'Renewal') + 0.5:.2f}" data-track-index="0"><div class="note-wrap" id="n1" data-layout-allow-occlusion><div class="note">
      <span class="ln">Not automatic:</span><span class="ln" id="n1-b">apply first,</span><span class="ln" id="n1-c">pay a premium<span class="sul" id="n1-ul"></span></span></div></div></div>
    <div class="clip" id="n2c" data-start="{LINES['vo05']:.2f}" data-duration="{LINES['vo06'] - LINES['vo05'] + 0.5:.2f}" data-track-index="0"><div class="note-wrap" id="n2" data-layout-allow-occlusion><div class="note">
      <span class="ln">Each state:</span><span class="ln" id="n2-a">own rules,</span><span class="ln" id="n2-b">own rates<span class="sul" id="n2-ul"></span></span></div></div></div>
  </div>
  <script>
    {JS_HELPERS}
    const flip = (side, t) => {{   // side: "fh" or "lh"
      tl.to("#slider", {{ x: side === "fh" ? 0 : 297, duration: 0.35, ease: "back.out(1.6)" }}, t);
      const fh = side === "fh";
      tl.to("#ring-fh, #cinf", {{ opacity: fh ? 1 : 0, duration: 0.25 }}, t + 0.1);
      tl.to("#ring, #cn", {{ opacity: fh ? 0 : 1, duration: 0.25 }}, t + 0.1);
      tl.set("#cl", {{ textContent: fh ? "no end date" : "years left" }}, t + 0.1);
      tl.set("#v1", {{ textContent: fh ? "Freehold" : "Leasehold" }}, t + 0.1);
      reveal("#v1", t + 0.1, 0.35);
    }};
    const ring = (yrs, t, d = 0.9) => tl.to("#ring", {{ strokeDashoffset: {C:.2f} * (1 - yrs / 99), duration: d, ease: "power2.inOut" }}, t);
    const swap = (sel, text, t, d = 0.45) => {{ tl.set(sel, {{ textContent: text }}, t); tl.set(sel === "#v3a" ? "#v3" : sel, {{ color: "{FOREST}" }}, t); reveal(sel === "#v3a" ? "#v3" : sel, t, d); }};

    // frame 0 rest state = thumbnail: switch on LEASEHOLD, full 99-year ring, "?" fields
    gsap.set("#slider", {{ x: 297 }});
    gsap.set("#ring", {{ strokeDashoffset: 0 }});
    gsap.set("#v2, #v3, #v4", {{ color: "#8A8478" }});
    gsap.set("#bfill", {{ transformOrigin: "0% 50%" }});
    gsap.set("#price", {{ opacity: 0 }});
    // hook
    pulse("#s-paper", {at('vo01', 'Same')}, 1.03);                       // "Same street"
    pulse("#tog", {at('vo01', 'two')}, 1.06);                            // "two condos"
    flip("fh", {at('vo01', 'freehold')});                                // "freehold"
    flip("lh", {at('vo01', 'leasehold')});                               // "leasehold"
    pulse("#v2, #v3, #v4", {at('vo01', 'What')}, 1.15);                  // "What changes"
    // freehold / leasehold
    flip("fh", {at('vo02', 'Freehold')});                                // "Freehold"
    swap("#v2", "No end date", {at('vo02', 'no')});                      // "no end date"
    flip("lh", {at('vo02', 'Leasehold')});                               // "Leasehold"
    swap("#v2", "Lease from state", {at('vo02', 'lease')});             // "a lease from the state"
    ring(0, {at('vo02', 'often') - 0.4:.2f}, 0.3); count("#cnum", 99, 0, {at('vo02', 'often') - 0.4:.2f}, 0.3);
    ring(99, {at('vo02', '99')}, 0.8); count("#cnum", 0, 99, {at('vo02', '99')}, 0.8);   // "often for 99 years"
    swap("#v2", "Often 99 years", {at('vo02', '99')});
    // the lease runs out
    ring(0, {at('vo03', 'runs')}, 1.0); count("#cnum", 99, 0, {at('vo03', 'runs')}, 1.0);   // "runs out"
    swap("#v3a", "Back to the state", {at('vo03', 'land')});              // "the land goes back to the state"
    pulse("#v3", {at('vo03', 'state')}, 1.06);
    pop("#renew", {at('vo03', 'unless')});                               // "unless it's renewed"
    ring(99, {at('vo03', 'renewed')}, 0.8); count("#cnum", 0, 99, {at('vo03', 'renewed')}, 0.8);
    // renewal
    noteIn("#n1", {at('vo04', 'Renewal')});                              // "Renewal isn't automatic"
    tl.to("#renew", {{ rotation: -360, duration: 0.6, ease: "power2.inOut" }}, {at('vo04', 'automatic')});
    reveal("#n1-b", {at('vo04', 'apply')}, 0.45);                        // "You apply"
    tl.set("#v3a", {{ textContent: "Renew:" }}, {at('vo04', 'apply')}); tl.set("#v3b", {{ textContent: "premium" }}, {at('vo04', 'apply')});
    reveal("#v3", {at('vo04', 'apply')}, 0.45);
    reveal("#n1-c", {at('vo04', 'pay')}, 0.45);                          // "pay a premium"
    sweep("#n1-ul", {at('vo04', 'premium')}, 0.5);
    sweep("#v3hl", {at('vo04', 'premium')}, 0.5);
    pulse("#v3", {at('vo04', 'state', 0)}, 1.06);                        // "the state sets"
    noteOut("#n1", {LINES['vo05'] - 0.2:.2f});
    // each state
    noteIn("#n2", {at('vo05', 'Each')});                                 // "Each state"
    reveal("#n2-a", {at('vo05', 'rules')}, 0.4);                         // "own rules"
    reveal("#n2-b", {at('vo05', 'rates')}, 0.4);                         // "and rates"
    sweep("#n2-ul", {at('vo05', 'cost')}, 0.5);                          // "the cost can differ"
    pulse("#v3", {at('vo05', 'differ')}, 1.08);
    noteOut("#n2", {LINES['vo06'] - 0.2:.2f});
    // illustration: 35 years left, the loan shrinks
    pulse("#hdr", {at('vo06', 'Illustration')}, 1.08);                   // "Illustration"
    tl.to("#renew", {{ opacity: 0, duration: 0.2 }}, {at('vo06', 'Illustration')});
    ring(35, {at('vo06', '35')}, 1.0); count("#cnum", 99, 35, {at('vo06', '35')}, 1.0);   // "35 years left"
    pulse("#clock", {at('vo06', 'lease')}, 1.04);
    tl.to("#bar", {{ opacity: 1, duration: 0.01 }}, {at('vo06', 'Some')});
    reveal("#bar", {at('vo06', 'Some')}, 0.5);                           // "Some banks"
    swap("#v4", "", {at('vo06', 'Some')});
    tl.to("#bfill", {{ scaleX: 0.6, duration: 0.6, ease: "power2.inOut" }}, {at('vo06', 'less')});   // "lend less"
    tl.to("#bsub", {{ opacity: 1, duration: 0.01 }}, {at('vo06', 'fewer')});
    reveal("#bsub", {at('vo06', 'fewer')}, 0.5);                         // "or for fewer years"
    // state consent
    tl.fromTo("#stamp", {{ opacity: 0, scale: 1.8, rotation: -26 }}, {{ opacity: 1, scale: 1, rotation: -8, duration: 0.2, ease: "power4.out" }}, {at('vo07', 'consent')});
    tl.to("#s-paper", {{ keyframes: [{{ x: -6, duration: 0.033 }}, {{ x: 5, duration: 0.033 }}, {{ x: 0, duration: 0.033 }}] }}, {at('vo07', 'consent') + 0.2:.2f});
    pulse("#v1", {at('vo07', 'sell')}, 1.06);                            // "to sell"
    pulse("#bar", {at('vo07', 'refinance')}, 1.04);                      // "or refinance"
    tl.to("#wk", {{ opacity: 1, duration: 0.01 }}, {at('vo07', 'weeks')});
    reveal("#wk", {at('vo07', 'weeks')}, 0.4);                           // "weeks"
    pulse("#wk", {at('vo07', 'months')}, 1.1);                           // "or months"
    // the upside
    tl.to("#price", {{ opacity: 1, duration: 0.01 }}, {at('vo08', 'upside')});
    reveal("#price", {at('vo08', 'upside')}, 0.5);                       // "The upside"
    tl.fromTo("#pdn", {{ y: -14 }}, {{ y: 4, duration: 0.35, ease: "back.out(2)" }}, {at('vo08', 'lower')});   // "priced lower"
    pulse("#price", {at('vo08', 'lower')}, 1.06);
    tl.to("#slider", {{ keyframes: [{{ x: 0, duration: 0.3, ease: "power2.inOut" }}, {{ x: 297, duration: 0.3, ease: "power2.inOut", delay: 0.5 }}] }}, {at('vo08', 'freehold')});   // "a similar freehold"
    // checklist
    pulse("#s-paper", {at('vo09', 'title')}, 1.03);                      // "check the title"
    pop("#k1", {at('vo09', 'tenure')});                                  // "the tenure"
    pop("#k2", {at('vo09', 'years')});                                   // "the years left"
    pop("#k3", {at('vo09', 'restriction')});                             // "any restriction"
    pulse("#stamp", {at('vo09', 'restriction')}, 1.08);
    // close: the sheet drops away
    tl.to("#s-paper", {{ y: 2000, rotation: 9, duration: 0.45, ease: "power3.in" }}, {CLOSE});
    window.__timelines["title"] = tl;
  </script>
</template>
"""

# ---------------------------------------------------------------- headlines (one clip per beat)
HEADS = [  # (start, end, line a, line b)
    (0.0, LINES["vo02"], "Freehold or", "leasehold?"),
    (LINES["vo02"], LINES["vo03"], "Freehold", "has no end date"),
    (LINES["vo03"], LINES["vo04"], "When it ends", "land goes back"),
    (LINES["vo04"], LINES["vo05"], "Renewal", "isn't automatic"),
    (LINES["vo05"], LINES["vo06"], "Each state", "sets its own"),
    (LINES["vo06"], LINES["vo07"], "35 years left", "loan may shrink"),
    (LINES["vo07"], LINES["vo08"], "Some titles", "need consent"),
    (LINES["vo08"], LINES["vo09"], "The upside", "often cheaper"),
    (LINES["vo09"], CLOSE, "Before you buy", "read the title"),
]


def heads_file() -> str:
    groups, js = [], []
    for i, (s, e, a, b) in enumerate(HEADS):
        groups.append(f'<div class="hg clip" id="h{i}" data-start="{s}" data-duration="{e - s:.2f}" data-track-index="0">'
                      f'<div class="label">Land title</div><div class="a">{sp(a)}</div><div class="b">{sp(b)}</div></div>')
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
    <div class="label">Land title</div>
    <div class="head" id="c-head"><div class="a">{sp("Know the tenure")}</div><div class="b">{sp("before you buy")}</div></div>
    <div id="c-list" style="position:absolute;left:75px;top:520px;font:500 40px/1.5 Outfit;color:{IVORY}">
      <div class="li">Freehold: no end date</div><div class="li">Leasehold: often 99 years</div><div class="li">Renewal isn't automatic</div><div class="li">Check years left &amp; consent</div></div>
    <div id="c-cta" style="position:absolute;left:75px;top:860px;width:760px;height:130px;background:{ORANGE};display:flex;align-items:center;padding-left:40px;font:600 62px Outfit;color:{FOREST}"><span id="c-ctat" style="display:inline-block">Comment "TITLE"</span></div>
    <img id="c-logo" src="assets/horizontal-reverse.svg" style="position:absolute;left:62px;top:1030px;width:500px;height:100px" alt="Senang Homes"/>
  </div>
  <script>
    {JS_HELPERS}
    words("#c-head", 0.3);
    tl.fromTo("#c-list .li", {{ opacity: 0, x: -30 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "expo.out", stagger: 0.15 }}, 0.6);
    reveal("#c-cta", {t(at('vo10', 'Comment'))}, 0.45);                  // "Comment"
    tl.fromTo("#c-ctat", {{ scale: 1 }}, {{ keyframes: [{{ scale: 1.1, duration: 0.12, ease: "power2.out" }}, {{ scale: 1, duration: 0.3, ease: "power2.inOut" }}] }}, {t(at('vo10', 'TITLE'))});
    tl.fromTo("#c-logo", {{ opacity: 0, x: -70 }}, {{ opacity: 1, x: 0, duration: 0.6, ease: "expo.out" }}, {t(at('vo10', 'you') + 0.4)});
    window.__timelines["close"] = tl;
  </script>
</template>
"""


# ---------------------------------------------------------------- captions
def caption_groups():
    groups = []
    for vid, s in LINES.items():
        words = WORDS[vid]
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
    (at('vo01', 'freehold'), "click-soft", 0.26, 0.36), (at('vo01', 'leasehold'), "click-soft", 0.26, 0.36),
    (at('vo02', 'Freehold'), "click-soft", 0.26, 0.36), (at('vo02', 'Leasehold'), "click-soft", 0.26, 0.36),
    (at('vo02', '99'), "typing", 0.14, 0.45), (at('vo03', 'runs'), "whoosh-short", 0.2, 0.57),
    (at('vo03', 'unless'), "pop", 0.22, 0.4), (at('vo04', 'Renewal'), "whoosh-short", 0.22, 0.57),
    (at('vo04', 'premium'), "pop", 0.2, 0.4), (at('vo05', 'Each'), "whoosh-short", 0.22, 0.57),
    (at('vo06', '35'), "typing", 0.14, 0.45), (at('vo06', 'less'), "whoosh", 0.2, 0.57),
    (at('vo07', 'consent'), "impact-bass-1", 0.3, 1.2), (at('vo07', 'weeks'), "click-soft", 0.24, 0.36),
    (at('vo08', 'upside'), "whoosh-short", 0.22, 0.57), (at('vo08', 'lower'), "pop", 0.22, 0.4),
    (at('vo09', 'tenure'), "pop", 0.22, 0.4), (at('vo09', 'years'), "pop", 0.22, 0.4),
    (at('vo09', 'restriction'), "pop", 0.24, 0.4), (CLOSE, "whoosh", 0.25, 0.57),
    (at('vo10', 'TITLE'), "impact-bass-2", 0.28, 1.5),
]


def index_file() -> str:
    hosts = [
        f'      <div id="title" data-composition-id="title" data-composition-src="compositions/title.html" data-start="0" data-duration="{CLOSE + 0.6:.2f}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>',
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
    (COMP / "title.html").write_text(TITLE, encoding="utf-8")
    (COMP / "heads.html").write_text(heads_file(), encoding="utf-8")
    (COMP / "close.html").write_text(close_file(), encoding="utf-8")
    (COMP / "captions.html").write_text(captions_file(), encoding="utf-8")
    (ROOT / "index.html").write_text(index_file(), encoding="utf-8")
    print(f"wrote title/heads/close/captions ({len(caption_groups())} caption groups), {len(SFX)} sfx, index.html")
