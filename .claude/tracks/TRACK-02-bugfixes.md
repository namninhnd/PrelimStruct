# Track 2: Bug Fixes

> **Priority:** HIGH (Independent)
> **Start Wave:** 0 (Immediate)
> **Primary Agents:** debugger, frontend-specialist
> **Status:** ✅ 17.4, 18.1, 18.2 DONE

---

## Overview

Fix two critical bugs that exist in V3.0: coupling beam NoneType error and missing secondary beams. These are independent of the architecture refactor and can start immediately.

---

## Tasks

### Task 17.4: Fix Coupling Beam Generation Error
**Agent:** debugger
**Model:** sonnet
**Wave:** 0 (Immediate)
**Dependencies:** NONE
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 17.4.1: Reproduce NoneType division error in test case
- [ ] 17.4.2: Trace error to source in `coupling_beam.py`
- [ ] 17.4.3: Add null checks for wall geometry parameters
- [ ] 17.4.4: Fix calculation when opening dimensions are None
- [ ] 17.4.5: Add unit tests for edge cases (no openings, zero dimensions)
- [ ] 17.4.6: Verify coupling beam appears in visualization

**Files Impacted:**
- `src/fem/coupling_beam.py`
- `src/fem/core_wall_geometry.py` (investigation)
- `tests/test_coupling_beam.py`

**Verification:**
- No error when generating coupling beams
- Coupling beams display correctly for all core wall types
- Unit tests cover edge cases

---

### Task 18.1: Debug Secondary Beam Generation
**Agent:** debugger
**Model:** sonnet
**Wave:** 0 (Immediate)
**Dependencies:** NONE
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 18.1.1: Trace secondary beam creation in `model_builder.py`
- [ ] 18.1.2: Identify why secondary beams are skipped
- [ ] 18.1.3: Fix beam generation logic for Y-direction spans
- [ ] 18.1.4: Ensure secondary beams connect to primary beams
- [ ] 18.1.5: Add secondary beams to visualization

**Files Impacted:**
- `src/fem/model_builder.py` (read + targeted fix)
- `src/fem/visualization.py` (add secondary beam rendering)
- `tests/test_model_builder.py`

**Verification:**
- Secondary beams appear in plan view
- Secondary beams connect properly to primary beams
- Model statistics show correct beam count

---

### Task 18.2: Beam Visualization Color/Legend
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 0 (Immediate)
**Dependencies:** 18.1 (secondary beams exist) ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 18.2.1: Differentiate primary vs secondary beams in visualization (color/style)
- [ ] 18.2.2: Add legend entry for secondary beams
- [ ] 18.2.3: Show beam type in hover tooltip

**Files Impacted:**
- `src/fem/visualization.py`

**Verification:**
- Primary and secondary beams visually distinct
- Legend shows both beam types
- Tooltip displays beam type

---

## Parallelism Within Track

```
17.4 ──────────────────┐
                        ├─> (both independent, parallel)
18.1 ─────> 18.2 ──────┘
```

Tasks 17.4 and 18.1 can run in parallel (different files). Task 18.2 waits for 18.1.

---

## Cross-Track Dependencies

| This Track Produces | Required By |
|---------------------|-------------|
| 18.1 complete (secondary beams fixed) | Track 6: visualization works correctly |
| 17.4 complete (coupling beams fixed) | Track 3: wall modeling builds on working coupling beams |

---

## Agent Instructions

**Task 17.4 + 18.1 prompt (debugger):**
> Investigate and fix two independent bugs:
> 1. Coupling beam NoneType division error in src/fem/coupling_beam.py. Reproduce the error, trace the root cause, add null checks, and write edge-case tests.
> 2. Secondary beams not appearing in FEM preview. Trace the beam generation in src/fem/model_builder.py, identify why Y-direction secondary beams are skipped, fix the logic, and verify they appear in visualization.
> Work on both bugs, starting with whichever is easier to reproduce first. Write tests for both.

**Task 18.2 prompt (frontend-specialist):**
> In src/fem/visualization.py, differentiate primary and secondary beams visually. Use different colors or line styles. Add a legend entry for each beam type. Add beam type to the hover tooltip. Secondary beams should now exist in the model after the bug fix.

---

*Track Owner: Orchestrator*
*Last Updated: 2026-01-26*
