#!/usr/bin/env python3
"""One-time helper: turn a short-lived Facebook USER token into a NON-EXPIRING Page token.

Why: a Page access token derived from a *long-lived* user token does not expire, so Blue Hulk
never needs its token refreshed again.

You need three things:
  1. App ID       — App dashboard → Settings → Basic
  2. App Secret   — same page (click "Show")
  3. A fresh short-lived USER access token from the Graph API Explorer, generated with
     pages_show_list + pages_read_engagement + pages_manage_posts, with your Page selected.
     (Use the *User* token here, NOT a Page token.)

Run it:
    python get_permanent_token.py

Secrets are typed hidden (getpass) and never printed. It prints your Page's id and a
non-expiring Page token — paste those into FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN in .env.
"""
import getpass
import os
import sys

import requests

GRAPH = "https://graph.facebook.com/v21.0"


def main() -> None:
    app_id = os.environ.get("FB_APP_ID") or input("App ID: ").strip()
    app_secret = os.environ.get("FB_APP_SECRET") or getpass.getpass("App Secret (hidden): ").strip()
    short_token = (
        os.environ.get("FB_SHORT_TOKEN")
        or getpass.getpass("Short-lived USER token (hidden): ").strip()
    )

    # 1) short-lived user token -> long-lived user token (~60 days)
    r = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"Token exchange failed: {r.status_code} {r.text}")
    long_token = r.json()["access_token"]
    print("\n✓ Long-lived user token obtained.")

    # 2) long-lived user token -> Page token (non-expiring)
    r = requests.get(f"{GRAPH}/me/accounts", params={"access_token": long_token}, timeout=30)
    if not r.ok:
        sys.exit(f"/me/accounts failed: {r.status_code} {r.text}")
    pages = r.json().get("data", [])
    if not pages:
        sys.exit(
            "No Pages returned. Re-generate the user token and make sure you tick your Page "
            "in the Facebook login dialog."
        )

    print("\nNon-expiring credentials — paste these into .env:\n")
    for p in pages:
        print(f"  # Page: {p.get('name')}")
        print(f"  FB_PAGE_ID={p.get('id')}")
        print(f"  FB_PAGE_ACCESS_TOKEN={p.get('access_token')}\n")

    print("Verify afterwards with debug_token — it should show \"type\":\"PAGE\" and no expiry.")


if __name__ == "__main__":
    main()
