# Session Handoff: Phase 8 (Moment Sign) + Phase 9 (Wind Loads)

## Project Location
```
C:\Users\daokh\Desktop\PrelimStruct v3-5\
```

## Branch
```
feature/v35-fem-lock-unlock-cleanup
```

---

## Summary

This session completed two phases:

1. **Phase 8**: Fixed moment sign convention — sagging moments now display as positive, hogging as negative (matching ETABS convention).
2. **Phase 9**: Enabled wind load cases (Wx+/Wx-/Wy+/Wy-) with centroid diaphragm master nodes, 4-direction wind application, manual + HK Code wind input UI, and a critical fix for gravity singularity.

**Final test result: 291 passed, 0 failed.**

---

## Phase 8: Moment Sign Convention (v3.5.1)

### Problem
Force diagrams showed inverted moments — sagging negative, hogging positive.

### Root Cause
`force_normalization.py` treated moments the same as shear for j-end negation. OpenSees `localForce` has **opposite** sign relationships:
- **Shear (Vy, Vz)**: i-end matches engineering, j-end is opposite → negate j-end
- **Moments (My, Mz, T)**: i-end is opposite to engineering, j-end matches → negate i-end

### Fix
- Split `NEGATED_J_END_TYPES` into `{"Vy", "Vz"}` (shear) and new `NEGATED_I_END_TYPES = {"My", "Mz", "T"}` (moments)
- Added `normalize_i_end_force()` function
- Updated `visualization.py:_display_node_force()` to apply i-end negation
- Updated beam/column force tables for i-end moment negation

### Files Modified
- `src/fem/force_normalization.py` — core fix
- `src/fem/visualization.py` — diagram display
- `src/ui/components/beam_forces_table.py` — table i-end
- `src/ui/components/column_forces_table.py` — table i-end
- `tests/test_force_normalization.py` — updated tests
- `tests/test_column_forces_table.py` — updated tests

---

## Phase 9: Wind Load Cases (Wx, Wy)

### Situation
Wind load infrastructure was 90% built but disabled (`apply_wind_loads=False`) because `WindEngine` had been removed. Three issues:
1. `project.wind_result` never populated → wind permanently disabled
2. Director bug: referenced non-existent `self.options.wind_load_pattern`
3. Master node = corner joint (`min(node_tags)`) → wrong torsion point

### Changes Made

| # | Change | File |
|---|--------|------|
| 1 | Extended `WindResult` with `base_shear_x`, `base_shear_y` | `data_models.py` |
| 2 | Centroid master nodes at 90000+ tag range | `model_builder.py` |
| 3 | `_compute_floor_shears()` signature → explicit `base_shear_kn` | `model_builder.py` |
| 4 | Fixed Director: 4-direction wind (Wx+/Wx-/Wy+/Wy-) | `director.py` |
| 5 | Synced legacy `build_fem_model()` path | `model_builder.py` |
| 6 | Wind input UI: Manual + HK Code Calculator modes | `fem_views.py` |
| 7 | New HK Code wind calculator | `wind_calculator.py` |
| 8 | Always apply diaphragms (reviewer fix) | `fem_engine.py` |

### Critical Post-Review Fix
The centroid master node (`restraints=[0, 0, 1, 1, 1, 0]`) caused a **singular matrix** for gravity load cases. The master node's Ux/Uy/Rz DOFs were free but not connected to any element or constraint when diaphragms were skipped for patterns 1-3.

**Fix**: Changed `fem_engine.py` to always apply `rigidDiaphragm` constraints for all load patterns (not just wind). Physically correct — real floor plates are rigid under all loads.

### New Files
- `src/fem/wind_calculator.py` — simplified HK Code wind calculation
- `tests/test_wind_calculator.py` — 5 tests
- `tests/test_diaphragm_master.py` — 5 tests
- `tests/verification/test_wind_equilibrium.py` — 2 integration tests

---

## Key Conventions (Accumulated from Phases 0-9)

| Topic | Convention |
|-------|-----------|
| vecxz (beams) | `(dy/L, -dx/L, 0)` for horizontal beams |
| vecxz (columns) | `(0, 1, 0)` for vertical columns |
| Force extraction | `ops.eleResponse(tag, 'localForce')` — NOT `ops.eleForce()` |
| Gravity load | `wy = -magnitude` (load in -local_y = downward) |
| Shear normalization | Negate j-end (Vy, Vz) |
| Moment normalization | Negate i-end (My, Mz, T) |
| Diaphragm master | Centroid node, tag 90000 + floor_level |
| Diaphragm constraint | Applied for ALL load patterns |
| Wind patterns | Wx+=4, Wx-=5, Wy+=6, Wy-=7 |
| Wind base shear | Separate `base_shear_x` and `base_shear_y` |

---

## Test Coverage

- 180 core unit tests
- 111 verification + integration tests
- **291 total, 0 failures**

---

## Remaining Actions

1. Visual verification in Streamlit: wind arrows, lateral displacement, force diagrams under Wx/Wy
2. Optional: UI smoke test for Manual ↔ HK Code Calculator switching
3. Git commit and tag as appropriate
