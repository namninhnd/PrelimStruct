# PrelimStruct - Claude Code Guidelines

## Project Overview

PrelimStruct is a preliminary structural design platform for tall buildings, targeting the Hong Kong market with HK Code 2013 compliance. The platform provides finite element analysis using OpenSeesPy with AI-assisted modeling and results interpretation.

### Version History
- **v2.1**: Preliminary design calculator (simplified methods)
- **v3.0**: FEM + AI integration (OpenSeesPy, ConcreteProperties, DeepSeek)
- **v3.5**: Pure FEM-based platform (in planning) - see [PRD.md](PRD.md)

### Current Status
- **Version**: 3.0 (stable)
- **Next Version**: 3.5 (planning)
- **Progress Tracker**: [progress_v3_fem_ai.txt](progress_v3_fem_ai.txt)
- **Requirements**: [PRD.md](PRD.md)

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | Python 3.11+ | Core application |
| **Data Models** | Pydantic | Type-safe data classes |
| **UI** | Streamlit | Interactive dashboard |
| **FEM Engine** | OpenSeesPy | Finite element analysis |
| **Section Analysis** | ConcreteProperties | Cross-section capacity |
| **Visualization** | Plotly, opsvis | Interactive charts, FEM views |
| **AI Providers** | DeepSeek, Grok, OpenRouter | LLM integration |
| **Testing** | pytest | Unit and integration tests |

### Dependencies
See [requirements.txt](requirements.txt) for full list.

---

## Project Structure

```
PrelimStruct v3-5/
├── app.py                      # Streamlit dashboard entry point
├── CLAUDE.md                   # This file - AI guidelines
├── PRD.md                      # Product Requirements Document (v3.5)
├── progress_v3_fem_ai.txt      # Task tracker
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Test configuration
│
├── src/
│   ├── core/                   # Core data models and utilities
│   │   ├── data_models.py      # Pydantic models (ProjectData, inputs, results)
│   │   ├── constants.py        # Carbon factors, default values
│   │   └── load_tables.py      # HK Code load tables
│   │
│   ├── engines/                # Design calculation engines
│   │   ├── slab_engine.py      # Slab design (HK Code)
│   │   ├── beam_engine.py      # Beam design (HK Code)
│   │   ├── column_engine.py    # Column design (HK Code)
│   │   ├── wind_engine.py      # Wind/lateral analysis
│   │   ├── coupling_beam_engine.py  # Coupling beam design
│   │   └── punching_shear.py   # Punching shear checks
│   │
│   ├── fem/                    # FEM module (OpenSeesPy integration)
│   │   ├── fem_engine.py       # FEMModel class, element creation
│   │   ├── model_builder.py    # Geometry to FEM conversion
│   │   ├── solver.py           # Analysis solver interface
│   │   ├── visualization.py    # Plan/Elevation/3D views
│   │   ├── core_wall_geometry.py    # Core wall shape generators
│   │   ├── coupling_beam.py    # Coupling beam geometry
│   │   ├── beam_trimmer.py     # Beam trimming at walls
│   │   ├── section_properties.py    # Section property calculator
│   │   ├── load_combinations.py     # ULS/SLS combinations
│   │   ├── results_processor.py     # Post-processing results
│   │   ├── analysis_summary.py      # FEM vs simplified comparison
│   │   ├── sls_checks.py       # Serviceability checks
│   │   ├── materials.py        # OpenSeesPy material helpers
│   │   └── design_codes/
│   │       ├── __init__.py
│   │       └── hk2013.py       # HK Code 2013 ConcreteProperties extension
│   │
│   ├── ai/                     # AI assistant module
│   │   ├── providers.py        # LLM providers (DeepSeek, Grok, OpenRouter)
│   │   ├── config.py           # AI configuration
│   │   ├── prompts.py          # Prompt templates
│   │   ├── llm_service.py      # AIService high-level interface
│   │   ├── response_parser.py  # Structured response parsing
│   │   ├── mesh_generator.py   # Automated mesh generation
│   │   ├── auto_setup.py       # Model setup automation
│   │   ├── optimizer.py        # Design optimization
│   │   └── results_interpreter.py  # AI results interpretation
│   │
│   └── report/
│       └── report_generator.py # HTML report generation
│
├── tests/                      # pytest test files
│   ├── conftest.py             # Test fixtures
│   ├── test_*.py               # Unit and integration tests
│
└── .claude/                    # Claude Code agent configuration
    ├── agents/                 # Specialist agent definitions
    ├── skills/                 # Domain-specific knowledge modules
    ├── workflows/              # Slash command procedures
    ├── rules/                  # Global rules (GEMINI.md)
    └── ARCHITECTURE.md         # Agent system overview
```

---

## Key Files Reference

### Entry Points
| File | Purpose | When to Modify |
|------|---------|----------------|
| `app.py` | Streamlit dashboard | UI changes, visualization updates |
| `src/fem/model_builder.py` | Geometry → FEM | Model structure changes |
| `src/fem/fem_engine.py` | OpenSeesPy operations | Element types, materials |

### Data Models
| File | Contains | When to Modify |
|------|----------|----------------|
| `src/core/data_models.py` | All Pydantic models | New fields, validation rules |

### Design Engines
| File | Calculates | Code Reference |
|------|------------|----------------|
| `src/engines/slab_engine.py` | Slab design | HK Code Cl 6.1, 7.3 |
| `src/engines/beam_engine.py` | Beam design | HK Code Cl 6.1, 6.7 |
| `src/engines/column_engine.py` | Column design | HK Code Cl 6.2 |
| `src/engines/wind_engine.py` | Wind forces | COP Wind Effects 2019 |

### AI Module
| File | Purpose | When to Use |
|------|---------|-------------|
| `src/ai/providers.py` | LLM provider implementations | New providers |
| `src/ai/prompts.py` | Prompt templates | New AI features |
| `src/ai/llm_service.py` | High-level AI interface | AI interactions |

---

## Agent System

This project uses specialized agents for different tasks. Agents are defined in `.claude/agents/`.

### Available Agents

| Agent | Primary Role | Skills |
|-------|--------------|--------|
| `project-planner` | Task breakdown, architecture | brainstorming, plan-writing |
| `backend-specialist` | API, FEM logic, calculations | api-patterns, database-design |
| `frontend-specialist` | Streamlit UI, visualization | react-patterns, frontend-design |
| `debugger` | Root cause analysis | systematic-debugging |
| `test-engineer` | Test writing, coverage | testing-patterns, tdd-workflow |
| `security-auditor` | Security review | vulnerability-scanner |
| `documentation-writer` | Technical docs | documentation-templates |
| `product-manager` | Requirements, user stories | plan-writing, brainstorming |

### Agent Routing

```
Task Type                          → Agent
─────────────────────────────────────────────────────
Planning/architecture              → project-planner
FEM engine, calculations           → backend-specialist
UI changes, visualization          → frontend-specialist
Bug investigation                  → debugger
Test writing                       → test-engineer
Documentation                      → documentation-writer
Requirements clarification         → product-manager
```

### Agent Handoff Protocol

When completing work, provide:
1. **Context**: Task description and why
2. **Outcome**: Files changed, tests passing
3. **Next Steps**: What should follow
4. **Recommended Agent**: Who continues
5. **Open Issues**: Blockers or decisions needed

---

## Code Standards

### Python Style
- **Type hints**: Required for all function signatures
- **Data models**: Pydantic dataclasses
- **Docstrings**: Google style for public functions
- **Line length**: 100 characters max
- **Imports**: Organized (stdlib, third-party, local)

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `beam_engine.py` |
| Classes | PascalCase | `BeamEngine` |
| Functions | snake_case | `calculate_moment()` |
| Constants | UPPER_SNAKE | `MAX_STRESS` |
| Enums | PascalCase/UPPER | `LoadType.DEAD` |

### HK Code References

**Always cite clause numbers when implementing calculations:**

```python
# HK Code 2013 Cl 6.1.2.4 - Ultimate concrete stress-strain
# HK Code 2013 Cl 3.1.7 - Modulus of elasticity
alpha = 0.67  # Stress block coefficient
gamma = 0.45 if fcu <= 60 else ...  # Per Cl 6.1.2.4(b)
```

### Key HK Code Clauses

| Topic | Clause | Used In |
|-------|--------|---------|
| Concrete stress-strain | Cl 6.1.2.4 | `hk2013.py` |
| Elastic modulus | Cl 3.1.7 | `hk2013.py` |
| Flexural tensile strength | Cl 3.1.6.3 | `hk2013.py` |
| Partial safety factors | Cl 2.4.3 | Load combinations |
| Deflection limits | Cl 7.3.1.2 | SLS checks |
| Drift limits | Cl 7.3.2 | Lateral analysis |
| Deep beams | Cl 6.7 | Coupling beams |
| Minimum reinforcement | Cl 9.2.1.1 | All members |

---

## FEM Module Architecture

### Model Building Pipeline

```
ProjectData
    │
    ▼
model_builder.py
    ├── Create nodes (floor-based numbering)
    ├── Create beam elements
    ├── Create column elements
    ├── Apply boundary conditions (fixed base)
    ├── Apply loads (gravity, wind)
    └── Create rigid diaphragms
    │
    ▼
FEMModel (fem_engine.py)
    │
    ▼
solver.py (OpenSeesPy analysis)
    │
    ▼
results_processor.py
    │
    ▼
visualization.py (Plan, Elevation, 3D views)
```

### Core Wall Configurations

| Type | Class | Description |
|------|-------|-------------|
| I_SECTION | `ISectionCoreWall` | Two walls blended |
| TWO_C_FACING | `TwoCFacingCoreWall` | Facing C-shapes |
| TWO_C_BACK_TO_BACK | `TwoCBackToBackCoreWall` | Back-to-back |
| TUBE_CENTER_OPENING | `TubeCenterOpeningCoreWall` | Box with center door |
| TUBE_SIDE_OPENING | `TubeSideOpeningCoreWall` | Box with side door |

---

## AI Module Architecture

### Provider Hierarchy

```
LLMProvider (abstract)
    │
    ├── DeepSeekProvider (PRIMARY)
    ├── GrokProvider (BACKUP)
    └── OpenRouterProvider (FALLBACK)
```

### AI Service Flow

```
User Request
    │
    ▼
AIService.chat() / get_design_review()
    │
    ├── Select prompt template (prompts.py)
    ├── Call provider.chat()
    ├── Parse response (response_parser.py)
    └── Return structured result
```

### Prompt Templates

| Template | Purpose | Output Format |
|----------|---------|---------------|
| DESIGN_REVIEW | Design assessment | JSON (DesignReviewResponse) |
| RESULTS_INTERPRETATION | FEM analysis | Text summary |
| OPTIMIZATION | Cost/performance | JSON (OptimizationResponse) |
| MODEL_SETUP | FEM recommendations | Text guidance |

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_fem_engine.py

# Run marked tests
pytest -m "not slow"
```

### Test Organization

| File | Tests | Coverage |
|------|-------|----------|
| `test_ai_providers.py` | 68 | LLM providers |
| `test_fem_engine.py` | 45 | FEM model operations |
| `test_model_builder.py` | 33 | Geometry conversion |
| `test_visualization_*.py` | 42 | Plan/Elevation/3D views |
| `test_hk2013_design_code.py` | 31 | HK Code materials |
| `test_ai_integration.py` | 20 | End-to-end AI workflows |

### Test Markers

```python
@pytest.mark.slow      # Long-running tests
@pytest.mark.integration  # Integration tests
```

---

## Environment Variables

### Required for AI Features

```env
# Primary provider (required)
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com  # or reseller URL

# Backup providers (optional)
GROK_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here

# Configuration
LLM_PROVIDER=deepseek  # deepseek | grok | openrouter
LLM_MODEL=deepseek-v3.2
LLM_TIMEOUT=60
LLM_MAX_RETRIES=3
```

### Example .env File

See [.env.example](.env.example) for template.

---

## V3.5 Planning Reference

### Key Upgrade Points

1. **FEM-Only**: Remove simplified methods entirely
2. **Shell Elements**: Walls (ShellMITC4 + Plate Fiber Section), Slabs (ShellMITC4)
3. **Wind Loads**: 24 cases per HK COP (48 combinations)
4. **UI Overhaul**: FEM views prominent, display options below
5. **AI Chat**: Model building assistant
6. **Reaction Export**: View and export reaction table for all base nodes and load cases

### Full Requirements

See [PRD.md](PRD.md) for complete Feature → Task → Sub-task breakdown.

### Progress Tracking

See [progress_v3_fem_ai.txt](progress_v3_fem_ai.txt) for task status.

---

## Quick Commands

### Development

```bash
# Run dashboard
streamlit run app.py

# Run tests
pytest

# Type check
mypy src/

# Format code
black src/ tests/
```

### AI Testing

```bash
# Test AI providers
pytest tests/test_ai_providers.py -v

# Test with real API (requires keys)
pytest tests/test_ai_integration.py -m "not slow"
```

---

## Common Tasks

### Adding a New Element Type

1. Create element class in `src/fem/`
2. Add to `FEMModel` in `fem_engine.py`
3. Update `model_builder.py` to generate element
4. Add visualization in `visualization.py`
5. Write unit tests

### Adding a New Load Combination

1. Add to `LoadCombination` enum in `data_models.py`
2. Define factors in `load_combinations.py`
3. Update UI in `app.py` (load combination selector)
4. Add tests

### Adding a New AI Feature

1. Create prompt template in `prompts.py`
2. Add response dataclass in `response_parser.py`
3. Add method to `AIService` in `llm_service.py`
4. Integrate in `app.py` or other consumer
5. Add tests

---

## References

### HK Codes
- Code of Practice for Structural Use of Concrete 2013 (2020 edition)
- Manual for Design and Detailing of Reinforced Concrete to the Code of Practice for Structural Use of Concrete 2013
- Code of Practice on Wind Effects in Hong Kong 2019

### OpenSees Documentation
- OpenSeesPy: https://openseespydoc.readthedocs.io/
- opsvis: https://opsvis.readthedocs.io/
- ShellMITC4: https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
- Shell Element (wiki): https://opensees.berkeley.edu/wiki/index.php/Shell_Element
- Plate Fiber Section: https://opensees.berkeley.edu/wiki/index.php?title=Plate_Fiber_Section
- NDMaterial Command: https://opensees.berkeley.edu/wiki/index.php?title=NDMaterial_Command
- SurfaceLoad Element: https://opensees.berkeley.edu/wiki/index.php/SurfaceLoad_Element
- BuildingTcl (model flow): https://opensees.berkeley.edu/wiki/index.php?title=Getting_Started_with_BuildingTcl

### ConcreteProperties
- https://github.com/robbievanleeuwen/concrete-properties

---

*Last Updated: 2026-01-24*
*Version: 3.0 (targeting 3.5)*
