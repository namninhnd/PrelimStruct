# Track 9: Technical Debt & Code Health

> **Priority:** P1 (SHOULD)
> **Start Wave:** Immediate (parallel with other tracks)
> **Primary Agents:** debugger, backend-specialist
> **Status:** ⏳ PENDING
> **Created:** 2026-01-29 (from session discoveries)

---

## Overview

Technical debt and type safety issues discovered during regression fixes and task completion. These are mostly type annotation issues that don't break runtime but could hide real bugs. One critical issue (TD-01) could cause runtime errors.

---

## Tasks

### TD-01: Fix ColumnEngine.check_combined_load Reference
**Agent:** debugger
**Model:** sonnet
**Skills:** @[systematic-debugging]
**Priority:** 🔴 P0 (Critical - potential runtime crash)
**Status:** ✅ DONE (2026-01-29)

**Problem:** `app.py:961` calls `ColumnEngine.check_combined_load()` which was removed during FEM-only refactor (Task 16.1). This will cause `AttributeError` if the code path is executed.

**Resolution (2026-01-29):**
- Removed dead code call (8 lines) from app.py lines 960-967
- Replaced with comment: `# V3.5: check_combined_load() removed - combined_utilization set by ColumnEngine.calculate()`
- Rationale: `ColumnEngine.calculate()` already handles combined_utilization via FEM results
- Tests: 853 passed, 8 skipped

**Files Changed:** `app.py`

---

### TD-02: Fix WallPanel base_point Type Mismatch
**Agent:** backend-specialist
**Model:** gemini-3-pro
**Skills:** @[clean-code]
**Priority:** 🟡 P2 (Type error only)
**Status:** PENDING

**Problem:** `_extract_wall_panels()` passes 3-tuple `(x, y, z)` but `WallPanel.__init__` expects 2-tuple `(x, y)`.

**Solution Options:**
1. Slice the tuple: `(x, y, z)[:2]`
2. Update WallPanel to accept 3-tuple
3. Update WallPanel to use `Tuple[float, ...]`

**Files:** `src/fem/model_builder.py` (lines 683-890)

**Verification:**
- LSP diagnostics clean for these lines
- Tests still pass

---

### TD-03: Fix app.py Type Annotations
**Agent:** backend-specialist
**Model:** gemini-3-pro
**Skills:** @[clean-code]
**Priority:** 🟡 P2 (Type errors only)
**Status:** PENDING

**Sub-tasks:**
- [ ] TD-03.1: Add null checks for `length_x/length_y` before passing (lines 1404-1603)
- [ ] TD-03.2: Fix `lateral_system` attribute access (line 1689)
- [ ] TD-03.3: Convert list to tuple for `suggested_omit_columns` (line 1791)
- [ ] TD-03.4: Define `selected_slab_type` before use (line 2006)
- [ ] TD-03.5: Add null checks for beam result attributes (lines 2053-2069)

**Files:** `app.py`

**Verification:**
- LSP diagnostics reduced for app.py
- App runs without type-related crashes

---

### TD-04: Deprecated Code Cleanup
**Agent:** backend-specialist
**Model:** gemini-3-pro
**Skills:** @[clean-code]
**Priority:** 🟢 P3 (Low - cleanup)
**Status:** PENDING

**Sub-tasks:**
- [ ] TD-04.1: Deprecate or remove `src/fem/analysis_summary.py`
- [ ] TD-04.2: Add proper deprecation notice to `test_moment_frame.py`
- [ ] TD-04.3: Remove any other unused simplified-method code

**Files:** 
- `src/fem/analysis_summary.py`
- `tests/test_moment_frame.py`

**Verification:**
- No import errors
- Tests still pass (with skips)

---

### TD-05: FEM-Based Moment Frame Tests
**Agent:** test-engineer
**Model:** sonnet
**Skills:** @[testing-patterns]
**Priority:** 🟡 P2 (Track 8 dependency)
**Status:** PENDING (linked to Track 8)

**Problem:** `test_moment_frame.py` tests are skipped because they use deprecated simplified API.

**Action:** Write new FEM-based moment frame tests to replace the skipped tests.

**Files:** `tests/test_moment_frame.py` (rewrite)

**Verification:**
- New tests pass
- Coverage maintained or improved

---

## Execution Order

```
TD-01 (Critical) → TD-02 → TD-03 → TD-04 → TD-05 (Track 8)
```

TD-01 should be done immediately. TD-02 through TD-04 can run during Track 6/7 work.
TD-05 is linked to Track 8 (Testing).

---

## Cross-Track Dependencies

| This Track Produces | Required By |
|---------------------|-------------|
| TD-01 complete (no runtime crash) | All tracks (app stability) |
| TD-05 complete | Track 8: 23.1 (unit tests) |

---

*Track Owner: Orchestrator*
*Created: 2026-01-29*
