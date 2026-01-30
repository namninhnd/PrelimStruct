# PrelimStruct V3.5 - Master Orchestration Plan

> **Generated:** 2026-01-26
> **Last Updated:** 2026-01-29 12:55
> **Status:** IN PROGRESS ✅ REGRESSIONS RESOLVED
> **Execution Mode:** SEQUENTIAL (one task globally, token-efficient)
> **Tracks:** 9 work streams
> **Waves:** 6 execution waves + 1 regression wave (COMPLETE)
> **Models:** Claude Opus (complex) | Claude Sonnet (medium) | Gemini 3 Pro (simple)
> **Code Review:** Gemini 3 Pro (after each task)
> **Orchestrator:** Claude Opus 4.5 (coordination only, no implementation)

---

## 🎯 EXECUTION QUEUE (ACTIVE)

| # | Task ID | Description | Agent | Model | Track | Status |
|---|---------|-------------|-------|-------|-------|--------|
| ~~1~~ | ~~TD-01~~ | ~~Fix check_combined_load crash~~ | ~~debugger~~ | ~~sonnet~~ | ~~9~~ | ✅ DONE |
| ~~2~~ | ~~21.1~~ | ~~Relocate FEM views section~~ | ~~frontend-specialist~~ | ~~sonnet~~ | ~~6~~ | ✅ DONE |
| ~~3~~ | ~~20.3~~ | ~~Load combination UI overhaul~~ | ~~frontend-specialist~~ | ~~sonnet~~ | ~~5~~ | ✅ DONE |
| ~~4~~ | ~~20.4~~ | ~~Custom live load input~~ | ~~frontend-specialist~~ | ~~gemini~~ | ~~5~~ | ✅ DONE |
| **5** | **20.6** | **Remove analysis load pattern** | **backend-specialist** | **gemini** | **5** | **🔄 NEXT** |
| 3 | 20.3 | Load combination UI overhaul | frontend-specialist | sonnet | 5 | QUEUED |
| 4 | 20.4 | Custom live load input | frontend-specialist | gemini | 5 | QUEUED |
| 5 | 20.6 | Remove analysis load pattern | backend-specialist | gemini | 5 | QUEUED |
| 6 | 21.5 | Switch to opsvis from vfo | backend-specialist | sonnet | 6 | QUEUED |
| 7 | 21.2 | Conditional utilization display | frontend-specialist | gemini | 6 | QUEUED |
| 8 | 21.3 | Independent axis scale controls | frontend-specialist | gemini | 6 | QUEUED |
| 9 | 21.6 | Display options panel | frontend-specialist | sonnet | 6 | QUEUED |
| 10 | 21.4 | Calculation tables toggle | frontend-specialist | sonnet | 6 | QUEUED |
| 11 | 21.7 | Reaction table view + export | frontend-specialist | sonnet | 6 | QUEUED |
| 12 | 22.1 | AI chat interface component | frontend-specialist | sonnet | 7 | QUEUED |
| 13 | 22.2 | AI model builder backend | backend-specialist | opus | 7 | QUEUED |
| 14 | 22.3 | Model config from chat | backend-specialist | sonnet | 7 | QUEUED |
| 15 | TD-02 | WallPanel base_point type fix | backend-specialist | gemini | 9 | QUEUED |
| 16 | TD-03 | app.py type annotations | backend-specialist | gemini | 9 | QUEUED |
| 17 | TD-04 | Deprecated code cleanup | backend-specialist | gemini | 9 | QUEUED |
| 18 | 23.1 | Unit tests for new features | test-engineer | sonnet | 8 | QUEUED |
| 19 | 23.2 | Integration tests | test-engineer | sonnet | 8 | QUEUED |
| 20 | 23.3 | Benchmark validation | test-engineer | opus | 8 | QUEUED |
| 21 | TD-05 | FEM-based moment frame tests | test-engineer | sonnet | 9 | QUEUED |

**Legend:** 🔄 NEXT = Dispatching now | ⏳ IN_PROGRESS | ✅ DONE | ❌ BLOCKED

---

## Dependency Graph

```
WAVE 0 (Immediate - No Dependencies)
  Track 1: [16.1] Architecture cleanup ──────────────────────┐
  Track 2: [17.4] + [18.1] Bug fixes (parallel) ────────────┤
                                                              │
WAVE 1 (After 16.1 completes)                                │
  Track 1: [16.3] Model flow reorganize ─────────────────────┤
  Track 6: [16.2] Dashboard FEM-only ───────────────────┐    │
  Track 2: [18.2] Beam visualization (after 18.1) ──────┤    │
                                                         │    │
WAVE 2 (After 16.3 completes - BIG WAVE)                 │    │
  Track 3: [17.1] Wall elements ─────────────────────────┤    │
  Track 5: [20.1]+[20.2] Load definitions ──────────┐   │    │
  Track 6: [21.5] opsvis switch ────────────────┐   │   │    │
  Track 7: [22.2] AI backend ──────────────┐    │   │   │    │
  Track 3: [17.2] Wall location UI ────────┤    │   │   │    │
  Track 7: [22.1] AI chat UI ─────────────┤    │   │   │    │
                                           │    │   │   │    │
WAVE 3 (After 17.1 / 20.1+20.2 complete)  │    │   │   │    │
  Track 3: [17.3] Auto-omit columns ──────┤    │   │   │    │
  Track 4: [19.1] Slab elements ───────────┤    │   │   │    │
  Track 5: [20.6] Remove analysis pattern  │    │   │   │    │
  Track 5: [20.3] Load combo UI ──────────┤    │   │   │    │
  Track 5: [20.4] Custom live load UI ────┤    │   │   │    │
  Track 6: [21.1] Relocate FEM views ─────┤    │   │   │    │
                                           │    │   │   │    │
WAVE 4 (After 19.1, 21.5 complete)        │    │   │   │    │
  Track 4: [19.2] Slab panel detection ───┤    │   │   │    │
  Track 4: [20.5] Surface load on slabs ──┤    │   │   │    │
  Track 6: [21.6] Display options panel ──┤    │   │   │    │
  Track 6: [21.2]+[21.3] Utilization+Axis ┤    │   │   │    │
  Track 7: [22.3] Model config from chat ─┤    │   │   │    │
                                           │    │   │   │    │
WAVE 5 (After Waves 3-4 settle)           │    │   │   │    │
  Track 4: [19.3] Slab visualization ─────┤    │   │   │    │
  Track 6: [21.4] Calculation tables ─────┤    │   │   │    │
  Track 6: [21.7] Reaction table ─────────┤    │   │   │    │
                                           │    │   │   │    │
WAVE 6 (After all implementation)          │    │   │   │    │
  Track 8: [23.1] Unit tests ─────────────┤    │   │   │    │
  Track 8: [23.2] Integration tests ──────┤    │   │   │    │
  Track 8: [23.3] Benchmark validation ───┘    │   │   │    │
```

---

## Track Summary

| Track | Name | Tasks | Agent(s) | Start Wave | Critical? | Model |
|-------|------|-------|----------|------------|-----------|-------|
| 1 | Architecture Foundation | 16.1, 16.3 | backend-specialist | 0 | YES | ✅ DONE |
| 2 | Bug Fixes | 17.4, 18.1, 18.2 | debugger, frontend-specialist | 0 | NO | ✅ DONE |
| 3 | Wall Modeling | 17.1, 17.2, 17.3, R1-R4 | backend-specialist, frontend-specialist, debugger | 2 | YES | ✅ COMPLETE |
| 4 | Slab Modeling | 19.1, 19.2, 19.3, 20.5, 20.5a | backend-specialist, frontend-specialist | 3 | YES | ✅ DONE |
| 5 | Load System | 20.1, 20.2, 20.3, 20.4, 20.6 | backend-specialist, frontend-specialist | 2 | YES | ⏳ PENDING (20.3+) |
| 6 | UI/UX Overhaul | 16.2, 21.1-21.7 | frontend-specialist, backend-specialist | 1 | NO | ✅ 16.2 DONE |
| 7 | AI Chat | 22.1, 22.2, 22.3 | frontend-specialist, backend-specialist | 2 | NO | ⏳ PENDING |
| 8 | Testing & QA | 23.1, 23.2, 23.3 | test-engineer | 6 | YES | ⏳ PENDING |
| 9 | Technical Debt | TD-01 to TD-05 | debugger, backend-specialist | Immediate | YES (TD-01) | ⏳ PENDING |

---

## File Conflict Analysis

### Critical Shared Files

| File | Tracks That Modify | Conflict Risk | Mitigation |
|------|-------------------|---------------|------------|
| `src/fem/model_builder.py` | 1, 3, 4 | HIGH | Sequence: Track 1 -> Track 3 -> Track 4 |
| `app.py` | 2, 5, 6, 7 | HIGH | Frontend tasks sequenced through Track 6 pipeline |
| `src/fem/load_combinations.py` | 5 | LOW | Single track owns this file |
| `src/fem/visualization.py` | 2, 4, 6 | MEDIUM | Coordinate 18.2, 19.3, 21.5/21.6 |
| `src/core/data_models.py` | 1, 3, 4, 5 | MEDIUM | Changes are additive (new fields), low conflict |
| `src/ai/` module | 7 | LOW | Single track owns AI files |
| `requirements.txt` | 6 | LOW | Single change (opsvis) |

### Safe Parallelism (Different Files)

These track pairs can safely run in parallel:

| Parallel Pair | Reason |
|---------------|--------|
| Track 1 + Track 2 | 16.1 touches engines/, 17.4/18.1 touch fem/ bugs |
| Track 3 + Track 5 | 17.1 = wall_element.py, 20.1 = load_combinations.py |
| Track 3 + Track 7 | wall_element.py vs src/ai/ |
| Track 5 + Track 7 | load_combinations.py vs src/ai/ |
| Track 6 (21.5) + Track 3 | visualization.py vs wall_element.py |
| Track 6 (app.py tasks) + any backend track | app.py vs src/ modules |

### Dangerous Parallelism (Same Files)

These MUST be sequenced:

| Conflict | Reason |
|----------|--------|
| Track 3 then Track 4 | Both modify model_builder.py |
| Track 1 before Track 3 | 16.3 restructures model_builder.py first |
| Track 6 (16.2) before Track 6 (21.1) | Sequential app.py restructure |

---

## Wave Execution Plan

### Wave 0: Immediate Dispatch
**Agents needed:** 2 (backend-specialist + debugger)

| Agent | Task | Track | Files | Model |
|-------|------|-------|-------|-------|
| backend-specialist | 16.1: Remove simplified method code | Track 1 | src/engines/, data_models.py | gemini-3-pro |
| debugger | 17.4: Fix coupling beam error | Track 2 | src/fem/coupling_beam.py | sonnet |
| debugger | 18.1: Debug secondary beam generation | Track 2 | src/fem/model_builder.py (read-only investigation) | sonnet |

**Note:** 17.4 and 18.1 are independent bugs. Can use one debugger agent for both sequentially, or two in parallel.

**Gate:** Wave 1 starts when 16.1 completes.

---

### Wave 1: After 16.1
**Agents needed:** 2 (backend-specialist + frontend-specialist)

| Agent | Task | Track | Files | Model |
|-------|------|-------|-------|-------|
| backend-specialist | 16.3: Reorganize model flow | Track 1 | model_builder.py, fem_engine.py | opus |
| frontend-specialist | 16.2: Update dashboard FEM-only | Track 6 | app.py | gemini-3-pro |
| frontend-specialist | 18.2: Update beam visualization | Track 2 | visualization.py (after 18.1 done) | gemini-3-pro |

**Gate:** Wave 2 starts when 16.3 completes.

---

### Wave 2: After 16.3 (Big Wave)
**Agents needed:** 3-4 (backend x2-3, frontend x1)

| Agent | Task | Track | Files | Model |
|-------|------|-------|-------|-------|
| backend-specialist | 17.1: ShellMITC4 wall elements | Track 3 | wall_element.py (new), model_builder.py | opus |
| backend-specialist | 20.1 + 20.2: Wind cases + load structure | Track 5 | load_combinations.py | gemini-3-pro |
| backend-specialist | 21.5: Switch to opsvis | Track 6 | visualization.py, requirements.txt | sonnet |
| backend-specialist | 22.2: AI model builder backend | Track 7 | src/ai/ | opus |
| frontend-specialist | 17.2: Custom core wall location UI | Track 3 | app.py (sidebar section) | gemini-3-pro |
| frontend-specialist | 22.1: AI chat interface | Track 7 | app.py (new section above settings) | sonnet |

**Note:** Backend tasks are on DIFFERENT files - safe to parallel. Frontend tasks both touch app.py but different sections - coordinate carefully or sequence.

**Gate:** Wave 3 starts when 17.1 and 20.1+20.2 complete.

---

### Wave 3: After 17.1 + Load Definitions
**Agents needed:** 2-3

| Agent | Task | Track | Files | Model |
|-------|------|-------|-------|-------|
| backend-specialist | 17.3: Auto-omit columns near walls | Track 3 | model_builder.py | sonnet |
| backend-specialist | 19.1: ShellMITC4 slab elements | Track 4 | slab_element.py (new), model_builder.py | opus |
| backend-specialist | 20.6: Remove analysis load pattern | Track 5 | model_builder.py, load_combinations.py | gemini-3-pro |
| frontend-specialist | 20.3: Load combination UI | Track 5 | app.py | sonnet |
| frontend-specialist | 20.4: Custom live load input | Track 5 | app.py | gemini-3-pro |
| frontend-specialist | 21.1: Relocate FEM views | Track 6 | app.py | sonnet |

**WARNING:** 17.3, 19.1, 20.6 all touch model_builder.py. Sequence: 17.3 first, then 19.1, then 20.6. Or dispatch 19.1 only after 17.3 completes.

**Gate:** Wave 4 starts when 19.1 completes.

---

### Wave 4: After Slab Elements + opsvis
**Agents needed:** 2-3

| Agent | Task | Track | Files | Model |
|-------|------|-------|-------|-------|
| backend-specialist | 19.2: Slab panel detection | Track 4 | model_builder.py | opus |
| backend-specialist | 20.5: Surface load on slabs | Track 4 | model_builder.py, load_combinations.py | sonnet |
| backend-specialist | 22.3: Model config from chat | Track 7 | src/ai/ | sonnet |
| frontend-specialist | 21.6: Display options panel | Track 6 | app.py (after 21.5) | sonnet |
| frontend-specialist | 21.2 + 21.3: Utilization + axis scales | Track 6 | app.py | gemini-3-pro |

**Note:** 19.2 and 20.5 both touch model_builder.py - sequence 19.2 first.

---

### Wave 5: Finalization
**Agents needed:** 1-2

| Agent | Task | Track | Files | Model |
|-------|------|-------|-------|-------|
| frontend-specialist | 19.3: Slab visualization | Track 4 | visualization.py | sonnet |
| frontend-specialist | 21.4: Calculation tables | Track 6 | app.py | sonnet |
| frontend-specialist | 21.7: Reaction table view + export | Track 6 | app.py | sonnet |

---

### Wave 6: Testing & QA
**Agents needed:** 1

| Agent | Task | Track | Files | Model |
|-------|------|-------|-------|-------|
| test-engineer | 23.1: Unit tests for new features | Track 8 | tests/ | sonnet |
| test-engineer | 23.2: Integration tests | Track 8 | tests/ | sonnet |
| test-engineer | 23.3: Benchmark validation | Track 8 | tests/ | opus |

---

## Critical Path

```
16.1 -> 16.3 -> 17.1 -> 19.1 -> 19.2 -> 19.3
                  |                 |
                  +-> 17.3          +-> 20.5
                                    |
                                    +-> 23.1 -> 23.2 -> 23.3
```

The critical path runs through: Architecture -> Wall Elements -> Slab Elements -> Testing

Any delay on Track 1 or Track 3 delays the entire project.

---

## Agent Utilization Summary

| Agent | Wave 0 | Wave 1 | Wave 2 | Wave 3 | Wave 4 | Wave 5 | Wave 6 |
|-------|--------|--------|--------|--------|--------|--------|--------|
| backend-specialist | 16.1 | 16.3 | 17.1, 20.1/2, 21.5, 22.2 | 17.3, 19.1, 20.6 | 19.2, 20.5, 22.3 | - | - |
| frontend-specialist | - | 16.2, 18.2 | 17.2, 22.1 | 20.3, 20.4, 21.1 | 21.6, 21.2/3 | 19.3, 21.4, 21.7 | - |
| debugger | 17.4, 18.1 | - | - | - | - | - | - |
| test-engineer | - | - | - | - | - | - | 23.1-3 |

---

## Status Key

- `PENDING` - Not started, waiting for dependencies
- `READY` - Dependencies met, ready for dispatch
- `IN_PROGRESS` - Agent dispatched, work underway
- `REVIEW` - Work complete, needs verification
- `DONE` - Verified and merged
- `BLOCKED` - Unexpected dependency or issue

---

*Orchestrator: Claude Opus 4.5*
*Last Updated: 2026-01-29*

---

## REGRESSION WAVE (Priority - Before Wave 3 continues)

> [!CAUTION]
> 4 regressions discovered during Task 17.2 testing. **ALL RESOLVED (2026-01-29)**

| # | Issue | Agent | Priority | Status |
|---|-------|-------|----------|--------|
| R4 | Custom position not working | debugger | P0 | ✅ DONE |
| R2 | Missing coupling beams | backend-specialist | P0 | ✅ DONE |
| R1 | Beams not trimmed at walls | backend-specialist | P1 | ✅ DONE |
| R3 | Slab gaps near walls | backend-specialist | P1 | ✅ NO ISSUE |

**Summary:**
- R4: Fixed variable pass issue in app.py (custom X/Y not passed to LateralInput)
- R2: Added CouplingBeamGenerator call in build_fem_model() 
- R1: Added beam trimming for secondary beams (not just primary)
- R3: Investigation confirmed no gap issue - slabs correctly extend to walls

**Bonus:** Fixed 23 test synchronization issues (enum renames, trace name changes)
