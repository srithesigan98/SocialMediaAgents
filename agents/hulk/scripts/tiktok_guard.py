#!/usr/bin/env python3
"""Check a post against TikTok's Community Guidelines (and the owner's no-price rule) before it goes up.

    import tiktok_guard
    problems = tiktok_guard.problems(caption, [Path("slide-1.jpg"), Path("video.mp4")])   # [] = clean

Added 2026-11-19 after TikTok issued Community Guidelines violations on posts showing prices: the
owner ruled that nothing with a price goes to TikTok, and that every TikTok post is checked first.

Two layers. A regex catches money amounts in the caption for free. Otherwise Claude reads the caption
and every slide / a frame every 2 s of each video against RULES. A failed check (API error, refusal,
unreadable answer) raises CheckError instead of returning [] — nothing reaches TikTok unchecked.
Videos need ffmpeg on PATH.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import anthropic

MODEL = "claude-opus-5-5"
MONEY = re.compile(r"\b(?:RM|MYR|USD|SGD|S\$|US\$)\s?\d|\$\s?\d|\d[\d,.]*\s?(?:k\s)?(?:ringgit|psf)\b", re.I)

RULES = """You check posts for Senang Homes, a Malaysian property agent, before they are published on TikTok.
The account has already received TikTok Community Guidelines violations, so be strict: if a rule is broken
anywhere — on screen in any image or video frame, or in the caption — the post is rejected.

1. No prices or money amounts (the owner's rule). Reject any amount of money: property prices or starting
   prices ("from RM785K", "RM970K"), nett/SPA price, price per sqft, monthly instalments, rent, deposits,
   fees, stamp duty, rebates or discounts in RM, loan amounts, salaries, and illustrative figures
   ("a RM500K home"). Price tags and price stickers count. Percentages on their own are not money amounts.
2. No financial promises (TikTok: Frauds and Scams — fake investment offers, get-rich-quick schemes).
   Reject guaranteed or certain returns, rental yield, capital appreciation or "passive income", loan-approval
   guarantees, "can't lose" claims, and invented urgency or scarcity ("last unit", "today only").
3. No marketing of regulated financial products (TikTok: Regulated Goods and Services): pushing people to
   sign up for a loan, insurance or investment scheme. Neutral education about how they work is fine.
4. Nothing misleading presented as fact, no personal data of other people (names with contact details, IC
   numbers, phone numbers other than the business's own), and nothing sexual, violent, hateful or dangerous.

The business's own WhatsApp contact line is allowed. Images are numbered; a video appears as frames.
Reply with JSON only: {"ok": true or false, "problems": ["<where: 'image N' or 'caption'> — <rule broken, what you saw>"]}"""


class CheckError(RuntimeError):
    """The check itself could not run — treat as 'not cleared', never as clean."""


def caption_problems(caption: str) -> list[str]:
    return [f"caption — rule 1, money amount {m.group(0).strip()!r}" for m in MONEY.finditer(caption)][:3]


def _frames(video: Path, out: Path, every: float = 2.0, cap: int = 40) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps=1/{every},scale=720:-2",
                    "-frames:v", str(cap), "-q:v", "4", str(out / "f%03d.jpg")], check=True)
    return sorted(out.glob("f*.jpg"))


def problems(caption: str, media: list[Path]) -> list[str]:
    """Rule breaches found in the caption or media ([] means cleared). Raises CheckError if unsure."""
    found = caption_problems(caption)
    if found:
        return found
    with tempfile.TemporaryDirectory() as tmp:
        images: list[Path] = []
        for i, m in enumerate(media):
            if not m.exists():
                raise CheckError(f"media missing: {m}")
            images += _frames(m, Path(tmp) / str(i)) if m.suffix.lower() == ".mp4" else [m]
        content: list[dict] = []
        for n, img in enumerate(images, 1):
            kind = "png" if img.suffix.lower() == ".png" else "jpeg"
            content += [{"type": "text", "text": f"Image {n}:"},
                        {"type": "image", "source": {"type": "base64", "media_type": f"image/{kind}",
                                                     "data": base64.standard_b64encode(img.read_bytes()).decode()}}]
        content.append({"type": "text", "text": f"Caption:\n<caption>\n{caption}\n</caption>"})
        try:
            resp = anthropic.Anthropic().beta.messages.create(
                model=MODEL, max_tokens=8000, system=RULES,
                messages=[{"role": "user", "content": content}],
                betas=["server-side-fallback-2026-07-01"],
                # In extra_body so this works on SDKs older than these parameters (CI installs the latest).
                extra_body={"output_config": {"effort": "medium"}, "fallbacks": "default"},
            )
        except anthropic.APIError as exc:
            raise CheckError(f"Claude API: {exc}") from exc
    if resp.stop_reason == "refusal":
        raise CheckError("the guideline check was refused")
    text = "".join(b.text for b in resp.content if b.type == "text")
    match = re.search(r"\{.*\}", text, re.S)
    try:
        verdict = json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        verdict = None
    if not isinstance(verdict, dict) or "ok" not in verdict:
        raise CheckError(f"unreadable verdict: {text[:200]!r}")
    if verdict["ok"] and not verdict.get("problems"):
        return []
    return [str(p) for p in verdict.get("problems") or ["flagged without a reason"]]


if __name__ == "__main__":   # python tiktok_guard.py "<caption>" file1.jpg video.mp4 ...
    print(problems(sys.argv[1], [Path(p) for p in sys.argv[2:]]) or "cleared")
