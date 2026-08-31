# Tasks: [FEATURE NAME]

**Spec:** `specs/NNN-short-slug/spec.md` · **Plan:** `specs/NNN-short-slug/plan.md`

> One task, one commit. Per Article VIII, a task is finished when it is written, tested
> against something real, and committed — not when the code exists. A task that cannot
> be committed on its own is two tasks.

---

## Ordering rule

Tests that describe the behaviour come before the behaviour. Not ceremony: a test
written after the fact tends to assert what the code does rather than what was wanted,
and the difference between those two is where defects live.

Where a task depends on another, say so. Where tasks are independent, mark them `[P]` —
they can be done in any order or in parallel.

---

## Tasks

| # | Task | Depends on | Commit message |
|---|---|---|---|
| 1 | | — | |
| 2 | | 1 | |
| 3 | `[P]` | 1 | |

## Definition of done

Every box, for every task. Not at the end — per task.

- [ ] `ruff check .` clean
- [ ] `mypy` clean
- [ ] `pytest -m "unit or contract"` green, coverage at 100% with the statement count
      reported alongside it (Article IV)
- [ ] `pytest -m "integration or evaluation"` green against a running broker, if the
      change touches the seam (Article III)
- [ ] `python scripts/export_schema.py --check` passes
- [ ] `python scripts/check_compatibility.py` against `main` passes, or the plan says
      why a break is intended and how it rolls out
- [ ] Documentation updated in the same commit (Article IX)
- [ ] Committed and pushed
