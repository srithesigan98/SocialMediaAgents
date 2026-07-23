#!/usr/bin/env python3
"""Publish a post to a Facebook Page via the Meta Graph API.

Requires FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN in .env (see .env.example and scripts/README.md
for how to generate them at developers.facebook.com).

Usage:
    python post_to_facebook.py --file drafts/20260717-120000.md
    python post_to_facebook.py --text "Your post text here"
    python post_to_facebook.py --file drafts/20260717-120000.md --image poster.png
    python post_to_facebook.py --text "Caption" --image-url https://example.com/poster.png

Unlike the Threads API, the Facebook Graph API accepts direct local file uploads for photos —
so a Canva-exported poster PNG can be attached with --image without hosting it anywhere.

Always review a draft before posting — this script does not validate content.
"""
import argparse
import os
import re
import sys

import requests
from dotenv import load_dotenv

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def strip_draft_metadata(text: str) -> str:
    # generate_draft.py prepends HTML comment metadata lines; strip them before posting.
    return re.sub(r"^<!--.*?-->\n?", "", text, flags=re.MULTILINE).strip()


def publish_text(text: str, page_id: str, token: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{page_id}/feed",
        data={"message": text, "access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def publish_photo(text: str, page_id: str, token: str,
                  image_path: str | None, image_url: str | None) -> str:
    data = {"caption": text, "access_token": token}
    files = None
    if image_path:
        files = {"source": open(image_path, "rb")}
    else:
        data["url"] = image_url
    resp = requests.post(
        f"{GRAPH_API_BASE}/{page_id}/photos",
        data=data,
        files=files,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a draft markdown file")
    group.add_argument("--text", help="Raw post text")
    img = parser.add_mutually_exclusive_group()
    img.add_argument("--image", help="Local image file (e.g. exported Canva poster PNG) to attach")
    img.add_argument("--image-url", help="Publicly reachable image URL to attach")
    args = parser.parse_args()

    load_dotenv()
    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        sys.exit("FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN must be set. Copy .env.example to .env "
                 "and fill it in (see scripts/README.md for how to generate the token).")

    if args.file:
        text = strip_draft_metadata(open(args.file, encoding="utf-8").read())
    else:
        text = args.text

    if args.image and not os.path.exists(args.image):
        sys.exit(f"Image file not found: {args.image}")

    print("About to post:\n---")
    print(text)
    print("---")
    if args.image:
        print(f"With image file: {args.image}")
    elif args.image_url:
        print(f"With image URL: {args.image_url}")
    if input("Publish this to the Facebook Page? [y/N] ").strip().lower() != "y":
        print("Aborted.")
        return

    if args.image or args.image_url:
        post_id = publish_photo(text, page_id, token, args.image, args.image_url)
    else:
        post_id = publish_text(text, page_id, token)
    print(f"Published. Post id: {post_id}")


if __name__ == "__main__":
    main()
