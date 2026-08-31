"""Shared path setup and broker fixtures.

``scripts/`` is deliberately not part of the installed package - it is repository
tooling, not published contract - so the contract tier puts it on the path rather than
importing it from the distribution.

The broker fixtures live here rather than under ``tests/integration/`` because the
evaluation tier needs them too, and a fixture defined in a sibling directory is not
visible across it.
"""

from __future__ import annotations

import importlib.util
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

TIERS = ("unit", "contract", "integration", "evaluation")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Give every test the tier marker for the directory it lives in, and refuse strays.

    CI selects by marker (``-m "unit or contract"``), so a test with no tier marker is
    collected, reported as passing, and never actually run by the gate. ``--strict-markers``
    does not catch that - it catches a *misspelled* marker, not a *missing* one.

    This was not hypothetical. ``tests/unit/test_envelope.py`` was moved rather than
    written and carried no marker, so all 18 envelope tests were silently deselected and
    coverage of ``envelope.py`` sat at 69% while the run reported "99 passed".

    Deriving the marker from the directory means a new file cannot forget one, and the
    hard failure below means a test file dropped outside the four tiers is a collection
    error rather than a test that quietly never runs.
    """
    strays = []
    for item in items:
        tier = next((part for part in item.path.parts if part in TIERS), None)
        if tier is None:
            strays.append(str(item.path.relative_to(REPO_ROOT)))
            continue
        item.add_marker(getattr(pytest.mark, tier))

    if strays:
        raise pytest.UsageError(
            "these test files are not in a tier directory, so the marker-filtered CI run "
            f"would never execute them: {sorted(set(strays))}. "
            f"Move each into tests/{{{','.join(TIERS)}}}/."
        )


# The host position by default, because that is where a developer runs pytest. CI
# overrides it for the container positions.
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BROKER_TIMEOUT_S = 10.0

# Set by the workflow that starts a broker before running these tiers. There, an
# unreachable broker means the run proved nothing while reporting green, which is worse
# than failing - so it fails. On a laptop with nothing started, skipping is correct.
REQUIRE_BROKER = os.environ.get("EVENTBUS_REQUIRE_BROKER") == "1"


def _no_broker(reason: str) -> None:
    """Fail where a broker was promised, skip where it was merely optional."""
    if REQUIRE_BROKER:
        pytest.fail(f"EVENTBUS_REQUIRE_BROKER=1 but {reason}")
    pytest.skip(reason)


@pytest.fixture(scope="session")
def broker_metadata() -> Any:
    """Cluster metadata, or skip the tier when no broker is reachable.

    Skipped rather than failed by default: the unit and contract tiers must run cleanly
    on a laptop with nothing started. Set ``EVENTBUS_REQUIRE_BROKER=1`` to turn a skip
    into a failure, which is what the nightly workflow does after starting one.
    """
    if not importlib.util.find_spec("confluent_kafka"):
        _no_broker("confluent-kafka is not installed; install with: pip install -e '.[broker]'")
    from confluent_kafka.admin import AdminClient

    admin = AdminClient({"bootstrap.servers": BOOTSTRAP, "socket.timeout.ms": 5000})
    try:
        return admin.list_topics(timeout=BROKER_TIMEOUT_S)
    except Exception as exc:
        _no_broker(f"no broker reachable at {BOOTSTRAP}: {exc}")


@pytest.fixture
def producer() -> Any:
    """A producer bound to the configured listener."""
    if not importlib.util.find_spec("confluent_kafka"):
        _no_broker("confluent-kafka is not installed")
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
    if not importlib.util.find_spec("confluent_kafka"):
        _no_broker("confluent-kafka is not installed")
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
