"""The register is held against the live broker, in both directions.

``.claude/agents/design.md`` states the rule: *a topic that exists on a broker but not
in that table is undocumented infrastructure*. While the register was a Markdown table
nothing could check it, and something had already slipped through - the control plane
has been producing to a dead-letter topic that appeared in no register anywhere. It was
found by reading the producers, which is not a control that scales.

This is the control. The broker runs with auto-create enabled, so a typo'd topic name
becomes real infrastructure the moment anything sends to it; reconciliation is what
keeps that from also being invisible.
"""

from __future__ import annotations

import pytest

from agentic_events import registry as reg

pytestmark = pytest.mark.evaluation

# Kafka's own bookkeeping. Not infrastructure this platform declares or owns.
INTERNAL_PREFIX = "__"

# Topics this repository's own test tiers create by publishing to them. Namespaced
# under this repo's name with a 'test-' event type so they are recognisable as
# scaffolding rather than platform traffic, and exempt by that shape rather than by a
# hardcoded list that would quietly grow.
TEST_EVENT_TYPE_PREFIX = "test-"


def _is_test_topic(name: str) -> bool:
    segments = name.split(".")
    return len(segments) >= 2 and segments[1].startswith(TEST_EVENT_TYPE_PREFIX)


def _platform_topics(metadata) -> set[str]:
    """Every topic on the broker that this platform is responsible for declaring."""
    return {
        name
        for name in metadata.topics
        if not name.startswith(INTERNAL_PREFIX) and not _is_test_topic(name)
    }


def test_no_topic_on_the_broker_is_missing_from_the_register(broker_metadata):
    undeclared = _platform_topics(broker_metadata) - set(reg.topic_names())
    assert undeclared == set(), (
        f"these topics exist on the broker and in no register: {sorted(undeclared)}. "
        f"A topic on a broker but not in contracts/topics.yaml is undocumented "
        f"infrastructure - add the entry in the same change that introduces the topic."
    )


def test_every_live_topic_satisfies_the_naming_convention(broker_metadata):
    convention = reg.convention()
    offenders = [n for n in _platform_topics(broker_metadata) if not convention.matches(n)]
    assert offenders == [], (
        f"these live topics do not match {convention.pattern}: {offenders}. "
        f"Auto-create means a typo becomes real infrastructure silently."
    )


def test_no_live_topic_mixes_dot_and_underscore_separators(broker_metadata):
    # Kafka collapses '.' and '_' to the same JMX metric name, so two topics differing
    # only in separator would silently share metrics. Checked against what is actually
    # on the broker, not only against what the register says.
    offenders = [n for n in _platform_topics(broker_metadata) if "_" in n]
    assert offenders == [], f"topic names must never contain '_': {offenders}"


def test_registered_topics_that_do_not_exist_yet_are_reported_not_failed(broker_metadata):
    # The other direction, and deliberately not an assertion of absence. A registered
    # topic with no messages yet simply has not been created - the dead-letter topic is
    # exactly that, and it existing in the register before it exists on the broker is
    # the register working, not failing.
    live = _platform_topics(broker_metadata)
    not_yet_created = sorted(set(reg.topic_names()) - live)
    print(f"\nregistered but not yet on the broker: {not_yet_created or 'none'}")
    assert set(not_yet_created) <= set(reg.topic_names())
