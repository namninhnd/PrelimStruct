# Quick Wins for v3.5 Upgrade - 2-Day Sprint (REVISED after Momus Review)

---

## 🔴 LIVE PROGRESS TRACKER

> **STATUS**: IN PROGRESS  
> **Last Updated**: [Agent updates this on completion]  
> **Session Recovery**: Copy table below to continue from interruption

| Task | Description | Agent | Status | Session ID | Updated By |
|------|-------------|-------|--------|------------|------------|
| **0** | Wire unified FEM views (BLOCKER) | @frontend-specialist | ✅ DONE | ses_3ec4176a9ffevE2AYzIciJE2Hl | @frontend-specialist |
| **1** | Verify conditional utilization | @frontend-specialist | ⏳ PENDING | - | - |
| **2** | Beam color differentiation | @backend-specialist | ⏳ PENDING | `ses_3ec415e72ffe77uwxqcgROilNQ` | - |
| **3** | Fix coupling beam NoneType | @debugger | ⏳ PENDING | `ses_3ec413d92ffeZOrugV6SWSWxxC` | - |
| **4** | Reaction table + CSV export | @backend-specialist | ⏳ PENDING | - | - |
| **5** | Calculation tables toggle | @frontend-specialist | ⏳ PENDING | - | - |
| **6** | UI layout reorganization | @frontend-specialist | ⏳ PENDING | - | - |

**Legend**: ⏳ PENDING | 🔄 IN PROGRESS | ✅ DONE | ❌ BLOCKED | ⚠️ NEEDS REVIEW

### Handoff Log

| Timestamp | Agent | Action | Notes |
|-----------|-------|--------|-------|
| 2026-01-31 | @frontend-specialist | Task 0 DONE | Wired unified views, tested successfully |
| _waiting for first update_ | - | - | - |

---

**REVISION NOTE**: This plan was corrected based on Momus feedback:
- ✅ Task 0: Integration points now explicit (both view blocks specified, session state key documented)
- ✅ Task 2: File references corrected (`element_renderer.py`, `visualization_core.py`)
- ✅ Task 4 (Custom LL): REMOVED - feature already fully implemented
- ✅ Task 4 (Reaction Table): Scope reduced to single load pattern only (solver limitation)
- ✅ Task 3: Reproduction path added (I_SECTION/TWO_C_FACING trigger error)
- ✅ Task count: 8 → 7 tasks

## Context

### Original Request
User: "We need to discuss about the upgrade recently. However, I m not so happy with it, and it looks so far the same as previous one!"

### Interview Summary

**Key Discussions**:
- User frustrated: 46 commits in 2 weeks, but app looks identical to before
- User expected: visual UI changes, new features, better performance, improved results
- User selected: "Pause refactoring, quick wins first"
- User selected ALL 7 quick wins from PRD.md

**User's Specific Complaints**:
1. "still has 3 views, which is not as what we planned" → Expected: unified view system
2. "main opsv View should be a descendant of all 3 views" → Expected: opsvis as parent data source
3. "beams are not well defined with different colours" → Expected: primary vs secondary beam colors
4. "analysis layer is on all the time" → Expected: conditional display only after analysis

**Root Cause Identified**:
- ✅ Refactoring created `src/ui/views/fem_views.py` (450 lines) with unified view system
- ✅ Created `src/fem/visualization_core.py` with opsvis integration
- ❌ BUT `app.py` (2443 lines) NEVER USES THE NEW MODULES
- ❌ Still calls old `create_plan_view()`, `create_elevation_view()`, `create_3d_view()` directly
- **Result**: All refactoring work created dead code - app runs old pre-refactor version

**Research Findings**:
- PRD.md Feature 21 (UI/UX Enhancement) defines all requested tasks
- `fem_views.py` already implements: unified views, display options, conditional overlay, export
- `visualization_core.py` already implements: opsvis extraction with fallback
- Codebase has 793 tests, pytest infrastructure exists
- LSP shows type errors in app.py (None checks, tuple mismatches)

---

## Work Objectives

### Core Objective
Deliver 7 visible improvements (1 blocker + 6 quick wins) in 2 days to demonstrate the v3.5 upgrade is real and working.

### Concrete Deliverables
1. Unified FEM view system (single module, opsvis-based)
2. Beam color differentiation (primary blue, secondary light blue)
3. Conditional utilization display (only after analysis runs)
4. Reaction table with CSV export (current load pattern)
5. Coupling beam error fixed (no NoneType crashes)
6. Calculation tables toggle (show/hide element checks)
7. Better UI layout (views below metrics, legends at bottom)

**NOTE**: Custom live load input (old Task 4) removed - already fully implemented in v3.0!

### Definition of Done
- [ ] User runs `streamlit run app.py` and sees IMMEDIATE visual difference from current state
- [ ] All 7 tasks complete and tested
- [ ] No regressions in existing features
- [ ] Manual QA verification for each task

### Must Have
- Task 0 (wire unified views) MUST be done first - it's a blocker
- All 6 quick wins from user selection
- No breaking changes to existing workflows

### Must NOT Have (Guardrails)
- **NO deep refactoring** - quick wins only
- **NO shell element implementation** (deferred to later - too complex for quick win)
- **NO 24 wind cases** (deferred to later - requires deep changes)
- **NO AI chat** (deferred to later - separate major feature)
- **NO database schema changes**
- **NO API changes that break existing code**
- **NO over-engineering** - simple, working solutions only
- **NO "while we're here" scope creep** - stick to the 8 tasks

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest, 793 tests)
- **User wants tests**: Manual verification first, regression tests after
- **Framework**: pytest
- **QA approach**: Manual verification after each task, then add regression tests

### Manual QA Approach

**For Each Task**:
1. Run `streamlit run app.py`
2. Navigate to affected section
3. Execute verification steps (defined in each TODO)
4. Document evidence (screenshots, terminal output)
5. Check for regressions in related features

---

## Orchestration Guide (FOR SISYPHUS-ORCHESTRATOR)

**CRITICAL**: Follow this orchestration plan to save tokens and stay focused.

### Agent & Skill Assignments

| Task | Agent | Skills to Load | Rationale |
|------|-------|----------------|-----------|
| Task 0 | `frontend-specialist` | `react-patterns`, `clean-code` | UI integration work, need frontend expertise |
| Task 1 | `frontend-specialist` | `clean-code` | UI verification only, reuse frontend agent |
| Task 2 | `backend-specialist` | `clean-code`, `python-patterns` | Visualization code logic, Python implementation |
| Task 3 | `debugger` | `systematic-debugging`, `python-patterns` | Root cause analysis of NoneType error |
| Task 4 | `backend-specialist` | `python-patterns`, `clean-code` | Data extraction and export, backend logic |
| Task 5 | `frontend-specialist` | `react-patterns`, `clean-code` | UI tables and collapsible sections |
| Task 6 | `frontend-specialist` | `react-patterns`, `clean-code` | UI layout reorganization |

### Execution Waves (Token-Efficient Orchestration)

**WAVE 0 (BLOCKER - MUST COMPLETE FIRST)**:
```
Task 0: Wire Unified Views
├─ Agent: frontend-specialist
├─ Skills: react-patterns, clean-code
└─ BLOCKING: All other tasks depend on this
```

**WAVE 1 (PARALLEL - After Wave 0)**:
```
Task 1: Verify Conditional Utilization (verification only - quick)
├─ Agent: frontend-specialist (reuse from Wave 0 if possible)
├─ Skills: clean-code
└─ Time: 15 min

Task 2: Beam Color Differentiation
├─ Agent: backend-specialist
├─ Skills: clean-code, python-patterns
└─ Time: 2 hours

Task 3: Fix Coupling Beam Error
├─ Agent: debugger
├─ Skills: systematic-debugging, python-patterns
└─ Time: 1-2 hours
```

**WAVE 2 (PARALLEL - After Wave 1)**:
```
Task 4: Reaction Table + Export
├─ Agent: backend-specialist (reuse from Task 2)
├─ Skills: python-patterns, clean-code
└─ Time: 3-4 hours

Task 5: Calculation Tables Toggle
├─ Agent: frontend-specialist (reuse from Task 1)
├─ Skills: react-patterns, clean-code
└─ Time: 2-3 hours
```

**WAVE 3 (SEQUENTIAL - Final Polish)**:
```
Task 6: UI Layout Reorganization
├─ Agent: frontend-specialist (reuse from Task 5)
├─ Skills: react-patterns, clean-code
└─ Time: 30 min
```

### Token Budget Allocation

| Wave | Estimated Tokens | Rationale |
|------|------------------|-----------|
| Wave 0 | 20,000 | Critical blocker, needs careful integration |
| Wave 1 | 30,000 | 3 parallel tasks, each 10K average |
| Wave 2 | 50,000 | 2 larger tasks, each 25K |
| Wave 3 | 10,000 | Simple layout changes |
| **Total** | **110,000** | Well within 200K budget |

### Handoff Protocol Between Waves

**After Each Wave:**
1. ✅ Verify all tasks in wave complete
2. ✅ Run manual QA verification for each task
3. ✅ Commit changes with proper messages
4. ✅ Update todo list to mark wave complete
5. ✅ Proceed to next wave ONLY if all wave tasks pass

**DO NOT:**
- ❌ Start next wave before current wave completes
- ❌ Mix tasks across waves (respect dependencies)
- ❌ Skip manual QA verification steps

---

## Task Flow

```
Task 0 (BLOCKER) → Task 21.2 (verify existing code)
                 → Task 18.2 (beam colors) → Task 17.4 (bug fix)
                                          → Task 20.4 (custom LL)
                                          → Task 21.7 (reactions)
                                          → Task 21.4 (calc tables)
                                          → Task 21.1 (layout)
```

## Parallelization

| Group | Tasks | Reason |
|-------|-------|--------|
| A | 2, 3 | Independent features after Task 0 |
| B | 4, 5 | Both add new UI sections |

| Task | Depends On | Reason |
|------|------------|--------|
| All | Task 0 | Task 0 must complete first - wires unified views |
| 21.2 | Task 0 | Verification of existing code in unified views |

---

## TODOs

- [ ] 0. Wire Up Unified FEM Views in app.py (BLOCKER)

  **Agent**: `frontend-specialist`  
  **Skills**: `react-patterns`, `clean-code`  
  **Wave**: 0 (BLOCKER - must complete first)

  **What to do**:
  - **Add Import** (after line 46):
    ```python
    from src.ui.views.fem_views import render_unified_fem_views
    ```
  - **Replace First View Block** (lines ~1950-2000):
    - Locate section with first `create_plan_view()` call (around line 1954)
    - Replace entire view rendering with:
      ```python
      render_unified_fem_views(
          project=project,
          analysis_result=st.session_state.get('fem_preview_analysis_result'),
          config_overrides={}
      )
      ```
  - **Replace Second View Block** (lines ~2170-2220):
    - Locate section with second `create_plan_view()` call (around line 2172)
    - Replace with same unified call OR remove block entirely if redundant
  - **Remove Old Imports** (lines 44-46):
    - Delete: `create_plan_view`, `create_elevation_view`, `create_3d_view`
  - **Test**: Run `streamlit run app.py` and verify views render

  **Must NOT do**:
  - Don't refactor other parts of app.py
  - Don't change the logic around analysis results
  - Don't modify session state management

  **Parallelizable**: NO (blocks all other tasks)

  **References**:

  **Pattern References**:
  - `src/ui/views/fem_views.py:126-450` - Complete unified view implementation (already coded!)
  - `src/ui/views/fem_views.py:126` - Function signature: `render_unified_fem_views(project, analysis_result, config_overrides)`
  - `app.py:44-46` - Current imports of old view functions
  - `app.py:~1954, ~1971, ~1982, ~2172, ~2191, ~2208` - Current old view calls to replace

  **API/Type References**:
  - `src.core.data_models.ProjectData` - Project data structure passed to views
  - Analysis result object has attributes: `.success`, `.node_displacements`, `.node_reactions`
  - Session state key: `fem_preview_analysis_result` - stores analysis results

  **Why Each Reference Matters**:
  - `fem_views.py:126-450` contains COMPLETE working implementation - don't rewrite, just use it!
  - The function already handles: model building, caching, display options, tabs, export
  - Current app.py calls are scattered across ~250 lines - unified view replaces all of this

  **Acceptance Criteria**:

  **Manual Execution Verification**:
  - [ ] Start app: `streamlit run app.py`
  - [ ] Navigate to FEM Views section (should be below KEY METRICS)
  - [ ] Verify: 3 tabs appear (Plan View, Elevation View, 3D View)
  - [ ] Verify: Display Options expander appears with checkboxes (show nodes, supports, loads, labels, slabs, mesh, ghost cols)
  - [ ] Verify: Color Scheme selector shows "Element Type" and "Utilization" options
  - [ ] Verify: Plan View tab has floor level selector (format: "G/F (+0.00)", "1/F (+4.00)", etc.)
  - [ ] Verify: Elevation View tab has X/Y direction radio buttons
  - [ ] Verify: Model Statistics section shows: Nodes, Elements, Loads, Diaphragms, Slab Load metrics
  - [ ] Verify: Export Visualization section shows: view selector, format dropdown, buttons
  - [ ] Click each tab and verify views render without errors

  **Evidence Required**:
  - [ ] Screenshot of Display Options panel (showing all checkboxes)
  - [ ] Screenshot of each tab (Plan, Elevation, 3D) rendering correctly
  - [ ] Terminal output shows no errors during view rendering

  **Commit**: YES
  - Message: `feat(ui): wire unified FEM views to replace old 3-view system`
  - Files: `app.py`
  - Pre-commit: `streamlit run app.py --server.headless true` (check app loads without error)

---

- [ ] 1. Verify Conditional Utilization Display (Task 21.2)

  **Agent**: `frontend-specialist` (reuse from Task 0)  
  **Skills**: `clean-code`  
  **Wave**: 1 (PARALLEL with 2, 3, 4)

  **What to do**:
  - After Task 0 complete, verify that utilization bars/colors only appear after analysis runs
  - Check `fem_views.py` lines 226-244 for conditional overlay logic
  - Verify utilization map is empty `{}` when no analysis results
  - Verify color mode "Utilization" shows grey/default when no results

  **Must NOT do**:
  - Don't modify the conditional logic (already correct in fem_views.py)
  - Don't add new utilization calculation code

  **Parallelizable**: YES (with Task 18.2 after Task 0)

  **References**:

  **Pattern References**:
  - `src/ui/views/fem_views.py:226-244` - Conditional overlay toggle logic
  - `src/ui/views/fem_views.py:246-255` - Utilization map handling

  **Acceptance Criteria**:

  **Manual Execution Verification**:
  - [ ] Start app with NO analysis run: `streamlit run app.py`
  - [ ] Navigate to FEM Views
  - [ ] Verify: NO utilization bars visible on elements
  - [ ] Verify: Color Scheme "Utilization" mode shows elements in grey/default color
  - [ ] Run FEM Analysis (click "Run FEM Analysis" button in app)
  - [ ] Verify: "Overlay Analysis Results" checkbox appears
  - [ ] Check "Overlay Analysis Results" checkbox
  - [ ] Verify: Utilization colors/bars NOW appear (if utilization data exists)

  **Evidence Required**:
  - [ ] Screenshot of views BEFORE analysis (no utilization visible)
  - [ ] Screenshot of views AFTER analysis with overlay (utilization visible)

  **Commit**: NO (verification only, no code changes)

---

- [ ] 2. Beam Color Differentiation (Task 18.2)

  **Agent**: `backend-specialist`  
  **Skills**: `clean-code`, `python-patterns`  
  **Wave**: 1 (PARALLEL with 1, 3, 4)

  **What to do**:
  - Modify beam visualization to differentiate primary vs secondary beams with different colors
  - Primary beams: Blue (#1f77b4)
  - Secondary beams: Light Blue (#aec7e8)
  - Add legend entry: "Primary Beam" and "Secondary Beam"
  - Show beam type in hover tooltip

  **Must NOT do**:
  - Don't change existing beam generation logic in model_builder.py
  - Don't add complex classification logic - use existing element metadata

  **Parallelizable**: YES (with Task 17.4, 20.4 after Task 0)

  **References**:

  **Pattern References**:
  - `src/fem/visualization/element_renderer.py:125` - Beam classification (`if elem.section_tag == 2:`)
  - `src/fem/visualization/element_renderer.py:163` - Color assignment (`COLORS["beam_secondary"]` vs `COLORS["beam"]`)
  - `src/fem/visualization_core.py:565-566` - Secondary beam identification logic
  - `src/fem/builders/beam_builder.py:319` - `create_secondary_beams()` function

  **API/Type References**:
  - `src.fem.fem_engine.ElementType` - Enum with element types (may need to add SECONDARY_BEAM)
  - Plotly color constants: `#1f77b4` (blue), `#aec7e8` (light blue)

  **Why Each Reference Matters**:
  - `element_renderer.py:125` contains beam classification logic (`section_tag == 2` for secondary)
  - `element_renderer.py:163` shows current color scheme - modify this to differentiate colors
  - Current colors exist: `COLORS["beam"]` and `COLORS["beam_secondary"]` - need to verify/update values
  - Classification is already implemented - just need to ensure colors are visually distinct

  **Acceptance Criteria**:

  **Manual Execution Verification**:
  - [ ] Run app: `streamlit run app.py`
  - [ ] Navigate to FEM Views → Plan View
  - [ ] Verify: Primary beams (along X and Y grids) appear in BLUE (#1f77b4)
  - [ ] Verify: Secondary beams (if any exist based on settings) appear in LIGHT BLUE (#aec7e8)
  - [ ] Verify: Legend shows "Primary Beam" (blue) and "Secondary Beam" (light blue) entries
  - [ ] Hover over primary beam: tooltip shows "Type: Primary Beam" (or similar)
  - [ ] Hover over secondary beam: tooltip shows "Type: Secondary Beam"
  - [ ] Check Elevation View and 3D View: same color differentiation

  **Evidence Required**:
  - [ ] Screenshot of Plan View showing both beam types in different colors
  - [ ] Screenshot of legend with both beam type entries
  - [ ] Screenshot of tooltip showing beam type

  **Commit**: YES
  - Message: `feat(viz): differentiate primary and secondary beams with color coding`
  - Files: `src/fem/visualization/element_renderer.py`
  - Pre-commit: `pytest tests/test_visualization*.py -v`

---

- [ ] 3. Fix Coupling Beam Generation Error (Task 17.4)

  **Agent**: `debugger`  
  **Skills**: `systematic-debugging`, `python-patterns`  
  **Wave**: 1 (PARALLEL with 1, 2, 4)

  **What to do**:
  - **Reproduce Error**:
    - In app sidebar, select core wall type: I_SECTION or TWO_C_FACING
    - Observe NoneType division error in terminal/UI
  - Trace error to source in `src/fem/builders/beam_builder.py` (coupling beam creation) or `src/fem/coupling_beam.py`
  - Search for division operations involving: `opening_width`, `opening_height`, `span`, `depth`
  - Add null checks before division: `if value is not None and value != 0:`
  - Fix calculation when opening dimensions are None or zero
  - Add unit tests for edge cases (no openings, zero dimensions, None values)

  **Must NOT do**:
  - Don't rewrite coupling beam logic from scratch
  - Don't change core wall geometry calculations unnecessarily

  **Parallelizable**: YES (with Task 18.2, 20.4 after Task 0)

  **References**:

  **Pattern References**:
  - `src/fem/builders/beam_builder.py` - BeamBuilder class with `create_coupling_beams()` method
  - `src/fem/coupling_beam.py` - Coupling beam geometry generation
  - `src/fem/core_wall_geometry.py` - Core wall classes with opening attributes (opening_width, opening_height)

  **API/Type References**:
  - Core wall classes: `ISectionCoreWall`, `TwoCFacingCoreWall`, etc. - check opening_width, opening_height attributes
  - Error traceback (if available) showing exact line causing NoneType division

  **Test References**:
  - `tests/test_coupling_beam*.py` - Existing coupling beam tests (if any)

  **Why Each Reference Matters**:
  - `beam_builder.py` calls coupling beam creation - error likely occurs during build
  - Division by None likely in span/depth or opening dimension calculations
  - Core wall types without coupling beams (e.g., TUBE types) may pass None for opening dimensions
  - Need defensive checks: `if opening_width and opening_width > 0:` before division

  **Acceptance Criteria**:

  **Manual Execution Verification**:
  - [ ] Run app: `streamlit run app.py`
  - [ ] Configure project with core wall that has coupling beams (e.g., I_SECTION, TWO_C_FACING)
  - [ ] Verify: NO NoneType division error appears in terminal or UI
  - [ ] Verify: Coupling beams appear in visualization (if applicable to core type)
  - [ ] Try edge cases: zero opening width, zero opening height, TUBE cores
  - [ ] Verify: Graceful handling (no errors, appropriate warning messages if needed)

  **Test Execution Verification**:
  - [ ] Run tests: `pytest tests/test_coupling_beam*.py -v`
  - [ ] Verify: All tests PASS
  - [ ] New tests cover: None openings, zero dimensions, invalid geometry

  **Evidence Required**:
  - [ ] Terminal output showing NO errors when building model with coupling beams
  - [ ] Screenshot of coupling beams in visualization
  - [ ] Test output showing new edge case tests passing

  **Commit**: YES
  - Message: `fix(fem): add null checks for coupling beam generation to prevent NoneType errors`
  - Files: `src/fem/builders/beam_builder.py`, `src/fem/coupling_beam.py` (whichever has the error), `tests/test_coupling_beam*.py` (add tests)
  - Pre-commit: `pytest tests/test_coupling_beam*.py -v`

---

**NOTE: Task 4 (Custom Live Load Input) has been REMOVED - feature already fully implemented!**  
- `src/core/data_models.py:418` - `custom_live_load` field exists
- `src/ui/sidebar.py:187` - "9: Other (Custom)" option exists  
- Feature is production-ready - no work needed

**Task numbering updated**: Old Tasks 5-7 are now Tasks 4-6

---

- [ ] 4. Reaction Table View and Export (Task 21.7)

  **Agent**: `backend-specialist` (reuse from Task 2)  
  **Skills**: `python-patterns`, `clean-code`  
  **Wave**: 2 (PARALLEL with 5, AFTER Wave 1)

  **What to do**:
  - Create new "Reaction Table" section in results area (after FEM Views or in separate tab)
  - Extract reaction forces from all support nodes at base (Z=0 or fixed nodes using `Node.is_fixed` attribute)
  - Display reactions per node: Node ID, Fx, Fy, Fz, Mx, My, Mz
  - **SCOPE LIMITATION**: Show reactions for **most recent analysis run only** (current load pattern)
  - Label table as "Reactions - Current Load Pattern"  
  - Calculate total reactions (sum of all nodes) for current pattern
  - Implement export to CSV functionality (use pandas DataFrame.to_csv)
  - Add "Copy to Clipboard" button for quick data sharing

  **Must NOT do**:
  - **DO NOT implement multi-case support** (DL/SDL/LL/W1-W24/combinations) - solver limitation
  - Don't implement Excel export yet (defer if complex) - CSV only for quick win
  - Don't modify analysis solver logic
  - Don't change load combination definitions

  **Future Enhancement**:
  - Multi-load-case support requires solver enhancement to run/store multiple analyses
  - This is a Phase 2+ feature, not part of quick wins

  **Parallelizable**: YES (with Task 21.4 after Task 0)

  **References**:

  **Pattern References**:
  - Analysis result object: `.node_reactions` - dict of {node_tag: [Fx, Fy, Fz, Mx, My, Mz]}
  - `src/fem/solver.py` - Solver that produces analysis results
  - `src/fem/load_combinations.py` - Load combination definitions

  **API/Type References**:
  - `src.fem.solver.AnalysisResult` - Result object structure
  - Pandas DataFrame for table display and CSV export

  **Why Each Reference Matters**:
  - Need to understand structure of node_reactions dict (keys, value format)
  - Need to identify which nodes are at base (Z=0 or fixed supports)
  - Need to extract reactions for each load case/combination separately

  **Acceptance Criteria**:

  **Manual Execution Verification**:
  - [ ] Run app: `streamlit run app.py`
  - [ ] Configure project and run FEM Analysis
  - [ ] Navigate to Reaction Table section
  - [ ] Verify: Table title shows "Reactions - Current Load Pattern"
  - [ ] Verify: Table displays with columns: Node ID, Fx, Fy, Fz, Mx, My, Mz
  - [ ] Verify: All base nodes (supports) are listed
  - [ ] Verify: Total row at bottom shows sum of reactions
  - [ ] Click "Export to CSV" button
  - [ ] Verify: CSV file downloads with correct data
  - [ ] Click "Copy to Clipboard" button
  - [ ] Verify: Data copied (can paste into spreadsheet)

  **Evidence Required**:
  - [ ] Screenshot of reaction table for one load case
  - [ ] Screenshot of total reactions row
  - [ ] CSV file content (sample rows)
  - [ ] Terminal output confirming export successful

  **Commit**: YES
  - Message: `feat(results): add reaction table view with CSV export for all load cases`
  - Files: `app.py` (add Reaction Table section), new file `src/ui/views/reaction_table.py` (if extracted to module)
  - Pre-commit: `streamlit run app.py --server.headless true`

---

- [ ] 5. Calculation Tables Toggle (Task 21.4)

  **Agent**: `frontend-specialist` (reuse from Task 1)  
  **Skills**: `react-patterns`, `clean-code`  
  **Wave**: 2 (PARALLEL with 4, AFTER Wave 1)

  **What to do**:
  - Create collapsible "Calculations" section (use st.expander)
  - Show element capacity checks from HKConcreteProperties (if available)
  - Organize tables by floor (separate expander or tabs per floor)
  - Include columns: Element ID, Element Type, Demand, Capacity, Utilization (%), Status (PASS/WARN/FAIL)
  - Add export to CSV option (similar to reaction table)
  - Default state: collapsed (not expanded)

  **Must NOT do**:
  - Don't recalculate capacities (use existing results from design engines)
  - Don't add new capacity check logic (use what exists)

  **Parallelizable**: YES (with Task 21.7 after Task 0)

  **References**:

  **Pattern References**:
  - Existing results in `project.results` (SlabResult, BeamResult, ColumnResult)
  - `src/engines/slab_engine.py`, `src/engines/beam_engine.py`, `src/engines/column_engine.py` - Design results
  - Current results display in app.py (search for "Detailed Results" or results tabs)

  **API/Type References**:
  - `src.core.data_models.SlabResult`, `BeamResult`, `ColumnResult` - Result dataclasses with utilization, status
  - Streamlit `st.expander()` for collapsible section

  **Why Each Reference Matters**:
  - Results already exist in project.results - just need to format them into tables
  - Need to extract: element ID (if available), demand values, capacity values, utilization ratio
  - Need to determine floor organization (by element floor attribute or geometry)

  **Acceptance Criteria**:

  **Manual Execution Verification**:
  - [ ] Run app: `streamlit run app.py`
  - [ ] Configure project and run design calculations
  - [ ] Navigate to Calculations section (below FEM Views or in separate area)
  - [ ] Verify: "Calculations" expander appears (collapsed by default)
  - [ ] Click to expand "Calculations"
  - [ ] Verify: Sub-sections or tabs for each floor (G/F, 1/F, 2/F, etc.)
  - [ ] Expand one floor section
  - [ ] Verify: Table displays with columns: Element ID, Type, Demand, Capacity, Utilization (%), Status
  - [ ] Verify: Status column shows color-coded PASS (green), WARN (yellow), FAIL (red)
  - [ ] Click "Export to CSV" button
  - [ ] Verify: CSV file downloads with all calculation data

  **Evidence Required**:
  - [ ] Screenshot of collapsed "Calculations" expander
  - [ ] Screenshot of expanded table for one floor
  - [ ] Screenshot showing color-coded Status column
  - [ ] CSV file sample

  **Commit**: YES
  - Message: `feat(results): add collapsible calculation tables organized by floor`
  - Files: `app.py` (add Calculations section), possibly `src/ui/views/calculation_tables.py` (if extracted)
  - Pre-commit: `streamlit run app.py --server.headless true`

---

- [ ] 6. UI Layout Reorganization (Task 21.1)

  **Agent**: `frontend-specialist` (reuse from Task 5)  
  **Skills**: `react-patterns`, `clean-code`  
  **Wave**: 3 (SEQUENTIAL - final polish, AFTER Wave 2)

  **What to do**:
  - Move FEM Views section to appear BELOW KEY METRICS section in app.py
  - Move visualization legends to bottom of each view (Plan, Elevation, 3D)
  - Arrange view buttons/tabs: Plan (Left), Elevation (Center), 3D (Right) - already done in unified views
  - Add floor selection dropdown next to Plan View (already in unified views)
  - Format floor labels as "G/F (+0.00)", "1/F (+4.00)", etc. (already in unified views)

  **Must NOT do**:
  - Don't change KEY METRICS calculation logic
  - Don't rearrange other sections unnecessarily

  **Parallelizable**: NO (best done last after other UI changes complete)

  **References**:

  **Pattern References**:
  - `app.py` - Current layout structure (find KEY METRICS section and FEM Views section)
  - `src/ui/views/fem_views.py:268-280` - Floor label formatting (already implemented!)

  **Why Each Reference Matters**:
  - Need to find current FEM Views section location in app.py
  - Need to move it below KEY METRICS section (cut/paste in code)
  - Floor formatting and view arrangement already handled by unified views module

  **Acceptance Criteria**:

  **Manual Execution Verification**:
  - [ ] Run app: `streamlit run app.py`
  - [ ] Scroll down main page
  - [ ] Verify: KEY METRICS section appears FIRST
  - [ ] Verify: FEM Views section appears BELOW KEY METRICS (not above)
  - [ ] Verify: Within FEM Views, tabs are arranged: Plan | Elevation | 3D
  - [ ] Verify: Floor selector in Plan View shows format "G/F (+0.00)", "1/F (+4.00)"
  - [ ] Verify: Legends appear at BOTTOM of each view (not top)

  **Evidence Required**:
  - [ ] Screenshot showing order: KEY METRICS → FEM Views
  - [ ] Screenshot of Plan View with floor selector formatted correctly
  - [ ] Screenshot showing legend at bottom of view

  **Commit**: YES (groups with final testing)
  - Message: `refactor(ui): relocate FEM views below key metrics and polish layout`
  - Files: `app.py`
  - Pre-commit: `streamlit run app.py --server.headless true`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 0 | `feat(ui): wire unified FEM views to replace old 3-view system` | `app.py` | `streamlit run app.py --server.headless true` |
| 1 | N/A (verification only) | N/A | Manual QA |
| 2 | `feat(viz): differentiate primary and secondary beams with color coding` | `src/fem/visualization.py` | `pytest tests/test_visualization*.py -v` |
| 3 | `fix(fem): add null checks for coupling beam generation to prevent NoneType errors` | `src/fem/coupling_beam.py`, tests | `pytest tests/test_coupling_beam*.py -v` |
| 4 | `feat(ui): add custom live load input for Class 9 'Other' option` | `src/ui/sidebar.py`, `src/core/data_models.py` | `pytest tests/test_load_tables.py -v` |
| 5 | `feat(results): add reaction table view with CSV export for all load cases` | `app.py`, `src/ui/views/reaction_table.py` | `streamlit run app.py --server.headless true` |
| 6 | `feat(results): add collapsible calculation tables organized by floor` | `app.py`, `src/ui/views/calculation_tables.py` | `streamlit run app.py --server.headless true` |
| 7 | `refactor(ui): relocate FEM views below key metrics and polish layout` | `app.py` | `streamlit run app.py --server.headless true` |

---

## Success Criteria

### Verification Commands
```bash
# Run full app
streamlit run app.py

# Run relevant tests
pytest tests/test_visualization*.py tests/test_coupling_beam*.py tests/test_load_tables.py -v

# Check app loads without errors
streamlit run app.py --server.headless true
```

### Final Checklist
- [ ] All 7 tasks (0-6) completed
- [ ] All commits made with proper messages
- [ ] All manual QA verifications passed with evidence
- [ ] No regressions in existing features
- [ ] User can SEE immediate visual difference when running app
- [ ] All "Must NOT Have" guardrails respected (no scope creep)
