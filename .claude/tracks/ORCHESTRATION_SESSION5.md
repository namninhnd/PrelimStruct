# PrelimStruct V3.5 - Session 5 Orchestration Plan

> **Session Start:** 2026-01-30 09:21
> **Orchestrator:** Claude Opus 4.5 (Antigravity)
> **Status:** TRACK 12 COMPLETE
> **Mode:** Sequential execution (one task globally)
> **Role:** Orchestration ONLY - no self-implementation

---

## Session Context

### Prior Session Status (Session 4 - 2026-01-29)
- **Tracks 1-10**: All COMPLETE
- **Final Status**: "READY FOR RELEASE"
- **Test Results**: 956 passed, 10 skipped (core tests)
- **Known Issues**: 3 collection errors, coverage gaps

### Current Observations
```
Test Collection: 926 tests collected, 3 errors
Error Files:
- test_debug.py (collection error)
- tests/test_ai_model_builder.py (collection error)  
- tests/test_integration_e2e.py (collection error)
```

---

## Available Tracks

### Active Tracks (Carrying Forward)

| Track | Status | Description |
|-------|--------|-------------|
| Track 11 | NOT STARTED | Coverage Improvements (Optional) |

### New Tracks to Create

Based on analysis of remaining work:

| Track | Priority | Description |
|-------|----------|-------------|
| Track 12 | HIGH | Collection Error Fixes |
| Track 13 | MEDIUM | Documentation Updates (README for V3.5) |
| Track 14 | LOW | Benchmark Validation (ETABS comparison) |

---

## Execution Strategy

### Phase A: Fix Critical Issues
1. **Track 12**: Fix 3 collection errors (blocking tests from running)

### Phase B: Quality Polish (Optional)
2. **Track 11**: Coverage improvements (time permitting)
3. **Track 13**: Documentation updates

### Phase C: Validation
4. **Track 14**: Benchmark validation against ETABS

---

## Track Creation Status

| Track | File | Status |
|-------|------|--------|
| Track 11 | TRACK-11-coverage-improvements.md | EXISTS |
| Track 12 | TRACK-12-collection-fixes.md | TO CREATE |
| Track 13 | TRACK-13-documentation.md | TO CREATE |
| Track 14 | TRACK-14-benchmark.md | TO CREATE |

---

## Next Actions

1. ~~Investigate collection errors (debug what's broken)~~ ✅ DONE
2. ~~Create Track 12 with fix plan~~ ✅ DONE
3. **Execute Track 12 sequentially** ← CURRENT
4. Then proceed to Track 11 if requested

---

## Collection Error Root Cause

| Error File | Root Cause | Fix |
|------------|------------|-----|
| `tests/test_ai_model_builder.py` | Missing `MODEL_BUILDER_SYSTEM_PROMPT` in prompts.py | CE-01 |
| `tests/test_integration_e2e.py` | Same import chain failure | CE-01 |
| `test_debug.py` (root) | Scratch file - not a test | CE-02 (delete) |

---

## Track 12 Execution Plan

| Order | Task | Agent | Status |
|-------|------|-------|--------|
| 1 | CE-01: Add MODEL_BUILDER_SYSTEM_PROMPT | backend-specialist | PENDING |
| 2 | CE-02: Delete test_debug.py | manual | PENDING |
| 3 | CE-03: Verify collection | test-engineer | PENDING |

---

*Session 5 Orchestration initialized*
*Date: 2026-01-30*
*Updated: 2026-01-30 09:30*
