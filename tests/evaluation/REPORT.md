# Functional verification report — the seam

This is the primary QA artefact for this repository, not a supplement. Most of what can
go wrong here cannot be reached by a unit test: the broker has no application logic, and
the failure that cost real debugging time was a client bootstrapping successfully and
then failing every subsequent send.

**Every row is a test that runs, not a check somebody performed once.** Reproduce all of
it with:

```bash
docker compose up -d
pytest -m "integration or evaluation" -q
```

Last full run: **2026-08-31**, `13 passed, 0 skipped` — on a GitHub Actions
`ubuntu-latest` runner ([run 33430441078](https://github.com/jayakumar-devaraj/agentic-sdlc-eventbus/actions/runs/33430441078))
and against Docker Desktop on Windows. Both, deliberately: they resolve
`host.docker.internal` differently, and the listener topology depends on that.

## Caller positions — `tests/evaluation/test_caller_positions.py`

ADR 0001 exists because an address does not say who can reach it. Each listener is
therefore exercised **from the position it claims to serve**, by a client actually
sitting there — not from inside the broker container, where everything resolves and
nothing is proved.

| Position | Listener | How | Result |
|---|---|---|---|
| Host machine | `PLAINTEXT_HOST` → `localhost:9092` | A client on the host reads cluster metadata and is checked against the address the broker **advertised**, not the one it dialled | PASS |
| Container on `eventbus` | `PLAINTEXT` → `broker:19092` | `kafka-broker-api-versions.sh` from a disposable `apache/kafka:4.1.2` container on the network | PASS |
| Container in another project | `DOCKER_INTERNAL` → `host.docker.internal:9093` | Same, from a container with **no** shared network — the position that broke | PASS |
| Host listener from a foreign container | `PLAINTEXT_HOST` | The **negative** case: the same call must fail | PASS (correctly refuses) |

That last row is the one that keeps the design honest. `PLAINTEXT_HOST` advertises
`localhost`, which inside another container resolves to that container itself. If it
ever becomes reachable, `DOCKER_INTERNAL` is redundant and ADR 0001 needs revisiting —
so it is asserted rather than assumed.

A protocol-level call is used throughout, never a TCP probe. A port that accepts a
connection and a broker that answers Kafka are different claims, and only the second one
matters. (The compose healthcheck *is* a bare TCP probe — `apache/kafka-native` ships no
CLI, confirmed by inspection — which is exactly why this tier exists alongside it.)

## Register reconciliation — `tests/evaluation/test_register_reconciles_with_broker.py`

The broker runs with auto-create enabled, so a typo'd topic name becomes real
infrastructure the moment anything sends to it. Reconciliation is what stops that from
also being invisible.

| Check | Result |
|---|---|
| No topic on the broker is absent from `contracts/topics.yaml` | PASS |
| Every live topic satisfies the naming convention | PASS |
| No live topic mixes `.` and `_` separators (they collide in JMX metric names) | PASS |
| Registered topics not yet on the broker are reported, not failed | PASS — `control-plane.dlq.v1` |

That last line is the register working ahead of reality rather than lagging it. The
dead-letter topic is declared before anything has failed hard enough to create it.

**This check found a real gap.** `control-plane.dlq.v1` had been produced to since the
control plane grew a dead-letter path and appeared in no register anywhere. It was found
by reading the sibling repository's producers — which is not a control that scales, and
is the reason this test exists.

## Envelope round trip — `tests/integration/test_envelope_roundtrip.py`

Before this, the contract and the transport were tested separately and never together.

| Check | Result |
|---|---|
| An envelope survives the wire unchanged | PASS |
| The returned body still satisfies its registered per-topic schema | PASS |
| Trace context survives the broker hop | PASS |
| Timestamps come back timezone-aware | PASS |
| A malformed message is rejected by the contract, not silently accepted | PASS |

Timezone-awareness is asserted **after** a real round trip rather than on a model built
in memory, because serialisation is where an aware datetime quietly becomes naive.

Test traffic goes to `eventbus.test-*` topics, never a registered one. Publishing
fabricated drift to `mlops.drift-detected.v1` would put it in front of a real consumer.

## What this report does not cover

Stated rather than left to be discovered:

- **Multi-broker behaviour.** Single node, replication factor 1. Nothing here says
  anything about partition leadership, ISR shrink, or an unclean leader election.
- **Authentication and encryption.** Every listener is `PLAINTEXT`, scoped
  `local-dev-only` in `contracts/listeners.yaml`. There is no SASL or TLS path to verify
  because there is deliberately no SASL or TLS.
- **Retention, compaction, or throughput.** Auto-created topics inherit cluster defaults.
  No load has been applied and no claim about capacity is made.
- **That the contract is the *right* contract.** These tests prove the envelope survives
  a broker and satisfies its own schema. They cannot prove two repositories agree about
  what `correlation_id` *means* — that is exactly how the correlation-id defect survived
  two green suites, and it is why `contract_violations()` exists as prose-turned-code.
