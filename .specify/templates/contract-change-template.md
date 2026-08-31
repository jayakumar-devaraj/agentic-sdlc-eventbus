# Contract change: [WHAT IS CHANGING]

**Spec:** `specs/NNN-short-slug/spec.md`

> Required for any change to the envelope, the topic register, or the listener topology.
> Those three are the only things this repository publishes, so a change to one of them
> is the only kind of change here that can break another repository.

---

## What is changing

- [ ] Envelope field added / changed / removed
- [ ] Topic added / retired / renamed
- [ ] Listener or advertised address changed
- [ ] Per-topic event schema changed

## Compatibility

Run it; do not reason about it (Article VI):

```bash
git show origin/main:src/agentic_events/contracts/envelope/v1.0.schema.json > /tmp/baseline.json
python scripts/export_schema.py
python scripts/check_compatibility.py /tmp/baseline.json src/agentic_events/contracts/envelope/v1.0.schema.json
```

**Result:** compatible / breaking
**Output:**

```
```

## If breaking

A breaking change is not forbidden. It is forbidden to make one *quietly*.

- **New schema version:** …
- **Rollout order across repositories:** …
- **How producers on the old version keep working during the rollout:** …
- **ADR recording it:** `docs/adr/NNNN-…`

## If a listener changed

Article III. An address alone does not say who can reach it.

- **Caller position served:** internal-network / intra-cluster / host-machine / foreign-container
- **Verified from that position by:**

```
# the command actually run, and its result
```

- **Does `contracts/listeners.yaml` still match `docker-compose.yml`?** (the contract
  tier asserts this — paste the run)

## If a topic changed

- [ ] `contracts/topics.yaml` updated in this same change (Article VII)
- [ ] Event schema added under `contracts/schemas/`, named after the topic
- [ ] `carries` set correctly — `envelope`, or `raw` for anything that must survive
      failing the envelope contract
- [ ] README table regenerated
- [ ] Reconciliation against the live broker run

## Downstream repositories

Which of `agentic-sdlc-control-plane`, `agentic-sdlc-mlops`, `url-shortener-api` this
reaches, and what each needs to do — including "nothing", where that is actually true.

| Repository | Impact | Action needed |
|---|---|---|
| | | |
