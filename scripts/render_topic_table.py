"""Render the topic register into README.md, between generated markers.

The README table used to *be* the register, which meant the platform's rule about
undocumented infrastructure rested on a document nothing could parse. Now
``contracts/topics.yaml`` is the register and this renders a view of it, so the two
cannot disagree - ``--check`` fails when they have.

Usage:
    python scripts/render_topic_table.py            # rewrite the block in README.md
    python scripts/render_topic_table.py --check    # fail if the block is stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentic_events import registry as reg

README = Path(__file__).resolve().parents[1] / "README.md"
BEGIN = "<!-- BEGIN GENERATED: topic-register -->"
END = "<!-- END GENERATED: topic-register -->"


def render() -> str:
    """Render the register as a Markdown table."""
    lines = [
        BEGIN,
        "",
        f"Generated from `src/agentic_events/contracts/topics.yaml` by "
        f"`scripts/render_topic_table.py`. Convention: `{reg.convention().pattern}`.",
        "",
        "| Topic | Producer | Consumer(s) | Carries |",
        "|---|---|---|---|",
    ]
    for topic in reg.topics():
        consumers = ", ".join(f"`{c}`" for c in topic.consumers) if topic.consumers else "_none_"
        lines.append(f"| `{topic.name}` | `{topic.producer}` | {consumers} | {topic.carries} |")
    lines += ["", END]
    return "\n".join(lines)


def _split(text: str) -> tuple[str, str]:
    """Return the text before and after the generated block."""
    start = text.find(BEGIN)
    end = text.find(END)
    if start == -1 or end == -1 or end < start:
        raise SystemExit(
            f"error: README.md must contain the markers {BEGIN} and {END}, in that order."
        )
    return text[:start], text[end + len(END) :]


def main() -> int:
    """Rewrite or verify the generated topic table in README.md."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Exit non-zero if stale.")
    args = parser.parse_args()

    current = README.read_text(encoding="utf-8")
    before, after = _split(current)
    updated = before + render() + after

    if not args.check:
        README.write_text(updated, encoding="utf-8")
        print(f"rendered {len(reg.topics())} topics into README.md")
        return 0

    if current == updated:
        print("README topic table is current")
        return 0

    print(
        "error: the README topic table does not match contracts/topics.yaml.\n"
        "The register changed and its view did not. Run:\n"
        "    python scripts/render_topic_table.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
