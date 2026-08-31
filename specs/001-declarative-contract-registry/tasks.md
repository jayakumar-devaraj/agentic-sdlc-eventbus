# Tasks: declarative contract registry

**Spec:** `specs/001-declarative-contract-registry/spec.md` · **Plan:** `specs/001-declarative-contract-registry/plan.md`

> This is the record of what was actually done, with the commit each task produced. One
> task, one commit, tested before committing — Article VIII.

---

## Ordering rule

Layout and tooling first, because every later task is judged by gates that had to exist
before they could judge anything. Then the specs, then the code that reads them, then
the gates that enforce them, then the broker-backed tiers that prove the whole thing
against something real.

The contract and evaluation tiers deliberately come after the code they test rather than
before it. This spec documents an audit-driven refactor of behaviour that already
existed, so the tests describe a contract being *pinned*, not one being designed. Specs
002 onward are test-first.

---

## Tasks

| # | Task | Depends on | Commit |
|---|---|---|---|
| 1 | Move the package under `src/`, add `py.typed`, add ruff and mypy, split tests into four tiers | — | `b1bc08e` Move agentic_events under src/ so tests exercise the built artifact |
| 2 | Write `contracts/topics.yaml`, `contracts/listeners.yaml` and their meta-schemas | 1 | `70a899e` |
| 3 | Derive the six per-topic event schemas by reading the actual producers and consumers | 2 | `70a899e` |
| 4 | Add `errors.py` and `registry.py`; loaders, lookups, and both validators | 2, 3 | `70a899e` Make the topic register something a machine can read |
| 5 | Add `telemetry.py` — W3C trace context, no SDK dependency | 1 | `b502cc1` |
| 6 | Add `traceparent`/`tracestate` to the envelope; `contract_violations()`; `validate_strict()` | 5 | `b502cc1` Carry trace context, and warn where the schema cannot enforce meaning |
| 7 | `scripts/export_schema.py` and the committed golden schema | 1 | `ea8c45b` |
| 8 | `scripts/check_compatibility.py`, plus contract tests for each breaking shape | 7 | `ea8c45b` |
| 9 | Contract tests: compose matches the listener spec; every spec is valid | 2, 4 | `ea8c45b` Turn two stated rules into gates that actually fail |
| 10 | Integration tier: round-trip a real envelope through the running broker | 4, 6 | `ca3a3f9` |
| 11 | Evaluation tier: every caller position, plus the negative case | 2 | `ca3a3f9` |
| 12 | Evaluation tier: reconcile the register against the live broker | 2 | `ca3a3f9` Test the envelope against a real broker, from every caller position |
| 13 | `.specify/` constitution and templates; `scripts/new_spec.py`; this spec | 1–12 | in progress |
| 14 | ADRs 0002, 0003, 0004 | 13 | pending |
| 15 | CI: least-privilege permissions, lint and typecheck, contract gate, nightly broker tiers | 8, 12 | pending |
| 16 | Supply chain: Dependabot, `pip-audit`, pinned mermaid install, `CODEOWNERS` | 1 | pending |
| 17 | README regenerated from the register; `CLAUDE.md` and `.claude/agents/*` updated | 13, 14 | pending |

## Findings that came out of doing the work

Neither was in the audit that preceded this spec. Both came from reading the sibling
repositories rather than from reasoning about this one.

1. **`control-plane.dlq.v1` was in no register.** Produced to since the control plane
   grew a dead-letter path. Now registered, and marked `carries: raw` — it exists to
   preserve messages that failed the envelope contract, so it cannot itself be carried
   in one.
2. **The drift contract lives in `metrics`, not `payload`.** `consumer.py:153-157` reads
   `metric_name` and the threshold out of `metrics`. The audit had proposed schemas
   covering `payload` alone, which would have looked complete and validated the half
   nobody reads. The registered schemas cover both.

## Definition of done

Per task, not at the end. Run for every commit above:

- [x] `ruff check .` clean
- [x] `mypy` clean
- [x] `pytest -m "unit or contract"` green; coverage 100% over 244 statements —
      **the count reported alongside the percentage**, per Article IV
- [x] `pytest -m "integration or evaluation"` green against the running broker
- [x] `python scripts/export_schema.py --check` passes
- [x] `python scripts/check_compatibility.py` against `origin/main` passes, and was
      separately shown to fail on a real break (see `contract-change.md`)
- [x] Documentation updated in the same commit
- [x] Committed and pushed after each task
