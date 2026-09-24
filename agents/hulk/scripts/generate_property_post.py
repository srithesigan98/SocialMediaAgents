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

# Windows consoles default to cp1252; make emoji/curly-quote output (e.g. the WhatsApp CTA) safe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL = "claude-sonnet-5"
LIMITS = {"threads": 500, "instagram": 800}

HERE = common.HERE
DRAFTS_DIR = HERE / "drafts"


def templates_dir(cfg: dict) -> Path:
    return common.profile_path(cfg, cfg.get("templates_dir", "templates"))


def frameworks(cfg: dict) -> list[str]:
    return sorted(p.stem for p in templates_dir(cfg).glob("*.md"))


def listing_block(listing: dict) -> str:
    labels = {
        "ref": "Reference", "title": "Title", "type": "Property type", "deal": "Sale or rent",
        "location": "Location", "price": "Price", "size": "Size (sqft)",
        "bedrooms": "Bedrooms", "bathrooms": "Bathrooms", "unit_type": "Unit type",
        "tenure": "Tenure", "developer": "Developer",
        "completion_status": "Completion status", "expected_vp": "Expected vacant possession",
        "monthly_instalment": "Monthly instalment", "loan_amount": "Loan amount (90%)",
        "monthly_rental_estimate": "Estimated monthly rental", "rental_yield": "Rental yield",
        "legal_fees_freebies": "Legal fees / freebies", "highlight": "Highlight",
        "status": "Status",
    }
    lines = [f"- {label}: {listing[key]}" for key, label in labels.items() if listing.get(key)]
    return "\n".join(lines)


def build_prompt(cfg: dict, listing: dict, framework: str | None, platform: str, cta: str) -> str:
    parts = [
        "Write one post for this property. Use ONLY the facts below — no invented details.",
        "",
        listing_block(listing),
        "",
        f"Platform: {platform}. Hard limit: {LIMITS[platform]} characters, of which the last "
        f"{len(cta)} are reserved for a closing WhatsApp CTA that gets appended automatically "
        f"after your text — so budget for at most {LIMITS[platform] - len(cta) - 2} characters.",
        "",
        "Do NOT write a WhatsApp link, phone number, or any closing call-to-action yourself — "
        "just end after your last content sentence.",
    ]
    if framework:
        template = (templates_dir(cfg) / f"{framework}.md").read_text(encoding="utf-8")
        parts += ["", "Use this framework:", "", template]
    else:
        available = "\n\n".join(
            (templates_dir(cfg) / f"{name}.md").read_text(encoding="utf-8") for name in frameworks(cfg)
        )
        parts += ["", "Pick whichever of these frameworks fits this property best:", "", available]
    return "\n".join(parts)


def generate(listing: dict, framework: str | None, platform: str, cfg: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")

    persona = common.profile_path(cfg, cfg["persona"]).read_text(encoding="utf-8")
    cta = common.cta_line(cfg, listing)

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=persona,
        messages=[{"role": "user", "content": build_prompt(cfg, listing, framework, platform, cta)}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if len(text) < 100:
        # A rare model failure mode: most of the answer lands in a discarded thinking block
        # instead of the text block, leaving almost nothing real here. Publishing this would
        # ship a caption that's just the CTA with no property content.
        raise ValueError(f"Draft came back too short ({len(text)} chars) — treating as a bad response.")

    # Always appended in code, never left to the model — asking it to reproduce the CTA
    # "unchanged" was unreliable: it would sometimes write its own close paraphrase of the
    # link instead, which didn't string-match and produced a duplicated CTA in the final post.
    text = f"{text}\n\n{cta}"
    if len(text) > LIMITS[platform]:
        raise ValueError(f"Draft is {len(text)} chars, over the {platform} limit of {LIMITS[platform]}.")
    return text


def save_draft(cfg: dict, text: str, listing: dict, platform: str, framework: str | None) -> Path:
    DRAFTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = DRAFTS_DIR / f"{stamp}-{cfg['_profile']}-{listing['ref']}-{platform}.md"
    path.write_text(
        f"<!-- profile: {cfg['_profile']} -->\n<!-- ref: {listing['ref']} -->\n<!-- platform: {platform} -->\n"
        f"<!-- framework: {framework or 'auto'} -->\n\n{text}\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref", help="Listing reference from the sheet, e.g. HE-001")
    parser.add_argument("--profile", default=None, help="Hulk profile (default: HULK_PROFILE or senang-homes)")
    parser.add_argument("--framework", default=None)
    parser.add_argument("--platform", choices=sorted(LIMITS), default="threads")
    args = parser.parse_args()

    load_dotenv(HERE / ".env")
    cfg = common.load_config(args.profile)
    if args.framework and args.framework not in frameworks(cfg):
        sys.exit(f"Unknown framework. Options: {', '.join(frameworks(cfg))}")
    listing = common.find_listing(cfg, args.ref)
    text = generate(listing, args.framework, args.platform, cfg)
    path = save_draft(cfg, text, listing, args.platform, args.framework)

    print(text)
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    main()
