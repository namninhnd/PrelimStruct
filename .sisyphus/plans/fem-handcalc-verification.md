# FEM Verification vs Hand Calculations (1x1 + 2x3 Bay Benchmarks) - Rebaseline Plan v2

## TL;DR

> **Quick Summary**: Rebuild the FEM-vs-handcalc verification plan from scratch using current repository reality, not assumptions. Keep the existing benchmark suite, add missing hard checks/evidence integration, and lock in physics-correct acceptance criteria.
>
> **What is already true (from exhaustive repo scan + test runs)**:
> - Benchmark infrastructure exists under `tests/verification/`
> - 1x1/2x3 equilibrium + distribution + mesh checks exist
> - Helper builders and evidence writer module exist
> - Current suite passes (`pytest tests/verification -q` -> 64 passed)
>
> **Gaps this v2 plan closes**:
> - Evidence JSON writer is tested but not wired into benchmark runs
> - 2x3 column axial group checks are not present
> - Original beam/column hand assumptions need explicit shell-beam load-path caveat
> - Verification commands should target `tests/verification` (avoid full-repo collection cost)
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES (2 waves)
> **Critical Path**: evidence integration -> 2x3 column axial grouping -> mesh/tolerance hardening

---

## Context

### Original Intent
- Verify FEM outputs for simple models (1x1 bay, 2x3 bays) against hand calculations.
- Explain "weird" results with objective, reproducible checks.

### What Exists Now (Verified)
- Benchmark builders + independent load calculators:
  - `tests/verification/benchmarks.py`
  - `tests/verification/test_benchmark_builder.py`
- 1x1 equilibrium + reaction distribution checks:
  - `tests/verification/test_equilibrium_1x1.py`
- 2x3 equilibrium + group distribution checks:
  - `tests/verification/test_equilibrium_2x3.py`
- Mesh refinement checks (2x3, mesh 1->2):
  - `tests/verification/test_mesh_refinement_2x3.py`
- Column and beam diagnostics/checks:
  - `tests/verification/test_column_forces_1x1.py`
  - `tests/verification/test_beam_shear_1x1.py`
- Evidence writer utility + tests:
  - `tests/verification/evidence_writer.py`
  - `tests/verification/test_evidence_writer.py`

### Physics Clarification (Must Be Explicit)
- In shell-beam shared-node models, slab load can transfer directly to column nodes through shell action.
- Therefore, base reactions remain the primary handcalc verification target.
- Beam shear and column element axial checks are still useful, but should be treated as consistency/sanity checks, not strict tributary-equality checks unless model topology enforces that load path.

### Verified Benchmark Spec (Keep Fixed)
- Geometry:
  - `bay_x = 6.0 m`, `bay_y = 6.0 m`
  - `floors = 1`, `story_height = 4.0 m`
  - Models: 1x1 bay and 2x3 bays
- Sections:
  - Slab thickness: `150 mm`
  - Primary beam: `300 x 600 mm`
  - Column: `500 x 500 mm`
  - Secondary beams: `0`
- Materials:
  - `fcu = 40 MPa`
- Load cases:
  - DL: slab + beam + column self-weight
  - SDL: `1.5 kPa` slab pressure only
  - LL: `3.0 kPa` slab pressure only

---

## Work Objectives

### Core Objective
Produce an auditable verification ladder for 1x1 and 2x3 benchmark models that is:
1) equilibrium-first,
2) load-path-aware,
3) evidence-producing,
4) stable under mesh refinement.

### Definition of Done
- Benchmark verification tests pass from `tests/verification` scope.
- For 1x1 and 2x3 (SDL/LL):
  - analysis succeeds,
  - global equilibrium passes tolerance,
  - tributary group reaction checks pass tolerance.
- 2x3 column axial group checks exist and pass (load-path-aware criteria).
- Mesh stability checks pass for `slab_elements_per_bay=1` vs `2` (optional `3`).
- Evidence JSON artifacts are produced for benchmark runs under `.sisyphus/evidence/benchmarks/`.
- Plan and tests explicitly document shell-beam load-transfer caveat.

### Not In Scope
- No production UI changes.
- No nonlinear, P-Delta, dynamic, or buckling analysis.
- No core wall in these benchmarks.
- No secondary beam variation matrix.

---

## Verification Strategy (Mandatory)

> **Universal Rule: Zero human intervention**
>
> All checks run via pytest-only automation.

### Test Decision
- Infrastructure exists: YES (`pytest`)
- Workflow: TDD (RED -> GREEN -> REFACTOR)

### Tolerance Policy (v2)
- Global equilibrium (SDL/LL): <= 0.5% relative error
- Global equilibrium (DL): <= 1.0% relative error
- 1x1 symmetry (reactions): <= 5% max deviation from mean
- 1x1 tributary reaction check: <= 10%
- 2x3 group-average reactions vs tributary expectation: <= 15%
- Mesh stability (group averages, mesh 1->2): <= 5% change

### Important Interpretation Rules
- Treat base reactions as the primary global validation signal.
- Treat beam shear/column element-force checks as secondary consistency signals unless the model is explicitly load-path-constrained.
- Do not tune tolerances only to make tests green; change only with written rationale.

---

## Execution Strategy

### Wave 1 (Foundational Hardening)
- Evidence writer integration into benchmark test flows
- 2x3 column axial group checks
- Plan/test doc alignment for shell-beam load-path behavior

### Wave 2 (Stability + Quality)
- Optional mesh level 3 extension
- Command set hardening (`tests/verification` scope)
- CI-ready benchmark verification target

Critical path: Task 1 -> Task 2 -> Task 3

---

## TODOs

- [ ] 1. Wire benchmark evidence generation into actual benchmark test runs (TDD)

  **What to do (RED -> GREEN -> REFACTOR)**:
  - RED: add failing tests expecting benchmark tests to emit deterministic JSON files.
  - GREEN: call `write_evidence(...)` from benchmark verification flows (not only writer unit tests).
  - REFACTOR: centralize evidence record construction helper to avoid duplicate test code.

  **References**:
  - `tests/verification/evidence_writer.py`
  - `tests/verification/test_evidence_writer.py`
  - `tests/verification/test_equilibrium_1x1.py`
  - `tests/verification/test_equilibrium_2x3.py`

  **Acceptance Criteria**:
  - [ ] `.sisyphus/evidence/benchmarks/1x1_SDL.json` is generated by benchmark execution.
  - [ ] `.sisyphus/evidence/benchmarks/2x3_LL.json` is generated by benchmark execution.
  - [ ] Mesh-specific output uses suffix format `_mesh{N}`.

- [ ] 2. Add 2x3 column axial group checks (TDD)

  **What to do (RED -> GREEN -> REFACTOR)**:
  - RED: add failing tests for corner/edge/interior column axial group averages.
  - GREEN: extract base column axial by parent-column grouping and classify by coordinates.
  - REFACTOR: reuse existing group classification helpers from 2x3 reaction tests where practical.

  **References**:
  - `tests/verification/test_equilibrium_2x3.py`
  - `tests/verification/test_column_forces_1x1.py`
  - `src/fem/force_normalization.py`

  **Acceptance Criteria**:
  - [ ] 2x3 SDL column axial group checks exist and pass.
  - [ ] 2x3 LL column axial group checks exist and pass.
  - [ ] Group ordering is physically sensible (`interior > edge > corner`) under SDL and LL.

- [ ] 3. Rework beam/column hand-check assertions to be load-path-aware (TDD)

  **What to do (RED -> GREEN -> REFACTOR)**:
  - RED: add failing tests that enforce documented interpretation (global equilibrium hard-gate, member-force sanity secondary).
  - GREEN: align assertions and messages so they do not imply invalid tributary equality for shell-beam shared-node load paths.
  - REFACTOR: keep clear, concise diagnostics in failure output.

  **References**:
  - `tests/verification/test_beam_shear_1x1.py`
  - `tests/verification/test_column_forces_1x1.py`
  - `.sisyphus/notepads/fem-handcalc-verification/learnings.md`

  **Acceptance Criteria**:
  - [ ] Test docstrings and assertions are consistent with shell-beam load-transfer behavior.
  - [ ] No benchmark test encodes known-invalid one-way tributary assumptions for beam shear.

- [ ] 4. Extend mesh convergence coverage (optional level 3) and keep runtime bounded (TDD)

  **What to do**:
  - Add optional mesh-level-3 run for 2x3 SDL if runtime remains acceptable.
  - Check monotonic convergence trend and bounded deltas for group averages.

  **References**:
  - `tests/verification/test_mesh_refinement_2x3.py`
  - `src/fem/model_builder.py` (`slab_elements_per_bay`)

  **Acceptance Criteria**:
  - [ ] Mesh 1->2 checks remain <= 5% for each group.
  - [ ] If mesh 3 enabled, trend is stable and documented.

- [ ] 5. Harden verification command set and CI entrypoint

  **What to do**:
  - Keep benchmark verification commands scoped to `tests/verification` to avoid full-suite collection cost.
  - Add one CI-friendly command set in this plan and (if needed) in project docs.

  **References**:
  - `pytest.ini`
  - `README.md`

  **Acceptance Criteria**:
  - [ ] Command block below runs cleanly in local dev.
  - [ ] Commands are deterministic and do not rely on manual setup.

---

## Success Criteria

### Verification Commands
```bash
pytest tests/test_baseline_forces.py -q
pytest tests/test_reaction_extraction.py -q
pytest tests/verification -q
pytest tests/verification -k "benchmark_1x1 or benchmark_2x3" -q
```

### Final Checklist
- [ ] 1x1 SDL/LL/DL equilibrium checks pass
- [ ] 1x1 reaction distribution symmetry/tributary checks pass
- [ ] 2x3 SDL/LL equilibrium and group distribution checks pass
- [ ] 2x3 column axial group checks pass
- [ ] Mesh refinement stability checks pass
- [ ] Evidence JSON artifacts are produced under `.sisyphus/evidence/benchmarks/`
- [ ] Shell-beam load-path caveat is documented in both plan and tests

---

## Current Baseline Snapshot (2026-02-06)

- `pytest tests/test_baseline_forces.py -q` -> 22 passed
- `pytest tests/test_reaction_extraction.py -q` -> 2 passed
- `pytest tests/verification -q` -> 64 passed
- `pytest tests/verification -k "benchmark_1x1 or benchmark_2x3" -q` -> 28 passed, 36 deselected

This snapshot confirms strong existing coverage; v2 is focused on closing the remaining verification/audit gaps.
