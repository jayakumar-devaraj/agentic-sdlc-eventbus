# Envelope contract changelog

Every change to `v1.0.schema.json`, which is the artifact
`agentic-sdlc-control-plane`, `agentic-sdlc-mlops`, and `url-shortener-api` diff against.

The schema file itself is **generated** by `scripts/export_schema.py` and carries no
history of its own — a diff shows what changed but never why, or whether a consumer had
to do anything about it. That is what this file is for.

`scripts/check_compatibility.py` decides whether a change is breaking, from the
consumer's position. Its verdict goes in the **Compatibility** column, and it is a
command that was run, never a judgement made by reading the diff.

| Date | Schema | Change | Compatibility | Consumer action |
|---|---|---|---|---|
| 2026-08-31 | 1.0 | `traceparent` and `tracestate` added, optional with a `None` default. The envelope crosses every service boundary and could not carry a trace; `correlation_id` was doing a trace id's job without its guarantees. See ADR 0003. | **Compatible** — verified against `origin/main`'s envelope | None. Optionally set `traceparent` from an existing span via `agentic_events.telemetry.current_traceparent()`. |
| 2026-08-31 | 1.0 | `metrics` and `payload` now carry an explicit `"additionalProperties": true`. Not an authored change — pydantic 2.13.5 emits it where 2.10.4 emitted nothing. | **Compatible** — JSON Schema already defaults `additionalProperties` to `true`, so this makes an implicit default explicit | None. Nothing on the wire changes. |

## What has deliberately not changed

Recorded because a reader should be able to tell the difference between "not yet" and
"decided against".

- **`correlation_id` is still an unconstrained `str`.** It should not be — the
  correlation-id defect survived two green suites precisely because the envelope
  guaranteed a type and said nothing about meaning. It stays unconstrained because all
  three sibling repositories emit envelopes that predate the rule, and a newly-required
  constraint is a new schema version rather than a patch. `contract_violations()` warns;
  `validate_strict()` is the opt-in hard check. See ADR 0004.
- **`timestamp` still accepts a naive datetime.** Same reason, same mechanism.
- **`metrics` and `payload` are still open.** This one is permanent. The envelope must
  not learn what any tenant's metrics mean. Per-topic shapes are registered separately
  under `contracts/schemas/` and checked through `registry.validate_event()`.

## Adding an entry

A row here is required for any change to the envelope model. The
`.specify/templates/contract-change-template.md` record for the change carries the
detail; this table carries the summary a downstream maintainer needs to decide whether
their repository has to do anything.

A schema version bump — `v1.0` to `v1.1` or `v2.0` — gets its own file
(`v1.1.schema.json`) rather than replacing this one, because a consumer pinned to the
old version needs the old artifact to keep existing.
