"""Shared event contract for the agentic-sdlc-* platform.

This package is installed as a dependency by every other repository in the platform.
Nothing here is internal: a change to a public name is a change to a published contract.

Two layers, deliberately separate:

* :mod:`agentic_events.envelope` - the envelope every message shares. It validates
  structure and says nothing about meaning.
* :mod:`agentic_events.registry` - the declarative register of topics, listener
  topology, and the per-topic schemas for the parts the envelope leaves open. Read from
  the specs shipped in ``agentic_events/contracts/``, never from constants in Python.
"""

from agentic_events.envelope import SCHEMA_VERSION, EventEnvelope, GitTarget, Producer
from agentic_events.errors import (
    ContractError,
    ContractWarning,
    PayloadValidationError,
    RegistryError,
    UnknownTopicError,
)

__all__ = [
    "SCHEMA_VERSION",
    "ContractError",
    "ContractWarning",
    "EventEnvelope",
    "GitTarget",
    "PayloadValidationError",
    "Producer",
    "RegistryError",
    "UnknownTopicError",
]
