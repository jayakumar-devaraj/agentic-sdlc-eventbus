"""Exceptions this package owns.

Consumers previously caught :class:`pydantic.ValidationError` directly, which coupled
them to the validation library rather than to this contract. Everything raised across
this package's public surface derives from :class:`ContractError`, so a consumer can
catch one thing and stay insulated from how validation happens to be implemented.
"""

from __future__ import annotations


class ContractError(Exception):
    """Base class for every error this package raises."""


class RegistryError(ContractError):
    """The contract registry itself is unusable.

    Raised when a registry file is missing, unparseable, or fails its meta-schema.
    This is a defect in this repository, not in the caller.
    """


class UnknownTopicError(ContractError):
    """A topic was referenced that the register does not declare.

    The broker runs with auto-create enabled, so an unregistered topic name will
    happily become real infrastructure. This error is what makes the register
    load-bearing rather than advisory.
    """

    def __init__(self, topic: str) -> None:
        """Record the offending topic name."""
        self.topic = topic
        super().__init__(
            f"Topic {topic!r} is not in the register. A topic that exists on a broker "
            f"but not in contracts/topics.yaml is undocumented infrastructure - add the "
            f"entry in the same change that introduces the topic."
        )


class PayloadValidationError(ContractError):
    """An event's payload did not satisfy the schema registered for its topic.

    The envelope deliberately does not validate ``payload``; this is the error raised
    by the separate, opt-in check that does.
    """

    def __init__(self, topic: str, reason: str) -> None:
        """Record the topic whose payload schema was violated, and why."""
        self.topic = topic
        self.reason = reason
        super().__init__(f"Payload for topic {topic!r} failed its registered schema: {reason}")


class ContractWarning(UserWarning):
    """A value satisfies the schema's type but not the contract's intent.

    This exists because of a defect that survived two green test suites: the envelope
    guaranteed ``correlation_id`` was a *string* and said nothing about what the string
    meant, so two repositories agreed with the schema and disagreed with each other.

    Warnings rather than errors, deliberately. This package is already installed by
    three sibling repositories whose producers emit values that predate these checks;
    turning those into hard failures on a patch release would break running services
    with no migration window. Strictness is opt-in through
    :func:`agentic_events.envelope.validate_strict` until the fleet is clean.
    """
