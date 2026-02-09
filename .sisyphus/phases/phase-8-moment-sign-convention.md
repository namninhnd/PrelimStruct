# Phase 8: Moment Sign Convention Fix

## Problem Statement

The force diagram displays moment values with **inverted signs**: sagging moments appear as negative and hogging moments appear as positive. The desired convention is **positive = sagging, negative = hogging** (ETABS M33 convention).

## Root Cause

OpenSeesPy `localForce` returns element END forces (force the element exerts on the nodes), which have different sign relationships to engineering internal forces for **shear** vs **moments**:

| DOF type | i-end relationship | j-end relationship |
|----------|-------------------|-------------------|
| **N** (axial) | OpenSees = Engineering | OpenSees = -Engineering |
| **Vy, Vz** (shear) | OpenSees = Engineering | OpenSees = -Engineering |
| **Mz, My, T** (moments/torsion) | OpenSees = **-Engineering** | OpenSees = **+Engineering** |

**Proof** (fixed-fixed beam under gravity UDL `wy = -w`):
- OpenSees returns: `Mz_i = +wL^2/12` (positive), `Mz_j = -wL^2/12` (negative)
- Engineering convention: `M_i = -wL^2/12` (hogging=negative), `M_j = -wL^2/12` (hogging=negative)
- Therefore: `Mz_i(OpenSees) = -Mz_i(engineering)` and `Mz_j(OpenSees) = +Mz_j(engineering)`

The current code (`force_normalization.py`) treats moments the **same** as shear (negate j-end only), but they need the **opposite** treatment (negate i-end only):

| | Current code | Correct behavior |
|--|---|---|
| **Shear i-end** | Keep raw ✓ | Keep raw |
| **Shear j-end** | Negate ✓ | Negate |
| **Moment i-end** | Keep raw ✗ | **Negate** |
| **Moment j-end** | Negate ✗ | **Keep raw** |

## Diagram Shape Consequence

After fix, the diagram shape will change from "tension side" (accidental) to **"ETABS style"** (positive drawn above beam). This is consistent with the existing annotation `"Positive Mz = sagging"` at lines 2647, 3275, 4095 in `visualization.py`.

---

## Files to Modify (5 source files + 3 test files)

### 1. `src/fem/force_normalization.py` (Core fix)

**Current code (lines 1-54):**

```python
NEGATED_J_END_TYPES: Set[str] = {"Vy", "Vz", "My", "Mz", "T"}

def normalize_end_force(force_i: float, force_j: float, force_type: str) -> float:
    if force_type in NEGATED_J_END_TYPES:
        return -force_j
    return _normalize_axial_force(force_i, force_j)
```

**Required changes:**

1. **Line 12**: Split `NEGATED_J_END_TYPES` into two sets:
   ```python
   NEGATED_J_END_TYPES: Set[str] = {"Vy", "Vz"}        # Shear: negate j-end
   NEGATED_I_END_TYPES: Set[str] = {"My", "Mz", "T"}   # Moments: negate i-end
   ```

2. **Lines 21-24**: Update `normalize_end_force` for j-end behavior:
   ```python
   def normalize_end_force(force_i: float, force_j: float, force_type: str) -> float:
       """Normalize j-end force for display. Negates j-end shear, keeps j-end moments raw."""
       if force_type in NEGATED_J_END_TYPES:
           return -force_j
       if force_type in NEGATED_I_END_TYPES:
           return force_j  # Moments: j-end already matches engineering convention
       return _normalize_axial_force(force_i, force_j)
   ```

3. **Add new function** after `normalize_end_force`:
   ```python
   def normalize_i_end_force(force_i: float, force_type: str) -> float:
       """Normalize i-end force for display. Negates i-end moments, keeps i-end shear raw."""
       if force_type in NEGATED_I_END_TYPES:
           return -force_i
       return force_i
   ```

4. **Lines 27-53**: Update `get_normalized_forces` to return BOTH i and j values:
   ```python
   def get_normalized_forces(forces: Dict[str, float]) -> Dict[str, float]:
       """Return normalized forces for both i-end and j-end display.

       Returns dict with keys like 'N_i', 'N_j', 'Vy_i', 'Vy_j', etc.
       for consistency, or the existing flat keys for j-end only (backward compat).
       """
       # ... keep existing logic but fix moment signs
   ```

   Specifically, apply `normalize_i_end_force` to i-end values:
   - `"N": normalize_i_end_force(n_i, "N")` for i-end (= n_i, unchanged)
   - `"Mz": normalize_i_end_force(mz_i, "Mz")` for i-end (= -mz_i, NEGATED)

   **NOTE**: `get_normalized_forces` currently returns j-end normalized values. The function's consumers should be checked. If it's only used for j-end display, update the j-end Mz/My/T values to NOT negate (remove the existing negation).

5. **Update the module docstring** (lines 1-8) to reflect the new convention.

---

### 2. `src/fem/visualization.py` (Diagram rendering)

**Current code (lines 617-622):**

```python
def _display_node_force(force_i: float, force_j: float, force_type: str, at_j_end: bool = False) -> float:
    value = _display_end_force(force_i, force_j, force_type) if at_j_end else force_i
    if force_type == "N":
        return -value
    return value
```

**Required change:**

```python
def _display_node_force(force_i: float, force_j: float, force_type: str, at_j_end: bool = False) -> float:
    if at_j_end:
        value = _display_end_force(force_i, force_j, force_type)
    else:
        # i-end: negate moments to convert OpenSees convention → engineering convention
        from src.fem.force_normalization import normalize_i_end_force
        value = normalize_i_end_force(force_i, force_type)
    if force_type == "N":
        return -value
    return value
```

**Alternative** (to avoid import inside function): import `normalize_i_end_force` at the top of the file (line 79 area) alongside the existing import of `normalize_end_force as _normalize_end_force_shared`.

Update line 79:
```python
from src.fem.force_normalization import normalize_end_force as _normalize_end_force_shared, normalize_i_end_force as _normalize_i_end_shared
```

Then in `_display_node_force`:
```python
def _display_node_force(force_i: float, force_j: float, force_type: str, at_j_end: bool = False) -> float:
    if at_j_end:
        value = _display_end_force(force_i, force_j, force_type)
    else:
        value = _normalize_i_end_shared(force_i, force_type)
    if force_type == "N":
        return -value
    return value
```

**This function is called at the following locations** (all use `_display_node_force`):
- Line 1241-1246: subdivided element i-end forces (elevation view)
- Line 1260-1264: subdivided element j-end forces (elevation view)
- Line 1368-1378: single element forces (elevation view)
- Line 1536-1541: subdivided element i-end forces (plan view)
- Line 1555-1560: subdivided element j-end forces (plan view)
- Line 1668-1676: single element forces (plan view)

All these locations call `_display_node_force` which will automatically pick up the fix. **No changes needed at the call sites.**

---

### 3. `src/ui/components/beam_forces_table.py` (Beam table)

**Current code for i-end nodes (lines 108-118):**

```python
if node_i and forces:
    node_positions.append((node_i.x, node_i.y, node_i.z))
    n_i = forces.get('N_i', 0) / 1000.0
    force_values.append({
        'N_i': n_i,
        'Vy_i': forces.get('Vy_i', forces.get('V_i', 0)) / 1000.0,
        'Vz_i': forces.get('Vz_i', 0) / 1000.0,
        'My_i': forces.get('My_i', forces.get('M_i', 0)) / 1000.0,
        'Mz_i': forces.get('Mz_i', 0) / 1000.0,
        'T_i': forces.get('T_i', 0) / 1000.0,
    })
```

**Required change** - negate moment i-end values:

```python
if node_i and forces:
    node_positions.append((node_i.x, node_i.y, node_i.z))
    n_i = forces.get('N_i', 0) / 1000.0
    force_values.append({
        'N_i': n_i,
        'Vy_i': forces.get('Vy_i', forces.get('V_i', 0)) / 1000.0,
        'Vz_i': forces.get('Vz_i', 0) / 1000.0,
        'My_i': -forces.get('My_i', forces.get('M_i', 0)) / 1000.0,
        'Mz_i': -forces.get('Mz_i', 0) / 1000.0,
        'T_i': -forces.get('T_i', 0) / 1000.0,
    })
```

**Current code for j-end node (lines 143-156):**

```python
normalized_my = self._display_end_force(my_i, my_j, "My")
normalized_mz = self._display_end_force(mz_i, mz_j, "Mz")
normalized_t = self._display_end_force(t_i, t_j, "T")
```

These call `normalize_end_force()` which will be updated in step 1 to return `force_j` (raw, not negated) for moments. **No additional changes needed here** since the core function is fixed.

**Import**: Add `normalize_i_end_force` import at line 14:
```python
from src.fem.force_normalization import normalize_end_force, normalize_i_end_force
```

**Alternative** (cleaner): Use `normalize_i_end_force` for i-end extraction instead of manual negation. This keeps the logic centralized:
```python
force_values.append({
    'N_i': n_i,
    'Vy_i': forces.get('Vy_i', forces.get('V_i', 0)) / 1000.0,
    'Vz_i': forces.get('Vz_i', 0) / 1000.0,
    'My_i': normalize_i_end_force(forces.get('My_i', forces.get('M_i', 0)) / 1000.0, "My"),
    'Mz_i': normalize_i_end_force(forces.get('Mz_i', 0) / 1000.0, "Mz"),
    'T_i': normalize_i_end_force(forces.get('T_i', 0) / 1000.0, "T"),
})
```

---

### 4. `src/ui/components/column_forces_table.py` (Column table)

Same pattern as beam table. Two locations:

**i-end nodes (lines 99-108):**

Current:
```python
'My_i': forces.get('My_i', forces.get('M_i', 0)) / 1000.0,
'Mz_i': forces.get('Mz_i', 0) / 1000.0,
'T_i': forces.get('T_i', 0) / 1000.0,
```

Change to (negate moments at i-end):
```python
'My_i': -forces.get('My_i', forces.get('M_i', 0)) / 1000.0,
'Mz_i': -forces.get('Mz_i', 0) / 1000.0,
'T_i': -forces.get('T_i', 0) / 1000.0,
```

**j-end node (lines 136-138):** `normalize_end_force` is called via `self._display_end_force`. After the core fix in `force_normalization.py`, this will automatically return `force_j` (raw) for moments. **No additional changes needed.**

**Import**: Add `normalize_i_end_force` to the import at line 7 if using the centralized approach.

---

### 5. `tests/test_force_normalization.py` (Unit tests - MUST UPDATE)

Multiple test assertions need updating to reflect the new behavior:

**Line 81-86: `test_my_negated_at_j_end`**
- Old: `assert result == -50.0` (My j-end was negated)
- New: `assert result == 50.0` (My j-end is now RAW)
- Rename test to `test_my_raw_at_j_end`

**Line 88-93: `test_mz_negated_at_j_end`**
- Old: `assert result == 80.0` (Mz j-end: -(-80) = 80)
- New: `assert result == -80.0` (Mz j-end is now RAW: -80)
- Rename test to `test_mz_raw_at_j_end`

**Line 95-100: `test_t_negated_at_j_end`**
- Old: `assert result == -15.0` (T j-end was negated)
- New: `assert result == 15.0` (T j-end is now RAW)
- Rename test to `test_t_raw_at_j_end`

**Line 129: `test_table_and_overlay_same_for_mz`**
- Old: `assert table_result == 75.0` (-(-75) = 75)
- New: `assert table_result == -75.0` (raw j-end: -75)

**Lines 154-169: `test_all_force_types_consistency`**
- Need to update to check `NEGATED_J_END_TYPES` (now only Vy, Vz) AND `NEGATED_I_END_TYPES` (My, Mz, T)
- For Vy, Vz: `assert result == -force_j`
- For My, Mz, T: `assert result == force_j` (raw, not negated)

**Lines 190-197: `test_normalizes_all_force_components`**
- Old: `assert result["My"] == -40.0` and `assert result["Mz"] == 20.0` and `assert result["T"] == -5.0`
- New: `assert result["My"] == 40.0` and `assert result["Mz"] == -20.0` and `assert result["T"] == 5.0`

**Lines 231-235: `test_handles_2d_force_keys`**
- Old: `assert result["Mz"] == 50.0` (-(-50) = 50)
- New: `assert result["Mz"] == -50.0` (raw j-end: -50)

**Lines 241-246: `test_contains_expected_types`**
- Old: `expected = {"Vy", "Vz", "My", "Mz", "T"}`
- New: `expected = {"Vy", "Vz"}` (only shear in j-end negation set)
- Add new test for `NEGATED_I_END_TYPES == {"My", "Mz", "T"}`

**Add new tests** for `normalize_i_end_force`:
```python
class TestNormalizeIEndForce:
    def test_mz_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(100.0, "Mz") == -100.0

    def test_my_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(50.0, "My") == -50.0

    def test_t_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(20.0, "T") == -20.0

    def test_vy_not_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(30.0, "Vy") == 30.0

    def test_n_not_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(100.0, "N") == 100.0
```

---

### 6. `tests/test_column_forces_table.py` (Column table tests)

**Line 232-235: `test_j_end_forces_normalized_correctly`**
- Old: expects My j-end = 0.5 kNm (was: `-(-500)/1000 = 0.5`)
- New: expects My j-end = -0.5 kNm (raw: `-500/1000 = -0.5`)
- Update assertion: `assert abs(last_row["My-minor (kNm)"] - (-0.5)) < 0.01`

**Line 213-216: test description**
- Update: "Vy, Vz should be negated; My, Mz, T should be RAW (not negated)"

---

### 7. `tests/verification/test_beam_shear_1x1.py` (Beam shear verification)

**Lines 106-119**: Uses `normalize_end_force(vy_i, vy_j, "Vy")` for shear.
- Shear normalization is UNCHANGED (still negates j-end for Vy). **No changes needed.**

---

## Execution Order

1. **`src/fem/force_normalization.py`** - Core fix (must be first)
2. **`src/fem/visualization.py`** - Update `_display_node_force`
3. **`src/ui/components/beam_forces_table.py`** - Fix i-end moment signs
4. **`src/ui/components/column_forces_table.py`** - Fix i-end moment signs
5. **`tests/test_force_normalization.py`** - Update test expectations
6. **`tests/test_column_forces_table.py`** - Update test expectations
7. Run full test suite: `python -m pytest tests/ -x -q`

## Gate Criteria

1. All existing tests pass (after updating sign expectations)
2. For a gravity-loaded beam:
   - Midspan Mz should be **positive** (sagging)
   - Support Mz should be **negative** (hogging)
3. `Mz >> My` for gravity beams (unchanged, only signs flip)
4. Shear signs unchanged (Vy, Vz behavior not affected)
5. Axial N signs unchanged

## Verification Script

After implementing, run this quick diagnostic to confirm the fix:

```python
# Quick verification: build a beam, check Mz signs
from tests.verification.benchmarks import build_benchmark_project_1x1, make_benchmark_options
from src.fem.model_builder import build_fem_model
from src.fem.solver import analyze_model
from src.fem.results_processor import ResultsProcessor

project = build_benchmark_project_1x1()
model = build_fem_model(project, make_benchmark_options())
results = analyze_model(model, load_cases=["SDL"])
result = results["SDL"]

# Find a beam midspan sub-element
for tag, elem in model.elements.items():
    pid = elem.geometry.get("parent_beam_id")
    if pid and elem.geometry.get("sub_element_index", 0) == 2:
        forces = result.element_forces.get(tag, {})
        mz_i = forces.get("Mz_i", 0)
        print(f"Raw OpenSees Mz_i at midspan: {mz_i:.1f} N-m")
        print(f"Expected: NEGATIVE (OpenSees convention for sagging at i-end)")

        from src.fem.force_normalization import normalize_i_end_force
        display_mz = normalize_i_end_force(mz_i / 1000.0, "Mz")
        print(f"Display Mz at midspan: {display_mz:.1f} kN-m")
        print(f"Expected: POSITIVE (sagging = positive in engineering convention)")
        break
```

## Risk Assessment

- **Low risk**: Shear (Vy, Vz) and axial (N) sign handling is UNCHANGED
- **Medium risk**: All moment (Mz, My) and torsion (T) display values will flip sign
- **Not affected**: `solver.py` raw force extraction, `results_processor.py` envelope logic (uses `abs()`)
- **Not affected**: `create_opsvis_force_diagram` at line 3998 — this calls `opsv.section_force_diagram_3d` which uses its own sign convention directly from OpenSees

## Summary Table

| File | Change | Lines |
|------|--------|-------|
| `src/fem/force_normalization.py` | Split NEGATED sets, add `normalize_i_end_force`, fix `normalize_end_force` for moments | 1-54 |
| `src/fem/visualization.py` | Update `_display_node_force` to negate i-end moments | 79, 617-622 |
| `src/ui/components/beam_forces_table.py` | Negate My_i, Mz_i, T_i at i-end extraction | 14, 111-118 |
| `src/ui/components/column_forces_table.py` | Negate My_i, Mz_i, T_i at i-end extraction | 7, 101-108 |
| `tests/test_force_normalization.py` | Update sign expectations for moments, add i-end tests | Multiple |
| `tests/test_column_forces_table.py` | Update j-end My expectation | 232-235 |

---

## Execution Log (2026-02-09)

### Implemented Changes

1. **Core normalization fix** (`src/fem/force_normalization.py`)
   - Split j-end negation set into:
     - `NEGATED_J_END_TYPES = {"Vy", "Vz"}`
     - `NEGATED_I_END_TYPES = {"My", "Mz", "T"}`
   - Updated `normalize_end_force()` so moments/torsion are **raw at j-end**.
   - Added `normalize_i_end_force()` so moments/torsion are **negated at i-end**.
   - Updated module docstring to document OpenSees vs engineering sign mapping.

2. **Overlay display fix** (`src/fem/visualization.py`)
   - Updated `_display_node_force()` to apply i-end normalization via `normalize_i_end_force`.
   - j-end path continues using shared `normalize_end_force()`.

3. **Beam table fix** (`src/ui/components/beam_forces_table.py`)
   - i-end values now negate `My_i`, `Mz_i`, and `T_i`.
   - j-end values inherit corrected behavior from shared normalization.

4. **Column table fix** (`src/ui/components/column_forces_table.py`)
   - i-end values now negate `My_i`, `Mz_i`, and `T_i`.
   - j-end values inherit corrected behavior from shared normalization.

5. **Test updates**
   - `tests/test_force_normalization.py`
     - Updated moment/torsion j-end expectations to raw values.
     - Added `normalize_i_end_force()` coverage for moment/shear/axial behavior.
     - Updated negation-set tests for the new split constants.
   - `tests/test_column_forces_table.py`
     - Updated j-end My expectation to `-0.5 kNm` (raw j-end behavior).
     - Updated test description to reflect split convention.

### Verification Evidence

- Targeted tests:
  - `python -m pytest tests/test_force_normalization.py tests/test_column_forces_table.py -q`
  - Result: **36 passed**.
- Full suite gate:
  - `python -m pytest tests/ -x -q && python -c "print('full-suite-ok')"`
  - Result: printed `full-suite-ok` (full suite passed with `-x`).

### Diagnostics Status

- Clean diagnostics:
  - `src/fem/force_normalization.py`
  - `tests/test_force_normalization.py`
  - `tests/test_column_forces_table.py`
- Pre-existing basedpyright issues remain in:
  - `src/fem/visualization.py` (constant redefinition/type-annotation strictness)
  - `src/ui/components/beam_forces_table.py` (pandas typing strictness)
  - `src/ui/components/column_forces_table.py` (pandas typing strictness)
  - These were present outside Phase 8 scope and were not introduced by this fix.

### Next-Phase Actions

1. Run a manual UI check in Streamlit for a gravity-loaded beam and verify:
   - midspan `Mz > 0` (sagging), support `Mz < 0` (hogging).
2. Capture one regression screenshot set (plan/elevation + table) as Phase 8 evidence artifact.
3. Optional cleanup phase: address pre-existing basedpyright strict-typing errors in visualization/tables.
4. If all visual checks pass, proceed to commit/PR for this phase.
