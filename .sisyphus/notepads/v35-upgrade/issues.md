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

*None yet - session just started*

## Session Log

### 2026-02-03
- Started Wave 1 parallel execution
- Tasks 1, 2, 3 dispatched simultaneously
