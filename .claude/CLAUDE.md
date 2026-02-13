# PrelimStruct Agent Operating Guide

> **Canonical Source Statement**: This CLAUDE.md is the single source of truth for agent operating policy in the PrelimStruct root project.

---

## Scope

### Governance Boundary

This document governs all operations within the **PrelimStruct root project**.

**IN SCOPE:**
- Root project directory: `C:\Users\daokh\Desktop\PrelimStruct v3-5`
- All modules under `src/` (core, engines, fem, ai, ui, report)
- All test files under `tests/`
- Configuration files at root (pytest.ini, requirements.txt, .env.example)
- Documentation files at root (README.md, progress_v3_fem_ai.txt)

**EXPLICITLY OUT OF SCOPE:**
- `repos/*` directory and all nested repositories within it
- External dependencies in virtual environments
- Generated artifacts (reports, screenshots, cached data)
- Any subdirectories under `repos/` are governed by their own local CLAUDE.md or AGENTS.md files

---

## Instruction Precedence

Instructions are resolved in the following priority order (highest to lowest):

| Priority | Source |
|----------|--------|
| 1 | System/Developer Instructions - Direct user prompts and system-level directives |
| 2 | Root CLAUDE.md - This file's policies and constraints |
| 3 | Local Context Documents - Files in `.sisyphus/` notepads and plan files |
| 4 | Task-Specific Prompts - Inline prompts within task definitions |

**Tie-Break Rule:** When two instructions at the same precedence level conflict, the **more specific** instruction wins. Specificity is determined by:
- Scope narrowing (file-specific > module-specific > project-wide)
- Recency (newer > older, for local context docs)
- Detail level (concrete constraints > general guidelines)

---

## Agent Categories

| Category | Purpose |
|----------|---------|
| **backend** | API integration, service implementations, data processing |
| **visual-engineering** | UI/UX implementation, Streamlit widgets, dashboard components |
| **deep** | Complex investigation, debugging, FEM analysis, solver issues |
| **quick** | Fast iterations, test maintenance, minor fixes |
| **writing** | Documentation, reports, markdown updates |
| **unspecified-low** | Safe defaults for ambiguous Python tasks |

---

## Skill Bundles

| Bundle Name | Skills | Use When |
|-------------|--------|----------|
| **Python Core** | `python-patterns`, `clean-code` | Any Python file modification |
| **FEM Development** | `python-patterns`, `systematic-debugging`, `clean-code` | OpenSeesPy, solver, force handling |
| **AI Integration** | `api-patterns`, `python-patterns`, `clean-code` | LLM providers, prompts, responses |
| **Testing** | `testing-patterns`, `clean-code` | pytest, fixtures, test design |
| **UI Work** | `streamlit`, `frontend-design`, `clean-code` | Streamlit widgets, layouts, state |
| **E2E Testing** | `playwright`, `webapp-testing` | Browser automation, screenshots |
| **Documentation** | `documentation-templates`, `clean-code` | README, markdown, reports |
| **HK Code Work** | `python-patterns`, `clean-code` | Design code compliance, calculations |

---

## Usage Triggers

### Domain Routing Matrix

| Domain | Files | Category | Skills | Trigger Keywords |
|--------|-------|----------|--------|------------------|
| **FEM debugging** | `src/fem/**`, `tests/test_fem*.py` | `deep` | `python-patterns`, `systematic-debugging`, `clean-code` | OpenSeesPy, fem, solver, force normalization, diaphragm, rigidDiaphragm, localForce, element, node, ops. |
| **AI provider integration** | `src/ai/**`, `tests/test_ai*.py` | `backend` | `api-patterns`, `python-patterns`, `clean-code` | DeepSeek, Grok, OpenRouter, LLM, prompt, provider, httpx, AI assistant |
| **Test maintenance** | `tests/**` | `quick` | `testing-patterns`, `clean-code` | pytest, fixture, marker, test_, @pytest.mark |
| **Streamlit UI development** | `src/ui/**`, `app.py` | `visual-engineering` | `streamlit`, `frontend-design`, `clean-code` | Streamlit, sidebar, state, widget, st., container, expander |
| **Report generation** | `src/report/**` | `writing` | `documentation-templates`, `clean-code` | Jinja2, HTML report, template, report |
| **Core data model** | `src/core/**` | `quick` | `python-patterns`, `clean-code` | data_models, constants, load_tables, dataclass, HK Code |
| **Docs updates** | `README.md`, `*.md` | `writing` | `documentation-templates`, `clean-code` | README, documentation, markdown, handoff |
| **HK Code compliance** | `src/**/design_codes/**`, `src/**/hk2013*.py` | `deep` | `python-patterns`, `clean-code` | HK Code 2013, HK Wind Code, ConcreteProperties, design code, compliance |
| **Playwright/E2E testing** | `test_*.js`, `e2e_*.js` | `quick` | `playwright`, `webapp-testing` | Playwright, browser, screenshot, E2E, chromium, page.locator |

### Fallback Route

When a request does NOT match any domain trigger above:

```yaml
Fallback Configuration:
  category: "unspecified-low"
  load_skills: ["clean-code", "python-patterns"]
  reasoning: "Safe defaults for ambiguous Python tasks"
```

If the task is clearly complex or high-risk despite ambiguous triggers:

```yaml
High-Risk Fallback:
  category: "deep"
  load_skills: ["systematic-debugging", "python-patterns", "clean-code"]
  reasoning: "Deep investigation for unclear but important tasks"
```

---

## Guardrails

### FEM Development Guardrails

| Convention | Rule |
|------------|------|
| Force extraction | Always use `ops.eleResponse(tag, 'localForce')` — NOT `ops.eleForce()` |
| Shear normalization | Negate j-end (Vy, Vz) |
| Moment normalization | Negate i-end (My, Mz, T) |
| Gravity load | `wy = -magnitude` (load in -local_y = downward) |
| Diaphragm master | Centroid node, tag 90000 + floor_level |
| Diaphragm constraint | Applied for ALL load patterns (not just wind) |
| Wind patterns | Wx+=4, Wx-=5, Wy+=6, Wy-=7 |
| vecxz (beams) | `(dy/L, -dx/L, 0)` for horizontal beams |
| vecxz (columns) | `(0, 1, 0)` for vertical columns |

### Playwright Testing Guardrails

#### Selector Hierarchy (Preference Order)

1. **`getByRole`** - Most stable, uses ARIA roles
   ```javascript
   await page.getByRole('button', { name: /Run FEM Analysis/i }).click();
   ```

2. **`aria-label`** - Semantic and resilient
   ```javascript
   await page.locator('input[aria-label="Bays in X"]').fill('3');
   ```

3. **`text=`** - Readable but may match multiple
   ```javascript
   await page.locator('text=Display Options').click();
   ```

4. **CSS selectors** - Last resort, most brittle
   ```javascript
   await page.locator('button.st-emotion-cache-xyz').click();
   ```

#### Rerun Synchronization (Streamlit-Specific)

| Action | Wait Time | Reason |
|--------|-----------|--------|
| After `page.goto()` | 3000ms | Initial load + Streamlit init |
| After input change | 1000ms | Streamlit rerun cycle |
| After expander open | 500ms | DOM update |
| After simple button click | 1000ms | Standard action completion |
| After FEM Analysis button | 8000ms | Analysis computation time |
| After FEM completion check | up to 180000ms | Wait for "Analysis Successful" banner |

#### Evidence Capture Paths

- Test screenshots: `test_screenshots/<test_name>/`
- Evidence archive: `.sisyphus/evidence/`
- Viewport only: `await page.screenshot({ path: 'view.png' })`
- Full page: `await page.screenshot({ path: 'full.png', fullPage: true })`

#### Known Edge Cases

1. **FEM Analysis Timeout** - "Analysis Successful" banner times out after 180s for base case; use smaller test cases
2. **Radio Button Selection** - Click label text with `force: true` instead of hidden input
3. **Stale Element Reference** - Re-query element after any Streamlit state change
4. **Scroll-Required Elements** - Scroll into view before interaction

---

## Must NOT Have

The following are explicitly prohibited in this project:

1. **Modifications to `repos/*`** - Root agents never touch nested repositories
2. **Hardcoded API keys** - All credentials must come from environment variables
3. **`ops.eleForce()` calls** - Always use `ops.eleResponse(tag, 'localForce')`
4. **Unmarked slow tests** - FEM tests must use `@pytest.mark.slow`
5. **Magic numbers for codes** - HK Code references must use named constants
6. **Duplicate policy documents** - No competing CLAUDE.md or AGENTS.md at root
7. **Playwright timeouts without handling** - FEM analysis waits need explicit timeout handling
8. **Manual verification language** - No "ask user to verify" patterns; use machine-checkable validation
9. **Unresolved placeholders** - No [agent], [skill], [module] placeholders in delivered documents

---

## Validation Checklist

Machine-checkable commands and criteria for verifying policy compliance:

```bash
# Test collection (pre-commit check)
python -m pytest --collect-only -q

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src

# Skip slow tests
pytest tests/ -v -m "not slow"

# Run specific FEM tests
pytest tests/test_fem_engine.py -v

# Run AI provider tests
pytest tests/test_ai_providers.py -v
```

### Compliance Criteria

- [ ] All .py files have proper HK Code 2013 references where applicable
- [ ] FEM-related code uses `ops.eleResponse(tag, 'localForce')` not `ops.eleForce()`
- [ ] AI provider code handles all three provider fallbacks (DeepSeek, Grok, OpenRouter)
- [ ] Tests use correct markers (`slow`, `integration`)
- [ ] No `repos/*` paths are modified by root agents
- [ ] Streamlit components follow established patterns in `src/ui/`
- [ ] pytest collection passes without errors

---

## Project Context

**PrelimStruct v3-5** — AI-Assisted Preliminary Structural Design Platform

- **Language**: Python 3.9+
- **UI Framework**: Streamlit >= 1.30.0
- **FEM Engine**: OpenSeesPy >= 3.5.0
- **AI Providers**: httpx-based (DeepSeek primary, Grok backup, OpenRouter fallback)
- **Testing**: pytest >= 7.4.0
- **Code Compliance**: HK Code 2013, HK Wind Code 2019
- **Module Structure**: 73 .py files across src/core, src/engines, src/fem, src/ai, src/ui, src/report
