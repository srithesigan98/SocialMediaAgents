#!/usr/bin/env python3
"""Thin wrappers over the Threads and Instagram Graph APIs: publish, read comments, reply.

Credentials come from .env:
  THREADS_USER_ID / THREADS_ACCESS_TOKEN  (scopes: threads_basic, threads_content_publish,
                                           threads_manage_replies)
  IG_USER_ID / IG_ACCESS_TOKEN            (scopes: instagram_business_basic,
                                           instagram_business_content_publish,
                                           instagram_business_manage_comments,
                                           instagram_business_manage_messages)
"""
from __future__ import annotations

import os
import time

import requests

THREADS_BASE = "https://graph.threads.net/v1.0"
IG_BASE = "https://graph.instagram.com/v23.0"

PUBLISH_DELAY_SECONDS = 5  # both APIs want a beat between container creation and publish


class MissingCredentials(RuntimeError):
    pass


def _creds(*names: str) -> tuple[str, ...]:
    values = [os.environ.get(n, "").strip() for n in names]
    missing = [n for n, v in zip(names, values) if not v]
    if missing:
        raise MissingCredentials(f"Missing in .env: {', '.join(missing)}")
    return tuple(values)


def _check(resp: requests.Response) -> dict:
    if not resp.ok:
        raise RuntimeError(f"{resp.request.method} {resp.url.split('?')[0]} -> {resp.status_code}: {resp.text}")
    return resp.json()


# --------------------------------------------------------------------------- Threads

def threads_publish(text: str, image_url: str | None = None) -> str:
    user_id, token = _creds("THREADS_USER_ID", "THREADS_ACCESS_TOKEN")
    params = {"text": text, "access_token": token,
              "media_type": "IMAGE" if image_url else "TEXT"}
    if image_url:
        params["image_url"] = image_url

    creation_id = _check(requests.post(f"{THREADS_BASE}/{user_id}/threads", params=params, timeout=30))["id"]
    time.sleep(PUBLISH_DELAY_SECONDS)
    return _check(requests.post(
        f"{THREADS_BASE}/{user_id}/threads_publish",
        params={"creation_id": creation_id, "access_token": token}, timeout=30,
    ))["id"]


def threads_replies(media_id: str) -> list[dict]:
    """Top-level replies on one of our posts. Needs threads_manage_replies."""
    _, token = _creds("THREADS_USER_ID", "THREADS_ACCESS_TOKEN")
    data = _check(requests.get(
        f"{THREADS_BASE}/{media_id}/replies",
        params={"fields": "id,text,username,timestamp,hide_status", "access_token": token},
        timeout=30,
    ))
    return data.get("data", [])


def threads_reply(reply_to_id: str, text: str) -> str:
    """Public reply under a comment. Threads has no public DM API — this is the closest thing."""
    user_id, token = _creds("THREADS_USER_ID", "THREADS_ACCESS_TOKEN")
    creation_id = _check(requests.post(
        f"{THREADS_BASE}/{user_id}/threads",
        params={"text": text, "media_type": "TEXT", "reply_to_id": reply_to_id, "access_token": token},
        timeout=30,
    ))["id"]
    time.sleep(PUBLISH_DELAY_SECONDS)
    return _check(requests.post(
        f"{THREADS_BASE}/{user_id}/threads_publish",
        params={"creation_id": creation_id, "access_token": token}, timeout=30,
    ))["id"]


def threads_me() -> dict:
    _, token = _creds("THREADS_USER_ID", "THREADS_ACCESS_TOKEN")
    return _check(requests.get(f"{THREADS_BASE}/me",
                               params={"fields": "id,username", "access_token": token}, timeout=30))


# --------------------------------------------------------------------------- Instagram

def instagram_publish(caption: str, image_url: str) -> str:
    """Instagram requires media — a caption alone cannot be published."""
    user_id, token = _creds("IG_USER_ID", "IG_ACCESS_TOKEN")
    creation_id = _check(requests.post(
        f"{IG_BASE}/{user_id}/media",
        params={"caption": caption, "image_url": image_url, "access_token": token}, timeout=60,
    ))["id"]
    time.sleep(PUBLISH_DELAY_SECONDS)
    return _check(requests.post(
        f"{IG_BASE}/{user_id}/media_publish",
        params={"creation_id": creation_id, "access_token": token}, timeout=60,
    ))["id"]


def instagram_comments(media_id: str) -> list[dict]:
    _, token = _creds("IG_USER_ID", "IG_ACCESS_TOKEN")
    data = _check(requests.get(
        f"{IG_BASE}/{media_id}/comments",
        params={"fields": "id,text,username,timestamp,from", "access_token": token}, timeout=30,
    ))
    return data.get("data", [])


def instagram_reply(comment_id: str, text: str) -> str:
    """Public reply under the comment."""
    _, token = _creds("IG_USER_ID", "IG_ACCESS_TOKEN")
    return _check(requests.post(
        f"{IG_BASE}/{comment_id}/replies",
        params={"message": text, "access_token": token}, timeout=30,
    ))["id"]


def instagram_private_reply(comment_id: str, text: str) -> str:
    """Send a DM to the commenter — the ManyChat-style move.

    Meta allows exactly one private reply per comment, within 7 days of the comment.
    """
    user_id, token = _creds("IG_USER_ID", "IG_ACCESS_TOKEN")
    return _check(requests.post(
        f"{IG_BASE}/{user_id}/messages",
        json={"recipient": {"comment_id": comment_id}, "message": {"text": text}},
        params={"access_token": token}, timeout=30,
    )).get("message_id", "sent")


def instagram_me() -> dict:
    _, token = _creds("IG_USER_ID", "IG_ACCESS_TOKEN")
    return _check(requests.get(f"{IG_BASE}/me",
                               params={"fields": "id,username", "access_token": token}, timeout=30))
