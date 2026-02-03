# Force Diagram Bug - Handoff Document

## Date: 2026-02-03

## Summary
Force diagrams (Mz moment, Vy shear, N axial) are **NOT rendering** in the FEM visualization views despite the UI controls being correctly wired. The analysis runs successfully, but the force diagram overlays don't appear on Plan View or Elevation View.

---

## Current State

### What Works
- FEM Analysis runs successfully (green "Analysis Successful" banner)
- Plan View, Elevation View, 3D View all render structural geometry correctly
- Display Options expander opens and force type radio buttons can be selected
- Analysis results are stored in `st.session_state["fem_preview_analysis_result"]`
- Lock/Unlock functionality works

### What Doesn't Work
- **Force diagrams don't render** - No red moment/shear curves appear on beams
- **No numerical annotations** - Values should appear at 0.0L, 0.5L, 1.0L positions
- This affects both Plan View and Elevation View

---

## Root Cause Investigation (Incomplete)

### Hypothesis: `element_forces` is empty after analysis

The rendering logic in `visualization.py` line 2094:
```python
if config.section_force_type and analysis_result:
    forces = ResultsProcessor.extract_section_forces(...)
```

For force diagrams to render, BOTH conditions must be true:
1. `config.section_force_type` must be set (e.g., "Mz") ✅ Confirmed working
2. `analysis_result` must exist AND have `element_forces` populated ❓ **NEEDS VERIFICATION**

### Debug Code Added (TEMPORARY - REMOVE LATER)

**File: `src/fem/visualization.py`** (around line 2094)
```python
_logger.warning(f"[FORCE_DIAG_ELEV] force_type={config.section_force_type}")
_logger.warning(f"[FORCE_DIAG_ELEV] element_forces_count={len(getattr(analysis_result, 'element_forces', {}))}")
```

**File: `src/ui/views/fem_views.py`** (around line 475)
```python
st.caption(f"[DEBUG] force_code={force_code}, has_results={has_results}, element_forces={ef_count}")
```

---

## Key Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `src/fem/visualization.py` | Force diagram rendering | 669-802 (elevation), 805-920 (plan), 2094-2121 (call site) |
| `src/fem/results_processor.py` | Extract section forces | 507-620 (`extract_section_forces`) |
| `src/fem/solver.py` | Populate element_forces | 195-237 (force extraction loop) |
| `src/ui/views/fem_views.py` | UI integration | 531-540 (elevation call), 461-467 (plan call) |
| `app.py` | Main entry | 1850-1854 (render_unified_fem_views call) |

---

## Data Flow

```
1. User clicks "Run FEM Analysis"
   └─> fem_views.py line 335: result = analyze_model(model)
   
2. Solver extracts forces
   └─> solver.py line 196-237: result.element_forces[elem_tag] = {...}
   
3. Result stored in session state
   └─> fem_views.py line 342: st.session_state["fem_preview_analysis_result"] = result
   
4. Page reruns, app.py calls render_unified_fem_views()
   └─> app.py line 1852: analysis_result=st.session_state.get('fem_preview_analysis_result')
   
5. Elevation view created with analysis_result
   └─> fem_views.py line 539: analysis_result=analysis_result
   
6. visualization.py checks and renders
   └─> line 2094: if config.section_force_type and analysis_result:
   └─> line 2097-2101: forces = ResultsProcessor.extract_section_forces(...)
   └─> line 2115-2121: render_section_forces(...)
```

---

## Likely Issue Points

### 1. Solver not populating `element_forces` (MOST LIKELY)
- `solver.py` line 235-237 has `try/except pass` that silently swallows errors
- `ops.eleForce(elem_tag)` might be failing for certain element types

### 2. Force extraction returning empty
- `results_processor.py` line 565: Returns empty if `result.element_forces` is empty
- Line 575-584: Filters only 2-node beam elements

### 3. Session state timing issue
- The result might be stored but not properly retrieved on rerun
- `has_results` check at line 286 might be failing

---

## CAUTION FOR PROMETHEUS

### Architecture Decisions to Preserve
1. **FEM-only architecture** (v3.5) - No simplified calculation engines
2. **HK Code 2013 compliance** - All calculations must reference clause numbers
3. **OpenSeesPy integration** - Using 3D beam-column elements with 12 DOF
4. **Session state pattern** - Analysis results cached in `st.session_state`

### Critical Files - Handle With Care
1. `src/fem/solver.py` - The `try/except pass` on line 235-237 hides errors. Consider adding logging.
2. `src/fem/results_processor.py` - The `SectionForcesData` dataclass must match visualization expectations
3. `src/fem/visualization.py` - Large file (2800+ lines). Force diagram code is in `render_section_forces()` and `render_section_forces_plan()`

### Known Issues
1. **OpenSeesPy standalone tests hang** - `ops.analyze(1)` hangs outside Streamlit but works inside
2. **LSP errors are false positives** - openseespy, plotly, opsvis don't have type stubs
3. **Wind loads disabled** - `apply_wind_loads` defaults to False because WindEngine was removed in v3.5

### Test Files Created (Can Delete)
- `test_force_diagrams.js` - Playwright test for force diagrams
- `test_debug_forces.js` - Debug version with console output
- `diagnostic_element_forces.py` - Python diagnostic (has import error)
- `test_screenshots/force_diagrams/` - Screenshot evidence

### Hand Calculation Reference (For Verification)
When force diagrams work, verify against:
- **Beam**: 300x600mm, 6m span, edge beam
- **LC1 (1.4G+1.6Q)**: w=41.49 kN/m
- **Expected M_max** (simply-supported): wL²/8 = 186.71 kNm
- **Expected V_max**: wL/2 = 124.47 kN
- Continuous beam interior moment ≈ wL²/10 = 149.36 kNm

---

## Recommended Next Steps

1. **Verify `element_forces` population**
   - Add logging to `solver.py` line 196-237 (remove try/except pass)
   - Check what `ops.eleForce()` returns for each element type

2. **Check session state**
   - Log `len(analysis_result.element_forces)` after analysis completes
   - Verify the same object is retrieved after `st.rerun()`

3. **Test extraction**
   - Call `ResultsProcessor.extract_section_forces()` directly with a mock result
   - Verify `SectionForcesData.elements` is populated

4. **Simplify for debugging**
   - Create minimal 1-bay, 1-floor model
   - Hardcode known forces to verify rendering code works

---

## Git Status
- Debug code added to `visualization.py` and `fem_views.py` (REMOVE AFTER FIX)
- Test scripts added (can delete)
- No core functionality changes made
