#!/usr/bin/env python3
"""Generate a Blue Hulk Facebook post draft using Claude, grounded in the persona, playbook,
copywriting engine, and topic guard.

Usage:
    python generate_draft.py "recovering after a losing streak"
    python generate_draft.py "quiet market week" --framework market_condition_read
    python generate_draft.py "EPF vs trading account" --framework malaysian_post

Drafts are written to scripts/drafts/ as timestamped markdown files for human review —
this script never posts anything on its own.
"""
import argparse
import datetime
import os
import sys
from pathlib import Path

import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
DRAFTS_DIR = HERE / "drafts"

MODEL = "claude-sonnet-5"


def load_context() -> str:
    persona = (AGENT_DIR / "persona" / "blue-hulk-system-prompt.md").read_text()
    playbook = (AGENT_DIR / "playbook" / "content-playbook.md").read_text()
    engine = (AGENT_DIR / "playbook" / "copywriting-engine.md").read_text()
    topics = yaml.safe_load((AGENT_DIR / "config" / "topics.yaml").read_text())
    topics_block = (
        "Allowed topics:\n- "
        + "\n- ".join(topics["allowed_topics"])
        + "\n\nDenied topics (never write about these):\n- "
        + "\n- ".join(topics["denied_topics"])
    )
    return f"{persona}\n\n---\n\n{playbook}\n\n---\n\n{engine}\n\n---\n\n{topics_block}"


def list_frameworks() -> list[str]:
    return sorted(p.stem for p in (AGENT_DIR / "templates").glob("*.md"))


def generate(topic: str, framework: str | None) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")

    client = Anthropic(api_key=api_key)
    system_prompt = load_context()

    instruction = f'Write one Facebook post about: "{topic}"'
    if framework:
        template_path = AGENT_DIR / "templates" / f"{framework}.md"
        if not template_path.exists():
            sys.exit(f"Unknown framework '{framework}'. Options: {', '.join(list_frameworks())}")
        instruction += f"\n\nUse this framework/template:\n\n{template_path.read_text()}"
    else:
        instruction += "\n\nPick whichever framework from the playbook best fits this topic."
    instruction += (
        "\n\nFollow the persona's output format (framework + emotion line, post text, optional"
        " poster treatment, verify note) and run the copywriting engine's pre-publish checklist"
        " before finalizing."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": instruction}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", help="The topic or angle for this post")
    parser.add_argument(
        "--framework",
        choices=list_frameworks(),
        default=None,
        help="Force a specific framework/template (default: let Blue Hulk choose)",
    )
    args = parser.parse_args()

    load_dotenv(HERE / ".env")
    draft = generate(args.topic, args.framework)

    DRAFTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = DRAFTS_DIR / f"{stamp}.md"
    out_path.write_text(
        f"<!-- topic: {args.topic} -->\n<!-- framework: {args.framework or 'auto'} -->\n\n{draft}\n"
    )

    print(draft)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
