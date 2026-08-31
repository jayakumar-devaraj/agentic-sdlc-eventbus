"""Start a new spec from the templates in ``.specify/templates/``.

Stock spec-kit keeps its scripts under ``.specify/scripts/`` in both bash and PowerShell
flavours. This repository keeps one Python copy under ``scripts/`` instead: Python is
already a hard requirement here, so a Python script needs no second implementation to
stay correct on a second platform, and everything under ``scripts/`` is covered by the
same ruff and mypy gates as the package. ``.specify/`` holds the constitution and the
templates, which is the part that carries the meaning.

Usage:
    python scripts/new_spec.py "declarative contract registry"
    python scripts/new_spec.py --contract-change "add region to the envelope"
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / ".specify" / "templates"
SPECS = REPO_ROOT / "specs"


def slugify(title: str) -> str:
    """Reduce a title to a lowercase, hyphen-separated slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError("title must contain at least one alphanumeric character")
    return slug


def next_number() -> str:
    """Return the next zero-padded spec number."""
    existing = [d.name[:3] for d in SPECS.glob("[0-9][0-9][0-9]-*") if d.is_dir()]
    highest = max((int(n) for n in existing), default=0)
    return f"{highest + 1:03d}"


def main() -> int:
    """Create a spec directory seeded from the templates."""
    parser = argparse.ArgumentParser(description="Start a new spec.")
    parser.add_argument("title", help="Short human title, e.g. 'add region to the envelope'.")
    parser.add_argument(
        "--contract-change",
        action="store_true",
        help="Also seed the contract-change record. Required for any envelope, topic, "
        "or listener change.",
    )
    args = parser.parse_args()

    slug = slugify(args.title)
    directory = SPECS / f"{next_number()}-{slug}"
    if directory.exists():
        print(f"error: {directory} already exists", file=sys.stderr)
        return 1

    wanted = ["spec", "plan", "tasks"]
    if args.contract_change:
        wanted.append("contract-change")

    directory.mkdir(parents=True)
    for name in wanted:
        source = TEMPLATES / f"{name}-template.md"
        if not source.exists():
            print(f"error: missing template {source}", file=sys.stderr)
            return 1
        body = source.read_text(encoding="utf-8")
        body = body.replace("[FEATURE NAME]", args.title)
        body = body.replace("[WHAT IS CHANGING]", args.title)
        body = body.replace("NNN-short-slug", directory.name)
        body = body.replace("YYYY-MM-DD", date.today().isoformat())
        (directory / f"{name}.md").write_text(body, encoding="utf-8")

    print(f"created {directory.relative_to(REPO_ROOT)}/")
    for name in wanted:
        print(f"  {name}.md")
    print("\nWrite spec.md before plan.md, and plan.md before tasks.md.")
    print("Check both against .specify/memory/constitution.md as you go.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
