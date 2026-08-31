"""Shared path setup and broker fixtures.

``scripts/`` is deliberately not part of the installed package - it is repository
tooling, not published contract - so the contract tier puts it on the path rather than
importing it from the distribution.

The broker fixtures live here rather than under ``tests/integration/`` because the
evaluation tier needs them too, and a fixture defined in a sibling directory is not
visible across it.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = REPO_ROOT / "src" / "agentic_events" / "contracts"

if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

# The host position by default, because that is where a developer runs pytest. CI
# overrides it for the container positions.
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BROKER_TIMEOUT_S = 10.0


@pytest.fixture(scope="session")
def broker_metadata() -> Any:
    """Cluster metadata, or skip the tier when no broker is reachable.

    Skipped rather than failed: the unit and contract tiers must run cleanly on a laptop
    with nothing started. CI decides separately whether a skip is acceptable - the
    workflow that owns these tiers starts a broker first and treats a skip as a failure.
    """
    pytest.importorskip("confluent_kafka", reason="install with: pip install -e '.[broker]'")
    from confluent_kafka.admin import AdminClient

    admin = AdminClient({"bootstrap.servers": BOOTSTRAP, "socket.timeout.ms": 5000})
    try:
        return admin.list_topics(timeout=BROKER_TIMEOUT_S)
    except Exception as exc:
        pytest.skip(f"no broker reachable at {BOOTSTRAP}: {exc}")


@pytest.fixture
def producer() -> Any:
    """A producer bound to the configured listener."""
    pytest.importorskip("confluent_kafka")
    from confluent_kafka import Producer

    return Producer(
        {
            "bootstrap.servers": BOOTSTRAP,
            # Publishing from the Windows host to a container broker intermittently
            # times out on the first attempt. Retries and a real delivery timeout make
            # these tests measure the contract rather than the host's networking.
            "message.timeout.ms": 15000,
            "retries": 5,
            "socket.keepalive.enable": True,
        }
    )


@pytest.fixture
def consumer_factory() -> Iterator[Callable[..., Any]]:
    """Build consumers that are always closed, even when a test fails."""
    pytest.importorskip("confluent_kafka")
    from confluent_kafka import Consumer

    created: list[Any] = []

    def build(group_id: str, **overrides: Any) -> Any:
        consumer = Consumer(
            {
                "bootstrap.servers": BOOTSTRAP,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                **overrides,
            }
        )
        created.append(consumer)
        return consumer

    yield build

    for consumer in created:
        consumer.close()
