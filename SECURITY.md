# Security

## What this repository is

A single-node Kafka broker for local development, plus `agentic_events` — a contract package
installed by `agentic-sdlc-control-plane`, `agentic-sdlc-mlops`, and `url-shortener-api`.

That second half is the part with a security surface worth stating plainly: **anything that
reaches this package's dependency tree reaches all three of theirs.** The package itself is small
and does no I/O, but it is a distribution point.

## The broker is unauthenticated, deliberately

Every listener is `PLAINTEXT` with no authentication and no encryption. This is declared
explicitly in `src/agentic_events/contracts/listeners.yaml`, where every listener carries
`scope: local-dev-only`, rather than left as an unstated default.

That posture is correct for a single-node broker bound to a developer machine and **is not
suitable for anything else.** Any deployment outside a developer machine needs SASL/TLS listeners
and a superseding ADR. Changing a listener's `scope` without one is a defect, and
`tests/unit/test_registry.py` fails if the scope widens.

`KAFKA_AUTO_CREATE_TOPICS_ENABLE=true` means any producer that can reach the broker can create
unbounded topics. Also correct for local development, also not for production — see the README.

## Reporting a vulnerability

Open a private security advisory through GitHub's *Security → Report a vulnerability* on this
repository. Please do not open a public issue for anything affecting the envelope contract or the
dependency tree, since a fix there has to roll out across four repositories.

Expect an acknowledgement within a few days. This is a portfolio platform, not a staffed service,
and it is better to say that than to publish a response time nobody is on call for.

## What is scanned, and when

| Check | Runs |
|---|---|
| `pip-audit --strict` over every extra, including `broker` | every PR, and weekly |
| `gitleaks` over full history | every PR, and weekly |
| SBOM (CycloneDX) | every PR, and weekly; retained 30 days |
| No local machine paths in committed files | every PR |
| Dependabot, grouped | weekly |

Advisories fail the build rather than printing. An advisory that only prints is a notification,
not a gate.

## Secrets

There are none in this repository and none are expected. The one credential-shaped value here is
`CLUSTER_ID`, which is a fixed KRaft cluster identifier — public by nature, and pinned so cluster
metadata stays valid across container restarts against the same named volume.
