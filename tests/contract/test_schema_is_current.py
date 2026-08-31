"""The committed envelope schema must be what the model produces.

The exported schema is the artifact downstream repositories diff against. If the model
can change without it changing, it is decoration rather than a contract - which is the
state this repository was in before it existed.
"""

import json

import pytest

from agentic_events.envelope import SCHEMA_VERSION
from export_schema import TARGET, render

pytestmark = pytest.mark.contract


def test_committed_schema_matches_the_model():
    assert TARGET.exists(), "run: python scripts/export_schema.py"
    assert TARGET.read_text(encoding="utf-8") == render(), (
        "The envelope model changed and the exported contract did not. "
        "Run: python scripts/export_schema.py"
    )


def test_schema_is_deterministic_so_diffs_mean_something():
    # An ordering that shifted between runs would make every regeneration look like a
    # change and hide the one that mattered.
    assert render() == render()


def test_schema_declares_its_version_and_identity():
    schema = json.loads(render())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert f"v{SCHEMA_VERSION}.schema.json" in schema["$id"]


def test_schema_still_forbids_unknown_top_level_fields():
    # extra="forbid" is what stops a producer inventing a field the platform then
    # quietly depends on. Losing it would not fail any other test here.
    assert json.loads(render())["additionalProperties"] is False


def test_the_open_fields_are_still_open():
    # metrics and payload accept arbitrary event-specific shapes on purpose: this
    # package must not learn what any tenant's metrics mean. A test that pinned their
    # contents would encode exactly the coupling the design forbids.
    properties = json.loads(render())["properties"]
    for field in ("metrics", "payload"):
        assert properties[field]["type"] == "object"
        assert "properties" not in properties[field]
