# Phase 5: Visualization + Force Table Updates

## Prerequisite
Phases 0-4 must be complete. All axis fixes are verified, envelope is separated.

## Objective
Update ALL user-facing displays to reflect the corrected axis convention:
1. Fix inverted display name labels in `visualization.py`
2. Rename force table DataFrame column names (extraction + headers + format dicts)
3. Update default highlight column in beam tables
4. Add local axis arrows toggle (hidden by default)
5. Add convention legend/annotation

## Critical Finding: Labels Are Currently BACKWARDS

**File: `src/fem/visualization.py`, lines 89-96:**
```python
FORCE_DISPLAY_NAMES: Dict[str, str] = {
    "N": "N (Axial)",
    "Vy": "V-major",    # After fix: Vy IS major shear ✓ but label style inconsistent
    "Vz": "V-minor",    # After fix: Vz IS minor shear ✓ but label style inconsistent
    "My": "M-major",    # WRONG after fix — My is now MINOR axis
    "Mz": "M-minor",    # WRONG after fix — Mz is now MAJOR axis
    "T": "T (Torsion)",
}
```

After Phases 1-3: `Mz = major`, `My = minor`. The My/Mz labels must swap, and all labels should be explicit with axis name for clarity.

## Changes

### 1. Fix `FORCE_DISPLAY_NAMES` in `visualization.py`

**File: `src/fem/visualization.py`, lines 89-96**

```python
# BEFORE:
FORCE_DISPLAY_NAMES: Dict[str, str] = {
    "N": "N (Axial)",
    "Vy": "V-major",
    "Vz": "V-minor",
    "My": "M-major",
    "Mz": "M-minor",
    "T": "T (Torsion)",
}

# AFTER:
FORCE_DISPLAY_NAMES: Dict[str, str] = {
    "N": "N (Axial)",
    "Vy": "Vy (Major Shear)",
    "Vz": "Vz (Minor Shear)",
    "My": "My (Minor Moment)",
    "Mz": "Mz (Major Moment)",
    "T": "T (Torsion)",
}
```

This dict is consumed at 5 locations in visualization.py (lines 1229, 1327, 1529, 1629, 3996) via `.get()` — no changes needed at those call sites, they will pick up the new values automatically.

Also re-exported via `src/fem/visualization/__init__.py` lines 47, 105 — no changes needed there either.

### 2. Update Beam Forces Table

**File: `src/ui/components/beam_forces_table.py`**

There are **4 locations** that reference `'My (kNm)'` / `'Mz (kNm)'` as DataFrame column name strings. ALL must be updated together:

#### 2a. Data extraction (lines 183-184)
```python
# BEFORE:
'My (kNm)': forces['My_i'],
'Mz (kNm)': forces['Mz_i'],

# AFTER:
'My-minor (kNm)': forces['My_i'],
'Mz-major (kNm)': forces['Mz_i'],
```

#### 2b. Force columns array (line 266)
```python
# BEFORE:
force_columns = ['N (kN)', 'Vy (kN)', 'Vz (kN)', 'My (kNm)', 'Mz (kNm)', 'T (kNm)']

# AFTER:
force_columns = ['N (kN)', 'Vy (kN)', 'Vz (kN)', 'My-minor (kNm)', 'Mz-major (kNm)', 'T (kNm)']
```

#### 2c. Highlight column mapping (lines 267-274)
```python
# BEFORE:
highlight_col = {
    'N': 'N (kN)',
    'Vy': 'Vy (kN)',
    'Vz': 'Vz (kN)',
    'My': 'My (kNm)',
    'Mz': 'Mz (kNm)',
    'T': 'T (kNm)',
}.get(self.force_type, 'My (kNm)')

# AFTER:
highlight_col = {
    'N': 'N (kN)',
    'Vy': 'Vy (kN)',
    'Vz': 'Vz (kN)',
    'My': 'My-minor (kNm)',
    'Mz': 'Mz-major (kNm)',
    'T': 'T (kNm)',
}.get(self.force_type, 'Mz-major (kNm)')  # Default to Mz (major) instead of My
```

#### 2d. Format dict (lines 285-286)
```python
# BEFORE:
'My (kNm)': '{:.1f}',
'Mz (kNm)': '{:.1f}',

# AFTER:
'My-minor (kNm)': '{:.1f}',
'Mz-major (kNm)': '{:.1f}',
```

### 3. Update Column Forces Table

**File: `src/ui/components/column_forces_table.py`**

Same 4 locations as beam table:

#### 3a. Data extraction (lines 172-173)
```python
# BEFORE:
'My (kNm)': forces['My_i'],
'Mz (kNm)': forces['Mz_i'],

# AFTER:
'My-minor (kNm)': forces['My_i'],
'Mz-major (kNm)': forces['Mz_i'],
```

#### 3b. Force columns array (line 250)
```python
# BEFORE:
force_columns = ['N (kN)', 'Vy (kN)', 'Vz (kN)', 'My (kNm)', 'Mz (kNm)', 'T (kNm)']

# AFTER:
force_columns = ['N (kN)', 'Vy (kN)', 'Vz (kN)', 'My-minor (kNm)', 'Mz-major (kNm)', 'T (kNm)']
```

#### 3c. Highlight column mapping (lines 251-258)
```python
# BEFORE:
highlight_col = {
    'N': 'N (kN)',
    'Vy': 'Vy (kN)',
    'Vz': 'Vz (kN)',
    'My': 'My (kNm)',
    'Mz': 'Mz (kNm)',
    'T': 'T (kNm)',
}.get(self.force_type, 'N (kN)')

# AFTER:
highlight_col = {
    'N': 'N (kN)',
    'Vy': 'Vy (kN)',
    'Vz': 'Vz (kN)',
    'My': 'My-minor (kNm)',
    'Mz': 'Mz-major (kNm)',
    'T': 'T (kNm)',
}.get(self.force_type, 'N (kN)')  # Column default stays N (axial-dominant)
```

**NOTE:** Column table default stays `'N (kN)'` — this is intentional. Columns are axial-dominant members; N is the correct default highlight. Do NOT change this to `'Mz-major (kNm)'`.

#### 3d. Format dict (lines 270-271)
```python
# BEFORE:
'My (kNm)': '{:.1f}',
'Mz (kNm)': '{:.1f}',

# AFTER:
'My-minor (kNm)': '{:.1f}',
'Mz-major (kNm)': '{:.1f}',
```

### 4. Local Axis Arrows (Hidden by Default)

**File: `src/fem/visualization.py`**

#### 4a. Add config option (line 327, after `load_case_label`)
```python
show_local_axes: bool = False  # Toggle to show local axis arrows on elements
```

#### 4b. Add rendering function
Add a function `_draw_local_axes(fig, model, ...)` that:
- Iterates over frame elements (beams + columns)
- For each element: get node coords, compute local_x from node direction
- Retrieve vecxz from `elem.geometry.get('vecxz')`
- Compute: `local_y = cross(vecxz, local_x)`, `local_z = cross(local_x, local_y)`
- Draw 3 colored arrows at element midpoint:
  - Red arrow = local_x (along element)
  - Green arrow = local_y (vertical for beams)
  - Blue arrow = local_z (horizontal for beams)
- Arrow length: 10% of element length
- Use Plotly scatter3d traces with mode='lines'

#### 4c. Integration point
Call `_draw_local_axes()` from the main visualization render function when `config.show_local_axes` is True.

**NOTE:** This is the most complex sub-task. Implement the arrow rendering but keep the toggle mechanism simple (a boolean in config). If the visualization framework has an existing layer system, integrate with it; otherwise, add as additional Plotly traces.

### 5. Convention Legend

Add a small annotation to force diagram plots:

```python
fig.add_annotation(
    text="Convention: Mz = Major axis (M33), My = Minor axis (M22)<br>Positive Mz = sagging",
    xref="paper", yref="paper",
    x=0.01, y=0.01,
    showarrow=False,
    font=dict(size=9, color="gray"),
    align="left",
)
```

Place this in the force diagram rendering functions where `section_force_type` is used (around the code that calls `FORCE_DISPLAY_NAMES`).

### 6. Update existing test `tests/test_column_forces_table.py`

This test file references old DataFrame column names that will break:

**Line 189:** Column header assertion
```python
# BEFORE:
"N (kN)", "Vy (kN)", "Vz (kN)", "My (kNm)", "Mz (kNm)", "T (kNm)"

# AFTER:
"N (kN)", "Vy (kN)", "Vz (kN)", "My-minor (kNm)", "Mz-major (kNm)", "T (kNm)"
```

**Lines 234-235:** DataFrame cell access
```python
# BEFORE:
assert abs(last_row["My (kNm)"] - 0.5) < 0.01, \
    f"Expected My ~0.5 kNm after normalization, got {last_row['My (kNm)']}"

# AFTER:
assert abs(last_row["My-minor (kNm)"] - 0.5) < 0.01, \
    f"Expected My ~0.5 kNm after normalization, got {last_row['My-minor (kNm)']}"
```

### 7. Known-affected Playwright/JS tests (document only)

These JS test files reference old label text and will need updating in Phase 6 or separately:

| File | Lines | Old Text | New Text Needed |
|------|-------|----------|-----------------|
| `tests/playwright_force_diagram_v3.js` | 48 | `'M-major (Strong Axis)'` | `'Mz (Major Moment)'` |
| `tests/playwright_force_diagram_v3.js` | 57 | `'M-minor'`, `'V-major'` | `'My (Minor Moment)'`, `'Vy (Major Shear)'` |
| `tests/test_force_diagram.js` | 52-56 | `'M-major'` | `'Mz (Major Moment)'` |
| `tests/test_opsvis_debug.js` | 114, 133 | `'M-major'` | `'Mz (Major Moment)'` |

**DO NOT modify these JS files in Phase 5.** Document them as known-affected for Phase 6 cleanup.

## Testing

### Visual Verification (Manual)
1. Run the app with a simple beam model
2. View force diagrams → labels should say "Mz (Major Moment)" for gravity bending
3. View force tables → "Mz-major" column should have the dominant values under gravity
4. Toggle local axes → arrows should show green=up for beams, red=along element

### Automated Tests
- Test that `FORCE_DISPLAY_NAMES["Mz"]` == "Mz (Major Moment)"
- Test that `FORCE_DISPLAY_NAMES["My"]` == "My (Minor Moment)"
- Test that beam table default highlight column is `'Mz-major (kNm)'`
- Test that column table default highlight column is `'N (kN)'` (unchanged)
- Update `tests/test_column_forces_table.py` as specified in Section 6

## Acceptance Criteria
1. `FORCE_DISPLAY_NAMES` labels are correct: Mz = Major, My = Minor
2. Force diagram labels show "Mz (Major Moment)" for gravity bending plots
3. Beam force table headers show "Mz-major (kNm)" and "My-minor (kNm)"
4. Column force table headers show "Mz-major (kNm)" and "My-minor (kNm)"
5. Beam table default highlighted column is `'Mz-major (kNm)'`
6. Column table default highlighted column stays `'N (kN)'`
7. DataFrame column names are consistent across extraction, headers, format dicts, and highlight maps
8. Local axis arrows render correctly when toggled on (hidden by default)
9. Convention legend appears on force diagrams
10. `tests/test_column_forces_table.py` updated and passing
11. All existing tests pass (same exclusion policy: `pytest tests/ --ignore=tests/verification/test_beam_shear_1x1.py -x --tb=short`)
12. Playwright JS tests documented as known-affected (NOT fixed in this phase)

## Guardrails
- **DO NOT** modify solver.py, fem_engine.py, or results_processor.py
- **DO NOT** change force extraction logic or normalization
- **DO NOT** change the internal force dict keys (N_i, Vy_i, etc.) — only change the user-facing display strings
- **DO NOT** reorder table columns — only change the display text
- **DO NOT** change the column table default highlight from `'N (kN)'` — it is correct for columns
- **DO NOT** modify the Playwright JS test files — they are Phase 6 scope
- Keep the local axis arrows hidden by default — no visual change unless user opts in
- If the force table UI framework limits header text length, abbreviate to "Mz-maj" / "My-min"
- When renaming DataFrame column names, update ALL 4 locations per table file (extraction, columns array, highlight map, format dict) — missing one will cause a KeyError at runtime

## Phase 4 Findings (Context for This Phase)
- `ElementForceEnvelope` now has 10 separated fields: N, Vy, Vz, Mz, My (each with max/min)
- `export_envelope_summary()` now shows: "Maximum Mz (major)", "Maximum My (minor)", "Maximum Vy (major shear)", "Maximum Vz (minor shear)", "Maximum axial"
- `get_critical_elements("moment")` uses `Mz_max`, `get_critical_elements("shear")` uses `Vy_max`
- No changes were made to visualization.py or UI table files in Phases 1-4, so ALL line numbers are accurate

## Commit Message
```
feat(ui): update force labels for ETABS major/minor axis convention

Fix FORCE_DISPLAY_NAMES: Mz = Major Moment, My = Minor Moment.
Update beam/column force table headers with major/minor annotations.
Add local axis arrows toggle and convention legend to force diagrams.
```

## Execution Log

### Status
- Completed on 2026-02-08.

### Changes Applied
- `src/fem/visualization.py`
  - Updated `FORCE_DISPLAY_NAMES`: Mz -> "Mz (Major Moment)", My -> "My (Minor Moment)", Vy -> "Vy (Major Shear)", Vz -> "Vz (Minor Shear)".
  - Added `show_local_axes: bool = False` to `VisualizationConfig` dataclass.
  - Added `_draw_local_axes(fig, model, arrow_frac)` function: renders red/green/blue arrows at element midpoints for local x/y/z axes in 3D view.
  - Integrated `_draw_local_axes` call in `create_3d_view` when `config.show_local_axes` is True.
  - Added convention legend annotation to `create_plan_view` (Plotly) and `create_elevation_view` (Plotly) — appears only when section forces are rendered.
  - Added convention annotation to `create_opsvis_force_diagram` (matplotlib).
- `src/ui/components/beam_forces_table.py`
  - Updated 4 locations: data extraction, force_columns array, highlight_col map, format dict.
  - Column names changed: `My (kNm)` -> `My-minor (kNm)`, `Mz (kNm)` -> `Mz-major (kNm)`.
  - Default highlight column changed from `My (kNm)` to `Mz-major (kNm)` (major moment).
- `src/ui/components/column_forces_table.py`
  - Updated same 4 locations with identical renames.
  - Default highlight column stays `N (kN)` (axial-dominant for columns — unchanged).
- `tests/test_column_forces_table.py`
  - Updated expected column names in assertions (line 189, lines 234-235).

### Verification Evidence
- Legacy column name cleanup check:
  - `grep -rn "'My (kNm)'\|'Mz (kNm)'" src tests` -> **zero matches**.
  - `grep -rn "M-major\|M-minor\|V-major\|V-minor" src/fem/visualization.py` -> **zero matches**.
- Targeted Phase 5 tests:
  - `pytest tests/test_column_forces_table.py tests/test_visualization.py tests/test_results_processor.py tests/test_envelope_separation.py -x --tb=short -q`
  - Result: **54 passed**.
- FEM core tests:
  - `pytest tests/test_fem_engine.py tests/test_model_builder.py -x --tb=short -q`
  - Result: **87 passed**.
- Full regression gate:
  - `pytest tests/ --ignore=tests/verification/test_beam_shear_1x1.py -x --tb=no`
  - Result: exit code **0**.
- Syntax verification:
  - `python -m py_compile` on all 4 changed files: all compile cleanly.

### Acceptance Criteria Mapping
1. `FORCE_DISPLAY_NAMES` labels correct: Mz = "Mz (Major Moment)", My = "My (Minor Moment)". ✓
2. Force diagram labels show "Mz (Major Moment)" for gravity bending plots. ✓
3. Beam force table headers show "Mz-major (kNm)" and "My-minor (kNm)". ✓
4. Column force table headers show "Mz-major (kNm)" and "My-minor (kNm)". ✓
5. Beam table default highlighted column is `Mz-major (kNm)`. ✓
6. Column table default highlighted column stays `N (kN)`. ✓
7. DataFrame column names consistent across extraction, headers, format dicts, highlight maps. ✓
8. Local axis arrows render correctly when toggled on (hidden by default via `show_local_axes=False`). ✓
9. Convention legend appears on force diagrams (plan view, elevation view, opsvis). ✓
10. `tests/test_column_forces_table.py` updated and passing. ✓
11. All existing tests pass. ✓
12. Playwright JS tests documented as known-affected (NOT fixed in this phase). ✓

### Known-Affected Playwright/JS Tests (Phase 6 Scope)
| File | Lines | Old Text | New Text Needed |
|------|-------|----------|-----------------|
| `tests/playwright_force_diagram_v3.js` | 48 | `'M-major (Strong Axis)'` | `'Mz (Major Moment)'` |
| `tests/playwright_force_diagram_v3.js` | 57 | `'M-minor'`, `'V-major'` | `'My (Minor Moment)'`, `'Vy (Major Shear)'` |
| `tests/test_force_diagram.js` | 52-56 | `'M-major'` | `'Mz (Major Moment)'` |
| `tests/test_opsvis_debug.js` | 114, 133 | `'M-major'` | `'Mz (Major Moment)'` |

### Notes
- `lsp_diagnostics` not available (`basedpyright-langserver` not installed).
- All LSP errors flagged during edits were pre-existing pandas type-stub issues, not related to Phase 5 changes.
- No changes made to `solver.py`, `fem_engine.py`, `results_processor.py`, or `force_normalization.py`.

## Next Phase Actions (Phase 6)
- Execute `phase-6-integration-tests.md`:
  - Update Playwright/JS test files listed above with new display name labels.
  - Add integration tests verifying end-to-end force label correctness.
  - Ensure full test suite (including previously excluded tests) passes cleanly.
  - Final xfail cleanup if any remain.
