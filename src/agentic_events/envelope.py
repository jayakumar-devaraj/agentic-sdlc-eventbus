"""The Universal Event Contract envelope, shared by every agentic-sdlc-* repository."""

from __future__ import annotations

import warnings
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agentic_events.errors import ContractError, ContractWarning
from agentic_events.telemetry import is_valid_traceparent

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
    registered separately under ``contracts/schemas/`` and validated on demand through
    :func:`agentic_events.registry.validate_event`.

    Two identifiers, deliberately, because they have different lifetimes:

    * ``event_id`` is per message. A redelivery of one event reuses it.
    * ``correlation_id`` is per *episode* - one drift condition, one governed run. Two
      detections of the same unresolved condition share it, which is what stops one
      regression from starting a run a minute.
    * ``traceparent`` is per request path, and is neither of the above.

    This class enforces structure. Where it cannot enforce meaning it warns rather than
    passing silently - see :func:`contract_violations`.
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

    # Added in 0.2.0. Optional with a default, so every envelope already in flight stays
    # valid: this package is installed by three sibling repositories and a newly-required
    # field would break their running producers on upgrade.
    traceparent: str | None = Field(
        default=None,
        description=(
            "W3C trace context. None when the producer has no tracing SDK "
            "installed or no span is active."
        ),
    )
    tracestate: str | None = Field(
        default=None,
        description="W3C tracestate, carried verbatim. Vendor-specific and not interpreted here.",
    )

    @field_validator("traceparent")
    @classmethod
    def _traceparent_must_be_well_formed(cls, value: str | None) -> str | None:
        """Reject a malformed ``traceparent`` outright.

        Unlike the soft checks below, this one is a hard error. The field is new, so
        nothing on the wire carries it yet and there is no fleet to migrate - and a
        malformed trace id is never the intended value, only a broken one.
        """
        if value is not None and not is_valid_traceparent(value):
            raise ValueError(
                f"traceparent must be a valid W3C trace context, got {value!r}. "
                f"Use agentic_events.telemetry.current_traceparent() to produce one."
            )
        return value

    @model_validator(mode="after")
    def _warn_on_contract_violations(self) -> EventEnvelope:
        """Surface violations of what the schema cannot express."""
        for violation in contract_violations(self):
            warnings.warn(violation, ContractWarning, stacklevel=3)
        return self


def contract_violations(envelope: EventEnvelope) -> list[str]:
    """Return the ways ``envelope`` satisfies the schema but not the contract.

    This function exists because of a defect that survived two green test suites. The
    envelope guaranteed ``correlation_id`` was a *string* and said nothing about what
    the string meant, so two repositories both satisfied the schema and still disagreed
    with each other. Every check here is one of those - a rule the type system cannot
    express, written down where a test can reach it instead of only in prose.

    Args:
        envelope: The envelope to inspect.

    Returns:
        Human-readable descriptions, empty when the envelope is clean.
    """
    violations: list[str] = []

    if not envelope.correlation_id.strip():
        violations.append(
            "correlation_id is empty or whitespace. It identifies an episode across "
            "repositories; an empty one silently groups unrelated events together."
        )

    if envelope.correlation_id == str(envelope.event_id):
        violations.append(
            "correlation_id equals event_id. They have different lifetimes on purpose: "
            "event_id is per message, correlation_id is per episode. Using the message "
            "id as the episode id makes every redelivery and re-detection look like a "
            "new episode, which is how one unresolved condition becomes many runs."
        )

    if envelope.timestamp.tzinfo is None or envelope.timestamp.utcoffset() is None:
        violations.append(
            "timestamp is naive. Events from different producers are ordered against "
            "each other, and a naive local time silently misorders against an aware one."
        )

    return violations


def validate_strict(envelope: EventEnvelope) -> None:
    """Raise if ``envelope`` violates a contract rule the schema cannot express.

    The same checks :func:`contract_violations` reports, as errors instead of warnings.
    Opt-in, and it stays opt-in until the fleet is clean: three sibling repositories
    already emit envelopes that predate these rules, so making them hard failures on a
    patch release would break running producers with no migration window. A consumer
    that wants the guarantee today can call this; a producer that wants to prove it
    emits clean events can call it in its own tests.

    Args:
        envelope: The envelope to check.

    Raises:
        ContractError: if any violation is found. All of them are reported at once.
    """
    violations = contract_violations(envelope)
    if violations:
        joined = "\n  - ".join(violations)
        raise ContractError(f"Envelope violates the event contract:\n  - {joined}")
