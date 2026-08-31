"""Shared event contract for the agentic-sdlc-* platform.

This package is installed as a dependency by every other repository in the platform.
Nothing here is internal: a change to a public name is a change to a published contract.
"""

from agentic_events.envelope import SCHEMA_VERSION, EventEnvelope, GitTarget, Producer

__all__ = ["SCHEMA_VERSION", "EventEnvelope", "GitTarget", "Producer"]
