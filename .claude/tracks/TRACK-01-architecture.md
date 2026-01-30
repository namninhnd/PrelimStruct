# Track 1: Architecture Foundation

> **Priority:** CRITICAL PATH
> **Start Wave:** 0 (Immediate)
> **Primary Agent:** backend-specialist
> **Status:** ✅ DONE (All tasks complete)

---

## Overview

Remove the simplified calculation method entirely and reorganize the FEM model flow to follow OpenSees BuildingTcl conventions. This track is the **critical path** - every other track (except Track 2: Bug Fixes) depends on its completion.

---

## Tasks

### Task 16.1: Remove Simplified Method Code
**Agent:** backend-specialist
**Model:** gemini-3-pro
**Wave:** 0 (Immediate)
**Dependencies:** NONE
**Status:** ✅ DONE (2026-01-26)

**Sub-tasks:**
- [x] 16.1.1: Audit `src/engines/` for simplified calculation code
- [x] 16.1.2: Remove simplified beam/column/slab calculation paths
- [x] 16.1.3: Update `SlabEngine`, `BeamEngine`, `ColumnEngine` to use FEM results only
- [x] 16.1.4: Remove `StructuralLayout` simplified calculation references
- [x] 16.1.5: Update `data_models.py` to remove simplified-only fields
- [x] 16.1.6: Update unit tests to reflect FEM-only approach

**Files Impacted:**
- `src/engines/slab_engine.py`
- `src/engines/beam_engine.py`
- `src/engines/column_engine.py`
- `src/engines/wind_engine.py`
- `src/core/data_models.py`
- `tests/test_feature1.py` (and related test files)

**Verification:**
- All tests pass after removal
- No references to "simplified" in calculation paths
- App runs without errors

**Exit Gate:** Unlocks Task 16.3 and Track 6 (Task 16.2)

---

### Task 16.3: Reorganize Model Flow (OpenSees Building Pattern)
**Agent:** backend-specialist
**Model:** opus
**Wave:** 1 (After 16.1)
**Dependencies:** Task 16.1 ✅
**Status:** ✅ DONE (2026-01-26)

**Sub-tasks:**
- [X] 16.3.1: Study OpenSees BuildingTcl pattern from reference
- [X] 16.3.2: Restructure `model_builder.py` to follow OpenSees conventions
- [X] 16.3.3: Separate model definition, loads, and analysis into distinct phases
- [X] 16.3.4: Implement proper node numbering scheme (floor-based)
- [X] 16.3.5: Add model validation before analysis
- [X] 16.3.6: Document new model structure in code comments

**Files Impacted:**
- `src/fem/model_builder.py` (major restructure)
- `src/fem/fem_engine.py`
- `tests/test_model_builder.py`
- `tests/test_fem_engine.py`

**References:**
- https://opensees.berkeley.edu/wiki/index.php?title=Getting_Started_with_BuildingTcl

**Verification:**
- Model builds following OpenSees conventions
- Node/element numbering is consistent and floor-based
- Model passes validation checks
- Existing tests updated and passing

**Exit Gate:** Unlocks Tracks 3, 4, 5 (all backend model work)

---

## Cross-Track Dependencies

| This Track Produces | Required By |
|---------------------|-------------|
| 16.1 complete (simplified removed) | Track 6: Task 16.2 (dashboard cleanup) |
| 16.3 complete (model flow reorganized) | Track 3: Task 17.1 (wall elements) |
| 16.3 complete | Track 4: Task 19.1 (slab elements) |
| 16.3 complete | Track 5: Task 20.1 (wind load cases) |

---

## Agent Instructions

When dispatching the backend-specialist for this track:

**Task 16.1 prompt:**
> Audit and remove all simplified calculation methods from the codebase. The project is transitioning to FEM-only (OpenSeesPy). Remove simplified paths from src/engines/, update data_models.py to remove simplified-only fields, and update all affected tests. Ensure the app still runs and all remaining tests pass. Do NOT touch src/fem/ module.

**Task 16.3 prompt:**
> Restructure src/fem/model_builder.py to follow OpenSees BuildingTcl conventions. Separate model definition, loads, and analysis into distinct phases. Implement proper floor-based node numbering. Add model validation before analysis. Study the OpenSees BuildingTcl pattern first. Update all related tests.

---

*Track Owner: Orchestrator*
*Last Updated: 2026-01-26*
