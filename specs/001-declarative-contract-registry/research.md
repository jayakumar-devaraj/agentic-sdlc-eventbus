# Research: declarative contract registry

**Spec:** `specs/001-declarative-contract-registry/spec.md`

Options that were genuinely considered, and what decided each. Written to save the next
person from re-opening a question that already has an answer — and to make it obvious
when the answer has expired.

---

## 1. Where does the declarative layer live?

| Option | Verdict |
|---|---|
| `contracts/` at the repository root | **Rejected.** Reads well on GitHub and does not ship. Package data comes from inside the package; a contract artifact absent from the wheel cannot be read by the three repositories that install it, which is the entire reason it exists. |
| `src/agentic_events/contracts/`, declared as package data | **Chosen.** Ships. Verified by building the wheel and listing it: 11 contract files plus `py.typed`. |
| Root `contracts/`, copied into the wheel by a build hook | **Rejected.** Reconciles both, at the cost of a custom build step that can silently stop copying. The failure mode is an empty `contracts/` directory inside a wheel nobody inspects. |

The audit that preceded this spec proposed the first option. Building the wheel is what
changed the answer — see ADR 0002.

## 2. How is the envelope's wire contract produced?

| Option | Verdict |
|---|---|
| Hand-written JSON Schema beside the model | **Rejected.** Two sources of truth that drift silently, and nothing to notice. |
| Generated from the model, committed, staleness enforced in CI | **Chosen.** `scripts/export_schema.py` writes it; `--check` fails when the model has moved and the artifact has not. Drift becomes a build failure rather than a discovery. |
| Generated at build time, never committed | **Rejected.** Nothing to diff. The whole value is a reviewable artifact in the pull request. |

Sorted keys and a fixed indent, because the file's job is to be diffed. An ordering that
shifted between runs would make every regeneration look like a change.

## 3. How is compatibility judged?

| Option | Verdict |
|---|---|
| Confluent Schema Registry | **Rejected.** A service to run, for six topics on a single-node broker. What is actually wanted is a diffable artifact and a CI gate; files and a script deliver both with nothing to operate. |
| `datamodel-code-generator` / an off-the-shelf differ | **Rejected.** None encodes *this* contract's rules — that a newly-required field is a new schema version, that nullable spelled `anyOf` is the same as nullable spelled `type: [x, null]`. |
| A checker in this repository, tested against each breaking shape | **Chosen.** ~150 lines, and `tests/contract/test_backward_compatibility.py` feeds it thirteen breaking and non-breaking shapes rather than trusting it. |

**Revisit if** the platform grows past one producer per topic, or a second language
appears. A registry earns its operational cost at that point; it does not at this one.

## 4. Eager or lazy spec loading?

Lazy, cached with `functools.lru_cache`. Import is the wrong place to raise on a
malformed spec, and a consumer that never queries the registry should not pay to parse
it. The cost — a corrupt spec surfacing at some unlucky caller's first use rather than in
CI — is paid back by `tests/contract/test_specs_are_valid.py`, which forces every spec
eagerly.

## 5. Which Kafka client for the broker-backed tiers?

| Option | Verdict |
|---|---|
| `kafka-python` | **Rejected here.** It is what the three sibling repositories use, which is an argument for consistency — but it is pure-Python and slower to surface protocol-level problems, and these tiers exist to exercise the protocol. |
| `confluent-kafka` | **Chosen.** librdkafka underneath, closer to what a production consumer would use, and Windows wheels exist. Isolated in a `broker` extra so the unit and contract tiers install nothing that talks to a broker. |

Consistency with the siblings was the real trade. It lost because these tests verify the
*broker*, not this repository's client code — there is no client code here to be
consistent with.

## 6. Enforcing the rules the schema cannot express

`correlation_id` must not be empty, must not simply be the `event_id`, and timestamps
must be aware. All three are real; the correlation-id defect is what they catch.

| Option | Verdict |
|---|---|
| Constrain the fields now | **Rejected.** Rejects envelopes all three sibling repositories emit today. Correct destination, wrong first step. |
| Warn, plus an opt-in `validate_strict()` | **Chosen.** A migration window rather than a hard cut. Article II says a newly-required constraint is a new version, not a patch — and that applies to constraints, not only to fields. |
| Say nothing, keep it in prose | **Rejected.** Prose is where it broke the first time. |

All three current producers already pass both checks, so the window should be short.
**Flipping the default is its own spec** — tracked as an open question on `spec.md`, so
that "temporarily lenient" does not quietly become permanent.
