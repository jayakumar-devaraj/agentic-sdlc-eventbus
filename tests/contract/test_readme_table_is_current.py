"""The README's topic table must match the register it is generated from.

The table used to *be* the register, which meant the platform's rule about undocumented
infrastructure rested on a document nothing could parse. Now the register is
``contracts/topics.yaml`` and the table is a view of it - and a view that can silently
disagree with its source is worse than no view, because it still reads as authoritative.
"""

import pytest

from render_topic_table import README, render

pytestmark = pytest.mark.contract


def test_readme_table_matches_the_register():
    assert render() in README.read_text(encoding="utf-8"), (
        "The register changed and the README table did not. "
        "Run: python scripts/render_topic_table.py"
    )


def test_every_registered_topic_appears_in_the_readme():
    from agentic_events import registry as reg

    readme = README.read_text(encoding="utf-8")
    missing = [t.name for t in reg.topics() if f"`{t.name}`" not in readme]
    assert missing == []
