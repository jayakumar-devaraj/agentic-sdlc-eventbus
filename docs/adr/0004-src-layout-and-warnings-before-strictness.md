# 0004: `src/` layout, and warnings before strictness

Date: 2026-08-31
Status: Accepted

## Context

Two decisions with one thing in common: both are about the gap between what this
repository tests and what three other repositories actually receive.

**The layout.** `agentic_events/` sat at the repository root. With `pip install -e .` and
pytest run from that root, tests imported the working tree. The wheel — the artifact
`agentic-sdlc-control-plane`, `agentic-sdlc-mlops`, and `url-shortener-api` install — was
never exercised by anything. A file missing from the distribution, or package data that
does not ship, is invisible to a green suite. That matters more here than in most repos,
because the contract registry is now package data: had it shipped only in the source tree,
every consumer would import the package successfully and find no contracts inside it.

The package was also fully annotated and shipped no `py.typed`, so every downstream
`mypy` run silently degraded `EventEnvelope` to `Any`. The type safety existed and was
not delivered.

**The strictness.** `contract_violations()` writes down rules the schema cannot express:
`correlation_id` must not be empty, must not simply be the `event_id`, and timestamps must
be timezone-aware. These are real rules — the correlation-id defect is exactly what they
catch. The question was whether to enforce them.

## Decision

**`src/` layout**, with `--import-mode=importlib`, so tests resolve `agentic_events`
through the installed distribution rather than by accident of the current directory. Ship
`py.typed`.

**Contract violations warn; they do not reject.** They raise `ContractWarning`, and
`validate_strict()` is an opt-in entry point that raises `ContractError` on the same
conditions.

The reason is a migration window, not squeamishness. Three sibling repositories emit
envelopes today that predate these rules. Making them hard failures on a patch release
would break producers that are running right now, with no window to adapt — and Article II
of the constitution says a newly-required constraint is a new schema version, not a patch.
That applies to constraints, not only to fields.

As it happens all three current producers already pass both checks: each uses
`datetime.now(timezone.utc)`, and none uses `event_id` as `correlation_id`. So the
expected migration is short. Flipping the default is a spec of its own.

## Consequences

- Tests exercise the built artifact. Package data that does not ship now fails here
  instead of in a consumer's process.
- Downstream type checking works. `EventEnvelope` is a real type to `mypy` again.
- The import path is unchanged — only the source tree moved — so the three installing
  repositories need no change.
- A producer emitting a violating envelope keeps working and gets a warning. That is the
  intended behaviour and also the risk: a warning nobody reads is not a control. The
  strict entry point exists so a consumer that wants the guarantee today can have it, and
  so a producer can prove it emits clean events in its own tests.
- There is now a decision to revisit rather than a rule that is simply enforced. That is
  recorded as an open question on `specs/001` so it does not quietly become permanent.
