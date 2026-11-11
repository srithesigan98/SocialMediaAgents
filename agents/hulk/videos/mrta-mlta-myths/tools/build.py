#!/usr/bin/env python3
"""Writes index.html, compositions/s1..s8.html and compositions/captions.html for the MRTA/MLTA reel.

    python tools/build.py

The eight scenes share one offer letter drawn at the same place, so cuts between them read as one
frame that rebuilds (SPEC.md). Every reveal is keyed to the word that names it: scene-local times
below come from assets/vo/*.words.json (Parakeet) minus the scene start. Caption words come from
SCRIPT.md by position. Edit layout/copy/motion here, then rebuild.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMP = ROOT / "compositions"
W, H, FILM = 1080, 1920, 60.0
LINES = {"vo01": 0.30, "vo02": 7.10, "vo03": 14.50, "vo04": 19.90,
         "vo05": 28.70, "vo06": 34.80, "vo07": 42.50, "vo08": 50.20}
# (id, start, end) — each scene's slot; the next scene starts where this one ends.
SCENES = [("s1", 0.0, 7.1), ("s2", 7.1, 14.5), ("s3", 14.5, 19.9), ("s4", 19.9, 28.7),
          ("s5", 28.7, 34.8), ("s6", 34.8, 42.5), ("s7", 42.5, 50.2), ("s8", 50.2, FILM)]

FOREST, IVORY, PEACH, TERRA, ORANGE, BEIGE, MUTED = (
    "#142E2B", "#F3F0E7", "#FFAA78", "#9A3418", "#F87947", "#E5DED0", "#5B6B66")
ORANGE_TEXT = "#B5531C"  # MLTA text on paper: bright orange is 2.4:1 on ivory, this is 4.4:1

FONTS = """
@font-face { font-family: "Outfit"; src: url("assets/fonts/Outfit-Regular.ttf"); font-weight: 400; }
@font-face { font-family: "Outfit"; src: url("assets/fonts/Outfit-Medium.ttf"); font-weight: 500; }
@font-face { font-family: "Outfit"; src: url("assets/fonts/Outfit-SemiBold.ttf"); font-weight: 600; }
@font-face { font-family: "Gelasio"; src: url("assets/fonts/Gelasio-MediumItalic.ttf"); font-weight: 500; font-style: italic; }
@font-face { font-family: "Caveat"; src: url("assets/fonts/Caveat.ttf"); font-weight: 400 700; }
"""

# Shared look. Elements GSAP transforms carry no CSS transform (contract rule 6): their resting
# rotation is set by the tween instead.
CSS = FONTS + f"""
.ground {{ position: absolute; inset: 0; background: {FOREST}; }}
.label {{ position: absolute; left: 75px; top: 205px; font: 500 28px Outfit; letter-spacing: .16em;
         color: {PEACH}; text-transform: uppercase; }}
.head {{ position: absolute; left: 75px; top: 245px; width: 930px; }}
.head .a {{ font: 600 84px/1 Outfit; letter-spacing: -0.01em; color: {IVORY}; }}
.head .b {{ font: italic 500 72px/1.15 Gelasio; color: {PEACH}; margin-top: 6px; }}
.hw {{ display: inline-block; }}
.letter-wrap {{ position: absolute; left: 110px; top: 440px; width: 860px; height: 690px; }}
.letter {{ position: absolute; inset: 0; background: {IVORY}; transform: rotate(-1.5deg);
          box-shadow: 0 24px 48px rgba(0,0,0,.35); padding: 52px 56px; color: {FOREST}; }}
.lh {{ border-bottom: 3px solid {FOREST}; padding-bottom: 18px; }}
.lh .t {{ font: 600 28px Outfit; letter-spacing: .14em; }}
.row {{ display: flex; align-items: baseline; padding: 26px 0 22px; border-bottom: 1px solid #D8D1C2; }}
.row .k {{ width: 250px; font: 400 28px Outfit; color: {MUTED}; }}
.row .v {{ font: 600 34px Outfit; color: {FOREST}; position: relative; }}
.blank {{ display: inline-block; width: 300px; border-bottom: 3px solid {FOREST}; height: 34px; }}
.hl {{ position: absolute; left: -10px; right: -10px; top: 4px; bottom: -4px; background: #FFD84D;
      opacity: .55; mix-blend-mode: multiply; }}
.fact {{ font: italic 500 32px Gelasio; color: {FOREST}; margin-top: 14px; }}
.note-wrap {{ position: absolute; left: 640px; top: 370px; width: 340px; height: 310px; }}
.note {{ position: absolute; inset: 0; background: {PEACH}; transform: rotate(4deg); padding: 26px 28px;
        box-shadow: 0 10px 18px rgba(0,0,0,.25); font: 600 50px/1 Caveat; color: {FOREST}; }}
.strike {{ position: absolute; left: 22px; right: 22px; top: 27%; height: 8px; background: {TERRA}; border-radius: 4px; }}
.stamp {{ position: absolute; left: 62px; top: 186px; padding: 6px 22px; border: 8px solid {TERRA};
         color: {TERRA}; font: 600 64px/1 Outfit; letter-spacing: .1em; mix-blend-mode: multiply; }}
.tiny {{ font: 400 28px Outfit; color: {MUTED}; }}
.tag {{ display: inline-block; padding: 6px 14px; border: 3px solid {FOREST}; border-radius: 4px;
       font: 600 30px Outfit; margin-right: 12px; }}
.ch {{ display: inline-block; white-space: pre; }}
"""

# Motion helpers, prepended to every scene's script. All seek-safe: fromTo only, no callbacks.
JS_HELPERS = """
    const tl = gsap.timeline({ paused: true });
    const words = (sel, t, gap = 0.07) => tl.fromTo(sel + " .hw", { opacity: 0, filter: "blur(10px)" },
      { opacity: 1, filter: "blur(0px)", duration: 0.18, ease: "power2.out", stagger: gap }, t);
    const stamp = (sel, t, shake) => {
      tl.fromTo(sel, { opacity: 0, scale: 1.8, rotation: -26 }, { opacity: 0.9, scale: 1, rotation: -12, duration: 0.2, ease: "power4.out" }, t);
      if (shake) tl.fromTo(shake, { x: 0 }, { keyframes: [{ x: -7, duration: 0.033 }, { x: 6, duration: 0.033 }, { x: -3, duration: 0.033 }, { x: 0, duration: 0.05 }] }, t + 0.18);
    };
    const strike = (sel, t) => tl.fromTo(sel, { scaleX: 0, rotation: -6 }, { scaleX: 1, rotation: -6, duration: 0.3, ease: "power2.inOut", transformOrigin: "0% 50%" }, t);
    const sweep = (sel, t, d = 0.45) => tl.fromTo(sel, { scaleX: 0 }, { scaleX: 1, duration: d, ease: "power2.inOut", transformOrigin: "0% 50%" }, t);
    const pop = (sel, t, s = 0.08) => tl.fromTo(sel, { opacity: 0, scale: 0.3 }, { opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.2)", stagger: s }, t);
    const draw = (sel, t, d = 0.9) => tl.fromTo(sel, { attr: { "stroke-dashoffset": 1 } }, { attr: { "stroke-dashoffset": 0 }, duration: d, ease: "power2.inOut" }, t);
    const reveal = (sel, t, d = 0.6) => tl.fromTo(sel, { clipPath: "inset(-10% 100% -10% 0)" }, { clipPath: "inset(-10% 0% -10% 0)", duration: d, ease: "power2.inOut" }, t);
    const noteIn = (sel, t) => tl.fromTo(sel, { y: -560, rotation: 16 }, { y: 0, rotation: 0, duration: 0.55, ease: "back.out(1.3)" }, t);
    const count = (sel, to, t, d) => tl.fromTo(sel, { textContent: 0 }, { textContent: to, duration: d, ease: "power2.out", snap: { textContent: 1 } }, t);
    const typed = (sel, t, gap = 0.045) => tl.fromTo(sel + " .ch", { opacity: 0 }, { opacity: 1, duration: 0.01, stagger: gap }, t);
"""


def sp(text: str) -> str:
    """Split a line into word spans (.hw) so headlines can enter word by word."""
    return " ".join(f'<span class="hw">{w}</span>' for w in text.split())


def chars(text: str) -> str:
    return "".join(f'<span class="ch">{c}</span>' for c in text)


def head(a: str, b: str, a_html: str | None = None) -> str:
    return f"""<div class="label" id="{{p}}-label">MRTA vs MLTA</div>
<div class="head" id="{{p}}-head"><div class="a">{a_html or sp(a)}</div><div class="b">{sp(b)}</div></div>"""


def letter(rows: str, extra: str = "") -> str:
    return f"""<div class="letter-wrap" id="{{p}}-letter"><div class="letter">
  <div class="lh"><span class="t">LETTER OF OFFER</span></div>
  {rows}{extra}
</div></div>"""


def default_rows(payee: str = '<span class="blank"></span>', cover: str = "MRTA / MLTA") -> str:
    return f"""<div class="row"><span class="k">Loan amount</span><span class="v">RM500,000</span></div>
  <div class="row"><span class="k">Tenure</span><span class="v">30 years</span></div>
  <div class="row"><span class="k">Mortgage cover</span><span class="v">{cover}</span></div>
  <div class="row"><span class="k">Benefit payable to</span><span class="v">{payee}</span></div>"""


def note(text: str, stamped: bool = True) -> str:
    extra = ('<div class="strike" id="{p}-strike"></div><div class="stamp" id="{p}-stamp">MYTH</div>'
             if stamped else "")
    return f"""<div class="note-wrap" id="{{p}}-note" data-layout-allow-occlusion><div class="note">{text}{extra}</div></div>"""


def chart_svg() -> str:
    """MRTA reducing curve vs MLTA level line. Illustration: RM500K, 30 years, 3% a year."""
    x0, x1, top, base = 120, 700, 60, 380
    g = 1.03

    def bal(t):  # share of the loan still owed after t years
        return (g ** 30 - g ** t) / (g ** 30 - 1)
    pt = lambda t: (x0 + (x1 - x0) * t / 30, base - (base - top) * bal(t))
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(pt, range(31)))
    gap = f"{x0},{top} {x1},{top} " + " ".join(f"{x:.1f},{y:.1f}" for x, y in map(pt, range(30, -1, -1)))
    grid = "".join(
        f'<line class="grid" x1="{x0}" x2="{x1}" y1="{base - (base - top) * f}" y2="{base - (base - top) * f}" stroke="#D8D1C2" stroke-width="2"/>'
        f'<text class="ax" x="{x0 - 14}" y="{base - (base - top) * f + 8}" text-anchor="end" font-family="Outfit" font-size="31" fill="{MUTED}">{lab}</text>'
        for f, lab in ((1, "RM500K"), (0, "RM0")))
    years = "".join(f'<text class="ax" x="{x0 + (x1 - x0) * t / 30}" y="{base + 34}" text-anchor="middle" font-family="Outfit" font-size="31" fill="{MUTED}">Year {t}</text>'
                    for t in (0, 30))
    ticks = "".join(f'<circle class="tick" cx="{pt(t)[0]:.1f}" cy="{pt(t)[1]:.1f}" r="9" fill="{FOREST}"/>' for t in range(5, 30, 5))
    return f"""<svg id="{{p}}-chart" width="680" height="400" viewBox="0 0 748 440" style="margin-top:118px;overflow:visible">
  <polygon id="{{p}}-gap" points="{gap}" fill="{ORANGE}" opacity="0.28"/>
  {grid}{years}
  <polyline id="{{p}}-mrta" points="{pts}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0" fill="none" stroke="{FOREST}" stroke-width="8" stroke-linecap="round"/>
  {ticks}
  <line id="{{p}}-mlta" x1="{x0}" x2="{x1}" y1="{top}" y2="{top}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0" stroke="{ORANGE}" stroke-width="8" stroke-linecap="round"/>
  <text id="{{p}}-mlta-l" x="{x1}" y="{top - 18}" text-anchor="end" font-family="Outfit" font-weight="600" font-size="32" fill="{ORANGE_TEXT}">MLTA stays level</text>
  <text id="{{p}}-mrta-l" x="{x0 + 24}" y="{base - 40}" font-family="Outfit" font-weight="600" font-size="32" fill="{FOREST}">MRTA shrinks</text>
</svg>
<div class="tiny" id="{{p}}-illus" style="margin-top:4px">Illustration: RM500K, 30 years, 3% a year</div>"""


# ---------------------------------------------------------------- scene bodies
S1 = (head("", "most believe", a_html='<span class="hw" id="{p}-n">4</span> <span class="hw">MRTA</span> <span class="hw">myths</span>')
      + f'<div id="{{p}}-ul" style="position:absolute;left:75px;top:418px;width:440px;height:6px;background:{PEACH}"></div>'
      + letter(default_rows(
          payee='<span class="hl" id="{p}-hl"></span><span class="blank"></span>'
                f'<span id="{{p}}-q" style="position:absolute;left:316px;top:-8px;font:600 56px Caveat;color:{TERRA}">?</span>',
          cover='<span class="hl" id="{p}-hl2"></span>MRTA / MLTA'))
      + note("MRTA pays my family", stamped=False))

S2 = (head("Who's paid?", "mostly the bank")
      + letter(default_rows(
          payee='<span class="hl" id="{p}-hl"></span><span class="blank" id="{p}-blank"></span>'
                f'<span id="{{p}}-q" style="position:absolute;left:316px;top:-8px;font:600 56px Caveat;color:{TERRA}">?</span>'
                f'<span id="{{p}}-bank" style="position:absolute;left:0;top:0;white-space:nowrap">{chars("THE BANK")}</span>'),
          extra=f"""<div class="fact" id="{{p}}-fact">&#8594; goes toward what you still owe</div>
  <div style="margin-top:22px;width:748px"><div class="tiny" style="margin-bottom:8px">Loan balance</div>
  <div style="position:relative;height:40px;background:{BEIGE}"><div id="{{p}}-drain" style="position:absolute;inset:0;background:{FOREST}"></div></div></div>""")
      + note("MRTA pays my family"))

S3 = (head("With MLTA?", "bank, then you")
      + letter(f"""<div class="row" id="{{p}}-row"><span class="k">Mortgage cover</span><span class="v" style="color:{ORANGE_TEXT}">MLTA</span></div>
  <div style="margin-top:34px">
  <div class="tiny" id="{{p}}-cap" style="margin-bottom:12px">Illustration: RM500K cover, RM380K owed</div>
  <div style="display:flex;height:78px;width:748px">
    <div id="{{p}}-bank" style="flex:0 0 76%;background:{FOREST};color:{IVORY};font:600 28px Outfit;display:flex;align-items:center;padding-left:22px;white-space:nowrap">Bank: RM<span id="{{p}}-n1">380</span>K</div>
    <div id="{{p}}-left" style="flex:1;background:{ORANGE};color:{FOREST};font:600 28px Outfit;display:flex;align-items:center;justify-content:center;white-space:nowrap">RM<span id="{{p}}-n2">120</span>K</div>
  </div>
  <div style="display:flex;justify-content:flex-end;width:748px;margin-top:12px"><span class="fact" id="{{p}}-fact" style="margin:0">usually to you or your nominee</span></div>
</div>""")
      + note("MRTA pays my family"))

S4 = head("Same cover?", "only MLTA") + letter(chart_svg()) + note("My cover stays the same")

FIRE_CARD = f"""<div id="{{p}}-fire" data-layout-allow-occlusion style="position:absolute;left:70px;top:560px;width:520px;height:520px;background:#FFFDF8;box-shadow:0 22px 40px rgba(0,0,0,.4);color:{FOREST}">
  <div style="background:{ORANGE};padding:22px 30px;font:600 28px Outfit;letter-spacing:.1em">FIRE / HOUSEOWNER POLICY</div>
  <svg width="160" height="140" viewBox="0 0 160 140" style="margin:30px 0 0 30px">
    <path id="{{p}}-house" d="M10 70 L80 12 L150 70 L150 132 L10 132 Z" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0" fill="none" stroke="{FOREST}" stroke-width="8" stroke-linejoin="round"/>
    <rect id="{{p}}-door" x="62" y="84" width="36" height="48" fill="{FOREST}"/></svg>
  <div id="{{p}}-r1" style="padding:10px 30px 0;font:600 36px Outfit">Covers the building <span id="{{p}}-ok" style="display:inline-block;color:#2E7D4F">&#10003;</span></div>
  <div id="{{p}}-r2" style="padding:16px 30px 0;font:600 36px Outfit;color:{MUTED}">Pays your loan <span id="{{p}}-no" style="display:inline-block;color:{TERRA}">&#10007;</span></div>
</div>"""
S5 = head("Fire cover?", "the building") + letter('<div style="height:10px"></div>') + FIRE_CARD + note("Fire insurance protects my loan")

SHIELD = f"""<svg id="{{p}}-shield" width="70" height="80" viewBox="0 0 70 80" style="vertical-align:middle;margin-left:18px;overflow:visible">
  <path d="M35 4 L64 14 L60 48 Q55 66 35 76 Q15 66 10 48 L6 14 Z" fill="{FOREST}"/>
  <path id="{{p}}-tick" d="M22 40 L31 50 L49 28" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0" fill="none" stroke="{IVORY}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
S6 = head("On death or TPD", "MRTA or MLTA can pay") + letter(f"""<div class="row"><span class="k">Loan amount</span><span class="v">RM500,000</span>{SHIELD}</div>
  <div style="padding:26px 0 0" id="{{p}}-if"><span style="font:600 30px Outfit">{sp("If you die or become TPD")}</span></div>
  <div style="margin-top:16px"><span class="tag" id="{{p}}-t1">MRTA</span><span class="tag" id="{{p}}-t2" style="border-color:{ORANGE_TEXT};color:{ORANGE_TEXT}">MLTA</span></div>
  <div style="margin-top:30px;position:relative;width:748px;height:46px;background:{BEIGE}">
    <div id="{{p}}-fill" style="position:absolute;left:0;top:0;bottom:0;width:72%;background:{FOREST}"></div>
    <div id="{{p}}-fill2" style="position:absolute;left:72%;top:0;bottom:0;right:0;background:#5E7A72"></div>
    <div style="position:absolute;inset:0;border:3px dashed {FOREST}"></div></div>
  <div style="display:flex;justify-content:space-between;width:748px;margin-top:10px"><span class="tiny" id="{{p}}-some">pays some of the loan</span><span class="tiny" id="{{p}}-all">or all of it</span></div>
  <div class="fact" id="{{p}}-fact" style="font-size:28px">up to the amount you're covered for</div>""")

S7_LETTER_ROWS = f"""<div style="padding-top:30px;font:600 30px Outfit" class="cond">Conditions of offer</div>
  <div class="row cond"><span style="font:400 28px Outfit">Valuation report on the property</span></div>
  <div class="row cond"><span class="v" style="font:400 28px Outfit">Borrower to obtain mortgage cover<span class="hl" id="{{p}}-hl"></span></span></div>
  <div class="row cond"><span style="font:400 28px Outfit">Fire insurance on the building</span></div>
  <div id="{{p}}-margin" style="font:600 46px/1 Caveat;color:{TERRA};margin-top:26px">&#8593; a bank condition, not a law</div>"""
S7 = head("Compulsory?", "not by law") + letter(S7_LETTER_ROWS) + note("MRTA is required by law")

CONDITIONS_STATIC = S7_LETTER_ROWS
MINI = (("Pays my family", -5), ("Cover stays same", 3), ("Fire covers my loan", -2), ("Required by law", 5))
S8 = (letter(CONDITIONS_STATIC) + note("MRTA is required by law")
      + head("Know who gets paid", "before you sign")
      + f'<div id="{{p}}-notes" style="position:absolute;left:75px;top:450px;width:930px;height:330px">'
      + "".join(f'<div class="mini" style="position:absolute;left:{i * 215}px;top:{(i % 2) * 24}px;width:210px;height:200px;background:{PEACH};box-shadow:0 8px 14px rgba(0,0,0,.25);padding:18px;font:600 32px/1 Caveat;color:{FOREST}">{t}'
                f'<div class="ministamp" style="position:absolute;left:30px;top:96px;border:5px solid {TERRA};color:{TERRA};font:600 34px Outfit;letter-spacing:.1em;padding:2px 10px;mix-blend-mode:multiply">MYTH</div></div>'
                for i, (t, r) in enumerate(MINI))
      + "</div>"
      + f'<div id="{{p}}-takaful" style="position:absolute;left:75px;top:810px;font:500 34px Outfit;color:{IVORY}">Takaful versions: <b id="{{p}}-k1" style="display:inline-block;font-weight:600;color:{PEACH}">MRTT</b> and <b id="{{p}}-k2" style="display:inline-block;font-weight:600;color:{PEACH}">MLTT</b></div>'
      + f'<div id="{{p}}-cta" style="position:absolute;left:75px;top:890px;width:760px;height:130px;background:{ORANGE};display:flex;align-items:center;padding-left:40px;font:600 62px Outfit;color:{FOREST}"><span id="{{p}}-ctat" style="display:inline-block">Comment "MRTA"</span></div>'
      + '<img id="{p}-logo" src="assets/horizontal-reverse.svg" style="position:absolute;left:62px;top:1050px;width:500px;height:100px" alt="Senang Homes"/>')

BODIES = {"s1": S1, "s2": S2, "s3": S3, "s4": S4, "s5": S5, "s6": S6, "s7": S7, "s8": S8}

# ---------------------------------------------------------------- motion (scene-local seconds)
# Cue words: scene start + word time from the transcript (see SPEC.md SHOTS).
MOTION = {
    # S1 is the thumbnail at frame 0: everything readable is already on screen; motion adds to it.
    "s1": """
    tl.fromTo("#s1-note", { rotation: 0 }, { keyframes: [{ rotation: -4, duration: 0.12 }, { rotation: 3, duration: 0.12 }, { rotation: 0, duration: 0.25 }] }, 0.3);
    sweep("#s1-hl2", 1.55, 0.4);                                   // "MRTA"
    sweep("#s1-hl", 2.85, 0.6);                                    // "who does it actually pay?"
    pop("#s1-q", 3.4);
    tl.fromTo("#s1-n", { scale: 1 }, { keyframes: [{ scale: 1.35, duration: 0.12, ease: "power2.out" }, { scale: 1, duration: 0.3, ease: "power2.inOut" }] }, 4.7);  // "four"
    sweep("#s1-ul", 5.4, 0.5);                                     // "most buyers believe"
    """,
    "s2": """
    words("#s2-head", 0.05);
    stamp("#s2-stamp", 0.4, "#s2-note");                           // "Myth one"
    tl.fromTo("#s2-note", { scale: 1 }, { keyframes: [{ scale: 1.05, duration: 0.15 }, { scale: 1, duration: 0.3 }] }, 2.3);   // "family"
    strike("#s2-strike", 3.1);                                     // "In fact"
    tl.fromTo("#s2-q", { opacity: 1, scale: 1 }, { opacity: 0, scale: 0.2, duration: 0.15, ease: "power3.in" }, 4.4);
    tl.fromTo("#s2-blank", { opacity: 1 }, { opacity: 0, duration: 0.15 }, 4.5);
    typed("#s2-bank", 4.75);                                       // "bank"
    reveal("#s2-fact", 5.2, 0.6);
    tl.fromTo("#s2-drain", { scaleX: 1 }, { scaleX: 0.35, duration: 0.45, ease: "power2.inOut", transformOrigin: "0% 50%" }, 5.44);  // "reduce"
    tl.to("#s2-drain", { scaleX: 0, duration: 0.45, ease: "power2.inOut", transformOrigin: "0% 50%" }, 6.08);                          // "clear"
    """,
    "s3": """
    tl.set("#s3-stamp", { rotation: -12, opacity: 0.9 }, 0); tl.set("#s3-strike", { rotation: -6 }, 0);
    words("#s3-head", 0.05);
    reveal("#s3-row", 0.2, 0.45);                                  // "MLTA"
    reveal("#s3-cap", 0.8, 0.5);
    reveal("#s3-bank", 1.2, 0.8); count("#s3-n1", 380, 1.2, 0.8);    // "money left after the loan"
    reveal("#s3-left", 2.85, 0.5); count("#s3-n2", 120, 2.85, 0.5);  // "goes to you"
    reveal("#s3-fact", 3.3, 0.7);                                  // "you, or your nominee"
    """,
    "s4": """
    noteIn("#s4-note", 0.0);
    words("#s4-head", 0.1);
    stamp("#s4-stamp", 0.6, "#s4-note");                           // "Myth two"
    sweep("#s4-chart .grid", 1.1, 0.5);
    tl.fromTo("#s4-chart .ax", { opacity: 0 }, { opacity: 1, duration: 0.3, stagger: 0.06 }, 1.3);
    tl.fromTo("#s4-illus", { opacity: 0 }, { opacity: 1, duration: 0.3 }, 1.5);
    strike("#s4-strike", 2.3);                                     // "In fact"
    draw("#s4-mrta", 3.0, 1.6);                                    // "MRTA cover shrinks"
    tl.fromTo("#s4-mrta-l", { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.35, ease: "expo.out" }, 4.2);
    pop("#s4-chart .tick", 4.8, 0.1);                              // "schedule"
    draw("#s4-mlta", 6.45, 0.8);                                   // "MLTA"
    tl.fromTo("#s4-gap", { opacity: 0 }, { opacity: 0.28, duration: 0.6, ease: "power2.out" }, 7.0);
    tl.fromTo("#s4-mlta-l", { opacity: 0, x: 20 }, { opacity: 1, x: 0, duration: 0.35, ease: "expo.out" }, 7.6);  // "stays level"
    """,
    "s5": """
    noteIn("#s5-note", 0.0);
    words("#s5-head", 0.1);
    stamp("#s5-stamp", 0.5, "#s5-note");                           // "Myth three"
    tl.fromTo("#s5-fire", { x: -760, rotation: -12 }, { x: 0, rotation: 2.5, duration: 0.6, ease: "expo.out" }, 0.8);  // "Fire insurance"
    draw("#s5-house", 1.3, 0.8);
    pop("#s5-door", 2.0);
    strike("#s5-strike", 2.95);                                    // "In fact"
    reveal("#s5-r1", 4.0, 0.45); pop("#s5-ok", 4.3);                // "the building"
    reveal("#s5-r2", 4.8, 0.45); pop("#s5-no", 5.05);               // "not the loan"
    tl.to("#s5-fire", { keyframes: [{ x: -8, duration: 0.04 }, { x: 7, duration: 0.04 }, { x: -3, duration: 0.04 }, { x: 0, duration: 0.05 }] }, 5.2);
    """,
    "s6": """
    words("#s6-head", 0.05);
    pop("#s6-shield", 0.35); draw("#s6-tick", 0.6, 0.35);
    words("#s6-if", 0.1, 0.33);                                     // "If you die or become … disabled"
    pop("#s6-t1", 3.28);                                           // "MRTA"
    pop("#s6-t2", 4.64);                                           // "MLTA"
    sweep("#s6-fill", 5.9, 0.4); reveal("#s6-some", 5.9, 0.4);      // "some"
    sweep("#s6-fill2", 6.3, 0.35); reveal("#s6-all", 6.3, 0.4);     // "or all"
    reveal("#s6-fact", 6.75, 0.6);
    """,
    "s7": """
    noteIn("#s7-note", 0.0);
    words("#s7-head", 0.1);
    stamp("#s7-stamp", 0.5, "#s7-note");                           // "Myth four"
    reveal("#s7-letter .cond", 0.9, 0.4);
    tl.fromTo("#s7-letter .cond", { y: 14 }, { y: 0, duration: 0.4, ease: "expo.out", stagger: 0.15 }, 0.9);
    strike("#s7-strike", 3.4);                                     // "It isn't"
    sweep("#s7-hl", 4.45, 0.7);                                    // "your bank can make mortgage cover"
    reveal("#s7-margin", 6.3, 0.9);                                // "a loan condition"
    """,
    "s8": """
    tl.set("#s8-stamp", { rotation: -12, opacity: 0.9 }, 0); tl.set("#s8-strike", { rotation: -6 }, 0);
    tl.fromTo("#s8-letter", { y: 0, rotation: 0 }, { y: 2000, rotation: 9, duration: 0.45, ease: "power3.in" }, 0.0);
    tl.fromTo("#s8-note", { y: 0, rotation: 0 }, { y: 2100, rotation: -14, duration: 0.45, ease: "power3.in" }, 0.03);
    words("#s8-head", 0.45);
    tl.fromTo("#s8-notes .mini", { y: -1000, rotation: 18 }, { y: 0, rotation: (i) => [-5, 3, -2, 5][i], duration: 0.55, ease: "back.out(1.2)", stagger: 0.12 }, 0.5);
    tl.fromTo("#s8-notes .ministamp", { opacity: 0, scale: 1.7, rotation: -24 }, { opacity: 0.9, scale: 1, rotation: -12, duration: 0.18, ease: "power4.out", stagger: 0.12 }, 1.15);
    reveal("#s8-takaful", 0.95, 0.6);
    pop("#s8-k1", 1.68); pop("#s8-k2", 2.8);                       // "MRTT", "MLTT"
    reveal("#s8-cta", 4.0, 0.45);                                  // "Comment"
    tl.fromTo("#s8-ctat", { scale: 1 }, { keyframes: [{ scale: 1.12, duration: 0.12, ease: "power2.out" }, { scale: 1, duration: 0.3, ease: "power2.inOut" }] }, 4.56);  // "MRTA"
    tl.fromTo("#s8-logo", { opacity: 0, x: -70 }, { opacity: 1, x: 0, duration: 0.6, ease: "expo.out" }, 5.6);
    """,
}

# Sound effects on visible actions (sound.md §4): absolute start, file, volume, optional duration.
SFX = [
    (3.38, "pop", 0.22, None),                     # "?" pops
    (7.50, "impact-bass-1", 0.32, 1.2),            # S2 stamp
    (11.85, "typing", 0.18, 0.5),                  # THE BANK types
    (19.90, "whoosh-short", 0.25, None),           # S4 note drops in
    (20.50, "impact-bass-2", 0.32, 1.2),           # S4 stamp
    (28.70, "whoosh-short", 0.22, None),           # S5 note
    (29.20, "impact-bass-1", 0.30, 1.2),           # S5 stamp
    (29.50, "whoosh-cinematic", 0.22, 1.3),        # fire card swoops in
    (35.15, "pop", 0.22, None),                    # shield
    (38.08, "click-soft", 0.30, None),             # MRTA tag
    (39.44, "click-soft", 0.30, None),             # MLTA tag
    (42.50, "whoosh-short", 0.22, None),           # S7 note
    (43.00, "impact-bass-2", 0.30, 1.2),           # S7 stamp
    (50.20, "whoosh", 0.25, None),                 # letter drops away
    (54.20, "impact-bass-1", 0.28, 1.5),           # CTA lands
]


SFX_LEN = {"click-soft": 0.36, "impact-bass-1": 2.1, "impact-bass-2": 2.59, "pop": 0.72, "typing": 1.54,
           "whoosh-cinematic": 5.54, "whoosh-short": 0.57, "whoosh": 0.57}


def scene_file(sid: str) -> str:
    body = BODIES[sid].replace("{p}", sid)
    if sid == "s8":  # the S7 letter and note leaving: already read for 7.7 s in S7, not new text
        body = body.replace('id="s8-letter"', 'id="s8-letter" data-layout-ignore').replace('id="s8-note"', 'id="s8-note" data-layout-ignore')
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; }}
    {CSS.replace(chr(10), chr(10) + '    ')}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
    <div class="ground"></div>
    {body}
  </div>
  <script>
    {JS_HELPERS}
    {MOTION[sid]}
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""


def caption_groups() -> list[tuple[float, float, list[tuple[str, float, float]]]]:
    script = {}
    for line in (ROOT / "SCRIPT.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| (vo\d\d) \| [^|]+ \| ([^|]+) \|", line)
        if m:
            script[m.group(1)] = m.group(2).split()
    groups = []
    for vid, s in LINES.items():
        words = json.loads((ROOT / f"assets/vo/{vid}.words.json").read_text())
        said = script[vid] if len(script[vid]) == len(words) else [w["text"] for w in words]
        cur = []
        for i, (w, text) in enumerate(zip(words, said)):
            cur.append((text, s + w["start"], s + w["end"]))
            nxt = words[i + 1] if i + 1 < len(words) else None
            pause = nxt is not None and nxt["start"] - w["end"] >= 0.15
            if text[-1] in ".?!:," and len(cur) >= 2 or len(cur) == 5 or pause or nxt is None:
                if len(cur) == 1 and groups and groups[-1][2][-1][2] > s:  # same line: merge a lone word back
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
    .g {{ position: absolute; left: 90px; right: 90px; top: 1205px; text-align: center;
         font: 600 54px/1.15 Outfit; color: {IVORY}; }}
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


def index_file() -> str:
    hosts = "\n".join(
        f'      <div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" '
        f'data-start="{s}" data-duration="{e - s:.2f}" data-track-index="1" data-track-kind="graphics" '
        f'data-width="{W}" data-height="{H}"></div>' for sid, s, e in SCENES)
    audio = [f'      <audio id="{vid}" class="clip" src="assets/vo/{vid}.wav" data-start="{s}" data-track-index="{10 + i}" data-volume="1"></audio>'
             for i, (vid, s) in enumerate(LINES.items())]
    # Music bed (HeyGen catalog, "warm lo-fi piano with soft beat"): 0.14 under the voice (sound.md §5),
    # strong from its first bar, fading out under the end card.
    audio.append(f'      <audio id="bgm" class="clip" src="assets/bgm/track.mp3" data-start="0" data-duration="{FILM}" '
                 f'data-track-index="20" data-volume="0.14" data-fade-in="0.3" data-fade-out="2.5"></audio>')
    for i, (t, name, vol, dur) in enumerate(SFX):
        d = f' data-duration="{dur or SFX_LEN[name]}"' + (' data-fade-out="0.3"' if dur else "")
        audio.append(f'      <audio id="sfx{i:02d}" class="clip" src="assets/sfx/{name}.mp3" data-start="{t:.2f}"{d} '
                     f'data-track-index="{30 + i}" data-volume="{vol}"></audio>')
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: {FOREST}; }}
      #root {{ position: relative; width: 100%; height: 100%; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{FILM}" data-width="{W}" data-height="{H}">
{hosts}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{FILM}" data-track-index="2" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:5"></div>
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
    for sid, _, _ in SCENES:
        (COMP / f"{sid}.html").write_text(scene_file(sid), encoding="utf-8")
    (COMP / "captions.html").write_text(captions_file(), encoding="utf-8")
    (ROOT / "index.html").write_text(index_file(), encoding="utf-8")
    print(f"wrote {len(SCENES)} scenes, {len(caption_groups())} caption groups, {len(SFX)} sfx, index.html")
