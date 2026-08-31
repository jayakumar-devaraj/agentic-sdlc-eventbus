"""W3C trace-context parsing, formatting, and the deliberate absence of a tracing SDK."""

import pytest

from agentic_events import telemetry

pytestmark = pytest.mark.unit

VALID = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


def test_a_well_formed_traceparent_parses_into_its_parts():
    ctx = telemetry.parse_traceparent(VALID)
    assert ctx.version == "00"
    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.span_id == "00f067aa0ba902b7"
    assert ctx.sampled is True


def test_the_sampled_bit_is_read_not_assumed():
    assert telemetry.parse_traceparent(VALID[:-2] + "00").sampled is False


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-a-traceparent",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7",  # missing flags
        "00-4bf92f3577b34da6a3ce929d0e0e473-00f067aa0ba902b7-01",  # trace id too short
        "00-4BF92F3577B34DA6A3CE929D0E0E4736-00f067aa0ba902b7-01",  # uppercase
        "00-00000000000000000000000000000000-00f067aa0ba902b7-01",  # all-zero trace id
        "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01",  # all-zero span id
    ],
)
def test_malformed_traceparents_are_rejected(value):
    assert telemetry.is_valid_traceparent(value) is False
    with pytest.raises(ValueError, match="valid W3C traceparent"):
        telemetry.parse_traceparent(value)


def test_all_zero_ids_are_rejected_even_though_they_match_the_shape():
    # The spec calls these invalid, and they are what broken instrumentation emits.
    # Accepting them would let exactly the failure this field exists to expose pass.
    assert telemetry.is_valid_traceparent("00-" + "0" * 32 + "-" + "0" * 16 + "-01") is False


def test_formatting_round_trips_through_parsing():
    rendered = telemetry.format_traceparent(0x4BF92F3577B34DA6A3CE929D0E0E4736, 0xF067AA0BA902B7)
    assert telemetry.parse_traceparent(rendered).trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert rendered.endswith("-01")
    assert telemetry.format_traceparent(1, 2, sampled=False).endswith("-00")


def test_short_ids_are_zero_padded_to_the_required_width():
    assert telemetry.format_traceparent(1, 1) == "00-" + "0" * 31 + "1-" + "0" * 15 + "1-01"


def test_no_tracing_sdk_means_no_trace_context_not_an_error(monkeypatch):
    # A producer with no tracing installed has no trace context to propagate, and None
    # is the correct thing to put on the wire. This package must never force a tracing
    # SDK on the repositories that install it.
    monkeypatch.setitem(__import__("sys").modules, "opentelemetry", None)
    assert telemetry.current_traceparent() is None


def test_an_active_recording_span_is_rendered_as_a_traceparent(monkeypatch):
    # Stands in for the OpenTelemetry SDK so the extraction path is actually exercised.
    # The SDK is not a dependency of this package and must not become one, so the only
    # way to reach this branch is to supply the shape it expects.
    sys = __import__("sys")
    types = __import__("types")

    fake_flags = type("Flags", (), {"sampled": True})()
    fake_ctx = type(
        "Ctx", (), {"is_valid": True, "trace_id": 0x1F, "span_id": 0x2A, "trace_flags": fake_flags}
    )()
    fake_span = type("Span", (), {"get_span_context": lambda self: fake_ctx})()

    module = types.ModuleType("opentelemetry")
    module.trace = types.SimpleNamespace(get_current_span=lambda: fake_span)
    monkeypatch.setitem(sys.modules, "opentelemetry", module)
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", module.trace)

    assert telemetry.current_traceparent() == "00-" + "0" * 30 + "1f-" + "0" * 14 + "2a-01"


def test_a_span_context_that_is_not_valid_yields_no_traceparent(monkeypatch):
    sys = __import__("sys")
    types = __import__("types")

    fake_ctx = type("Ctx", (), {"is_valid": False})()
    fake_span = type("Span", (), {"get_span_context": lambda self: fake_ctx})()
    module = types.ModuleType("opentelemetry")
    module.trace = types.SimpleNamespace(get_current_span=lambda: fake_span)
    monkeypatch.setitem(sys.modules, "opentelemetry", module)
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", module.trace)

    assert telemetry.current_traceparent() is None
