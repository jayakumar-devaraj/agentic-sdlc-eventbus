# Contributing

Read [`.specify/memory/constitution.md`](.specify/memory/constitution.md) first. It is short, and
every article in it is there because something was already learned the hard way.

## The shape of a change

Any change to the envelope, the topic register, or the listener topology — the only three things
this repository publishes — starts as a spec:

```bash
python scripts/new_spec.py --contract-change "what you are changing"
```

Write `spec.md` (what and why) before `plan.md` (how) before `tasks.md`. Anything smaller than
that — a typo, a comment, a test — does not need a spec. If you are unsure, the test is whether
another repository could notice.

## Before you open a pull request

```bash
ruff format . && ruff check . && mypy
pytest -m "unit or contract" --cov=agentic_events --cov-report=term-missing --cov-fail-under=100
python scripts/export_schema.py --check
python scripts/render_topic_table.py --check
```

If your change touches the seam — the envelope, a listener, the register — run the broker tiers
too. They are nightly in CI, which is not soon enough to catch your change before it merges:

```bash
docker compose up -d
pytest -m "integration or evaluation" -q
```

## Commits

- One small piece at a time: write it, test it against something real, commit it. Never batch a
  large untested pile into one commit at the end.
- If the message needs "and" three times, it is more than one commit.
- Imperative, and say **why**: *"Fix cross-container listener advertising the wrong address"*.
- Never add `Co-Authored-By` or "Generated with" trailers of any kind.
- Push after every commit. An unpushed commit is invisible work.

## Things that will get a change sent back

- **A new topic without a register entry in the same change.** A topic on a broker but not in
  `contracts/topics.yaml` is undocumented infrastructure.
- **A required envelope field added on a patch.** Three repositories install this package. That is
  a new schema version and a rollout order, not a patch — `contract-compat.yml` will say so.
- **A listener change verified from inside the broker container.** Everything resolves there and
  nothing is proved. Verify from the caller position the listener serves.
- **A doc claim with no command behind it.** Not a TODO — a bug.
- **Reporting coverage without the statement count.** 100% over 244 statements is a weak signal
  and this repository says so out loud.
- **Anything describing a tenant service's internals.** Naming one is fine; describing how it
  works is not.

## Where things live

| Question | Answer |
|---|---|
| How do I run this? | `README.md` |
| Why is it like this? | `docs/adr/` |
| What was the change trying to do? | `specs/` |
| What are the rules? | `.specify/memory/constitution.md` |
| How do I drive an AI agent here? | `AGENTS.md`, `.claude/agents/` |
