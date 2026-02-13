# Phase 14: Wall Node Merging, Collinear Beam Trim, and Polygonal Slab Exclusion

## Status: COMPLETE (Gates A-F PASS)

## Origin

Residual bugs identified during Phase 13 post-completion review (Sections 12 & 14 of `phase-13-core-wall-geometry-connectivity.md`). Phase 13 Gates A-J are COMPLETE with 122 passed / 24 skipped. Four residual issues remain from manual application testing after gate closure.

---

## 1. Problem Statement

Phase 13 resolved 12 structural issues (I-section support, coupling beams, tube placement, slab exclusion, wind traceability, FEM solvability). However, post-completion testing revealed 4 residual bugs — one of which (P0-BLOCKER singular matrix) blocks ALL load case analysis.

### P0-BLOCKER: Singular Matrix — Disconnected I-Section Wall Panels

**Symptom:** ALL load cases (DL, SDL, LL, Wx, Wy, Wtz) fail with `BandGenLinLapackSolver::solve() -factorization failed, matrix singular U(i,i) = 0, i= 30`.

**Root cause:** `WallMeshGenerator` (`wall_element.py:117`) uses `_get_next_node_tag()` counter that NEVER checks for existing nodes at the same physical location. When `core_wall_builder.py:116-124` calls `generate_mesh` for IW1, IW2, IW3 sequentially, each panel gets SEPARATE node tags at shared flange-web junction coordinates. This creates disconnected shell topology → zero stiffness coupling → singular matrix.

**Affected junctions:** 4 per z-level (IW1∩IW3 and IW2∩IW3, each with 2 endpoints), repeated across all `(elements_per_story × floors + 1)` z-levels.

### P0-C: W1-W24 Synthesis Failure (Downstream of P0-BLOCKER)

**Symptom:** `Cannot synthesize W1-W24: unsuccessful component results Wx, Wy, Wtz`.

**Root cause:** ALL load cases fail due to singular matrix → wind cases also fail → W1-W24 synthesis cannot proceed. Phase 13 already added graceful degradation (`wind_case_synthesizer.py:79-103`). Once P0-BLOCKER is fixed, this self-resolves. Verification-only task.

### P1-A (Bug 4): Untrimmed Beam on Collinear Edge

**Symptom:** One beam visible passing through I-section core wall in plan view.

**Root cause:** `_line_segment_intersection()` at `model_builder.py:462-490` returns `None` when `abs(det) < 1e-9` (collinear/parallel case). A beam at y=400mm (I-section bottom flange edge) is exactly collinear with the polygon edge → no intersection detected → beam passes through untrimmed.

### P1-B: Slab Gap at Coupling Beams (Conservative Bounding-Box Exclusion)

**Symptom:** Visible gap between slab edges and coupling beam endpoints — slab excluded from entire I-section bounding box, including the two side void strips where slab SHOULD exist.

**Root cause:** `SlabOpening` (`slab_element.py:67-94`) is rectangular-only. Phase 13 Design Decision explicitly deferred polygonal slab openings: *"I-section bounding-box exclusion is intentionally conservative in this phase (over-excludes two side void strips) and defer polygonal slab openings to future refinement."* Phase 14 implements this deferred refinement.

---

## 2. Baseline State (Pre-Execution Snapshot)

| Area | File(s) | Current Behavior | Issue |
|------|---------|------------------|-------|
| Wall node creation | `wall_element.py:177` | `_get_next_node_tag()` always creates new tag, never reuses | Coincident nodes at panel junctions are disconnected |
| Panel mesh sequencing | `core_wall_builder.py:116-124` | Sequential `generate_mesh` calls with no cross-panel node dedup | IW1/IW2/IW3 junction nodes have different tags at same (x,y,z) |
| Node registry usage | `core_wall_builder.py:140-148` | `registry.register_existing()` called AFTER mesh generation | Registry receives already-duplicated nodes — too late to deduplicate |
| Line intersection | `model_builder.py:462-490` | `abs(det) < 1e-9` → returns `None` | Collinear beam-on-edge case misses intersection entirely |
| Tolerance mismatch | `model_builder.py:466,587,254` | Intersection: `1e-9`, trim: `1e-6`, registry: `1e-6` | 3 orders of magnitude gap between intersection and trim tolerances |
| Slab opening model | `slab_element.py:67-94` | Rectangular only (`width_x`, `width_y`) | Cannot represent I-section polygon footprint |
| Slab exclusion | `model_builder.py:371-395` | Returns bounding-box `SlabOpening` for I-section | Over-excludes two side void strips |
| W1-W24 synthesis | `wind_case_synthesizer.py:79-103` | Graceful degradation already in place | Downstream of P0-BLOCKER — verification only |

---

## 3. Phase Goals

1. I-section wall panels (IW1, IW2, IW3) share node tags at flange-web junction points — zero duplicate nodes at coincident coordinates.
2. ALL 6 load cases (DL, SDL, LL, Wx, Wy, Wtz) solve successfully without singular matrix.
3. W1-W24 wind case synthesis succeeds when component cases succeed.
4. Beams collinear with polygon edges are correctly detected and trimmed (no untrimmed beams passing through core wall).
5. Slab exclusion uses I-section polygon footprint (not bounding box) — slab exists in side void strips, excluded only from actual wall footprint.
6. Tube wall behavior is unchanged (no regression).

---

## 4. Scope

### In Scope

1. Wall mesh node deduplication via NodeRegistry integration in `WallMeshGenerator.generate_mesh()`.
2. Solver verification for all 6 load cases + W1-W24 synthesis after node merge fix.
3. Collinear edge detection in `_line_segment_intersection()` for beam trimming.
4. Tolerance unification: align intersection detection to `1e-6` (matching trim and registry).
5. Polygonal `SlabOpening` support (optional `polygon_vertices` field).
6. `_get_core_opening_for_slab()` returns polygonal opening for I-section.
7. Tests for all above, following TDD pattern from Phase 13.

### Out of Scope

1. W1-W24 combination pipeline redesign (carried from Phase 13 exclusion).
2. New core wall configuration types beyond `I_SECTION` and `TUBE_WITH_OPENINGS`.
3. Full computational geometry library replacement for trim system.
4. Global conformal meshing architecture rewrite.
5. UI/report changes beyond what bug fixes require.
6. Tube wall polygonal slab exclusion (tube already uses correct rectangular exclusion).

---

## 5. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Node dedup strategy | Option A: Pass `NodeRegistry` into `WallMeshGenerator.generate_mesh()` and use `registry.get_or_create()` | Lowest complexity, reuses existing registry infrastructure, no post-processing needed |
| Node dedup scope | Wall-panel coincident nodes ONLY (not frame nodes) | Minimizes blast radius; frame nodes already use registry correctly |
| Path parity | Apply fix to BOTH `build_fem_model` and director path | Metis identified path divergence risk; both paths must produce identical results |
| Collinear boundary policy | Collinear beam-on-edge = INSIDE core → fully trimmed | Beam on wall boundary is structurally part of the wall, should not remain as separate element |
| Tolerance unification | Align `_line_segment_intersection` tolerance from `1e-9` to `1e-6` | Match trim function and NodeRegistry tolerance; eliminates 3-order-of-magnitude mismatch |
| Slab exclusion model | Add optional `polygon_vertices: List[Tuple[float, float]]` to `SlabOpening` | Backward-compatible; rectangular path unchanged when `polygon_vertices is None` |
| Slab element filtering | Center-point containment check against polygon | Consistent with existing center-point vs rectangle check; adequate for engineering accuracy |
| Tube behavior | Frozen as-is for this phase | Tube rectangular exclusion is already correct; no polygonization needed |
| W1-W24 synthesis | Verification only — do NOT modify `wind_case_synthesizer.py` | Graceful degradation already in place from Phase 13 Bug 2 fix |

---

## 6. Implementation Plan

### Step 0: Wall Panel Node Deduplication (P0-BLOCKER)

**Files:**
- `src/fem/wall_element.py` — `WallMeshGenerator.generate_mesh()`
- `src/fem/builders/core_wall_builder.py` — `CoreWallBuilder.create_core_walls()`
- `src/fem/model_builder.py` — `build_fem_model()` (if wall mesh is generated there)

**Problem addressed:** P0-BLOCKER (singular matrix from disconnected I-section wall panels)

**Fixes:**
1. Add optional `registry: NodeRegistry = None` parameter to `WallMeshGenerator.generate_mesh()`.
2. When `registry` is provided, replace `tag = self._get_next_node_tag()` at line 177 with:
   ```python
   if registry is not None:
       tag = registry.get_or_create(x, y, z, floor_level=floor_idx)
   else:
       tag = self._get_next_node_tag()
   ```
3. **CRITICAL — Double-add prevention:** `registry.get_or_create()` calls `ops.node(tag, x, y, z)` internally to add nodes to the OpenSeesPy model. The caller (`core_wall_builder.py:140-148`) currently also calls `registry.register_existing()` which attempts to add the same nodes again → `ValueError` crash. **Resolution:** When `registry` is passed to `generate_mesh()`, the subsequent `register_existing()` call in `core_wall_builder.py` MUST be removed or guarded with an `if not already_registered` check. The registry flow becomes: `generate_mesh(registry=reg)` creates/reuses nodes via registry → caller skips `register_existing()` since nodes are already in both registry and OpenSeesPy model.
4. In `core_wall_builder.py:116-124`, pass the shared `NodeRegistry` instance to each `generate_mesh()` call so IW1, IW2, IW3 share junction nodes.
5. Verify BOTH build paths (direct `build_fem_model` and director/builder path) pass registry consistently.
6. Ensure tube walls (`TW1-TW4`) are unaffected — tube panels share full edges, not junction points, so dedupe should be safe but must be regression-tested.

**Node tag numbering change:** With registry integration, wall node tags will shift from the `50000+` range (from `_get_next_node_tag()` auto-increment) to floor-based numbering (from registry's `get_or_create` scheme). Verify no downstream code depends on wall node tag ranges (grep for `50000` or tag-range assumptions in solver, visualization, or result extraction).

**Critical edge cases (from Metis):**
- Triple-junction: 3+ panels meeting at same (x,y,z) — `get_or_create` handles this naturally (returns existing tag).
- Multi-floor consistency: dedupe must work identically at every z-level.
- Tube regression: tube wall panels must not gain/lose nodes from registry integration.
- Double-add: `register_existing()` after `generate_mesh(registry=...)` must be removed/guarded to prevent ValueError.

**Expected node count delta:** For a 3-floor I-section model with `elements_per_story=2` and `elements_along_length=1`: 4 junction points × (2×3 + 1) = 4 × 7 = **28 duplicate nodes eliminated**. The exact formula is: `num_junctions × (elements_per_story × num_floors + 1)` where `num_junctions = 4` for I-section (IW1∩IW3 left, IW1∩IW3 right, IW2∩IW3 left, IW2∩IW3 right).

**Tests:**
- Unit: `WallMeshGenerator` with registry produces fewer total nodes than without registry for I-section (junction nodes merged). Expected delta: 28 fewer nodes for 3-floor/2-elem model.
- Unit: Same (x,y,z) across two panels → same node tag.
- Unit: Tube panels with registry → identical node count as without registry (no regression).
- Unit: No `ValueError` from double-add — `generate_mesh(registry=...)` followed by build path completes without crash.
- Integration: I-section model `ops.getNodeTags()` count matches expected (no duplicates).

---

### Step 1: Solver Verification (P0-C)

**Files:**
- `tests/test_gate_i_fem_solvability.py` — existing solvability gate test
- `src/fem/solver.py` — verify no code changes needed

**Problem addressed:** P0-C (W1-W24 downstream of singular matrix)

**Fixes:**
1. NO code changes. This is a verification-only step.
2. After Step 0, run full solver pipeline for I-section model with all 6 load cases.
3. Verify ALL cases return `success=True` and no `matrix singular` in logs.
4. Verify W1-W24 synthesis succeeds (all 24 combined cases generated).
5. If any case still fails, diagnose and fix before proceeding (indicates additional connectivity issue beyond panel junctions).

**Tests:**
- Integration: `test_core_models_analyze_without_singular_matrix` passes for I-section.
- Integration: W1-W24 synthesis produces exactly 24 combined cases.
- Integration: Tube model still solves (regression).

---

### Step 2: Collinear Edge Handling in Beam Trim (P1-A / Bug 4)

**Files:**
- `src/fem/model_builder.py` — `_line_segment_intersection()` at line 462

**Problem addressed:** P1-A (untrimmed beam on collinear polygon edge)

**Fixes:**
1. In `_line_segment_intersection()`, when `abs(det) < tolerance` (collinear case), add overlap detection branch:
   ```python
   if abs(det) < tolerance:
       # Collinear — check for 1D overlap on the shared line
       # Project both segments onto the dominant axis
       # Return overlap midpoint or endpoint if segments overlap
       # Return None only if segments are parallel but disjoint
   ```
2. Unify tolerance from `1e-9` to `1e-6` to match trim function and NodeRegistry (addresses Metis tolerance drift risk).
3. When overlap is detected, return an intersection point (midpoint of overlap region) so trim logic can classify the beam as crossing the polygon edge.
4. Handle sub-cases:
   - Full overlap: beam entirely on edge → return midpoint.
   - Partial overlap: beam extends beyond edge → return overlap boundary point.
   - Disjoint collinear: parallel but no overlap → return `None` (correct existing behavior).

**Critical edge cases (from Metis):**
- Near-collinear numeric noise (`det ~ epsilon`) — tolerance unification addresses this.
- Beam segment exactly on polygon vertex/endpoint — must not create NaN or division by zero.
- I-section critical collinear edges: y=0, y=400, y=2600, y=3000, x=0, x=1300, x=1700, x=3000.

**Tests:**
- Unit: Fully collinear overlapping segments → returns intersection point.
- Unit: Partially overlapping collinear segments → returns overlap boundary.
- Unit: Disjoint collinear (parallel, no overlap) → returns `None`.
- Unit: Near-collinear (`det` just above/below tolerance) → stable result.
- Integration: Beam at y=400mm on I-section polygon → correctly trimmed.
- Regression: All existing 8 trim tests still pass (non-collinear cases unchanged).

---

### Step 3: Polygonal Slab Exclusion (P1-B)

**Files:**
- `src/fem/slab_element.py` — `SlabOpening` dataclass
- `src/fem/model_builder.py` — `_get_core_opening_for_slab()`, slab mesh element filtering
- `src/fem/core_wall_geometry.py` — I-section polygon outline (read-only reference)

**Problem addressed:** P1-B (slab gap at coupling beams from over-aggressive bounding-box exclusion)

**Fixes:**
1. Add optional field to `SlabOpening`:
   ```python
   @dataclass
   class SlabOpening:
       opening_id: str
       origin: Tuple[float, float]
       width_x: float
       width_y: float
       polygon_vertices: Optional[List[Tuple[float, float]]] = None
   ```
2. In slab mesh element filtering (`slab_element.py:294`), when `polygon_vertices` is not None, use `point_in_polygon()` check on element center instead of rectangular bounds check.
3. Update `_get_core_opening_for_slab()` in `model_builder.py`:
   - For `I_SECTION`: return `SlabOpening` with `polygon_vertices` set to the 13-vertex I-section polygon (from `core_wall_geometry.py:270-304`), translated to global coordinates.
   - For `TUBE_WITH_OPENINGS`: keep existing rectangular `SlabOpening` unchanged.
4. Reuse existing `_point_in_polygon()` at `model_builder.py:493` or move to shared utility.
5. Update `tests/test_gate_f_slab_footprint.py` to expect polygonal exclusion for I-section (no longer bounding-box).

**Critical edge cases (from Metis):**
- Polygon orientation/closure: I-section polygon must be closed (first == last vertex) and consistently wound (CW or CCW).
- Slab elements whose center is outside polygon but corners cross into polygon — center-point check is acceptable per Design Decision.
- Global coordinate translation: polygon from geometry is local; must offset by core wall position.

**Tests:**
- Unit: `SlabOpening` with `polygon_vertices` excludes elements inside polygon, keeps elements outside.
- Unit: `SlabOpening` without `polygon_vertices` (None) uses rectangular check (backward compat).
- Unit: Elements in I-section side void strips (between flanges, outside web) → NOT excluded (restored slab).
- Integration: I-section model has slab elements in side void strips and no slab elements inside wall footprint.
- Integration: Tube model slab exclusion unchanged (regression).

---

### Step 4: Regression and Signoff

**Files:**
- All test files

**Fixes:**
1. Run full targeted regression: `pytest tests/ -q` for all gate-related tests.
2. Verify no new test failures introduced.
3. Run broader test suite for touched files.
4. Capture evidence screenshots if applicable.

**Tests:**
- `pytest tests/test_gate_i_fem_solvability.py -q` → PASS
- `pytest tests/test_gate_f_slab_footprint.py -q` → PASS
- `pytest tests/test_model_builder.py -q` → PASS
- `pytest tests/test_wall_element.py -q` → PASS
- `pytest tests/test_slab_wall_connectivity.py -q` → PASS
- `pytest tests/test_wind_case_synthesizer.py -q` → PASS
- `pytest tests/test_model_builder_wall_integration.py -q` → PASS

---

## 7. Dependency Order

```
Step 0 (wall node dedup — P0-BLOCKER) ──┬── Step 1 (solver verification — P0-C)
                                        │
                                        ├── Step 2 (collinear trim — P1-A) ─── independent of Step 0
                                        │
                                        ├── Step 3 (polygonal slab — P1-B) ─── independent of Step 0
                                        │
                                        └── Step 4 (regression) ──────────── after ALL steps complete
```

- **Step 0 MUST complete before Step 1** (solver verification requires node merge fix).
- **Step 2 is independent** of Step 0 (different code path, different bug).
- **Step 3 is independent** of Step 0 (slab exclusion, not wall nodes).
- **Steps 2 and 3 can run in parallel** with each other and with Steps 0-1.
- **Step 4 is final gate** — runs after all other steps.

### Parallel Execution Waves

```
Wave 1 (Start Immediately — Parallel):
├── Step 0: Wall node deduplication (P0-BLOCKER)
├── Step 2: Collinear edge handling (P1-A)
└── Step 3: Polygonal slab exclusion (P1-B)

Wave 2 (After Step 0):
└── Step 1: Solver verification (P0-C)

Wave 3 (After ALL):
└── Step 4: Regression + signoff
```

---

## 8. Acceptance Gates

| Gate | Step | Criteria | Evidence |
|------|------|----------|----------|
| **A: Baseline Freeze** | Pre | Branch snapshot, issue-to-code anchors, baseline tests pass | Git commit hash + `pytest` output |
| **B: Wall Node Dedup** | 0 | I-section panels share node tags at flange-web junctions; zero duplicate nodes at coincident (x,y,z); tube node count unchanged | Unit tests: junction node tag equality + total node count assertions |
| **C: Solver Pass** | 1 | ALL 6 load cases (DL, SDL, LL, Wx, Wy, Wtz) return `success=True`; W1-W24 synthesis produces 24 cases; no `matrix singular` in logs | Integration test: `test_core_models_analyze_without_singular_matrix` + W1-W24 count assertion |
| **D: Collinear Trim** | 2 | Collinear beam-on-edge correctly detected and trimmed; all 3 sub-cases (full overlap, partial overlap, disjoint) handled; existing 8 trim tests still pass | Unit tests: collinear overlap/disjoint + regression suite |
| **E: Polygonal Slab** | 3 | I-section slab uses polygon footprint (not bounding box); slab exists in side void strips; tube slab exclusion unchanged | Unit tests: polygon vs rectangular containment + integration slab element count |
| **F: Regression + Signoff** | 4 | All gate-related test files pass; no new failures in broader suite | `pytest` targeted + broader output |

---

## 9. Risks and Controls

| Risk | Impact | Probability | Control |
|------|--------|-------------|---------|
| Registry integration changes `generate_mesh` return contract | Shell element connectivity broken | Medium | Backward-compatible: `registry=None` default preserves existing behavior |
| Path divergence: fixing only one build path | Latent failures in untested path | High (from Metis) | Guardrail: apply fix to BOTH `build_fem_model` and director path; test both |
| Node dedupe affects tube walls unexpectedly | Tube regression | Low | Explicit tube node-count regression test before/after registry |
| Collinear tolerance change causes false positives | Near-parallel beams incorrectly classified as collinear | Low | Use unified `1e-6` tolerance (matches existing trim/registry); add near-collinear test case |
| Polygon slab exclusion invalidates Gate F tests | Test failures on unchanged functionality | High (from Metis) | Update `test_gate_f_slab_footprint.py` in same gate as fix |
| Center-point polygon check misses corner-overlapping elements | Slab element partially inside wall footprint | Low | Acceptable per Design Decision; engineering tolerance met |
| W1-W24 still fails after P0-BLOCKER fix | Additional connectivity issues beyond panel junctions | Medium | Step 1 is explicit verification gate; diagnose if fails |
| Polygon coordinate translation error | Wrong slab exclusion boundary | Medium | Use known 13-vertex polygon coordinates; assert polygon matches geometry |

---

## 10. Pre-existing Issues (Still Out of Scope)

1. Archived test import errors in `tests/archived/`.
2. Legacy pre-existing type/LSP errors outside touched files (e.g., openseespy type stubs).
3. Any unrelated report formatting issues.
4. W1-W24 combination pipeline redesign.

---

## 11. Files Expected to Change

| File | Steps | Planned Changes |
|------|-------|-----------------|
| `src/fem/wall_element.py` | 0 | Add `registry` parameter to `generate_mesh()`; use `registry.get_or_create()` when provided |
| `src/fem/builders/core_wall_builder.py` | 0 | Pass shared `NodeRegistry` to each `generate_mesh()` call |
| `src/fem/model_builder.py` | 0, 2, 3 | Pass registry in `build_fem_model()` wall path; fix `_line_segment_intersection()` collinear branch + tolerance; update `_get_core_opening_for_slab()` for I-section polygon |
| `src/fem/slab_element.py` | 3 | Add `polygon_vertices` field to `SlabOpening`; polygon containment check in mesh filtering |
| `tests/test_wall_element.py` | 0 | Node dedup unit tests: junction merging, tube regression |
| `tests/test_model_builder.py` | 2 | Collinear intersection tests: overlap, partial, disjoint, near-collinear |
| `tests/test_gate_i_fem_solvability.py` | 1 | Verify solver passes for all 6 load cases + W1-W24 synthesis |
| `tests/test_gate_f_slab_footprint.py` | 3 | Update I-section expectations from bounding-box to polygon |
| `tests/test_slab_wall_connectivity.py` | 3 | Verify slab exists in side void strips |
| `tests/test_model_builder_wall_integration.py` | 0, 1 | Wall-coupling connectivity after node dedupe |
| `tests/test_wind_case_synthesizer.py` | 1 | Verify graceful degradation unchanged (regression) |

---

## 12. Success Criteria

### Verification Commands
```bash
# Gate B: Wall node dedup
pytest tests/test_wall_element.py -q -k "registry or dedup or junction"
# Expected: all new tests pass; no duplicate nodes at junction coordinates

# Gate C: Solver verification
pytest tests/test_gate_i_fem_solvability.py -q
# Expected: 2+ passed; no "matrix singular" in output

# Gate D: Collinear trim
pytest tests/test_model_builder.py -q -k "collinear"
# Expected: all new collinear tests pass

# Gate E: Polygonal slab
pytest tests/test_gate_f_slab_footprint.py -q
# Expected: I-section polygon expectations pass; tube unchanged

# Gate F: Full regression
pytest tests/test_wall_element.py tests/test_model_builder.py tests/test_gate_i_fem_solvability.py tests/test_gate_f_slab_footprint.py tests/test_slab_wall_connectivity.py tests/test_wind_case_synthesizer.py tests/test_model_builder_wall_integration.py -q
# Expected: all pass, zero failures
```

### Final Checklist
- [ ] Zero duplicate node tags at I-section flange-web junctions (all z-levels)
- [ ] ALL 6 load cases solve without singular matrix
- [ ] W1-W24 synthesis produces 24 combined cases
- [ ] Zero untrimmed beams on collinear polygon edges
- [ ] Slab exists in I-section side void strips (not over-excluded)
- [ ] Zero slab elements inside I-section wall polygon footprint
- [ ] Tube wall behavior completely unchanged (node count, slab exclusion, solver)
- [ ] All Phase 13 regression tests still pass

---

## 13. Post-Phase Validation + UI Follow-Up (2026-02-14)

User confirmed runtime behavior is acceptable after Phase 14 fixes (manual validation: "looks good").

After this acceptance, a focused UI follow-up was requested and executed for FEM Display Options:

1. Removed "Show" prefix from option labels.
2. Renamed ghost-column toggle to "Omitted Column".
3. Added explicit toggles for Beam, Wall, and Diaphragm Master.
4. Reorganized toggles into the requested three-column layout.
5. Fixed Reaction (Base) behavior by wiring reaction rendering to `show_reactions` and propagating plan-view reactions.
6. Added deformed-shape scale annotation using the same scale-control family as section-force diagrams.

Files touched in this follow-up:

- `src/ui/views/fem_views.py`
- `src/fem/visualization.py`
- `tests/test_visualization_plan_view.py`
- `tests/test_visualization_elevation_view.py`
- `tests/test_visualization_3d_view.py`

This follow-up is UI/visualization ergonomics only and does not alter the completed structural-solver scope of Gates A-F.

---
