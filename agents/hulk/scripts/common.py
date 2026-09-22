#!/usr/bin/env python3
"""Shared Hulk engine: profiles, listings loading, WhatsApp links, run state.

A *profile* is one brand Hulk posts as — its persona, templates, schedule, spreadsheet and
credential names. Profiles live in ../profiles/<name>/profile.yaml. Every script takes
--profile; the default comes from HULK_PROFILE in .env, falling back to senang-homes.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
PROFILES_DIR = AGENT_DIR / "profiles"
STATE_DIR = HERE / "state"
POSTERS_DIR = HERE / "posters"

DEFAULT_PROFILE = "senang-homes"


def available_profiles() -> list[str]:
    return sorted(p.name for p in PROFILES_DIR.iterdir() if (p / "profile.yaml").exists())


def resolve_profile(name: str | None) -> str:
    profile = name or os.environ.get("HULK_PROFILE") or DEFAULT_PROFILE
    if profile not in available_profiles():
        raise SystemExit(f"Unknown profile {profile!r}. Available: {', '.join(available_profiles())}")
    return profile


def load_config(profile: str | None = None) -> dict:
    """Load one profile. Paths inside it are resolved relative to the profile directory."""
    profile = resolve_profile(profile)
    profile_dir = PROFILES_DIR / profile
    cfg = yaml.safe_load((profile_dir / "profile.yaml").read_text(encoding="utf-8"))
    cfg["_profile"] = profile
    cfg["_dir"] = profile_dir

    # Secrets / private URLs may override the file so they never land in git.
    # Scoped per profile first (SENANG_HOMES_LISTINGS_URL), then the plain name.
    prefix = profile.upper().replace("-", "_")
    for env_suffix, path in (("LISTINGS_URL", ("listings", "url")),
                             ("WHATSAPP_NUMBER", ("whatsapp", "number"))):
        value = os.environ.get(f"{prefix}_{env_suffix}") or os.environ.get(env_suffix)
        if value and path[0] in cfg:
            cfg[path[0]][path[1]] = value
    return cfg


def profile_path(cfg: dict, raw: str) -> Path:
    """Resolve a path written in a profile.yaml, relative to that profile's directory."""
    path = Path(raw)
    return path if path.is_absolute() else (cfg["_dir"] / path).resolve()


def credential(cfg: dict, key: str) -> str:
    """Read a credential this profile names, e.g. credential(cfg, "threads_access_token").

    Each profile maps a logical name to an .env variable, so two brands' tokens can never
    be mixed up by a script that forgot which account it was posting to.
    """
    var = cfg.get("credentials", {}).get(key)
    if not var:
        raise SystemExit(f"Profile {cfg['_profile']} defines no credential for {key!r}.")
    value = os.environ.get(var, "").strip()
    if not value:
        raise SystemExit(f"{var} is not set in .env (needed for {key} on profile {cfg['_profile']}).")
    return value


# --------------------------------------------------------------------------- listings

def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def _rows_from_csv_text(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def _rows_from_xlsx(path: Path) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError:  # pragma: no cover - depends on optional extra
        raise SystemExit("source: xlsx needs openpyxl — run: pip install openpyxl")
    ws = load_workbook(path, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h or "") for h in rows[0]]
    return [
        {h: ("" if v is None else str(v)) for h, v in zip(headers, r)}
        for r in rows[1:]
        if any(v is not None and str(v).strip() for v in r)
    ]


def _gsheet_csv_url(url: str) -> str:
    """Accept a normal Google Sheets share URL and turn it into a CSV export URL."""
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url)
    if not m:
        return url  # already a published-CSV or other direct link
    doc_id = m.group(1)
    gid_match = re.search(r"[#&?]gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"


def load_listings(cfg: dict) -> list[dict]:
    """Return listings as dicts keyed by the AGENT's field names (see config columns map)."""
    lc = cfg["listings"]
    source = lc["source"]

    if source == "gsheet":
        url = lc.get("url") or ""
        if not url:
            raise SystemExit("listings.source is gsheet but no listings.url (or LISTINGS_URL) is set.")
        resp = requests.get(_gsheet_csv_url(url), timeout=30)
        resp.raise_for_status()
        if "<html" in resp.text[:200].lower():
            raise SystemExit(
                "Google returned an HTML page, not CSV — the sheet isn't readable without login.\n"
                "Fix: File → Share → Anyone with the link (Viewer), or File → Share → "
                "Publish to web → CSV, and use that URL."
            )
        raw = _rows_from_csv_text(resp.text)
    elif source == "xlsx":
        raw = _rows_from_xlsx(profile_path(cfg, lc["path"]))
    elif source == "csv":
        raw = _rows_from_csv_text(profile_path(cfg, lc["path"]).read_text(encoding="utf-8-sig"))
    else:
        raise SystemExit(f"Unknown listings.source: {source!r} (use csv, xlsx or gsheet)")

    colmap = {field: _norm(header) for field, header in lc["columns"].items() if header}
    photo_overrides = load_photo_overrides(cfg)
    listings = []
    for row in raw:
        lookup = {_norm(k): (v or "").strip() for k, v in row.items() if k}
        item = {field: lookup.get(header, "") for field, header in colmap.items()}
        if not item.get("ref"):
            # No unique-id column in this sheet (common for agents whose listings are just
            # project name + unit type rows) — derive a stable one from title + size instead
            # of dropping the row. Stable across re-reads regardless of row order, as long as
            # title/size don't change.
            basis = f"{item.get('title', '')}-{item.get('size', '')}".strip("-")
            if not basis:
                continue  # nothing in the row to key off of at all
            item["ref"] = re.sub(r"[^a-z0-9]+", "-", basis.lower()).strip("-")
        if not item.get("photo_url"):
            item["photo_url"] = photo_overrides.get(item.get("title", ""), "")
        item["_raw"] = row
        listings.append(item)
    return listings


# --------------------------------------------------------------------------- area analytics

def _parse_number(text: str) -> float | None:
    """'RM729,600.00' -> 729600.0, '570' -> 570.0, '3,550 - 3,856' (a size range) -> 3703.0
    (the average — naively stripping non-digits from a range would concatenate both numbers
    into one bogus value). None if nothing numeric is in there."""
    text = text or ""
    range_match = re.match(r"\s*([\d,]+(?:\.\d+)?)\s*-\s*([\d,]+(?:\.\d+)?)\s*$", text)
    if range_match:
        lo, hi = (float(g.replace(",", "")) for g in range_match.groups())
        return (lo + hi) / 2
    digits = re.sub(r"[^\d.]", "", text)
    return float(digits) if digits else None


def price_per_sqft(listing: dict) -> float | None:
    price, size = _parse_number(listing.get("price", "")), _parse_number(listing.get("size", ""))
    return price / size if price and size else None


# Trailing tokens too generic to be a "neighborhood" on their own — e.g. "Jalan Kiara 5, Mont
# Kiara, KL" should group as "Mont Kiara", not the city-wide catch-all "KL".
_GENERIC_CITY_TOKENS = {"kl", "kuala lumpur", "kuala lumpur city"}


def _extract_area(location: str) -> str:
    parts = [p.strip() for p in location.split(",") if p.strip()]
    while parts and re.sub(r"\(.*?\)", "", parts[-1]).strip().lower() in _GENERIC_CITY_TOKENS:
        parts.pop()
    return parts[-1] if parts else location


def area_stats(cfg: dict) -> list[dict]:
    """Group active listings by area — the most specific comma-separated part of `location`
    after dropping generic trailing city tokens (see _extract_area) — and compute price/sqft
    stats per area — the data behind "which area fits your budget/lifestyle" comparison posts,
    as opposed to a single-listing post. Areas with no listing that has both a parseable price
    AND size are skipped — an average of zero real data points would just be a made-up number
    in the caption.
    """
    by_area: dict[str, list[dict]] = {}
    for item in active_listings(cfg):
        area = _extract_area(item.get("location", ""))
        if area:
            by_area.setdefault(area, []).append(item)

    stats = []
    for area, items in by_area.items():
        psf_values = [p for p in (price_per_sqft(i) for i in items) if p]
        if not psf_values:
            continue
        stats.append({
            "area": area,
            "listing_count": len(items),
            "project_count": len(set(i["title"] for i in items)),
            "avg_price_per_sqft": round(sum(psf_values) / len(psf_values)),
            "min_price_per_sqft": round(min(psf_values)),
            "max_price_per_sqft": round(max(psf_values)),
            "projects": sorted(set(i["title"] for i in items)),
        })
    return stats


def load_photo_overrides(cfg: dict) -> dict[str, str]:
    """title -> photo_url. Optional agents/hulk/profiles/<profile>/photo_overrides.csv, for
    sheets with no Image URL column of their own — one row per project, found by searching for
    the building's real photo. Missing file means no overrides, not an error."""
    path = cfg["_dir"] / "photo_overrides.csv"
    if not path.exists():
        return {}
    rows = _rows_from_csv_text(path.read_text(encoding="utf-8-sig"))
    return {
        r["title"].strip(): r["photo_url"].strip()
        for r in rows if r.get("title", "").strip() and r.get("photo_url", "").strip()
    }


def find_listing(cfg: dict, ref: str) -> dict:
    for item in load_listings(cfg):
        if item["ref"].strip().lower() == ref.strip().lower():
            return item
    raise SystemExit(f"No listing with ref {ref!r} in the sheet.")


def active_listings(cfg: dict) -> list[dict]:
    allowed = {s.strip().lower() for s in cfg["listings"]["active_statuses"]}
    out = []
    for item in load_listings(cfg):
        status = item.get("status", "").strip().lower()
        if not status or status in allowed:
            out.append(item)
    return out


# --------------------------------------------------------------------------- whatsapp

def whatsapp_link(cfg: dict, listing: dict) -> str:
    number = re.sub(r"\D", "", str(cfg["whatsapp"]["number"]))
    if not number or set(number) == {"0"}:
        raise SystemExit("Set a real whatsapp.number in config/agent.yaml (or WHATSAPP_NUMBER in .env).")
    prefill = cfg["whatsapp"]["prefill"].format(
        ref=listing.get("ref", ""), title=listing.get("title", "your listing")
    )
    return f"https://wa.me/{number}?text={urllib.parse.quote(prefill)}"


def cta_line(cfg: dict, listing: dict) -> str:
    return cfg["whatsapp"]["cta_template"].format(link=whatsapp_link(cfg, listing))


# --------------------------------------------------------------------------- state

def _state_path(cfg: dict, name: str) -> Path:
    STATE_DIR.mkdir(exist_ok=True)
    return STATE_DIR / f"{cfg['_profile']}-{name}.json"


def read_state(cfg: dict, name: str) -> dict:
    path = _state_path(cfg, name)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_state(cfg: dict, name: str, data: dict) -> None:
    _state_path(cfg, name).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(n: int) -> datetime:
    return now_utc() - timedelta(days=n)


def pick_listings(cfg: dict, count: int) -> list[dict]:
    """Choose the least-recently-posted active listings, respecting the cooldown."""
    posted = read_state(cfg, "posted").get("listings", {})
    cooldown = int(cfg["schedule"]["cooldown_days"])
    cutoff = days_ago(cooldown)

    candidates = []
    for item in active_listings(cfg):
        last = posted.get(item["ref"], {}).get("last_posted")
        last_dt = datetime.fromisoformat(last) if last else None
        if last_dt and last_dt > cutoff:
            continue  # still cooling down
        candidates.append((last_dt or datetime.min.replace(tzinfo=timezone.utc), item))

    if not candidates:
        return []
    candidates.sort(key=lambda pair: pair[0])
    return [item for _, item in candidates[:count]]


def mark_posted(cfg: dict, listing_ref: str, platform: str, post_id: str) -> None:
    state = read_state(cfg, "posted")
    listings = state.setdefault("listings", {})
    entry = listings.setdefault(listing_ref, {})
    entry["last_posted"] = now_utc().isoformat()
    entry.setdefault("posts", []).append(
        {"platform": platform, "post_id": post_id, "at": now_utc().isoformat()}
    )
    write_state(cfg, "posted", state)


def recent_posts(cfg: dict) -> list[dict]:
    """Every post the agent made inside the reply lookback window, newest first."""
    cutoff = days_ago(int(cfg["replies"]["lookback_days"]))
    out = []
    for ref, entry in read_state(cfg, "posted").get("listings", {}).items():
        for post in entry.get("posts", []):
            if datetime.fromisoformat(post["at"]) >= cutoff:
                out.append({**post, "ref": ref})
    out.sort(key=lambda p: p["at"], reverse=True)
    return out
