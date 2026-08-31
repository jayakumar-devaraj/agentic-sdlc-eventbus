# 0003: The envelope carries W3C trace context, alongside `correlation_id`

Date: 2026-08-31
Status: Accepted

## Context

The envelope crosses every service boundary in this platform. The platform runs an
OpenTelemetry and Langfuse stack. The envelope carried nothing a tracer could join on.

In practice `correlation_id` was doing a trace id's job, and it is not one. It is a
*business* identifier chosen by the producer to mean "one drift episode" or "one governed
run", and it deliberately survives across processes, retries, and days —
`agentic-sdlc-mlops` derives it from a one-hour episode window precisely so two detections
of the same unresolved condition do not become two runs. A trace id has a different
lifetime and different guarantees. One field cannot be both without the two meanings
eventually disagreeing, which is the same failure mode that produced the correlation-id
defect in the first place.

A second question: this package is installed by every repository in the platform. Adding
a tracing SDK as a dependency would force it on all of them.

## Decision

Add `traceparent` and `tracestate` to the envelope, optional with a `None` default.

`agentic_events.telemetry` owns the W3C format — parsing, rendering, and validation —
with **no dependency on OpenTelemetry**. `current_traceparent()` soft-imports the SDK and
returns `None` when it is absent or no span is recording, which is exactly what a producer
without tracing should put on the wire.

A malformed `traceparent` is a hard validation error rather than a warning. The field is
new, so nothing on the wire carries it yet and there is no fleet to migrate; a malformed
trace id is never the intended value, only a broken one. All-zero trace and span ids are
rejected too — the spec calls them invalid, and they are what broken instrumentation
emits, so accepting them would let the exact failure the field exists to expose pass
silently.

## Consequences

- A trace survives the broker hop. Previously the platform lost it there, which is the
  one place a distributed trace most needs to hold.
- The change is additive and verified as such: `check_compatibility.py` run against
  `origin/main`'s envelope reports it backward compatible, and a contract test rebuilds
  the schema without the two fields to assert the same thing on every future run.
- Three identifiers now travel together with three different lifetimes — `event_id` per
  message, `correlation_id` per episode, `traceparent` per request path. That is more to
  explain, and it is the point: they were previously conflated because there was only
  somewhere for two of them to go.
- No new runtime dependency. A consumer that wants trace propagation installs a tracing
  SDK itself; one that does not, does not.
- `tracestate` is carried verbatim and never interpreted. It is vendor-specific, and this
  package has no business understanding it.
