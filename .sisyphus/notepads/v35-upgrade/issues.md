# V3.5 Upgrade Issues & Blockers

## Active Issues

### Issue-001: Coupling Beam NoneType Bug
**Status**: Under investigation (Task 1)
**Symptom**: Division by None in coupling beam generation
**Suspected Cause**: Missing geometry values or uninitialized dimensions
**Impact**: Blocks Tasks 4, 5

## Potential Blockers

### Blocker-001: ETABS Access
**Risk**: Need ETABS software access for validation baseline
**Mitigation**: Task 2 creates building definitions; ETABS analysis is manual
**Status**: Accepted - manual process documented

### Blocker-002: Shell Element Validation
**Risk**: Shell elements may not match ETABS within 10% tolerance
**Mitigation**: Early validation in Wave 1, time buffer built into plan
**Status**: Monitoring

## Resolved Issues

### Issue-001: Coupling Beam NoneType Bug
**Status**: RESOLVED (Task 1)
**Resolution**: Added null checks before division operations in coupling beam generation

### Issue-002: pytest_playwright Missing
**Status**: KNOWN ISSUE (Task 16)
**Resolution**: Made plugin optional in conftest.py with try/except

### Issue-003: Engine Test Failures
**Status**: EXPECTED (Task 3)
**Resolution**: Tests reference removed simplified engines - need cleanup for v3.6

## Test Failures to Address in v3.6

### High Priority
1. `test_coupling_beam.py::TestCouplingBeamEngine::*` (15 tests) - CouplingBeamEngine removed with simplified engines
2. `test_slab_subdivision.py` (2 tests) - Require wind_result with WindEngine (removed)
3. `test_slab_wall_connectivity.py` (1 test) - Same as above

### Low Priority
4. `test_visualization_plan_view.py::test_plan_view_without_utilization_uses_default_beam_color` - Theme color changed

### Environment-Specific
5. `tests/ui/test_mobile.py` (3 tests) - Require pytest-playwright

## Session Log

### 2026-02-03
- Started Wave 1 parallel execution
- Tasks 1, 2, 3 dispatched simultaneously
- Task 16: Final Integration Testing completed
  - 927/949 tests passed (97.7% pass rate)
  - 7 test files skipped (removed engine imports)
  - 19 expected failures documented
  - 3 playwright errors (missing dependency)
  - ETABS validation: 5 test cases defined
  - End-to-end workflow: VERIFIED
