# Known Issues & Technical Debt

> **Last Updated:** 2026-01-30
> **Source:** Discovered during regression fixes and task completion

---

## 0. Failing Benchmark Tests (HIGH PRIORITY)

### 0.1 FEM Reaction Extraction Issue
**Files:** `tests/test_benchmark_validation.py`
**Tests:**
| Test | Status |
|------|--------|
| `test_simple_10_story_reactions` | FAILING |
| `test_reactions_non_zero[Simple_10Story_Frame]` | FAILING |
| `test_reactions_non_zero[Medium_20Story_Core]` | FAILING |

**Root Cause:** After analysis, `node_reactions` dictionary is empty even though `node_displacements` contains non-zero values (displacements at z>0 show real values). The issue is in reaction extraction from OpenSeesPy, not the constraint handler.

**Investigation needed:**
1. Check if `ops.nodeReaction(node_tag)` returns zeros for fixed nodes
2. Verify that base nodes (z=0) are actually fixed with `ops.fix()`
3. Check if reactions need to be extracted after analysis differently
4. Consider if `ops.reactions()` needs to be called first

**Potential fixes to try:**
```python
# In solver.py extract_results(), before calling nodeReaction:
ops.reactions()  # May need to compute reactions explicitly

# Or check if nodes are actually fixed:
for node_tag in base_nodes:
    print(f"Node {node_tag} fixity: {ops.nodeFixity(node_tag)}")
```

**Priority:** HIGH - These tests validate core FEM functionality
**Track:** Dedicated investigation task (complex debugging required)

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

**This requires deep FEM debugging, not a simple fix.** Suggested approach:

1. Create a minimal test case:
```python
import openseespy.opensees as ops

# Create simple 2-node model
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Nodes
ops.node(1, 0, 0, 0)
ops.node(2, 0, 0, 10)

# Fix base
ops.fix(1, 1, 1, 1, 1, 1, 1)

# Material and section
ops.geomTransf('Linear', 1, 0, 1, 0)
ops.element('elasticBeamColumn', 1, 1, 2, 1.0, 30e9, 1e9, 0.01, 0.01, 0.01, 1)

# Load
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)
ops.load(2, 0, 0, -1000, 0, 0, 0)  # -1000N in Z

# Analyze
ops.constraints('Plain')
ops.numberer('RCM')
ops.system('BandGeneral')
ops.test('NormDispIncr', 1e-8, 10)
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')
ops.analyze(1)

# Check
print("Disp at node 2:", ops.nodeDisp(2))
print("Reaction at node 1:", ops.nodeReaction(1))
```

2. If reactions are zero, try calling `ops.reactions()` before extraction
3. Check OpenSeesPy documentation for correct reaction extraction sequence

---

*Updated by Orchestrator: 2026-01-30*
