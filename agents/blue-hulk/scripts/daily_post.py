#!/usr/bin/env python3
"""Blue Hulk daily auto-poster — generate ONE on-brand Facebook post and publish it.

Fully automatic (no human review). Designed to run on a schedule (GitHub Actions). It is
grounded in the persona, content playbook, copywriting engine, and topic guard, and rotates
through config/daily_topics.yaml so posts don't repeat soon.

Credentials come from environment variables (GitHub Actions secrets) or a local .env:
    ANTHROPIC_API_KEY, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN

Duties (see ../playbook/posting-duties.md):
  1. Post every day.
  2. Every 4th day is a Striker Zones post ending with the Telegram CTA.
  3. Every 3rd day is a poster day — logged here; Canva generation happens in an assisted
     session (this headless job has no Canva access). Attach one with --poster-image PATH.

Run manually to test:
    python daily_post.py                       # generate + post today's topic
    python daily_post.py --dry-run             # generate + print only, do NOT post
    python daily_post.py --poster-image p.png  # post today's text with a poster image attached
"""
import argparse
import datetime
import os
import sys
from pathlib import Path

import requests
import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

# Windows consoles default to cp1252; make emoji/curly-quote output safe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
MODEL = "claude-sonnet-5"

# Duty 2/3 cadence (see ../playbook/posting-duties.md). Deterministic by date so ratios hold.
STRIKER_EVERY = 4   # 1 in 4 posts is a Striker Zones post
POSTER_EVERY = 3    # 1 in 3 posts carries a poster
STRIKER_TELEGRAM_CTA = "https://t.me/strikerzonesadmin_bot"


def is_striker_day(d: datetime.date) -> bool:
    return d.toordinal() % STRIKER_EVERY == 0


def is_poster_day(d: datetime.date) -> bool:
    return d.toordinal() % POSTER_EVERY == 0


def load_context() -> str:
    persona = (AGENT_DIR / "persona" / "blue-hulk-system-prompt.md").read_text(encoding="utf-8")
    playbook = (AGENT_DIR / "playbook" / "content-playbook.md").read_text(encoding="utf-8")
    engine = (AGENT_DIR / "playbook" / "copywriting-engine.md").read_text(encoding="utf-8")
    topics = yaml.safe_load((AGENT_DIR / "config" / "topics.yaml").read_text(encoding="utf-8"))
    topics_block = (
        "Allowed topics:\n- " + "\n- ".join(topics["allowed_topics"])
        + "\n\nDenied topics (never write about these):\n- " + "\n- ".join(topics["denied_topics"])
    )
    return f"{persona}\n\n---\n\n{playbook}\n\n---\n\n{engine}\n\n---\n\n{topics_block}"


def todays_topic(d: datetime.date) -> str:
    cfg = yaml.safe_load((AGENT_DIR / "config" / "daily_topics.yaml").read_text(encoding="utf-8"))
    if is_striker_day(d):
        pool = cfg["striker_zones_angles"]
    else:
        pool = cfg["topics"]
    # deterministic rotation by date so the whole list cycles before repeating
    return pool[d.toordinal() % len(pool)]


def generate_post(topic: str, striker: bool) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    if striker:
        cta_rule = (
            "This is a STRIKER ZONES post. After the trading lesson lands, close by inviting the "
            "reader into the Striker Zones trading community and include this exact link on its "
            f"own line: {STRIKER_TELEGRAM_CTA}\n"
            "The invite must be value-first and low-pressure (a community of traders working on "
            "the same discipline) — NO profit promises, income claims, 'signals', or scarcity."
        )
    else:
        cta_rule = (
            "End with a natural engagement CTA (a question or soft ask to comment/save), never a "
            "hard sales pitch and no external links."
        )
    instruction = (
        f'Write ONE ready-to-publish Facebook post about: "{topic}".\n\n'
        "Output ONLY the final post text exactly as it should appear on Facebook — no framework "
        "label, no emotion line, no notes, no preamble, and no surrounding quotes. Follow the "
        "copywriting engine's pre-publish checklist and the persona's voice and scope. "
        + cta_rule
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=load_context(),
        messages=[{"role": "user", "content": instruction}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def publish(text: str, image_path: str | None = None) -> str:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    if image_path:
        # Photo post — the poster (duty 3) rides along as the image, caption carries the text.
        with open(image_path, "rb") as fh:
            r = requests.post(
                f"{GRAPH_API_BASE}/{page_id}/photos",
                data={"caption": text, "access_token": token},
                files={"source": fh},
                timeout=60,
            )
    else:
        r = requests.post(
            f"{GRAPH_API_BASE}/{page_id}/feed",
            data={"message": text, "access_token": token},
            timeout=30,
        )
    if not r.ok:
        sys.exit(f"Publish failed: {r.status_code} {r.text}")
    return r.json()["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Generate and print, do not post")
    parser.add_argument("--poster-image", help="Path to a poster image to attach (duty 3)")
    args = parser.parse_args()

    load_dotenv(HERE / ".env")  # local convenience; real env vars (Actions secrets) take precedence
    required = ["ANTHROPIC_API_KEY"] + ([] if args.dry_run else ["FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"])
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required env var(s): {', '.join(missing)}")

    today = datetime.date.today()
    striker = is_striker_day(today)
    poster_day = is_poster_day(today)
    print(f"[blue-hulk] {today} | striker_zones_day={striker} | poster_day={poster_day}")

    topic = todays_topic(today)
    print(f"[blue-hulk] topic: {topic}")
    text = generate_post(topic, striker)
    print("[blue-hulk] generated post:\n" + "-" * 48 + f"\n{text}\n" + "-" * 48)

    if poster_day and not args.poster_image:
        # Duty 3: headless job can't reach Canva. Flag it so the poster is produced in-session.
        print("[blue-hulk] NOTE: today is a poster day — generate a Canva poster in an assisted "
              "session (see ../playbook/posting-duties.md), or re-run with --poster-image PATH.")

    if args.dry_run:
        print("[blue-hulk] --dry-run: not posting.")
        return

    post_id = publish(text, image_path=args.poster_image)
    print(f"[blue-hulk] published{' with poster' if args.poster_image else ''}. post id: {post_id}")


if __name__ == "__main__":
    main()
