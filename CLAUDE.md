# PrelimStruct - Claude Code Guidelines

## Project Overview

PrelimStruct is a preliminary structural design tool for tall buildings, targeting Hong Kong market with HK Code 2013 compliance. Currently at v2.1 (preliminary design complete), upgrading to v3.0 (FEM + AI).

### Tech Stack
- **Backend**: Python 3.11+, Pydantic dataclasses
- **UI**: Streamlit dashboard
- **FEM**: OpenSeesPy, ConcreteProperties (with HK2013 extension)
- **Visualization**: Plotly, opsvis/vfo
- **AI**: DeepSeek API
- **Testing**: pytest

### Key Files
- `app.py` - Streamlit dashboard entry point
- `src/core/data_models.py` - Pydantic data models
- `src/engines/` - Design calculation engines (beam, column, slab, lateral)
- `src/fem/` - FEM module (v3.0, in development)
- `src/ai/` - AI assistant module (v3.0, in development)
- `src/report/` - Report generation
- `progress_v3_fem_ai.txt` - Task tracker for v3.0

### Design Code Reference
- "Code of Practice for Structural Use of Concrete 2013 (2020 edition)"
- "Manual for Design and Detailing of Reinforced Concrete to the Code of Practice for Structural Use of Concrete 2013"

---

## Agent System

This project uses specialized agents for different tasks. Each agent has specific guidelines in `.claude/agents/`.

### Available Agents

| Agent | Model | File | Primary Role |
|-------|-------|------|--------------|
| **Plan** | Opus | `.claude/agents/plan.md` | Architecture, task breakdown, feasibility |
| **Coder** | Opus | `.claude/agents/coder.md` | Implementation, core logic, FEM/AI code |
| **UI Expert** | Opus | `.claude/agents/ui.md` | Streamlit, visualization, opsvis/vfo |
| **Code Reviewer** | Haiku | `.claude/agents/reviewer.md` | Code review after every commit |
| **Test** | Haiku | `.claude/agents/test.md` | Test execution, coverage, fixing failures |
| **Documentation** | Haiku | `.claude/agents/docs.md` | Technical documentation when requested |

### Agent Routing

**When to use each agent:**

```
User request about planning/architecture → Plan Agent
User request to implement feature → Coder Agent
User request involving UI/visualization → UI Expert Agent
After any commit → Code Reviewer Agent (automatic)
After implementation complete → Test Agent
User requests documentation → Documentation Agent
```

**Scope boundaries (Coder vs UI Expert):**
- Simple UI changes (add field, update label) → Coder Agent
- Complex UI (new visualizations, layout redesign, opsvis/vfo) → UI Expert Agent

### Agent Handoff Protocol

When completing work, each agent MUST provide:

1. **Context**: What was the task and why
2. **Outcome**: What was accomplished (files changed, tests passing)
3. **Next Steps**: What should be done next
4. **Recommended Agent**: Which agent should continue (if applicable)
5. **Open Issues**: Any blockers or decisions needed

Example handoff:
```
## Handoff Summary

**Context**: Implemented core wall I_SECTION geometry generator (Task 8.1.2)

**Outcome**:
- Created `src/fem/core_wall_geometry.py` with I_SECTION class
- Added unit tests in `tests/test_core_wall_geometry.py`
- All 5 tests passing

**Next Steps**:
- Task 8.1.3 (TWO_C_FACING) ready to start
- UI integration (Task 8.1.8) can begin after 8.1.2-8.1.6 complete

**Recommended Agent**: Code Reviewer (for commit review), then Coder (for 8.1.3)

**Open Issues**: None
```

---

## Code Standards

### Python Style
- Type hints required for all function signatures
- Pydantic dataclasses for data models
- Docstrings for public functions (Google style)
- Max line length: 100 characters

### File Organization
```
src/
├── core/           # Data models, shared utilities
├── engines/        # Design calculation engines
├── fem/            # FEM module (OpenSeesPy, ConcreteProperties)
│   └── design_codes/  # HK2013 and other code implementations
├── ai/             # AI assistant (DeepSeek integration)
└── report/         # Report generation
tests/              # pytest test files
```

### Naming Conventions
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Enums: `PascalCase` with `UPPER_SNAKE_CASE` members

### HK Code References
Always cite clause numbers when implementing code calculations:
```python
# HK Code 2013 Cl 6.1.2.4 - Ultimate concrete stress-strain
# HK Code 2013 Cl 3.1.7 - Modulus of elasticity
```

---

## Current Status (v3.0)

**Phase**: 1 - FEM Core (Features 8-10)
**Focus**: Feature 8 - FEM Foundation Layer
**Next Tasks**:
- Task 8.1.1 - Core Wall Data Models and Enum
- Task 8.4.1 - HK2013 Design Code Class

See `progress_v3_fem_ai.txt` for full task breakdown.
