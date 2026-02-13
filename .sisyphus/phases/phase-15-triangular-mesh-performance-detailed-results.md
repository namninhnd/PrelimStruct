# Phase 15 - Triangular Shell Toggle, Runtime Optimization, Detailed Results Refresh

## TL;DR

> **Quick Summary**: Add an opt-in triangular shell mode (default stays current quad `ShellMITC4`) and optimize multi-floor runtime by profiling first and removing proven bottlenecks (especially per-load-case model rebuilds). Refresh Streamlit `Detailed Results` to reflect current data model changes.
>
> **Deliverables**:
> - Opt-in `tri` shell mode for slabs + core walls (triangles derived from existing quad mesh to preserve node-sharing)
> - Correct shell surface load application for tri elements (area + nodal distribution)
> - Visualization + validation updates for mixed quad/tri shells
> - Runtime improvement path validated by benchmarks (primary KPI: `<60s` on 30 floors)
> - Updated `app.py` "Detailed Results" tabs to match current schema (e.g., rectangular columns)
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES (2 waves)
> **Critical Path**: Baseline profiling gate -> tri toggle plumbing + load conversion -> solver bottleneck fix -> regression + benchmark gates

---

## Context

### Original Request
- Phase 15: switch shell meshing to triangular mesh so shells integrate with beam/wall/column nodes more robustly and support coarse/fine control.
- Speed up multi-floor runs; do not rely on meshing change alone.
- Update Streamlit "Detailed Results" since it has fallen behind recent changes.

### Key Decisions (confirmed)
- **Performance target**: `<60s` for a 30-floor run using `scripts/benchmark.py`.
- **Rollout**: Triangular shell support ships as an **optional toggle** first (default remains current quad/ShellMITC4 behavior).
- **Testing**: **TDD** with pytest.

### Baseline Architecture Facts (verified)
- Current shell element is quad-only: `ElementType.SHELL_MITC4` / `ShellMITC4`.
  - Wall mesh: `src/fem/model_builder.py:1954` uses `WallMeshGenerator.generate_mesh(... registry=registry)`.
  - Slab mesh: `src/fem/builders/slab_builder.py:136` uses `SlabMeshGenerator.generate_mesh(...)`.
- Major runtime bottleneck: per-load-case OpenSees wipe + rebuild:
  - `src/fem/solver.py:408` wipes and rebuilds per load case.
  - `src/fem/fem_engine.py:360` always calls `ops.wipe()` inside `FEMModel.build_openseespy_model()`, so solving this requires refactoring the model build phases (structure vs loads vs analysis).
- Detailed Results UI tabs: `app.py:1958` (`Slab`, `Beams`, `Columns`, `Lateral`).

### External Element Research (triangular shells)
- Valid triangular shell elements for 3D shells include `ShellDKGT`, `ShellNLDKGT`, `ASDShellT3`.
- `Tri31` is 2D plane stress/strain (not a shell); do not use for walls/slabs.

---

## Work Objectives

### Core Objective
1) Enable triangular shell discretization as a safe opt-in mode without breaking default behavior.
2) Improve multi-floor runtime to meet `<60s` for 30 floors by fixing measured hotspots.
3) Ensure Streamlit Detailed Results reflects current data model semantics.

### Must NOT Have (Guardrails)
- Default behavior must remain quad/ShellMITC4 unless tri mode explicitly enabled.
- Do not change engineering design outputs/logic beyond what is necessary for mesh/solver parity.
- Do not modify `repos/*`.
- No manual verification language in acceptance criteria; all verification is agent-executed.
- Do not introduce scattered mesh-density knobs; define config once and thread through.

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: YES (TDD)

### Global Benchmarks / Evidence (agent-executable)

Primary KPI A (runtime, required):
```bash
python scripts/benchmark.py --floors 30 --timeout 60
# Expected: exit code 0 AND output contains a PASS line for 30 floors
```

Primary KPI B (wind multi-case runtime, required):
```bash
# Proposed new benchmark mode to add in this phase (see Task 1 / Task 6)
python scripts/benchmark.py --floors 30 --timeout 60 --wind
# Expected:
# - completes successfully
# - runs base wind cases (Wx/Wy/Wtz) plus gravity cases (DL/SDL/LL)
# - synthesizes W1-W24 in Python (no extra OpenSees solves), so the benchmark also verifies those keys exist
```

Profiling artifacts (before/after):
```bash
python -m cProfile -o .sisyphus/evidence/phase-15/before.prof scripts/benchmark.py --floors 30 --timeout 600 --wind
python -m cProfile -o .sisyphus/evidence/phase-15/after.prof scripts/benchmark.py --floors 30 --timeout 600 --wind
# Expected: both files exist and are non-empty
```

Solvability/regression gates:
```bash
pytest tests/test_gate_i_fem_solvability.py -q
pytest tests/verification/test_equilibrium_1x1.py tests/verification/test_equilibrium_2x3.py -q
```

Tri-toggle dedicated regressions (to be added in this phase):
```bash
pytest tests/test_tri_shell_toggle.py -q
```

---

## Execution Strategy

Wave 0 (Profiling Gate - MUST happen first):
- Task 1

Wave 1 (Tri toggle + correctness + cache/visualization compatibility):
- Task 2, 3, 4, 5

Wave 2 (Runtime optimization + Detailed Results refresh + final benchmarks):
- Task 6, 7, 8

Critical Path: Task 1 -> Task 2 -> Task 4 -> Task 6 -> Task 8

---

## TODOs

- [ ] 1. Baseline timing + profiling evidence for 30-floor benchmark (TDD/bench-first)

  **What to do (RED -> GREEN -> REFACTOR)**:
  - RED: Add a pytest (or lightweight harness test) that executes `scripts/benchmark.py --floors 30 --timeout 600` in a subprocess and asserts it completes successfully (skip if OpenSeesPy not installed).
  - RED: Add a gate test that verifies the triangular shell element is available before running tri-mode tests (skip tri tests if not available).
  - GREEN: Add cProfile run commands to emit `.sisyphus/evidence/phase-15/before.prof`.
  - REFACTOR: Keep results parsing stable; do not assert exact seconds yet.

  **Recommended Agent Profile**:
  - Category: `quick`
  - Skills: `testing-patterns`, `clean-code`

  **References**:
  - `scripts/benchmark.py` - canonical perf target harness
  - `src/fem/solver.py:321` - analyze_model entrypoint used by benchmark
  - `src/fem/fem_engine.py:360` - builder currently wipes OpenSees domain

  **Acceptance Criteria**:
  - [ ] `python -m cProfile -o .sisyphus/evidence/phase-15/before.prof scripts/benchmark.py --floors 30 --timeout 600 --wind` produces non-empty profile file
  - [ ] `python scripts/benchmark.py --floors 30 --timeout 60` runs and reports success (or is skipped deterministically if OpenSeesPy unavailable)
  - [ ] `python scripts/benchmark.py --floors 30 --timeout 60 --wind` runs and reports success (or is skipped deterministically if OpenSeesPy unavailable)
  - [ ] Tri-element availability gate:
    - A new test (or script) attempts to create a minimal OpenSees model with one `ShellDKGT` element; if OpenSees raises “unknown element” it marks tri-mode tests as skipped with a clear message.


- [ ] 2. Add mesh configuration knobs (type + density) in one place; thread into model build (TDD)

  **What to do**:
  - Introduce a single options surface (extend `ModelBuilderOptions`) to include:
    - `shell_mesh_type`: `"quad" | "tri"` (default `"quad"`)
    - `shell_mesh_density`: `"coarse" | "medium" | "fine"` (default `"medium"`)
  - Ensure this feeds both:
    - direct runtime path: `src/fem/model_builder.py` wall/slab generation
    - builder/director path: `src/fem/builders/core_wall_builder.py`, `src/fem/builders/slab_builder.py`
  - Add to FEM cache key so toggling forces a rebuild.

  **Must NOT do**:
  - Do not create separate per-module density flags (avoid knob sprawl).

  **Recommended Agent Profile**:
  - Category: `deep`
  - Skills: `python-patterns`, `clean-code`, `testing-patterns`

  **References**:
  - `src/fem/model_builder.py:1954` - wall mesh generation config is currently hardcoded
  - `src/fem/builders/slab_builder.py:140` - slab density currently uses `slab_elements_per_bay`
  - `src/ui/views/fem_views.py:51` - model cache key; must include new mesh toggles

  **Acceptance Criteria**:
  - [ ] New tests cover default options (quad path unchanged)
  - [ ] Changing `shell_mesh_type` changes the cache key and triggers rebuild


- [ ] 3. Implement tri shells via quad-splitting (preserve node-sharing) (TDD)

  **What to do**:
  - Keep existing node generation for slabs and walls.
  - Convert each quad shell element into 2 triangular shell elements by splitting along a consistent diagonal (document the rule).
  - Add a new FEM element type for tri shells (e.g., `ElementType.SHELL_DKGT_T3`) and implement OpenSees element creation for it.
  - Default element choice for v1 tri mode: `ShellDKGT` (simple, linear static). Do not attempt geometric nonlinearity in Phase 15.

  **Risk / Why this approach**:
  - Minimizes changes to connectivity: beam/slab node sharing and wall NodeRegistry reuse remain valid.
  - Enables coarse/fine control by changing element counts (density) without needing unstructured meshing.

  **Recommended Agent Profile**:
  - Category: `deep`
  - Skills: `python-patterns`, `clean-code`, `testing-patterns`

  **References**:
  - `src/fem/slab_element.py:117` - `SlabQuad` definition (4-node)
  - `src/fem/wall_element.py:71` - `ShellQuad` definition (4-node)
  - `src/fem/fem_engine.py` - current ShellMITC4 element build path; add tri path
  - External: https://openseespydoc.readthedocs.io/en/latest/src/ShellDKGT.html

  **Acceptance Criteria**:
  - [ ] With `shell_mesh_type="quad"`, node/element counts and element types match baseline (regression test)
  - [ ] With `shell_mesh_type="tri"`, slab and wall shells are created as triangles and model validates

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Tri toggle builds a solvable model
    Tool: Bash (pytest)
    Preconditions: OpenSeesPy installed
    Steps:
      1. pytest tests/test_tri_shell_toggle.py -q
      2. Assert: quad default test passes
      3. Assert: tri toggle test passes and analysis_result.success is True
    Expected Result: Both modes work; default unchanged
  ```


- [ ] 4. Fix shell surface load conversion for tri shells (TDD)

  **What to do**:
  - Update shell pressure -> nodal load distribution to handle 3-node shells:
    - correct element area computation
    - distribute pressure*area across 3 nodes instead of 4
  - Remove quad-only guards so SurfaceLoad can apply to both quad and tri shell element types.
  - Ensure pressure sign convention remains consistent with existing docstrings.

  **References**:
  - `src/fem/fem_engine.py:546` SurfaceLoad -> equivalent nodal load conversion (currently hard-guarded for ShellMITC4 + 4 nodes)
  - `src/fem/builders/slab_builder.py:241` surface load application uses `SurfaceLoad(pressure=...)`

  **Acceptance Criteria**:
  - [ ] Equilibrium tests remain green in both quad and tri modes:
    - `pytest tests/verification/test_equilibrium_1x1.py tests/verification/test_equilibrium_2x3.py -q`


- [ ] 5. Update visualization + validation + opsvis pruning to support tri shells (TDD)

  **What to do**:
  - Update any hard-coded `len(nodes)==4` shell assumptions to also recognize 3-node shells.
  - Ensure pruning for opsvis does not misclassify tri shells.
  - Update validation scripts / helpers if they report element counts/types.

  **References**:
  - Shell pruning for opsvis currently treats shells as 4-node only:
    - `src/fem/visualization.py:143` and `src/fem/visualization.py:186`
  - Additional quad-only rendering guards to audit/extend for tri shells:
    - `src/fem/visualization.py:1825`
    - `src/fem/visualization.py:2241`
    - `src/fem/visualization.py:2869`
    - `src/fem/visualization.py:2873`
    - `src/fem/visualization.py:3597`
    - `src/fem/visualization.py:3837`
  - `scripts/validate_shell_elements.py:181` - element type labeling

  **Acceptance Criteria**:
  - [ ] Plan/Elevation/3D views still render without exceptions in quad and tri modes (pytest/UI harness)
  - [ ] No crashes when opsvis mode is toggled on after analysis


- [ ] 6. Runtime optimization: eliminate unnecessary per-load-case full rebuilds (profile-driven) (TDD)

  **What to do**:
  - Measure time spent in build vs solve vs extraction using Task 1 artifacts.
  - Refactor the build/analyze pipeline to avoid rebuilding the structural domain for each load case.
    - Current issue: `_run_single_load_case()` wipes and rebuilds per case (`src/fem/solver.py:408`), and `build_openseespy_model()` itself wipes the OpenSees domain (`src/fem/fem_engine.py:360`).
  - Describe and implement **Option C: build-all-patterns-once** (plus a safer fallback):
    - **Option C (preferred for linear static)**: Build structure once + define all load patterns once; then solve each case by (a) clearing analysis state (`ops.wipeAnalysis()`), (b) removing/recreating only the active pattern(s) OR scaling factors via time series, and (c) running `ops.analyze(1)`.
    - **Safer fallback**: Build structure once; per case remove and recreate patterns (`ops.remove('loadPattern', pid)`, `ops.setTime(0.0)`), then run analysis.
  - Keep correctness gates: solvability + equilibrium + tri parity tests.
  - Keep correctness gates: solvability + equilibrium + tri parity tests.

  **Must NOT do**:
  - Do not remove load cases to appear faster.
  - Do not change load-pattern IDs.

  **References**:
  - `src/fem/solver.py:408` - current wipe/rebuild loop
  - `src/fem/fem_engine.py:337` - `build_openseespy_model(...)` entrypoint
  - `src/fem/fem_engine.py:360` - `ops.wipe()` inside builder (must be refactored)
  - `src/ui/views/fem_views.py:450` - UI runs DL/SDL/LL (+ wind) load cases
  - `scripts/benchmark.py:113` - benchmark uses analyze_model() (combined)

  **Acceptance Criteria**:
  - [ ] `python scripts/benchmark.py --floors 30 --timeout 60` completes successfully and is <= 60s on the target machine
  - [ ] `python scripts/benchmark.py --floors 30 --timeout 60 --wind` completes successfully and is <= 60s on the target machine
  - [ ] Profiling shows meaningful reduction in time spent in repeated model build steps (compare before.prof vs after.prof)
  - [ ] Wind-enabled benchmark mode is implemented and required (covers base wind cases + W1-W24 synthesis)


- [ ] 7. Refresh Streamlit "Detailed Results" tabs to match current schema + semantics (TDD/UI)

  **What to do**:
  - Update `app.py` Detailed Results to reflect current data model changes and avoid stale assumptions.
  - Concrete known stale issue: Columns tab assumes square `dimension x dimension`; update to display rectangular width/depth when available.
  - Ensure displayed values remain read-only and do not change design logic.

  **References**:
  - `app.py:1958` - Detailed Results tabs
  - `app.py:2041` - column size display logic
  - `src/ui/views/fem_views.py` - newer analysis tables exist; ensure no confusion between design summary vs FEM tables

  **Acceptance Criteria**:
  - [ ] New UI regression test asserts that when `project.column_result.width/depth` are set, the UI renders `width x depth` (not `dimension x dimension`).

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Detailed Results shows rectangular columns
    Tool: Playwright (playwright skill)
    Preconditions: `streamlit run app.py` serving locally
    Steps:
      1. Navigate to: http://localhost:8501
      2. Set column width/depth overrides in sidebar to a rectangle (e.g., 500x800)
      3. Scroll to "Detailed Results" and open "Columns" tab
      4. Assert: text contains "500 x 800 mm" (or equivalent formatting)
      5. Screenshot: .sisyphus/evidence/phase-15/detailed-results-rect-column.png
    Expected Result: UI no longer assumes square columns
  ```


- [ ] 8. Final parity + performance closure (TDD)

  **What to do**:
  - Add a tri-vs-quad parity test for global responses (tolerances) on a small model.
    - Suggested tolerance defaults (overrideable): reactions/base shear/max displacement within 5%.
  - Re-run full benchmark suite (10/20/30) and record results into `.sisyphus/evidence/phase-15/`.

  **References**:
  - `scripts/benchmark.py` - canonical performance harness
  - `tests/test_gate_i_fem_solvability.py` - solvability regression

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_tri_shell_toggle.py -q` passes with parity checks
  - [ ] `python scripts/benchmark.py --all --timeout 60` completes and 30-floor case meets target

---

## Success Criteria

- Performance: 30 floors completes in `<60s` for BOTH:
  - `python scripts/benchmark.py --floors 30 --timeout 60`
  - `python scripts/benchmark.py --floors 30 --timeout 60 --wind` (includes Wx/Wy/Wtz solves and W1-W24 synthesis)
- Safety: default quad mode is unchanged (tests prove it).
- Correctness: equilibrium + solvability suites pass in both modes.
- UX: `app.py` Detailed Results no longer assumes square columns; reflects current schema.
