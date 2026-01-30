# Track 5: Load System (HK COP Wind + Load Combinations)

> **Priority:** P0 (MUST) - Critical Path
> **Start Wave:** 2 (Partial - definitions), Wave 3 (UI)
> **Primary Agents:** backend-specialist, frontend-specialist
> **Status:** ✅ 20.1+20.2+20.3 DONE | ⏳ 20.4, 20.6 pending

---

## Overview

Expand the load case system to include all 24 HK COP wind directions (48 +/- combinations), well-structured load case naming, and improved UI for managing many combinations. Task 20.5 (surface loads) is handled in Track 4 since it depends on slab elements.

---

## External Dependencies (Must Be Complete Before Start)

| Dependency | Track | Task | Reason |
|------------|-------|------|--------|
| Model flow reorganized | Track 1 | 16.3 | Load integration needs clean model structure |

**Note:** Load case definitions (20.1, 20.2) work on `load_combinations.py` which is independent of `model_builder.py`. These can start as soon as Track 1 completes, in parallel with Tracks 3 and 4.

---

## Tasks

### Task 20.1: Implement Full HK COP Wind Load Cases
**Agent:** backend-specialist
**Model:** sonnet
**Wave:** 2 (After 16.3)
**Dependencies:** Track 1 (16.3 complete) ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 20.1.1: Define all 24 HK COP wind directions/cases
- [ ] 20.1.2: Create `WindLoadCase` enum with all cases (W1-W24)
- [ ] 20.1.3: Calculate wind forces for each direction
- [ ] 20.1.4: Generate +/- combinations (48 total wind combinations)
- [ ] 20.1.5: Update `load_combinations.py` with new cases
- [ ] 20.1.6: Cite HK COP Wind Effects clause numbers

**Files Impacted:**
- `src/fem/load_combinations.py`
- `src/core/data_models.py` (WindLoadCase enum)

**Verification:**
- 24 wind cases defined
- 48 wind combinations generated
- Forces correct for each direction

---

### Task 20.2: Define Well-Structured Load Cases
**Agent:** backend-specialist
**Model:** sonnet
**Wave:** 2 (Parallel with 20.1)
**Dependencies:** Track 1 (16.3 complete) ✅
**Status:** ✅ DONE (2026-01-27)

**Sub-tasks:**
- [ ] 20.2.1: Create clear load case naming: DL, SDL, LL, W1-W24, E1-E3
- [ ] 20.2.2: Define Eurocode 8 seismic cases (E1, E2, E3)
- [ ] 20.2.3: Implement load case categories (GRAVITY, WIND, SEISMIC)
- [ ] 20.2.4: Generate ULS/SLS combinations per HK Code
- [ ] 20.2.5: Add combination factors per Table 2.1

**Files Impacted:**
- `src/fem/load_combinations.py`
- `src/core/data_models.py` (load case enums, categories)

**Verification:**
- All load cases properly named
- Categories correctly assigned
- Factors match HK Code Table 2.1

**Note:** Tasks 20.1 and 20.2 are closely related and should be assigned to the SAME backend-specialist agent to avoid conflicts on `load_combinations.py`.

---

### Task 20.3: Load Combination UI Overhaul
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 3 (After 20.1 + 20.2)
**Dependencies:** Tasks 20.1, 20.2
**Status:** ✅ DONE (2026-01-29)

**Sub-tasks:**
- [x] 20.3.1: Create scrollable list for load combinations
- [x] 20.3.2: Add checkbox for each combination
- [x] 20.3.3: Implement "Select All" and "Select None" buttons
- [x] 20.3.4: Group combinations by category (GRAVITY/WIND/SEISMIC)
- [x] 20.3.5: Add collapsible sections for each category
- [x] 20.3.6: Show combination count (selected/total)
- [x] 20.3.7: Store selection in session state

**Files Impacted:**
- `app.py` (load combination section)

**Verification:**
- All combinations visible in scrollable list
- Select All/None works per category
- Selection persists in session

---

### Task 20.4: Custom Live Load Input (Class 9)
**Agent:** frontend-specialist
**Model:** haiku
**Wave:** 3 (Parallel with 20.3)
**Dependencies:** Minimal (existing load input structure)
**Status:** PENDING

**Sub-tasks:**
- [ ] 20.4.1: Add "Other" option to Live Load Class dropdown
- [ ] 20.4.2: Show kPa input field when "Other" selected
- [ ] 20.4.3: Validate input range (0.5 - 20.0 kPa)
- [ ] 20.4.4: Update `LoadInput` model with custom LL field
- [ ] 20.4.5: Apply custom LL to slab loading

**Files Impacted:**
- `app.py` (load input section)
- `src/core/data_models.py` (LoadInput update)

**Verification:**
- "Other" option available in dropdown
- Custom kPa input appears and validates
- Custom load applied to model

---

### Task 20.6: Remove Analysis Load Pattern
**Agent:** backend-specialist
**Model:** haiku
**Wave:** 3
**Dependencies:** Track 1 (16.3 complete)
**Status:** PENDING

**Sub-tasks:**
- [ ] 20.6.1: Remove "Analysis" load pattern from model
- [ ] 20.6.2: Add "Loading Pattern Factor" input for LL scaling
- [ ] 20.6.3: Apply factor to live load in combinations
- [ ] 20.6.4: Update documentation for factor usage

**Files Impacted:**
- `src/fem/model_builder.py` (remove pattern)
- `src/fem/load_combinations.py` (factor integration)
- `app.py` (factor input)

**Verification:**
- No "Analysis" pattern in model
- Factor input works and scales LL correctly

---

## Internal Dependency Chain

```
20.1 (Wind cases) ──┐
                     ├──> 20.3 (Load combo UI)
20.2 (Load struct) ──┘
                          20.4 (Custom LL) -- parallel with 20.3
20.6 (Remove analysis pattern) -- independent
```

---

## Parallelism Notes

- **20.1 + 20.2:** Same file (`load_combinations.py`) - assign to SAME agent, run sequentially
- **20.3 + 20.4:** Different app.py sections - can parallel if careful, or sequence
- **20.6:** Independent but touches model_builder.py - coordinate with Track 3/4

---

## Cross-Track Dependencies

| This Track Produces | Required By |
|---------------------|-------------|
| 20.1 + 20.2 complete (load cases defined) | Track 6: 21.7 (reaction table needs load cases) |
| 20.3 complete (UI for load combos) | Track 6: 21.4 (calculation tables reference combos) |
| All tasks complete | Track 8: 23.1 (load combination tests) |

---

## Agent Instructions

**Tasks 20.1 + 20.2 prompt (backend-specialist):**
> Implement the full HK COP wind load case system. Define all 24 wind directions (W1-W24) as a WindLoadCase enum. Calculate wind forces for each direction and generate +/- combinations (48 total). Create well-structured load case naming: DL, SDL, LL, W1-W24, E1-E3. Define categories (GRAVITY, WIND, SEISMIC). Generate ULS/SLS combinations per HK Code Table 2.1. Cite HK COP Wind Effects clause numbers. All work in load_combinations.py and data_models.py.

**Task 20.3 prompt (frontend-specialist):**
> Overhaul the load combination UI in app.py. Create a scrollable list with checkboxes for each combination. Group by category (GRAVITY/WIND/SEISMIC) with collapsible sections. Add Select All/None per category. Show selected/total count. Store selection in Streamlit session state.

**Task 20.4 prompt (frontend-specialist):**
> Add "Other" option to the Live Load Class dropdown in app.py. When selected, show a kPa input field. Validate range 0.5-20.0 kPa. Update LoadInput in data_models.py. Apply the custom load to slab loading calculations.

**Task 20.6 prompt (backend-specialist):**
> Remove the "Analysis" load pattern from the FEM model in model_builder.py. Add a "Loading Pattern Factor" input for LL scaling. Apply the factor to live load in combinations. Update load_combinations.py accordingly.

---

*Track Owner: Orchestrator*
*Last Updated: 2026-01-26*
