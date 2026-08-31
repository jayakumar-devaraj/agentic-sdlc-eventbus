"""The contract registry: topics, listener topology, and per-topic payload schemas.

Everything this module exposes is read from the declarative specs shipped alongside it
in ``agentic_events/contracts/``, never from constants in Python. That is the point of
the module: the register used to be a Markdown table in a README, which meant no test
could read it, no consumer could query it, and nothing could reconcile it against a
running broker.

Loading is lazy and cached rather than eager at import. Import time is not the right
place to raise on a malformed spec, and a consumer that never touches the registry
should not pay to parse it. ``tests/contract/`` validates every file eagerly, so a bad
spec still fails in CI rather than at some unlucky caller's first use.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache, lru_cache
from importlib.resources import files
from typing import Any, Final

import yaml
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as JSONSchemaValidationError

from agentic_events.errors import PayloadValidationError, RegistryError, UnknownTopicError

_CONTRACTS: Final = "contracts"


@dataclass(frozen=True, slots=True)
class Convention:
    """The topic naming convention, and the regex that enforces it."""

    pattern: str
    regex: str
    notes: str | None = None

    def matches(self, topic_name: str) -> bool:
        """Report whether ``topic_name`` satisfies the convention."""
        return re.match(self.regex, topic_name) is not None


@dataclass(frozen=True, slots=True)
class Topic:
    """One registered topic.

    ``carries`` distinguishes the two kinds of message on this bus. Most topics carry an
    :class:`~agentic_events.envelope.EventEnvelope`, and their registered schema
    constrains the open ``metrics``/``payload`` pair. The dead-letter topic carries a
    bare JSON object instead, because a message reaches it precisely by failing the
    envelope contract, and its schema constrains the whole message.
    """

    name: str
    producer: str
    consumers: tuple[str, ...]
    carries: str
    event_schema: str
    summary: str

    @property
    def carries_envelope(self) -> bool:
        """Report whether this topic's messages are ``EventEnvelope`` instances."""
        return self.carries == "envelope"


@dataclass(frozen=True, slots=True)
class Listener:
    """One broker listener, and the caller position it serves.

    ``caller_position`` is the field that matters. ADR 0001 exists because an address
    alone does not say who can reach it, and a client handed an unreachable reconnect
    address bootstraps successfully and then fails every send.
    """

    name: str
    caller_position: str
    bind: str
    advertised: str | None
    security_protocol: str
    scope: str
    serves: str


@dataclass(frozen=True, slots=True)
class SecurityPosture:
    """The broker's stated authentication and encryption posture."""

    authentication: str
    encryption: str
    rationale: str
    non_local_requirement: str


def _read_text(*parts: str) -> str:
    """Read a packaged contract file, or raise :class:`RegistryError` if it is missing."""
    resource = files("agentic_events").joinpath(_CONTRACTS, *parts)
    try:
        return resource.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError) as exc:
        name = "/".join(parts)
        raise RegistryError(f"Contract file {name!r} is missing from the package") from exc


def _load_yaml(name: str) -> dict[str, Any]:
    """Parse a packaged YAML spec into a mapping."""
    try:
        parsed = yaml.safe_load(_read_text(name))
    except yaml.YAMLError as exc:
        raise RegistryError(f"Contract file {name!r} is not parseable YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RegistryError(f"Contract file {name!r} must contain a mapping at its root")
    return parsed


def _load_json(*parts: str) -> dict[str, Any]:
    """Parse a packaged JSON document into a mapping."""
    name = "/".join(parts)
    try:
        parsed = json.loads(_read_text(*parts))
    except json.JSONDecodeError as exc:
        raise RegistryError(f"Contract file {name!r} is not parseable JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RegistryError(f"Contract file {name!r} must contain an object at its root")
    return parsed


def _validated(document: dict[str, Any], meta_schema_name: str, source: str) -> dict[str, Any]:
    """Validate a spec against its meta-schema, or raise :class:`RegistryError`."""
    validator = Draft202012Validator(_load_json(meta_schema_name))
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in errors
        )
        raise RegistryError(f"{source} does not satisfy {meta_schema_name}: {detail}")
    return document


@lru_cache(maxsize=1)
def _topics_document() -> dict[str, Any]:
    """Load and meta-validate ``topics.yaml`` once."""
    return _validated(_load_yaml("topics.yaml"), "topics.schema.json", "topics.yaml")


@lru_cache(maxsize=1)
def _listeners_document() -> dict[str, Any]:
    """Load and meta-validate ``listeners.yaml`` once."""
    return _validated(_load_yaml("listeners.yaml"), "listeners.schema.json", "listeners.yaml")


@lru_cache(maxsize=1)
def convention() -> Convention:
    """Return the topic naming convention."""
    raw = _topics_document()["convention"]
    return Convention(pattern=raw["pattern"], regex=raw["regex"], notes=raw.get("notes"))


@lru_cache(maxsize=1)
def topics() -> tuple[Topic, ...]:
    """Return every registered topic, in register order."""
    return tuple(
        Topic(
            name=raw["name"],
            producer=raw["producer"],
            consumers=tuple(raw["consumers"]),
            carries=raw["carries"],
            event_schema=raw["event_schema"],
            summary=" ".join(raw["summary"].split()),
        )
        for raw in _topics_document()["topics"]
    )


def topic_names() -> tuple[str, ...]:
    """Return the names of every registered topic."""
    return tuple(t.name for t in topics())


def topic(name: str) -> Topic:
    """Return the registered topic called ``name``.

    Raises:
        UnknownTopicError: if ``name`` is not in the register.
    """
    for candidate in topics():
        if candidate.name == name:
            return candidate
    raise UnknownTopicError(name)


@lru_cache(maxsize=1)
def listeners() -> tuple[Listener, ...]:
    """Return every declared broker listener, in spec order."""
    return tuple(
        Listener(
            name=raw["name"],
            caller_position=raw["caller_position"],
            bind=raw["bind"],
            advertised=raw["advertised"],
            security_protocol=raw["security_protocol"],
            scope=raw["scope"],
            serves=" ".join(raw["serves"].split()),
        )
        for raw in _listeners_document()["listeners"]
    )


def listener(name: str) -> Listener:
    """Return the declared listener called ``name``.

    Raises:
        RegistryError: if no listener by that name is declared.
    """
    for candidate in listeners():
        if candidate.name == name:
            return candidate
    raise RegistryError(f"No listener named {name!r} is declared in listeners.yaml")


@lru_cache(maxsize=1)
def cluster_id() -> str:
    """Return the broker's fixed KRaft cluster id."""
    return str(_listeners_document()["cluster_id"])


@lru_cache(maxsize=1)
def security_posture() -> SecurityPosture:
    """Return the broker's declared security posture."""
    raw = _listeners_document()["security_posture"]
    return SecurityPosture(
        authentication=raw["authentication"],
        encryption=raw["encryption"],
        rationale=" ".join(raw["rationale"].split()),
        non_local_requirement=" ".join(raw["non_local_requirement"].split()),
    )


@cache
def _body_validator(topic_name: str) -> Draft202012Validator:
    """Compile and cache the event-body validator registered for ``topic_name``."""
    relative = topic(topic_name).event_schema
    return Draft202012Validator(_load_json(*relative.split("/")))


def event_schema(topic_name: str) -> dict[str, Any]:
    """Return the JSON Schema registered for ``topic_name``'s event body.

    Raises:
        UnknownTopicError: if ``topic_name`` is not in the register.
    """
    schema = _body_validator(topic_name).schema
    if not isinstance(schema, dict):  # pragma: no cover - meta-schema forbids a bool schema
        raise RegistryError(f"Registered schema for {topic_name!r} is not an object")
    return schema


def _check(topic_name: str, instance: dict[str, Any]) -> None:
    """Validate ``instance`` against ``topic_name``'s registered schema."""
    try:
        _body_validator(topic_name).validate(instance)
    except JSONSchemaValidationError as exc:
        location = "/".join(str(p) for p in exc.absolute_path) or "<root>"
        raise PayloadValidationError(topic_name, f"{location}: {exc.message}") from exc


def validate_event(topic_name: str, *, metrics: dict[str, Any], payload: dict[str, Any]) -> None:
    """Validate an envelope's open fields against the schema registered for its topic.

    The envelope deliberately accepts ``metrics`` and ``payload`` as open mappings,
    because this package must not learn what any tenant's metrics mean. That openness is
    correct at the envelope layer and merely relocates the problem: every consumer then
    re-derives the same expectations by hand. This function is where that stops.

    Both fields are checked, not just ``payload``. For the drift topic the load-bearing
    half of the contract lives in ``metrics`` - the consumer reads ``metric_name`` and
    the threshold out of it - so a check that covered only ``payload`` would validate
    the half nobody depends on.

    Args:
        topic_name: The registered topic the event is published to.
        metrics: The envelope's ``metrics`` mapping.
        payload: The envelope's ``payload`` mapping.

    Raises:
        UnknownTopicError: if ``topic_name`` is not in the register.
        RegistryError: if the topic does not carry an envelope.
        PayloadValidationError: if the body does not satisfy the registered schema.
    """
    if not topic(topic_name).carries_envelope:
        raise RegistryError(
            f"Topic {topic_name!r} carries raw messages, not envelopes. "
            f"Use validate_raw_message() instead."
        )
    _check(topic_name, {"metrics": metrics, "payload": payload})


def validate_raw_message(topic_name: str, message: dict[str, Any]) -> None:
    """Validate a whole non-envelope message against its registered schema.

    Only the dead-letter topic carries these. It has to: a message lands there because
    it failed the envelope contract, so re-imposing that contract on the report would
    discard the evidence the report exists to preserve.

    Args:
        topic_name: The registered topic the message is published to.
        message: The entire decoded JSON message.

    Raises:
        UnknownTopicError: if ``topic_name`` is not in the register.
        RegistryError: if the topic carries envelopes rather than raw messages.
        PayloadValidationError: if the message does not satisfy the registered schema.
    """
    if topic(topic_name).carries_envelope:
        raise RegistryError(
            f"Topic {topic_name!r} carries envelopes. Use validate_event() instead."
        )
    _check(topic_name, message)
