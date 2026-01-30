# Track 6: UI/UX Overhaul

> **Priority:** P1 (SHOULD)
> **Start Wave:** 1 (Partial), rolling through Wave 5
> **Primary Agents:** frontend-specialist, backend-specialist (21.5 only)
> **Status:** PENDING

---

## Overview

Comprehensive UI/UX enhancement: remove simplified UI, relocate FEM views, add display controls, calculation tables, reaction exports, and switch visualization backend to opsvis. This is a long-running track that spans most of the project.

**WARNING: app.py Bottleneck** - Most tasks in this track modify `app.py`. They MUST be sequenced carefully to avoid merge conflicts. The execution order below is binding.

---

## External Dependencies

| Dependency | Track | Task | Reason |
|------------|-------|------|--------|
| Simplified code removed | Track 1 | 16.1 | Can't clean dashboard until backend is clean |
| Analysis working | Tracks 3-5 | Various | Some UI features need analysis results |

---

## Tasks (Execution Order is BINDING for app.py tasks)

### Task 16.2: Update Dashboard for FEM-Only Flow
**Agent:** frontend-specialist
**Model:** gemini-3-pro
**Wave:** 1 (After 16.1)
**Dependencies:** Track 1 (16.1 complete)
**Status:** DONE (2026-01-29)
**Sequence:** 1 of 8 (app.py)

**Sub-tasks:**
- [x] 16.2.1: Remove "Simplified Method" UI sections from `app.py`
- [x] 16.2.2: Update sidebar to focus on FEM model inputs
- [x] 16.2.3: Remove comparison views (FEM vs Simplified)
- [x] 16.2.4: Update KEY METRICS to show FEM results only
- [x] 16.2.5: Update status badges to reflect FEM analysis state

**Changes Made:**
- Removed import of `build_fem_vs_simplified_comparison`
- Removed "FEM vs Simplified" tab and 20 lines of comparison content
- Updated docstring and 3 captions from "simplified" to "preliminary design"
- app.py reduced from 2208 to 2186 lines

**Files:** `app.py`

**Verification:**
- No "simplified" options visible in UI
- Dashboard shows FEM-only workflow

---

### Task 21.5: Switch to opsvis from vfo
**Agent:** backend-specialist
**Model:** sonnet
**Wave:** 2
**Dependencies:** Minimal
**Status:** PENDING
**Note:** This is a backend task (library swap), NOT on app.py

**Sub-tasks:**
- [ ] 21.5.1: Remove vfo imports and usage
- [ ] 21.5.2: Implement opsvis data extraction
- [ ] 21.5.3: Update visualization functions to use opsvis format
- [ ] 21.5.4: Update requirements.txt (remove vfo, ensure opsvis)

**Files:** `src/fem/visualization.py`, `requirements.txt`

**Verification:**
- vfo completely removed
- opsvis provides visualization data

---

### Task 21.1: Relocate FEM Views Section
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 3 (After 16.2)
**Dependencies:** Task 16.2
**Status:** DONE (2026-01-29)
**Sequence:** 2 of 8 (app.py)

**Sub-tasks:**
- [x] 21.1.1: Move FEM Views section below KEY METRICS
- [x] 21.1.2: Move visualization legends to bottom of views
- [x] 21.1.3: Arrange view buttons: Plan (Left), Elevation (Center), 3D (Right)
- [x] 21.1.4: Add floor selection dropdown next to Plan View button
- [x] 21.1.5: Format floor labels as "G/F (+0.00)", "1/F (+4.00)", etc.

**Changes Made:**
- Added new FEM Views section immediately after Key Metrics (lines 1730-1859)
- Created horizontal button row with Plan/Elevation/3D buttons
- Added floor selector dropdown with HK convention labels (G/F, 1/F, 2/F, etc.)
- Legends placed at bottom of each view using st.caption()
- Fixed undefined variable `selected_slab_type` in Detailed Results section
- app.py now 2310 lines (added ~130 lines for FEM Views section)

**Files:** `app.py`

**Verification:**
- FEM Views below KEY METRICS
- Legends at bottom
- Floor selector properly formatted

---

### Task 21.2: Conditional Utilization Display
**Agent:** frontend-specialist
**Model:** haiku
**Wave:** 4 (After 21.1)
**Dependencies:** Task 21.1
**Status:** PENDING
**Sequence:** 3 of 8 (app.py)

**Sub-tasks:**
- [ ] 21.2.1: Hide utilization bars until FEM analysis complete
- [ ] 21.2.2: Hide element colors until analysis complete
- [ ] 21.2.3: Reduce utilization bar height to 50% of current
- [ ] 21.2.4: Add "Run Analysis" prompt when results not available

**Files:** `app.py`

---

### Task 21.3: Independent Axis Scale Controls
**Agent:** frontend-specialist
**Model:** haiku
**Wave:** 4 (Parallel with 21.2)
**Dependencies:** Task 21.1
**Status:** PENDING
**Sequence:** 4 of 8 (app.py - different section from 21.2)

**Sub-tasks:**
- [ ] 21.3.1: Add X-axis scale slider (0.5x - 2.0x)
- [ ] 21.3.2: Add Y-axis scale slider (0.5x - 2.0x)
- [ ] 21.3.3: Update Plotly figure with scaled axes
- [ ] 21.3.4: Maintain aspect ratio option (checkbox)

**Files:** `app.py`

---

### Task 21.6: Display Options Panel
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 4 (After 21.5)
**Dependencies:** Task 21.5 (opsvis available)
**Status:** PENDING
**Sequence:** 5 of 8 (app.py)

**Sub-tasks:**
- [ ] 21.6.1: Create display options panel BELOW FEM views
- [ ] 21.6.2: Add toggle: Show Loads (with opsvis plot_load)
- [ ] 21.6.3: Add toggle: Show Deformed Shape (plot_defo)
- [ ] 21.6.4: Add toggle: Show Reactions (plot_reactions)
- [ ] 21.6.5: Add force diagram dropdown: N, Vy, Vz, My, Mz, T
- [ ] 21.6.6: Add scale factor slider for deformed shape

**Files:** `app.py`, `src/fem/visualization.py`

---

### Task 21.4: Calculation Tables Toggle
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 5 (After analysis features ready)
**Dependencies:** Tracks 3-5 (analysis produces results)
**Status:** PENDING
**Sequence:** 6 of 8 (app.py)

**Sub-tasks:**
- [ ] 21.4.1: Create collapsible "Calculations" section
- [ ] 21.4.2: Show element capacity checks (HKConcreteProperties)
- [ ] 21.4.3: Organize tables by floor
- [ ] 21.4.4: Include columns: Element, Demand, Capacity, Utilization, Status
- [ ] 21.4.5: Add export to CSV option

**Files:** `app.py`

---

### Task 21.7: Reaction Table View and Export
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 5 (After load system complete)
**Dependencies:** Track 5 (load cases defined), analysis working
**Status:** PENDING
**Sequence:** 7 of 8 (app.py)

**Sub-tasks:**
- [ ] 21.7.1: Create Reaction Table section in results area
- [ ] 21.7.2: Extract reaction forces from all support nodes at base
- [ ] 21.7.3: Display reactions per node (Fx, Fy, Fz, Mx, My, Mz)
- [ ] 21.7.4: Show reactions for all individual load cases (DL, SDL, LL, W1-W24, E1-E3)
- [ ] 21.7.5: Show reactions for all load combinations (ULS, SLS)
- [ ] 21.7.6: Add load case/combination selector dropdown
- [ ] 21.7.7: Calculate total reactions (sum of all nodes) per load case
- [ ] 21.7.8: Implement export to CSV functionality
- [ ] 21.7.9: Implement export to Excel functionality (.xlsx)
- [ ] 21.7.10: Add "Copy to Clipboard" button for quick data sharing

**Files:** `app.py`

---

## Internal Execution Order (BINDING)

```
16.2 (Remove simplified UI)
  |
  v
21.1 (Relocate FEM views)
  |
  ├──> 21.2 (Conditional utilization)
  ├──> 21.3 (Axis scale controls)
  └──> 21.6 (Display options - needs 21.5 too)
         |
         v
       21.4 (Calculation tables)
         |
         v
       21.7 (Reaction table + export)

21.5 (opsvis switch) -- independent backend task, feeds into 21.6
```

---

## Cross-Track Dependencies

| This Track Produces | Required By |
|---------------------|-------------|
| 16.2 complete (clean dashboard) | Track 3: 17.2 (wall location UI) |
| 21.5 complete (opsvis) | 21.6 (display options panel) |
| 21.7 complete (reaction table) | Track 8: integration tests |

| This Track Requires | From Track |
|---------------------|------------|
| 16.1 complete | Track 1 |
| Load cases defined | Track 5 (for 21.7) |
| Analysis working | Tracks 3, 4, 5 (for 21.4, 21.7) |

---

*Track Owner: Orchestrator*
*Last Updated: 2026-01-26*
