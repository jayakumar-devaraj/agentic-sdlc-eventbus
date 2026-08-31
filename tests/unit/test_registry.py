"""The registry loads, meta-validates, and enforces the declarative contract specs."""

import pytest

from agentic_events import PayloadValidationError, RegistryError, UnknownTopicError
from agentic_events import registry as reg

pytestmark = pytest.mark.unit

_WINDOW = {"start": "2026-08-31T10:00:00Z", "end": "2026-08-31T11:00:00Z"}


# --- the register itself ------------------------------------------------------------


def test_every_registered_topic_satisfies_the_convention():
    convention = reg.convention()
    offenders = [t.name for t in reg.topics() if not convention.matches(t.name)]
    assert offenders == []


def test_no_registered_topic_uses_an_underscore():
    # Kafka collapses '.' and '_' to the same JMX metric name, so a register holding
    # both 'foo.bar' and 'foo_bar' would silently collide. The convention forbids '_'
    # and this asserts the register actually obeys it rather than trusting the regex.
    assert [t.name for t in reg.topics() if "_" in t.name] == []


def test_topic_names_are_unique():
    names = reg.topic_names()
    assert len(names) == len(set(names))


def test_topic_lookup_returns_the_registered_entry():
    topic = reg.topic("mlops.drift-detected.v1")
    assert topic.producer == "agentic-sdlc-mlops"
    assert "agentic-sdlc-control-plane" in topic.consumers


def test_unregistered_topic_raises_and_names_itself():
    with pytest.raises(UnknownTopicError) as caught:
        reg.topic("control-plane.not-a-real-topic.v1")
    assert caught.value.topic == "control-plane.not-a-real-topic.v1"


def test_a_topic_may_have_no_consumers():
    # An empty consumer list is a deliberate state, not a missing entry. Asserting it
    # keeps a future 'tidy-up' from deleting the audit topic for looking unused.
    assert reg.topic("control-plane.audit.v1").consumers == ()


def test_dead_letter_topic_carries_raw_messages_not_envelopes():
    assert reg.topic("control-plane.dlq.v1").carries_envelope is False
    assert reg.topic("control-plane.run-outcome.v1").carries_envelope is True


# --- listener topology (ADR 0001) ---------------------------------------------------


def test_every_caller_position_has_exactly_one_listener():
    # The bug ADR 0001 records was two caller positions sharing one advertised address.
    positions = [x.caller_position for x in reg.listeners()]
    assert len(positions) == len(set(positions))


def test_only_the_controller_is_unadvertised():
    unadvertised = [x.name for x in reg.listeners() if x.advertised is None]
    assert unadvertised == ["CONTROLLER"]


def test_advertised_addresses_are_distinct():
    # Two listeners advertising the same address is precisely the ADR 0001 defect: a
    # client bootstraps, is handed a reconnect address for someone else's position, and
    # then fails every send silently.
    advertised = [x.advertised for x in reg.listeners() if x.advertised is not None]
    assert len(advertised) == len(set(advertised))


def test_listener_lookup_and_unknown_listener():
    assert reg.listener("DOCKER_INTERNAL").caller_position == "foreign-container"
    with pytest.raises(RegistryError):
        reg.listener("NO_SUCH_LISTENER")


def test_every_listener_is_scoped_local_dev_only():
    # Every listener is unauthenticated. That is correct for a single-node broker on a
    # developer machine and is recorded as an explicit posture; this test is what makes
    # widening the scope without a superseding ADR fail loudly.
    assert {x.scope for x in reg.listeners()} == {"local-dev-only"}
    posture = reg.security_posture()
    assert (posture.authentication, posture.encryption) == ("none", "none")


def test_cluster_id_is_the_fixed_kraft_value():
    assert reg.cluster_id() == "GbUkriPcWUY1D0RM32nhAw"


# --- per-topic event body validation ------------------------------------------------


def test_valid_drift_body_passes():
    reg.validate_event(
        "mlops.drift-detected.v1",
        metrics={
            "metric_name": "p95_latency_ms",
            "reference_value": 42.1,
            "current_value": 61.8,
            "relative_delta_pct": 46.8,
            "threshold_pct": 20.0,
        },
        payload={
            "reference_window": {"start": "2026-08-31T10:00:00Z", "end": "2026-08-31T11:00:00Z"},
            "current_window": {"start": "2026-08-31T11:00:00Z", "end": "2026-08-31T12:00:00Z"},
            "sample_size": 483,
        },
    )


def test_drift_body_permits_null_baseline():
    # A baseline window with no observations has no reference value. A schema that
    # forbade null here would encode the wrong contract and reject a case the consumer
    # already renders correctly.
    reg.validate_event(
        "mlops.drift-detected.v1",
        metrics={
            "metric_name": "p95_latency_ms",
            "reference_value": None,
            "current_value": None,
            "relative_delta_pct": None,
            "threshold_pct": 20.0,
        },
        payload={
            "reference_window": {"start": "2026-08-31T10:00:00Z", "end": "2026-08-31T11:00:00Z"},
            "current_window": {"start": "2026-08-31T11:00:00Z", "end": "2026-08-31T12:00:00Z"},
            "sample_size": 0,
        },
    )


def test_drift_body_missing_the_metric_the_consumer_reads_is_rejected():
    # This is the half that matters. The control plane reads metric_name out of METRICS;
    # a schema covering only payload would have called this body valid.
    with pytest.raises(PayloadValidationError) as caught:
        reg.validate_event(
            "mlops.drift-detected.v1",
            metrics={
                "reference_value": 1.0,
                "current_value": 2.0,
                "relative_delta_pct": 100.0,
                "threshold_pct": 20.0,
            },
            payload={
                "reference_window": _WINDOW,
                "current_window": _WINDOW,
                "sample_size": 1,
            },
        )
    assert "metric_name" in str(caught.value)


def test_gate_decision_accepts_either_spelling_of_the_verdict():
    for key in ("decision", "status"):
        reg.validate_event(
            "control-plane.gate-decision.v1",
            metrics={},
            payload={key: "approve", "decided_by": "jayakumar"},
        )


def test_gate_decision_without_a_usable_verdict_is_rejected():
    with pytest.raises(PayloadValidationError):
        reg.validate_event(
            "control-plane.gate-decision.v1",
            metrics={},
            payload={"comment": "looks fine to me"},
        )


def test_gate_decision_rejects_a_verdict_outside_the_consumer_vocabulary():
    with pytest.raises(PayloadValidationError):
        reg.validate_event(
            "control-plane.gate-decision.v1", metrics={}, payload={"decision": "lgtm"}
        )


def test_telemetry_body_allows_a_null_short_code():
    reg.validate_event(
        "url-shortener.request-telemetry.v1",
        metrics={"status_code": 404, "latency_ms": 3.2, "is_404": True, "is_rate_limited": False},
        payload={"method": "GET", "path": "/nope", "code": None},
    )


def test_run_outcome_payload_stays_open_for_producer_supplied_extras():
    # The producer merges caller-supplied keys into payload by design, so that reporting
    # what a run produced does not version the envelope every repository installs.
    reg.validate_event(
        "control-plane.run-outcome.v1",
        metrics={},
        payload={
            "terminal_state": "completed",
            "detail": "",
            "published": True,
            "branch": "fix/regression",
            "anything_else": 1,
        },
    )


def test_audit_payload_must_not_be_empty():
    reg.validate_event("control-plane.audit.v1", metrics={}, payload={"node": "release_gate"})
    with pytest.raises(PayloadValidationError):
        reg.validate_event("control-plane.audit.v1", metrics={}, payload={})


def test_raw_dead_letter_message_validates_as_a_whole_message():
    reg.validate_raw_message(
        "control-plane.dlq.v1",
        {
            "source_topic": "mlops.drift-detected.v1",
            "error": "ValidationError: 3 validation errors",
            "failed_at": "2026-08-31T12:00:00Z",
            "reported_by": {"service": "agentic-sdlc-control-plane", "instance_id": "cp-1"},
            "raw_value": "{not json",
        },
    )


def test_the_two_validators_refuse_to_be_used_on_the_wrong_kind_of_topic():
    with pytest.raises(RegistryError, match="raw messages"):
        reg.validate_event("control-plane.dlq.v1", metrics={}, payload={})
    with pytest.raises(RegistryError, match="carries envelopes"):
        reg.validate_raw_message("control-plane.audit.v1", {})


def test_validating_against_an_unregistered_topic_raises_unknown_topic():
    with pytest.raises(UnknownTopicError):
        reg.validate_event("made-up.topic.v1", metrics={}, payload={})


def test_event_schema_is_retrievable_for_every_registered_topic():
    for topic in reg.topics():
        schema = reg.event_schema(topic.name)
        assert schema["$schema"].startswith("https://json-schema.org/")
