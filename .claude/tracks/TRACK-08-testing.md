# Track 8: Testing & Quality Assurance

> **Priority:** P0 (MUST)
> **Start Wave:** 6 (After all implementation)
> **Primary Agent:** test-engineer
> **Status:** PENDING

---

## Overview

Comprehensive testing for all new V3.5 features. Unit tests, integration tests, and benchmark validation against ETABS/SAP2000. This track starts after implementation tracks complete, but the test-engineer should be briefed on what to expect throughout the project.

---

## External Dependencies (ALL Tracks Must Complete)

| Dependency | Track | Reason |
|------------|-------|--------|
| Architecture refactored | Track 1 | FEM-only codebase |
| Bugs fixed | Track 2 | Coupling beams, secondary beams |
| Wall elements | Track 3 | ShellMITC4 walls |
| Slab elements | Track 4 | ShellMITC4 slabs |
| Load system | Track 5 | 48 wind combinations |
| UI overhaul | Track 6 | Dashboard tests |
| AI chat | Track 7 | AI integration tests |

**Note:** Individual unit tests are written by each track's agent during implementation. This track focuses on COMPREHENSIVE testing, gap analysis, and benchmark validation.

---

## Tasks

### Task 23.1: Unit Tests for New Features
**Agent:** test-engineer
**Model:** sonnet
**Wave:** 6
**Dependencies:** All implementation tracks
**Status:** PENDING

**Sub-tasks:**
- [ ] 23.1.1: Tests for ShellMITC4 wall elements (Track 3)
- [ ] 23.1.2: Tests for ShellMITC4 slab elements (Track 4)
- [ ] 23.1.3: Tests for wind load case generation - 24 cases (Track 5)
- [ ] 23.1.4: Tests for load combination UI logic (Track 5)
- [ ] 23.1.5: Tests for AI model builder (Track 7)

**Files Impacted:**
- `tests/test_wall_element.py` (verify or expand)
- `tests/test_slab_element.py` (verify or expand)
- `tests/test_load_combinations.py` (verify or expand)
- `tests/test_ai_model_builder.py` (verify or expand)
- New test files as needed

**Verification:**
- All new modules have >80% test coverage
- All tests pass
- No untested edge cases in critical paths

---

### Task 23.2: Integration Tests
**Agent:** test-engineer
**Model:** sonnet
**Wave:** 6 (After 23.1)
**Dependencies:** Task 23.1
**Status:** PENDING

**Sub-tasks:**
- [ ] 23.2.1: End-to-end model building test (geometry -> FEM model)
- [ ] 23.2.2: Analysis workflow test (build -> analyze -> results)
- [ ] 23.2.3: Report generation with new features
- [ ] 23.2.4: AI chat integration test (chat -> configure -> build)

**Files Impacted:**
- `tests/test_integration_e2e.py` (NEW)
- `tests/test_ai_integration.py` (expand)

**Verification:**
- Integration tests pass
- Full workflow completes without errors
- Report generates with wall/slab/load data

---

### Task 23.3: Benchmark Validation
**Agent:** test-engineer
**Model:** opus
**Wave:** 6 (After 23.2)
**Dependencies:** Task 23.2 (integration tests passing)
**Status:** PENDING

**Sub-tasks:**
- [ ] 23.3.1: Create benchmark models (3 test buildings)
- [ ] 23.3.2: Compare results with ETABS/SAP2000
- [ ] 23.3.3: Document discrepancies and acceptable tolerances
- [ ] 23.3.4: Create validation report

**Files Impacted:**
- `tests/benchmarks/` (NEW directory)
- `tests/test_benchmark_validation.py` (NEW)
- `docs/VALIDATION_REPORT.md` (NEW)

**Verification:**
- Results within 5% of benchmark for displacements
- Results within 10% for member forces
- Validation report documents all comparisons

---

## Internal Execution Order

```
23.1 (Unit tests) ──> 23.2 (Integration tests) ──> 23.3 (Benchmarks)
```

Strictly sequential - each phase builds confidence for the next.

---

## Testing Strategy

### Tests Written During Implementation (by other agents)
Each implementation agent writes tests for their specific work:
- Track 1: FEM-only model tests
- Track 3: Wall element tests
- Track 4: Slab element tests
- Track 5: Load combination tests
- Track 7: AI assistant tests

### Tests Written by This Track (gap analysis + comprehensive)
This track's test-engineer:
1. Reviews ALL tests from implementation agents
2. Identifies coverage gaps
3. Writes missing unit tests
4. Creates integration tests spanning multiple features
5. Builds benchmark validation suite

---

## Agent Instructions

**Task 23.1 prompt (test-engineer):**
> Review all existing tests in the tests/ directory. Identify coverage gaps for new V3.5 features: ShellMITC4 wall elements, ShellMITC4 slab elements, 24 HK COP wind cases, load combination system, and AI model builder. Write comprehensive unit tests to achieve >80% coverage on all new modules. Focus on edge cases: null geometry, zero-length elements, boundary conditions, invalid parameters.

**Task 23.2 prompt (test-engineer):**
> Create end-to-end integration tests. Test the complete workflow: geometry input -> model building -> FEM analysis -> results extraction -> report generation. Test the AI chat flow: natural language input -> parameter extraction -> model configuration -> building. Cover happy paths and error paths. Create tests/test_integration_e2e.py.

**Task 23.3 prompt (test-engineer):**
> Create benchmark validation suite. Define 3 test buildings of varying complexity (10-story simple, 20-story with core, 30-story with irregular layout). Compare FEM results (displacements, forces, reactions) against reference values. Document acceptable tolerances (5% displacement, 10% forces). Create a validation report in docs/VALIDATION_REPORT.md.

---

*Track Owner: Orchestrator*
*Last Updated: 2026-01-26*
