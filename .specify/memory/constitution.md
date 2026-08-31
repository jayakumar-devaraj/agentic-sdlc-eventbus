# Constitution — agentic-sdlc-eventbus

The non-negotiables for this repository. Every spec under `specs/` is checked against
this file before it is planned, and every plan is checked again before it is
implemented. A change that contradicts an article here does not proceed as a change; it
proceeds as an amendment to this file, with the reasoning written down.

These articles are not aspirations. Each one is here because it was learned, and most of
them cost something to learn.

---

## Article I — This repository owns a contract, not an application

A single-node Kafka broker plus `agentic_events`, the shared envelope contract every
other repository installs as a dependency. It owns **no application logic and no
database.**

If a change here starts encoding what an event *means* to a consumer, it belongs in that
consumer. The register may **name** a tenant service; it may never describe that
service's internals — not its endpoints, not its bugs, not its business rules.

## Article II — There is no such thing as a local-only change

`agentic_events` is installed by `agentic-sdlc-control-plane`, `agentic-sdlc-mlops`, and
`url-shortener-api`. Every change to it is a change to a published contract.

- **Additive by default.** New fields are optional with a default.
- **A field that becomes required is a breaking change** and needs a new schema version
  and a coordinated rollout, not a patch release.
- **Enforce structure, not meaning.** `metrics` and `payload` accept arbitrary
  event-specific shapes on purpose. This package must not learn what any tenant's
  metrics mean.

This article is machine-enforced by `scripts/check_compatibility.py`. It was prose for
a long time and prose is not a control.

## Article III — A green suite is not evidence about the seam

**This repository's tests passing proves nothing about the platform.** It is the
widest-reaching rule here and the one ADR 0001 produced.

A client that bootstraps successfully will still fail every subsequent produce and fetch
if it is handed a reconnect address it cannot reach. **Bootstrap succeeding proves
nothing.** So:

- Every listener change states which **caller position** it serves.
- Every listener change is verified **from that position** — a container on the network,
  a container outside it, or the host — never from inside the broker container, where
  everything resolves and nothing is proved.
- Never describe a workflow file as evidence. A passing run is evidence.

## Article IV — Say what a number does not prove

CI enforces 100% coverage on `agentic_events`, and that is reasonable for a package this
small. It is also **a weak signal and must never be presented as a strong one.**

Full coverage of a Pydantic model proves the model rejects what it was told to reject.
It proves nothing about whether the contract is the *right* contract — the correlation-id
defect sat underneath a fully covered envelope for weeks, because the envelope enforced
that the field was a string and the disagreement was about what the string *meant*.

**When reporting this number, report the statement count next to it.**

## Article V — Where the schema stops, write it down

The envelope guarantees `correlation_id` is a string and nothing about what the string
means. Two repositories can satisfy the schema and still disagree, which is exactly how
that defect survived two green suites.

Where this package deliberately stops enforcing, that boundary is recorded — in
`contract_violations()` where a test can reach it, not only in prose. Rules the type
system cannot express are still rules.

## Article VI — A doc claim not backed by a command actually run is a bug

Not a TODO. A bug.

`apache/kafka-native` ships no CLI tooling: that is recorded because it was confirmed by
inspection, not assumed from the image name. Every verification report in this
repository names the command that produced it.

## Article VII — The register is the register

A topic that exists on a broker but not in `contracts/topics.yaml` is **undocumented
infrastructure.** Adding a topic means adding the entry in the same change.

The broker runs with auto-create enabled — a deliberate plug-and-play choice — which
means a typo'd topic name becomes real infrastructure the moment anything sends to it.
Reconciliation against the live broker is what keeps that from also being invisible.

## Article VIII — Commit discipline

- Build one small piece at a time: write it, test it against something real, and only
  once it passes, commit it. Never batch a large untested pile into one commit.
- If a commit message needs "and" three times, it is more than one commit.
- Imperative messages that say **why**.
- Author is Jayakumar Devaraj. Never add `Co-Authored-By` or "Generated with" trailers of
  any kind.
- Push after every commit. An unpushed commit is invisible work.

## Article IX — Documentation moves with the change

A design decision revised, a bug fix that changes behaviour, a dependency pin changed —
the documentation changes in the same commit, not as a follow-up. **Stale docs are a bug.**

- Every significant decision gets an ADR: `docs/adr/NNNN-title.md`, Context / Decision /
  Consequences.
- README explains how to run and use this repository. It never explains *why* a decision
  was made — that is what ADRs are for.
- Never reference local machine paths in committed files.

## Article X — Configuration is declared, not scattered

The topic register, the listener topology, and the envelope's wire schema are
**declarative specs that CI and the runtime both read**. Nothing that belongs in a spec
lives as a constant in Python or as a value typed twice into a compose file.

Every listener declares its `scope`. Every listener is `local-dev-only` today, and
widening that requires SASL/TLS and a superseding ADR — not a port change.

---

## Amendment procedure

Amending this file is itself a spec: `specs/NNN-amend-constitution-*/spec.md`, stating
which article, what changed, and what was learned that the current wording gets wrong.
An article removed without that record is a regression, because every one of them is
here for a reason someone already paid for.

**Ratified:** 2026-08-31 · **Version:** 1.0.0
