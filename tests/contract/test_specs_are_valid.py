"""Every shipped contract spec loads and satisfies its meta-schema.

The registry loads lazily, which is right for a library - a consumer that never touches
the registry should not pay to parse it, and import time is the wrong place to raise on
a malformed spec. The cost of that choice is that a corrupt spec would otherwise surface
at some unlucky caller's first use rather than in CI. This module is what pays it back:
it forces every spec eagerly, so a bad one fails here instead of in another repository.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_events import registry as reg

pytestmark = pytest.mark.contract

CONTRACTS = Path(__file__).resolve().parents[2] / "src" / "agentic_events" / "contracts"


def test_topics_spec_loads_and_meta_validates():
    assert len(reg.topics()) >= 1
    assert reg.convention().pattern


def test_listeners_spec_loads_and_meta_validates():
    assert len(reg.listeners()) >= 1
    assert reg.cluster_id()
    assert reg.security_posture().rationale


@pytest.mark.parametrize("topic", reg.topics(), ids=lambda t: t.name)
def test_every_registered_topic_has_a_schema_file_that_is_itself_valid(topic):
    # A register entry pointing at a schema that does not exist, or that is not a legal
    # JSON Schema, is worse than no entry: it looks like coverage and provides none.
    schema = reg.event_schema(topic.name)
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("topic", reg.topics(), ids=lambda t: t.name)
def test_every_registered_topic_names_its_schema_after_itself(topic):
    assert topic.event_schema == f"schemas/{topic.name}.schema.json"


def test_no_orphaned_schema_files():
    # A schema file nobody registers is dead weight that reads as live contract.
    on_disk = {p.name for p in (CONTRACTS / "schemas").glob("*.schema.json")}
    registered = {f"{t.name}.schema.json" for t in reg.topics()}
    assert on_disk == registered


@pytest.mark.parametrize("topic", reg.topics(), ids=lambda t: t.name)
def test_envelope_topics_constrain_both_open_fields(topic):
    # The lesson from the drift topic: its contract lives in metrics, not payload. A
    # schema that only described payload would leave the half consumers actually read
    # unvalidated, and would look complete while doing it.
    if not topic.carries_envelope:
        pytest.skip("raw topics describe the whole message, not the metrics/payload pair")
    properties = reg.event_schema(topic.name)["properties"]
    assert set(properties) == {"metrics", "payload"}


def test_the_dead_letter_topic_is_the_only_raw_one():
    raw = [t.name for t in reg.topics() if not t.carries_envelope]
    assert raw == ["control-plane.dlq.v1"]


def test_every_schema_file_is_valid_json_and_declares_its_dialect():
    for path in sorted((CONTRACTS / "schemas").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema", path.name
        assert document.get("title"), path.name
        assert document.get("description"), path.name
