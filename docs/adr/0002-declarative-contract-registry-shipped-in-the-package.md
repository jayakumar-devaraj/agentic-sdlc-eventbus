# 0002: The contract registry is declarative, and ships inside the package

Date: 2026-08-31
Status: Accepted

## Context

Three things this repository publishes were enforced by human discipline alone.

The **topic register** was a Markdown table in `README.md`. `.claude/agents/design.md`
names that table as the register, so the rule "a topic on a broker but not in the table
is undocumented infrastructure" rested on a document nothing could parse or reconcile.
It had already drifted: `control-plane.dlq.v1` has been produced to since the control
plane grew a dead-letter path and appeared in no register anywhere. Finding it required
reading another repository's source, which is not a control that scales.

The **listener topology** was environment variables in `docker-compose.yml` with the
reasoning in a comment — the same comment ADR 0001 exists because of.

The **envelope** existed only as Python. No JSON Schema on disk, so nothing downstream
could diff the contract and nothing in CI could notice it had moved.

A second question came with the first: where do the declarative files live? The obvious
answer is a `contracts/` directory at the repository root, which reads well on GitHub.

## Decision

Topics, listener topology, per-topic event schemas, and the generated envelope schema
are declarative files, meta-validated against their own JSON Schemas and read at runtime
through `agentic_events.registry`.

They live at **`src/agentic_events/contracts/`**, inside the package, declared as package
data — not at the repository root. A contract artifact that is not in the wheel cannot be
read by the three repositories that install this package, which is the entire reason it
exists. Browsing convenience lost to shipping correctness.

The register distinguishes what a topic `carries`. Most carry an `EventEnvelope` and
their schema constrains the open `metrics`/`payload` pair. The dead-letter topic carries
bare JSON, because a message reaches it precisely by failing the envelope contract, and
wrapping the report in that contract would destroy the evidence it exists to preserve.

Registered schemas cover **both** open envelope fields, not just `payload`. The drift
topic's contract lives in `metrics` — `consumer.py` reads `metric_name` and the threshold
out of it — so a schema covering only `payload` would have looked complete while
validating the half nobody reads.

Loading is lazy and cached. Import is the wrong place to raise on a malformed spec, and a
consumer that never queries the registry should not pay to parse it; `tests/contract/`
forces every spec eagerly so a bad one still fails in CI.

## Consequences

- The README topic table is generated from the register and CI fails if it drifts. The
  README became a view of the register rather than the register.
- `docker-compose.yml` is asserted against `contracts/listeners.yaml` in the contract
  tier, so the ADR 0001 class of defect now fails in CI rather than in another
  repository's container.
- Any consumer can ask which topics exist, who produces them, and what shape their bodies
  take, without reading this repository's prose.
- The register is reconciled against the live broker in both directions. Auto-create
  remains enabled — a deliberate plug-and-play choice — and reconciliation is the answer
  to what that costs rather than removing it.
- Two runtime dependencies added, `pyyaml` and `jsonschema`, on a package that previously
  needed only `pydantic`. That is a real cost paid by three repositories; it buys them a
  queryable register and per-topic validation they were each re-deriving by hand.
- A schema derived by reading producers encodes current behaviour, which may differ from
  intent. They are deliberately open wherever a producer merges caller-supplied keys, so
  they under-constrain rather than falsely reject.
