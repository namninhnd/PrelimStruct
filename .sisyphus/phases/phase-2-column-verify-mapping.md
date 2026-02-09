# Phase 2: Column Verification + Explicit h/b Mapping

## Prerequisite
Phase 0 (rename) and Phase 1 (beam fix) must be complete.

## Objective
1. **Verify** that the current column vecxz `(0.0, 1.0, 0.0)` already produces correct axis alignment
2. **Add explicit mapping** that documents and enforces which dimension (h or b) maps to which local axis
3. Apply belt-and-suspenders enforcement in BOTH `materials.py` (receiver) and `column_builder.py` (caller)

## Current Column Axes (Analysis)

Columns are vertical: `local_x = (0, 0, 1)` (element axis from bottom to top node).

With current `vecxz = (0, 1, 0)`:
- `local_y = vecxz × local_x = (0,1,0) × (0,0,1) = (1, 0, 0)` = global X
- `local_z = local_x × local_y = (0,0,1) × (1,0,0) = (0, 1, 0)` = global Y

Force-stiffness mapping:
- `Mz` = bending about local_z (global Y) → stiffness = `E * Iz` = `E * b * h³ / 12`
- `My` = bending about local_y (global X) → stiffness = `E * Iy` = `E * h * b³ / 12`

**IF depth h maps to local_y (global X):**
- A lateral force in X → deflection in local_y → bending about local_z → `Mz` → uses `Iz = b*h³/12` = strong axis ✓
- A lateral force in Y → deflection in local_z → bending about local_y → `My` → uses `Iy = h*b³/12` = weak axis ✓
- **ETABS convention satisfied: Mz = M33 = major axis ✓**

**HYPOTHESIS: Columns are already correct. The hand-calc test below will confirm.**

## Step 1: Hand-Calc Verification Test

Create test in `tests/verification/test_column_axis_convention.py`:

### Test Case 1: Cantilever Column with Lateral Load in X
```
Column: H = 3m (height), b = 300mm (width), h = 500mm (depth)
Assume: depth h = 500mm along local_y = global X direction
Load: P = 100 kN lateral force at top, in +X direction
Expected:
  - Mz_base = P * H = 100 * 3 = 300 kN-m (major-axis bending about Y)
  - My should be ~0 (no Y-direction force)
  - Deflection at top = P * H³ / (3 * E * Iz)
    = 100e3 * 3³ / (3 * 30e9 * 0.3 * 0.5³ / 12)
    = 2.7e6 / (3 * 30e9 * 3.125e-3)
    = 2.7e6 / 2.8125e8
    = 9.6e-3 m = 9.6 mm
```

### Test Case 2: Cantilever Column with Lateral Load in Y
```
Same column, P = 100 kN in +Y direction
Expected:
  - My_base = P * H = 100 * 3 = 300 kN-m (minor-axis bending about X)
  - Mz should be ~0
  - Deflection at top = P * H³ / (3 * E * Iy)
    = 100e3 * 3³ / (3 * 30e9 * 0.5 * 0.3³ / 12)
    = 2.7e6 / (3 * 30e9 * 1.125e-3)
    = 2.7e6 / 1.0125e8
    = 26.67e-3 m = 26.7 mm
  Ratio: 26.7 / 9.6 ≈ 2.78 (= Iz/Iy ratio = h²/b² = 500²/300² = 2.78) ✓
```

### Test Case 3: Square Column (b = h = 400mm)
```
Square column: b = h = 400mm, H = 3m
Load: P = 100 kN in +X
Expected:
  - Mz = My = same magnitude (Iz = Iy for square section)
  - Deflection same in both directions
This verifies no asymmetry bugs for the symmetric case.
```

### Test Logic
- If Test 1 gives Mz ≈ 300 kN-m → columns are correct, proceed to Step 2
- If Test 1 gives My ≈ 300 kN-m instead → columns have the same bug as beams, need vecxz fix
- Record actual values and document which outcome occurred

## Step 2: Explicit Mapping in `column_builder.py`

**File: `src/fem/builders/column_builder.py`**

Add a clear docstring/comment at the column geometry assignment (lines 126 and 150).

**NOTE:** model_builder.py also has column vecxz at **line 1299** (shifted from 1291 after Phase 1 added beam vecxz computation). Add the same convention comment there too.

```python
# Column local axis convention (ETABS-compatible):
#   local_x = column axis (vertical, bottom → top)
#   local_y = global X direction (depth h aligns here)
#   local_z = global Y direction (width b aligns here)
#   vecxz = (0, 1, 0) produces this orientation for vertical columns
#
# Section property mapping:
#   Iz = b * h³ / 12 → Mz stiffness (major axis, bending about local_z = Y)
#   Iy = h * b³ / 12 → My stiffness (minor axis, bending about local_y = X)
geom: Dict[str, Any] = {"vecxz": (0.0, 1.0, 0.0)}
```

Apply the same comment at line 150 for the non-subdivided path.

## Step 3: Explicit Mapping in `materials.py`

**File: `src/fem/materials.py`**

Update the section property calculation (around lines 322-329) with explicit documentation:

```python
# Convert dimensions to meters
# width (b): dimension perpendicular to bending plane of Mz (along local_z for columns)
# height (h): dimension in the bending plane of Mz (along local_y for beams/columns)
b = width / 1000  # mm to m
h = height / 1000  # mm to m

# Section properties
A = b * h  # m²
# Iz = strong-axis MOI when h > b (used for Mz = major-axis bending)
Iz = b * h**3 / 12  # m⁴ (bending about local z-axis)
# Iy = weak-axis MOI when h > b (used for My = minor-axis bending)
Iy = h * b**3 / 12  # m⁴ (bending about local y-axis)
```

Also update the function's docstring to clarify the width/height convention:

```python
"""Create elastic beam section properties for rectangular cross-section.

Args:
    width: Section width in mm (b) — perpendicular to Mz bending plane.
           For beams: horizontal width. For columns: dimension along local_z.
    height: Section depth in mm (h) — in the Mz bending plane.
            For beams: vertical depth. For columns: dimension along local_y.
    ...
"""
```

## Step 4: Verify Caller Consistency

All 10 call sites of `get_elastic_beam_section` have been located. Verify each passes `width` (b) first and `height/depth` (h) second:

| # | File | Line | width= | height= | Status |
|---|------|------|--------|---------|--------|
| 1 | `builders/director.py` | 143 | `beam_sizes["primary"][0]` | `beam_sizes["primary"][1]` | Verify tuple order |
| 2 | `builders/director.py` | 149 | `beam_sizes["secondary"][0]` | `beam_sizes["secondary"][1]` | Verify tuple order |
| 3 | `builders/director.py` | 155 | `self.column_width` | `self.column_depth` | **KEY — verify these names match physical meaning** |
| 4 | `builders/beam_builder.py` | 514 | `coupling_beam_template.width` | `coupling_beam_template.depth` | Likely correct |
| 5 | `fem_engine.py` | 852 | `beam_width` (positional) | `beam_height` (positional) | Positional args — verify order |
| 6 | `fem_engine.py` | 857 | `column_width` (positional) | `column_height` (positional) | **Positional — verify order matches** |
| 7 | `model_builder.py` | 1204 | `beam_sizes["primary"][0]` | `beam_sizes["primary"][1]` | Same as #1 |
| 8 | `model_builder.py` | 1210 | `beam_sizes["secondary"][0]` | `beam_sizes["secondary"][1]` | Same as #2 |
| 9 | `model_builder.py` | 1216 | `column_width` | `column_depth` | **KEY — trace where these come from in ProjectData** |
| 10 | `model_builder.py` | 1769 | `coupling_beam_template.width` | `coupling_beam_template.depth` | Same as #4 |

**Critical sites are #3, #6, and #9** — column section creation. Trace `column_width` and `column_depth` back to the `ProjectData` / `GeometryInput` data model to confirm:
- `column_width` = the SMALLER dimension (b, along local_z = global Y)
- `column_depth` = the LARGER dimension (h, along local_y = global X)

If the data model uses generic names like `column_size` without distinguishing width/depth, document which index maps to which axis.

If any call site passes `height` as the first argument (i.e., swaps b and h), fix the call site — NOT the formula.

**Also add docstrings/comments to `director.py:155-158`** — this file was not in the original plan but it creates column sections too.

## Phase 1 Findings (Context for This Phase)
- **Positive Mz = sagging** confirmed for beams via statics-based moment check
- Beam tests used `load_type="Y"` (local Y) for gravity UDL — after fix, local_y = vertical, so this applies load downward
- For column tests: apply lateral load as a **point load at the top node** (not UDL). Use OpenSeesPy `ops.load(node, Fx, Fy, Fz, Mx, My, Mz)` or the model's load mechanism
- `test_beam_shear_1x1.py` was documented as known-affected but still passes (document only)
- model_builder.py column vecxz is now at **line 1299** (shifted +8 from Phase 1 beam changes)

## Acceptance Criteria
1. Test Case 1: Column `Mz_base ≈ 300 kN-m` for X-direction load (confirms major axis)
2. Test Case 2: Column `My_base ≈ 300 kN-m` for Y-direction load (confirms minor axis)
3. Test Case 2 deflection ≈ 2.78× Test Case 1 deflection (confirms Iz/Iy ratio)
4. Test Case 3: Square column shows symmetric behavior
5. Docstrings and comments added to `column_builder.py`, `materials.py`, and `director.py`
6. All 10 call sites of `get_elastic_beam_section` verified for correct width/height argument order
7. All existing tests still pass (same `test_beam_shear_1x1.py` exclusion as Phase 1 if needed)

## Guardrails
- **DO NOT** change the column vecxz value `(0.0, 1.0, 0.0)` unless the hand-calc test PROVES it's wrong
- **DO NOT** add a column rotation angle property
- **DO NOT** modify beam_builder.py — beam vecxz is done (Phase 1)
- **DO NOT** modify beam vecxz computation in model_builder.py (lines 1131-1137) — only touch column vecxz at line 1299
- **DO NOT** modify results_processor.py, visualization.py, or force tables
- If columns ARE broken (Test Case 1 fails): apply the same fix approach as Phase 1 — compute vecxz from column orientation. Document the specific vecxz value needed and implement it.

## Commit Message
```
fix(fem): add explicit column axis-to-section mapping

Verify column local axes match ETABS convention (Mz = major axis).
Add explicit documentation mapping width(b)/height(h) to local axis
directions in both materials.py and column_builder.py.
```

## Execution Log

### Status
- Completed on 2026-02-08.

### Changes Applied
- `tests/verification/test_column_axis_convention.py` (new)
  - Added hand-calculation verification suite for cantilever columns with `vecxz=(0.0, 1.0, 0.0)`.
  - Case 1 (X load): verifies major-axis response (`Mz`) and top deflection against 9.6 mm target.
  - Case 2 (Y load): verifies minor-axis response (`My`) and top deflection against 26.7 mm target.
  - Verifies deflection ratio `delta_y / delta_x ~= 2.78` and positive bending magnitude `P*H`.
  - Case 3 (square column): verifies symmetric X/Y deflection behavior.
- `src/fem/builders/column_builder.py`
  - Added explicit column local-axis and section-mapping comments at both vecxz assignment paths.
- `src/fem/model_builder.py`
  - Added explicit column local-axis and section-mapping comment at column vecxz assignment.
  - Updated `_extract_column_dims` docstring to formalize `(width=b, depth=h)` mapping semantics.
- `src/fem/materials.py`
  - Updated `get_elastic_beam_section` docstring to clarify `width=b` and `height=h` mapping.
  - Added explicit comments for `Iz=b*h^3/12` (major-axis) and `Iy=h*b^3/12` (minor-axis) usage.
- `src/fem/builders/director.py`
  - Added explicit comment at column section creation call clarifying width/depth mapping to local axes.

### Column Verification Results (Hand-Calc Checks)
- Test Case 1 (X load, 300x500 mm, H=3m, P=100kN):
  - `Mz_base ~= 300 kN-m`, `My_base ~= 0`, top deflection `~= 9.6 mm`.
- Test Case 2 (Y load, same column):
  - `My_base ~= 300 kN-m`, `Mz_base ~= 0`, top deflection `~= 26.7 mm`.
- Ratio check:
  - `26.7 / 9.6 ~= 2.78` confirmed.
- Square-column check (400x400 mm):
  - X and Y deflections are symmetric (within tolerance).

### Call-Site Consistency Audit (`get_elastic_beam_section`)
- All 10 located call sites were reviewed for `width` then `height/depth` order.
- Verified as consistent:
  1. `src/fem/builders/director.py:143`
  2. `src/fem/builders/director.py:149`
  3. `src/fem/builders/director.py:157`
  4. `src/fem/builders/beam_builder.py:514`
  5. `src/fem/fem_engine.py:852`
  6. `src/fem/fem_engine.py:857`
  7. `src/fem/model_builder.py:1208`
  8. `src/fem/model_builder.py:1214`
  9. `src/fem/model_builder.py:1220`
  10. `src/fem/model_builder.py:1778`
- Critical column paths (#3, #6, #9) trace to `_extract_column_dims`, which now explicitly documents width/depth mapping.

### Verification Evidence
- Focused Phase 2 regression:
  - `pytest tests/verification/test_column_axis_convention.py tests/test_column_subdivision.py tests/verification/test_column_forces_1x1.py -x --tb=short`
  - Result: **24 passed**.
- Full regression gate (same exclusion policy as prior phase):
  - `pytest tests/ --ignore=tests/verification/test_beam_shear_1x1.py -x --tb=short`
  - Result: exit code **0**.
- Known-affected check file status (informational):
  - `pytest tests/verification/test_beam_shear_1x1.py -x --tb=short`
  - Result: **6 passed**.
- Syntax/build sanity:
  - `python -m compileall src tests`
  - Result: completed successfully.

### Notes
- `lsp_diagnostics` could not be executed in this environment because `basedpyright-langserver` is not installed on PATH.
- Column vecxz value remained unchanged at `(0.0, 1.0, 0.0)`; tests confirmed this orientation is correct.

## Next Phase Actions (Phase 3)
- Execute `phase-3-coupling-beam-vecxz.md`:
  - Replace hardcoded coupling-beam vecxz with computed `(dy / L, -dx / L, 0.0)` in:
    - `src/fem/builders/beam_builder.py` coupling-beam override path.
    - `src/fem/model_builder.py` coupling-beam creation path.
  - Preserve `"coupling_beam": True` geometry flag and existing tag-management logic.
  - Add `tests/verification/test_coupling_beam_axis_convention.py` for X/Y spanning coupling beams.
