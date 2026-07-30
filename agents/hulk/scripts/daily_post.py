#!/usr/bin/env python3
"""Hulk daily auto-poster — generate ONE on-brand Threads post and publish it, every day.

Fully automatic (no human review). Designed to run on a schedule (GitHub Actions). Grounded in
the persona, content playbook, and topic guard.

Duty rules (see agents/hulk/scripts/README.md "Daily duty rules" for the source of truth):
    1. Post every day.
    2. Rotate deterministically through the 8 content frameworks in ../templates/ so the feed
       doesn't repeat the same shape two days running.
    3. Attach a poster when that day's framework is one of the three the persona calls
       "poster-worthy" (listicle_breakdown, standalone_aphorism, historical_compounding_reveal) —
       rendered locally with Pillow (see render_poster.py), matching the locked style spec in
       ../../design/poster-style-guide.md (shared with Blue Hulk). Unlike Facebook, the Threads
       API requires a publicly reachable image URL (no local file upload), so the poster PNG is
       committed to this repo and posted via its raw.githubusercontent.com URL. If rendering or
       the git push ever fails for any reason, rule 1 always wins — it falls back to a text-only
       post and prints a NOTE.

The framework rotation runs off ONE deterministic day counter, so which framework applies on a
given day is reproducible and never drifts:
    day_index = date.today().toordinal()
    framework = FRAMEWORKS[day_index % len(FRAMEWORKS)]

Credentials come from environment variables (GitHub Actions secrets) or a local .env:
    ANTHROPIC_API_KEY, THREADS_USER_ID, THREADS_ACCESS_TOKEN

Run manually to test:
    python daily_post.py                    # generate + post today's framework/topic
    python daily_post.py --dry-run          # generate + print only, do NOT post or push
    python daily_post.py --force-framework listicle_breakdown   # test a specific framework
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

from render_poster import render_poster

# Windows consoles default to cp1252; make emoji/curly-quote output safe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
REPO_ROOT = AGENT_DIR.parent.parent
GRAPH_API_BASE = "https://graph.threads.net/v1.0"
MODEL = "claude-sonnet-5"
MAX_LEN = 500  # Threads text post character limit

FRAMEWORKS = sorted(p.stem for p in (AGENT_DIR / "templates").glob("*.md"))
POSTER_WORTHY_FRAMEWORKS = {"listicle_breakdown", "standalone_aphorism", "historical_compounding_reveal"}

POSTER_PATH = HERE / "posted_assets" / "hulk-poster.png"  # single file, overwritten each poster day
GITHUB_OWNER_REPO = "srithesigan98/SocialMediaAgents"


def load_context() -> str:
    persona = (AGENT_DIR / "persona" / "hulk-system-prompt.md").read_text(encoding="utf-8")
    playbook = (AGENT_DIR / "playbook" / "content-playbook.md").read_text(encoding="utf-8")
    topics = yaml.safe_load((AGENT_DIR / "config" / "topics.yaml").read_text(encoding="utf-8"))
    topics_block = (
        "Allowed topics:\n- " + "\n- ".join(topics["allowed_topics"])
        + "\n\nDenied topics (never write about these):\n- " + "\n- ".join(topics["denied_topics"])
    )
    return f"{persona}\n\n---\n\n{playbook}\n\n---\n\n{topics_block}"


def day_index() -> int:
    return datetime.date.today().toordinal()


def todays_framework(force: str | None = None) -> str:
    if force:
        if force not in FRAMEWORKS:
            sys.exit(f"Unknown framework '{force}'. Options: {', '.join(FRAMEWORKS)}")
        return force
    return FRAMEWORKS[day_index() % len(FRAMEWORKS)]


def generate_post(framework: str) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    template = (AGENT_DIR / "templates" / f"{framework}.md").read_text(encoding="utf-8")

    instruction = (
        "Pick ONE topic from Hulk's allowed topic pillars (stock market, trading, crypto, or "
        "trading-adjacent personal finance) that fits today, then write ONE ready-to-publish "
        f"Threads post using this framework:\n\n{template}\n\n"
        f"Hard limit: the post MUST be under {MAX_LEN} characters (Threads' post limit) — aim "
        "for well under that so it reads tight, not padded.\n\n"
        "Output ONLY the final post text exactly as it should appear on Threads — no framework "
        "label, no topic label, no notes, no preamble, and no surrounding quotes."
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=load_context(),
        messages=[{"role": "user", "content": instruction}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if len(text) > MAX_LEN:
        text = text[:MAX_LEN].rsplit(" ", 1)[0].rstrip(".,;:!?") + "…"
        print(f"[hulk] NOTE: generated post exceeded {MAX_LEN} chars; trimmed.")
    return text


def generate_poster_slots(post_text: str) -> dict:
    """Ask Claude to split the already-written post into the poster's four text slots, per the
    locked style spec in ../../design/poster-style-guide.md."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    instruction = (
        "This Threads post needs a companion poster graphic. Extract these four slots from it "
        'and respond with ONLY a JSON object, no other text:\n\n'
        f'"""\n{post_text}\n"""\n\n'
        '{\n'
        '  "top_label": "a short one-line context tag, <=40 chars",\n'
        '  "headline": "the hook line, punchy, <=70 chars",\n'
        '  "body_lines": ["1-2 short supporting lines, each <=90 chars"],\n'
        '  "footer": "the closing line, <=90 chars"\n'
        "}"
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": instruction}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def push_poster_and_get_url(image_path: Path) -> str | None:
    """Commit the rendered poster to the repo and return its raw.githubusercontent.com URL —
    the Threads API requires a publicly reachable image URL and won't accept a local upload."""
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        rel_path = image_path.relative_to(REPO_ROOT).as_posix()

        subprocess.run(["git", "add", str(image_path)], cwd=REPO_ROOT, check=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"hulk: update daily poster ({day_index()})"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            raise RuntimeError(f"git commit failed: {commit.stdout}\n{commit.stderr}")
        if commit.returncode == 0:
            subprocess.run(["git", "push", "origin", branch], cwd=REPO_ROOT, check=True)

        return f"https://raw.githubusercontent.com/{GITHUB_OWNER_REPO}/{branch}/{rel_path}"
    except Exception as e:
        print(f"[hulk] Could not commit/push poster, skipping poster: {e}")
        return None


def generate_poster(post_text: str) -> str | None:
    """Rule 3: render a poster locally with Pillow (see render_poster.py), commit it to the
    repo, and return its raw GitHub URL. No Canva account/API involved — see
    agents/design/poster-style-guide.md."""
    try:
        slots = generate_poster_slots(post_text)
    except Exception as e:  # malformed JSON from the model, etc. — never let a poster kill the post
        print(f"[hulk] Could not derive poster slots, skipping poster: {e}")
        return None

    try:
        render_poster(
            slots["top_label"],
            slots["headline"],
            slots.get("body_lines", []),
            slots["footer"],
            POSTER_PATH,
            seed=day_index(),
        )
    except Exception as e:
        print(f"[hulk] Poster render failed, skipping poster: {e}")
        return None

    return push_poster_and_get_url(POSTER_PATH)


def publish(text: str, image_url: str | None = None) -> str:
    user_id = os.environ["THREADS_USER_ID"]
    token = os.environ["THREADS_ACCESS_TOKEN"]

    params = {"text": text, "access_token": token}
    if image_url:
        params["media_type"] = "IMAGE"
        params["image_url"] = image_url
    else:
        params["media_type"] = "TEXT"

    r = requests.post(f"{GRAPH_API_BASE}/{user_id}/threads", params=params, timeout=30)
    if not r.ok:
        sys.exit(f"Create container failed: {r.status_code} {r.text}")
    creation_id = r.json()["id"]

    time.sleep(5)  # Threads recommends a short delay between container creation and publish

    r = requests.post(
        f"{GRAPH_API_BASE}/{user_id}/threads_publish",
        params={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"Publish failed: {r.status_code} {r.text}")
    return r.json()["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Generate and print, do not post or push")
    parser.add_argument(
        "--force-framework", choices=FRAMEWORKS, default=None,
        help="Force today's post onto a specific framework, regardless of the day rotation",
    )
    args = parser.parse_args()

    load_dotenv(HERE / ".env")  # local convenience; real env vars (Actions secrets) take precedence
    required = ["ANTHROPIC_API_KEY"] + ([] if args.dry_run else ["THREADS_USER_ID", "THREADS_ACCESS_TOKEN"])
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required env var(s): {', '.join(missing)}")

    framework = todays_framework(args.force_framework)
    poster_worthy = framework in POSTER_WORTHY_FRAMEWORKS
    print(f"[hulk] day_index={day_index()} framework={framework} poster_worthy={poster_worthy}")

    text = generate_post(framework)
    print("[hulk] generated post:\n" + "-" * 48 + f"\n{text}\n" + "-" * 48)

    image_url = None
    if poster_worthy:
        if args.dry_run:
            print("[hulk] --dry-run: skipping poster render/push (would attach a poster here).")
        else:
            image_url = generate_poster(text)
            if not image_url:
                print("[hulk] NOTE: today's framework is poster-worthy but poster generation failed — posting text-only.")

    if args.dry_run:
        print(f"[hulk] --dry-run: not posting. would_attach_poster={poster_worthy}")
        return

    post_id = publish(text, image_url)
    print(f"[hulk] published{' (with poster)' if image_url else ''}. post id: {post_id}")


if __name__ == "__main__":
    main()
