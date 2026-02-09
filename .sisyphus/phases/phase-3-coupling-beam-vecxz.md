# Phase 3: Coupling Beam vecxz Fix

## Prerequisite
Phase 0 (rename), Phase 1 (beam fix), and Phase 2 (column verify) must be complete.

## Objective
Fix the vecxz vector for coupling beam elements so they follow the same ETABS convention as regular beams:
- `local_y = vertical (0,0,1)`
- `Mz = gravity/major-axis bending`

## Current State

### beam_builder.py — line 585

**File: `src/fem/builders/beam_builder.py`, line 585:**
```python
geometry_override={"vecxz": (0.0, 0.0, 1.0), "coupling_beam": True},
```

This hardcodes `vecxz = (0,0,1)` for ALL coupling beams regardless of spanning direction. This is the same bug as regular beams — Mz ends up as the lateral/minor-axis bending instead of gravity/major.

The call to `self._create_beam_element()` at line 579 passes `geometry_override`, which bypasses Phase 1's computed vecxz logic at line 166-176.

### model_builder.py — line 1870

**File: `src/fem/model_builder.py`, line 1870:**
```python
"vecxz": (0.0, 0.0, 1.0),
```

Inside the coupling beam subdivision loop (lines 1859-1874), each sub-element gets a hardcoded vecxz. The loop creates 6 sub-elements (`NUM_SUBDIVISIONS = 6`) connecting 7 nodes.

## Coupling Beam Orientations

Coupling beams span in two directions depending on `CoreWallConfig`:

### In beam_builder.py (lines 544-564)

**X-spanning** (lines 544-552):
- `CoreWallConfig.TWO_C_FACING`
- `CoreWallConfig.TUBE_CENTER_OPENING`
- Default fallback (lines 559-564)
- Direction: `(end_x - start_x, 0, 0)` → beam along X

**Y-spanning** (lines 553-558):
- `CoreWallConfig.TUBE_SIDE_OPENING`
- Direction: `(0, end_y - start_y, 0)` → beam along Y

The start/end coordinates are already computed at lines 549-564.

### In model_builder.py (lines 1805-1832)

**X-spanning** (lines 1805-1813):
- `CoreWallConfig.TWO_C_FACING`
- `CoreWallConfig.TUBE_CENTER_OPENING`

**Y-spanning** (lines 1814-1819):
- `CoreWallConfig.TUBE_SIDE_OPENING`

**X-spanning** (lines 1820-1826):
- `CoreWallConfig.TWO_C_BACK_TO_BACK` — **NOTE: This config only exists in model_builder.py, not in beam_builder.py**

**Default X-spanning** (lines 1828-1832):
- Fallback for any unhandled config

The start/end coordinates (`start_x, start_y, end_x, end_y`) are available in scope at lines 1810-1832.

## The Fix

### File 1: `src/fem/builders/beam_builder.py`

**Modify lines 579-586** — compute vecxz before passing the geometry_override:

```python
# BEFORE (lines 579-586):
parent_beam_id = self._create_beam_element(
    start_node=start_node,
    end_node=end_node,
    section_tag=self.coupling_section_tag,
    load_pattern=self.options.dl_load_pattern,
    section_dims=(coupling_beam_template.width, coupling_beam_template.depth),
    geometry_override={"vecxz": (0.0, 0.0, 1.0), "coupling_beam": True},
)

# AFTER:
# Compute vecxz for coupling beam (same formula as regular beams)
cb_dx = end_x - start_x
cb_dy = end_y - start_y
cb_length_xy = math.hypot(cb_dx, cb_dy)
if cb_length_xy > 1e-10:
    cb_vecxz = (cb_dy / cb_length_xy, -cb_dx / cb_length_xy, 0.0)
else:
    cb_vecxz = (0.0, 0.0, 1.0)  # Fallback

parent_beam_id = self._create_beam_element(
    start_node=start_node,
    end_node=end_node,
    section_tag=self.coupling_section_tag,
    load_pattern=self.options.dl_load_pattern,
    section_dims=(coupling_beam_template.width, coupling_beam_template.depth),
    geometry_override={"vecxz": cb_vecxz, "coupling_beam": True},
)
```

Note: `start_x, start_y, end_x, end_y` are already in scope from lines 549-564. `math` is already imported (used by Phase 1's regular beam vecxz at line 171).

### File 2: `src/fem/model_builder.py`

**Insert vecxz computation ONCE before the subdivision loop at line 1859, then use it inside:**

```python
# BEFORE (lines 1858-1874):
# Create 6 sub-elements connecting the 7 nodes
for i in range(NUM_SUBDIVISIONS):
    model.add_element(
        Element(
            tag=coupling_element_tag,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[node_tags[i], node_tags[i + 1]],
            material_tag=beam_material_tag,
            section_tag=coupling_section_tag,
            geometry={
                "parent_coupling_beam_id": parent_coupling_beam_id,
                "sub_element_index": i,
                "vecxz": (0.0, 0.0, 1.0),
            },
        )
    )
    coupling_element_tag += 1

# AFTER:
# Compute vecxz ONCE for this coupling beam (same formula as regular beams)
cb_dx = end_x - start_x
cb_dy = end_y - start_y
cb_length_xy = math.hypot(cb_dx, cb_dy)
if cb_length_xy > 1e-10:
    cb_vecxz = (cb_dy / cb_length_xy, -cb_dx / cb_length_xy, 0.0)
else:
    cb_vecxz = (0.0, 0.0, 1.0)  # Fallback

# Create 6 sub-elements connecting the 7 nodes
for i in range(NUM_SUBDIVISIONS):
    model.add_element(
        Element(
            tag=coupling_element_tag,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[node_tags[i], node_tags[i + 1]],
            material_tag=beam_material_tag,
            section_tag=coupling_section_tag,
            geometry={
                "parent_coupling_beam_id": parent_coupling_beam_id,
                "sub_element_index": i,
                "vecxz": cb_vecxz,
            },
        )
    )
    coupling_element_tag += 1
```

Note: `start_x, start_y, end_x, end_y` are already in scope from lines 1810-1832. `math` is already imported at the top of model_builder.py (used by Phase 1's regular beam vecxz at line 1133).

## Expected vecxz Values Per Orientation

| Config | Spanning | dx | dy | vecxz |
|--------|----------|----|----|-------|
| TWO_C_FACING | X | >0 | 0 | `(0, -1, 0)` |
| TUBE_CENTER_OPENING | X | >0 | 0 | `(0, -1, 0)` |
| TUBE_SIDE_OPENING | Y | 0 | >0 | `(1, 0, 0)` |
| TWO_C_BACK_TO_BACK | X | >0 | 0 | `(0, -1, 0)` |
| Default | X | >0 | 0 | `(0, -1, 0)` |

## Test: Hand Calculation Verification

Add tests to `tests/verification/test_coupling_beam_axis_convention.py`:

### Test Case 1: X-Spanning Coupling Beam
```
Coupling beam: L = 1.5m, b = 300mm, h = 800mm (deep coupling beam)
Load: UDL w = 50 kN/m (gravity)
Spanning: along X axis
Expected:
  - Mz_midspan = wL²/8 = 50 * 1.5² / 8 = 14.06 kN-m (positive = sagging)
  - My ≈ 0
  - Stiffness uses Iz = 0.3 * 0.8³ / 12 = 1.28e-2 m⁴
  - vecxz = (0, -1, 0)
```

### Test Case 2: Y-Spanning Coupling Beam
```
Same section as Test 1, but spanning along Y
Load: UDL w = 50 kN/m (gravity)
Expected:
  - Same Mz_midspan = 14.06 kN-m (direction-independent for gravity)
  - My ≈ 0
  - Stiffness uses Iz = same
  - vecxz = (1, 0, 0)
```

### Test Case 3: Verify Both Orientations in Same Model
```
Create a model with both X-spanning and Y-spanning coupling beams.
Apply gravity load. Both should produce Mz as the dominant moment.
```

### Test Implementation Notes
- Follow the same pattern as `test_beam_axis_convention.py`: create a simply-supported coupling beam directly using `FEMModel`, apply local-Y UDL via `UniformLoad(load_type="Y")`, solve, extract reactions and displacements.
- For vecxz unit-testing (non-integration), call `_create_beam_element` with coupling beam endpoints and verify the `geometry_override` vecxz matches expected values. Alternatively, build a model with `BeamBuilder` and inspect elements.
- Use `math.hypot` consistently (it's the same formula as Phase 1 beams).

## Acceptance Criteria
1. Test Case 1: X-spanning coupling beam `Mz ≈ 14.06 kN-m`, `My ≈ 0`
2. Test Case 2: Y-spanning coupling beam `Mz ≈ 14.06 kN-m`, `My ≈ 0`
3. vecxz is computed from coordinates, not hardcoded, in BOTH beam_builder.py and model_builder.py
4. The `"coupling_beam": True` flag is preserved in beam_builder.py geometry dict
5. The `"parent_coupling_beam_id"` key is preserved in model_builder.py geometry dict
6. All existing tests still pass (same exclusion policy: `pytest tests/ --ignore=tests/verification/test_beam_shear_1x1.py -x --tb=short`)
7. vecxz computation is OUTSIDE the subdivision loop in model_builder.py (compute once, reuse for all 6 sub-elements)

## Guardrails
- **DO NOT** modify regular beam vecxz logic in `_create_beam_element` (Phase 1, lines 166-176 of beam_builder.py)
- **DO NOT** modify regular beam vecxz logic in `_create_subdivided_beam` (Phase 1, lines 1131-1137 of model_builder.py)
- **DO NOT** modify column code (Phase 2)
- **DO NOT** modify results_processor.py, visualization.py, or force tables
- **DO NOT** remove the `"coupling_beam": True` flag from beam_builder.py geometry
- **DO NOT** remove the `"parent_coupling_beam_id"` key from model_builder.py geometry
- Preserve the coupling element tag management logic (lines 576-577 and 588-590 of beam_builder.py)
- In model_builder.py, compute `cb_vecxz` ONCE before the `for i in range(NUM_SUBDIVISIONS)` loop at line 1859, not inside it

## Phase 2 Findings (Context for This Phase)
- Column vecxz confirmed correct at `(0.0, 1.0, 0.0)` — no column changes needed
- `materials.py` docstring now clarifies width=b (perpendicular to Mz plane) and height=h (in Mz plane)
- All 10 `get_elastic_beam_section` call sites verified for consistent argument ordering
- `math` module is already imported in both beam_builder.py and model_builder.py (from Phase 1)
- Phase 1 confirmed positive Mz = sagging for simply-supported beams under gravity

## Commit Message
```
fix(fem): compute coupling beam vecxz for ETABS convention

Apply same vecxz = (dy, -dx, 0) formula to coupling beams, fixing
both X-spanning and Y-spanning orientations. Previously hardcoded
to (0,0,1) regardless of spanning direction.
```

## Execution Log

### Status
- Completed on 2026-02-08.

### Changes Applied
- `src/fem/builders/beam_builder.py`
  - Replaced hardcoded coupling-beam `vecxz=(0.0, 0.0, 1.0)` override with computed:
    - `cb_dx = end_x - start_x`
    - `cb_dy = end_y - start_y`
    - `cb_vecxz = (cb_dy / cb_length_xy, -cb_dx / cb_length_xy, 0.0)` when `cb_length_xy > 1e-10`
    - fallback `(0.0, 0.0, 1.0)`.
  - Preserved geometry flag: `"coupling_beam": True`.
- `src/fem/model_builder.py`
  - Added one-time coupling-beam vecxz computation before the 6-sub-element loop.
  - Replaced hardcoded sub-element `vecxz` with computed `cb_vecxz`.
  - Preserved key: `"parent_coupling_beam_id"`.
- `tests/verification/test_coupling_beam_axis_convention.py` (new)
  - Added hand-calc verification for X- and Y-spanning coupling beams (L=1.5m, w=50kN/m, b=300mm, h=800mm):
    - support shear `wL/2 = 37.5 kN`
    - midspan moment from statics `wL^2/8 = 14.06 kN-m` (positive sagging)
    - midspan deflection `5wL^4/(384EI) = 0.00858 mm`
  - Added same-model dual-orientation test (X + Y coupling beams in one model).
  - Added vecxz behavior checks for both creation paths:
    - `BeamBuilder.create_coupling_beams` (including `"coupling_beam": True` preservation)
    - `build_fem_model` coupling sub-elements (including `"parent_coupling_beam_id"` preservation)
    - Config coverage: `TWO_C_FACING`, `TUBE_SIDE_OPENING`, `TWO_C_BACK_TO_BACK`.

### Verification Evidence
- Targeted Phase 3 tests:
  - `pytest tests/verification/test_coupling_beam_axis_convention.py tests/test_coupling_beam.py tests/test_fem_engine.py::TestShellAndCouplingBeamElements::test_coupling_beam_element_builds -x --tb=short`
  - Result: **25 passed, 22 skipped**.
- Full regression gate (same exclusion policy):
  - `pytest tests/ --ignore=tests/verification/test_beam_shear_1x1.py -x --tb=short`
  - Result: exit code **0**.
- Known-affected check file status:
  - `pytest tests/verification/test_beam_shear_1x1.py -x --tb=short`
  - Result: **6 passed**.
- Syntax/build sanity:
  - `python -m compileall src tests`
  - Result: completed successfully.

### Acceptance Criteria Mapping
- X- and Y-spanning coupling beams now use computed vecxz (no hardcoded `(0,0,1)`) in both builder paths.
- Expected orientation vectors verified:
  - X-span -> `(0, -1, 0)`
  - Y-span -> `(1, 0, 0)`
- Gravity bending magnitude and sign verified by statics-based midspan moment checks.
- Minor-axis response under gravity confirmed by near-zero orthogonal displacement and horizontal support reactions.
- Required geometry metadata keys are preserved (`"coupling_beam"`, `"parent_coupling_beam_id"`).
- Model-builder vecxz computation is outside the subdivision loop (computed once, reused).

### Notes
- `lsp_diagnostics` could not be executed in this environment because `basedpyright-langserver` is not installed on PATH.

## Next Phase Actions (Phase 4)
- Execute `phase-4-envelope-separation.md`:
  - Refactor `ElementForceEnvelope` to separate axis-specific fields:
    - `Vy/Vz` and `Mz/My` envelopes instead of collapsed `V/M`.
  - Update envelope aggregation in `src/fem/results_processor.py` to compute and track major/minor components separately.
  - Update critical-element selection/export logic to use major-axis defaults (`Mz`, `Vy`).
  - Add/adjust tests to verify axis-specific envelope values and backward-safe reporting behavior.
