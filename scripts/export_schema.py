"""Export the envelope's wire contract to a versioned JSON Schema.

The envelope existed only as Python, which meant every consumer had to be Python and
had to install this package to know the shape of a message. It also meant nothing could
diff the contract: a field could change and no artifact in the repository changed with
it.

This script is the generator, and the file it writes is the artifact downstream
repositories diff against. It is committed, and ``--check`` fails when the committed
copy has drifted from the model - so a Pydantic edit that is not reflected in the
schema cannot merge.

Usage:
    python scripts/export_schema.py            # regenerate the committed schema
    python scripts/export_schema.py --check    # fail if the committed schema is stale
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentic_events.envelope import SCHEMA_VERSION, EventEnvelope

TARGET = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "agentic_events"
    / "contracts"
    / "envelope"
    / f"v{SCHEMA_VERSION}.schema.json"
)


def render() -> str:
    """Render the envelope's JSON Schema as deterministic, diffable text.

    Sorted keys and a fixed indent, because this file's whole job is to be diffed. An
    ordering that shifted between runs would turn every regeneration into noise and
    hide the one change that mattered.
    """
    schema = EventEnvelope.model_json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = (
        "https://github.com/jayakumar-devaraj/agentic-sdlc-eventbus"
        f"/contracts/envelope/v{SCHEMA_VERSION}.schema.json"
    )
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> int:
    """Regenerate or verify the committed envelope schema."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed schema differs from the model.",
    )
    args = parser.parse_args()

    generated = render()

    if not args.check:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(generated, encoding="utf-8")
        shown = TARGET.relative_to(Path.cwd()) if TARGET.is_relative_to(Path.cwd()) else TARGET
        print(f"wrote {shown}")
        return 0

    if not TARGET.exists():
        print(f"error: {TARGET} does not exist. Run scripts/export_schema.py.", file=sys.stderr)
        return 1

    committed = TARGET.read_text(encoding="utf-8")
    if committed == generated:
        print("envelope schema is current")
        return 0

    print("error: the committed envelope schema is stale.", file=sys.stderr)
    print("The model changed and the exported contract did not. Run:", file=sys.stderr)
    print("    python scripts/export_schema.py", file=sys.stderr)
    print("", file=sys.stderr)
    sys.stderr.writelines(
        difflib.unified_diff(
            committed.splitlines(keepends=True),
            generated.splitlines(keepends=True),
            fromfile="committed",
            tofile="generated",
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
