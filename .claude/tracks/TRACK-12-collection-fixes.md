# Track 12: Collection Error Fixes

> **Created:** 2026-01-30
> **Orchestrator:** Claude Opus 4.5 (Antigravity)
> **Status:** ✅ COMPLETE
> **Priority:** HIGH (Blocks test suite execution)
> **Dependency:** None
> **Estimated Effort:** 30 minutes total

---

## Overview

Three test files have collection errors that prevent the test suite from running cleanly. All errors trace to a single root cause plus one stray file.

---

## Root Cause Analysis

### Error 1 & 2: Missing Import

**Files Affected:**
- `tests/test_ai_model_builder.py`
- `tests/test_integration_e2e.py`

**Error:**
```
ImportError: cannot import name 'MODEL_BUILDER_SYSTEM_PROMPT' from 'src.ai.prompts'
```

**Chain:**
```
tests/test_*.py 
  → imports from src/ai/model_builder_assistant.py
    → imports MODEL_BUILDER_SYSTEM_PROMPT from .prompts
      → prompts.py doesn't export this constant
```

**Root Cause:** `src/ai/prompts.py` is missing `MODEL_BUILDER_SYSTEM_PROMPT` constant.

### Error 3: Stray Test File

**File:** `test_debug.py` (in project root, not tests/)

**Issue:** Scratch/debug file left in project root. Should be deleted or moved.

---

## Tasks

| Order | Task ID | Description | Agent | Category + Skills | Status | Est. |
|-------|---------|-------------|-------|-------------------|--------|------|
| 1 | CE-01 | Add MODEL_BUILDER_SYSTEM_PROMPT to prompts.py | backend-specialist | quick + [clean-code] | ✅ DONE | 15 min |
| 2 | CE-02 | Remove or relocate test_debug.py | - | manual | ✅ DONE | 2 min |
| 3 | CE-03 | Verify all tests collect successfully | test-engineer | quick + [testing-patterns] | ✅ DONE | 5 min |

---

## Task Details

### CE-01: Add MODEL_BUILDER_SYSTEM_PROMPT to prompts.py

**Priority:** CRITICAL
**Agent:** backend-specialist
**Category:** quick
**Skills:** clean-code

**Issue:** `model_builder_assistant.py` imports `MODEL_BUILDER_SYSTEM_PROMPT` but it doesn't exist in `prompts.py`.

**Files:**
- `src/ai/prompts.py` (add constant)
- `src/ai/model_builder_assistant.py` (verify import works)

**Prompt for Agent:**
```
TASK: Add missing MODEL_BUILDER_SYSTEM_PROMPT constant to src/ai/prompts.py

CONTEXT:
- src/ai/model_builder_assistant.py line 31 imports MODEL_BUILDER_SYSTEM_PROMPT from .prompts
- This constant doesn't exist in prompts.py, causing ImportError
- The constant should contain a system prompt for the AI model builder assistant
- Look at model_builder_assistant.py to understand what the prompt needs to do

EXPECTED OUTCOME:
- MODEL_BUILDER_SYSTEM_PROMPT constant added to prompts.py
- Import in model_builder_assistant.py works without error
- pytest --collect-only shows no import errors for these files

MUST DO:
1. Read src/ai/model_builder_assistant.py to understand the assistant's purpose
2. Review existing prompts in prompts.py for style consistency
3. Create appropriate MODEL_BUILDER_SYSTEM_PROMPT constant
4. Verify: python -c "from src.ai.model_builder_assistant import ModelBuilderAssistant"
5. Run: pytest tests/test_ai_model_builder.py --collect-only (should collect tests)

MUST NOT DO:
- Do not modify model_builder_assistant.py import statement
- Do not create a placeholder/empty prompt
- Do not change the structure of prompts.py
```

**Verification:**
```bash
python -c "from src.ai.prompts import MODEL_BUILDER_SYSTEM_PROMPT; print('OK')"
pytest tests/test_ai_model_builder.py --collect-only
pytest tests/test_integration_e2e.py --collect-only
```

---

### CE-02: Remove test_debug.py

**Priority:** LOW
**Agent:** Manual (orchestrator can do this)

**Issue:** `test_debug.py` in project root causes collection error.

**Options:**
1. DELETE the file (if it's scratch/debug code)
2. MOVE to tests/ folder (if it contains valid tests)
3. RENAME to `debug.py` (if it's a utility script)

**Action:** Check file contents, then delete if scratch file.

---

### CE-03: Verify Test Collection

**Priority:** HIGH
**Agent:** test-engineer  
**Category:** quick
**Skills:** testing-patterns

**Prompt for Agent:**
```
TASK: Verify all tests collect successfully after fixes

EXPECTED OUTCOME:
- pytest --collect-only shows 0 errors
- All test files are discovered

MUST DO:
1. Run: pytest --collect-only 2>&1 | tail -5
2. Confirm output shows "X tests collected" with no errors
3. If any remaining errors, report them for further investigation

MUST NOT DO:
- Do not modify any test files
- Do not skip failing collections
```

**Verification:**
```bash
pytest --collect-only 2>&1 | tail -5
# Expected: "XXX tests collected" with no errors
```

---

## Execution Order

1. **CE-01**: Fix the import (unblocks 2 test files)
2. **CE-02**: Remove stray file (unblocks 1 file)
3. **CE-03**: Verify all clear

---

## Success Criteria

- [ ] `pytest --collect-only` shows 0 errors
- [ ] All 900+ tests collected successfully
- [ ] No import errors in any test file

---

*Track created by Orchestrator*
*Date: 2026-01-30*
