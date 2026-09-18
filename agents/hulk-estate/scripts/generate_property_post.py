#!/usr/bin/env python3
"""Draft a property marketing post from one listing row, using Claude + the Hulk Estate persona.

    python generate_property_post.py HE-001
    python generate_property_post.py HE-001 --framework yield_math --platform instagram

Drafts are written to drafts/ for review. This script never posts anything.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

import common

MODEL = "claude-sonnet-5"
LIMITS = {"threads": 500, "instagram": 800}

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
DRAFTS_DIR = HERE / "drafts"


def frameworks() -> list[str]:
    return sorted(p.stem for p in (AGENT_DIR / "templates").glob("*.md"))


def listing_block(listing: dict) -> str:
    labels = {
        "ref": "Reference", "title": "Title", "type": "Property type", "deal": "Sale or rent",
        "location": "Location", "price": "Price", "size": "Size (sqft)",
        "bedrooms": "Bedrooms", "bathrooms": "Bathrooms", "tenure": "Tenure",
        "monthly_instalment": "Monthly instalment", "rental_yield": "Rental yield",
        "highlight": "Highlight", "status": "Status",
    }
    lines = [f"- {label}: {listing[key]}" for key, label in labels.items() if listing.get(key)]
    return "\n".join(lines)


def build_prompt(listing: dict, framework: str | None, platform: str, cta: str) -> str:
    parts = [
        "Write one post for this property. Use ONLY the facts below — no invented details.",
        "",
        listing_block(listing),
        "",
        f"Platform: {platform}. Hard limit: {LIMITS[platform]} characters including the CTA line.",
        "",
        "End the post with this exact CTA line, unchanged, on its own line:",
        cta,
    ]
    if framework:
        template = (AGENT_DIR / "templates" / f"{framework}.md").read_text(encoding="utf-8")
        parts += ["", "Use this framework:", "", template]
    else:
        available = "\n\n".join(
            (AGENT_DIR / "templates" / f"{name}.md").read_text(encoding="utf-8") for name in frameworks()
        )
        parts += ["", "Pick whichever of these frameworks fits this property best:", "", available]
    return "\n".join(parts)


def generate(listing: dict, framework: str | None, platform: str, cfg: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")

    persona = (AGENT_DIR / "persona" / "hulk-estate-system-prompt.md").read_text(encoding="utf-8")
    cta = common.cta_line(cfg, listing)

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=persona,
        messages=[{"role": "user", "content": build_prompt(listing, framework, platform, cta)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()

    # The CTA carries the closing link — never ship a post without it.
    if cta not in text:
        text = f"{text}\n\n{cta}"
    if len(text) > LIMITS[platform]:
        raise ValueError(f"Draft is {len(text)} chars, over the {platform} limit of {LIMITS[platform]}.")
    return text


def save_draft(text: str, listing: dict, platform: str, framework: str | None) -> Path:
    DRAFTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = DRAFTS_DIR / f"{stamp}-{listing['ref']}-{platform}.md"
    path.write_text(
        f"<!-- ref: {listing['ref']} -->\n<!-- platform: {platform} -->\n"
        f"<!-- framework: {framework or 'auto'} -->\n\n{text}\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref", help="Listing reference from the sheet, e.g. HE-001")
    parser.add_argument("--framework", choices=frameworks(), default=None)
    parser.add_argument("--platform", choices=sorted(LIMITS), default="threads")
    args = parser.parse_args()

    load_dotenv(HERE / ".env")
    cfg = common.load_config()
    listing = common.find_listing(cfg, args.ref)
    text = generate(listing, args.framework, args.platform, cfg)
    path = save_draft(text, listing, args.platform, args.framework)

    print(text)
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
