# Track 7: AI Chat Assistant

> **Priority:** P1 (SHOULD)
> **Start Wave:** 2 (Backend), Wave 2-3 (Frontend)
> **Primary Agents:** backend-specialist, frontend-specialist
> **Status:** PENDING

---

## Overview

Add an AI chat interface above Project Settings that helps users build FEM models through natural language conversation. The AI extracts building parameters, suggests configurations, and applies them to the UI.

---

## External Dependencies

| Dependency | Track | Task | Reason |
|------------|-------|------|--------|
| Dashboard cleaned up | Track 6 | 16.2 | Need stable app.py layout before adding chat |
| Existing AI module | N/A | Already exists | Build on src/ai/ providers, prompts |

**Note:** This track has LOW coupling to the FEM backend tracks. The AI chat can be developed against the existing ProjectData model and adapted later when new features (walls, slabs, loads) are integrated.

---

## Tasks

### Task 22.1: AI Chat Interface Component
**Agent:** frontend-specialist
**Model:** sonnet
**Wave:** 2-3 (After 16.2)
**Dependencies:** Track 6 (16.2 complete)
**Status:** PENDING

**Sub-tasks:**
- [ ] 22.1.1: Create chat container above Project Settings
- [ ] 22.1.2: Implement message history display
- [ ] 22.1.3: Add text input with send button
- [ ] 22.1.4: Style chat bubbles (user vs AI)
- [ ] 22.1.5: Add typing indicator during AI response
- [ ] 22.1.6: Implement auto-scroll to latest message

**Files Impacted:**
- `app.py` (new section above Project Settings)

**Verification:**
- Chat container appears above Project Settings
- Messages display correctly
- Send button triggers AI response

---

### Task 22.2: AI Model Builder Backend
**Agent:** backend-specialist
**Model:** opus
**Wave:** 2 (Can start early - independent module)
**Dependencies:** Minimal (existing AI infrastructure)
**Status:** PENDING

**Sub-tasks:**
- [ ] 22.2.1: Create `ModelBuilderAssistant` class in `src/ai/`
- [ ] 22.2.2: Design prompts for building parameter extraction
- [ ] 22.2.3: Implement intent detection (describe building, ask question, modify parameter)
- [ ] 22.2.4: Create parameter validation and suggestion logic
- [ ] 22.2.5: Generate configuration from conversation
- [ ] 22.2.6: Integrate with existing `AIService`

**Files Impacted:**
- `src/ai/model_builder_assistant.py` (NEW)
- `src/ai/prompts.py` (new templates)
- `src/ai/llm_service.py` (integration)
- `tests/test_ai_model_builder.py` (NEW)

**Verification:**
- AI extracts parameters from natural language
- Suggestions are valid and code-compliant
- Configuration generates correctly

---

### Task 22.3: Model Configuration from Chat
**Agent:** backend-specialist
**Model:** sonnet
**Wave:** 4 (After 22.2)
**Dependencies:** Task 22.2
**Status:** PENDING

**Sub-tasks:**
- [ ] 22.3.1: Map extracted parameters to `ProjectData` fields
- [ ] 22.3.2: Apply configuration to UI inputs
- [ ] 22.3.3: Preview configuration before applying
- [ ] 22.3.4: Allow user confirmation/modification
- [ ] 22.3.5: Handle partial configurations (fill defaults)

**Files Impacted:**
- `src/ai/model_builder_assistant.py`
- `app.py` (configuration preview + apply)
- `src/core/data_models.py` (mapping validation)

**Verification:**
- AI configuration populates UI fields
- User can preview and confirm
- Partial configs handled gracefully

---

## Internal Dependency Chain

```
22.2 (AI backend) ──> 22.3 (Config from chat)
22.1 (Chat UI) ──────────────┘ (UI + backend integrate)
```

**Parallelism:** 22.1 (frontend) and 22.2 (backend) can run in parallel - different files entirely.

---

## Cross-Track Dependencies

| This Track Produces | Required By |
|---------------------|-------------|
| 22.1 + 22.2 + 22.3 complete | Track 8: 23.2 (AI chat integration test) |

| This Track Requires | From Track |
|---------------------|------------|
| 16.2 complete (clean dashboard) | Track 6 |
| ProjectData model stable | Track 1 (16.1) |

---

## Agent Instructions

**Task 22.2 prompt (backend-specialist):**
> Create a ModelBuilderAssistant class in src/ai/model_builder_assistant.py. This class uses the existing AIService to chat with users about their building and extract structural parameters. Implement intent detection (describe building, ask question, modify parameter), parameter validation, and configuration generation. Design prompt templates for building parameter extraction. Integrate with the existing LLM providers in src/ai/providers.py. Write comprehensive tests.

**Task 22.1 prompt (frontend-specialist):**
> Create an AI chat interface in app.py, positioned above the Project Settings section. Implement a chat container with message history (user vs AI bubbles), text input with send button, typing indicator, and auto-scroll. Use Streamlit session state for message history. Style user messages and AI messages differently.

**Task 22.3 prompt (backend-specialist):**
> Extend the ModelBuilderAssistant to map extracted parameters to ProjectData fields. When the AI generates a configuration, show a preview in the UI before applying. Allow user to confirm or modify. Handle partial configurations by filling reasonable defaults. Integrate the apply-to-UI flow in app.py.

---

*Track Owner: Orchestrator*
*Last Updated: 2026-01-26*
