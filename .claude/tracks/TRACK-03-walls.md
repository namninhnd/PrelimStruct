# Track 3: Wall Modeling (ShellMITC4 + Plate Fiber Section)

> **Priority:** P0 (MUST) - Critical Path
> **Start Wave:** 2 (After Track 1 completes)
> **Primary Agents:** backend-specialist, frontend-specialist, debugger
> **Status:** ✅ COMPLETE (All tasks + regressions done 2026-01-29)

---

## Overview

Implement proper shell element wall modeling using ShellMITC4 with Plate Fiber Section and NDMaterial. This replaces the simplified beam-element wall representation with accurate shell behavior for stress distribution and coupled wall effects.

---

## External Dependencies (Must Be Complete Before Start)

| Dependency | Track | Task | Reason |
|------------|-------|------|--------|
| Model flow reorganized | Track 1 | 16.3 | model_builder.py must be restructured first |
| Coupling beam fix | Track 2 | 17.4 | Wall-coupled beams must work correctly |

---

## Tasks

### Task 17.1: Implement ShellMITC4 Wall Elements with Plate Fiber Section
**Agent:** backend-specialist
**Model:** opus
**Wave:** 2
**Dependencies:** Track 1 (16.3 complete) ✅
**Status:** ✅ DONE (2026-01-26)

**Sub-tasks:**
- [ ] 17.1.1: Study ShellMITC4 element and Plate Fiber Section documentation
- [ ] 17.1.2: Create `WallElement` class in `src/fem/wall_element.py`
- [ ] 17.1.3: Implement NDMaterial for concrete (PlaneStressUserMaterial or similar)
- [ ] 17.1.4: Implement Plate Fiber Section with fiber layers (cover + core concrete, steel)
- [ ] 17.1.5: Create wall mesh with ShellMITC4 quad elements
- [ ] 17.1.6: Add wall-to-beam connection logic (rigid links at floor levels)
- [ ] 17.1.7: Integrate wall elements into `model_builder.py`
- [ ] 17.1.8: Add unit tests for wall element creation
- [ ] 17.1.9: Validate against reference solutions

**Files Impacted:**
- `src/fem/wall_element.py` (NEW)
- `src/fem/model_builder.py` (integration)
- `src/fem/materials.py` (NDMaterial additions)
- `src/fem/fem_engine.py` (wall element support)
- `tests/test_wall_element.py` (NEW)

**References:**
- https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
- https://opensees.berkeley.edu/wiki/index.php/Shell_Element
- https://opensees.berkeley.edu/wiki/index.php?title=Plate_Fiber_Section
- https://opensees.berkeley.edu/wiki/index.php?title=NDMaterial_Command

**Verification:**
- Wall shell elements created in OpenSeesPy model
- Plate fiber section properly defines through-thickness behavior
- Stress distribution matches expected behavior
- Unit tests pass with >90% coverage

**Exit Gate:** Unlocks Tasks 17.3 and Track 4 (19.1)

---

### Task 17.2: Custom Core Wall Location Input
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 2 (Can parallel with 17.1)
**Dependencies:** Track 6 (16.2 complete - dashboard cleaned up)
**Status:** DONE (2026-01-29)

**Sub-tasks:**
- [x] 17.2.1: Add "Custom" option to core wall location dropdown
- [x] 17.2.2: Create input fields for centroid X, Y coordinates (m)
- [x] 17.2.3: Validate centroid is within building footprint
- [x] 17.2.4: Update `LateralInput` model with custom centroid fields (R4 fix)
- [x] 17.2.5: Update framing plan visualization to show custom location
- [x] 17.2.6: Add tooltip explaining coordinate system

**Implementation Notes:**
- Custom position UI now works for ALL core wall configs (I-Section, C-Wall, TUBE)
- Edge validation warns when core may extend outside building
- Coordinate system tooltip explains origin at bottom-left
- Unique radio widget keys prevent Streamlit conflicts

**Files Impacted:**
- `app.py` (lines 1210-1287 for I-Section/C-Wall, 1316-1398 for TUBE)

**Verification:**
- Custom location option appears in dropdown
- Validation prevents invalid coordinates
- Visualization updates in real-time

---

### Task 17.3: Auto-Omit Columns Near Core Walls (MODIFIED)
**Agent:** mixed (backend-sonnet / frontend-sonnet)
**Model:** sonnet
**Wave:** 3 (After 17.1)
**Dependencies:** Task 17.1 ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 17.3.1: Implement proximity detection algorithm (0.5m threshold, shapely)
- [ ] 17.3.2: Create `_suggest_column_omissions()` function in `model_builder.py`
- [ ] 17.3.3: Generate user-reviewable omission list (pre-generation)
- [ ] 17.3.4: Implement column filter based on user-approved list
- [ ] 17.3.5: Add beam trimming logic to connect to wall edge nodes (fixed connection)
- [ ] 17.3.6: Render mandatory ghost columns (grey dashed outline) at omitted locations
- [ ] 17.3.7: Add omission review UI with checkbox list in sidebar
- [ ] 17.3.8: Log omitted columns in analysis summary

**Files Impacted:**
- `src/fem/model_builder.py` (detection, suggestion, filtering, beam trimming)
- `src/fem/visualization.py` (ghost columns - mandatory)
- `app.py` (omission review UI with checkboxes)
- `tests/test_model_builder.py` (proximity, beam connections, integration tests)

**Verification:**
- Columns within 0.5m of core walls appear in suggestion list
- User can review and modify omission list via checkboxes
- Ghost columns (grey dashed) render at omitted locations
- Beams trim to wall edges with fixed connections
- Integration test validates complete workflow

**Related Documents:**
- See: `task_17_3_modified.md` for detailed implementation plan
- See: `orchestrator_note_wall_constraints.md` for wall geometry constraints

---

### Task 17.3b: Slab Regeneration After Column Omission (NEW)
**Agent:** backend-specialist
**Model:** sonnet
**Wave:** 3 (Parallel with or after 17.3)
**Dependencies:** Task 17.3 ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 17.3b.1: Create `_requires_slab_regeneration()` detection function
- [ ] 17.3b.2: Implement slab element deletion logic (preserve shared nodes)
- [ ] 17.3b.3: Create `_compute_slab_boundaries()` with wall edge trimming
- [ ] 17.3b.4: Regenerate slab mesh with updated boundaries
- [ ] 17.3b.5: Verify slab-to-wall connectivity (tolerance check)
- [ ] 17.3b.6: Add regeneration notification in UI

**Files Impacted:**
- `src/fem/model_builder.py` (deletion, boundary update, regeneration)
- `app.py` (regeneration notification)
- `tests/test_model_builder.py` (deletion, boundary update, regeneration tests)

**Verification:**
- Slabs regenerate when columns are omitted within panel boundaries
- Slab edge nodes align with wall edge nodes (tolerance < 1e-6)
- No floating slab elements remain
- UI displays regeneration notification

**Related Documents:**
- See: `task_17_3b_slab_regeneration.md` for detailed implementation plan

---

### Task 17.5: Slab Subdivision for Secondary Beams (NEW)
**Agent:** backend-specialist
**Model:** sonnet
**Wave:** 3 (After 17.3b)
**Dependencies:** Task 17.3b ✅
**Status:** ✅ DONE (2026-01-28)

**Description:**
Subdivide major slab panels into strip panels based on secondary beam configuration. Ensures slab-to-beam connectivity at intermediate support points.

**Files Impacted:**
- `src/fem/model_builder.py` (subdivision logic)
- `tests/test_slab_subdivision.py` (NEW)

**Verification:**
- Slabs subdivide correctly based on `num_secondary_beams`
- Strip panel edges align with secondary beam nodes
- Visual verification in Plan View

---

## Regression Fixes (Discovered 2026-01-28)

> [!CAUTION]
> These 4 issues were discovered during Task 17.2 testing. They affect core wall integration and must be fixed before 17.2 can be marked complete.

### R4: Fix Custom Core Wall Position Bug
**Agent:** debugger
**Model:** sonnet
**Skills:** @[systematic-debugging]
**Priority:** 🔴 P0 (blocking 17.2)
**Status:** DONE (2026-01-29)

**Problem:** Setting "Position Type" to "Custom" with X/Y coordinates does not move the core wall in the FEM view.

**Root Cause:** Two bugs in app.py:
1. Line 1288: Unconditional reset overwrote Custom selection for I-Section/C-Wall
2. Lines 1510-1522: LateralInput constructor missing location_type, custom_center_x, custom_center_y params

**Fix Applied:**
- Added default initialization (lines 1147-1151)
- Changed unconditional reset to conditional for TUBE only (lines 1289-1294)
- Added parameters to LateralInput constructor (lines 1510-1522)

**Files:** `app.py`
**Verified:** 38/38 model_builder tests pass, 16/16 core_wall tests pass

---

### R2: Implement Coupling Beams
**Agent:** backend-specialist
**Model:** sonnet
**Skills:** @[architecture], @[clean-code]
**Priority:** 🔴 P0 (structurally critical)
**Status:** DONE (2026-01-29)

**Problem:** Core walls with openings (I-Section, C-Wall) show no coupling beams.

**Root Cause:** CouplingBeamGenerator class existed but was never called in build_fem_model().

**Fix Applied:**
- Added import for CouplingBeamGenerator (line 40)
- Added coupling beam generation logic after wall mesh creation (lines 1358-1457)
- Beams generated at each floor level for walls with openings
- Proper node creation and connection to wall mesh

**Verified:** 
- TWO_C_FACING: 1 beam/floor, TWO_C_BACK_TO_BACK: 2 beams/floor
- TUBE_CENTER_OPENING: 1 beam/floor, TUBE_SIDE_OPENING: 1 beam/floor
- I_SECTION: 0 beams (no openings expected)

**Files:** `src/fem/model_builder.py`

---

### R1: Beam Trimming at Wall Boundaries
**Agent:** backend-specialist
**Model:** sonnet
**Skills:** @[clean-code]
**Priority:** 🟡 P1
**Status:** DONE (2026-01-29)

**Problem:** Beams extend through core wall region instead of stopping at wall edges.

**Root Cause:** Secondary beams were not calling trim_beam_segment_against_polygon() - only primary gridline beams had intersection checks.

**Fix Applied:**
- Added beam trimming logic for secondary beams (lines 1177-1340)
- Calls trim_beam_segment_against_polygon() for each secondary beam segment
- Handles trimming results, skips short segments
- Creates nodes at trimmed endpoints
- Added 2 new tests for secondary beam trimming

**Verified:** 67/67 related tests pass (model_builder, beam_trimmer, wall integration, fem_engine)

**Files:** `src/fem/model_builder.py`, `tests/test_model_builder.py`

---

### R3: Slab Infill Near Walls
**Agent:** backend-specialist
**Model:** sonnet
**Skills:** @[clean-code]
**Priority:** 🟡 P1
**Status:** CLOSED - NO ISSUE (2026-01-29)

**Problem:** Reported that slabs dont fill gap between beam grid and core wall edge.

**Investigation Result:** NO GAP ISSUE EXISTS
- Slabs correctly extend to core wall boundaries
- Only interior void (elevator/stair shaft) is excluded
- Wall thickness zone IS covered by slabs
- Nodes shared with wall elements for structural connection

**Evidence:**
- Manual geometry verification passed for both aligned and misaligned core scenarios
- test_slab_wall_connectivity.py passed
- _get_core_opening_for_slab() correctly returns only interior void

**Bonus:** Fixed 23 test synchronization issues during investigation (enum values, trace names)

---

## Internal Dependency Chain

```
17.1 (Wall elements) ──┬──> 17.3 (Auto-omit columns with user review) ──> 17.3b (Slab regeneration)
                       │
                       └──> Wall Constraint Validation (geometry bounds check)
17.2 (Wall location UI) -- parallel with 17.1
```

**Critical Path Notes:**
- **17.3 requires wall constraint validation** (see `orchestrator_note_wall_constraints.md`)
- **17.3b triggers after 17.3** (slab regeneration only when columns are omitted)

---

## Cross-Track Dependencies

| This Track Produces | Required By |
|---------------------|-------------|
| 17.1 complete (wall elements in model) | Track 4: 19.1 (slab elements, model_builder.py access) |
| 17.3 complete (column omission with user review) | Track 8: testing coverage |
| 17.3b complete (slab regeneration after omission) | Track 8: integration testing |

---

## Agent Instructions

**Task 17.1 prompt (backend-specialist):**
> Implement ShellMITC4 wall elements with Plate Fiber Section for the FEM model. Create a new WallElement class in src/fem/wall_element.py. Implement NDMaterial for concrete, Plate Fiber Section with fiber layers, and wall mesh with ShellMITC4 quad elements. Add wall-to-beam connection via rigid links at floor levels. Integrate into model_builder.py. Study the OpenSees documentation links provided in PRD.md Feature 17. Write comprehensive unit tests.

**Task 17.2 prompt (frontend-specialist):**
> Add a "Custom" option to the core wall location dropdown in app.py. When selected, show X/Y centroid coordinate inputs (meters). Validate that coordinates fall within the building footprint. Update the LateralInput model in data_models.py. Update the framing plan visualization to render the core wall at the custom location.

**Task 17.3 prompt (backend-specialist):** *(MODIFIED)*
> In model_builder.py, implement a proximity detection algorithm (0.5m threshold) that identifies columns near core wall geometry using shapely. Create a suggestion list that users can review via checkbox UI in app.py before model generation. Implement column filtering based on user-approved omissions. Add beam trimming logic to connect beams to nearest wall edge nodes with fixed connections (non-coupling beams). Render mandatory ghost columns (grey dashed outline) at omitted locations in visualization.py. See task_17_3_modified.md for full specification.

**Task 17.3b prompt (backend-specialist):** *(NEW)*
> Implement slab regeneration workflow after column omissions. In model_builder.py, create detection logic to identify when slabs need regeneration, delete existing slab elements (preserving shared nodes), compute updated slab boundaries trimmed to wall edges, and regenerate slab mesh with proper connectivity. Verify slab edge nodes align with wall edge nodes (tolerance < 1e-6). Add UI notification when regeneration occurs. See task_17_3b_slab_regeneration.md for full specification.

---

*Track Owner: Orchestrator*
*Last Updated: 2026-01-27 (Tasks 17.3 & 17.3b modified)*
