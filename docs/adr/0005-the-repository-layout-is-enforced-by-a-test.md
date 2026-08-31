# 0005: The repository layout is enforced by a test, and compose extras stay at the root

Date: 2026-08-31
Status: Accepted

## Context

The layout this repository adopted on 2026-08-31 — `src/` package, contracts inside the
package, four test tiers, `.specify/` and `specs/`, ADRs — was designed in an audit and
then built. Nothing checked that the build matched the design.

That gap showed up immediately. Auditing the finished tree against the proposal found
six items proposed and quietly not delivered: `uv.lock`, `.env.example`, a compose
override example, the envelope `CHANGELOG.md`, `tests/evaluation/REPORT.md`, and two of
the spec-kit documents. None was noticed by any test, because a layout described only in
a README is a suggestion. The next contributor would have inherited a structure that was
*mostly* the documented one, with no way to tell which parts were deliberate.

A second, smaller question came with it. The proposed tree put `docker-compose.yml`,
`.env.example`, and `docker-compose.override.example.yml` together under `compose/`.

## Decision

**The layout is asserted by `tests/contract/test_repository_structure.py`.** It checks
shape, never content: that the package is under `src/` and not also at the root, that
contracts are inside the package, that every test lives in one of the four tiers, that
ADRs are numbered without gaps, that each spec directory carries `spec.md`/`plan.md`/
`tasks.md`, that the required root files and workflows exist.

It runs in the `contract` tier, so it gates every pull request.

**`docker-compose.yml` stays at the repository root, and so do `.env.example` and
`docker-compose.override.example.yml`.** The `compose/` directory is retracted.

The reason is mechanical rather than aesthetic: Compose auto-loads `.env` and
`docker-compose.override.yml` only from the directory holding the compose file. In a
subdirectory neither is picked up automatically, which removes the only reason to have
them. Keeping the compose file at the root also means `docker compose up` needs no `-f`
flag — in the README quickstart, in four workflows, and in the contract test that reads it.

**`CLUSTER_ID` becomes `${CLUSTER_ID:-GbUkriPcWUY1D0RM32nhAw}`.** The committed default
is what ships; the environment can override it to run a second cluster side by side. The
contract test now asserts the *default* matches `contracts/listeners.yaml`, because the
default is the value every fresh `docker compose up` uses. It is not a secret — a KRaft
cluster id is public by nature — and it stays written down precisely so it is auditable.

**`uv.lock` is committed and gated.** Direct dependencies were exact-pinned while every
transitive one floated, so a build was never reproducible. `uv lock --check` runs in CI:
a lockfile allowed to drift is worse than none, because it reads as a guarantee it is not
providing.

## Consequences

- A structural change now either satisfies a stated rule or has to argue with a specific
  reason. The rules carry their reasons in the test, so the argument has something to be
  against.
- The test asserts shape only. It will not notice an empty `REPORT.md` or a spec whose
  `plan.md` says nothing. That limit is deliberate — a test that graded content would be
  guessing — and it is why the constitution and review still matter.
- **A dependency bump that does not regenerate `uv.lock` fails CI**, Dependabot's
  included. That is the same shape as the schema-staleness gate, with the same answer:
  run the command in the failure message and commit the result. It is friction, and it is
  the friction that makes the lockfile mean something.
- ADR numbering is now gapless *by test*. A superseded decision must be superseded in
  place rather than deleted, which is what an ADR record is for.
- The retracted `compose/` directory is recorded here rather than silently dropped, so a
  reader comparing this repository against the original audit can see that the difference
  was decided rather than forgotten.
