from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentic_events import EventEnvelope, GitTarget, Producer


def _valid_kwargs(**overrides):
    kwargs = dict(
        event_id=uuid4(),
        correlation_id="0190f7d1-2a3b-7c4d-8e5f-6a7b8c9d0e1f",
        service="agentic-sdlc-mlops",
        event_type="drift-detected",
        timestamp=datetime.now(timezone.utc),
        producer=Producer(service="agentic-sdlc-mlops", instance_id="mlops-consumer-7f9c"),
        git_target=GitTarget(
            repo_url="https://github.com/jayakumard10/url-shortener-api.git",
            branch="main",
        ),
        scenario_type="brownfield",
    )
    kwargs.update(overrides)
    return kwargs


def test_minimal_valid_envelope_defaults_tenant_and_schema_version():
    env = EventEnvelope(**_valid_kwargs())
    assert env.tenant == "default"
    assert env.schema_version == "1.0"
    assert env.metrics == {}
    assert env.payload == {}


def test_rejects_unknown_top_level_field():
    with pytest.raises(ValidationError):
        EventEnvelope(**_valid_kwargs(), unexpected_field="nope")


def test_rejects_invalid_scenario_type():
    with pytest.raises(ValidationError):
        EventEnvelope(**_valid_kwargs(scenario_type="not-a-real-scenario"))


def test_rejects_wrong_schema_version():
    with pytest.raises(ValidationError):
        EventEnvelope(**_valid_kwargs(schema_version="2.0"))


def test_git_target_allows_null_commit_sha_before_clone():
    env = EventEnvelope(**_valid_kwargs())
    assert env.git_target.commit_sha is None


def test_metrics_and_payload_accept_arbitrary_event_specific_shape():
    env = EventEnvelope(
        **_valid_kwargs(
            metrics={"p95_latency_ms": 61.8, "relative_delta_pct": 46.8},
            payload={"sample_size": 483},
        )
    )
    assert env.metrics["p95_latency_ms"] == 61.8
    assert env.payload["sample_size"] == 483


def test_producer_rejects_unknown_field():
    with pytest.raises(ValidationError):
        Producer(service="agentic-sdlc-mlops", instance_id="x", extra_field="nope")


def test_git_target_rejects_unknown_field():
    with pytest.raises(ValidationError):
        GitTarget(repo_url="https://example.com/r.git", branch="main", extra_field="nope")
