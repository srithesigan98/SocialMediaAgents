#!/usr/bin/env python3
"""Black Panther daily auto-poster — generate ONE Instagram feed post and publish it, every day.

Fully automatic (no human review). Designed to run on a schedule (GitHub Actions). Grounded in
the persona, topic guard, and the-watcher's caption/hashtag playbook.

Duty rule (see agents/black-panther/scripts/README.md for the source of truth):
    1. Post once a day. Every post carries a poster graphic — rendered locally with Pillow (see
       render_poster.py), matching the locked style spec in ../../design/poster-style-guide.md.
       Like Threads, the Instagram Graph API requires a publicly reachable image URL (no local
       file upload), so the poster PNG is committed to this repo and posted via its
       raw.githubusercontent.com URL. If rendering or the git push ever fails, rule 1 still
       wins — it prints a NOTE and skips the day rather than posting a broken/textless feed post
       (Instagram has no text-only post type, unlike Facebook/Threads).

Credentials come from environment variables (GitHub Actions secrets) or a local .env:
    ANTHROPIC_API_KEY, IG_USER_ID, IG_ACCESS_TOKEN

Run manually to test:
    python daily_post.py --dry-run    # generate + print + render only, do NOT post or push
    python daily_post.py              # generate + POST today's post
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

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
REPO_ROOT = AGENT_DIR.parent.parent
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
MODEL = "claude-sonnet-5"

GITHUB_OWNER_REPO = "srithesigan98/SocialMediaAgents"
POSTER_PATH = HERE / "posted_assets" / "black-panther-poster.png"
POST_LOG_PATH = HERE / "metrics" / "post_log.jsonl"


def load_context() -> str:
    persona = (AGENT_DIR / "persona" / "black-panther-system-prompt.md").read_text(encoding="utf-8")
    topics = yaml.safe_load((AGENT_DIR / "config" / "topics.yaml").read_text(encoding="utf-8"))
    topics_block = (
        "Allowed topics:\n- " + "\n- ".join(topics["allowed_topics"])
        + "\n\nDenied topics (never write about these):\n- " + "\n- ".join(topics["denied_topics"])
    )
    return f"{persona}\n\n---\n\n{topics_block}"


def day_index() -> int:
    return datetime.date.today().toordinal()


def generate_post() -> dict:
    """Ask Claude for a caption AND the poster's four slots in one call, since a feed post's
    poster and caption should share the same hook/angle rather than being derived separately."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    instruction = (
        "Pick ONE topic from the allowed topic pillars that fits today, then write ONE "
        "ready-to-publish Instagram feed post about it: a caption (hook line, 2-4 short body "
        "lines, soft native CTA) and a companion poster's four text slots.\n\n"
        "Respond with ONLY a JSON object, no other text:\n"
        "{\n"
        '  "caption": "the full caption text, hashtags included at the end (5-8, mixed niche/geo/broad)",\n'
        '  "top_label": "a short one-line context tag for the poster, <=40 chars",\n'
        '  "headline": "the poster hook line, punchy, <=70 chars",\n'
        '  "body_lines": ["1-2 short supporting lines for the poster, each <=90 chars"],\n'
        '  "footer": "the poster\'s closing line, <=90 chars"\n'
        "}"
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=900,
        system=load_context(),
        messages=[{"role": "user", "content": instruction}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def _wait_until_fetchable(url: str, attempts: int = 8, delay_seconds: float = 2.0) -> bool:
    """raw.githubusercontent.com can lag a few seconds behind a fresh push, and Instagram fetches
    image_url as soon as the media container is created — this closes that race window (same
    issue Hulk's Threads posting hit; see its daily_post.py for the original fix)."""
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(url, timeout=10)
            if r.ok:
                return True
        except requests.RequestException:
            pass
        if attempt < attempts:
            time.sleep(delay_seconds)
    return False


def push_poster_and_get_url(image_path: Path) -> str | None:
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        rel_path = image_path.relative_to(REPO_ROOT).as_posix()

        subprocess.run(["git", "add", str(image_path)], cwd=REPO_ROOT, check=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"black-panther: update poster (day {day_index()})"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            raise RuntimeError(f"git commit failed: {commit.stdout}\n{commit.stderr}")
        if commit.returncode == 0:
            subprocess.run(["git", "push", "origin", branch], cwd=REPO_ROOT, check=True)

        url = f"https://raw.githubusercontent.com/{GITHUB_OWNER_REPO}/{branch}/{rel_path}"
        if not _wait_until_fetchable(url):
            print(f"[black-panther] NOTE: poster pushed but not yet fetchable at {url}")
            return None
        return url
    except Exception as e:
        print(f"[black-panther] Could not commit/push poster: {e}")
        return None


def publish(caption: str, image_url: str) -> str:
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]

    r = requests.post(
        f"{GRAPH_API_BASE}/{user_id}/media",
        params={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"Create media container failed: {r.status_code} {r.text}")
    creation_id = r.json()["id"]

    # Instagram processes the container asynchronously — poll status_code until FINISHED
    # rather than a fixed sleep (per Meta's Content Publishing API docs).
    for attempt in range(15):
        r = requests.get(
            f"{GRAPH_API_BASE}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
        r.raise_for_status()
        status = r.json().get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            sys.exit(f"Media container failed processing: {r.text}")
        time.sleep(2)
    else:
        sys.exit("Media container never finished processing (timed out after 30s).")

    r = requests.post(
        f"{GRAPH_API_BASE}/{user_id}/media_publish",
        params={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"Publish failed: {r.status_code} {r.text}")
    return r.json()["id"]


def log_publish(post_id: str, topic_hint: str) -> None:
    """Append this publish to metrics/post_log.jsonl and push it — the metrics-collect
    workflow reads this log to know which post IDs to fetch engagement numbers for. A logging
    failure must never fail the run; the post already went out successfully."""
    entry = {
        "date": datetime.date.today().isoformat(),
        "day_index": day_index(),
        "post_id": post_id,
        "platform": "instagram",
        "topic_hint": topic_hint,
    }
    try:
        POST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(POST_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        subprocess.run(["git", "add", str(POST_LOG_PATH)], cwd=REPO_ROOT, check=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"black-panther: log post {post_id} (day {day_index()})"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            raise RuntimeError(f"git commit failed: {commit.stdout}\n{commit.stderr}")
        if commit.returncode == 0:
            subprocess.run(["git", "push", "origin", branch], cwd=REPO_ROOT, check=True)
    except Exception as e:
        print(f"[black-panther] NOTE: could not log post to metrics/post_log.jsonl: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Generate and render, do not post or push")
    args = parser.parse_args()

    load_dotenv(HERE / ".env")
    required = ["ANTHROPIC_API_KEY"] + ([] if args.dry_run else ["IG_USER_ID", "IG_ACCESS_TOKEN"])
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required env var(s): {', '.join(missing)}")

    print(f"[black-panther] day_index={day_index()}")
    post = generate_post()
    print("[black-panther] caption:\n" + "-" * 48 + f"\n{post['caption']}\n" + "-" * 48)

    render_out = HERE / "drafts" / "poster-preview.png" if args.dry_run else POSTER_PATH
    render_out.parent.mkdir(parents=True, exist_ok=True)
    render_poster(
        post["top_label"], post["headline"], post.get("body_lines", []), post["footer"],
        render_out, seed=day_index(),
    )
    print(f"[black-panther] poster rendered: {render_out}")

    if args.dry_run:
        print("[black-panther] --dry-run: not posting.")
        return

    image_url = push_poster_and_get_url(POSTER_PATH)
    if not image_url:
        sys.exit("[black-panther] Poster isn't publicly reachable — Instagram requires an image for every post. Skipping today rather than posting broken.")

    post_id = publish(post["caption"], image_url)
    print(f"[black-panther] published. post id: {post_id}")
    log_publish(post_id, post["headline"])


if __name__ == "__main__":
    main()
