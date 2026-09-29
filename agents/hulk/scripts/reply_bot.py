#!/usr/bin/env python3
"""Auto-respond to every comment on a Hulk Estate post with the WhatsApp closing link.

    python reply_bot.py --dry-run     # show what it would send
    python reply_bot.py               # send replies once
    python reply_bot.py --watch 300   # keep polling every 300 seconds

This is the ManyChat replacement, built on the platform APIs directly:

  Instagram — a real private DM to the commenter (one per comment, within 7 days of it,
              per Meta's private-reply rule) plus an optional public reply.
  Threads   — a public reply under the comment. Threads has NO public DM API, so a DM is
              not possible there; the wa.me link goes in the visible reply instead.

Which template fires is decided by keyword intent in config/agent.yaml (price / loan /
viewing / availability / default). Every comment already answered is recorded in
state/replied.json, so re-running never double-replies.
"""
from __future__ import annotations

import argparse
import re
import sys
import time

import yaml
from dotenv import load_dotenv

import common
import platforms
from common import HERE

# Windows consoles default to cp1252; make emoji/curly-quote output (e.g. the WhatsApp CTA) safe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _matches(keyword: str, text: str) -> bool:
    """Whole-word match, so "rm" doesn't fire on "warm" and "view" doesn't fire on "reviewer"."""
    return re.search(rf"(?<!\w){re.escape(keyword.lower())}(?!\w)", text) is not None


def pick_intent(cfg: dict, comment_text: str) -> dict:
    text = (comment_text or "").lower()
    intents = cfg["replies"]["intents"]
    for name, intent in intents.items():
        if name == "default":
            continue
        if any(_matches(kw, text) for kw in intent.get("keywords", [])):
            return {"name": name, **intent}
    return {"name": "default", **intents["default"]}


def render_reply(cfg: dict, intent: dict, listing: dict, username: str) -> str:
    size = listing.get("size")
    beds = listing.get("bedrooms")
    size_line = " / ".join(filter(None, [f"{size} sqft" if size else "", f"{beds} rooms" if beds else ""]))
    return intent["reply"].format(
        name=f"@{username}" if username else "Hi",
        link=common.whatsapp_link(cfg, listing),
        ref=listing.get("ref", ""),
        title=listing.get("title", "this unit"),
        price=listing.get("price", "on request"),
        status=(listing.get("status") or "available").lower(),
        location=listing.get("location", ""),
        size_line=size_line or "full specs on request",
    )


def listing_for_post(cfg: dict, ref: str, listings: list[dict]) -> dict:
    """The listing a post is about, for the reply text and WhatsApp prefill. Campaign posts
    ("campaign-khaya", "campaign-khaya-reel-...") map to their project; area carousels and rows
    since removed from the sheet get a generic stand-in — never common.find_listing(), whose
    SystemExit on an unknown ref killed the whole run on the first campaign post."""
    for item in listings:
        if item["ref"] == ref:
            return item
    if ref.startswith("campaign-"):
        name = ref.split("-")[1]
        path = common.profile_path(cfg, f"campaigns/{name}.yaml")
        if path.exists():
            project = yaml.safe_load(path.read_text(encoding="utf-8"))["project"].lower()
            match = next((i for i in listings if common.project_of(i) == project), None)
            if match:
                return match
    return {"title": "our listings", "ref": ""}


def fetch_comments(cfg: dict, platform: str, post_id: str) -> list[dict]:
    if platform == "threads":
        return [
            {"id": c["id"], "text": c.get("text", ""), "username": c.get("username", "")}
            for c in platforms.threads_replies(cfg, post_id)
        ]
    return [
        {"id": c["id"], "text": c.get("text", ""),
         "username": c.get("username") or (c.get("from") or {}).get("username", "")}
        for c in platforms.instagram_comments(cfg, post_id)
    ]


def send(cfg: dict, platform: str, comment_id: str, text: str, dry_run: bool) -> list[str]:
    """Return a list of human-readable descriptions of what was (or would be) sent."""
    rc = cfg["replies"]
    if platform == "threads":
        planned = [("threads public reply", rc.get("threads_public_reply", True), platforms.threads_reply)]
    else:
        planned = [
            ("instagram DM", rc.get("instagram_private_reply", True), platforms.instagram_private_reply),
            ("instagram public reply", rc.get("instagram_public_reply", True), platforms.instagram_reply),
        ]
    actions = []
    for label, enabled, fn in planned:
        if not enabled:
            continue
        # Each action on its own: a failed DM (e.g. missing messaging permission) must not
        # block the public reply, or the commenter gets nothing at all.
        try:
            if not dry_run:
                fn(cfg, comment_id, text)
            actions.append(label)
        except Exception as exc:
            print(f"  ! {label} failed: {exc}")
    return actions


def run_once(cfg: dict, dry_run: bool) -> int:
    if not cfg["replies"].get("enabled", True):
        print("replies.enabled is false in config/agent.yaml — nothing to do.")
        return 0

    me = {}
    for platform, fetch_me in (("threads", platforms.threads_me), ("instagram", platforms.instagram_me)):
        try:
            me[platform] = fetch_me(cfg).get("username", "").lower()
        except Exception:
            me[platform] = ""  # own-comment filtering is best-effort

    state = common.read_state(cfg, "replied")
    done = set(state.get("comment_ids", []))
    handled = 0
    listings = common.load_listings(cfg)

    for post in common.recent_posts(cfg):
        platform, post_id = post["platform"], post["post_id"]
        try:
            comments = fetch_comments(cfg, platform, post_id)
        except Exception as exc:  # e.g. the post was deleted — skip it, keep going
            print(f"! could not read comments on {platform} {post_id}: {str(exc)[:160]}")
            continue

        listing = listing_for_post(cfg, post["ref"], listings)
        for comment in comments:
            key = f"{platform}:{comment['id']}"
            if key in done:
                continue
            if cfg["replies"].get("skip_own_comments", True) and \
                    comment["username"].lower() and comment["username"].lower() == me.get(platform):
                done.add(key)
                continue

            intent = pick_intent(cfg, comment["text"])
            text = render_reply(cfg, intent, listing, comment["username"])
            print(f"\n[{platform}] @{comment['username']}: {comment['text'][:80]}")
            print(f"  intent={intent['name']}\n  -> {text}")

            actions = send(cfg, platform, comment["id"], text, dry_run)
            if not actions:
                continue  # everything failed — leave it unanswered so the next run retries
            print(f"  {'would send' if dry_run else 'sent'}: {', '.join(actions)}")
            handled += 1
            if not dry_run:
                done.add(key)

    if not dry_run:
        state["comment_ids"] = sorted(done)
        common.write_state(cfg, "replied", state)
    return handled


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=None, help="Hulk profile (default: HULK_PROFILE or senang-homes)")
    parser.add_argument("--dry-run", action="store_true", help="Print replies without sending")
    parser.add_argument("--watch", type=int, metavar="SECONDS",
                        help="Keep polling this often instead of running once")
    args = parser.parse_args()

    load_dotenv(HERE / ".env")
    cfg = common.load_config(args.profile)
    print(f"Profile: {cfg['_profile']} ({cfg.get('name', '')})")

    while True:
        count = run_once(cfg, args.dry_run)
        print(f"\n{count} comment(s) handled.")
        if not args.watch:
            return
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
