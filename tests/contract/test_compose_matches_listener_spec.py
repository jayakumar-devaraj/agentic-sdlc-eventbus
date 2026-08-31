"""The broker's compose file must say exactly what the listener spec says.

ADR 0001 records a bug that cost real debugging time: a listener advertised an address
the caller could not reach, so clients bootstrapped successfully and then failed every
subsequent produce and fetch, silently. Bootstrap succeeding proves nothing.

That failure mode is invisible to every other test in this repository. The unit tier
never starts a broker; the integration tier connects from one position and would not
notice another position being wrong. What catches it is holding the compose file and
the declared topology against each other, which is what this module does - so a
listener change that contradicts the spec fails in CI rather than in another repo's
container three days later.
"""

import re
from pathlib import Path

import pytest
import yaml

from agentic_events import registry as reg

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]


_INTERPOLATED = re.compile(r"^\$\{[A-Z_][A-Z0-9_]*:-(?P<default>.*)\}$")


def _broker_environment() -> dict[str, str]:
    """Read the broker's environment, resolving `${VAR:-default}` to its default.

    The committed default is what ships and what every fresh `docker compose up` uses,
    so it is the value these tests hold against the spec. An operator exporting a
    different value locally is doing so deliberately and is not this repository's
    concern; a wrong default would be everyone's.
    """
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    resolved = {}
    for key, value in compose["services"]["kafka"]["environment"].items():
        text = str(value)
        match = _INTERPOLATED.match(text)
        resolved[key] = match.group("default") if match else text
    return resolved


def _parse_listener_list(value: str) -> dict[str, str]:
    """Turn ``NAME://host:port,NAME://host:port`` into a mapping."""
    entries = {}
    for item in value.split(","):
        name, _, address = item.partition("://")
        entries[name.strip()] = address.strip()
    return entries


def test_every_declared_listener_is_bound_in_compose():
    bound = _parse_listener_list(_broker_environment()["KAFKA_LISTENERS"])
    assert {x.name for x in reg.listeners()} == set(bound)


def test_bind_addresses_match_the_spec():
    bound = _parse_listener_list(_broker_environment()["KAFKA_LISTENERS"])
    assert {x.name: x.bind for x in reg.listeners()} == bound


def test_advertised_addresses_match_the_spec():
    # The field ADR 0001 is about. The advertised address is what a client is told to
    # reconnect to, and getting it wrong is what fails silently after a good bootstrap.
    advertised = _parse_listener_list(_broker_environment()["KAFKA_ADVERTISED_LISTENERS"])
    expected = {x.name: x.advertised for x in reg.listeners() if x.advertised is not None}
    assert expected == advertised


def test_the_controller_is_not_advertised():
    advertised = _parse_listener_list(_broker_environment()["KAFKA_ADVERTISED_LISTENERS"])
    assert "CONTROLLER" not in advertised


def test_security_protocol_map_matches_the_spec():
    declared = dict(
        item.split(":", 1)
        for item in _broker_environment()["KAFKA_LISTENER_SECURITY_PROTOCOL_MAP"].split(",")
    )
    assert {x.name: x.security_protocol for x in reg.listeners()} == declared


def test_cluster_id_matches_the_spec():
    # Fixed on purpose so KRaft metadata stays valid across restarts against the same
    # named volume. A regenerated id silently invalidates the existing log directory.
    assert _broker_environment()["CLUSTER_ID"] == reg.cluster_id()


def test_the_controller_quorum_points_at_the_controller_listener():
    environment = _broker_environment()
    assert environment["KAFKA_CONTROLLER_LISTENER_NAMES"] == "CONTROLLER"
    assert reg.listener("CONTROLLER").bind in environment["KAFKA_CONTROLLER_QUORUM_VOTERS"]


def test_inter_broker_traffic_uses_the_internal_network_listener():
    name = _broker_environment()["KAFKA_INTER_BROKER_LISTENER_NAME"]
    assert reg.listener(name).caller_position == "internal-network"
