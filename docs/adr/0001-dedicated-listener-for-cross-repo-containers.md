# 0001: Dedicated `DOCKER_INTERNAL` listener for cross-repo containers

Date: 2026-07-26
Status: Accepted

## Context

The original design pointed other repos' containers at this broker via `host.docker.internal:9092`,
reusing the `PLAINTEXT_HOST` listener already set up for host-machine CLI access. This looked
correct — the bootstrap connection succeeded, since the port is published — but every actual
produce/fetch silently failed. `PLAINTEXT_HOST` advertises `localhost:9092`; a client that
*bootstraps* via `host.docker.internal` is then told to *reconnect* to `localhost` for real traffic,
and inside a different container `localhost` resolves to that container itself, not this host.

This was found building `url-shortener-api` (the first consuming repo), not by this repo's own
testing — that testing only ever exercised the same-network (`PLAINTEXT`) and host-CLI
(`PLAINTEXT_HOST`-from-the-host) paths, never a genuinely separate container reaching in through the
published port. `url-shortener-api`'s telemetry publish is deliberately best-effort (its own
reliability design), so the failure degraded silently — logged `KafkaTimeoutError`s, zero impact on
its HTTP response — rather than crashing anything, which is exactly why it wasn't caught sooner.

## Decision

Added a third listener, `DOCKER_INTERNAL` on port 9093, advertised as `host.docker.internal:9093`.
Verified by producing from a container with *no* shared network with this repo (matching another
repo's real topology) and confirming the message was actually consumable, not just accepted.

## Consequences

- Three listeners now exist for three distinct caller positions: `PLAINTEXT` (same Docker network),
  `PLAINTEXT_HOST` (host machine), `DOCKER_INTERNAL` (another repo's own compose project). See the
  README's Cross-repo connectivity table for the exact value each caller uses.
- General lesson: a repo's own local testing proving a service "works" doesn't prove a *cross-repo*
  integration point works — that needs testing from the actual position the other repo calls from.
