#!/usr/bin/env python3
"""Hulk daily auto-poster — generate Threads posts and publish them, every day.

Fully automatic (no human review). Designed to run on a schedule (GitHub Actions), three times a
day. Grounded in the persona, content playbook, and topic guard.

Duty rules (see agents/hulk/scripts/README.md "Daily duty rules" for the source of truth):
    1. Post 3 times a day, no matter what (see SLOT_HOURS_UTC for the three times).
    2. Every post carries a poster graphic — rendered locally with Pillow (see render_poster.py),
       matching the locked style spec in ../../design/poster-style-guide.md. Unlike Facebook, the
       Threads API requires a publicly reachable image URL (no local file upload), so the poster
       PNG is committed to this repo and posted via its raw.githubusercontent.com URL. If
       rendering or the git push ever fails, rule 1 always wins — it falls back to a text-only
       post and prints a NOTE.
    3. 1 out of every 3 days is a Striker Zones day — on that day, the FIRST of the three daily
       posts (slot 0) is drawn from ../config/striker_zones_topics.yaml, and its final line is
       always a CTA linking to https://t.me/strikerzonesadmin_bot (verbatim; the script appends
       it as a safety net if the model ever omits it). The other two slots that day still run the
       normal framework rotation.

The framework rotation (for non-Striker slots) runs off ONE deterministic global slot counter, so
which framework applies on a given day+slot is reproducible and never drifts:
    day_index = date.today().toordinal()
    global_slot = day_index * len(SLOT_HOURS_UTC) + slot_index
    framework = ROTATION[global_slot % len(ROTATION)]
    is_striker_zone_day = day_index % STRIKER_ZONE_EVERY_N_DAYS == 0
ROTATION is a weighted, hand-interleaved expansion of FRAMEWORKS (see FRAMEWORK_WEIGHTS below) —
reach/engagement leaders repeat more often per cycle, but never back-to-back.

Credentials come from environment variables (GitHub Actions secrets) or a local .env:
    ANTHROPIC_API_KEY, THREADS_USER_ID, THREADS_ACCESS_TOKEN

Run manually to test:
    python daily_post.py --slot 0                       # generate + post that slot's content
    python daily_post.py --slot 0 --dry-run             # generate + print only, do NOT post or push
    python daily_post.py --slot 0 --dry-run --force-striker     # preview the Striker Zones branch
    python daily_post.py --slot 1 --dry-run --force-framework listicle_breakdown
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import requests
import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

from render_poster import compute_illustrative_levels, render_poster, render_striker_poster

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

# Weighted rotation — reviewed 2026-08-10 against the first ~11 days of real metrics
# (see playbook/content-playbook.md "Performance review" for the full data and reasoning).
# historical_compounding_reveal reaches far more people (262 avg views vs. an 24-81 range for
# everything else) but drew zero likes/replies across all 3 instances — pure impressions, no
# interaction. progress_reveal, contrarian_reframe, and call_reasoning_risk are the actual
# engagement drivers (best like/reply rate). This weighting leans into reach without abandoning
# the frameworks that build interaction, rather than collapsing onto the single biggest number.
# Uses a weighted list (not raw FRAMEWORKS) so the day/slot -> framework mapping stays fully
# deterministic — same reproducibility property as before, just a longer, uneven cycle.
FRAMEWORK_WEIGHTS = {
    "historical_compounding_reveal": 3,
    "contrarian_reframe": 2,
    "call_reasoning_risk": 2,
    "progress_reveal": 2,
    "standalone_aphorism": 1,
    "listicle_breakdown": 1,
    "audience_question": 1,
    "confession_lesson": 1,
}
# Hand-interleaved (not grouped) so no framework repeats back-to-back, including across the
# cycle's wrap point — sum of FRAMEWORK_WEIGHTS above, spread evenly rather than blocked.
ROTATION = [
    "historical_compounding_reveal",
    "contrarian_reframe",
    "call_reasoning_risk",
    "progress_reveal",
    "standalone_aphorism",
    "historical_compounding_reveal",
    "listicle_breakdown",
    "audience_question",
    "call_reasoning_risk",
    "confession_lesson",
    "historical_compounding_reveal",
    "contrarian_reframe",
    "progress_reveal",
]
assert Counter(ROTATION) == Counter({fw: FRAMEWORK_WEIGHTS.get(fw, 1) for fw in FRAMEWORKS}), \
    "ROTATION must contain exactly FRAMEWORK_WEIGHTS copies of each framework in FRAMEWORKS"

# 3 daily posting times, in UTC: 01:00 / 06:00 / 12:00 = 9am / 2pm / 8pm Malaysia (UTC+8).
# Must match the `cron:` entries in ../../../.github/workflows/hulk-daily.yml, in order.
SLOT_HOURS_UTC = [1, 6, 12]

STRIKER_ZONES_CTA_LINK = "https://t.me/strikerzonesadmin_bot"
STRIKER_ZONE_EVERY_N_DAYS = 3   # rule 3: 1 out of every 3 days
STRIKER_ZONE_SLOT = 0          # on a Striker Zones day, the first of the 3 daily posts carries it

GITHUB_OWNER_REPO = "srithesigan98/SocialMediaAgents"
POST_LOG_PATH = HERE / "metrics" / "post_log.jsonl"


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


def is_striker_zone_day(force: bool = False) -> bool:
    return force or day_index() % STRIKER_ZONE_EVERY_N_DAYS == 0


def todays_striker_topic() -> str:
    pool = yaml.safe_load((AGENT_DIR / "config" / "striker_zones_topics.yaml").read_text(encoding="utf-8"))["topics"]
    return pool[day_index() % len(pool)]


def todays_framework(slot_index: int, force: str | None = None) -> str:
    if force:
        if force not in FRAMEWORKS:
            sys.exit(f"Unknown framework '{force}'. Options: {', '.join(FRAMEWORKS)}")
        return force
    global_slot = day_index() * len(SLOT_HOURS_UTC) + slot_index
    return ROTATION[global_slot % len(ROTATION)]


def generate_post(framework: str | None, striker_zone_slot: bool) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if striker_zone_slot:
        topic = todays_striker_topic()
        instruction = (
            f'Write ONE ready-to-publish Threads post about: "{topic}".\n\n'
            "This is a Striker Zones promotional post — the body should teach the zone-based "
            "trading concept genuinely (not a bare ad), then transition naturally into Striker "
            "Zones as where readers can see this in practice. The FINAL line of the post MUST be "
            "a call to action that invites the reader to join Striker Zones and includes this "
            f"exact link, verbatim, with no changes: {STRIKER_ZONES_CTA_LINK}\n\n"
            f"Hard limit: the post MUST be under {MAX_LEN} characters (Threads' post limit).\n\n"
            "Output ONLY the final post text exactly as it should appear on Threads — no "
            "framework label, no notes, no preamble, and no surrounding quotes. Follow the "
            "persona's voice and scope, except that this post's CTA is explicitly promotional by "
            "design (Striker Zones) rather than the usual light/native CTA."
        )
    else:
        template = (AGENT_DIR / "templates" / f"{framework}.md").read_text(encoding="utf-8")
        instruction = (
            "Pick ONE topic from Hulk's allowed topic pillars (stock market, trading, crypto, or "
            "trading-adjacent personal finance) that fits today, then write ONE ready-to-publish "
            f"Threads post using this framework:\n\n{template}\n\n"
            f"Hard limit: the post MUST be under {MAX_LEN} characters (Threads' post limit) — "
            "aim for well under that so it reads tight, not padded.\n\n"
            "Output ONLY the final post text exactly as it should appear on Threads — no "
            "framework label, no topic label, no notes, no preamble, and no surrounding quotes."
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


def _wait_until_fetchable(url: str, attempts: int = 8, delay_seconds: float = 2.0) -> bool:
    """raw.githubusercontent.com can lag a few seconds behind a fresh push. Threads fetches the
    image_url almost immediately after container creation, and degrades silently to a text-only
    post if that fetch fails — it does NOT raise an API error, so this must be checked here."""
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
            ["git", "commit", "-m", f"hulk: update poster (day {day_index()}, {image_path.stem})"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            raise RuntimeError(f"git commit failed: {commit.stdout}\n{commit.stderr}")
        if commit.returncode == 0:
            subprocess.run(["git", "push", "origin", branch], cwd=REPO_ROOT, check=True)

        url = f"https://raw.githubusercontent.com/{GITHUB_OWNER_REPO}/{branch}/{rel_path}"
        if not _wait_until_fetchable(url):
            print(f"[hulk] NOTE: poster pushed but not yet fetchable at {url} — skipping poster this run.")
            return None
        return url
    except Exception as e:
        print(f"[hulk] Could not commit/push poster, skipping poster: {e}")
        return None


def generate_poster(post_text: str, slot_index: int) -> str | None:
    """Rule 2: render a poster locally with Pillow (see render_poster.py), commit it to the
    repo, and return its raw GitHub URL. No Canva account/API involved — see
    agents/design/poster-style-guide.md. Every post gets one; if it fails, rule 1 still wins."""
    try:
        slots = generate_poster_slots(post_text)
    except Exception as e:  # malformed JSON from the model, etc. — never let a poster kill the post
        print(f"[hulk] Could not derive poster slots, skipping poster: {e}")
        return None

    out_path = HERE / "posted_assets" / f"hulk-poster-slot{slot_index}.png"
    try:
        render_poster(
            slots["top_label"],
            slots["headline"],
            slots.get("body_lines", []),
            slots["footer"],
            out_path,
            seed=day_index() * len(SLOT_HOURS_UTC) + slot_index,
        )
    except Exception as e:
        print(f"[hulk] Poster render failed, skipping poster: {e}")
        return None

    return push_poster_and_get_url(out_path)


def generate_striker_zone_poster(slot_index: int) -> str | None:
    """On the Striker Zones slot, use the dedicated poster style that mirrors the real
    Striker Zones 2.1 Pro TradingView indicator (light theme, teal entry/SL risk box,
    orange/green TP labels) instead of the generic dark poster. Levels are always
    synthetic/illustrative (compute_illustrative_levels) — never a real live price."""
    seed = day_index() * len(SLOT_HOURS_UTC) + slot_index
    levels = compute_illustrative_levels(seed)
    out_path = HERE / "posted_assets" / f"hulk-poster-slot{slot_index}.png"
    try:
        render_striker_poster(
            levels["symbol_label"], levels["entry"], levels["sl"],
            levels["tp1"], levels["tp2"], levels["tp3"], levels["decimals"],
            out_path, seed=seed,
        )
    except Exception as e:
        print(f"[hulk] Striker Zones poster render failed, skipping poster: {e}")
        return None

    return push_poster_and_get_url(out_path)


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


def log_publish(post_id: str, slot_index: int, striker_zone_slot: bool, framework: str | None, had_poster: bool) -> None:
    """Append this publish to metrics/post_log.jsonl and push it — the metrics-collect
    workflow reads this log to know which post IDs to fetch engagement numbers for. A logging
    failure must never fail the run; the post already went out successfully."""
    entry = {
        "date": datetime.date.today().isoformat(),
        "day_index": day_index(),
        "slot": slot_index,
        "post_id": post_id,
        "platform": "threads",
        "striker_zone_slot": striker_zone_slot,
        "framework": framework,
        "had_poster": had_poster,
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
            ["git", "commit", "-m", f"hulk: log post {post_id} (day {day_index()}, slot {slot_index})"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            raise RuntimeError(f"git commit failed: {commit.stdout}\n{commit.stderr}")
        if commit.returncode == 0:
            subprocess.run(["git", "push", "origin", branch], cwd=REPO_ROOT, check=True)
    except Exception as e:
        print(f"[hulk] NOTE: could not log post to metrics/post_log.jsonl: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--slot", type=int, required=True, choices=range(len(SLOT_HOURS_UTC)),
        help="Which of the 3 daily posting slots this run is for (0, 1, or 2)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate and print, do not post or push")
    parser.add_argument(
        "--force-striker", action="store_true", help="Force this slot onto the Striker Zones branch"
    )
    parser.add_argument(
        "--force-framework", choices=FRAMEWORKS, default=None,
        help="Force this slot onto a specific framework (ignored if this slot is the Striker Zones slot)",
    )
    args = parser.parse_args()

    load_dotenv(HERE / ".env")  # local convenience; real env vars (Actions secrets) take precedence
    required = ["ANTHROPIC_API_KEY"] + ([] if args.dry_run else ["THREADS_USER_ID", "THREADS_ACCESS_TOKEN"])
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required env var(s): {', '.join(missing)}")

    striker_zone_slot = args.force_striker or (
        is_striker_zone_day() and args.slot == STRIKER_ZONE_SLOT
    )
    framework = None if striker_zone_slot else todays_framework(args.slot, args.force_framework)
    print(
        f"[hulk] day_index={day_index()} slot={args.slot} "
        f"striker_zone_slot={striker_zone_slot} framework={framework or 'n/a (striker)'}"
    )

    text = generate_post(framework, striker_zone_slot)
    print("[hulk] generated post:\n" + "-" * 48 + f"\n{text}\n" + "-" * 48)

    if striker_zone_slot and STRIKER_ZONES_CTA_LINK not in text:
        # Safety net: the model must include the exact CTA link on Striker Zones slots.
        text = text.rstrip() + f"\n\nJoin Striker Zones: {STRIKER_ZONES_CTA_LINK}"
        print("[hulk] NOTE: CTA link was missing from the generated text; appended it.")

    image_url = None
    if args.dry_run:
        print("[hulk] --dry-run: skipping poster render/push (every post normally gets one).")
    else:
        image_url = (
            generate_striker_zone_poster(args.slot) if striker_zone_slot
            else generate_poster(text, args.slot)
        )
        if not image_url:
            print("[hulk] NOTE: poster generation failed for this post — posting text-only.")

    if args.dry_run:
        print("[hulk] --dry-run: not posting. would_attach_poster=True (unless render/push fails)")
        return

    post_id = publish(text, image_url)
    print(f"[hulk] published{' (with poster)' if image_url else ''}. post id: {post_id}")
    log_publish(post_id, args.slot, striker_zone_slot, framework, bool(image_url))


if __name__ == "__main__":
    main()
