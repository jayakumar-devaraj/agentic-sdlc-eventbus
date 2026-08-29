# Change: Operational drift detected in p95_latency_ms: reference 180.0, current 402.5, relative change 123.6%, threshold 25.0%. Investigate the regression and remediate it.

**Scenario:** brownfield

## Design
Change scoped to existing file(s): tests/test_envelope.py. Modify in place to satisfy 'Operational drift detected in p95_latency_ms: reference 180.0, current 402.5, relative change 123.6%, threshold 25.0%. Investigate the regression and remediate it.' without changing public API signatures unless the impacted file is itself an API module.

## Generated files

- `demo_generated.py` - """Added by an agentic-sdlc control-plane run."""
- `tests/test_demo_generated.py`

## Tasks
- [T1] Implement: Change scoped to existing file(s): tests/test_envelope.py. Modify in place to satisfy 'Operational drift detected in p95_latency_ms: reference 180.0, current 402.5, relative change 123.6%, threshold 25.0%. Investigate the regression and remediate it.' without changing public API signatures unless the impacted file is itself an API module. (depends on: none)
- [T2] Write/update unit tests for the change (depends on: T1)
- [T3] Update the target service's documentation for the change (depends on: T1)
- [T4] Run guardrail checks and prepare for release (depends on: T2, T3)