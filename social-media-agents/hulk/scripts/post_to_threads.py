#!/usr/bin/env python3
"""Publish a text post to Threads via the Meta Threads Graph API.

Requires THREADS_USER_ID and THREADS_ACCESS_TOKEN (see .env.example) — you must create a
Meta developer app with Threads API access and generate these yourself; this script does not
handle the OAuth setup. Docs: https://developers.facebook.com/docs/threads

Usage:
    python post_to_threads.py --file drafts/20260716-120000.md
    python post_to_threads.py --text "Your post text here"
    python post_to_threads.py --file drafts/20260716-120000.md --image-url https://example.com/poster.png

--image-url attaches an image (e.g. a Canva-exported poster, per
../../design/poster-style-guide.md) to the post. The Threads API requires a publicly reachable
image URL — it does not accept local file uploads — so export the poster as PNG and host it (or
use the Canva export URL while it's valid).

Always review a draft before posting — this script does not filter or validate content beyond
Threads' own length limit.
"""
import argparse
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

GRAPH_API_BASE = "https://graph.threads.net/v1.0"
MAX_LEN = 500  # Threads text post character limit


def strip_draft_metadata(text: str) -> str:
    # generate_draft.py prepends HTML comment metadata lines; strip them before posting.
    return re.sub(r"^<!--.*?-->\n?", "", text, flags=re.MULTILINE).strip()


def publish(text: str, user_id: str, token: str, image_url: str | None = None) -> str:
    if len(text) > MAX_LEN:
        sys.exit(f"Post is {len(text)} characters, over the {MAX_LEN} limit. Trim it and retry.")

    params = {"text": text, "access_token": token}
    if image_url:
        params["media_type"] = "IMAGE"
        params["image_url"] = image_url
    else:
        params["media_type"] = "TEXT"

    create_resp = requests.post(
        f"{GRAPH_API_BASE}/{user_id}/threads",
        params=params,
        timeout=30,
    )
    create_resp.raise_for_status()
    creation_id = create_resp.json()["id"]

    # Threads recommends a short delay between container creation and publish.
    time.sleep(5)

    publish_resp = requests.post(
        f"{GRAPH_API_BASE}/{user_id}/threads_publish",
        params={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    publish_resp.raise_for_status()
    return publish_resp.json()["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a draft markdown file")
    group.add_argument("--text", help="Raw post text")
    parser.add_argument(
        "--image-url",
        default=None,
        help="Publicly reachable image URL (e.g. exported Canva poster) to attach to the post",
    )
    args = parser.parse_args()

    load_dotenv()
    user_id = os.environ.get("THREADS_USER_ID")
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not user_id or not token:
        sys.exit("THREADS_USER_ID and THREADS_ACCESS_TOKEN must be set. Copy .env.example to .env and fill it in.")

    if args.file:
        text = strip_draft_metadata(open(args.file).read())
    else:
        text = args.text

    print("About to post:\n---")
    print(text)
    print("---")
    if args.image_url:
        print(f"With image: {args.image_url}")
    if input("Publish this to Threads? [y/N] ").strip().lower() != "y":
        print("Aborted.")
        return

    post_id = publish(text, user_id, token, image_url=args.image_url)
    print(f"Published. Post id: {post_id}")


if __name__ == "__main__":
    main()
