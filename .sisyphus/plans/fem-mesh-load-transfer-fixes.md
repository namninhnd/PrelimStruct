# FEM Mesh/Load Transfer & Force Visualization Fixes

## TL;DR

> **Quick Summary**: Update the FEM discretization + slab meshing so slab surface loads reliably transfer into beams/columns, and make Plotly Plan/Elevation force overlays consistent with the force tables.
>
> **Deliverables**:
> - Fixed 5-node (4 sub-element) discretization for line elements (primary/secondary beams + columns)
> - Slab mesh generation aligned to beam subdivision nodes (remove `0.1L`-based sizing)
> - Beam/column Plotly Plan/Elevation force overlays sourced from the same normalized data used by tables
> - New Column Section Forces table + overlay consistency
> - Reaction extraction fixed + reaction table reliably shows all load cases via dropdown
> - Rectangular column sections respected end-to-end (UI → ProjectData → FEM model)
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES (3 waves)
> **Critical Path**: Reaction extraction fix → discretization + slab mesh alignment → load-transfer verification → overlay/table unification

---

## Context

### Original Request
1. Reduce all line elements (primary beam, secondary beam, column) to **5 nodes** (equal spacing). Then fix slab mesh to match the beam nodes (remove hard-coded `0.1L`).
2. Apply area loads on each mesh (not per whole bay) — current issue observed as **no beam forces** in the force table.
3. Beam force diagram (Plotly Plan/Elevation overlays) must plot according to the beam force table for consistent outcomes.
4. Add a Column Section Forces table like beam, and plot according to the table (Plotly overlays).
5. Fix reaction forces table to show all load cases; currently reactions fail to show.
6. Replace “Element Overrides” conceptually with “Section Properties” showing selected sections; model auto-updates when user changes section properties (e.g., self-weight in DL).
7. In “Section Properties”, allow rectangular column sections (like beams), not just square.

### Interview Summary (Decisions)
- Discretization is **fixed** (not user-configurable): 5 nodes per line element (4 sub-elements).
- Force diagram default remains **"None"**.
- “Beam force diagram” refers to **Plotly Plan/Elevation overlays**, not a separate 1D chart.
- Reaction table UI should remain **dropdown per load case**.
- Test strategy: **TDD with pytest**.

### Key Code Touchpoints (Verified)
- Discretization constants:
  - `src/fem/model_builder.py` `NUM_SUBDIVISIONS = 6` (current)
  - `src/fem/builders/beam_builder.py` local `NUM_SUBDIVISIONS = 6` (current)
  - `src/fem/builders/column_builder.py` local `NUM_SUBDIVISIONS = 6` (current)
- Slab meshing:
  - `src/fem/model_builder.py` slab block uses `target_size = 0.1 * max(panel dims)` then snaps to align with `beam_div` + `sec_div`
  - `src/fem/slab_element.py` `SlabMeshGenerator.generate_mesh(...)` reuses `existing_nodes` by `(round(x,6), round(y,6), round(z,6))`
- Surface loads:
  - `src/fem/model_builder.py` `_apply_slab_surface_loads(...)` applies DL/SDL/LL pressure per slab element
  - `src/fem/fem_engine.py` converts each shell pressure to equivalent nodal loads and applies by load pattern
- Force overlays vs tables:
  - Plotly overlays extract forces via `src/fem/results_processor.py` `ResultsProcessor.extract_section_forces(...)` (raw end forces)
  - Beam table normalizes end forces in `src/ui/components/beam_forces_table.py` (`_display_end_force` / `_normalize_end_force`)
- Rectangular columns blocked by backend:
  - `src/fem/model_builder.py` `_extract_column_dims(...)` forces square if `column_result.dimension > 0`
  - `src/ui/project_builder.py` always sets `ColumnResult.dimension = max(width, depth)`
- Reactions likely empty because solver never calls `ops.reactions()`:
  - `src/fem/solver.py` `FEMSolver.extract_results()` calls `ops.nodeReaction(...)` directly

### Metis Review (Gaps Addressed)
- Reaction extraction fix: explicitly add `ops.reactions()` before reading node reactions.
- Overlay/table mismatch: create a shared force normalization path used by both overlays and tables.
- Slab-beam load transfer: treat as mesh-node sharing compatibility problem; verify via tests.
- Rectangular columns: preserve width/depth independently; stop `dimension` from squaring columns.

---

## Work Objectives

### Core Objective
Make FEM gravity surface loads (slab pressures) reliably produce non-zero beam/column section forces, with consistent reporting across force tables and Plotly overlays.

### Concrete Deliverables
- Line elements discretized into **4 sub-elements / 5 nodes** (equal spacing) across beams + columns.
- Slab meshing uses **deterministic division counts** based on beam subdivision count + secondary beam strip count; removes `0.1L` sizing.
- Plotly Plan/Elevation force overlays use the **same normalized force conventions** as the beam/column force tables.
- New Column Section Forces table component integrated in `src/ui/views/fem_views.py`.
- Reaction forces extracted and displayed for all load cases.
- Rectangular column sections supported end-to-end.

### Definition of Done
- `pytest tests/ -v` passes.
- For a small reference model (1 bay, 1 floor):
  - Slab DL/LL produces **non-zero** beam section forces in `Beam Section Forces`.
  - Plotly overlay values match the force table’s normalized values for the same load case and component.
  - Reaction table shows non-empty reactions for each load case.

### Must NOT Have (Guardrails)
- Do not change load pattern IDs: DL=1, SDL=2, LL=3, Wx+/Wx-/Wy+/Wy-=4..7.
- Do not introduce acceptance criteria that require human/manual verification.
- Do not add new force component semantics beyond existing: N, Vy, Vz, My, Mz, T.
- Do not weaken node-sharing tolerance rules (keep 6-decimal rounding strategy consistent).

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> All verification is agent-executed (pytest + Playwright + scripted Streamlit run). No “user manually checks”.

### Test Decision
- **Infrastructure exists**: YES (`pytest`)
- **Automated tests**: YES (TDD)
- **Framework**: pytest

### TDD Workflow (per task)
Each task follows RED → GREEN → REFACTOR:
1. **RED**: add/adjust a failing pytest test capturing the desired behavior.
2. **GREEN**: implement minimal code changes to pass.
3. **REFACTOR**: clean up with tests staying green.

### Agent-Executed QA Scenarios (MANDATORY)

Tooling:
- Backend/tests: Bash (`pytest`)
- UI regression: Playwright (reuse existing scripts)

Scenarios (global):
1. Run Streamlit, click `Run FEM Analysis`, open `Beam Section Forces`, confirm table is non-empty and forces are not all zero.
2. Toggle `Force Type` from `None` to a component (e.g., `M-minor (Weak Axis)`), confirm Plan/Elevation overlays show values and match the table values (same sign convention).
3. Open `Reaction Forces Table`, select each load case from dropdown, confirm reactions populate.
4. In Sidebar `Section Properties`, set column width/depth to rectangular (e.g., 500x800), rerun FEM analysis, confirm column self-weight and/or internal forces change vs square baseline.

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Start Immediately):
- Task 1: Fix reaction extraction (`ops.reactions()`)
- Task 2: Rectangular column dimensions respected end-to-end
- Task 3: Create shared force normalization utility (tables + overlays)

Wave 2 (After Wave 1):
- Task 4: Enforce 5-node discretization (4 sub-elements) and update subdivision-related tests
- Task 5: Replace slab mesh sizing with beam-node-aligned division logic (remove `0.1L`)

Wave 3 (After Wave 2):
- Task 6: Load transfer integration test (surface load → non-zero beam forces)
- Task 7: Add Column Section Forces table + integrate into FEM views + overlay consistency checks

Critical Path: Task 1 → Task 4 → Task 5 → Task 6

---

## TODOs

> Implementation + Test = ONE Task. (TDD)

- [x] 1. Fix reaction extraction so reaction table can populate (TDD)

  **What to do (RED → GREEN → REFACTOR)**:
  - RED: Add pytest that runs a minimal FEM analysis and asserts `AnalysisResult.node_reactions` is non-empty for a gravity load case.
  - GREEN: In `src/fem/solver.py` `FEMSolver.extract_results()`, call `ops.reactions()` after analysis and before iterating `ops.nodeReaction(...)`.
  - REFACTOR: Keep reaction filtering logic but ensure non-zero reactions are retained.

  **Must NOT do**:
  - Do not change UI reaction table behavior yet; fix the data source first.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `testing-patterns`

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 1
  - Blocks: Task 7 (reaction table verification)

  **References**:
  - `src/fem/solver.py` — `FEMSolver.extract_results()` reaction loop
  - `src/ui/components/reaction_table.py` — expects `result.node_reactions` populated

  **Acceptance Criteria**:
  - [ ] New test fails before fix and passes after.
  - [ ] For a minimal model: `result.node_reactions` has at least one node with a non-zero component.

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Reactions available after analysis
    Tool: Bash (pytest)
    Preconditions: openseespy installed; tests runnable
    Steps:
      1. pytest tests/test_reaction_table.py -v
      2. Assert: test confirms node_reactions non-empty for DL
    Expected Result: Reaction extraction works and test passes
  ```

- [x] 2. Support rectangular column sections end-to-end (TDD)

  **What to do (RED → GREEN → REFACTOR)**:
  - RED: Add unit test for `_extract_column_dims(project)` ensuring width/depth are preserved when set.
  - GREEN:
    - Update `_extract_column_dims` in `src/fem/model_builder.py` to only fall back to `dimension` when width/depth are not explicitly provided.
    - Update `src/ui/project_builder.py` so `ColumnResult.dimension` does not force squaring behavior downstream (dimension remains informational).
  - REFACTOR: Keep backward compatibility for legacy square-only configs.

  **Must NOT do**:
  - Do not remove `dimension` field usage everywhere; only stop it from overriding explicit width/depth.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `testing-patterns`, `clean-code`

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 1
  - Blocks: Task 4 (column discretization still uses column dims)

  **References**:
  - `src/fem/model_builder.py` `_extract_column_dims`
  - `src/ui/project_builder.py` `ColumnResult(...)` construction
  - `src/ui/sidebar.py` `_render_overrides` (already captures width/depth)

  **Acceptance Criteria**:
  - [ ] Pytest proves `_extract_column_dims` returns (width, depth) as entered.
  - [ ] Rectangular input (e.g., 500x800) does not become square in FEM section creation.

- [x] 3. Unify force normalization used by Plotly overlays and force tables (TDD)

  **What to do (RED → GREEN → REFACTOR)**:
  - RED: Add unit tests that encode the current beam table normalization rules (end-force sign handling for Vy/Vz/My/Mz/T).
  - GREEN:
    - Create a shared utility (new module) for end-force normalization and component mapping.
    - Refactor:
      - `src/ui/components/beam_forces_table.py` to use shared normalization.
      - `src/fem/results_processor.py` `extract_section_forces(...)` to use the same normalization so Plotly overlays match table conventions.
  - REFACTOR: Remove duplicated normalization logic.

  **Must NOT do**:
  - Do not silently change sign conventions without tests demonstrating intended behavior.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `testing-patterns`, `clean-code`

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 1
  - Blocks: Task 7 (column forces table + overlays)

  **References**:
  - `src/ui/components/beam_forces_table.py` `_display_end_force`, `_normalize_end_force`
  - `src/fem/results_processor.py` `ResultsProcessor.extract_section_forces`
  - `src/fem/visualization.py` — overlays consume `extract_section_forces`

  **Acceptance Criteria**:
  - [ ] New unit tests cover normalization of at least: N, Vy, Mz.
  - [ ] For a known force pair (i/j), overlay-normalized value == table-normalized value.

- [x] 4. Enforce 5-node discretization (4 sub-elements) for line elements + update tests (TDD)

  **What to do (RED → GREEN → REFACTOR)**:
  - RED: Update/add tests currently asserting 6 sub-elements / 7 nodes to instead assert 4 sub-elements / 5 nodes.
  - GREEN: Change discretization constants:
    - `src/fem/model_builder.py` `NUM_SUBDIVISIONS = 4`
    - `src/fem/builders/beam_builder.py` local `NUM_SUBDIVISIONS = 4`
    - `src/fem/builders/column_builder.py` local `NUM_SUBDIVISIONS = 4`
  - REFACTOR: Update docstrings/comments that hardcode “6/7”.

  **Must NOT do**:
  - Do not make subdivision count user-configurable (explicitly fixed by requirement).

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `testing-patterns`

  **Parallelization**:
  - Can Run In Parallel: NO
  - Parallel Group: Wave 2
  - Blocked By: Task 2 (column dims)
  - Blocks: Task 5, Task 6, Task 7

  **References**:
  - `src/fem/model_builder.py` `NUM_SUBDIVISIONS`, `_create_subdivided_beam`, column creation loop
  - `src/fem/builders/beam_builder.py` `_create_beam_element`
  - `src/fem/builders/column_builder.py` `create_columns`
  - Existing tests: `tests/test_beam_subdivision.py` (and any column subdivision tests)

  **Acceptance Criteria**:
  - [ ] Tests confirm 5 nodes per parent beam/column group.
  - [ ] Beam force table renders 5 rows per member (positions 0.00L → 1.00L) after analysis.

- [x] 5. Remove `0.1L` slab mesh sizing and align slab mesh divisions to beam nodes (TDD)

  **What to do (RED → GREEN → REFACTOR)**:
  - RED:
    - Add tests ensuring slab meshing selects `elements_along_x/y` as deterministic multiples of (beam_subdivisions, secondary strip count) and that intermediate beam nodes are reused by slab mesh (`existing_nodes` hit).
  - GREEN:
    - In `src/fem/model_builder.py` slab meshing block:
      - Remove `target_size = 0.1 * ...` sizing approach.
      - Compute `elements_along_x/y` based on:
        - `beam_div = NUM_SUBDIVISIONS` (now 4)
        - `sec_div = num_secondary_beams + 1` (or 1)
        - `lcm(beam_div, sec_div)` on the axis orthogonal to secondary beams
        - Optional refinement multiplier `options.slab_elements_per_bay` (must preserve node alignment)
      - Pass `beam_subdivision_count=beam_div` to `SlabMeshGenerator.generate_mesh(...)` for clarity.
  - REFACTOR:
    - Ensure rounding/coord matching stays consistent (`round(..., 6)`).

  **Must NOT do**:
  - Do not remove node sharing mechanism in `SlabMeshGenerator`.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `testing-patterns`

  **Parallelization**:
  - Can Run In Parallel: NO
  - Parallel Group: Wave 2
  - Blocked By: Task 4
  - Blocks: Task 6

  **References**:
  - `src/fem/model_builder.py` slab meshing block (currently contains `target_size = 0.1 * ...`)
  - `src/fem/slab_element.py` `SlabMeshGenerator.generate_mesh(...)` and node reuse (`existing_nodes`)

  **Acceptance Criteria**:
  - [ ] Tests confirm slab mesh reuses intermediate beam node tags along a bay edge.
  - [ ] No `0.1 * max(...)` sizing remains in slab meshing path.

- [x] 6. Prove slab surface loads transfer into beams (non-zero beam forces) (TDD, integration)

  **What to do (RED → GREEN → REFACTOR)**:
  - RED: Add a small integration test:
    - Build a minimal ProjectData (1 bay x 1 bay, 1 floor, slabs on).
    - Run `analyze_model(..., load_cases=["DL"])`.
    - Assert at least one beam sub-element has non-zero moment/shear (using `AnalysisResult.element_forces`).
  - GREEN: Fix any remaining mesh-node sharing gaps causing load bypass (expected primarily in Task 5).
  - REFACTOR: Keep test stable (avoid brittle exact values; assert non-zero with tolerances).

  **Must NOT do**:
  - Do not “fake” beam forces by applying area loads as beam line loads; requirement is mesh-based load application.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `testing-patterns`

  **Parallelization**:
  - Can Run In Parallel: NO
  - Parallel Group: Wave 3
  - Blocked By: Task 5
  - Blocks: Task 7

  **References**:
  - `src/fem/model_builder.py` `_apply_slab_surface_loads(...)`
  - `src/fem/fem_engine.py` surface load → nodal load conversion
  - `src/fem/solver.py` `analyze_model(...)`
  - UI consumer: `src/ui/components/beam_forces_table.py`

  **Acceptance Criteria**:
  - [ ] New integration test passes: beam forces are present and not all ~0 under slab loads.
  - [ ] Optional: total vertical reactions approximately match total applied slab load (+ self-weight) within tolerance.

- [x] 7. Add Column Section Forces table + make overlays consistent with tables (TDD + Playwright QA)

  **What to do (RED → GREEN → REFACTOR)**:
  - RED:
    - Add tests for column force extraction/grouping by `parent_column_id` and that resulting DataFrame is non-empty after analysis.
    - Add Playwright regression flow for new expander presence.
  - GREEN:
    - Create `src/ui/components/column_forces_table.py` mirroring `BeamForcesTable` but grouping by `parent_column_id`.
    - Integrate into `src/ui/views/fem_views.py` as a new expander near beam forces.
    - Ensure Plotly overlays (Plan/Elevation) use the shared normalization from Task 3.
  - REFACTOR:
    - Keep UI consistent: filters (floor, element selector), export buttons.

  **Must NOT do**:
  - Do not introduce a separate force extraction path for overlays; keep one canonical normalization.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: `playwright`, `testing-patterns`

  **Parallelization**:
  - Can Run In Parallel: NO
  - Parallel Group: Wave 3
  - Blocked By: Task 6

  **References**:
  - `src/ui/components/beam_forces_table.py` (template for UI + extraction)
  - `src/fem/builders/column_builder.py` geometry keys: `parent_column_id`, `sub_element_index`
  - `src/fem/model_builder.py` column creation geometry keys (same)
  - `src/ui/views/fem_views.py` beam table integration area
  - Existing Playwright: `tests/playwright_beam_table_test.js` (expander + table selectors)

  **Acceptance Criteria**:
  - [ ] Column forces expander renders after analysis.
  - [ ] Column table shows non-empty forces for at least one column under DL.
  - [ ] Plotly overlays for selected force component match normalized table conventions.

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Beam + Column tables and overlays consistent
    Tool: Playwright
    Preconditions: streamlit app runnable locally
    Steps:
      1. Launch app at http://localhost:8501
      2. Click button with role "button" name /Run FEM Analysis/i
      3. Open expander "Beam Section Forces" and confirm dataframe visible
      4. Open expander "Column Section Forces" and confirm dataframe visible
      5. In "Display Options", set "Force Type" radio to "M-minor (Weak Axis)"
      6. Confirm Plan/Elevation overlay shows force labels (not empty)
      7. Screenshot evidence
    Evidence:
      - .sisyphus/evidence/task-7-beam-table.png
      - .sisyphus/evidence/task-7-column-table.png
      - .sisyphus/evidence/task-7-overlay.png
  ```

---

## Commit Strategy

Suggested atomic commits (optional, executor-controlled):
1. `fix(fem): extract node reactions via ops.reactions()`
2. `fix(fem): preserve rectangular column width/depth`  
3. `refactor(fem): unify section force normalization across tables/overlays`
4. `feat(fem): switch line discretization to 5 nodes`  
5. `feat(fem): align slab mesh divisions to beam nodes`  
6. `test(fem): add load-transfer integration coverage`  
7. `feat(ui): add column section forces table`

---

## Success Criteria

### Verification Commands
```bash
pytest tests/ -v
```

### Final Checklist
- [x] Beams + columns discretized to 5 nodes (4 sub-elements)
- [x] Slab mesh aligned to beam node positions (no `0.1L` sizing)
- [x] Beam forces table non-empty and non-zero under slab loads
- [x] Plotly overlays match table normalization/sign conventions
- [x] Reaction forces extracted and visible for all load cases
- [x] Rectangular column input respected in FEM model
