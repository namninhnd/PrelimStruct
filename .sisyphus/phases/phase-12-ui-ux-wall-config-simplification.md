# Phase 12: UI/UX Cleanup + Wall Configuration Simplification

## Status: COMPLETE — All Gates A-F Passed (2026-02-11)

## User Clarification (Authoritative)

- Remove `Key Metrics` from app dashboard (`app.py`).
- Legacy core-wall variants are removed (no variant remapping).
- Tube opening dimensions are shared across `TOP` / `BOTTOM` / `BOTH` placement.
- `Tube with Openings` is center-opening canonical only in this phase.
- Core location UX is presets-only; hidden compatibility remains for legacy custom-location data.
- Side/corner placement follows bounding-box clearance rule.
- Update both UI paths: `app.py` and `src/ui/sidebar.py`.
- Lock behavior disables all editable controls when FEM inputs are locked.

---

## 1. Problem Statement

Current input UX has redundant controls and split logic across runtime and modular paths:

- `Quick Presets` and related dropdowns add clutter.
- Wind-load inputs are located in FEM views instead of the `Lateral System` input block.
- Lock UX is inconsistent: `Unlock to Modify` is conditional and helper caption remains when unlocked.
- Core-wall model includes five legacy variants that no longer match desired UX/domain constraints.
- Core location allows free custom placement, but target behavior requires constrained presets.

This phase simplifies UI and domain model while preserving FEM correctness and stable behavior.

---

## 2. Current State (Verified)

| Area | File | Current Behavior |
|------|------|------------------|
| Runtime sidebar + main dashboard | `app.py` | Contains `Quick Presets`, `Key Metrics`, and primary page flow |
| Modular sidebar path | `src/ui/sidebar.py` | Duplicate/parallel input controls and lateral system block |
| Wind-load inputs | `src/ui/views/fem_views.py` | `Wind Loads` expander with `Manual` (`Vx`, `Vy`, `q0`) and `HK Code Calculator` (`q0`, `Cf`) modes |
| FEM lock controls | `src/ui/views/fem_views.py` | Conditional unlock button + `Run analysis to lock inputs` caption |
| Core location UI | `src/ui/sidebar.py`, `src/core/data_models.py` | Two modes today: `Center` + `Custom` free-form `X/Y` |
| Core-wall enum | `src/core/data_models.py` | Five config variants (`I`, `TWO_C_*`, `TUBE_*`) |
| FEM geometry/builders | `src/fem/core_wall_geometry.py`, `src/fem/model_builder.py`, `src/fem/core_wall_helpers.py`, `src/fem/builders/core_wall_builder.py`, `src/fem/builders/beam_builder.py`, `src/fem/builders/director.py` | Dispatch and calculations tied to old variants |
| Downstream coupling/trim logic | `src/fem/coupling_beam.py`, `src/fem/beam_trimmer.py` | Variant-specific behavior |

---

## 3. Phase Goal

Deliver one coherent UI/domain workflow:

1. Keep only relevant Page 1 inputs and remove redundant controls.
2. Place wind-load inputs in `Lateral System` above `Core Wall System`.
3. Always render `Unlock to Modify` button, disabled before lock and enabled after lock.
4. Remove app dashboard `Key Metrics` section.
5. Reduce wall configurations to two canonical options:
   - `I-section`
   - `Tube with Openings`
6. Support tube opening placement modes `TOP`, `BOTTOM`, `BOTH` with shared dimensions.
7. Restrict core location to exactly 9 presets (center + 4 side middles + 4 corners).

---

## 4. Scope

### In Scope

1. Runtime and modular UI cleanup (`app.py`, `src/ui/sidebar.py`, `src/ui/views/fem_views.py`).
2. Core-wall domain/model simplification and constraints.
3. FEM geometry/helper/builder remapping to new model.
4. Legacy compatibility policy:
   - remove old wall variants (explicit rejection)
   - preserve hidden compatibility for legacy custom-location values.
5. Tests-after updates (unit/integration/UI/regression).

### Out of Scope

1. Canonical W1-W24 wind synthesis/combination pipeline changes.
2. Solver/load-physics redesign.
3. Broad report redesign beyond required fallout fixes.

---

## 5. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary UI paths | Update both `app.py` and `src/ui/sidebar.py` | Prevent runtime/modular drift |
| Lock UX | Always show `Unlock to Modify`; disable before lock | Clearer interaction contract |
| Wall variants | Keep only `I_SECTION` and `TUBE_WITH_OPENINGS` | Reduced complexity and clearer UX |
| Tube openings | `TOP` / `BOTTOM` / `BOTH` placement, shared dimensions | Minimal parameter surface |
| Tube geometry basis | Canonical `TUBE_WITH_OPENINGS` uses former center-opening cross-section path only | Removes center-vs-side ambiguity in this phase |
| Core location | 9 presets only, no free-form UI input | Constrained and predictable placement |
| Legacy handling | Remove old variants; keep custom-location compatibility | Matches user intent + safer existing data handling |
| Placement rule | Bounding-box clearance for side/corner placements | Prevents out-of-footprint geometry |

### 5.1 Lock-State Contract (Mandatory)

- Source of truth remains `st.session_state["fem_inputs_locked"]`.
- When locked: all editable controls are disabled.
- `Unlock to Modify` remains visible and enabled as the sole edit-action control.

### 5.2 Legacy Compatibility Contract (Mandatory)

- Legacy wall variants are rejected explicitly (no silent remap).
- Legacy custom-location values map deterministically to nearest preset with tie-break order:
  `CENTER` -> side-middle presets (clockwise) -> corner presets (clockwise).

### 5.3 Tube-With-Openings Semantics (Mandatory)

- `TOP` / `BOTTOM` / `BOTH` define opening placement within the canonical tube profile.
- In Phase 12, `TUBE_WITH_OPENINGS` routes through the former center-opening geometry/coupling path.
- Former side-opening variant is retired with legacy variants and is not silently remapped.

---

## 6. Implementation Plan

### Step 1: Runtime + Modular UI Cleanup

**Files**
- `app.py`
- `src/ui/sidebar.py`
- `src/ui/views/fem_views.py`

**Actions**
1. Remove `Quick Presets` and related building-type dropdown controls.
2. Move wind-load controls from FEM `Wind Loads` expander into sidebar `Lateral System`, directly below `Terrain Category` and above `Core Wall System`.
3. Move both wind input modes and fields:
   - `Manual`: `Base Shear Vx`, `Base Shear Vy`, `Reference Pressure q0`
   - `HK Code Calculator`: `Reference Pressure q0`, `Force Coefficient Cf`
4. Remove wind-input editing controls from `src/ui/views/fem_views.py`; keep only read-only status/result display there.
5. Ensure relocated wind controls also honor lock state (`disabled=inputs_locked`).
6. Remove app dashboard `Key Metrics` block.
7. Replace helper caption-based lock hint with always-present unlock button behavior.

### Step 2: Core-Wall Model Simplification

**Files**
- `src/core/data_models.py`
- `src/ui/project_builder.py`
- `src/ui/components/core_wall_selector.py`

**Actions**
1. Narrow wall config enum to two options.
2. Add tube opening placement field.
3. Replace free custom location mode with 9 presets in UI.
4. Keep hidden compatibility for legacy custom-location inputs.

### Step 3: FEM Remap for New Core-Wall Model

**Files**
- `src/fem/core_wall_geometry.py`
- `src/fem/model_builder.py`
- `src/fem/core_wall_helpers.py`
- `src/fem/beam_trimmer.py`
- `src/fem/coupling_beam.py`
- `src/fem/builders/core_wall_builder.py`
- `src/fem/builders/beam_builder.py`
- `src/fem/builders/director.py`

**Actions**
1. Update dispatch/extraction paths for two-option model.
2. Route `TUBE_WITH_OPENINGS` to canonical center-opening geometry/coupling path in this phase.
3. Implement opening placement behavior (`TOP`/`BOTTOM`/`BOTH`) with shared dimensions.
4. Preserve deterministic section/property generation and panel extraction.

### Step 4: Tests-After and Regression

**Files**
- `tests/test_core_wall_data_models.py`
- `tests/test_core_wall_geometry.py`
- `tests/test_model_builder.py`
- `tests/test_coupling_beam.py`
- `tests/test_beam_trimmer.py`
- `tests/ui/test_core_wall_selector.py`
- `tests/ui/test_fem_views_state.py`
- `tests/ui/test_sidebar_cleanup.py` (new)

**Actions**
1. Update legacy assumptions to new canonical options.
2. Add tests for explicit rejection of removed variants.
3. Add tests for compatibility mapping of legacy custom-location values.
4. Add UI lock-behavior assertions and sidebar cleanup assertions.

---

## 7. Test Plan

### New/Expanded Tests

1. `tests/ui/test_sidebar_cleanup.py`
   - Ensure no `Quick Presets`
   - Ensure wind controls appear in `Lateral System` before core controls
   - Ensure no free-form location mode
2. Legacy compatibility tests
   - Explicit rejection of removed variants
   - Deterministic mapping of legacy custom-location data
   - Explicit assertion that side-opening legacy variant is rejected (no remap)

### Updated Tests

1. `tests/test_core_wall_data_models.py`
2. `tests/test_core_wall_geometry.py`
3. `tests/test_model_builder.py`
4. `tests/test_coupling_beam.py`
5. `tests/test_beam_trimmer.py`
6. `tests/ui/test_core_wall_selector.py`
7. `tests/ui/test_fem_views_state.py`

---

## 8. Acceptance Gates

All must pass:

1. Runtime and modular UI paths both reflect sidebar cleanup and wind-input relocation.
2. `Unlock to Modify` is always visible; lock behavior disables all editable controls.
3. App dashboard `Key Metrics` section is removed.
4. Only two core-wall options remain in canonical model and selector UI.
5. Tube opening placement supports `TOP`/`BOTTOM`/`BOTH` with shared dimensions only.
6. Core location UI supports exactly 9 presets; no free-form location input.
7. Removed legacy wall variants are explicitly rejected; no silent remap.
8. Legacy custom-location compatibility mapping is deterministic and tested.
9. Builder-layer remap files (`core_wall_builder.py`, `beam_builder.py`, `director.py`) are updated and covered by tests.
10. Targeted and broader regression suites pass.

---

## 9. Risks and Controls

| Risk | Impact | Control |
|------|--------|---------|
| Runtime/modular UI drift | Inconsistent behavior across entry paths | Update and test both paths explicitly |
| Silent coercion of removed variants | Hidden incorrect modeling | Explicit validation failure + tests |
| Lock-state regressions | Inputs editable when they should be locked | Central lock assertions + UI tests |
| Placement edge cases near boundaries | Core extends out of footprint | Bounding-box clearance rule + compatibility tests |
| Coupling/trim behavior drift | Incorrect FEM topology/forces | Targeted geometry + builder + coupling tests |

---

## 10. Deliverables

1. Phase 12 planning/spec document (this file).
2. Phase 12A execution log template with gate/evidence structure.
3. Implementation-ready gate checklist aligned to user-confirmed constraints.

---

## 11. Follow-On (Not in This Phase)

### Existing Items

1. Optional full retirement of duplicate modular runtime path.
2. Expanded report-level UX simplification beyond immediate fallout.
3. Additional E2E visual regression automation for broader dashboard modules.

### Items Surfaced During Phase 12A Execution

4. **Slab mesh does not exclude core wall void area.**
   `tests/test_slab_wall_connectivity.py::test_slab_wall_connectivity` fails with "28 slab elements generated INSIDE the core wall void." This is a pre-existing issue — slab mesh generation creates elements inside the core wall footprint. Confirmed identical on baseline (before any Phase 12A changes). Root cause: `build_fem_model` slab meshing path does not subtract the core wall bounding box from the slab region. Affects structural accuracy when slabs and core walls coexist.

5. **Pre-existing LSP / type errors (37 total across 7 files).**
   Frozen baseline documented in Phase 12A execution log, Section 4 Gate D. Key clusters:
   - `src/fem/core_wall_geometry.py:566-570` — `SlabOpening` constructor call uses wrong parameter names (`x`, `y`, `width`, `height` instead of `opening_id`, `origin`, `width_x`, `width_y`). 5 errors. This likely causes a runtime failure in `_get_core_opening_for_slab()` and may be related to item 4 above.
   - `src/ui/project_builder.py` — `loading_pattern_factor` parameter removed but still passed (1 error); `BeamResult`/`ColumnResult` constructor calls missing `element_type`/`size` (4 errors); `Any | None` not assignable to `float` for `length_x`/`length_y` (2 errors).
   - `src/report/report_generator.py` — `.name` accessed on `str` instead of enum (2 errors); missing generic type arguments (6 errors); `HAS_AI_INTERPRETER` constant redefinition (1 error); dict type mismatch (1 error).
   - `src/fem/builders/core_wall_builder.py:127` — `list[int] | None` vs `List[int]` type mismatch for restraints (1 error).
   - `tests/conftest.py:165` and `tests/test_integration_e2e.py:477-534` — test-side type issues (13 errors).

6. **Skipped legacy coupling beam tests.**
   3 tests in `tests/test_coupling_beam.py` are marked `@pytest.mark.skip` with reason strings referencing retired variants (`TWO_C_BACK_TO_BACK`, `TUBE_SIDE_OPENING`, `TWO_C_FACING`). These are documentation-only stubs. Future cleanup should either delete them or rewrite them as meaningful `TUBE_WITH_OPENINGS` placement tests.

7. **Archived test file hygiene.**
   Files in `tests/archived/` (`test_feature2.py`, `test_dashboard.py`, `test_feature5.py`) have longstanding import errors for removed classes (e.g., `CouplingBeamEngine`). These are not executed in CI but create noise during static analysis. Consider deletion or quarantine.

---

## 12. Documentation Quality Controls (Phase 12 + 12A)

Apply these quality controls while executing Phase 12A:

1. Gate coverage: every Phase 12 gate appears exactly once in Phase 12A results.
2. Evidence completeness: each closed gate has required evidence IDs (code/test/ops as applicable).
3. Evidence immutability: prefer commit-pinned permalinks or timestamped command evidence over floating references.
4. Rollback readiness: medium/high-risk gates include trigger + rollback steps.
5. Acceptance strictness: PASS only when all pass criteria are met (else FAIL or WAIVED).
6. Waiver hygiene: each waiver includes ID, approver, expiry, and compensating control.
7. Signoff integrity: required signoffs are present before final completion status.
8. Timeline integrity: Phase 12A remains append-only and chronological; corrections are additive.
