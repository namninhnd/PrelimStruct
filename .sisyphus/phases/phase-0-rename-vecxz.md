# Phase 0: Rename `local_y` → `vecxz` (Pure Refactor)

## Objective
Rename the misleading geometry dict key `"local_y"` to `"vecxz"` across the entire codebase. This variable is NOT the local y-axis — it is the vecxz vector passed to OpenSeesPy's `geomTransf('Linear', tag, *vecxz)` to define the local x-z plane.

## Background
- In OpenSeesPy, `geomTransf('Linear', tag, *vecxz)` takes a vector in the local x-z plane
- OpenSees computes: `local_y = vecxz × local_x`, then `local_z = local_x × local_y`
- The codebase stores this vector as `"local_y"` in element geometry dicts, which is confusing
- This rename is a prerequisite for all subsequent phases

## Scope: PURE RENAME ONLY
- Change the dict key from `"local_y"` to `"vecxz"`
- Change the variable name from `vector_y` to `vecxz` in fem_engine.py
- Update test assertions that reference `"local_y"`
- **DO NOT** change any vector values — all `(0.0, 0.0, 1.0)` and `(0.0, 1.0, 0.0)` stay exactly as-is
- **DO NOT** change any functional behavior

## Files to Modify

### 1. `src/fem/builders/beam_builder.py`

**Line 166** — Default geometry for beams:
```python
# BEFORE:
geom_base = geometry_override if geometry_override else {"local_y": (0.0, 0.0, 1.0)}
# AFTER:
geom_base = geometry_override if geometry_override else {"vecxz": (0.0, 0.0, 1.0)}
```

**Line 575** — Coupling beam geometry override:
```python
# BEFORE:
geometry_override={"local_y": (0.0, 0.0, 1.0), "coupling_beam": True},
# AFTER:
geometry_override={"vecxz": (0.0, 0.0, 1.0), "coupling_beam": True},
```

### 2. `src/fem/builders/column_builder.py`

**Line 126** — Column geometry (subdivided path):
```python
# BEFORE:
geom: Dict[str, Any] = {"local_y": (0.0, 1.0, 0.0)}
# AFTER:
geom: Dict[str, Any] = {"vecxz": (0.0, 1.0, 0.0)}
```

**Line 150** — Column geometry (non-subdivided path):
```python
# BEFORE:
geometry={"local_y": (0.0, 1.0, 0.0)},
# AFTER:
geometry={"vecxz": (0.0, 1.0, 0.0)},
```

### 3. `src/fem/model_builder.py`

**Line 1136** — Beam creation in model_builder:
```python
# BEFORE:
"local_y": (0.0, 0.0, 1.0),
# AFTER:
"vecxz": (0.0, 0.0, 1.0),
```

**Line 1291** — Column creation in model_builder:
```python
# BEFORE:
"local_y": (0.0, 1.0, 0.0),
# AFTER:
"vecxz": (0.0, 1.0, 0.0),
```

**Line 1853** — Coupling beam creation in model_builder:
```python
# BEFORE:
"local_y": (0.0, 0.0, 1.0),
# AFTER:
"vecxz": (0.0, 0.0, 1.0),
```

### 4. `src/fem/fem_engine.py`

Three identical blocks at **lines 424, 461, 501**. Each one:
```python
# BEFORE:
vector_y = elem.geometry.get('local_y', (0.0, 0.0, 1.0))
# ...
ops.geomTransf('Linear', geom_transf_tag, *vector_y)

# AFTER:
vecxz = elem.geometry.get('vecxz', (0.0, 0.0, 1.0))
# ...
ops.geomTransf('Linear', geom_transf_tag, *vecxz)
```

Exact locations:
- **Line 424**: `ELASTIC_BEAM` element block
- **Line 461**: `BEAM_COLUMN` element block
- **Line 501**: `SHELL` / `COUPLING_BEAM` element block

### 5. Test Files

**`tests/test_column_subdivision.py`**
- **Line 243**: Rename test function `test_local_y_is_vertical` → `test_vecxz_for_vertical_columns`
- **Line 244**: Update docstring from "local_y" to "vecxz"
- **Line 262**: Change `element.geometry.get("local_y")` → `element.geometry.get("vecxz")`
- **Line 263**: Change assertion to check `"vecxz"` key

**`tests/test_fem_engine.py`**
- **Line 788**: Change `geometry={"local_y": (0.0, 1.0, 0.0)}` → `geometry={"vecxz": (0.0, 1.0, 0.0)}`

**`tests/verification/test_beam_shear_1x1.py`**
- **Lines 101-102**: Update comments that reference `local_y=(0,0,1)` to say `vecxz=(0,0,1)`

**`tests/verification/test_column_forces_1x1.py`**
- **Line 241**: Change `"local_y": (0, 1, 0)` → `"vecxz": (0, 1, 0)`

## Acceptance Criteria
1. `grep -r "local_y" src/ tests/` returns **zero** matches (except in comments explaining the old name, if any)
2. All existing tests pass with **no failures** — run `pytest tests/ -x --tb=short`
3. No functional behavior changes — the FEM model produces identical results
4. The variable name `vector_y` no longer exists in fem_engine.py

## Guardrails
- **DO NOT** change any tuple values: `(0.0, 0.0, 1.0)` and `(0.0, 1.0, 0.0)` must remain unchanged
- **DO NOT** modify force_normalization.py, solver.py, results_processor.py, or visualization.py
- **DO NOT** add any new logic, imports, or functions
- If any test fails after the rename, it means you missed a reference — find and rename it, don't change logic

## Commit Message
```
refactor(fem): rename misleading 'local_y' key to 'vecxz'

The geometry dict key 'local_y' was actually the vecxz vector passed
to OpenSeesPy geomTransf, not the local y-axis. Rename for clarity
before the axis convention fix.
```

## Execution Log

### Status
- Completed on 2026-02-08.

### Changes Applied
- `src/fem/builders/beam_builder.py`
  - Renamed default geometry key and coupling-beam override key: `"local_y"` -> `"vecxz"`.
- `src/fem/builders/column_builder.py`
  - Renamed both subdivided and non-subdivided column geometry keys: `"local_y"` -> `"vecxz"`.
- `src/fem/model_builder.py`
  - Renamed beam, column, and coupling-beam geometry keys: `"local_y"` -> `"vecxz"`.
- `src/fem/fem_engine.py`
  - Renamed local variable `vector_y` -> `vecxz` in all three element build blocks.
  - Updated geometry lookup key from `"local_y"` to `"vecxz"`.
- `tests/test_column_subdivision.py`
  - Renamed test `test_local_y_is_vertical` -> `test_vecxz_for_vertical_columns`.
  - Updated docstring and assertions to use `vecxz`.
- `tests/test_fem_engine.py`
  - Updated test element geometry key to `"vecxz"`.
- `tests/verification/test_beam_shear_1x1.py`
  - Updated explanatory comments to use `vecxz` naming.
- `tests/verification/test_column_forces_1x1.py`
  - Updated geometry key to `"vecxz"`.

### Verification Evidence
- `grep "local_y" src` -> zero matches.
- `grep "local_y" tests` -> zero matches.
- `grep "vector_y" src/fem/fem_engine.py` -> zero matches.
- Focused regression run:
  - `pytest tests/test_column_subdivision.py tests/test_fem_engine.py tests/verification/test_beam_shear_1x1.py tests/verification/test_column_forces_1x1.py -x --tb=short`
  - Result: **74 passed**.
- Full suite gate command:
  - `pytest tests/ -x --tb=short`
  - Result: exit code **0**.
- Syntax/build sanity:
  - `python -m compileall src tests`
  - Result: completed successfully.

### Notes
- `lsp_diagnostics` could not be executed in this environment because `basedpyright-langserver` is not installed on PATH.
- No vector tuple values were changed; all existing `(0.0, 0.0, 1.0)` and `(0.0, 1.0, 0.0)` values remain unchanged.

## Next Phase Actions (Phase 1)
- Implement beam-direction-based vecxz computation for horizontal beams:
  - `vecxz = (dy / length_xy, -dx / length_xy, 0.0)`.
- Apply the same beam vecxz logic in both:
  - `src/fem/builders/beam_builder.py`
  - `src/fem/model_builder.py`
- Add/execute hand-calculation verification tests per `phase-1-beam-vecxz-fix.md`:
  - Mz midspan (`wL^2/8`), support shear (`wL/2`), deflection check against `Iz`, and sign convention check.
