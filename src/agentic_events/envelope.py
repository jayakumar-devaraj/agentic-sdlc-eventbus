"""The Universal Event Contract envelope, shared by every agentic-sdlc-* repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal["1.0"] = "1.0"


class Producer(BaseModel):
    """The service instance that emitted an event."""

    model_config = ConfigDict(extra="forbid")

    service: str
    instance_id: str


class GitTarget(BaseModel):
    """The repository, branch, and commit an event refers to."""

    model_config = ConfigDict(extra="forbid")

    repo_url: str
    branch: str
    commit_sha: str | None = None


class EventEnvelope(BaseModel):
    """The Universal Event Contract envelope shared by all agentic-sdlc-* repos.

    The wire form of this model is exported to ``contracts/envelope/v1.0.schema.json``
    and that file, not this class, is the artifact downstream repositories diff against.

    ``metrics`` and ``payload`` are intentionally open: only the envelope shape is
    validated here, never a specific ``event_type``'s business payload. Those are
    registered separately under ``contracts/payloads/`` and validated on demand through
    :func:`agentic_events.registry.validate_payload`.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    event_id: UUID
    correlation_id: str
    tenant: str = "default"
    service: str
    event_type: str
    timestamp: datetime
    producer: Producer
    git_target: GitTarget
    scenario_type: Literal["greenfield", "brownfield", "ambiguous"]
    metrics: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
