"""What the registry does when a contract spec is corrupt, missing, or malformed.

These reach past the public API on purpose. Every path here is an error boundary whose
whole job is to convert an unreadable spec into one clear exception, and the only way
to exercise them is to hand the loader a spec that is actually broken. Untested
defensive code is a claim, not a guarantee - and this package is installed by three
other repositories, so a silently-degrading registry would fail in their process, not
in this repository's tests.
"""

import pytest

from agentic_events import RegistryError
from agentic_events import registry as reg

pytestmark = pytest.mark.unit


def test_missing_contract_file_names_the_file_it_could_not_find():
    with pytest.raises(RegistryError, match=r"no-such-file\.yaml"):
        reg._read_text("no-such-file.yaml")


def test_unparseable_yaml_is_reported_as_such(monkeypatch):
    monkeypatch.setattr(reg, "_read_text", lambda *_: "key: [unclosed")
    with pytest.raises(RegistryError, match="not parseable YAML"):
        reg._load_yaml("topics.yaml")


def test_yaml_that_is_not_a_mapping_is_rejected(monkeypatch):
    # A spec file that parses but is a list, not a mapping, would otherwise fail much
    # later with an opaque TypeError somewhere inside a comprehension.
    monkeypatch.setattr(reg, "_read_text", lambda *_: "- one\n- two\n")
    with pytest.raises(RegistryError, match="must contain a mapping"):
        reg._load_yaml("topics.yaml")


def test_unparseable_json_is_reported_as_such(monkeypatch):
    monkeypatch.setattr(reg, "_read_text", lambda *_: "{not json")
    with pytest.raises(RegistryError, match="not parseable JSON"):
        reg._load_json("topics.schema.json")


def test_json_that_is_not_an_object_is_rejected(monkeypatch):
    monkeypatch.setattr(reg, "_read_text", lambda *_: "[1, 2, 3]")
    with pytest.raises(RegistryError, match="must contain an object"):
        reg._load_json("topics.schema.json")


def test_a_spec_that_fails_its_meta_schema_reports_where_and_why():
    # The meta-schema is what stops a hand-edited register from loading in a shape the
    # rest of the module then assumes. The error has to say which field, because a
    # register with six topics gives no other clue.
    with pytest.raises(RegistryError) as caught:
        reg._validated(
            {"schema_version": "1.0", "convention": {"pattern": "x", "regex": "x"}, "topics": []},
            "topics.schema.json",
            "topics.yaml",
        )
    message = str(caught.value)
    assert "topics.yaml does not satisfy topics.schema.json" in message
    assert "topics" in message


def test_meta_schema_rejects_a_topic_missing_its_carries_field():
    incomplete = {
        "schema_version": "1.0",
        "convention": {"pattern": "x", "regex": "x"},
        "topics": [
            {
                "name": "a.b.v1",
                "producer": "p",
                "consumers": [],
                "event_schema": "schemas/a.b.v1.schema.json",
                "summary": "s",
            }
        ],
    }
    with pytest.raises(RegistryError, match="carries"):
        reg._validated(incomplete, "topics.schema.json", "topics.yaml")
