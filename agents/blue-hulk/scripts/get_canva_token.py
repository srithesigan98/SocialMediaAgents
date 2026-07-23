#!/usr/bin/env python3
"""One-time helper: run Canva's OAuth 2.0 + PKCE flow and print a refresh token.

Why a refresh token, not an access token: Canva access tokens expire in ~4 hours, which is
useless for a daily unattended job. The REFRESH token is what daily_post.py's generate_poster()
actually stores and uses — it exchanges it for a fresh access token on every run.

You need first (from the Canva Developer Portal -> Your integration -> Credentials/Scopes):
  1. Client ID
  2. Client Secret
  3. A registered redirect URI matching REDIRECT_URI below (http://127.0.0.1:8888/callback)
  4. These scopes enabled: design:content:read design:content:write brandtemplate:content:read
     brandtemplate:meta:read
     (design:meta:read and asset:read/write are NOT requested — generate_poster() never calls
     an /v1/assets or design-meta endpoint, and requesting scopes your integration hasn't
     enabled causes Canva to reject the whole request with invalid_scope.)

Run it:
    python get_canva_token.py

It opens your browser for a one-time Canva login/approve, catches the redirect locally on
port 8888, exchanges the code for tokens, and prints them. Nothing is posted anywhere by this
script — it only performs authentication.
"""
import base64
import getpass
import hashlib
import http.server
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import load_dotenv

AUTH_URL = "https://www.canva.com/api/oauth/authorize"
TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "design:content:read design:content:write brandtemplate:content:read brandtemplate:meta:read"

_received_code: dict[str, str] = {}


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in qs:
            _received_code["code"] = qs["code"][0]
            body = b"<html><body>Authorized. You can close this tab and return to the terminal.</body></html>"
        else:
            body = b"<html><body>No code received. Check the terminal for details.</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:  # silence default request logging
        pass


def make_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    client_id = (os.environ.get("CANVA_CLIENT_ID") or input("Canva Client ID: ")).strip()
    client_secret = (
        os.environ.get("CANVA_CLIENT_SECRET") or getpass.getpass("Canva Client Secret (hidden): ")
    ).strip()

    print(f"[canva] Using Client ID: {client_id}  (length {len(client_id)})")
    print("[canva] Compare that EXACTLY against the Client ID on your integration's Credentials page.\n")

    verifier, challenge = make_pkce_pair()
    authorize_url = AUTH_URL + "?" + urllib.parse.urlencode(
        {
            "code_challenge": challenge,
            "code_challenge_method": "s256",
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
        }
    )

    server = http.server.HTTPServer(("127.0.0.1", 8888), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("\nOpening your browser to log in and approve the integration...")
    print(f"If it doesn't open automatically, visit:\n{authorize_url}\n")
    webbrowser.open(authorize_url)

    thread.join(timeout=180)
    server.server_close()

    code = _received_code.get("code")
    if not code:
        sys.exit("Timed out waiting for the Canva redirect. Re-run and approve within 3 minutes.")

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code_verifier": verifier,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"Token exchange failed: {r.status_code} {r.text}")

    tokens = r.json()
    print("\n=== Success. Store these — the refresh token is the one that matters long-term ===\n")
    print(f"CANVA_CLIENT_ID={client_id}")
    print(f"CANVA_CLIENT_SECRET={client_secret}")
    print(f"CANVA_ACCESS_TOKEN={tokens.get('access_token')}   # expires in ~{tokens.get('expires_in')}s, informational only")
    print(f"CANVA_REFRESH_TOKEN={tokens.get('refresh_token')}")
    print(
        "\nPut CANVA_CLIENT_ID, CANVA_CLIENT_SECRET, and CANVA_REFRESH_TOKEN into .env and into "
        "the GitHub repository secrets. Do NOT store the access token anywhere — it's short-lived "
        "and daily_post.py derives a fresh one from the refresh token on every run."
    )


if __name__ == "__main__":
    main()
