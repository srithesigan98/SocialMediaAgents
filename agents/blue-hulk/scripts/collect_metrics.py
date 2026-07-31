#!/usr/bin/env python3
"""Collect engagement metrics for Blue Hulk's published Facebook posts.

Reads metrics/post_log.jsonl (written by daily_post.py on every publish), calls the Facebook
Graph API for each logged post's current likes/comments/shares (+ best-effort impressions via
the Insights endpoint, which needs read_insights on the Page token and silently degrades to null
if that permission isn't granted), and appends one timestamped snapshot per post to
metrics/history.jsonl. Designed to run on a schedule (GitHub Actions) so the dashboard has a
trend over time, not just a single latest-value snapshot.

Never fails the whole run over one bad post — a single post's fetch error is logged and skipped
so the rest of the batch still gets collected.

Run manually to test:
    python collect_metrics.py
"""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
POST_LOG_PATH = HERE / "metrics" / "post_log.jsonl"
HISTORY_PATH = HERE / "metrics" / "history.jsonl"


def load_post_ids() -> list[str]:
    if not POST_LOG_PATH.exists():
        return []
    ids, seen = [], set()
    for line in POST_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        post_id = json.loads(line)["post_id"]
        if post_id not in seen:
            seen.add(post_id)
            ids.append(post_id)
    return ids


def fetch_engagement(post_id: str, token: str) -> dict:
    r = requests.get(
        f"{GRAPH_API_BASE}/{post_id}",
        params={"fields": "likes.summary(true),comments.summary(true),shares", "access_token": token},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "likes": data.get("likes", {}).get("summary", {}).get("total_count"),
        "comments": data.get("comments", {}).get("summary", {}).get("total_count"),
        "shares": data.get("shares", {}).get("count"),
    }


def fetch_impressions(post_id: str, token: str) -> dict:
    """Best-effort — requires read_insights on the Page token. Returns nulls if unavailable."""
    try:
        r = requests.get(
            f"{GRAPH_API_BASE}/{post_id}/insights",
            params={"metric": "post_impressions,post_engaged_users", "access_token": token},
            timeout=30,
        )
        r.raise_for_status()
        values = {row["name"]: row["values"][0]["value"] for row in r.json().get("data", [])}
        return {
            "impressions": values.get("post_impressions"),
            "engaged_users": values.get("post_engaged_users"),
        }
    except Exception:
        return {"impressions": None, "engaged_users": None}


def append_and_push(snapshots: list[dict]) -> None:
    if not snapshots:
        print("[blue-hulk-metrics] Nothing to append.")
        return
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        for snap in snapshots:
            f.write(json.dumps(snap) + "\n")

    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        subprocess.run(["git", "add", str(HISTORY_PATH)], cwd=REPO_ROOT, check=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"blue-hulk: metrics snapshot ({len(snapshots)} posts)"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            raise RuntimeError(f"git commit failed: {commit.stdout}\n{commit.stderr}")
        if commit.returncode == 0:
            subprocess.run(["git", "push", "origin", branch], cwd=REPO_ROOT, check=True)
    except Exception as e:
        print(f"[blue-hulk-metrics] NOTE: could not commit/push history.jsonl: {e}")


def main() -> None:
    load_dotenv(HERE / ".env")
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not token:
        sys.exit("Missing required env var: FB_PAGE_ACCESS_TOKEN")

    post_ids = load_post_ids()
    print(f"[blue-hulk-metrics] {len(post_ids)} post(s) in log.")

    collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    snapshots = []
    for post_id in post_ids:
        try:
            snap = {"collected_at": collected_at, "post_id": post_id}
            snap.update(fetch_engagement(post_id, token))
            snap.update(fetch_impressions(post_id, token))
            snapshots.append(snap)
            print(f"[blue-hulk-metrics] {post_id}: {snap}")
        except Exception as e:
            print(f"[blue-hulk-metrics] NOTE: failed to fetch metrics for {post_id}, skipping: {e}")

    append_and_push(snapshots)


if __name__ == "__main__":
    main()
