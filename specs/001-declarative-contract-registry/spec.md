# Spec: declarative contract registry

**Spec ID:** `001-declarative-contract-registry` · **Status:** Implemented
**Created:** 2026-08-31

> Written after the audit that produced it and alongside the implementation, not
> reconstructed afterwards to look like process. `.specify/` and this spec arrived in
> the same change as the work; commits `b1bc08e`..`ca3a3f9` are the record of the order
> things actually happened in. Specs 002 onward start before their implementation.

---

## Problem

Three things this repository publishes were enforced by human discipline alone.

1. **The envelope existed only as Python.** No JSON Schema on disk, no golden file. A
   field could change and no artifact in the repository changed with it, so there was
   nothing for a downstream repository to diff and nothing for CI to compare.

2. **The topic register was a Markdown table in `README.md`.** `.claude/agents/design.md`
   names that table as the register, so the platform's rule about undocumented
   infrastructure rested on a document nothing could parse, validate, or reconcile
   against a broker.

3. **The listener topology was hand-written environment variables in a compose file**,
   with the reasoning in a comment. ADR 0001 records what that costs: a listener
   advertised an address the caller could not reach, so clients bootstrapped
   successfully and then failed every subsequent produce and fetch, silently.

`development.md` already stated the rule that a field becoming required is a breaking
change. Nothing enforced it. A pull request could make `tenant` required and every check
in this repository would stay green while every producer in the platform broke on
upgrade.

## Evidence

The register had already drifted, and it took reading the producers to find out:

```
$ grep -rn "TOPIC = \|_TOPIC = " agentic-sdlc-control-plane/agentic_control_plane/events.py
26:GATE_DECISION_TOPIC = "control-plane.gate-decision.v1"
27:AUDIT_TOPIC = "control-plane.audit.v1"
28:DLQ_TOPIC = "control-plane.dlq.v1"      <-- in no register anywhere
```

`control-plane.dlq.v1` has been produced to since the control plane grew a dead-letter
path. It appears in no register. Finding it required opening another repository's
source, which is not a control that scales.

The second piece of evidence is where the drift contract actually lives:

```
$ grep -n "metrics.get\|payload.get" agentic-sdlc-control-plane/agentic_control_plane/consumer.py
153:    metric_name = metrics.get("metric_name", "an operational metric")
154:    reference = metrics.get("reference_value")
157:    threshold = metrics.get("threshold_pct")
```

The consumer reads the load-bearing half out of `metrics`, not `payload`. Any schema
covering only `payload` would have looked complete and validated the half nobody
depends on.

## Who is affected

| Repository | How |
|---|---|
| `agentic-sdlc-control-plane` | Installs the package. Produces to four topics, consumes two. Owns the unregistered dead-letter topic. |
| `agentic-sdlc-mlops` | Installs the package. Produces drift, consumes run outcomes. |
| `url-shortener-api` | Installs the package. Produces telemetry. |
| This repository | Owns all three artifacts and enforced none of them. |

## Outcome

- [x] The envelope's wire contract exists as a committed, versioned JSON Schema, and CI
      fails when the model moves and the artifact does not.
- [x] A breaking change to that schema fails CI, judged from the consumer's position.
- [x] The topic register is machine-readable, meta-validated, and queryable at runtime by
      any consumer.
- [x] Every registered topic has an event schema covering both open envelope fields.
- [x] The listener topology is declared, and the compose file is asserted against it.
- [x] Each advertised listener is verified from the caller position it claims to serve.
- [x] The register is reconciled against a live broker in both directions.
- [x] `control-plane.dlq.v1` is registered, correctly marked as carrying raw JSON.

## Explicitly out of scope

- **Extracting agent state machines, routing, prompts, or tool schemas into specs.** This
  repository contains none of those: no graph, no node, no LLM call, no prompt. That work
  belongs to `agentic-sdlc-control-plane` and `agentic-sdlc-cobol-modernizer`, which do.
- **Making `correlation_id` format-constrained or timestamps required-aware.** Both would
  reject envelopes three sibling repositories emit today. They ship as warnings plus an
  opt-in strict mode; see `plan.md`.
- **Authentication or TLS on the broker.** Every listener is `local-dev-only` and the
  spec records that as an explicit posture. Changing it needs its own spec and ADR.
- **Retiring `KAFKA_AUTO_CREATE_TOPICS_ENABLE`.** It is deliberate. Reconciliation is
  the answer to what it costs, not removal.

## Constitutional check

| Article | Bearing on this change | Satisfied? |
|---|---|---|
| I — contract, not application | Schemas describe event shapes; none describes a tenant's internals. Topics name services, as permitted. | Yes |
| II — no local-only change | Every envelope change here is additive; verified by `check_compatibility.py` against the pre-change schema. | Yes |
| III — the seam, not the suite | The evaluation tier exercises all three advertised listeners from their own positions, including the negative case. | Yes |
| IV — say what a number does not prove | Coverage is 100% over 244 statements and the count is reported with it. | Yes |
| VII — the register is the register | Register is machine-readable and reconciled against the live broker. | Yes |
| X — declared, not scattered | Topics, listeners, and the envelope schema all moved out of prose and constants. | Yes |

## Open questions

| Question | Who answers | Status |
|---|---|---|
| When do the soft contract checks become hard? | Platform owner, once all three repos emit clean envelopes | Open — needs a spec of its own |
| Should `control-plane.dlq.v1` have a consumer, or stay human-drained? | `agentic-sdlc-control-plane` | Open — registered with an empty consumer list, deliberately |
| Does the mermaid diagram check justify an unpinned `npm install` on every CI run? | This repository | Answered in 002 |
