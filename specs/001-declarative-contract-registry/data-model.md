# Data model: the contract registry

**Spec:** `specs/001-declarative-contract-registry/spec.md`

What the registry holds, what each field is *for*, and where each is enforced. Every
entity below is a frozen dataclass in `agentic_events.registry`, hydrated from a spec
file and meta-validated on load.

---

## Overview

```
topics.yaml ──────────► Convention          (the naming rule, and the regex enforcing it)
                └─────► Topic × 6           (name, producer, consumers, carries, event_schema)
                                │
                                └── event_schema ──► schemas/<topic>.schema.json
                                                     (the shape of the envelope's OPEN fields)

listeners.yaml ───────► Listener × 4        (name, caller_position, bind, advertised, scope)
                └─────► SecurityPosture     (authentication, encryption, and why)
                └─────► cluster_id

envelope.py ──────────► EventEnvelope ──generated──► envelope/v1.0.schema.json
                                                     (the wire contract consumers diff)
```

Two layers that never merge, deliberately. The **envelope** is one shape for every
message and validates structure only. The **registry** describes what varies per topic,
including the parts the envelope leaves open. Collapsing them would make this package
learn what a tenant's metrics mean, which Article I forbids.

---

## `Convention`

The topic naming rule, held as data rather than as a docstring.

| Field | Type | Notes |
|---|---|---|
| `pattern` | `str` | Human form: `{service}.{event-type}.v{n}` |
| `regex` | `str` | Machine form. `matches()` is what tests and reconciliation call |
| `notes` | `str \| None` | Why there is no tenant segment; why the convention locks once a producer ships |

Separator is `.`; words inside a segment join with `-`; **never `_`**. Kafka collapses
`.` and `_` to the same JMX metric name, so `foo.bar` and `foo_bar` would silently share
metrics. Confirmed during broker testing, not inferred.

## `Topic`

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Must satisfy `Convention.regex` |
| `producer` | `str` | Exactly one. A topic with two producers is two topics or a design error |
| `consumers` | `tuple[str, ...]` | **May be empty** — a deliberate "no consumer today" state, not a missing entry |
| `carries` | `"envelope" \| "raw"` | See below |
| `event_schema` | `str` | Path to the registered schema, relative to `contracts/` |
| `summary` | `str` | What the event means. May *name* a tenant service; may not describe its internals |

### `carries` — the distinction that is easy to miss

`envelope` (5 topics): the message is an `EventEnvelope`, and the registered schema
constrains the open `metrics`/`payload` pair.

`raw` (1 topic, `control-plane.dlq.v1`): the message is a bare JSON object, and the
schema constrains the whole of it. A message reaches the dead-letter topic **because it
failed the envelope contract** — wrapping the report in that same contract would destroy
the evidence the report exists to preserve.

Enforced by `validate_event()` and `validate_raw_message()`, each of which refuses the
wrong kind of topic rather than guessing.

## `Listener`

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Matches the compose `KAFKA_LISTENERS` entry |
| `caller_position` | enum | **The load-bearing field.** `internal-network`, `intra-cluster`, `host-machine`, `foreign-container` |
| `bind` | `str` | Where the broker listens |
| `advertised` | `str \| None` | Where a client is told to *reconnect*. `None` only for the controller |
| `security_protocol` | enum | `PLAINTEXT` today, for all four |
| `scope` | `local-dev-only \| non-local` | All four are `local-dev-only`; widening needs SASL/TLS and an ADR |
| `serves` | `str` | Which caller this exists for, in prose |

`caller_position` is a **closed set on purpose**. A new value means a caller position was
discovered that ADR 0001 did not anticipate, which is a design event, not a config edit.

`advertised` is the field ADR 0001 is about. `bind` says where the broker listens;
`advertised` says where a client is told to come back to. A client handed an unreachable
reconnect address bootstraps successfully and then fails every send, silently.

## `SecurityPosture`

| Field | Type |
|---|---|
| `authentication` | `none \| sasl` |
| `encryption` | `none \| tls` |
| `rationale` | `str` |
| `non_local_requirement` | `str` |

`none`/`none` is correct for a single-node broker on a developer machine. It is recorded
as an **explicit posture** rather than left as an unstated default, so that widening it
is a visible decision. `tests/unit/test_registry.py` fails if any listener's `scope`
moves off `local-dev-only`.

---

## Where each rule is enforced

Deliberately layered — a rule enforced in only one place is a rule with one point of
failure.

| Rule | Enforced by |
|---|---|
| Spec files are well-formed | `topics.schema.json`, `listeners.schema.json` — checked on load, and eagerly in `tests/contract/` |
| Topic names satisfy the convention | `Convention.matches()`, asserted over the register and over the **live broker** |
| Every registered topic has a real schema file | `tests/contract/test_specs_are_valid.py`, including no orphaned files |
| Envelope topics constrain both open fields | Same module — a schema describing only `payload` looks complete and validates the half nobody reads |
| Compose matches the declared topology | `tests/contract/test_compose_matches_listener_spec.py` |
| Each listener works from its own position | `tests/evaluation/test_caller_positions.py` — including the negative case |
| No undeclared topic exists on the broker | `tests/evaluation/test_register_reconciles_with_broker.py` |
| The exported wire contract matches the model | `scripts/export_schema.py --check` |
| A change does not break a consumer | `scripts/check_compatibility.py`, in `contract-compat.yml` |

## What the model deliberately does not hold

- **Per-topic partition counts, retention, or compaction.** Auto-created topics inherit
  cluster defaults. Encoding per-topic settings here would imply this repository
  provisions them, and it does not.
- **Consumer group names or offsets.** Runtime state belonging to each consumer.
- **What any `event_type` means to its consumer.** Article I. The register says a topic
  exists, who produces it, and what shape its body takes — never what a consumer should
  do about it.
