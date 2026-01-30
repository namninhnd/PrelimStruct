# Track 4: Slab Modeling (ShellMITC4 + Elastic Membrane Plate Section)

> **Priority:** P0 (MUST) - Critical Path
> **Start Wave:** 3 (After Track 3 Task 17.1 completes)
> **Primary Agents:** backend-specialist, frontend-specialist
> **Status:** ✅ 19.1, 19.2, 19.3, 20.5, 20.5a DONE

---

## Overview

Implement ShellMITC4 shell elements with Elastic Membrane Plate Section for floor slabs. Includes slab panel detection from beam layout, mesh generation, and surface load application. Task 20.5 (surface loads) is included here because it directly depends on slab elements.

---

## External Dependencies (Must Be Complete Before Start)

| Dependency | Track | Task | Reason |
|------------|-------|------|--------|
| Model flow reorganized | Track 1 | 16.3 | model_builder.py restructured |
| Wall elements integrated | Track 3 | 17.1 | Avoid model_builder.py conflict; walls first |

---

## Tasks

### Task 19.1: Implement ShellMITC4 Slab Elements
**Agent:** backend-specialist
**Model:** opus
**Wave:** 3
**Dependencies:** Track 3 (17.1 complete) ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 19.1.1: Study ShellMITC4 element documentation
- [ ] 19.1.2: Create `SlabElement` class in `src/fem/slab_element.py`
- [ ] 19.1.3: Implement Elastic Membrane Plate Section material
- [ ] 19.1.4: Create slab mesh generation (quad elements)
- [ ] 19.1.5: Ensure slab nodes align with beam nodes (connectivity)
- [ ] 19.1.6: Integrate slab elements into `model_builder.py`
- [ ] 19.1.7: Add unit tests for slab element creation

**Files Impacted:**
- `src/fem/slab_element.py` (NEW)
- `src/fem/model_builder.py` (integration)
- `src/fem/materials.py` (Elastic Membrane Plate Section)
- `tests/test_slab_element.py` (NEW)

**References:**
- https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
- https://opensees.berkeley.edu/wiki/index.php/Elastic_Membrane_Plate_Section

**Verification:**
- Slab shell elements created in OpenSeesPy model
- Nodes shared between slabs and beams
- Mesh quality meets standards (aspect ratio < 5)

**Exit Gate:** Unlocks Tasks 19.2 and 20.5

---

### Task 19.2: Slab Panel Detection from Beams
**Agent:** backend-specialist
**Model:** opus
**Wave:** 4 (After 19.1)
**Dependencies:** Task 19.1 ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 19.2.1: Create algorithm to detect slab panels bounded by beams
- [ ] 19.2.2: Handle irregular panel shapes (L-shaped, openings)
- [ ] 19.2.3: Generate mesh for each panel independently
- [ ] 19.2.4: Handle slab openings (stairs, elevators)
- [ ] 19.2.5: Ensure continuity across panel boundaries

**Files Impacted:**
- `src/fem/model_builder.py` (panel detection logic)
- `src/fem/slab_element.py` (mesh refinement)
- `tests/test_model_builder.py`

**Verification:**
- Slab panels correctly detected from beam layout
- Mesh generated for each panel
- No gaps or overlaps between panels

---

### Task 20.5: Surface Load on Slabs
**Agent:** backend-specialist
**Model:** sonnet
**Wave:** 4 (After 19.1, parallel with 19.2)
**Dependencies:** Task 19.1 (slab elements exist) ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 20.5.1: Implement OpenSees SurfaceLoad element
- [ ] 20.5.2: Apply distributed load to slab shell elements
- [ ] 20.5.3: Display load as kPa (kN/m2) in UI
- [ ] 20.5.4: Remove nodal load approach from slabs
- [ ] 20.5.5: Verify load distribution is correct

**Files Impacted:**
- `src/fem/model_builder.py` (load application)
- `src/fem/load_combinations.py` (surface load integration)
- `app.py` (kPa display)

**Reference:** https://opensees.berkeley.edu/wiki/index.php/SurfaceLoad_Element

**Verification:**
- Surface loads applied to slab elements
- Load displayed in kPa units
- Total load equals expected value

---

### Task 20.5a: Surface Load UI Display (Unit Conversion)
**Agent:** frontend-specialist
**Model:** gemini-3-pro
**Wave:** 4 (After 20.5)
**Dependencies:** Task 20.5 (surface loads implemented) ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 20.5a.1: Add surface load display in FEM Preview tooltips (Pa → kPa conversion)
- [ ] 20.5a.2: Add "Slab Design Load" metric in sidebar (kPa display)
- [ ] 20.5a.3: Update model summary to show surface load count
- [ ] 20.5a.4: Add surface load visualization (optional: show load vectors on slabs)

**Files Impacted:**
- `src/fem/visualization.py` (tooltip conversion)
- `app.py` (sidebar display, FEM preview)

**Important Note:**
- Surface loads are stored in **Pa (N/m²)** in `SurfaceLoad.pressure`
- **For display, convert to kPa**: `display_value_kpa = pressure_pa / 1000.0`
- This maintains UI consistency with beam loads and design inputs

**Verification:**
- Slab hover tooltips show load in kPa
- Sidebar displays slab design load
- Units are consistent across UI

---

### Task 19.3: Slab Visualization Update
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 5 (After 19.2)
**Dependencies:** Task 19.2 (panels detected) ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 19.3.1: Add slab mesh visualization in plan view
- [ ] 19.3.2: Show slab stress contours after analysis
- [ ] 19.3.3: Add toggle to show/hide slab elements
- [ ] 19.3.4: Display slab thickness in hover tooltip

**Files Impacted:**
- `src/fem/visualization.py`
- `app.py` (toggle control)

**Verification:**
- Slab mesh visible in plan view
- Stress contours display after analysis
- Toggle works correctly

---

## Internal Dependency Chain

```
19.1 (Slab elements) ──> 19.2 (Panel detection) ──> 19.3 (Visualization)
          |
          └──> 20.5 (Surface loads) -- parallel with 19.2
```

---

## Cross-Track Dependencies

| This Track Produces | Required By |
|---------------------|-------------|
| 19.1 complete (slabs in model) | Track 5: 20.5 (surface loads) - included here |
| 19.2 complete (panels detected) | Track 6: 21.4 (calculation tables include slab results) |
| All tasks complete | Track 8: 23.1 (slab element unit tests) |

---

## Agent Instructions

**Task 19.1 prompt (backend-specialist):**
> Create ShellMITC4 slab elements with Elastic Membrane Plate Section. Create a new SlabElement class in src/fem/slab_element.py. Generate quad element mesh for slab regions. Ensure slab nodes align with beam nodes for proper connectivity. Integrate into model_builder.py. The wall elements (Track 3) are already integrated - follow the same pattern. Write unit tests.

**Task 19.2 prompt (backend-specialist):**
> Create an algorithm to detect slab panels bounded by beams in the floor plan. Handle irregular shapes (L-shaped, with openings for stairs/elevators). Generate mesh for each panel independently. Ensure continuity across panel boundaries. Work in model_builder.py and slab_element.py.

**Task 20.5 prompt (backend-specialist):**
> Implement OpenSees SurfaceLoad element to apply distributed loads (kPa) to slab shell elements. Replace the current nodal load approach for slabs. Integrate with load_combinations.py. Verify total load equals expected value. Reference: https://opensees.berkeley.edu/wiki/index.php/SurfaceLoad_Element

**Task 19.3 prompt (frontend-specialist):**
> Add slab mesh visualization to the plan view in visualization.py. Show stress contours after analysis. Add a show/hide toggle in app.py. Display slab thickness in hover tooltips.

---

*Track Owner: Orchestrator*
*Last Updated: 2026-01-26*
