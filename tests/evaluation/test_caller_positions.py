"""Every advertised listener is verified from the position it claims to serve.

This is the tier ADR 0001 produced. The bug it records was not that the broker was
down - the broker was fine, and a client bootstrapped against it successfully. The bug
was that the client was then handed a reconnect address it could not reach, so every
subsequent produce and fetch failed silently.

That means bootstrap succeeding proves nothing, and a test that connects from one
position proves nothing about the others. So each caller position is exercised from an
actual client sitting in that position: the host runs a client directly, a container on
this repo's own network runs one, and a container in a *different* network runs one.
The third is the position that broke.

These shell out to `docker run` rather than importing a client, because that is what
occupying a different network actually requires. `apache/kafka-native` ships no CLI, so
admin operations use a disposable full-tooling `apache/kafka` client container - adding
tooling to the broker image to make a test easier would change the thing under test.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from agentic_events import registry as reg

pytestmark = pytest.mark.evaluation

CLIENT_IMAGE = "apache/kafka:4.1.2"
BROKER_NETWORK = "eventbus"
DOCKER_TIMEOUT_S = 120


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    probe = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        capture_output=True,
        timeout=30,
        check=False,
    )
    return probe.returncode == 0


requires_docker = pytest.mark.skipif(
    not _docker_available(), reason="docker is not available on this machine"
)


def _api_versions_from(network: str | None, bootstrap: str) -> subprocess.CompletedProcess[bytes]:
    """Ask the broker for its API versions from inside a throwaway container.

    A protocol-level call, not a TCP probe. A port that accepts a connection and a
    broker that answers Kafka are different claims, and only the second one matters.
    """
    command = ["docker", "run", "--rm"]
    if network:
        command += ["--network", network]
    # Docker Desktop resolves host.docker.internal on its own; Linux CI runners do not,
    # so the mapping is passed explicitly. Harmless where it is already resolvable.
    command += ["--add-host", "host.docker.internal:host-gateway"]
    command += [
        CLIENT_IMAGE,
        "/opt/kafka/bin/kafka-broker-api-versions.sh",
        "--bootstrap-server",
        bootstrap,
    ]
    return subprocess.run(
        command, capture_output=True, timeout=DOCKER_TIMEOUT_S, check=False
    )


# --- position 1: the host machine ----------------------------------------------------


def test_host_position_reaches_the_broker_at_the_advertised_address(broker_metadata):
    # The client library reports the address it was TOLD to reconnect to, which is the
    # advertised value rather than the one it dialled. That distinction is the whole of
    # ADR 0001, so this asserts on what the broker advertised, not on what was typed.
    declared = reg.listener("PLAINTEXT_HOST")
    assert declared.caller_position == "host-machine"

    reported = {f"{b.host}:{b.port}" for b in broker_metadata.brokers.values()}
    assert declared.advertised in reported, (
        f"host clients were told to reconnect to {reported}, but listeners.yaml "
        f"declares {declared.advertised} for the host position"
    )


# --- position 2: a container on this repo's own network -------------------------------


@requires_docker
def test_internal_network_position_reaches_the_broker():
    declared = reg.listener("PLAINTEXT")
    assert declared.caller_position == "internal-network"

    result = _api_versions_from(BROKER_NETWORK, declared.advertised or "")
    assert result.returncode == 0, (
        f"a container on the {BROKER_NETWORK} network could not reach "
        f"{declared.advertised}:\n{result.stderr.decode(errors='replace')}"
    )


# --- position 3: a container in a different compose project ---------------------------


@requires_docker
def test_foreign_container_position_reaches_the_broker():
    # The position that actually broke. PLAINTEXT_HOST cannot serve it: that listener
    # advertises 'localhost', which inside another container resolves to that container
    # itself rather than to this host, so a client bootstraps and then talks to nothing.
    declared = reg.listener("DOCKER_INTERNAL")
    assert declared.caller_position == "foreign-container"

    result = _api_versions_from(None, declared.advertised or "")
    assert result.returncode == 0, (
        f"a container outside the {BROKER_NETWORK} network could not reach "
        f"{declared.advertised}. This is the ADR 0001 failure:\n"
        f"{result.stderr.decode(errors='replace')}"
    )


@requires_docker
def test_the_host_listener_is_genuinely_unreachable_from_a_foreign_container():
    # The negative half, and the reason the third listener exists at all. If this ever
    # starts passing, DOCKER_INTERNAL has become redundant and ADR 0001 needs revisiting
    # - so it is asserted rather than assumed.
    result = _api_versions_from(None, reg.listener("PLAINTEXT_HOST").advertised or "")
    assert result.returncode != 0, (
        "the host listener is now reachable from a foreign container. That contradicts "
        "ADR 0001's premise; revisit the ADR before relying on this."
    )
