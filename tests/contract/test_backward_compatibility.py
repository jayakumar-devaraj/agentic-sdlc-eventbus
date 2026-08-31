"""The compatibility checker itself must be right before CI can rely on it.

CI runs ``scripts/check_compatibility.py`` against the schema on the target branch. That
gate is only worth having if the checker actually recognises the changes it claims to,
so these tests feed it each breaking shape directly rather than trusting it.
"""

import copy
import json

import pytest

from check_compatibility import breaking_changes
from export_schema import render

pytestmark = pytest.mark.contract


@pytest.fixture
def schema():
    return json.loads(render())


def test_a_schema_is_compatible_with_itself(schema):
    assert breaking_changes(schema, copy.deepcopy(schema)) == []


def test_adding_an_optional_field_is_allowed(schema):
    changed = copy.deepcopy(schema)
    changed["properties"]["region"] = {
        "anyOf": [{"type": "string"}, {"type": "null"}],
        "default": None,
    }
    assert breaking_changes(schema, changed) == []


def test_making_an_existing_field_required_is_breaking(schema):
    changed = copy.deepcopy(schema)
    changed["required"] = [*schema["required"], "tenant"]
    problems = breaking_changes(schema, changed)
    assert any("tenant" in p and "became required" in p for p in problems)


def test_adding_a_new_required_field_is_breaking(schema):
    changed = copy.deepcopy(schema)
    changed["properties"]["region"] = {"type": "string"}
    changed["required"] = [*schema["required"], "region"]
    assert any("added as required" in p for p in breaking_changes(schema, changed))


def test_removing_a_field_is_breaking(schema):
    changed = copy.deepcopy(schema)
    del changed["properties"]["tenant"]
    assert any("tenant" in p and "removed" in p for p in breaking_changes(schema, changed))


def test_narrowing_a_nullable_field_to_non_null_is_breaking(schema):
    # commit_sha is null before a clone happens. Forbidding null would reject a case the
    # platform produces routinely - and Pydantic spells nullable as anyOf, so the
    # checker has to see through that spelling to notice.
    changed = copy.deepcopy(schema)
    changed["$defs"]["GitTarget"]["properties"]["commit_sha"] = {"type": "string"}
    problems = breaking_changes(schema, changed)
    assert any("commit_sha" in p and "null" in p for p in problems)


def test_a_breaking_change_inside_a_nested_model_is_caught(schema):
    # Producer and GitTarget live in $defs. Walking only the root would miss them
    # entirely, which is the bug this test exists to prevent in the checker.
    changed = copy.deepcopy(schema)
    del changed["$defs"]["Producer"]["properties"]["instance_id"]
    assert any("Producer" in p and "instance_id" in p for p in breaking_changes(schema, changed))


def test_dropping_a_scenario_type_is_breaking(schema):
    changed = copy.deepcopy(schema)
    changed["properties"]["scenario_type"]["enum"] = ["greenfield", "brownfield"]
    problems = breaking_changes(schema, changed)
    assert any("scenario_type" in p and "ambiguous" in p for p in problems)


def test_adding_a_scenario_type_is_allowed(schema):
    changed = copy.deepcopy(schema)
    existing = schema["properties"]["scenario_type"]["enum"]
    changed["properties"]["scenario_type"]["enum"] = [*existing, "migration"]
    assert breaking_changes(schema, changed) == []


def test_changing_the_schema_version_const_is_breaking(schema):
    changed = copy.deepcopy(schema)
    changed["properties"]["schema_version"]["const"] = "2.0"
    assert any("schema_version" in p for p in breaking_changes(schema, changed))


def test_closing_a_previously_open_field_is_breaking(schema):
    changed = copy.deepcopy(schema)
    changed["properties"]["event_type"]["enum"] = ["drift-detected", "run-outcome"]
    assert any("closed value set" in p for p in breaking_changes(schema, changed))


def test_beginning_to_forbid_unknown_properties_is_breaking():
    old = {"type": "object", "properties": {"a": {"type": "string"}}}
    new = {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": False}
    assert any("forbids unknown properties" in p for p in breaking_changes(old, new))


def test_removing_a_whole_nested_model_is_breaking(schema):
    changed = copy.deepcopy(schema)
    del changed["$defs"]["GitTarget"]
    assert any("GitTarget" in p for p in breaking_changes(schema, changed))


def test_the_trace_fields_added_in_this_change_are_not_breaking(schema):
    # The concrete claim made when traceparent and tracestate were added: optional with
    # a None default, so nothing already in flight becomes invalid. Asserted rather than
    # assumed, by rebuilding the schema as it was before them.
    before = copy.deepcopy(schema)
    del before["properties"]["traceparent"]
    del before["properties"]["tracestate"]
    assert breaking_changes(before, schema) == []
