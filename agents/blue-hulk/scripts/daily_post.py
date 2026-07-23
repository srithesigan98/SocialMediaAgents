#!/usr/bin/env python3
"""Blue Hulk daily auto-poster — generate ONE on-brand Facebook post and publish it, every day.

Fully automatic (no human review). Designed to run on a schedule (GitHub Actions). Grounded in
the persona, content playbook, copywriting engine, and topic guard.

Duty rules (see agents/blue-hulk/README.md "Daily duty rules" for the source of truth):
    1. Post every day.
    2. 1 out of every 4 posts is a Striker Zones post — drawn from
       config/striker_zones_topics.yaml — and its CTA must link to
       https://t.me/strikerzonesadmin_bot.
    3. 1 out of every 3 posts should carry a Canva poster related to that post.
       Canva generation isn't wired for this headless script yet (it needs the Canva Connect
       API with its own OAuth credentials, set up the same way FB_PAGE_ACCESS_TOKEN was) — see
       generate_poster() below. Until that's configured, poster days still publish as a text
       post (rule 1 always wins) and print a NOTE so it's obvious a poster was owed.

All three rules run off ONE deterministic day counter, so which rule applies on a given day is
reproducible and never drifts:
    day_index = date.today().toordinal()
    is_striker_zone_day = day_index % 4 == 0   (rule 2 — exactly 1 in 4 days)
    is_poster_day       = day_index % 3 == 0   (rule 3 — exactly 1 in 3 days)

Credentials come from environment variables (GitHub Actions secrets) or a local .env:
    ANTHROPIC_API_KEY, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
    CANVA_ACCESS_TOKEN, CANVA_BRAND_TEMPLATE_ID   (optional — enables rule 3 automation)

Run manually to test:
    python daily_post.py                    # generate + post today's topic/rules
    python daily_post.py --dry-run          # generate + print only, do NOT post
    python daily_post.py --force-striker    # test the Striker Zones branch regardless of date
    python daily_post.py --force-poster     # test the poster branch regardless of date
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

STRIKER_ZONES_CTA_LINK = "https://t.me/strikerzonesadmin_bot"
STRIKER_ZONE_EVERY_N_DAYS = 4   # rule 2: 1 out of every 4 posts
POSTER_EVERY_N_DAYS = 3        # rule 3: 1 out of every 3 posts


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


def day_index() -> int:
    return datetime.date.today().toordinal()


def is_striker_zone_day(force: bool = False) -> bool:
    return force or day_index() % STRIKER_ZONE_EVERY_N_DAYS == 0


def is_poster_day(force: bool = False) -> bool:
    return force or day_index() % POSTER_EVERY_N_DAYS == 0


def todays_topic(striker_zone_day: bool) -> str:
    filename = "striker_zones_topics.yaml" if striker_zone_day else "daily_topics.yaml"
    pool = yaml.safe_load((AGENT_DIR / "config" / filename).read_text(encoding="utf-8"))["topics"]
    # deterministic rotation by date so the whole list cycles before repeating
    idx = day_index() % len(pool)
    return pool[idx]


def generate_post(topic: str, striker_zone_day: bool) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if striker_zone_day:
        instruction = (
            f'Write ONE ready-to-publish Facebook post about: "{topic}".\n\n'
            "This is a Striker Zones promotional post — the body should teach the zone-based "
            "trading concept genuinely (not a bare ad), then transition naturally into Striker "
            "Zones as where readers can see this in practice. The FINAL line of the post MUST be "
            "a call to action that invites the reader to join Striker Zones and includes this "
            f"exact link, verbatim, with no changes: {STRIKER_ZONES_CTA_LINK}\n\n"
            "Output ONLY the final post text exactly as it should appear on Facebook — no "
            "framework label, no emotion line, no notes, no preamble, and no surrounding quotes. "
            "Follow the copywriting engine's pre-publish checklist and the persona's voice and "
            "scope, except that this post's CTA is explicitly promotional by design (Striker "
            "Zones) rather than the usual soft engagement CTA."
        )
    else:
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


def generate_poster(post_text: str) -> str | None:
    """Rule 3 hook: render a Canva poster for this post and return a publicly reachable image URL.

    Returns None (graceful no-op) until Canva automation is wired — see scripts/README.md
    "Automating Canva posters (rule 3)" for what CANVA_ACCESS_TOKEN + CANVA_BRAND_TEMPLATE_ID
    need to be, and how to get them. Once set, replace this body with a Canva Connect API
    autofill + export call (POST /v1/autofills, poll, GET the export URL) using the approved
    "High-Contrast Trading Strategy Poster" template referenced in
    ../../design/poster-style-guide.md.
    """
    token = os.environ.get("CANVA_ACCESS_TOKEN")
    template_id = os.environ.get("CANVA_BRAND_TEMPLATE_ID")
    if not token or not template_id:
        return None
    # TODO: implement the Canva Connect API autofill/export call here once credentials exist.
    print("[blue-hulk] CANVA_ACCESS_TOKEN is set but generate_poster() isn't implemented yet.")
    return None


def publish_text(text: str) -> str:
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


def publish_photo(text: str, image_url: str) -> str:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    r = requests.post(
        f"{GRAPH_API_BASE}/{page_id}/photos",
        data={"caption": text, "url": image_url, "access_token": token},
        timeout=60,
    )
    if not r.ok:
        sys.exit(f"Publish (photo) failed: {r.status_code} {r.text}")
    return r.json()["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Generate and print, do not post")
    parser.add_argument(
        "--force-striker", action="store_true", help="Force today's post onto the Striker Zones branch"
    )
    parser.add_argument(
        "--force-poster", action="store_true", help="Force today's post onto the poster branch"
    )
    args = parser.parse_args()

    load_dotenv(HERE / ".env")  # local convenience; real env vars (Actions secrets) take precedence
    required = ["ANTHROPIC_API_KEY"] + ([] if args.dry_run else ["FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"])
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required env var(s): {', '.join(missing)}")

    striker = is_striker_zone_day(args.force_striker)
    poster = is_poster_day(args.force_poster)

    topic = todays_topic(striker)
    print(f"[blue-hulk] day_index={day_index()} striker_zone_day={striker} poster_day={poster}")
    print(f"[blue-hulk] topic: {topic}")

    text = generate_post(topic, striker)
    print("[blue-hulk] generated post:\n" + "-" * 48 + f"\n{text}\n" + "-" * 48)

    if striker and STRIKER_ZONES_CTA_LINK not in text:
        # Safety net: the model must include the exact CTA link on Striker Zones days.
        text = text.rstrip() + f"\n\nJoin Striker Zones: {STRIKER_ZONES_CTA_LINK}"
        print("[blue-hulk] NOTE: CTA link was missing from the generated text; appended it.")

    image_url = None
    if poster:
        image_url = generate_poster(text)
        if not image_url:
            print(
                "[blue-hulk] NOTE: today is a poster day (1-in-3) but Canva automation isn't "
                "wired yet — posting text-only. See scripts/README.md 'Automating Canva posters "
                "(rule 3)' to enable it."
            )

    if args.dry_run:
        print(f"[blue-hulk] --dry-run: not posting. would_attach_poster={bool(image_url)}")
        return

    post_id = publish_photo(text, image_url) if image_url else publish_text(text)
    print(f"[blue-hulk] published{' (with poster)' if image_url else ''}. post id: {post_id}")


if __name__ == "__main__":
    main()
