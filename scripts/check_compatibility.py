"""Detect breaking changes between two versions of the envelope's JSON Schema.

``.claude/agents/development.md`` states the rule this enforces:

    Additive by default. New fields are optional with a default. A field that becomes
    required is a breaking change and needs a new topic version, not a patch release.

Until now that rule was enforced by whoever remembered it. This package is installed by
three sibling repositories, so "whoever remembered it" is not a control - a pull request
could make ``tenant`` required and every check in this repository would stay green while
every producer in the platform started failing on upgrade.

What counts as breaking is defined from the *consumer's* position, which is the only one
that matters for a published contract:

* a property becoming required - existing producers omit it
* a property disappearing - existing consumers read it
* a type set narrowing - a value that used to be legal no longer is
* an enum losing a member, or a const changing - same reason
* a schema that used to accept unknown keys refusing them

Adding an optional property, widening a type, and adding an enum member are all fine,
and this script stays quiet about them.

Usage:
    python scripts/check_compatibility.py BASELINE.json CURRENT.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_JSON_TYPES = frozenset({"null", "boolean", "object", "array", "number", "string", "integer"})


def _type_set(schema: dict[str, Any]) -> frozenset[str]:
    """Return the JSON types a subschema accepts.

    Pydantic renders an optional field as ``anyOf: [{type: X}, {type: null}]`` rather
    than as a type list, so both spellings have to collapse to the same answer or every
    nullable field would look like a change to itself.
    """
    declared = schema.get("type")
    types: set[str] = set()
    if isinstance(declared, str):
        types.add(declared)
    elif isinstance(declared, list):
        types.update(t for t in declared if isinstance(t, str))

    for branch in schema.get("anyOf", []) or schema.get("oneOf", []):
        if isinstance(branch, dict):
            types |= _type_set(branch)

    if "const" in schema:
        types.add("string")

    return frozenset(types & _JSON_TYPES)


def _subschemas(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return every object schema in the document, keyed by a readable path.

    The root plus each ``$defs`` entry. Nested models live in ``$defs``, so walking only
    the root would miss a breaking change to Producer or GitTarget entirely.
    """
    found: dict[str, dict[str, Any]] = {"<root>": document}
    for name, schema in (document.get("$defs") or {}).items():
        if isinstance(schema, dict):
            found[name] = schema
    return found


def _enum_members(schema: dict[str, Any]) -> frozenset[Any] | None:
    """Return a property's closed value set, or ``None`` if it is not closed."""
    if "const" in schema:
        return frozenset({schema["const"]})
    if isinstance(schema.get("enum"), list):
        return frozenset(schema["enum"])
    return None


def _compare_property(where: str, name: str, old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Report breaking differences between one property's old and new schema."""
    problems: list[str] = []

    old_types, new_types = _type_set(old), _type_set(new)
    lost_types = old_types - new_types
    if old_types and new_types and lost_types:
        problems.append(
            f"{where}.{name}: no longer accepts {sorted(lost_types)}. "
            f"A value that used to be legal now fails validation."
        )

    old_members, new_members = _enum_members(old), _enum_members(new)
    if old_members is not None and new_members is not None:
        removed = old_members - new_members
        if removed:
            problems.append(
                f"{where}.{name}: dropped allowed value(s) {sorted(map(str, removed))}. "
                f"Producers still emitting them will be rejected."
            )
    elif old_members is None and new_members is not None:
        problems.append(
            f"{where}.{name}: became a closed value set. Values outside it now fail."
        )

    return problems


def breaking_changes(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Return every backward-incompatible difference from ``old`` to ``new``.

    Args:
        old: The baseline schema, usually the copy on the target branch.
        new: The schema produced by the change under review.

    Returns:
        Human-readable descriptions, empty when the change is backward compatible.
    """
    problems: list[str] = []
    old_parts, new_parts = _subschemas(old), _subschemas(new)

    for where, old_schema in old_parts.items():
        new_schema = new_parts.get(where)
        if new_schema is None:
            problems.append(
                f"{where}: the whole schema was removed. Consumers referencing it break."
            )
            continue

        old_props = old_schema.get("properties") or {}
        new_props = new_schema.get("properties") or {}
        old_required = set(old_schema.get("required") or [])
        new_required = set(new_schema.get("required") or [])

        for name in sorted(set(old_props) - set(new_props)):
            problems.append(f"{where}.{name}: removed. A consumer reading it now gets nothing.")

        for name in sorted(new_required - old_required):
            verb = "added as required" if name not in old_props else "became required"
            problems.append(
                f"{where}.{name}: {verb}. Every producer that omits it starts failing on "
                f"upgrade - that is a new schema version, not a patch."
            )

        for name in sorted(set(old_props) & set(new_props)):
            problems.extend(_compare_property(where, name, old_props[name], new_props[name]))

        if old_schema.get("additionalProperties") is not False and (
            new_schema.get("additionalProperties") is False
        ):
            problems.append(
                f"{where}: now forbids unknown properties. Producers sending extras are rejected."
            )

    return problems


def main() -> int:
    """Compare two schema files and report whether the change is backward compatible."""
    parser = argparse.ArgumentParser(description="Check envelope schema compatibility.")
    parser.add_argument("baseline", type=Path, help="Schema as it exists on the target branch.")
    parser.add_argument("current", type=Path, help="Schema produced by this change.")
    args = parser.parse_args()

    if not args.baseline.exists():
        print(f"no baseline at {args.baseline}; treating as a new contract", file=sys.stderr)
        return 0

    problems = breaking_changes(
        json.loads(args.baseline.read_text(encoding="utf-8")),
        json.loads(args.current.read_text(encoding="utf-8")),
    )
    if not problems:
        print("envelope schema change is backward compatible")
        return 0

    print("error: this change breaks the published envelope contract.\n", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    print(
        "\nThis package is installed by agentic-sdlc-control-plane, agentic-sdlc-mlops,\n"
        "and url-shortener-api. A breaking change needs a new schema version and a\n"
        "coordinated rollout, not a patch release.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
