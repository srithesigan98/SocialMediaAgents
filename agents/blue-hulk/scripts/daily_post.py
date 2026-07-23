#!/usr/bin/env python3
"""Blue Hulk daily auto-poster — generate ONE on-brand Facebook post and publish it.

Fully automatic (no human review). Designed to run on a schedule (GitHub Actions). It is
grounded in the persona, content playbook, copywriting engine, and topic guard, and rotates
through config/daily_topics.yaml so posts don't repeat soon.

Credentials come from environment variables (GitHub Actions secrets) or a local .env:
    ANTHROPIC_API_KEY, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN

Run manually to test:
    python daily_post.py            # generate + post today's topic
    python daily_post.py --dry-run  # generate + print only, do NOT post
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


def todays_topic() -> str:
    pool = yaml.safe_load((AGENT_DIR / "config" / "daily_topics.yaml").read_text(encoding="utf-8"))["topics"]
    # deterministic rotation by date so the whole list cycles before repeating
    idx = datetime.date.today().toordinal() % len(pool)
    return pool[idx]


def generate_post(topic: str) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    instruction = (
        f'Write ONE ready-to-publish Facebook post about: "{topic}".\n\n'
        "Output ONLY the final post text exactly as it should appear on Facebook — no framework "
        "label, no emotion line, no notes, no preamble, and no surrounding quotes. Follow the "
        "copywriting engine's pre-publish checklist and the persona's voice and scope. End with a "
        "natural engagement CTA (a question or soft ask to comment/save), never a hard sales pitch."
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=load_context(),
        messages=[{"role": "user", "content": instruction}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def publish(text: str) -> str:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
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
    args = parser.parse_args()

    load_dotenv(HERE / ".env")  # local convenience; real env vars (Actions secrets) take precedence
    required = ["ANTHROPIC_API_KEY"] + ([] if args.dry_run else ["FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"])
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required env var(s): {', '.join(missing)}")

    topic = todays_topic()
    print(f"[blue-hulk] topic: {topic}")
    text = generate_post(topic)
    print("[blue-hulk] generated post:\n" + "-" * 48 + f"\n{text}\n" + "-" * 48)

    if args.dry_run:
        print("[blue-hulk] --dry-run: not posting.")
        return

    post_id = publish(text)
    print(f"[blue-hulk] published. post id: {post_id}")


if __name__ == "__main__":
    main()
