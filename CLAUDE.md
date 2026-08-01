# CLAUDE.md

Standing instructions for AI agents (and human contributors) working in this repository. Claude
Code auto-loads this file every session; it is committed so the process that produced this
repository is reproducible by anyone who clones it.

The three roles this file refers to are defined as executable agents in
[`.claude/agents/`](.claude/agents/).

## Commit discipline

- Build one small piece at a time: write it, test it against something real (not just "looks
  right"), and only once it passes, commit it. Never batch a large, untested pile of files into
  one commit at the end — that's exactly the failure mode this rule exists to prevent.
- Each commit should be small enough to describe honestly in its own message — if the message
  needs "and" three times, it's probably more than one commit.
- Author: Jayakumar Devaraj <jayakumar.d10@gmail.com>. Never add Co-Authored-By or "Generated
  with" trailers/footers of any kind.
- Fresh `git init` per repo, no monolith history preserved.

## Self-check before continuing

Periodically ask: "Has it been a while since my last commit, or have I built more than one
untested piece without committing?" If yes, stop and commit what already passes its own tests
before writing anything new — don't let uncommitted work pile up into a batch to sort out later.
This applies to every repo in this platform, checked regularly, not just at the end of a session.

## Keep documentation in sync

Whenever a plan or implementation changes — a design decision gets revised, a bug fix changes
behavior, a dependency pin changes — update the relevant documentation (README, this file, the
platform's planning document) in the same change, not as a follow-up. Stale docs are a bug, not
a TODO.

## Documentation standard

- README.md section order, fixed: Tech stack -> Architecture -> Quickstart -> Local development
  -> Testing -> Deployment/CI. Nothing else. README explains how to run/use this repo, never why
  a decision was made (that's ADRs, `docs/adr/`) or how this repo relates to the other repos in
  this platform split (tracked in a private planning document, not committed anywhere).
- Never reference local machine paths (`C:\Users\...`, `C:\srcCode\...`) in committed files.
- Every significant design decision gets a lightweight ADR: `docs/adr/NNNN-title.md` (Context /
  Decision / Consequences).
- A doc claim not backed by a command actually run against real containers/code is a bug, not
  documentation — verify before writing, not after.

## AI-assisted engineering practice

This platform demonstrates AI-assisted engineering across three roles per repo, scoped to what
actually applies (an infra-only repo has no unit tests to write; that's not a gap, it's correctly
scoped — see the repo's own README for its functional verification report instead):

1. **Design**: a design document and architecture diagram for this repo (README + this file).
2. **Development**: error handling and logging where there's real code to have them; auditing
   capabilities where that's this repo's concern; meaningful Git commit history (see above).
3. **QA**: unit tests + coverage report where there's application code; a functional verification
   report where there isn't.

## This repo's place in the platform

Single-node Apache Kafka broker (KRaft mode) plus `agentic_events`, the shared event envelope
contract every other repo installs as a dependency. Repos in this platform split that carry the
`agentic-sdlc-*` prefix must stay domain-agnostic — no reference to any specific tenant service's
implementation details (its endpoints, its bugs, its internals). Referencing a tenant service by
name as an illustrative example (e.g. in a topic-naming table) is fine; describing its internals
is not.
