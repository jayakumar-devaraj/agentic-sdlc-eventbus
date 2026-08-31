"""The repository layout is a contract too, and this is what holds it.

A structure that exists only in a README is a suggestion. Everything asserted here was
either designed deliberately or learned the hard way, and each rule names which - so a
later change either satisfies it or has to argue with a specific reason rather than with
an unexplained convention.

This is deliberately about *shape*, never about content. It does not care what an ADR
says, only that decisions get recorded as ADRs; not what a spec argues, only that specs
carry the sections the workflow depends on.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "src" / "agentic_events"
CONTRACTS = PACKAGE / "contracts"
TIERS = ("unit", "contract", "integration", "evaluation")


# --- the package ---------------------------------------------------------------------


def test_the_package_lives_under_src():
    # Not at the repository root. With the package at root, pytest imports the working
    # tree and the wheel three sibling repositories install is never exercised. See
    # ADR 0004.
    assert PACKAGE.is_dir()
    assert not (REPO / "agentic_events").exists(), "the package must not also exist at the root"


def test_the_package_ships_a_pep561_marker():
    # Without it every downstream mypy silently degrades EventEnvelope to Any: the type
    # safety exists and is not delivered.
    assert (PACKAGE / "py.typed").is_file()


def test_the_contracts_live_inside_the_package_not_at_the_root():
    # A contract artifact that is not in the wheel cannot be read by the repositories
    # that install this package, which is the entire reason it exists. ADR 0002.
    assert CONTRACTS.is_dir()
    assert not (REPO / "contracts").exists(), (
        "contracts/ at the repository root would not ship in the wheel - see ADR 0002"
    )


def test_every_module_the_public_surface_needs_is_present():
    expected = {"__init__.py", "envelope.py", "errors.py", "registry.py", "telemetry.py"}
    assert expected <= {p.name for p in PACKAGE.glob("*.py")}


def test_the_contract_layer_has_all_four_kinds_of_spec():
    assert (CONTRACTS / "topics.yaml").is_file()
    assert (CONTRACTS / "listeners.yaml").is_file()
    # One meta-schema per document, so a malformed spec names the document it came from.
    assert (CONTRACTS / "topics.schema.json").is_file()
    assert (CONTRACTS / "listeners.schema.json").is_file()
    assert (CONTRACTS / "schemas").is_dir()
    assert (CONTRACTS / "envelope").is_dir()


def test_the_envelope_directory_carries_a_changelog():
    # The schema file is generated and has no history of its own: a diff shows what
    # changed, never why or whether a consumer must act.
    assert (CONTRACTS / "envelope" / "CHANGELOG.md").is_file()


# --- tests -------------------------------------------------------------------------


def test_every_test_lives_in_one_of_the_four_tiers():
    # CI selects by marker, so a test outside a tier is collected, counted as passing,
    # and never actually run by the gate. conftest.py turns this into a collection
    # error at runtime; this asserts the layout that makes that possible.
    strays = [p.name for p in (REPO / "tests").glob("test_*.py") if p.parent.name not in TIERS]
    assert strays == [], f"move these into tests/{{{','.join(TIERS)}}}/: {strays}"


def test_all_four_tiers_exist_and_none_is_empty():
    for tier in TIERS:
        directory = REPO / "tests" / tier
        assert directory.is_dir(), f"missing tier: tests/{tier}/"
        assert list(directory.glob("test_*.py")), f"tests/{tier}/ has no tests"


def test_the_evaluation_tier_carries_its_verification_report():
    # This is an infrastructure repository: most of what can go wrong cannot be reached
    # by a unit test, so the report is the primary QA artefact rather than a supplement.
    assert (REPO / "tests" / "evaluation" / "REPORT.md").is_file()


# --- the spec-driven layer -----------------------------------------------------------


def test_the_constitution_and_every_template_are_present():
    assert (REPO / ".specify" / "memory" / "constitution.md").is_file()
    templates = REPO / ".specify" / "templates"
    for name in ("spec", "plan", "tasks", "contract-change"):
        assert (templates / f"{name}-template.md").is_file(), f"missing {name}-template.md"


def test_every_spec_directory_is_numbered_and_complete():
    specs = sorted(d for d in (REPO / "specs").iterdir() if d.is_dir())
    assert specs, "specs/ must hold at least the record of how this layout arrived"
    for spec in specs:
        assert spec.name[:3].isdigit(), f"{spec.name} must start with a three-digit number"
        for required in ("spec.md", "plan.md", "tasks.md"):
            assert (spec / required).is_file(), f"{spec.name} is missing {required}"


def test_spec_numbers_are_unique():
    numbers = [d.name[:3] for d in (REPO / "specs").iterdir() if d.is_dir()]
    assert len(numbers) == len(set(numbers))


# --- decisions and governance --------------------------------------------------------


def test_adrs_are_numbered_without_gaps_or_duplicates():
    # A gap means an ADR was deleted rather than superseded, and a superseded decision
    # still has to be readable or the record is worse than none.
    adrs = (REPO / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")
    numbers = sorted(int(p.name[:4]) for p in adrs)
    assert numbers, "docs/adr/ must hold at least ADR 0001"
    assert numbers == list(range(1, len(numbers) + 1)), f"ADR numbering has a gap: {numbers}"


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "pyproject.toml",
        "uv.lock",
        "docker-compose.yml",
        ".env.example",
        "docker-compose.override.example.yml",
        ".github/CODEOWNERS",
        ".github/dependabot.yml",
    ],
)
def test_required_root_file_exists(path):
    assert (REPO / path).is_file(), f"missing {path}"


@pytest.mark.parametrize(
    "workflow", ["ci.yml", "contract-compat.yml", "broker-tiers.yml", "security.yml"]
)
def test_required_workflow_exists(workflow):
    assert (REPO / ".github" / "workflows" / workflow).is_file()


def test_local_compose_overrides_are_ignored_not_committed():
    # Compose merges .env and docker-compose.override.yml automatically from beside
    # docker-compose.yml. Committing either would apply one developer's local overrides
    # to everybody, silently. They may exist on a machine; they must never be tracked.
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignored
    assert "docker-compose.override.yml" in ignored


# --- scripts -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "script",
    [
        "export_schema.py",
        "check_compatibility.py",
        "render_topic_table.py",
        "new_spec.py",
        "validate-mermaid.mjs",
    ],
)
def test_required_script_exists(script):
    assert (REPO / "scripts" / script).is_file()


def test_python_scripts_use_underscores_so_the_contract_tier_can_import_them():
    offenders = [p.name for p in (REPO / "scripts").glob("*.py") if "-" in p.stem]
    assert offenders == [], f"rename to underscores; tests import these: {offenders}"
