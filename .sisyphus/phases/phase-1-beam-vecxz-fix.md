# Phase 1: Beam vecxz Fix + Hand-Calc Verification

## Prerequisite
Phase 0 (rename `local_y` → `vecxz`) must be complete.

## Objective
Fix the vecxz vector for ALL beam elements so that:
- `local_y = vertical (0,0,1)` for all horizontal beams
- `Mz = gravity bending = major-axis bending` (ETABS M33 convention)
- `Mz` uses `Iz = b*h³/12` = strong-axis MOI

## The Bug (Current State)
For a beam along global X with `vecxz = (0,0,1)`:
- OpenSees computes: `local_y = vecxz × local_x = (0,0,1) × (1,0,0) = (0,1,0)` horizontal
- `local_z = local_x × local_y = (1,0,0) × (0,1,0) = (0,0,1)` vertical
- Gravity bending → `My` (about horizontal local_y) → uses `Iy = h*b³/12` = WEAK axis
- **Result: WRONG stiffness for gravity bending**

## The Fix
Compute vecxz from beam node coordinates using the general formula:
```python
vecxz = (dy, -dx, 0.0)  # where (dx, dy) is the normalized beam plan direction
```

**Proof for beam along X** (`dx=1, dy=0`):
- `vecxz = (0, -1, 0)`
- `local_y = (0,-1,0) × (1,0,0) = (0, 0, 1)` = vertical ✓
- `local_z = (1,0,0) × (0,0,1) = (0, -1, 0)` = horizontal ✓
- Gravity bending → `Mz` (about horizontal local_z) → uses `Iz = b*h³/12` = STRONG axis ✓

**Proof for beam along Y** (`dx=0, dy=1`):
- `vecxz = (1, 0, 0)`
- `local_y = (1,0,0) × (0,1,0) = (0, 0, 1)` = vertical ✓
- `local_z = (0,1,0) × (0,0,1) = (1, 0, 0)` = horizontal ✓

**General formula works for any horizontal beam angle in plan.**

## Files to Modify

### 1. `src/fem/builders/beam_builder.py`

The `_create_beam_element` method already has access to `start_x, start_y, end_x, end_y` (see lines 140-141).

**Replace line 166** — compute vecxz from node coordinates instead of hardcoding:
```python
# BEFORE (after Phase 0 rename):
geom_base = geometry_override if geometry_override else {"vecxz": (0.0, 0.0, 1.0)}

# AFTER:
if geometry_override:
    geom_base = geometry_override
else:
    # Compute vecxz so local_y = vertical (ETABS convention: Mz = major-axis bending)
    dx = end_x - start_x
    dy = end_y - start_y
    length_xy = (dx**2 + dy**2) ** 0.5
    if length_xy > 1e-10:
        vecxz = (dy / length_xy, -dx / length_xy, 0.0)
    else:
        vecxz = (0.0, 0.0, 1.0)  # Fallback for zero-length (shouldn't happen)
    geom_base = {"vecxz": vecxz}
```

### 2. `src/fem/model_builder.py`

**Line 1136** — model_builder also creates beam elements directly.

The function `_create_subdivided_beam` (starts ~line 1090) has `start_x, start_y, end_x, end_y` at lines 1111-1112:
```python
start_x, start_y, start_z = start_node_obj.x, start_node_obj.y, start_node_obj.z
end_x, end_y, end_z = end_node_obj.x, end_node_obj.y, end_node_obj.z
```

**Insert vecxz computation before the geom dict at line 1135:**
```python
# BEFORE (lines 1135-1139):
geom = {
    "vecxz": (0.0, 0.0, 1.0),
    "parent_beam_id": parent_beam_id,
    "sub_element_index": i,
}

# AFTER:
# Compute vecxz so local_y = vertical (ETABS convention: Mz = major-axis bending)
dx = end_x - start_x
dy = end_y - start_y
length_xy = (dx**2 + dy**2) ** 0.5
if length_xy > 1e-10:
    vecxz_val = (dy / length_xy, -dx / length_xy, 0.0)
else:
    vecxz_val = (0.0, 0.0, 1.0)  # Fallback for zero-length

geom = {
    "vecxz": vecxz_val,
    "parent_beam_id": parent_beam_id,
    "sub_element_index": i,
}
```

**NOTE:** Compute `vecxz_val` ONCE before the `for i in range(NUM_SUBDIVISIONS)` loop (line 1132), not inside it — all sub-elements of the same beam share the same direction.

### 3. `src/fem/fem_engine.py` — NO CHANGES
The engine already reads whatever `vecxz` value is in the geometry dict and passes it to OpenSeesPy. No changes needed here.

## Test: Hand Calculation Verification

Create a new test file `tests/verification/test_beam_axis_convention.py`:

### Test Case 1: Simply-Supported Beam Along X
```
Beam: L = 6m, b = 300mm, h = 500mm
Load: UDL w = 10 kN/m (gravity, -Z direction)
Expected:
  - Mz_midspan = wL²/8 = 10 * 6² / 8 = 45 kN-m (positive = sagging)
  - Vy_support = wL/2 = 10 * 6 / 2 = 30 kN
  - Deflection uses Iz = 0.3 * 0.5³ / 12 = 3.125e-3 m⁴ (strong axis)
  - My should be ~0 (no lateral load)
```

### Test Case 2: Simply-Supported Beam Along Y
```
Beam: L = 6m, b = 300mm, h = 500mm (same section)
Load: UDL w = 10 kN/m (gravity, -Z direction)
Expected: Same Mz and Vy as Test Case 1 (direction-independent)
```

### Test Case 3: Verify Stiffness (Deflection Check)
```
Simply-supported beam, L = 6m, E = 30 GPa, b = 300mm, h = 500mm
UDL w = 10 kN/m
Expected midspan deflection = 5wL⁴ / (384 * E * Iz)
  = 5 * 10000 * 6⁴ / (384 * 30e9 * 3.125e-3)
  = 5 * 10000 * 1296 / (384 * 30e9 * 3.125e-3)
  = 64800000 / 36000000000
  = 1.8e-3 m = 1.8 mm
If the code returns deflection using Iy instead (wrong axis), the deflection would be:
  Iy = 0.5 * 0.3³ / 12 = 1.125e-3 m⁴
  deflection = 5.0 mm (2.78× larger) — detectable difference
```

### Test Case 4: Sign Convention
```
Verify that Mz at midspan is POSITIVE for a sagging beam (gravity load).
If Mz comes back negative, force_normalization.py needs a sign fix (tracked for later).
Record the actual sign — this informs Phase 2+ work.
```

### Test Implementation Notes
- Use OpenSeesPy directly in the test (create model, apply load, solve, extract forces)
- Use the actual `FEMEngine` / model builder if possible, to test the full pipeline
- Tolerance: 1% for force magnitudes, exact match for sign (positive/negative)

### CRITICAL: Known Test Impact — `tests/verification/test_beam_shear_1x1.py`

This file's helper `_extract_beam_end_shear_vz` (lines 93-122) extracts **Vz** as gravity shear.
After this fix, gravity shear moves from Vz to Vy:

| | Old axes (vecxz=0,0,1) | New axes (vecxz=dy,-dx,0) |
|---|---|---|
| Gravity shear | Vz (vertical) | **Vy** (vertical) |
| Lateral shear | Vy (horizontal) | **Vz** (horizontal) |

Tests that assert `Vz > threshold` under gravity load (lines 190-227) may now:
- **Fail** if Vz drops below the threshold (no horizontal load → Vz ≈ 0)
- **Pass silently** if shell-frame interaction produces enough horizontal Vz

**Action: DO NOT modify `test_beam_shear_1x1.py` in this phase.** This file is a complex benchmark
test that will be properly rewritten in Phase 6. If these tests fail in the full suite run, document
the failures in the execution log and exclude them from the "all non-affected tests pass" criterion.
The expected behavior is that `_extract_beam_end_shear_vz` now extracts the MINOR shear component.

## Acceptance Criteria
1. Test Case 1: `Mz_midspan ≈ 45 kN-m` (within 1%), positive sign
2. Test Case 2: Same results as Test Case 1 (proves direction-independence)
3. Test Case 3: Midspan deflection ≈ 1.8mm (proves Iz is used, not Iy)
4. Test Case 4: Positive Mz = sagging confirmed
5. `My` values are near-zero for gravity-only loading (no lateral load applied)
6. All non-affected tests still pass — **`tests/verification/test_beam_shear_1x1.py` is a KNOWN affected test** (Vz extraction now gets minor-axis shear). Document any failures from this file in the execution log but do not count them as blockers.
7. In `beam_builder.py`, the vecxz computation goes OUTSIDE the subdivision loop (compute once, reuse for all 4 sub-elements)

## Guardrails
- **DO NOT** modify `materials.py` — section property definitions stay as-is
- **DO NOT** modify `force_normalization.py` — sign fixes come later if needed
- **DO NOT** modify `results_processor.py` or `visualization.py`
- **DO NOT** modify column_builder.py — columns are Phase 2
- **DO NOT** change coupling beam code at line 575 — that's Phase 3
- **DO NOT** modify `tests/verification/test_beam_shear_1x1.py` — it will be rewritten in Phase 6
- If Test Case 4 shows negative Mz for sagging, RECORD this finding but do NOT fix it here. Note it in the test file as a comment for Phase 2+ to address.
- In `beam_builder.py`, compute vecxz BEFORE the subdivision loop (line 166 is before line 169 `for i in range(NUM_SUBDIVISIONS)`), not inside it. Same for `model_builder.py` — compute before line 1132's loop.

## Commit Message
```
fix(fem): compute beam vecxz for ETABS major-axis convention

Compute vecxz = (dy, -dx, 0) from beam node coordinates so that
local_y = vertical, making Mz = gravity/major-axis bending using
Iz (strong-axis MOI). Verified with hand calculations.

ETABS convention: M33/Mz = always major-axis bending.
```

## Execution Log

### Status
- Completed on 2026-02-08.

### Changes Applied
- `src/fem/builders/beam_builder.py`
  - Replaced hardcoded beam vecxz with direction-based computation:
    - `dx = end_x - start_x`
    - `dy = end_y - start_y`
    - `vecxz = (dy / length_xy, -dx / length_xy, 0.0)` when `length_xy > 1e-10`
    - fallback `vecxz = (0.0, 0.0, 1.0)` for degenerate length.
  - Computation is performed once before the subdivision loop and reused by all 4 sub-elements.
- `src/fem/model_builder.py`
  - In `_create_subdivided_beam`, added the same direction-based vecxz calculation once before the subdivision loop.
  - Replaced static vecxz assignment in each sub-element geometry with computed `vecxz_val`.
- `tests/verification/test_beam_axis_convention.py` (new)
  - Added beam-axis convention verification with hand-calculation checks.
  - Added direct vecxz checks for both directions in both generation paths:
    - `BeamBuilder._create_beam_element`
    - `model_builder._create_subdivided_beam`
  - Added simply-supported 6m beam checks for X- and Y-spanning beams:
    - support shear `wL/2 = 30 kN`
    - midspan moment from statics `wL^2/8 = 45 kN-m` (positive sagging)
    - midspan deflection `5wL^4/(384EI) = 1.8 mm` using `Iz`
    - direction-independence between X and Y spans.

### Verification Evidence
- vecxz formula now present in both target files:
  - `src/fem/builders/beam_builder.py:173`
  - `src/fem/model_builder.py:1135`
- New and directly impacted tests:
  - `pytest tests/verification/test_beam_axis_convention.py tests/test_beam_subdivision.py -x --tb=short`
  - Result: **14 passed**.
- Full regression excluding known-affected file gate:
  - `pytest tests/ --ignore=tests/verification/test_beam_shear_1x1.py -x --tb=short`
  - Result: exit code **0**.
- Known-affected file check (document-only per phase instructions):
  - `pytest tests/verification/test_beam_shear_1x1.py -x --tb=short`
  - Result: **6 passed** in current run (no blocker observed).
- Syntax/build sanity:
  - `python -m compileall src tests`
  - Result: completed successfully.

### Notes
- `lsp_diagnostics` could not be executed in this environment because `basedpyright-langserver` is not installed on PATH.
- `tests/verification/test_beam_shear_1x1.py` was intentionally left unchanged per guardrails.

## Next Phase Actions (Phase 2)
- Execute `phase-2-column-verify-mapping.md`:
  - Add `tests/verification/test_column_axis_convention.py` with cantilever X/Y load verification and square-column symmetry check.
  - Verify current column vecxz `(0.0, 1.0, 0.0)` against hand-calcs before changing behavior.
  - Add explicit axis/section mapping documentation in:
    - `src/fem/builders/column_builder.py`
    - `src/fem/materials.py`
  - Audit call sites to ensure width/height ordering (`b` then `h`) is consistent across beam/column section creation.
