from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal["1.0"] = "1.0"


class Producer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    instance_id: str


class GitTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_url: str
    branch: str
    commit_sha: str | None = None


class EventEnvelope(BaseModel):
    """The Universal Event Contract envelope shared by all agentic-sdlc-* repos.

    Mirrors the JSON Schema in 4-repo-migration-PLAN.md section 2. `metrics`
    and `payload` are intentionally open (event_type-specific) — only the
    envelope shape itself is validated here, never a specific event_type's
    business payload.
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
