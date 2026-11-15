#!/usr/bin/env python3
"""Word timings for the Kokoro voice lines (fallback for Parakeet, whose model host was blocked here).

The text is known exactly (we wrote it), so this is alignment, not recognition: speech/pause segments come
from the wav's energy, each punctuation phrase is mapped to a speech run, and words inside a phrase share
its time by espeak phoneme count (the same phonemizer Kokoro speaks from). Captions use the DISPLAY text,
where `token{n}` means the token covers n spoken words (e.g. RM600,000{3} = "six hundred thousand").

    python tools/align.py      -> assets/vo/voNN.words.json
"""
import json, re
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro_onnx.tokenizer import Tokenizer

ROOT = Path(__file__).resolve().parent.parent
DISPLAY = {
    "vo01": "Your salary looks fine. So why did the bank say no? Usually, it's one number: your DSR.{3}",
    "vo02": "Debt service ratio. Add up your monthly debts, then divide by your net income, after EPF{3} and tax.",
    "vo03": "Illustration: RM5,000{2} net a month. Car loan, RM800.{2} PTPTN,{5} RM200.{2} The new home loan, RM2,000.{2}",
    "vo04": "That's RM3,000{2} in debts. Divide by RM5,000:{2} 60%{2} of your income.",
    "vo05": "A credit card you pay in full may still count. Here, RM500{2} more: now 70%.{2}",
    "vo06": "Each bank sets its own limit, and may also check what's left after your debts.",
    "vo07": "To bring it down, cancel cards you don't use, and clear small loans before you apply.",
    "vo08": "Cancel that card, clear the car loan, and the same home is 44%.{2}",
    "vo09": "Comment \"DSR\",{3} and we'll work out your number before you view.",
}
tok = Tokenizer()


def segments(wav):
    a, sr = sf.read(wav)
    if a.ndim > 1: a = a.mean(1)
    hop = int(sr * 0.01)
    rms = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a) - hop, hop)])
    on = rms > max(rms.max() * 0.03, 1e-4)
    segs, start, gap = [], None, 0
    for i, v in enumerate(on):
        if v:
            if start is None: start = i
            gap = 0; last = i
        elif start is not None:
            gap += 1
            if gap >= 9:   # 90 ms pause splits
                segs.append([start / 100, (last + 1) / 100]); start = None
    if start is not None: segs.append([start / 100, (last + 1) / 100])
    return segs


def main():
    lines = dict(l.rstrip("\n").split("\t") for l in (ROOT / "tools/lines.tsv").open())
    for vid, spoken in lines.items():
        sw = spoken.split()
        weights = [len(re.sub(r"[ˈˌ\s.,:?!]", "", tok.phonemize(w, "en-us"))) + 1 for w in sw]
        # phrases = runs of spoken words ending in punctuation
        phrases, cur = [], []
        for i, w in enumerate(sw):
            cur.append(i)
            if w[-1] in ".,:?!": phrases.append(cur); cur = []
        if cur: phrases.append(cur)
        segs = segments(ROOT / f"assets/vo/{vid}.wav")
        while len(segs) > len(phrases):   # merge across the smallest pause
            g = min(range(len(segs) - 1), key=lambda k: segs[k + 1][0] - segs[k][1])
            segs[g] = [segs[g][0], segs[g + 1][1]]; del segs[g + 1]
        times = [None] * len(sw)
        if len(segs) == len(phrases):
            groups = list(zip(phrases, segs))
        else:   # fewer pauses than phrases: put each pause on the phrase end nearest in weight share
            speech = sum(e - s for s, e in segs); tw = sum(weights)
            ends, acc = [], 0
            for ph in phrases[:-1]:
                acc += sum(weights[i] for i in ph); ends.append(acc / tw)
            groups, first, acc = [], 0, 0
            for g in range(len(segs)):
                acc += segs[g][1] - segs[g][0]
                if g == len(segs) - 1: last = len(phrases)
                else:
                    cand = range(first + 1, len(phrases))
                    last = min(cand, key=lambda j: abs(ends[j - 1] - acc / speech))
                groups.append(([i for ph in phrases[first:last] for i in ph], segs[g])); first = last
        for idx, (s, e) in groups:
            tot = sum(weights[i] for i in idx); t = s
            for i in idx:
                d = (e - s) * weights[i] / tot; times[i] = (round(t, 3), round(t + d, 3)); t += d
        out, k = [], 0
        for n, token in enumerate(DISPLAY[vid].split()):
            m = re.match(r"(.*)\{(\d+)\}$", token)
            text, cnt = (m.group(1), int(m.group(2))) if m else (token, 1)
            out.append({"id": f"w{n}", "text": text, "start": times[k][0], "end": times[k + cnt - 1][1]}); k += cnt
        assert k == len(sw), (vid, k, len(sw))
        (ROOT / f"assets/vo/{vid}.words.json").write_text(json.dumps(out, indent=1))
        print(vid, f"{len(segs)} runs/{len(phrases)} phrases", " ".join(f"{w['text']}@{w['start']:.2f}" for w in out))


main()
