# Spec: [FEATURE NAME]

**Spec ID:** `NNN-short-slug` · **Status:** Draft | Approved | Implemented | Superseded
**Created:** YYYY-MM-DD

> **WHAT and WHY only.** No file names, no function signatures, no library choices.
> Those belong in `plan.md`. A spec a reviewer cannot argue with because it is already
> describing an implementation is not doing its job.

---

## Problem

What is wrong today, stated so that someone who has never opened this repository can
tell whether it matters. Prefer the observable failure over the abstraction.

## Evidence

How this was established. A command that was run, a file that was read, a defect that
occurred. Per Article VI, a claim with nothing behind it does not go in a spec.

```
# the command, and enough of its output to be checked
```

## Who is affected

Which repositories, which caller positions, which humans. This repository publishes a
contract three others install, so "nobody, it is internal" is almost always wrong — and
if it is genuinely right, say why.

## Outcome

What is true when this is done, written so it can be verified rather than believed.

- [ ] …
- [ ] …

## Explicitly out of scope

What this deliberately does not do, and where that work belongs instead. A boundary
stated here is worth more than one discovered in review.

## Constitutional check

| Article | Bearing on this change | Satisfied? |
|---|---|---|
| II — no local-only change | | |
| III — the seam, not the suite | | |
| VII — the register is the register | | |
| X — declared, not scattered | | |

Any "no" is either a reason not to proceed or an amendment to the constitution. It is
never something to note and move past.

## Open questions

Things that must be answered before planning, each with who can answer it. An
unanswered question left implicit becomes an assumption nobody agreed to.
