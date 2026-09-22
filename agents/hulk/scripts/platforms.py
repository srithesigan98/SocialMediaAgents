#!/usr/bin/env python3
"""Thin wrappers over the Threads and Instagram Graph APIs: publish, read comments, reply.

Every call takes the profile config and reads that profile's credentials through
common.credential(), so a script can never post one brand's content with another
brand's token. Which .env variables a profile uses is declared in its profile.yaml:

  Threads   scopes: threads_basic, threads_content_publish, threads_manage_replies
  Instagram scopes: instagram_business_basic, instagram_business_content_publish,
                    instagram_business_manage_comments, instagram_business_manage_messages
"""
from __future__ import annotations

import time

import requests

import common

THREADS_BASE = "https://graph.threads.net/v1.0"
IG_BASE = "https://graph.instagram.com/v23.0"

PUBLISH_DELAY_SECONDS = 5  # both APIs want a beat between container creation and publish


def _threads(cfg: dict) -> tuple[str, str]:
    return common.credential(cfg, "threads_user_id"), common.credential(cfg, "threads_access_token")


def _ig(cfg: dict) -> tuple[str, str]:
    return common.credential(cfg, "ig_user_id"), common.credential(cfg, "ig_access_token")


def _check(resp: requests.Response) -> dict:
    if not resp.ok:
        raise RuntimeError(f"{resp.request.method} {resp.url.split('?')[0]} -> {resp.status_code}: {resp.text}")
    return resp.json()


# --------------------------------------------------------------------------- Threads

def threads_publish(cfg: dict, text: str, image_url: str | None = None) -> str:
    user_id, token = _threads(cfg)
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


def threads_publish_carousel(cfg: dict, text: str, image_urls: list[str]) -> str:
    """Multi-image carousel post — 2-10 images, per Meta's carousel container flow: each image
    is created as its own item first (is_carousel_item=true), then combined into one CAROUSEL
    container carrying the caption, then published like any other post."""
    if not 2 <= len(image_urls) <= 10:
        raise ValueError(f"Threads carousels need 2-10 images, got {len(image_urls)}")
    user_id, token = _threads(cfg)

    item_ids = []
    for url in image_urls:
        item_ids.append(_check(requests.post(
            f"{THREADS_BASE}/{user_id}/threads",
            params={"media_type": "IMAGE", "image_url": url, "is_carousel_item": "true",
                    "access_token": token},
            timeout=30,
        ))["id"])

    carousel_id = _check(requests.post(
        f"{THREADS_BASE}/{user_id}/threads",
        params={"media_type": "CAROUSEL", "children": ",".join(item_ids), "text": text,
                "access_token": token},
        timeout=30,
    ))["id"]
    time.sleep(PUBLISH_DELAY_SECONDS)
    return _check(requests.post(
        f"{THREADS_BASE}/{user_id}/threads_publish",
        params={"creation_id": carousel_id, "access_token": token}, timeout=30,
    ))["id"]


def threads_replies(cfg: dict, media_id: str) -> list[dict]:
    """Top-level replies on one of our posts. Needs threads_manage_replies."""
    _, token = _threads(cfg)
    data = _check(requests.get(
        f"{THREADS_BASE}/{media_id}/replies",
        params={"fields": "id,text,username,timestamp,hide_status", "access_token": token},
        timeout=30,
    ))
    return data.get("data", [])


def threads_reply(cfg: dict, reply_to_id: str, text: str) -> str:
    """Public reply under a comment. Threads has no public DM API — this is the closest thing."""
    user_id, token = _threads(cfg)
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


def threads_me(cfg: dict) -> dict:
    _, token = _threads(cfg)
    return _check(requests.get(f"{THREADS_BASE}/me",
                               params={"fields": "id,username", "access_token": token}, timeout=30))


# --------------------------------------------------------------------------- Instagram

def instagram_publish(cfg: dict, caption: str, image_url: str) -> str:
    """Instagram requires media — a caption alone cannot be published."""
    user_id, token = _ig(cfg)
    creation_id = _check(requests.post(
        f"{IG_BASE}/{user_id}/media",
        params={"caption": caption, "image_url": image_url, "access_token": token}, timeout=60,
    ))["id"]
    time.sleep(PUBLISH_DELAY_SECONDS)
    return _check(requests.post(
        f"{IG_BASE}/{user_id}/media_publish",
        params={"creation_id": creation_id, "access_token": token}, timeout=60,
    ))["id"]


def instagram_publish_carousel(cfg: dict, caption: str, image_urls: list[str]) -> str:
    """Multi-image carousel post — 2-10 images. Same container-then-publish flow as
    instagram_publish, except each image is created as a captionless carousel item first."""
    if not 2 <= len(image_urls) <= 10:
        raise ValueError(f"Instagram carousels need 2-10 images, got {len(image_urls)}")
    user_id, token = _ig(cfg)

    item_ids = []
    for url in image_urls:
        item_ids.append(_check(requests.post(
            f"{IG_BASE}/{user_id}/media",
            params={"image_url": url, "is_carousel_item": "true", "access_token": token},
            timeout=60,
        ))["id"])

    carousel_id = _check(requests.post(
        f"{IG_BASE}/{user_id}/media",
        params={"media_type": "CAROUSEL", "children": ",".join(item_ids), "caption": caption,
                "access_token": token},
        timeout=60,
    ))["id"]
    time.sleep(PUBLISH_DELAY_SECONDS)
    return _check(requests.post(
        f"{IG_BASE}/{user_id}/media_publish",
        params={"creation_id": carousel_id, "access_token": token}, timeout=60,
    ))["id"]


def instagram_comments(cfg: dict, media_id: str) -> list[dict]:
    _, token = _ig(cfg)
    data = _check(requests.get(
        f"{IG_BASE}/{media_id}/comments",
        params={"fields": "id,text,username,timestamp,from", "access_token": token}, timeout=30,
    ))
    return data.get("data", [])


def instagram_reply(cfg: dict, comment_id: str, text: str) -> str:
    """Public reply under the comment."""
    _, token = _ig(cfg)
    return _check(requests.post(
        f"{IG_BASE}/{comment_id}/replies",
        params={"message": text, "access_token": token}, timeout=30,
    ))["id"]


def instagram_private_reply(cfg: dict, comment_id: str, text: str) -> str:
    """Send a DM to the commenter — the ManyChat-style move.

    Meta allows exactly one private reply per comment, within 7 days of the comment.
    """
    user_id, token = _ig(cfg)
    return _check(requests.post(
        f"{IG_BASE}/{user_id}/messages",
        json={"recipient": {"comment_id": comment_id}, "message": {"text": text}},
        params={"access_token": token}, timeout=30,
    )).get("message_id", "sent")


def instagram_me(cfg: dict) -> dict:
    _, token = _ig(cfg)
    return _check(requests.get(f"{IG_BASE}/me",
                               params={"fields": "id,username", "access_token": token}, timeout=30))
