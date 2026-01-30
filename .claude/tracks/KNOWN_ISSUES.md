# Known Issues & Technical Debt

> **Last Updated:** 2026-01-30
> **Source:** Discovered during regression fixes and task completion

---

## 0. Failing Benchmark Tests (HIGH PRIORITY)

### 0.1 FEM Constraint Handler Issue
**Files:** `tests/test_benchmark_validation.py`
**Tests:**
| Test | Status |
|------|--------|
| `test_simple_10_story_reactions` | FAILING |
| `test_reactions_non_zero[Simple_10Story_Frame]` | FAILING |
| `test_reactions_non_zero[Medium_20Story_Core]` | FAILING |

**Root Cause:** OpenSeesPy `PlainHandler` warns about non-identity constraint matrices for rigid diaphragm nodes, causing reactions to be 0.

**Fix:** Update `build_openseespy_model()` in `src/fem/solver.py` to use `Transformation` constraint handler:
```python
# Current (problematic):
ops.constraints('Plain')

# Fix:
ops.constraints('Transformation')
```

**Location:** `src/fem/solver.py` - look for `ops.constraints('Plain')`

**Priority:** HIGH - These are real FEM analysis issues affecting reaction calculations
**Track:** Backlog (or create dedicated fix task)

---

## 1. Type Annotation Errors

### 1.1 WallPanel base_point Mismatch
**File:** `src/fem/model_builder.py`
**Lines:** 683-778, 796-890
**Issue:** `_extract_wall_panels()` passes 3-tuple `(x, y, z)` but `WallPanel.__init__` expects 2-tuple `(x, y)`
**Impact:** LSP error only - code works at runtime
**Fix:** Either update WallPanel to accept 3-tuple or slice the tuple `(x, y, z)[:2]`
**Priority:** Low

### 1.2 app.py Type Mismatches
**File:** `app.py`
**Issues:**
| Line | Error | Fix |
|------|-------|-----|
| 1301-1500 | `length_x/length_y` type `float | None` vs `float` | Add null check before passing |
| 1586 | `lateral_system` attribute unknown | Update LateralInput or check attribute existence |
| 1688 | `suggested_omit_columns` type mismatch | Convert list to tuple |
| 1923 | `selected_slab_type` undefined | Define before use |
| 1970-1986 | Attribute access on None | Add null checks |
| 2091 | `st.components` unknown | Update Streamlit types or ignore |

**Priority:** Medium

---

## 2. Deprecated Code

### 2.1 analysis_summary.py
**File:** `src/fem/analysis_summary.py`
**Status:** No longer imported after Task 16.2
**Function:** `build_fem_vs_simplified_comparison`
**Action:** Can be deleted or deprecated
**Priority:** Low (cleanup)

### 2.2 Moment Frame Tests
**File:** `tests/test_moment_frame.py`
**Status:** Entire module skipped with `pytest.mark.skip`
**Reason:** Uses deprecated API:
- `LateralInput.core_dim_x/y/thickness` (removed)
- `ColumnEngine.check_combined_load` (removed)
- `WindEngine.get_required_moment_of_inertia` (simplified workflow)
**Action:** Write FEM-based replacement tests
**Priority:** Medium (Track 8)

---

## 3. Missing Functionality

### 3.1 ColumnEngine.check_combined_load
**File:** `src/engines/column_engine.py`, `app.py:962`
**Issue:** Method was removed but still referenced in app.py
**Impact:** Will raise AttributeError if that code path is executed
**Fix:** Either implement FEM-based version or remove the call
**Priority:** High (potential runtime error)

---

## 4. Test Suite Status

| Metric | Value |
|--------|-------|
| Total tests | 1128 |
| Passing | 1113 |
| Skipped | 12 |
| Failed | 3 |

**Failed tests:** Benchmark validation (FEM constraint handler - see Issue 0.1)
**Skipped tests:** `test_moment_frame.py` (deprecated API) + integration marks

---

## Resolution Tracking

| Issue | Track | Status | Priority |
|-------|-------|--------|----------|
| **FEM Constraint Handler** | Backlog | **PENDING** | **HIGH** |
| WallPanel base_point | Backlog | Pending | Low |
| app.py type errors | Backlog | Pending | Medium |
| analysis_summary.py cleanup | Backlog | Pending | Low |
| Moment frame tests | Track 8 | Pending | Medium |
| check_combined_load | Backlog | Pending | High |

---

## Fix Instructions for Issue 0.1

```powershell
# 1. Find the constraint handler
Select-String -Path src/fem/solver.py -Pattern "constraints"

# 2. Change from Plain to Transformation
# Before: ops.constraints('Plain')
# After:  ops.constraints('Transformation')

# 3. Run benchmark tests to verify
pytest tests/test_benchmark_validation.py -v
```

---

*Updated by Orchestrator: 2026-01-30*
