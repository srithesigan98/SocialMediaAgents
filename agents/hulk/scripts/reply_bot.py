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
import time
import traceback

from dotenv import load_dotenv

import common
import platforms
from common import HERE


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
    actions = []
    if platform == "threads":
        if rc.get("threads_public_reply", True):
            if not dry_run:
                platforms.threads_reply(cfg, comment_id, text)
            actions.append("threads public reply")
    else:
        if rc.get("instagram_private_reply", True):
            if not dry_run:
                platforms.instagram_private_reply(cfg, comment_id, text)
            actions.append("instagram DM")
        if rc.get("instagram_public_reply", True):
            if not dry_run:
                platforms.instagram_reply(cfg, comment_id, text)
            actions.append("instagram public reply")
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

    for post in common.recent_posts(cfg):
        platform, post_id = post["platform"], post["post_id"]
        try:
            comments = fetch_comments(cfg, platform, post_id)
        except Exception:
            print(f"! could not read comments on {platform} {post_id}:\n{traceback.format_exc()}")
            continue

        listing = common.find_listing(cfg, post["ref"])
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

            try:
                actions = send(cfg, platform, comment["id"], text, dry_run)
            except Exception:
                print(f"  ! reply failed:\n{traceback.format_exc()}")
                continue

            print(f"  {'would send' if dry_run else 'sent'}: {', '.join(actions) or 'nothing (all reply modes off)'}")
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
