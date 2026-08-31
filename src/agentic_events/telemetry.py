"""W3C trace-context helpers for the envelope.

The envelope crosses every service boundary in this platform and, until now, carried
nothing a tracer could join on. ``correlation_id`` was doing the job of a trace id
without any of its guarantees: it is chosen by the producer to mean "one drift
episode" or "one run", which is a *business* correlation and deliberately survives
across processes, retries, and days. A trace id is a different thing with a different
lifetime, and overloading one field to be both is how they end up disagreeing.

So the envelope carries both, and this module owns the trace half of it.

No dependency on OpenTelemetry. This package is installed by every repository in the
platform and must not force a tracing SDK on any of them. :func:`current_traceparent`
soft-imports the SDK and returns ``None`` when it is absent or no span is recording,
which is exactly what a producer without tracing should put on the wire.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

# https://www.w3.org/TR/trace-context/#traceparent-header-field-values
# version "00": <version>-<trace-id>-<parent-id>-<trace-flags>
TRACEPARENT_RE: Final = re.compile(r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")

_ALL_ZERO_TRACE_ID: Final = "0" * 32
_ALL_ZERO_SPAN_ID: Final = "0" * 16


@dataclass(frozen=True, slots=True)
class TraceContext:
    """A parsed ``traceparent``."""

    version: str
    trace_id: str
    span_id: str
    trace_flags: str

    @property
    def sampled(self) -> bool:
        """Report whether the sampled bit is set."""
        return bool(int(self.trace_flags, 16) & 0x01)


def is_valid_traceparent(value: str) -> bool:
    """Report whether ``value`` is a well-formed W3C ``traceparent``.

    All-zero trace ids and span ids are rejected. The spec defines them as invalid, and
    they are the value a broken instrumentation emits, so accepting them would let the
    exact failure this field exists to make visible pass silently.
    """
    if TRACEPARENT_RE.match(value) is None:
        return False
    _, trace_id, span_id, _ = value.split("-")
    return trace_id != _ALL_ZERO_TRACE_ID and span_id != _ALL_ZERO_SPAN_ID


def parse_traceparent(value: str) -> TraceContext:
    """Parse a ``traceparent`` into its components.

    Args:
        value: The header value to parse.

    Returns:
        The parsed context.

    Raises:
        ValueError: if ``value`` is not a well-formed ``traceparent``.
    """
    if not is_valid_traceparent(value):
        raise ValueError(f"Not a valid W3C traceparent: {value!r}")
    version, trace_id, span_id, trace_flags = value.split("-")
    return TraceContext(
        version=version, trace_id=trace_id, span_id=span_id, trace_flags=trace_flags
    )


def format_traceparent(trace_id: int, span_id: int, *, sampled: bool = True) -> str:
    """Render OpenTelemetry-style integer ids as a W3C ``traceparent``.

    Args:
        trace_id: 128-bit trace id.
        span_id: 64-bit span id.
        sampled: Whether the sampled flag should be set.

    Returns:
        A ``traceparent`` string.
    """
    return f"00-{trace_id:032x}-{span_id:016x}-{'01' if sampled else '00'}"


def current_traceparent() -> str | None:
    """Return the active span's ``traceparent``, or ``None``.

    ``None`` is a correct and expected answer, not a failure: a producer with no tracing
    SDK installed, or with no span in progress, has no trace context to propagate. The
    import is deliberately local so that importing this module never pulls in the SDK.
    """
    try:
        from opentelemetry import trace
    except ImportError:
        return None

    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return format_traceparent(
        span_context.trace_id, span_context.span_id, sampled=span_context.trace_flags.sampled
    )
