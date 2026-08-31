"""Shared test fixtures and path setup.

``scripts/`` is deliberately not part of the installed package - it is repository
tooling, not published contract - so the contract tier puts it on the path rather than
importing it from the distribution.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = REPO_ROOT / "src" / "agentic_events" / "contracts"

if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
