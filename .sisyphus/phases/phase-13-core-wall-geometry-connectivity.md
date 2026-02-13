# Phase 13: Core Wall Geometry, Beam Connectivity, Slab Exclusion, and Wind Traceability

## Status: COMPLETE (Gates A-J complete in phase-13a execution log)

## Origin

Issues identified during manual application testing after Phase 12A completion (2026-02-11).

## Execution Snapshot (Phase 13A)

- 2026-02-12: Gate A completed in `.sisyphus/phases/phase-13a-execution-log.md`.
- Baseline frozen: branch/worktree snapshot captured, issue-to-code anchors recorded, and baseline targeted checks passed.
- 2026-02-12: Gate B completed. Canonical I-section orientation contract frozen in ISectionCoreWall docstring.
  Wall node registration implemented in core_wall_builder.py (register_existing). Congruence test added.
- 2026-02-12: Gate C completed. All 8 trim tests pass including concave 4-intersection case.
  Interior beam suppression test added: zero non-coupling beams inside tube footprint.
- 2026-02-12: Gate D completed. I-section coupling generates 2 parallel beams (test passes).
  Endpoint connectivity integration test confirms coupling endpoints share wall mesh nodes.
- 2026-02-12: Gate E completed. Tube opening placement propagation verified across geometry, wall panels, and coupling behavior.
- 2026-02-12: Gate F completed. Slab exclusion now uses full core footprint for I-section and tube.
- 2026-02-12: Gate G completed. UI defaults aligned to 3.0m × 3.0m with semantic consistency checks.
- 2026-02-12: Gate H completed. Wind read-only traceability and per-floor load details added with regression coverage.
- 2026-02-12: Gate I completed. Representative I-section and tube solve-path checks pass with no singular-matrix message.
- 2026-02-12: Gate J completed. Trim re-run + targeted regression matrix + broader verification sweep all pass; phase signoff finalized.

Screenshots provided as evidence:
- `audit_screenshots/newplot (1).png`
- `audit_screenshots/newplot (2).png`
- `audit_screenshots/newplot (3).png`
- `audit_screenshots/tube1.png`
- `audit_screenshots/tube2.png`

---

## 1. Problem Statement

Phase 12A simplified the core wall model to `I_SECTION` and `TUBE_WITH_OPENINGS`, but current behavior still has geometry/connectivity defects and missing wind-detail traceability.

User-reported issues to resolve in this phase:

1. **Wind Loads (read-only) is not explainable** - no calculation trace for design (factored) wind pressure and no per-floor `Wx`, `Wy`, `Wtz` breakdown.
2. **Core wall defaults are not aligned with required startup values** - current defaults are not `3m x 3m` for both I-section and tube dimensions.
3. **I-section still allows slab inside core footprint**.
4. **I-section input semantics are confusing/misaligned in practice** - "Flange Width" and "Web Length" behavior appears swapped to users.
5. **I-section beam trimming fails for many flange-intersection scenarios** - endpoint intersections trim correctly, but non-endpoint flange intersections can leave untrimmed split beams.
6. **I-section is missing required coupling beam topology** - should have 2 parallel coupling beams connecting the 4 flange ends.
7. **Tube opening placement effectively works only for `BOTH`** - `TOP` and `BOTTOM` are not consistently reflected across geometry + wall panels + coupling behavior.
8. **Tube model still contains unwanted interior beam(s)** - non-coupling beam crossing openings/inside tube appears; only coupling beams around opening regions should remain.
9. **Tube still shows slab inside core footprint**.
10. **FEM solve fails with singular matrix** (`BandGenLinLapackSolver ... matrix singular U(i,i)=0`) when core wall is enabled.
11. **I-section geometric interpretation is inconsistent across subsystems** - outline-based trim logic and wall panel builders use different orientation assumptions.
12. **Coupling beam endpoints may be disconnected from wall mesh nodes** - can create floating/duplicate nodes and singular solve paths.

---

## 2. Baseline State (Pre-Execution Snapshot)

Note: This table captures the verified baseline before Phase 13A gate execution. Refer to `.sisyphus/phases/phase-13a-execution-log.md` for current post-fix status and evidence.

| Area | File(s) | Current Behavior | Issue |
|------|---------|------------------|-------|
| Wind read-only display | `src/ui/views/fem_views.py:250-263` | Shows only `Vx`, `Vy`, `q0` summary values | Missing calculation trace and per-floor `Wx`, `Wy`, `Wtz` |
| UI defaults (I-section) | `app.py:1398-1405`, `src/ui/sidebar.py:493-506` | Defaults are `Flange Width=6.0m`, `Web Length=8.0m` | Required default is `3.0m` and `3.0m` |
| UI defaults (tube) | `app.py:1421-1429`, `src/ui/sidebar.py:519-533` | Defaults are `Length X=6.0m`, `Length Y=6.0m` | Required default is `3.0m` and `3.0m` |
| I-section semantics | `app.py:1411-1414`, `src/ui/sidebar.py:511-514`, `src/fem/core_wall_geometry.py:50-52` | `length_x=flange_width`, `length_y=web_length`, but UI wording remains ambiguous in plan-view workflows | User perceives flange/web behavior as swapped |
| Beam trimming | `src/fem/model_builder.py:525-639` | Both-ends-outside case keeps only first/last outside segments | Concave I-section 4-intersection paths lose valid middle outside segment |
| I-section coupling | `src/fem/coupling_beam.py:119-120` | `generate_coupling_beams()` returns `[]` for `I_SECTION` | Missing 2 coupling beams connecting flange ends |
| Tube outline placement | `src/fem/core_wall_geometry.py:477-488` | Opening uses centered coordinates only | `TOP`/`BOTTOM` placement not represented |
| Tube wall panels | `src/fem/builders/core_wall_builder.py:213-216` | Generates 4 full panels (`TW1-TW4`) | No split/gap at opening zones |
| Tube interior non-coupling beams | `src/fem/model_builder.py:1512-1591`, `src/fem/model_builder.py:546-549` | Trim logic can preserve segments through hole/outside-hole regions | Unwanted interior beam crossing opening can survive |
| Slab exclusion | `src/fem/model_builder.py:346-395` | Excludes tube interior void only, returns `None` for I-section | Slab remains on/inside core footprint |
| I-section orientation contract | `src/fem/core_wall_geometry.py:225-259`, `src/fem/builders/core_wall_builder.py:176-207` | Outline and shell-panel interpretations are not guaranteed to represent the same canonical orientation | Trim boundary and physical shell mesh can diverge |
| Coupling endpoint connectivity | `src/fem/builders/beam_builder.py:549-555`, `src/fem/builders/core_wall_builder.py:124-128` | Coupling endpoints are created via registry path; wall mesh nodes are created with independent tag path | Potential disconnected/floating connectivity and solver singularity |
| Tube BOTH outline loop contract | `src/fem/core_wall_geometry.py:461-488`, `src/fem/model_builder.py:478-523` | BOTH behavior requires multiple closed loops; current return shape is not explicitly contract-guarded in plan | Trim classification may break if loops are not emitted as closed subpaths |
| WindResult field inventory | `src/core/data_models.py:757-768` | Wind payload currently contains base shear, pressure, drift summary only | Missing explicit per-floor and method-trace fields required for read-only detail |
| Dead duplicate slab helper | `src/fem/core_wall_geometry.py:527-573` | Duplicate helper uses stale `SlabOpening(x=...)` signature | Dead code + constructor mismatch |
| FEM solver | User runtime logs | Repeated singular matrix error at first static step | Likely from disconnected/floating/zero-stiffness path caused by geometry/connectivity defects |

---

## 3. Phase Goals

1. Beam trimming handles arbitrary concave intersections for I-section without dropping valid middle segments.
2. I-section generates exactly 2 parallel coupling beams connecting the 4 flange-end points.
3. Tube opening placement behavior is consistent for `TOP`, `BOTTOM`, and `BOTH` in outline, wall panels, and coupling-beam placement.
4. No non-coupling beams remain inside tube core footprint or through opening voids.
5. Slab mesh excludes full core wall footprint for both I-section and tube.
6. Default dimensions are `3.0m x 3.0m` for I-section (`Flange/Web` or renamed X/Y) and tube (`Length X/Y`).
7. I-section input semantics are unambiguous and behavior matches labels.
8. Wind read-only display includes calculation trace and per-floor `Wx`, `Wy`, `Wtz` values.
9. FEM analysis with core wall enabled solves without singular matrix failures.
10. I-section canonical orientation is explicitly defined and used consistently by outline, wall panel builder, and coupling-beam geometry.
11. Coupling beam endpoints are topologically connected to wall mesh (shared nodes or explicit constraints).
12. Tube `BOTH` outline emits valid multi-loop geometry for trim-hole classification.

---

## 4. Scope

### In Scope

1. Beam trimming algorithm generalization + concave edge-case handling.
2. I-section coupling beam generation and orientation correction.
3. Tube opening placement propagation to outline, wall panels, and coupling beams.
4. Suppression of non-coupling interior beams in tube footprint/opening zones.
5. Slab footprint exclusion for I-section and tube.
6. Core-wall default dimension updates to `3m x 3m` in both runtime sidebar paths.
7. I-section input semantics/labels and mapping consistency.
8. Wind read-only detail expansion (including per-floor `Wx/Wy/Wtz` and method trace).
9. Solver verification and singular-matrix closure checks.
10. Tests for all above.
11. Canonical I-section orientation prerequisite and geometry-consistency checks.
12. Coupling endpoint-to-wall connectivity contract and verification.
13. WindResult field inventory and extension plan before UI rendering changes.

### Out of Scope

1. New core wall configuration types beyond `I_SECTION` and `TUBE_WITH_OPENINGS`.
2. W1-W24 combination pipeline redesign.
3. Full report-system redesign beyond wind display fallout.
4. Pre-existing unrelated type/LSP issues outside touched files.

---

## 5. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Beam trim strategy | Parametric split by sorted intersections + midpoint classification | Handles 2, 4, N intersections for concave boundaries |
| I-section canonical orientation | Add Step 0 prerequisite: choose one canonical orientation and align outline + shell panels + coupling generation to that contract | Prevents mixed-interpretation geometry from causing trim/mesh/coupling divergence |
| Floor framing trim reference | Trim primary/secondary floor beams against **core outer footprint**, not opening holes | Prevents non-coupling beams from crossing tube interior/openings |
| I-section coupling topology | 2 beams, parallel to each other, connecting opposite flange-end pairs | Matches user-required "connect 4 flange ends with 2 parallel coupling beams" |
| Coupling endpoint connectivity | Coupling beam end nodes must coincide with wall mesh nodes or be explicitly tied with constraints | Eliminates floating connectivity and singular matrix risk |
| Tube opening placement | Placement-driven opening y-location (`TOP`, `BOTTOM`, `BOTH`) across all geometry layers | Eliminates "works only on BOTH" behavior |
| Tube BOTH outline format | Emit `outer_loop + opening_loop_1 + opening_loop_2`, each closed (`first == last`) | Satisfies `_split_outline_loops` / `_classify_loops` hole-loop contract |
| Tube wall panels | Opening-face panel split into two wall segments with gap | Removes wall shell elements through opening regions |
| Slab exclusion | Full core bounding-box opening for both configs | Guarantees zero slab mesh inside wall footprint |
| I-section slab exclusion granularity | Keep bounding-box exclusion in this phase (conservative) and document over-exclusion tradeoff | Avoids adding non-rectangular slab-opening model changes mid-fix |
| Defaults | Set I-section and tube key lengths to `3.0m` | User-requested startup behavior |
| I-section UI semantics | Use explicit directional naming (`Width (X)`, `Height (Y)`) and align mapping | Removes flange/web interpretation ambiguity in plan view |
| Wind traceability | Store/display method inputs + design pressure + per-floor `Wx/Wy/Wtz` table | Makes read-only section auditable and explainable |
| Solver closure | Add connectivity sanity checks before analysis and verify no singular error | Converts repeated runtime failure into measurable acceptance gate |

---

## 6. Implementation Plan

### Step 0: Canonical Geometry Contract (Prerequisite)

**Files:**
- `src/fem/core_wall_geometry.py`
- `src/fem/builders/core_wall_builder.py`
- `src/fem/coupling_beam.py`
- `src/fem/model_builder.py`

**Problems addressed:** #11 and #12 (enabler for #5/#6/#10)

**Fixes:**
1. Freeze one canonical I-section orientation contract and codify it explicitly.
2. Align outline generation, wall panel extraction, and coupling generation to the same contract.
3. Add explicit coupling endpoint connectivity rule: endpoints must share wall mesh nodes or be explicitly constrained to wall nodes.
4. Add geometry-consistency checks (outline vs panel footprint congruence) as acceptance prerequisites for downstream steps.

**Tests / Evidence:**
- Outline/panel congruence test for I-section orientation.
- Coupling endpoint connectivity evidence (no floating endpoints; endpoint nodes tied to wall mesh topology).

---

### Step 1: Beam Trimming Generalization + Interior Beam Suppression (Critical)

**File:** `src/fem/model_builder.py`

**Problems addressed:** #5 and #8

**Fixes:**
1. Replace current both-ends-outside branch in `trim_beam_segment_against_polygon` with general interval walk:
   - Split by sorted intersections.
   - Test each interval midpoint.
   - Keep intervals classified as outside core footprint.
2. Ensure floor framing (primary/secondary beams) trims against outer footprint policy so regular beams are not retained through tube interior/opening holes.
3. Keep coupling beams as separate explicit generation path (do not rely on generic floor-beam trimming).

**Tests:**
- I-section 4-intersection case keeps middle valid segment.
- I-section along-X and along-Y screenshot-equivalent scenarios trim to flange boundaries.
- Tube opening scenario keeps zero non-coupling beams inside footprint.
- Regression: simple 2-intersection trim still passes.

---

### Step 2: I-Section Coupling Beam Topology (Critical)

**Files:**
- `src/fem/coupling_beam.py`
- `src/fem/builders/beam_builder.py`

**Problems addressed:** #6

**Fixes:**
1. Add I-section coupling generation path (do not return empty list).
2. Generate 2 coupling beams connecting flange-end pairs (4 flange ends total), with parallel orientation.
3. Ensure beam-builder placement/orientation uses coupling geometry data, not fixed axis assumptions.
4. Ensure coupling-beam endpoints resolve to wall-connected topology (node sharing/snapping or explicit constraints).

**Tests:**
- `I_SECTION` generates exactly 2 coupling beams.
- Beam endpoints coincide with computed flange-end target points.
- Two beams are parallel and consistent across floors.
- Coupling endpoint node tags are connected to wall mesh graph (no floating coupling nodes).

---

### Step 3: Tube Opening Placement Propagation (Critical)

**Files:**
- `src/fem/core_wall_geometry.py`
- `src/fem/builders/core_wall_builder.py`
- `src/fem/coupling_beam.py`

**Problems addressed:** #7

**Fixes:**
1. Update `TubeWithOpeningsCoreWall.get_outline_coordinates()` to place opening(s) by placement mode:
   - `BOTTOM`: opening at bottom face.
   - `TOP`: opening at top face.
   - `BOTH`: two openings.
2. For `BOTH`, emit multi-loop outline as `outer + opening_1 + opening_2`, each loop explicitly closed (`first == last`) so `_split_outline_loops` and `_classify_loops` can classify holes deterministically.
3. Split affected tube wall panel(s) into segmented panels with opening gaps.
4. Align coupling-beam y-locations with opening placement outputs.

**Tests:**
- Outline coordinates differ correctly for `TOP`, `BOTTOM`, `BOTH`.
- Wall panel counts/lengths match split expectations.
- Coupling beam locations align with selected opening placement.
- Loop parsing test confirms `BOTH` produces one outer loop + two hole loops.

---

### Step 4: Slab Footprint Exclusion (Critical)

**Files:**
- `src/fem/model_builder.py`
- `src/fem/core_wall_geometry.py`

**Problems addressed:** #3 and #9

**Fixes:**
1. `_get_core_opening_for_slab` returns full core footprint opening (bounding box) for both I-section and tube.
2. Remove or deprecate dead duplicate slab-opening helper in `core_wall_geometry.py`.
3. Document that I-section bounding-box exclusion is intentionally conservative in this phase (over-excludes two side void strips) and defer polygonal slab openings to future refinement.

**Tests:**
- Zero slab elements inside I-section core footprint.
- Zero slab elements inside tube core footprint.
- Existing slab connectivity tests updated and passing.

---

### Step 5: UI Defaults + I-Section Input Semantics (Moderate)

**Files:**
- `app.py`
- `src/ui/sidebar.py`

**Problems addressed:** #2 and #4

**Fixes:**
1. Set defaults:
   - I-section dimensions: `3.0m`, `3.0m`.
   - Tube `Length X`, `Length Y`: `3.0m`, `3.0m`.
2. Replace ambiguous I-section labels/help text with directional semantics (`Width (X)`, `Height (Y)`) and ensure values map to geometry consistently.
3. Keep both UI paths (app + modular sidebar) identical.

**Tests:**
- UI default value tests for both paths.
- UI label/mapping tests to prevent semantic inversion regressions.

---

### Step 6: Wind Read-Only Detail Expansion (Moderate)

**Files:**
- `src/core/data_models.py`
- `src/fem/wind_calculator.py`
- `src/ui/views/fem_views.py`

**Problems addressed:** #1

**Fixes:**
1. Perform a `WindResult` field inventory (`current vs required`) before extending data contracts.
2. Extend wind result payload with trace fields required for read-only explanation:
   - input mode/method,
   - terrain and coefficient data,
   - design/factored pressure,
   - per-floor `Wx`, `Wy`, `Wtz` (and floor elevation).
3. Render an explanatory section in `Wind Loads (Read-only)` showing formulas/inputs and per-floor table.

**Tests:**
- UI tests confirm new fields are shown when data exists.
- Calculator/data-model tests confirm per-floor arrays are generated and consistent.

---

### Step 7: FEM Solvability Closure (Critical)

**Files:**
- `src/fem/model_builder.py`
- related tests/integration harness

**Problems addressed:** #10

**Fixes:**
1. Add explicit model sanity checks before solve (connectivity/orphan node/zero-length checks for affected geometry paths).
2. Run targeted I-section and tube scenarios from user-reported failure conditions.
3. Confirm analysis no longer fails at step 0 with singular matrix.

**Tests / Evidence:**
- Integration test(s) pass for both core configs.
- No `BandGenLinLapackSolver ... matrix singular` in solver logs for acceptance scenarios.

---

## 7. Dependency Order

```
Step 0 (canonical geometry contract) ───────┬── Step 1 (trim + interior beam suppression) ──┐
                                            ├── Step 2 (I-section coupling topology) ───────┼── Step 7 (solver closure)
                                            ├── Step 3 (tube placement propagation) ────────┤
                                            └── Step 4 (slab footprint exclusion) ──────────┘

Step 5 (defaults + semantics) ─ independent
Step 6 (wind detail) ─ independent
```

- Step 0 is mandatory before any geometry/coupling implementation.
- Steps 1-4 must converge before final solver verification.
- Re-run Step 1 trimming regressions after Step 3 changes (outline shape changes can affect trim behavior).
- Step 5 and Step 6 are independent and can run in parallel.

---

## 8. Acceptance Gates

Gate-letter note: this plan's acceptance gates are technical outcome gates. The execution log includes an additional operational Gate A (baseline/traceability), so letter mapping is shifted by one there. Also, this plan's Gate E (Interior Beam Suppression) is merged into execution-log Gate C.

| Gate | Criteria | Evidence |
|------|----------|----------|
| **A: Canonical Geometry Contract** | I-section outline, wall panels, and coupling geometry use one agreed orientation contract | Outline/panel congruence tests + geometry snapshots |
| **B: Beam Trimming** | I-section concave trim keeps all valid outside segments across X/Y scenarios | Unit tests including screenshot-equivalent geometry cases (re-run after Gate D) |
| **C: I-Section Coupling** | Exactly 2 parallel coupling beams connect 4 flange ends and endpoints are wall-connected | Unit tests + node-connectivity checks + plan-view verification |
| **D: Tube Placement** | `TOP/BOTTOM/BOTH` correctly reflected in outline + panels + coupling beams; BOTH emits valid multi-loop holes | Placement-specific tests + loop split/classification test |
| **E: Interior Beam Suppression** | No non-coupling floor beams remain inside tube footprint/opening | Targeted beam-generation assertions |
| **F: Slab Exclusion** | Zero slab elements inside core footprint for both configs (I-section bounding-box approach documented) | Slab mesh tests + integration check |
| **G: Defaults/Semantics** | I/tube default lengths are `3.0m`; I-section UI semantics are consistent | UI tests in both paths |
| **H: Wind Traceability** | `WindResult` inventory complete and read-only section shows method, pressure trace, per-floor `Wx/Wy/Wtz` | Data-model + calculator + UI tests |
| **I: FEM Solvable** | No singular matrix failure on representative I/tube models | Integration run + solver log proof |
| **J: Regression** | Full relevant test suite passes without new failures | `pytest` targeted + broader runs |

---

## 9. Risks and Controls

| Risk | Impact | Probability | Control |
|------|--------|-------------|---------|
| I-section orientation contract left ambiguous | Outline/mesh/coupling divergence persists | High | Gate A prerequisite with explicit canonical contract and congruence tests |
| Trim generalization breaks simple cases | Incorrect beam topology | Medium | Preserve and run 2-intersection regressions |
| Coupling endpoints not connected to wall mesh | Floating elements, singular stiffness | High | Enforce node-sharing/tie contract + connectivity diagnostics |
| Tube BOTH outline loops malformed | Hole classification fails in trimming | Medium | Add explicit loop-shape tests (`outer + hole1 + hole2`, each closed) |
| Coupling beam orientation wrong for I-section | Wrong load path | Medium | Endpoint-based assertions + visual checks |
| Tube panel split breaks wall meshing | Shell mesh errors | Medium | Add panel-level mesh validity tests |
| Footprint slab exclusion too aggressive | Missing slab strips near core edge | Low | Boundary-adjacent panel tests |
| Wind trace data absent in `WindResult` | UI cannot render required detail | Medium | Extend data model first; test serialization/usage |
| Solver still singular after geometry fixes | Phase objective not met | Medium | Add pre-solve sanity checks and isolate failing case logs |

---

## 10. Pre-existing Issues (Still Out of Scope Unless Directly Touched)

1. Archived test import errors in `tests/archived/`.
2. Legacy pre-existing type/LSP errors outside touched files.
3. Any unrelated report formatting issues.

---

## 11. Files Expected to Change

| File | Steps | Planned Changes |
|------|-------|-----------------|
| `src/fem/model_builder.py` | 0, 1, 4, 7 | Geometry contract checks, trim algorithm, interior beam suppression, slab exclusion, solver sanity hooks |
| `src/fem/coupling_beam.py` | 0, 2, 3 | Canonical orientation alignment, I-section coupling generation, placement alignment |
| `src/fem/builders/beam_builder.py` | 0, 2 | Coupling beam orientation from geometry data + endpoint connectivity enforcement |
| `src/fem/core_wall_geometry.py` | 0, 3, 4 | Canonical orientation alignment, tube opening multi-loop outline, dead slab helper cleanup |
| `src/fem/builders/core_wall_builder.py` | 0, 3 | Orientation-aligned panel extraction, tube wall-panel splitting for opening gaps |
| `src/ui/sidebar.py` | 5 | Defaults to 3m + directional I-section semantics |
| `app.py` | 5 | Defaults to 3m + directional I-section semantics |
| `src/core/data_models.py` | 6 | Wind result trace/per-floor fields |
| `src/fem/wind_calculator.py` | 6 | Populate wind detail payload |
| `src/ui/views/fem_views.py` | 6 | Read-only wind detail rendering |
| `tests/test_model_builder.py` | 0, 1, 4, 7 | Geometry contract, trim, exclusion, solver-path tests |
| `tests/test_coupling_beam.py` | 0, 2, 3 | I-section coupling topology, endpoint connectivity, tube placement tests |
| `tests/test_core_wall_geometry.py` | 0, 3 | I-section orientation contract + tube placement/outline loop tests |
| `tests/test_slab_wall_connectivity.py` | 4 | Slab footprint exclusion verification |
| `tests/test_model_builder_wall_integration.py` | 0, 2, 7 | Wall-coupling connectivity and full integration solvability checks |
| `tests/ui/test_sidebar_cleanup.py` or new UI tests | 5, 6 | Defaults/labels/wind read-only detail assertions |

---

## 12. Post-Completion Review — Residual Bugs (2026-02-12)

**Reviewer:** Claude Opus 4.6 (Independent Reviewer)

Phase 13 Gates A-J are all COMPLETE with 122 passed / 24 skipped in final regression. The core scope (I-section support, coupling beams, tube placement, slab exclusion, FEM solvability) is structurally sound. However, four residual bugs remain from manual application testing after gate closure.

### Bug 1 (P0): Floor Duplication in Plan View Dropdown

**Symptom:** Floor selector shows "1/F (+3.00)" three times, "2/F (+6.00)" three times, etc.

**Root cause:** `visualization.py:749-766` — `_get_floor_elevations()` extracts floor elevations from ALL shell elements by averaging their node z-coordinates:
```python
# Line 766 — averages z of ALL shell nodes, including wall shells
_add_level(sum(node_zs) / len(node_zs))
```
Wall shells span between floors (e.g., z=0→1.5, z=1.5→3.0 with `elements_per_story=2`), producing intermediate elevations (0.75, 2.25, 3.75, etc.). Slab shells sit exactly at floor levels (3.0, 6.0, 9.0). Combined, a 3-floor building gets ~9 "floor" entries instead of 3.

The `_format_floor_label` function (`fem_views.py:172-176`) rounds these to the nearest floor number via `int(round(z / story_height))`, causing triplication:
- z=2.25 → round(0.75)=1 → "1/F (+3.00)"
- z=3.0 → round(1.0)=1 → "1/F (+3.00)"
- z=3.75 → round(1.25)=1 → "1/F (+3.00)"

**Fix:** Filter `_get_floor_elevations` to only use slab-type shell elements, OR pass canonical `floor_elevations` from geometry directly.

**Files:** `src/fem/visualization.py:749-766`

### Bug 2 (P0): "Cannot synthesize W1-W24: unsuccessful component results Wx, Wy, Wtz"

**Symptom:** Error raised when running FEM analysis with wind loads enabled.

**Root cause:** `wind_case_synthesizer.py:93-102` raises `ValueError` when any Wx/Wy/Wtz result has `success=False`. Since ALL THREE wind cases fail, this points to a model-level issue (not wind-specific). The ValueError in `fem_views.py:441` masks the underlying solver failure message — the actual analysis error codes from OpenSeesPy are lost before reaching the user.

**Potential underlying causes (priority order):**
1. Model validation failure (`solver.py:349-356`) returns `success=False` for ALL cases including DL/SDL/LL, but W1-W24 synthesis error surfaces first
2. Empty wind patterns — if wind data is incomplete, no loads get added to patterns 4/6/8
3. Structural singularity introduced by I-section geometry

**Fix (two parts):**
- **Error handling:** Gracefully skip W1-W24 synthesis instead of raising ValueError; log which cases failed and their error messages
- **Root cause debug:** Add diagnostic logging to `_run_single_load_case` to surface the actual OpenSeesPy error code/message

**Files:** `src/fem/wind_case_synthesizer.py:85-102`, `src/ui/views/fem_views.py:439-441`, `src/fem/solver.py`

### Bug 3 (P1): Missing Beams/Slabs in Some Plan Views

**Symptom:** Some floor selections show no beams or slabs.

**Root cause:** Direct consequence of Bug 1. When user selects a "duplicate" floor entry at an intermediate wall-shell elevation (e.g., z=2.25 labeled "1/F (+3.00)"), the plan view renders elements at z≈2.25m where only wall shell sub-elements exist — no beams or slabs. Fixing Bug 1 eliminates this entirely.

**Fix:** N/A — auto-resolved by Bug 1 fix.

### Bug 4 (P1): Untrimmed Beam Through I-Section Core Wall

**Symptom:** One beam visible passing through the I-section core wall in plan view (see `audit_screenshots/isectionwall1.png`).

**Root cause:** The I-section outline (`core_wall_geometry.py:283-302`) is a single concave 12-vertex polygon. `_get_outer_trim_loop` (`model_builder.py:572-581`) correctly returns it as one loop. However, when a beam lies on or very near a polygon edge (gridline coincident with the I-section bottom boundary), `_line_segment_intersection` encounters a collinear/degenerate case — the beam either misses intersection detection or finds ambiguous results, passing through untrimmed.

**Fix:** Add collinear-edge handling to `trim_beam_segment_against_polygon`, or inflate the trim polygon by a small epsilon to avoid degenerate intersection geometry.

**Files:** `src/fem/model_builder.py:584-633`, `src/fem/core_wall_geometry.py:283-302`

---

### Recommended Phase 14 Scope

| Priority | Bug | Fix Scope | Files |
|----------|-----|-----------|-------|
| P0-A | Floor duplication | Filter wall shells from elevation extraction | `visualization.py:749-766` |
| P0-B | W1-W24 error masking | Graceful synthesis skip + diagnostic logging | `wind_case_synthesizer.py`, `fem_views.py` |
| P0-C | W1-W24 root cause | Debug actual solver failure for wind cases | `solver.py`, `model_builder.py` |
| P1-A | Untrimmed beam | Collinear edge handling in trim algorithm | `model_builder.py:584-633` |
| P1-B | Missing beams/slabs | N/A — auto-fixed by P0-A | — |

**Note:** Phase 13 scope explicitly listed "W1-W24 combination pipeline redesign" as OUT OF SCOPE (Section 4). The W1-W24 synthesis error is a pre-existing issue from Phases 10/11 that surfaced during Phase 13 testing but was never in-scope for this phase.

---

## 13. Bug Fix Review — Bugs 1 & 2 (2026-02-12)

**Reviewer:** Claude Opus 4.6 (Independent Reviewer)

### Bug 1 (Floor Duplication) — FULL PASS

**Fix at `visualization.py:768-770`:** Added z-spread filter to skip wall shells.

```python
z_spread = max(node_zs) - min(node_zs)
if z_spread > tolerance:
    continue  # vertical (wall) shell — skip
```

**Assessment:** Clean, minimal, correct. Wall shells have nodes at different z-levels (z_spread >> 0.01), slab shells have all nodes at the same z (z_spread ~ 0). The filter precisely targets the root cause without affecting any other code path. The comment is clear.

**Test gap (low risk):** No dedicated unit test for the wall-shell exclusion behavior. A test like "model with wall + slab shells returns only slab-level elevations" would harden it.

**Verdict: FULL PASS**

### Bug 2 (W1-W24 Error Masking) — FULL PASS

**Fix at `wind_case_synthesizer.py:79-103`:** `with_synthesized_w1_w24_cases` now catches `ValueError`, logs detailed diagnostics, and returns original results gracefully.

Key design decisions — all correct:
- `synthesize_w1_w24_cases` (strict) still raises `ValueError` for direct callers
- `with_synthesized_w1_w24_cases` (UI wrapper) catches and degrades gracefully
- Logged warning includes per-component status: missing vs failed + actual error message
- The `fem_views.py:451-474` failed-case reporting now naturally surfaces "Failed: Wx, Wy, Wtz" to the user instead of a cryptic exception

**Test gap (low risk):** No test for the graceful degradation path. A test like "with_synthesized returns originals without ValueError when component fails" would cover the new behavior. The existing `test_synthesize_fails_fast_*` tests only cover the strict path.

**Verdict: FULL PASS**

### Requested Test Additions

The agent should add the following tests to close the coverage gaps:

1. **`tests/test_wind_case_synthesizer.py`** — Add:
   ```python
   def test_with_synthesized_returns_originals_when_component_fails():
       """with_synthesized gracefully skips W1-W24 when a component is unsuccessful."""
       dl = _build_result(scale=1.0)
       wx = _build_result(scale=2.0)
       wy = _build_result(scale=3.0, success=False)  # failed
       wtz = _build_result(scale=4.0)
       merged = with_synthesized_w1_w24_cases({"DL": dl, "Wx": wx, "Wy": wy, "Wtz": wtz})
       assert merged["DL"] is dl  # original preserved
       assert "W1" not in merged  # no synthesis attempted
       assert "W24" not in merged
   ```

2. **`tests/test_model_builder.py`** (or new visualization test) — Add:
   ```python
   def test_get_floor_elevations_excludes_wall_shells():
       """Wall shells spanning between floors should not create intermediate floor entries."""
       # Build model with slab shells at z=3.0 and wall shells at z=0→3.0
       # Assert returned elevations contain only [3.0], not [1.5, 3.0] or similar
   ```

---

**Signed:** Claude Opus 4.6 (Independent Reviewer), 2026-02-12

---

## 14. Post-Fix Testing — Singular Matrix & Slab Gap Analysis (2026-02-12)

**Reviewer:** Claude Opus 4.6 (Independent Reviewer)

### Finding: P0 Singular Matrix — Disconnected I-Section Wall Panels

**Symptom:** ALL load cases (DL, SDL, LL, Wx, Wy, Wtz) fail with:
```
BandGenLinLapackSolver::solve() -factorization failed, matrix singular U(i,i) = 0, i= 30
```

**Root cause confirmed:** The three I-section wall panels (IW1, IW2, IW3) share physical intersection points at the flange-web junctions but have **separate, disconnected node tags** at those locations.

**Mechanism:**

`WallMeshGenerator` (`wall_element.py:117-119`) uses an auto-incrementing `_get_next_node_tag()` counter that NEVER checks for existing nodes at the same physical location. When `core_wall_builder.py:116-124` calls `generate_mesh` for each panel sequentially:

1. **IW1** (left flange, orientation=90°) creates nodes along Y at x=offset_x. With `elements_along_length=2`, the middle node is at **(offset_x, web_y, z)** → assigned tag e.g. `50002`
2. **IW3** (web, orientation=0°) creates nodes along X at y=web_y. The first node is at **(offset_x, web_y, z)** → assigned tag e.g. `50018`

Same physical coordinates `(offset_x, web_y, z)`, but different node tags `50002` vs `50018`. IW1 shell elements reference `50002`, IW3 shell elements reference `50018`. The two panels can displace independently at the junction → **zero stiffness coupling → singular matrix**.

This affects 4 junctions per z-level (IW1∩IW3 and IW2∩IW3, each with left/right endpoints), repeated across all `(elements_per_story × floors + 1)` z-levels.

**Evidence:**
- `wall_element.py:177`: `tag = self._get_next_node_tag()` — always creates new tag, never reuses
- `core_wall_builder.py:116-124`: Sequential `generate_mesh` calls with no node deduplication between panels
- Error code `-3` on ALL load cases confirms structural (not load-specific) defect
- `i=30` in singular matrix maps to approximately the 5th node's DOF — consistent with first junction node

**Recommended fix (3 options, any one sufficient):**

| Option | Approach | Complexity |
|--------|----------|------------|
| **A (Recommended)** | Use NodeRegistry in WallMeshGenerator: before creating each node, check if one already exists at that (x,y,z) and reuse its tag | Low — modify `generate_mesh` to accept registry |
| **B** | Post-process: after all panels are meshed, find coincident nodes and merge tags in shell element connectivity | Medium — requires element tag remapping |
| **C** | Pre-compute shared junction nodes and pass them as constraints to subsequent `generate_mesh` calls | Medium — requires panel intersection detection |

### Finding: Slab Gap at Coupling Beams — Expected Behavior (Not a New Bug)

The visible gap between slab edges and coupling beam endpoints in `audit_screenshots/isection-phase13.png` is the documented **conservative bounding-box slab exclusion** from Phase 13 Gate F.

Per Section 5 Design Decisions: *"I-section bounding-box exclusion is intentionally conservative in this phase (over-excludes two side void strips) and defer polygonal slab openings to future refinement."*

The coupling beams sit AT the I-section bounding box boundary. The slab is excluded from the entire bounding box. This is per-design. Refining to polygonal exclusion (slab touching coupling beams) should be a Phase 14 item.

### Updated Phase 14 Scope

| Priority | Issue | Root Cause | Fix Scope |
|----------|-------|------------|-----------|
| **P0-BLOCKER** | Singular matrix (all load cases fail) | Wall panel nodes not merged at flange-web junctions | Node merging in `WallMeshGenerator` / `core_wall_builder.py` |
| P0-C | W1-W24 root cause debug | Masked by singular matrix — may self-resolve once wall panels are connected | Verify after P0-BLOCKER fix |
| P1-A | Bug 4: untrimmed beam | Collinear edge case in trim algorithm | `model_builder.py:584-633` |
| P1-B | Slab gap at coupling beams | Conservative bounding-box exclusion (by design) | Polygonal slab opening |

**Note:** The W1-W24 synthesis error (Bug 2/P0-B, now gracefully handled) is likely a downstream consequence of the singular matrix. Once the wall panel connectivity is fixed and DL/SDL/LL succeed, the wind load cases should also succeed (assuming wind data is valid). This should be verified after the P0-BLOCKER fix.

---

**Signed:** Claude Opus 4.6 (Independent Reviewer), 2026-02-12
