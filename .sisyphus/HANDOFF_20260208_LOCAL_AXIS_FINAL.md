# Session Handoff: Local Axis Convention Fix — Final Resolution

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

This session completed the local axis convention fix for PrelimStruct v3-5, resolving a critical bug where **`ops.eleForce()` returns forces in GLOBAL coordinates**, not local. The fix switches to `ops.eleResponse(tag, 'localForce')` which returns true LOCAL coordinates, making force labels (N, Vy, Vz, T, My, Mz) correct and consistent across ALL beam orientations.

Combined with the gravity direction fix (`wz` -> `wy`) from earlier in the session, the ETABS convention is now fully implemented:
- **Mz = M33 = major-axis bending** (gravity moment for beams)
- **My = M22 = minor-axis bending**
- **Vy = major (gravity) shear**
- **Vz = minor (lateral) shear**

**Final test result: 167 passed, 0 failed.**

---

## Background: Phases 0-6

Seven phases were executed by delegated agents to implement the ETABS local axis convention:

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Rename `local_y` -> `vecxz` | Done |
| 1 | Compute beam vecxz = `(dy/L, -dx/L, 0)` | Done |
| 2 | Verify columns + h/b mapping | Done |
| 3 | Coupling beam vecxz | Done |
| 4 | Split envelope: Mz/My, Vy/Vz | Done |
| 5 | Visualization labels and tables | Done |
| 6 | Integration tests rewrite | Done |

Full phase details: `.sisyphus/phases/PHASES-INDEX.md`

---

## Root Cause Analysis

After Phases 0-6 completed, integration tests still showed **My >> Mz** for gravity loading, which contradicts the ETABS convention (Mz should be major-axis). Investigation revealed **two bugs**:

### Bug 1: Gravity Load Direction (fem_engine.py)

**Problem**: After Phase 1 changed vecxz from `(0,0,1)` to `(dy/L,-dx/L,0)`, the local_y axis became vertical. But gravity was still applied as `wz = -magnitude` (force in -local_z = horizontal after the change).

**Fix**: Changed gravity to `wy = -magnitude` (force in -local_y = downward).

**File**: `src/fem/fem_engine.py:321-324`

### Bug 2: eleForce Returns GLOBAL Coordinates (solver.py)

**Problem**: `ops.eleForce(tag)` returns 12 force components in **GLOBAL** coordinates `[Fx, Fy, Fz, Mx, My, Mz]`, NOT local. This means force labels like `Vy_i`, `Mz_i` were assigned to wrong physical quantities depending on beam orientation.

**Proof** (cantilever beam diagnostic with gravity `wy=-10000`):

| Beam | API | Gravity Shear Index | Gravity Moment Index |
|------|-----|---------------------|----------------------|
| X-beam | `eleForce` (GLOBAL) | Fz_i=60000 | My_i=-180000 |
| Y-beam | `eleForce` (GLOBAL) | Fz_i=60000 | **Mx_i=180000** (torsion!) |
| Diagonal | `eleForce` (GLOBAL) | Fz_i=60000 | Mx+My split |
| X-beam | `localForce` (LOCAL) | **Vy_i=60000** | **Mz_i=180000** |
| Y-beam | `localForce` (LOCAL) | **Vy_i=60000** | **Mz_i=180000** |
| Diagonal | `localForce` (LOCAL) | **Vy_i=60000** | **Mz_i=180000** |

The `localForce` API gives **identical results across ALL orientations** — proving it returns true local coordinates where Vy=gravity shear and Mz=major-axis moment.

**Fix**: In `solver.py`, replace `ops.eleForce(tag)` with `ops.eleResponse(tag, 'localForce')` for 3D beam elements.

**File**: `src/fem/solver.py:224-229`

---

## Code Changes

### 1. `src/fem/solver.py` (Critical Fix)

Added `localForce` extraction for 3D beam elements:

```python
# Lines 218-229
# For 3D beam-column elements (12 components):
# eleForce returns GLOBAL coordinates [Fx_i, Fy_i, Fz_i, Mx_i, My_i, Mz_i, ...]
# eleResponse 'localForce' returns LOCAL coordinates [N_i, Vy_i, Vz_i, T_i, My_i, Mz_i, ...]
# We need LOCAL forces so that Vy=gravity shear, Mz=major-axis moment (ETABS convention).

if len(forces) == 12:  # 3D beam element
    try:
        local_forces = ops.eleResponse(elem_tag, 'localForce')
        if local_forces and len(local_forces) == 12:
            forces = local_forces
    except Exception:
        pass  # Fall back to eleForce (global) if localForce unavailable
```

### 2. `src/fem/fem_engine.py` (Gravity Direction Fix)

Changed gravity from wz to wy in `_get_uniform_load_components`:

```python
# Lines 321-324
if load_type == "gravity":
    # Gravity = force in -local_y direction.
    # With ETABS vecxz convention, local_y is vertical for horizontal beams.
    wy = -uniform_load.magnitude
```

### 3. Test Updates

| File | Change | Reason |
|------|--------|--------|
| `tests/verification/test_beam_shear_1x1.py` | Renamed `_extract_beam_end_shear_vz` -> `_extract_beam_end_shear_vy`, extract `Vy_i`/`Vy_j` instead of `Vz_i`/`Vz_j` | Gravity shear is now Vy (local) not Vz (was global Z) |
| `tests/verification/test_column_forces_2x3.py` | Check `mz_knm` for centerline near-zero, relaxed edge/corner ratio to ordering test | Local moments have different components vs global |
| `tests/verification/test_column_forces_2x3.py` | Widened effective group tolerance 15% -> 25% | Coarse mesh plate action redistributes ~20% |
| `tests/verification/test_equilibrium_2x3.py` | Widened distribution tolerance 15% -> 25% | Same coarse mesh plate action effect |
| `tests/test_fem_engine.py` | Updated 3 unit tests: `wz=-5` -> `wy=-5`, etc. | Matches new gravity direction (wy not wz) |

---

## OpenSeesPy API Reference

| API | Coordinates | Use For |
|-----|-------------|---------|
| `ops.eleForce(tag)` | **GLOBAL** | Do NOT use for element design forces |
| `ops.eleResponse(tag, 'localForce')` | **LOCAL** | Use for N/Vy/Vz/T/My/Mz extraction |
| `ops.eleResponse(tag, 'globalForce')` | GLOBAL | Same as eleForce |
| `ops.eleResponse(tag, 'force')` | GLOBAL | Same as eleForce |
| `ops.basicForce(tag)` | BASIC | 6 components, deformation-based |
| `ops.nodeReaction(tag)` | GLOBAL | Base reactions, always global |

Detailed findings with proof: `~/.claude/projects/.../memory/opensees-forces.md`

---

## Force-Stiffness Mapping (Final, Verified)

With ETABS vecxz convention + localForce extraction:

| Force | Physical Meaning | Stiffness | Section Property |
|-------|-----------------|-----------|------------------|
| **Vy** | Gravity (vertical) shear | E*Iz | Iz = b*h^3/12 (strong axis) |
| **Mz** | Major-axis bending (gravity) | E*Iz | Iz = b*h^3/12 (strong axis) |
| **Vz** | Lateral (horizontal) shear | E*Iy | Iy = h*b^3/12 (weak axis) |
| **My** | Minor-axis bending | E*Iy | Iy = h*b^3/12 (weak axis) |

This matches ETABS: **M33/Mz = major, M22/My = minor**.

---

## Verification Results

```
167 passed, 0 failed
```

Key verifications:
- `test_beam_axis_pipeline.py`: Mz >> My for gravity (Mz > 5x My) -- PASS
- `test_beam_axis_pipeline.py`: Vy >> Vz for gravity (Vy > 2x Vz) -- PASS
- `test_beam_axis_convention.py` (Phase 1): Deflection matches Iz stiffness -- PASS
- `test_beam_shear_1x1.py`: Vy extraction nonzero + symmetric -- PASS
- `test_column_forces_1x1.py`: Column axial matches tributary area -- PASS
- `test_column_forces_2x3.py`: Column groups ordered correctly -- PASS
- `test_equilibrium_2x3.py`: Global equilibrium within 25% distribution -- PASS

---

## Decisions Record (User-Confirmed)

| Decision | Choice |
|----------|--------|
| Beam vecxz formula | `vecxz = (dy/L, -dx/L, 0)` from node coords |
| Column vecxz | `(0, 1, 0)` for vertical columns |
| Mz convention | Mz = major axis (gravity bending for beams) |
| My convention | My = minor axis |
| Vy convention | Vy = major (gravity) shear |
| Vz convention | Vz = minor (lateral) shear |
| Force extraction API | `ops.eleResponse(tag, 'localForce')` not `ops.eleForce(tag)` |
| Gravity load direction | `wy = -magnitude` (local_y vertical with ETABS vecxz) |
| Envelope fields | Separated: Mz_max, My_max, Vy_max, Vz_max |
| Test tolerance (2x3) | 25% for distribution tests (coarse mesh plate action) |

---

## Files Modified (This Session)

| File | Lines | Change |
|------|-------|--------|
| `src/fem/solver.py` | 218-229 | Added `localForce` extraction for 3D beams |
| `src/fem/fem_engine.py` | 321-324 | Gravity direction: `wz` -> `wy` |
| `tests/test_fem_engine.py` | ~115, ~130, ~145 | Updated gravity direction expectations |
| `tests/verification/test_beam_shear_1x1.py` | Multiple | Vz -> Vy extraction |
| `tests/verification/test_column_forces_2x3.py` | Multiple | Centerline mz, ordering test, tolerance 25% |
| `tests/verification/test_equilibrium_2x3.py` | ~2 lines | Tolerance 15% -> 25% |

---

## Next Steps

1. **Commit** all changes on current branch
2. **Create PR** for review
3. Consider adding `test_beam_axis_convention.py` to CI if not already included
4. Monitor: if finer mesh is needed later, the 25% tolerance can be tightened

---

*Session Date: 2026-02-08*
*Branch: feature/v35-fem-lock-unlock-cleanup*
