# PrelimStruct V3.5 Upgrade Work Plan

## TL;DR

> **Quick Summary**: Transform PrelimStruct from hybrid (simplified+FEM) to pure FEM architecture with ShellMITC4 elements for walls/slabs, 60 HK Code load combinations, redesigned UI per wireframes, and reaction export functionality.
> 
> **Deliverables**:
> - Pure FEM-only architecture (remove simplified engines)
> - ShellMITC4 shell elements for walls and slabs (activated)
> - 60 load combinations visible in UI with scrollable list
> - Reaction export table (CSV/Excel)
> - Redesigned UI per user wireframes
> - ETABS validation report for 3-5 test buildings
> 
> **Estimated Effort**: Medium-Large (~35-45 days)
> **Parallel Execution**: YES - 5 waves
> **Critical Path**: Validation Baseline → Shell Activation → Load Combo UI → Reaction Export → UI Polish

---

## Context

### Original Request
Upgrade PrelimStruct from v3.0 to v3.5 per PRD.md requirements, transforming it from a hybrid simplified/FEM platform to a pure FEM-based structural analysis tool for Hong Kong tall buildings.

### Interview Summary
**Key Discussions**:
- **Migration**: Breaking change acceptable (v3.0 projects won't load in v3.5)
- **Validation**: ETABS comparison for shell element accuracy
- **AI Chat**: Deferred to v3.6 (reduces scope and risk)
- **UI**: User has wireframes ready for implementation
- **Size Limit**: 30 floors maximum (conservative for preliminary tool)

**Research Findings**:
- Shell element infrastructure (WallMeshGenerator, SlabMeshGenerator) exists but is not activated
- 60 load combinations already defined in `load_combinations.py`
- Coupling beam has NoneType division bug (needs root cause analysis)
- UI audit score: 6.5/10 "Functional but forgettable"
- Backend ~62% ready, Frontend ~40% ready

### Metis Review
**Identified Gaps** (addressed):
- Added validation baseline phase before implementation
- Added 30% time buffer for unknowns
- Defined explicit scope guardrails (MUST NOT list)
- Added acceptance criteria with executable verification
- Documented edge cases and limitations

---

## Work Objectives

### Core Objective
Transform PrelimStruct into a pure FEM-based structural analysis platform with ShellMITC4 elements, full HK Code load combinations, and professional UI/UX.

### Concrete Deliverables
1. `src/fem/model_builder.py` using ShellMITC4 elements for walls/slabs
2. `app.py` UI redesigned per user wireframes
3. Reaction export table component with CSV/Excel download
4. Load combination scrollable list with multi-select
5. ETABS validation report (`VALIDATION_REPORT.md`)
6. Migration guide (`MIGRATION.md`) for v3.0 users

### Definition of Done
- [ ] `pytest tests/` → 100% pass (all 265+ tests)
- [ ] `python scripts/validate_shell_elements.py` → All cases within 10% of ETABS
- [ ] Manual verification: Core wall selector visible on page load
- [ ] Manual verification: FEM views above fold without scrolling
- [ ] `python -c "from src.engines import *"` → ImportError (engines removed)

### Must Have
- ShellMITC4 elements for walls (Plate Fiber Section)
- ShellMITC4 elements for slabs (Elastic Membrane Plate Section)
- 60 load combinations visible in scrollable UI
- Reaction export to CSV/Excel
- ETABS validation for 3-5 buildings

### Must NOT Have (Guardrails)
- NO backward compatibility with v3.0 projects (breaking change)
- NO AI Chat (F22 deferred to v3.6)
- NO custom load combination builder
- NO user-drawn walls or custom polygons
- NO slab openings or varying thickness
- NO undo/redo system (too complex)
- NO mobile-optimized responsive design
- NO element types beyond ShellMITC4
- NO nonlinear analysis (linear static only)
- NO buildings > 30 floors

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest, 265+ tests)
- **User wants tests**: TDD where practical, tests-after for UI
- **Framework**: pytest (existing)

### Automated Verification Approach

| Deliverable Type | Verification Tool | Method |
|------------------|-------------------|--------|
| Shell Elements | `pytest` + custom validation script | Compare to ETABS results |
| Load Combinations | `pytest tests/test_load_combinations.py` | Unit tests for factors |
| UI Changes | Playwright automation | Screenshot comparison |
| Reaction Export | `pytest` + manual CSV inspection | Verify data integrity |
| Engine Removal | `python -c "from src.engines import *"` | Expect ImportError |

### ETABS Validation Protocol
Create 3-5 test buildings:
1. Simple 10-story with I-Section core
2. 20-story with Two-C-Facing core
3. 30-story with Tube core (max limit)
4. Edge case: Maximum bays (10x10)
5. Edge case: Minimum configuration

Compare: Displacements (±5%), Member forces (±10%), Reactions (±5%)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately) - Foundation:
├── Task 1: Root cause analysis - coupling beam bug
├── Task 2: Create ETABS validation baseline (3-5 buildings)
└── Task 3: Remove simplified engine files

Wave 2 (After Wave 1) - Shell Elements:
├── Task 4: Activate ShellMITC4 for walls
├── Task 5: Activate ShellMITC4 for slabs
└── Task 6: Update model_builder.py integration

Wave 3 (After Wave 2) - Load System:
├── Task 7: Load combination UI overhaul
├── Task 8: Implement reaction export table
└── Task 9: Surface load on shell slabs

Wave 4 (After Wave 3) - UI/UX:
├── Task 10: Apply wireframes to app.py
├── Task 11: Relocate FEM views section
├── Task 12: Visual core wall selector
└── Task 13: Fix mobile viewport overlay

Wave 5 (After Wave 4) - Polish:
├── Task 14: Write MIGRATION.md
├── Task 15: Write VALIDATION_REPORT.md
├── Task 16: Final integration testing
└── Task 17: Performance benchmarking
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 4, 5 | 2, 3 |
| 2 | None | 16 | 1, 3 |
| 3 | None | 4, 5 | 1, 2 |
| 4 | 1, 3 | 6, 9 | 5 |
| 5 | 1, 3 | 6, 9 | 4 |
| 6 | 4, 5 | 7, 8, 9 | None |
| 7 | 6 | 10 | 8, 9 |
| 8 | 6 | 10 | 7, 9 |
| 9 | 4, 5 | 16 | 7, 8 |
| 10 | 7, 8 | 11, 12 | None |
| 11 | 10 | 16 | 12, 13 |
| 12 | 10 | 16 | 11, 13 |
| 13 | 10 | 16 | 11, 12 |
| 14 | None | 16 | 1-13 |
| 15 | 2, 16 | None | 14 |
| 16 | 6, 9, 11, 12, 13 | 15, 17 | 14 |
| 17 | 16 | None | 15 |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2, 3 | debugger, test-engineer, backend-specialist |
| 2 | 4, 5, 6 | backend-specialist (parallel dispatch) |
| 3 | 7, 8, 9 | frontend-specialist, backend-specialist |
| 4 | 10-13 | frontend-specialist (all) |
| 5 | 14-17 | documentation-writer, test-engineer |

---

## TODOs

### Wave 1: Foundation

---

- [ ] 1. Root Cause Analysis: Coupling Beam NoneType Bug

  **What to do**:
  - Trace NoneType division error in `src/fem/coupling_beam.py`
  - Identify where None value originates (geometry? user input?)
  - Add null checks before division operations
  - Add unit tests for edge cases (no openings, zero dimensions)
  - Verify coupling beam appears in visualization after fix

  **Must NOT do**:
  - Refactor entire coupling beam module (only fix the bug)
  - Change coupling beam geometry calculations if working

  **Recommended Agent Profile**:
  - **Category**: `debugger`
    - Reason: Root cause analysis and bug fixing
  - **Skills**: [`systematic-debugging`]
    - `systematic-debugging`: 4-phase debugging methodology

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: None

  **References**:
  - `src/fem/coupling_beam.py` - CouplingBeamGenerator class with bug
  - `src/fem/core_wall_geometry.py` - CoreWallGeometry providing dimensions
  - `tests/test_coupling_beam.py` - Existing tests (if any)

  **Acceptance Criteria**:
  ```bash
  # Reproduce the bug first
  python -c "from src.fem.coupling_beam import CouplingBeamGenerator; \
    from src.core.data_models import CoreWallGeometry, CoreWallConfig; \
    g = CoreWallGeometry(config=CoreWallConfig.TUBE_CENTER_OPENING); \
    gen = CouplingBeamGenerator(g); \
    print(gen.generate_coupling_beams())"
  # Assert: No NoneType error, returns list (possibly empty)
  
  # Run unit tests
  pytest tests/test_coupling_beam.py -v
  # Assert: All tests pass
  ```

  **Commit**: YES
  - Message: `fix(fem): resolve NoneType division in coupling beam generation`
  - Files: `src/fem/coupling_beam.py`, `tests/test_coupling_beam.py`

---

- [ ] 2. Create ETABS Validation Baseline

  **What to do**:
  - Define 3-5 test buildings with known configurations:
    1. Simple 10-story with I-Section core
    2. 20-story with Two-C-Facing core
    3. 30-story with Tube center opening (max limit)
  - Document each building's geometry, loads, materials
  - Run ETABS analysis for each (manual - structural engineer task)
  - Record key results: max displacement, base reactions, critical stresses
  - Create validation script comparing PrelimStruct to ETABS

  **Must NOT do**:
  - Automate ETABS (manual process)
  - Create more than 5 test buildings

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires structural engineering knowledge + documentation
  - **Skills**: [`testing-patterns`, `documentation-templates`]
    - `testing-patterns`: Test case design
    - `documentation-templates`: Validation report structure

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 16 (final validation)
  - **Blocked By**: None

  **References**:
  - `PRD.md:Success Criteria` - 95% match target
  - `src/fem/load_combinations.py` - Load cases to apply
  - `src/core/data_models.py:ProjectData` - Input structure

  **Acceptance Criteria**:
  ```bash
  # Verify validation files created
  ls .sisyphus/validation/
  # Assert: Contains building_01.json, building_02.json, building_03.json, ETABS_results.xlsx
  
  # Verify validation script runs
  python scripts/validate_shell_elements.py --list-cases
  # Assert: Output lists 3-5 test cases
  ```

  **Commit**: YES
  - Message: `test(fem): add ETABS validation baseline for 5 test buildings`
  - Files: `.sisyphus/validation/*`, `scripts/validate_shell_elements.py`

---

- [ ] 3. Remove Simplified Engine Files

  **What to do**:
  - Verify no external imports from `src/engines/` (except from app.py)
  - Update `app.py` to remove engine imports if any
  - Delete or archive simplified engine files:
    - `src/engines/slab_engine.py`
    - `src/engines/beam_engine.py`
    - `src/engines/column_engine.py`
    - `src/engines/wind_engine.py`
    - `src/engines/coupling_beam_engine.py`
    - `src/engines/punching_shear.py`
  - Update `__init__.py` if exists
  - Run all tests to verify no breakage

  **Must NOT do**:
  - Delete files referenced by active code (check first!)
  - Remove the `src/engines/` directory itself (keep for future)

  **Recommended Agent Profile**:
  - **Category**: `backend`
    - Reason: Code removal and import cleanup
  - **Skills**: [`clean-code`]
    - `clean-code`: Safe code removal practices

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: None

  **References**:
  - `src/engines/*.py` - Files to remove
  - `app.py:24-28` - Engine imports
  - `CLAUDE.md:Design Engines` - Documentation of engines

  **Acceptance Criteria**:
  ```bash
  # Verify engines removed
  python -c "from src.engines import SlabEngine"
  # Assert: ImportError (module not found)
  
  # Verify app still runs
  streamlit run app.py --server.headless true &
  sleep 5 && curl -s http://localhost:8501 | grep "PrelimStruct"
  # Assert: Returns HTML with "PrelimStruct"
  
  # All tests pass
  pytest tests/ -v --ignore=tests/test_engines/
  # Assert: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(core): remove simplified engines for FEM-only architecture`
  - Files: `src/engines/*.py` (deleted), `app.py`

---

### Wave 2: Shell Elements

---

- [ ] 4. Activate ShellMITC4 for Walls

  **What to do**:
  - Study existing `src/fem/wall_element.py` (already has WallMeshGenerator)
  - Modify `src/fem/model_builder.py` to use `WallMeshGenerator` instead of frame elements
  - Create Plate Fiber Section for wall material (HK Code 2013 concrete)
  - Ensure wall nodes connect to beam nodes at floor levels
  - Implement rigid diaphragm constraint at each floor

  **Must NOT do**:
  - Support wall types beyond 5 core configurations
  - Add varying wall thickness along height
  - Implement openings in walls (use coupling beams)

  **Recommended Agent Profile**:
  - **Category**: `backend`
    - Reason: FEM model building and OpenSeesPy integration
  - **Skills**: [`api-patterns`]
    - `api-patterns`: Clean API design for mesh generation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 5)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 1, 3

  **References**:
  - `src/fem/wall_element.py:WallMeshGenerator` - Existing mesh generator
  - `src/fem/model_builder.py:build_fem_model()` - Integration point
  - `src/fem/materials.py` - HK Code 2013 material definitions
  - OpenSees docs: https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html

  **Acceptance Criteria**:
  ```bash
  # Unit test for wall elements
  pytest tests/test_wall_element.py -v
  # Assert: All tests pass
  
  # Verify shell elements created in model
  python -c "
  from src.fem.model_builder import build_fem_model
  from src.core.data_models import ProjectData
  project = ProjectData()
  project.lateral.core_wall_config = 'I_SECTION'
  model = build_fem_model(project)
  shells = [e for e in model.elements.values() if 'SHELL' in str(e.element_type)]
  print(f'Shell elements: {len(shells)}')
  assert len(shells) > 0, 'No shell elements created'
  "
  # Assert: Output shows shell elements > 0
  ```

  **Commit**: YES
  - Message: `feat(fem): activate ShellMITC4 elements for core walls`
  - Files: `src/fem/model_builder.py`, `src/fem/wall_element.py`

---

- [ ] 5. Activate ShellMITC4 for Slabs

  **What to do**:
  - Study existing `src/fem/slab_element.py` (already has SlabMeshGenerator)
  - Modify `src/fem/model_builder.py` to create slab shell elements
  - Create Elastic Membrane Plate Section for slab material
  - Ensure slab nodes align with beam nodes (shared nodes)
  - Set mesh density (elements per bay) for reasonable accuracy

  **Must NOT do**:
  - Support slab openings (stairs, elevators)
  - Support varying thickness slabs
  - Support curved or non-rectangular slabs

  **Recommended Agent Profile**:
  - **Category**: `backend`
    - Reason: FEM model building and OpenSeesPy integration
  - **Skills**: [`api-patterns`]
    - `api-patterns`: Clean API design for mesh generation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 1, 3

  **References**:
  - `src/fem/slab_element.py:SlabMeshGenerator` - Existing mesh generator
  - `src/fem/model_builder.py:build_fem_model()` - Integration point
  - OpenSees docs: https://opensees.berkeley.edu/wiki/index.php/Elastic_Membrane_Plate_Section

  **Acceptance Criteria**:
  ```bash
  # Unit test for slab elements
  pytest tests/test_slab_element.py -v
  # Assert: All tests pass
  
  # Verify slab shell elements in model
  python -c "
  from src.fem.model_builder import build_fem_model
  from src.core.data_models import ProjectData
  project = ProjectData()
  model = build_fem_model(project)
  slabs = [e for e in model.elements.values() if e.element_type.name == 'SHELL_MITC4']
  print(f'Slab elements: {len(slabs)}')
  assert len(slabs) > 0, 'No slab shell elements created'
  "
  # Assert: Output shows slab elements > 0
  ```

  **Commit**: YES
  - Message: `feat(fem): activate ShellMITC4 elements for floor slabs`
  - Files: `src/fem/model_builder.py`, `src/fem/slab_element.py`

---

- [ ] 6. Update Model Builder Integration

  **What to do**:
  - Ensure shell elements properly connect to frame elements (beams, columns)
  - Add rigid diaphragm constraints at floor levels
  - Update node numbering scheme for shell elements
  - Add model validation before analysis (mesh quality checks)
  - Update `get_model_statistics()` to count shell elements

  **Must NOT do**:
  - Change existing beam/column element logic
  - Add new element types beyond shell

  **Recommended Agent Profile**:
  - **Category**: `backend`
    - Reason: Integration and validation logic
  - **Skills**: [`api-patterns`, `testing-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential after Wave 2a
  - **Blocks**: Tasks 7, 8, 9
  - **Blocked By**: Tasks 4, 5

  **References**:
  - `src/fem/model_builder.py` - Main integration file
  - `src/fem/fem_engine.py:FEMModel` - Model class to update
  - `src/fem/visualization.py:get_model_statistics()` - Statistics function

  **Acceptance Criteria**:
  ```bash
  # Full model builds without error
  python -c "
  from src.fem.model_builder import build_fem_model
  from src.core.data_models import ProjectData
  project = ProjectData()
  project.geometry.floors = 10
  project.lateral.core_wall_config = 'I_SECTION'
  model = build_fem_model(project)
  stats = model.get_statistics()
  print(f'Nodes: {stats[\"nodes\"]}, Shells: {stats[\"shells\"]}, Frames: {stats[\"frames\"]}')
  "
  # Assert: Shows non-zero counts for all element types
  
  # Run analysis without error
  pytest tests/test_model_builder.py -v
  # Assert: All tests pass
  ```

  **Commit**: YES
  - Message: `feat(fem): integrate shell elements with rigid diaphragm constraints`
  - Files: `src/fem/model_builder.py`, `src/fem/fem_engine.py`

---

### Wave 3: Load System

---

- [ ] 7. Load Combination UI Overhaul

  **What to do**:
  - Create scrollable list component for 60 load combinations
  - Add checkbox for each combination (multi-select)
  - Implement "Select All" and "Deselect All" buttons
  - Group combinations by category (GRAVITY, WIND, SEISMIC, SLS)
  - Add collapsible sections for each category
  - Show count: "12 of 60 selected"
  - Store selection in session state

  **Must NOT do**:
  - Allow editing/creating custom combinations
  - Add filtering by load magnitude
  - Implement drag-drop reordering

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI component development
  - **Skills**: [`frontend-ui-ux`, `react-patterns`]
    - `frontend-ui-ux`: Streamlit component patterns
    - `react-patterns`: State management

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 8, 9)
  - **Blocks**: Task 10
  - **Blocked By**: Task 6

  **References**:
  - `src/fem/load_combinations.py:LoadCombinationLibrary` - 60 combinations
  - `app.py:1040-1100` - Current load combination UI
  - User wireframes (provided by user)

  **Acceptance Criteria**:
  ```bash
  # Playwright test for load combination visibility
  python tests/ui/test_load_combinations.py
  # Assert: JSON output shows {"visible_combinations": 60, "checkboxes": 60}
  
  # Manual verification via screenshot
  python tests/ui/screenshot.py --target load_combinations
  # Assert: Screenshot saved showing scrollable list
  ```

  **Commit**: YES
  - Message: `feat(ui): implement scrollable load combination selector with multi-select`
  - Files: `app.py`, `src/ui/components/load_selector.py`

---

- [ ] 8. Implement Reaction Export Table

  **What to do**:
  - Create Reaction Table section in results area
  - Extract reaction forces from all base support nodes
  - Display per node: Fx, Fy, Fz, Mx, My, Mz
  - Add load case/combination dropdown selector
  - Calculate and display total reactions (sum of all nodes)
  - Implement CSV export button
  - Implement Excel (.xlsx) export button
  - Add "Copy to Clipboard" functionality

  **Must NOT do**:
  - Add filtering by node ID
  - Create reaction charts/graphs
  - Support partial node selection

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Data table UI + export functionality
  - **Skills**: [`frontend-ui-ux`, `api-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 7, 9)
  - **Blocks**: Task 10
  - **Blocked By**: Task 6

  **References**:
  - `PRD.md:Task 21.7` - Reaction table requirements
  - `src/fem/solver.py:AnalysisResult` - Reaction data source
  - `src/fem/results_processor.py` - Results extraction

  **Acceptance Criteria**:
  ```bash
  # Verify CSV export works
  python -c "
  from src.fem.solver import AnalysisResult
  # Mock result with reactions
  result = AnalysisResult(...)
  result.export_reactions_csv('test_reactions.csv')
  import os
  assert os.path.exists('test_reactions.csv'), 'CSV not created'
  "
  # Assert: File created
  
  # Verify UI element exists (Playwright)
  python tests/ui/test_reactions_table.py
  # Assert: {"table_visible": true, "export_button": true}
  ```

  **Commit**: YES
  - Message: `feat(ui): add reaction table with CSV/Excel export`
  - Files: `app.py`, `src/ui/components/reaction_table.py`, `src/fem/solver.py`

---

- [ ] 9. Surface Load on Shell Slabs

  **What to do**:
  - Implement OpenSees SurfaceLoad element for slabs
  - Apply distributed loads (kPa) to slab shell elements
  - Remove legacy nodal load approach for slabs
  - Display load magnitude in UI (kPa units)
  - Verify total load equals expected (area × pressure)

  **Must NOT do**:
  - Support point loads on slabs
  - Support line loads on slabs
  - Add load pattern visualization on 3D view

  **Recommended Agent Profile**:
  - **Category**: `backend`
    - Reason: OpenSeesPy load application
  - **Skills**: [`api-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 7, 8)
  - **Blocks**: Task 16
  - **Blocked By**: Tasks 4, 5

  **References**:
  - OpenSees docs: https://opensees.berkeley.edu/wiki/index.php/SurfaceLoad_Element
  - `src/fem/model_builder.py:_apply_loads()` - Load application point
  - `src/core/data_models.py:LoadInput` - Load values

  **Acceptance Criteria**:
  ```bash
  # Verify surface load applied
  python -c "
  from src.fem.model_builder import build_fem_model
  from src.fem.solver import analyze_model
  from src.core.data_models import ProjectData
  project = ProjectData()
  project.loads.dead_load = 5.0  # kPa
  model = build_fem_model(project)
  result = analyze_model(model)
  # Check total vertical reaction equals expected load
  total_area = project.geometry.bay_x * project.geometry.bay_y * project.geometry.num_bays_x * project.geometry.num_bays_y
  expected_load = 5.0 * total_area  # kN
  print(f'Expected: {expected_load}, Actual: {sum(result.reactions.values())}')
  "
  # Assert: Values within 5% tolerance
  ```

  **Commit**: YES
  - Message: `feat(fem): implement SurfaceLoad for shell slab elements`
  - Files: `src/fem/model_builder.py`, `src/fem/solver.py`

---

### Wave 4: UI/UX

---

- [ ] 10. Apply Wireframes to app.py

  **What to do**:
  - Implement user-provided wireframe layout
  - Apply custom CSS theme (colors, fonts, spacing)
  - Define brand colors (blue + orange, NO PURPLE)
  - Implement 8px spacing scale (4/8/16/32/64px)
  - Add custom fonts (if specified in wireframes)
  - Replace generic Streamlit aesthetic

  **Must NOT do**:
  - Create entirely new screens not in wireframes
  - Add animations or micro-interactions (separate task if needed)
  - Implement dark mode
  - Build responsive mobile layout

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI styling and layout
  - **Skills**: [`frontend-ui-ux`, `tailwind-patterns`]
    - `frontend-ui-ux`: Design system implementation
    - `tailwind-patterns`: Spacing scale patterns

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (foundation for 11, 12, 13)
  - **Blocks**: Tasks 11, 12, 13
  - **Blocked By**: Tasks 7, 8

  **References**:
  - **UI Reference Image**: https://storage.googleapis.com/s4a-prod-share-preview/default/st_app_screenshot_image/16f258d6-ec9d-4407-92ac-fd7a256f4a7c/Home_Page.png
    - Streamlit design with clean sidebar, professional branding, Meinhardt style
    - Use as primary visual reference for layout and styling patterns
  - **Logo**: Meinhardt logo (user to provide `assets/meinhardt_logo.png`)
  - `app.py:64-153` - Current CSS styling
  - `AUDIT_CRITIQUE.json` - Design recommendations

  **Acceptance Criteria**:
  ```bash
  # Screenshot comparison
  python tests/ui/screenshot.py --target full_page --output new_design.png
  # Assert: Visual inspection shows wireframe match (manual)
  
  # Verify custom colors applied
  grep -q "1E3A5F" app.py  # Check brand color present
  # Assert: Exit code 0
  ```

  **Commit**: YES
  - Message: `feat(ui): apply wireframe design with custom theme`
  - Files: `app.py`

---

- [ ] 11. Relocate FEM Views Section

  **What to do**:
  - Move FEM Views section to appear immediately below KEY METRICS
  - Move visualization legends to bottom of views
  - Arrange view buttons: Plan (Left), Elevation (Center), 3D (Right)
  - Add floor selection dropdown next to Plan View button
  - Format floor labels as "G/F (+0.00)", "1/F (+4.00)", etc.
  - Ensure FEM views visible without scrolling (above fold)

  **Must NOT do**:
  - Change the actual visualization code
  - Add new view types
  - Implement pan/zoom controls

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Layout restructuring
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4b (with Tasks 12, 13)
  - **Blocks**: Task 16
  - **Blocked By**: Task 10

  **References**:
  - `PRD.md:Task 21.1` - FEM views relocation spec
  - `app.py:render_unified_fem_views()` - Current implementation
  - `src/ui/views/fem_views.py` - FEM views module

  **Acceptance Criteria**:
  ```bash
  # Playwright: FEM views above fold
  python tests/ui/test_fem_above_fold.py
  # Assert: {"fem_plan_view_y": <900, "visible_without_scroll": true}
  
  # Screenshot
  python tests/ui/screenshot.py --target fem_views --viewport 1920x1080
  # Assert: Screenshot saved, visual inspection confirms position
  ```

  **Commit**: YES
  - Message: `feat(ui): relocate FEM views below KEY METRICS`
  - Files: `app.py`, `src/ui/views/fem_views.py`

---

- [ ] 12. Visual Core Wall Selector

  **What to do**:
  - Replace checkbox + text radios with clickable configuration cards
  - Create SVG diagrams for each of 5 core wall types
  - Show configuration preview on hover
  - Highlight selected configuration
  - Make selector visible on page load (no expand/collapse)

  **Must NOT do**:
  - Add new core wall configuration types
  - Allow custom geometry editing
  - Create 3D previews

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Custom UI component with SVG
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4b (with Tasks 11, 13)
  - **Blocks**: Task 16
  - **Blocked By**: Task 10

  **References**:
  - `PRD.md:Task 17.2` - Custom core wall location
  - `src/fem/core_wall_geometry.py` - 5 core wall types
  - `AUDIT_CRITIQUE.json:critical_issues[1]` - Core wall selector bug

  **Acceptance Criteria**:
  ```bash
  # Playwright: Core wall selector visible
  python tests/ui/test_core_wall_selector.py
  # Assert: {"selector_visible": true, "cards_count": 5, "clickable": true}
  
  # Click each configuration
  python tests/ui/test_core_wall_click.py --config I_SECTION
  # Assert: {"selected": "I_SECTION", "preview_updated": true}
  ```

  **Commit**: YES
  - Message: `feat(ui): add visual core wall selector with SVG previews`
  - Files: `app.py`, `src/ui/components/core_wall_selector.py`, `static/svg/core_walls/`

---

- [ ] 13. Fix Mobile Viewport Overlay

  **What to do**:
  - Fix sidebar overlay issue on mobile viewport (<768px)
  - Ensure content is accessible when sidebar is open
  - Option A: Collapse sidebar by default on mobile
  - Option B: Document as "desktop recommended" (minimal fix)
  - Test on 375x812 viewport (iPhone X)

  **Must NOT do**:
  - Build full responsive mobile layout
  - Create hamburger menu
  - Optimize touch targets

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Minor CSS fix
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4b (with Tasks 11, 12)
  - **Blocks**: Task 16
  - **Blocked By**: Task 10

  **References**:
  - `AUDIT_CRITIQUE.json:critical_issues[8]` - Mobile overlay issue
  - `audit_screenshots/10_mobile_view.png` - Current mobile state

  **Acceptance Criteria**:
  ```bash
  # Playwright mobile test
  python tests/ui/test_mobile.py --viewport 375x812
  # Assert: {"content_visible": true, "sidebar_overlay": false} OR {"warning_shown": true}
  ```

  **Commit**: YES
  - Message: `fix(ui): resolve mobile viewport sidebar overlay`
  - Files: `app.py`

---

### Wave 5: Polish

---

- [ ] 14. Write MIGRATION.md

  **What to do**:
  - Document breaking changes from v3.0 to v3.5
  - Explain why v3.0 projects won't load
  - Provide manual migration steps (if any data is recoverable)
  - List removed features (simplified engines)
  - List new features (shell elements, 60 combos)
  - Include FAQ section

  **Must NOT do**:
  - Create automated migration tool
  - Promise backward compatibility

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Technical documentation
  - **Skills**: [`documentation-templates`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Anytime (no dependencies)
  - **Blocks**: Task 16
  - **Blocked By**: None

  **References**:
  - `PRD.md` - Feature list
  - `CLAUDE.md` - Project structure
  - `README.md` - Current documentation

  **Acceptance Criteria**:
  ```bash
  # Verify file exists with required sections
  grep -q "Breaking Changes" MIGRATION.md && \
  grep -q "Removed Features" MIGRATION.md && \
  grep -q "New Features" MIGRATION.md
  # Assert: Exit code 0
  ```

  **Commit**: YES
  - Message: `docs: add MIGRATION.md for v3.0 to v3.5 upgrade guide`
  - Files: `MIGRATION.md`

---

- [ ] 15. Write VALIDATION_REPORT.md

  **What to do**:
  - Document ETABS comparison methodology
  - Present results for 3-5 test buildings
  - Show displacement comparisons (table + charts if applicable)
  - Show reaction comparisons
  - Calculate % error for each metric
  - Conclude: PASS (within tolerance) or FAIL (needs investigation)

  **Must NOT do**:
  - Run additional ETABS analyses
  - Automate report generation

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Technical report
  - **Skills**: [`documentation-templates`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: After Task 2 provides data
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 16

  **References**:
  - `.sisyphus/validation/*` - ETABS results from Task 2
  - `scripts/validate_shell_elements.py` - Validation script

  **Acceptance Criteria**:
  ```bash
  # Verify file exists with results
  grep -q "PASS" VALIDATION_REPORT.md || grep -q "FAIL" VALIDATION_REPORT.md
  # Assert: Exit code 0 (one of PASS or FAIL present)
  ```

  **Commit**: YES
  - Message: `docs: add VALIDATION_REPORT.md with ETABS comparison results`
  - Files: `VALIDATION_REPORT.md`

---

- [ ] 16. Final Integration Testing

  **What to do**:
  - Run full test suite: `pytest tests/ -v`
  - Run ETABS validation script
  - Verify all 17 tasks' acceptance criteria pass
  - Test complete workflow: Create project → Configure → Analyze → Export
  - Document any remaining issues

  **Must NOT do**:
  - Add new features
  - Fix non-critical bugs (log for v3.6)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration and verification
  - **Skills**: [`testing-patterns`, `webapp-testing`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final step)
  - **Blocks**: Task 17
  - **Blocked By**: Tasks 6, 9, 11, 12, 13, 14

  **References**:
  - All task acceptance criteria
  - `pytest.ini` - Test configuration
  - `scripts/validate_shell_elements.py`

  **Acceptance Criteria**:
  ```bash
  # Full test suite
  pytest tests/ -v --tb=short
  # Assert: Exit code 0, all tests pass
  
  # Validation script
  python scripts/validate_shell_elements.py --all
  # Assert: All buildings within tolerance
  
  # Workflow test
  python tests/integration/test_full_workflow.py
  # Assert: Exit code 0
  ```

  **Commit**: YES
  - Message: `test: verify v3.5 integration and ETABS validation`
  - Files: Test result logs

---

- [ ] 17. Performance Benchmarking

  **What to do**:
  - Benchmark analysis time for 10, 20, 30 floor buildings
  - Measure memory usage during analysis
  - Document results in README.md or separate doc
  - Verify 30-floor building completes in <60 seconds
  - Log any performance warnings

  **Must NOT do**:
  - Optimize code (document for v3.6 if needed)
  - Create automated performance testing framework

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Measurement and documentation
  - **Skills**: [`performance-profiling`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Final
  - **Blocks**: None (last task)
  - **Blocked By**: Task 16

  **References**:
  - `PRD.md:Success Criteria` - <30s for 30-story
  - `src/fem/solver.py` - Analysis code

  **Acceptance Criteria**:
  ```bash
  # Benchmark script
  python scripts/benchmark.py --floors 30 --timeout 60
  # Assert: Output shows "PASS: Analysis completed in Xs" where X <= 60
  ```

  **Commit**: YES
  - Message: `docs: add performance benchmarks for v3.5`
  - Files: `README.md` (updated), `PERFORMANCE.md` (optional)

---

## Commit Strategy

| After Task | Message | Files | Pre-commit |
|------------|---------|-------|------------|
| 1 | `fix(fem): resolve NoneType division in coupling beam` | coupling_beam.py, tests | pytest tests/test_coupling_beam.py |
| 3 | `refactor(core): remove simplified engines` | src/engines/*.py, app.py | pytest |
| 4 | `feat(fem): activate ShellMITC4 for walls` | model_builder.py, wall_element.py | pytest tests/test_wall_element.py |
| 5 | `feat(fem): activate ShellMITC4 for slabs` | model_builder.py, slab_element.py | pytest tests/test_slab_element.py |
| 6 | `feat(fem): integrate shell elements with diaphragm` | model_builder.py, fem_engine.py | pytest tests/test_model_builder.py |
| 7 | `feat(ui): scrollable load combination selector` | app.py | Manual UI check |
| 8 | `feat(ui): reaction table with CSV/Excel export` | app.py, solver.py | pytest |
| 9 | `feat(fem): SurfaceLoad for shell slabs` | model_builder.py | pytest |
| 10 | `feat(ui): apply wireframe design` | app.py | Manual UI check |
| 11 | `feat(ui): relocate FEM views below KEY METRICS` | app.py | Playwright |
| 12 | `feat(ui): visual core wall selector` | app.py, core_wall_selector.py | Playwright |
| 13 | `fix(ui): mobile viewport sidebar overlay` | app.py | Playwright |
| 14 | `docs: MIGRATION.md` | MIGRATION.md | None |
| 15 | `docs: VALIDATION_REPORT.md` | VALIDATION_REPORT.md | None |
| 16 | `test: v3.5 integration verification` | - | pytest |
| 17 | `docs: performance benchmarks` | README.md | None |

---

## Success Criteria

### Verification Commands
```bash
# All tests pass
pytest tests/ -v
# Expected: Exit code 0, 265+ tests pass

# Shell elements active
python -c "from src.fem.model_builder import build_fem_model; m = build_fem_model(); print(len([e for e in m.elements.values() if 'SHELL' in str(e.element_type)]))"
# Expected: > 0

# Simplified engines removed
python -c "from src.engines import SlabEngine"
# Expected: ImportError

# ETABS validation
python scripts/validate_shell_elements.py --all
# Expected: All cases PASS (within 10% tolerance)

# Performance
python scripts/benchmark.py --floors 30 --timeout 60
# Expected: PASS (< 60 seconds)
```

### Final Checklist
- [ ] All "Must Have" present (shell elements, 60 combos, reaction export)
- [ ] All "Must NOT Have" absent (no AI chat, no v3.0 compat, no >30 floors)
- [ ] All 265+ tests pass
- [ ] ETABS validation within 10% tolerance
- [ ] UI matches wireframes
- [ ] MIGRATION.md and VALIDATION_REPORT.md complete
- [ ] Performance < 60s for 30-floor building

---

## Scope Guardrails (Metis-Enforced)

### MUST NOT (Forbidden Actions)
- Add AI Chat (deferred to v3.6)
- Support v3.0 project files (breaking change)
- Add element types beyond ShellMITC4
- Support >30 floor buildings
- Create custom load combination builder
- Add slab openings or varying thickness
- Implement undo/redo system
- Build responsive mobile layout
- Add nonlinear analysis

### If Tempted to Add Features Not in Plan
1. STOP
2. Document request in `.sisyphus/backlog/v36-ideas.md`
3. Continue with current task
4. Review backlog after v3.5 release

---

*Plan generated by Prometheus (Planning Agent)*
*Metis review incorporated: 2026-02-03*
*Estimated effort: 35-45 days with 30% buffer*
