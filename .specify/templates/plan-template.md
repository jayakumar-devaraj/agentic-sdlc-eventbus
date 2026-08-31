# Plan: [FEATURE NAME]

**Spec:** `specs/NNN-short-slug/spec.md` · **Status:** Draft | Approved | Implemented

> **HOW.** This is where file names, signatures, and library choices belong. If the spec
> had to be reopened to write this, say so — a plan that contradicts its spec means the
> spec was wrong, and the spec gets fixed rather than quietly diverged from.

---

## Approach

The shape of the change in a paragraph, then the reasoning. Lead with the decision, not
with the survey of alternatives.

## Alternatives rejected

| Option | Why not |
|---|---|
| | |

Only real candidates. A straw man in this table is worse than an empty table.

## Contract impact

**Required.** This repository publishes a contract three others install.

- **Envelope schema changes:** none / additive / breaking
- **New or changed topics:** …
- **Listener topology changes:** … (and which caller position each serves — Article III)
- **Does `scripts/check_compatibility.py` pass against `main`?** …
- **If breaking:** the new schema version, and the rollout order across repositories.

## Verification

How this will be shown to work, by tier. Per Article III, this repository's own suite is
not evidence about the seam, so a change that touches the seam needs a row in the last
two.

| Tier | What it will prove | New or changed |
|---|---|---|
| `unit/` | | |
| `contract/` | | |
| `integration/` | | |
| `evaluation/` | | |

## Files

| Path | Change |
|---|---|
| | |

## Risks

What could go wrong, and what would make it visible. "Nothing" is not an answer; a
change with no failure mode is a change with an unexamined one.

## Documentation moving with this change

Per Article IX, listed here rather than left to memory.

- [ ] README
- [ ] ADR `docs/adr/NNNN-…`
- [ ] `.specify/memory/constitution.md`
- [ ] `.claude/agents/*.md`
