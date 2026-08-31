"""An envelope survives a real broker, and comes back validating.

Before this existed, the contract and the transport were tested separately and never
together. The unit tier proved the model rejects what it should; the CI compose job
proved a topic could be auto-created. Nothing put an actual envelope on an actual wire
and read it back, so serialisation, key encoding, and the registry's per-topic schema
were all unverified against the thing they exist to survive.

Published to a topic of this test's own, never to a registered one. Writing test
traffic onto mlops.drift-detected.v1 would put fabricated drift in front of a real
consumer.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest

from agentic_events import EventEnvelope, GitTarget, Producer
from agentic_events import registry as reg
from agentic_events.envelope import validate_strict
from agentic_events.telemetry import format_traceparent

pytestmark = pytest.mark.integration

TEST_TOPIC = "eventbus.test-roundtrip.v1"


def _envelope(**overrides: object) -> EventEnvelope:
    kwargs: dict[str, object] = {
        "event_id": uuid.uuid4(),
        "correlation_id": f"drift-test-{uuid.uuid4().hex[:12]}",
        "service": "agentic-sdlc-mlops",
        "event_type": "drift-detected",
        "timestamp": datetime.now(UTC),
        "producer": Producer(service="agentic-sdlc-mlops", instance_id="roundtrip-test"),
        "git_target": GitTarget(repo_url="https://example.invalid/r.git", branch="main"),
        "scenario_type": "brownfield",
        "metrics": {
            "metric_name": "p95_latency_ms",
            "reference_value": 42.1,
            "current_value": 61.8,
            "relative_delta_pct": 46.8,
            "threshold_pct": 20.0,
        },
        "payload": {
            "reference_window": {"start": "2026-08-31T10:00:00Z", "end": "2026-08-31T11:00:00Z"},
            "current_window": {"start": "2026-08-31T11:00:00Z", "end": "2026-08-31T12:00:00Z"},
            "sample_size": 483,
        },
    }
    kwargs.update(overrides)
    return EventEnvelope(**kwargs)  # type: ignore[arg-type]


def _publish_and_read_back(producer, consumer_factory, envelope: EventEnvelope) -> str:
    """Publish one envelope and return the raw value read back off the broker."""
    consumer = consumer_factory(f"roundtrip-{uuid.uuid4().hex[:8]}")
    consumer.subscribe([TEST_TOPIC])
    # Join the group before publishing. Subscribing after the send would race the
    # earliest-offset reset and read nothing on a topic that already has history.
    consumer.poll(timeout=5.0)

    producer.produce(TEST_TOPIC, key=envelope.correlation_id, value=envelope.model_dump_json())
    remaining = producer.flush(timeout=15.0)
    assert remaining == 0, f"{remaining} message(s) never left the producer queue"

    deadline_polls = 30
    for _ in range(deadline_polls):
        message = consumer.poll(timeout=1.0)
        if message is None:
            continue
        assert message.error() is None, message.error()
        if message.key() == envelope.correlation_id.encode():
            return message.value().decode("utf-8")
    pytest.fail(f"published envelope never came back off {TEST_TOPIC}")


def test_an_envelope_survives_the_wire_unchanged(producer, consumer_factory, broker_metadata):
    sent = _envelope()
    raw = _publish_and_read_back(producer, consumer_factory, sent)

    received = EventEnvelope.model_validate_json(raw)
    assert received == sent, "the envelope that came back is not the one that went out"


def test_the_returned_envelope_still_satisfies_its_registered_schema(
    producer, consumer_factory, broker_metadata
):
    # The half that was never checked end to end: the registry's per-topic schema
    # applied to a body that has actually been serialised, transported, and reparsed.
    sent = _envelope()
    received = EventEnvelope.model_validate_json(
        _publish_and_read_back(producer, consumer_factory, sent)
    )
    reg.validate_event(
        "mlops.drift-detected.v1", metrics=received.metrics, payload=received.payload
    )
    validate_strict(received)


def test_trace_context_survives_the_wire(producer, consumer_factory, broker_metadata):
    # The reason the field was added: a trace has to be joinable on the other side of
    # the broker, which is exactly where the platform previously lost it.
    traceparent = format_traceparent(uuid.uuid4().int >> 4, uuid.uuid4().int >> 64)
    sent = _envelope(traceparent=traceparent, tracestate="vendor=eventbus")
    received = EventEnvelope.model_validate_json(
        _publish_and_read_back(producer, consumer_factory, sent)
    )
    assert received.traceparent == traceparent
    assert received.tracestate == "vendor=eventbus"


def test_timestamps_come_back_timezone_aware(producer, consumer_factory, broker_metadata):
    # Serialisation is where an aware datetime quietly becomes naive, and a naive one
    # misorders against every other producer's events. Asserted after a real round trip
    # rather than on a model built in memory.
    received = EventEnvelope.model_validate_json(
        _publish_and_read_back(producer, consumer_factory, _envelope())
    )
    assert received.timestamp.tzinfo is not None
    assert received.timestamp.utcoffset() is not None


def test_a_malformed_message_is_rejected_by_the_contract_not_silently_accepted(
    producer, consumer_factory, broker_metadata
):
    # The broker will carry anything. Being the thing that refuses it is the envelope's
    # job, and this proves the refusal happens on a real message off a real topic.
    consumer = consumer_factory(f"roundtrip-bad-{uuid.uuid4().hex[:8]}")
    consumer.subscribe([TEST_TOPIC])
    consumer.poll(timeout=5.0)

    key = f"malformed-{uuid.uuid4().hex[:8]}"
    producer.produce(TEST_TOPIC, key=key, value=json.dumps({"not": "an envelope"}))
    assert producer.flush(timeout=15.0) == 0

    for _ in range(30):
        message = consumer.poll(timeout=1.0)
        if message is None or message.key() != key.encode():
            continue
        with pytest.raises(Exception, match="validation error"):
            EventEnvelope.model_validate_json(message.value().decode("utf-8"))
        return
    pytest.fail("the malformed message never came back")
