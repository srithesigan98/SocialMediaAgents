#!/usr/bin/env python3
"""One-time helper: find your Canva brand template ID and its autofill field names.

Run with no argument to LIST your brand templates (id + title), so you can spot the
"High-Contrast Trading Strategy Poster" one and copy its id:

    python inspect_canva_template.py

Run with a template id to see its autofill dataset schema (the real field names
generate_poster() in daily_post.py needs to send data for):

    python inspect_canva_template.py BAFxxxxxxxxx

Needs CANVA_CLIENT_ID, CANVA_CLIENT_SECRET, CANVA_REFRESH_TOKEN in .env (from get_canva_token.py).
"""
import base64
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
API_BASE = "https://api.canva.com/rest/v1"


def get_access_token() -> str:
    client_id = os.environ["CANVA_CLIENT_ID"]
    client_secret = os.environ["CANVA_CLIENT_SECRET"]
    refresh_token = os.environ["CANVA_REFRESH_TOKEN"]
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"Token refresh failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


def list_templates(token: str) -> None:
    r = requests.get(f"{API_BASE}/brand-templates", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if not r.ok:
        sys.exit(f"List brand templates failed: {r.status_code} {r.text}")
    items = r.json().get("items", [])
    if not items:
        print("No brand templates found on this account.")
        return
    print(f"Found {len(items)} brand template(s):\n")
    for t in items:
        print(f"  id: {t['id']}\n  title: {t.get('title')}\n")
    print("Copy the id matching your poster template, then re-run:")
    print("  python inspect_canva_template.py <that-id>")


def show_dataset(token: str, template_id: str) -> None:
    r = requests.get(
        f"{API_BASE}/brand-templates/{template_id}/dataset",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"Get dataset failed: {r.status_code} {r.text}")
    dataset = r.json().get("dataset", {})
    if not dataset:
        print("This template has no autofill fields defined (nothing to fill in).")
        return
    print(f"Autofill fields for template {template_id}:\n")
    for field_name, field in dataset.items():
        print(f"  \"{field_name}\"  ->  type: {field.get('type')}")
    print(
        "\nUpdate generate_poster()'s autofill `data=` mapping in daily_post.py to use these "
        "exact field name(s) instead of the 'post_text' placeholder."
    )


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    token = get_access_token()
    if len(sys.argv) > 1:
        show_dataset(token, sys.argv[1])
    else:
        list_templates(token)


if __name__ == "__main__":
    main()
