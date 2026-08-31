# Plan: declarative contract registry

**Spec:** `specs/001-declarative-contract-registry/spec.md` · **Status:** Implemented

---

## Approach

Move the three published artifacts out of prose and constants into declarative specs
that ship inside the package, and make CI, the runtime, and the compose file all read
from them.

The specs live at `src/agentic_events/contracts/` rather than at the repository root.
This is the one place the plan departs from the audit that preceded it, and the reason
is decisive: a contract artifact that is not in the wheel cannot be read by the three
repositories that install this package, which is the entire reason it exists. Root-level
`contracts/` reads better on GitHub and would not ship.

Two loaders, not one, because the bus carries two kinds of message. Most topics carry an
`EventEnvelope` and their schema constrains the open `metrics`/`payload` pair. The
dead-letter topic carries bare JSON — a message reaches it precisely by failing the
envelope contract, so wrapping the report in that contract would destroy the evidence.
A single validator would have had to pretend those are the same thing.

## Alternatives rejected

| Option | Why not |
|---|---|
| Hand-write the envelope JSON Schema | Two sources of truth that drift silently. Generating it from the model and diffing the committed copy makes drift a CI failure instead. |
| Validate only `payload` per topic | The drift contract lives in `metrics` — the consumer reads `metric_name` and the threshold out of it. This would have validated the half nobody reads. |
| Make `correlation_id` a constrained type now | Rejects envelopes all three sibling repos emit today. Correct destination, wrong first step; see below. |
| Eager spec loading at import | Import is the wrong place to raise on a malformed spec, and a consumer that never queries the registry should not pay to parse it. Lazy, with the contract tier forcing every spec eagerly in CI. |
| Confluent Schema Registry | A whole service to run for six topics on a single-node broker. The value here is a diffable artifact and a CI gate, and files plus a script deliver both. |
| Keep the README table as the register and generate the YAML from it | Backwards. Markdown is the lossy format; it should be the view. |

## Contract impact

- **Envelope schema changes:** additive. `traceparent` and `tracestate`, both optional
  with a `None` default.
- **New or changed topics:** `control-plane.dlq.v1` registered. It already existed on the
  producing side; this records it rather than creating it.
- **Listener topology changes:** none. The topology is unchanged and now declared.
- **Does `check_compatibility.py` pass against the pre-change schema?** Yes — asserted by
  `test_the_trace_fields_added_in_this_change_are_not_breaking`, which rebuilds the
  schema without the two fields and compares.

### Why the soft checks are warnings

`correlation_id` format and timezone-awareness are real contract rules, and the
correlation-id defect is exactly what they would have caught. They still ship as
`ContractWarning` plus an opt-in `validate_strict()`, because:

- Three sibling repositories emit envelopes today that predate these rules.
- A hard failure on a patch release breaks running producers with no migration window.
- Article II says a newly-required constraint is a new version, not a patch — and that
  applies to constraints, not only to fields.

Every current producer already passes both checks (all three use `datetime.now(UTC)` and
none uses `event_id` as `correlation_id`), so the migration window is expected to be
short. Flipping the default is a spec of its own, not a follow-up commit.

## Verification

| Tier | What it proves | New or changed |
|---|---|---|
| `unit/` | Schema rejects what it should; the registry loads, meta-validates, and refuses corrupt specs; trace context parses. | New: `test_registry`, `test_registry_failure_modes`, `test_telemetry`; extended `test_envelope`. |
| `contract/` | The committed schema matches the model; the compatibility checker catches each breaking shape; the compose file matches `listeners.yaml`; every spec is valid and every registered topic has a schema. | New: four modules. |
| `integration/` | A real envelope survives a real broker and re-validates, with trace context and timezone-awareness intact. | New: `test_envelope_roundtrip`. |
| `evaluation/` | Each advertised listener works from the position it serves, the host listener is genuinely unreachable from a foreign container, and the register reconciles with the live broker. | New: two modules. |

Result, run against the running broker on 2026-08-31: **128 passed, 1 skipped**, 100%
coverage over **244 statements** (Article IV — the count belongs next to the percentage).

## Files

| Path | Change |
|---|---|
| `src/agentic_events/` | Moved from repository root; `py.typed` added |
| `src/agentic_events/contracts/topics.yaml` | New — the register |
| `src/agentic_events/contracts/listeners.yaml` | New — the topology, with caller positions |
| `src/agentic_events/contracts/{topics,listeners}.schema.json` | New — meta-schemas |
| `src/agentic_events/contracts/schemas/*.schema.json` | New — six per-topic event schemas |
| `src/agentic_events/contracts/envelope/v1.0.schema.json` | New — generated, committed |
| `src/agentic_events/registry.py` | New — loader and validators |
| `src/agentic_events/errors.py` | New — repo-owned exception boundary |
| `src/agentic_events/telemetry.py` | New — W3C trace context, no SDK dependency |
| `src/agentic_events/envelope.py` | Trace fields; `contract_violations`; `validate_strict` |
| `scripts/{export_schema,check_compatibility,new_spec}.py` | New |
| `tests/{unit,contract,integration,evaluation}/` | New four-tier structure |
| `pyproject.toml` | src layout, package data, ruff, mypy, markers |

## Risks

| Risk | How it becomes visible |
|---|---|
| The per-topic schemas were derived by reading producers, so they encode current behaviour and could be wrong about intent. | They are `additionalProperties: true` wherever the producer merges caller-supplied keys, so they under-constrain rather than falsely reject. A wrong schema surfaces as a `PayloadValidationError` in a consumer, not as silent acceptance. |
| Warnings fire on every envelope construction in a hot path. | Python's default filter shows each unique warning once per call site. Every current producer already passes both checks, so in practice none fire. |
| `src/` move changes how the package resolves for the three repos that install it. | The import path is unchanged; only the source tree moved. Verified by installing the built distribution and running the suite against it. |
| The evaluation tier depends on Docker and on network shape. | It skips cleanly with no Docker, and the workflow that owns it starts a broker first and treats a skip as a failure. |

## Documentation moving with this change

- [x] README — regenerated topic table, new sections for the registry and tiers
- [x] ADR `docs/adr/0002` — contracts are declarative and ship inside the package
- [x] ADR `docs/adr/0003` — the envelope carries W3C trace context
- [x] ADR `docs/adr/0004` — src layout so tests exercise the built artifact
- [x] `.specify/memory/constitution.md` — ratified
- [x] `.claude/agents/*.md` — updated to point at the specs rather than the README table
