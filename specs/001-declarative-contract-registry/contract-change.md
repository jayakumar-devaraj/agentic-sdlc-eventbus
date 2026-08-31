# Contract change: declarative contract registry

**Spec:** `specs/001-declarative-contract-registry/spec.md`

---

## What is changing

- [x] Envelope field added — `traceparent`, `tracestate`, both optional with a `None` default
- [x] Topic added — `control-plane.dlq.v1`, recorded rather than created
- [ ] Listener or advertised address changed — **no.** The topology is unchanged; it is now declared.
- [x] Per-topic event schemas added — six, one per registered topic

## Compatibility

`origin/main` carries no exported schema — this change introduces the artifact — so the
baseline was built by rendering `origin/main`'s own `envelope.py` through the same
generator. That compares the model as it was against the model as it is, which is the
comparison the gate will make on every pull request from here.

```
$ git show origin/main:agentic_events/envelope.py > /tmp/envelope_main.py
$ python /tmp/build_baseline.py
baseline built from origin/main envelope.py
fields: ['correlation_id', 'event_id', 'event_type', 'git_target', 'metrics', 'payload',
         'producer', 'scenario_type', 'schema_version', 'service', 'tenant', 'timestamp']

$ python scripts/check_compatibility.py /tmp/baseline.json \
      src/agentic_events/contracts/envelope/v1.0.schema.json
envelope schema change is backward compatible
```

**Result: compatible.**

### The gate was checked against a real break, not only a passing case

A gate that has only ever returned "fine" has not been shown to do anything. Making
`tenant` required — the exact example `development.md` uses — and re-running it:

```
$ python scripts/check_compatibility.py /tmp/baseline.json /tmp/broken.json
error: this change breaks the published envelope contract.

  - <root>.tenant: became required. Every producer that omits it starts failing on
    upgrade - that is a new schema version, not a patch.

This package is installed by agentic-sdlc-control-plane, agentic-sdlc-mlops,
and url-shortener-api. A breaking change needs a new schema version and a
coordinated rollout, not a patch release.

$ echo $?
1
```

Exit 1. `tests/contract/test_backward_compatibility.py` covers the other twelve shapes.

## If breaking

Not breaking. No new schema version, no rollout ordering required.

## If a listener changed

No listener changed. The topology moved from a compose comment into
`contracts/listeners.yaml` unaltered, and is now asserted from both directions:

```
$ pytest tests/contract/test_compose_matches_listener_spec.py -q
8 passed

$ pytest tests/evaluation/test_caller_positions.py -q
4 passed
```

The evaluation run exercises each advertised listener **from the position it serves** —
host directly, a container on the `eventbus` network, and a container outside it — plus
the negative case proving the host listener is genuinely unreachable from a foreign
container. If that negative ever passes, `DOCKER_INTERNAL` has become redundant and
ADR 0001 needs revisiting.

## If a topic changed

- [x] `contracts/topics.yaml` updated in the same change (Article VII)
- [x] Event schema added under `contracts/schemas/`, named after the topic
- [x] `carries` set correctly — `control-plane.dlq.v1` is `raw`; a message reaches it by
      failing the envelope contract, so it cannot itself be carried in one
- [x] README table regenerated from the register
- [x] Reconciliation run against the live broker

```
$ pytest tests/evaluation/test_register_reconciles_with_broker.py -q -s
registered but not yet on the broker: ['control-plane.dlq.v1']
4 passed
```

The dead-letter topic is registered and not yet on the broker, because nothing has
failed hard enough to produce to it. That is the register working ahead of reality
rather than lagging it, which is the direction it should drift.

## Downstream repositories

| Repository | Impact | Action needed |
|---|---|---|
| `agentic-sdlc-control-plane` | None forced. Gains a queryable register and per-topic validation for the four topics it produces to, including the dead-letter one it owns. | Optional: adopt `registry.validate_event()`; set `traceparent` from its existing OTEL spans. |
| `agentic-sdlc-mlops` | None forced. | Optional: same. Its `episode_correlation_id()` already satisfies both soft checks. |
| `url-shortener-api` | None forced. | Optional: same. Note its `correlation_id` is a fresh UUID per request, so it is a message id doing an episode id's job — legitimate for telemetry, worth a look when the strict switch is considered. |

None of the three needs to change to keep working. That is the point of Article II, and
it is why the soft checks warn instead of rejecting.
