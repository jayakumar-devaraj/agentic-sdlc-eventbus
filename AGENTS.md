# AGENTS.md

How to work on this repository with an AI coding agent, and how to check the agent is bound by
this repository's rules rather than its own defaults.

| File | Holds |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Standing instructions: commit discipline, documentation standard, this repo's place in the platform |
| [`.claude/agents/design.md`](.claude/agents/design.md) | The topic register and listener topology. Read-only over the source tree |
| [`.claude/agents/development.md`](.claude/agents/development.md) | Changes to `agentic_events` and the broker stack. Treats the envelope as a published contract |
| [`.claude/agents/qa.md`](.claude/agents/qa.md) | Tests the contract package and designs functional verification for broker behaviour |

## Provenance — read this before trusting the rest

**These definitions were written on 2026-07-31, after the implementation they describe.**
`git log -- .claude/` shows that, and it should. This platform was built through interactive
sessions against `CLAUDE.md`; no prompt chain was ever stored, and reconstructing one now would be
manufacturing an audit trail that did not exist. **What is reproducible is the rules and the
workflow below — not the original sessions.**

## Invoking an agent

Claude Code resolves `.claude/agents/` from the repository root, so run from the repo:

```bash
claude --agent qa -p "your task here"
```

### Check the binding actually worked

This repo's `qa` agent carries an unusual instruction: that its own headline 100% coverage is a
**weak** signal and must never be presented as a strong one. That makes it a good binding check,
because a generic agent will say the opposite.

```bash
claude --agent qa -p "In under 40 words: what do you say about this repo's 100% coverage number?"
```

Verified 2026-08-01, this returns:

> 100% covers 31 statements in a Pydantic envelope — it proves the schema rejects invalid input,
> nothing more. The real risk lives in the seam CI can't unit-test: cross-container reconnects,
> broker admin ops, topic behavior — covered by the functional verification report instead.

If instead you get congratulated on full coverage, the agent did not load.

## Which agent for which task

| Task | Agent | Why |
|---|---|---|
| Add a topic | `design` | The README table is the register; a topic on the broker but not in the table is undocumented infrastructure |
| Change the envelope | `development` | It is installed by every other repo. Additive by default; a newly-required field is a new topic version, not a patch |
| Change listeners or `advertised.listeners` | `design`, then `qa` | Each listener serves a caller position, and the change is verified *from that position* — bootstrap succeeding proves nothing (ADR 0001) |
| Add tests | `qa` | Knows the difference between covering this package and covering the seam |

## What these agents do not do

- **They do not treat this repo's tests as evidence about the platform.** This repo's suite passing
  proves nothing about the seam — the widest-reaching rule in the platform, and the one this
  repository's own ADR 0001 produced.
- **They cannot see what the envelope does not enforce.** It guarantees `correlation_id` is a
  string and nothing about what the string means. Two repos can satisfy the schema and still
  disagree, which is exactly how the correlation-id defect survived two green suites.
