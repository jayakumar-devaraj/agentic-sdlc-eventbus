import warnings
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentic_events import ContractError, ContractWarning, EventEnvelope, GitTarget, Producer
from agentic_events.envelope import contract_violations, validate_strict


def _valid_kwargs(**overrides):
    kwargs = dict(
        event_id=uuid4(),
        correlation_id="0190f7d1-2a3b-7c4d-8e5f-6a7b8c9d0e1f",
        service="agentic-sdlc-mlops",
        event_type="drift-detected",
        timestamp=datetime.now(UTC),
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


# --- trace context -------------------------------------------------------------------

VALID_TRACEPARENT = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


def test_trace_fields_default_to_none_so_existing_producers_stay_valid():
    # The whole point of adding these as optional: three sibling repositories already
    # emit envelopes without them, and a newly-required field would break their
    # producers on upgrade.
    env = EventEnvelope(**_valid_kwargs())
    assert env.traceparent is None
    assert env.tracestate is None


def test_a_valid_traceparent_is_carried():
    env = EventEnvelope(**_valid_kwargs(traceparent=VALID_TRACEPARENT, tracestate="vendor=x"))
    assert env.traceparent == VALID_TRACEPARENT
    assert env.tracestate == "vendor=x"


def test_a_malformed_traceparent_is_rejected_outright():
    # Hard error, not a warning: the field is new, so there is no fleet to migrate, and
    # a malformed trace id is never an intended value.
    with pytest.raises(ValidationError, match="valid W3C trace context"):
        EventEnvelope(**_valid_kwargs(traceparent="00-tooshort-01"))


def test_correlation_id_and_traceparent_are_different_identifiers():
    # correlation_id survives across processes and days by design; a trace id does not.
    # Overloading one field to be both is how they end up disagreeing.
    env = EventEnvelope(**_valid_kwargs(traceparent=VALID_TRACEPARENT))
    assert env.correlation_id != env.traceparent


# --- what the schema cannot enforce --------------------------------------------------


def test_a_clean_envelope_reports_no_violations_and_warns_about_nothing():
    with warnings.catch_warnings():
        warnings.simplefilter("error", ContractWarning)
        env = EventEnvelope(**_valid_kwargs())
    assert contract_violations(env) == []
    validate_strict(env)


def test_using_the_message_id_as_the_episode_id_is_flagged():
    # The defect class this whole layer exists for: event_id is per message,
    # correlation_id is per episode. Conflating them makes every redelivery look like a
    # new episode, and the schema cannot see the difference because both are strings.
    event_id = uuid4()
    with pytest.warns(ContractWarning, match="different lifetimes"):
        env = EventEnvelope(**_valid_kwargs(event_id=event_id, correlation_id=str(event_id)))
    with pytest.raises(ContractError, match="correlation_id equals event_id"):
        validate_strict(env)


def test_an_empty_correlation_id_is_flagged():
    with pytest.warns(ContractWarning, match="empty or whitespace"):
        env = EventEnvelope(**_valid_kwargs(correlation_id="   "))
    assert len(contract_violations(env)) == 1


def test_a_naive_timestamp_is_flagged():
    with pytest.warns(ContractWarning, match="naive"):
        env = EventEnvelope(**_valid_kwargs(timestamp=datetime(2026, 8, 31, 12, 0, 0)))
    with pytest.raises(ContractError, match="naive"):
        validate_strict(env)


def test_violations_are_reported_together_not_one_at_a_time():
    event_id = uuid4()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ContractWarning)
        env = EventEnvelope(
            **_valid_kwargs(
                event_id=event_id,
                correlation_id=str(event_id),
                timestamp=datetime(2026, 8, 31, 12, 0, 0),
            )
        )
    assert len(contract_violations(env)) == 2
    with pytest.raises(ContractError) as caught:
        validate_strict(env)
    assert str(caught.value).count("  - ") == 2


def test_violations_warn_rather_than_reject_by_default():
    # Deliberate, and the reason is a migration window: making these hard failures on a
    # patch release would break producers that are running right now. Strictness is
    # opt-in until the fleet is clean.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ContractWarning)
        env = EventEnvelope(**_valid_kwargs(correlation_id=""))
    assert isinstance(env, EventEnvelope)
