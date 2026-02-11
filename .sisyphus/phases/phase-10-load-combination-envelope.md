# Phase 10: Load Combination Enveloping + Combination UI

## Status: REVIEWED & APPROVED (2026-02-10)

---

## 0. Implementation + Review Log

### 0.1 Agent Implementation (2026-02-10)

- Added solver-compatible wind load components to `LoadComponentType` in `src/fem/load_combinations.py`:
  - `WX_POS`, `WX_NEG`, `WY_POS`, `WY_NEG`
- Added simplified wind combination APIs in `src/fem/load_combinations.py`:
  - `get_simplified_wind_combinations()` (8 combos = 4 directions x 2 gravity variants)
  - `get_simplified_all_combinations()` (gravity + simplified wind + SLS only)
- Created `src/fem/combination_processor.py` with:
  - `combine_results()` for linear superposition into `AnalysisResult`
  - `compute_envelope()` for max/min envelope across combined results
  - `get_applicable_combinations()` for filtering combos to solved load components
- Integrated FEM UI in `src/ui/views/fem_views.py`:
  - Added radio toggle: `Load Case` vs `Load Combination`
  - In combo mode, dropdown filters from `st.session_state.selected_combinations`
  - Combined result is computed via `combine_results()` and assigned to `analysis_result`
  - Added session cache `fem_combined_results_cache`
  - Added cache invalidation in `_clear_analysis_state()`
  - In combo mode, reaction table fed with `{selected_combo_name: combined_result}`
  - opsvis force diagram restricted to Load Case mode (combo mode shows info message)
- Added combo-governing-name fields to `EnvelopeValue` in `src/core/data_models.py`:
  - `governing_max_case_name`, `governing_min_case_name` (Optional[str])
- Added torsion envelope fields to `ElementForceEnvelope` in `src/fem/results_processor.py`:
  - `T_max`, `T_min`
- Updated `to_equation()` to render simplified wind components before W1-W24 loop

### 0.2 Reviewer Verdict: PASS (with 1 bug fix)

**Review checklist results:**

| # | Check | Result |
|---|-------|--------|
| 1 | W1-W24 isolation preserved (`get_uls_wind_combinations()` untouched) | PASS |
| 2 | Units remain raw SI through combination pipeline (no /1000 in processor) | PASS |
| 3 | Missing component = zero contribution, no exception | PASS |
| 4 | Session cache lifecycle (`_clear_analysis_state()` invalidates combo cache) | PASS |
| 5 | Load Case mode behavior unchanged | PASS |
| 6 | Load Combination mode updates force plots/tables/reaction table | PASS |
| 7 | opsvis constrained to Load Case mode only | PASS |
| 8 | `EnvelopeValue` new fields don't affect existing enum-based consumers | PASS |
| 9 | `T_max`/`T_min` in `ElementForceEnvelope` no regression | PASS |
| 10 | Superposition math verified (manual: 1.4*100+1.4*50+1.6*80=338.0, exact match) | PASS |

**Verification runs:**
- Phase 10 specific tests: **36 passed**
- Broad regression (12 test files): **203 passed**
- Full suite exit code: **0**

### 0.3 Post-Review Bug Fix (Reviewer)

**Bug: Simplified wind combos invisible in FEM combo dropdown**

- **Root cause**: `fem_views.py:529-531` filtered `simplified_combinations` by `comb.name in selected_names`, where `selected_names` comes from the sidebar (`st.session_state.selected_combinations`). The sidebar uses `get_all_combinations()` which has W1-W24 names (`LC_W1_MAX`, etc.), NOT the simplified names (`LC_WXP_MAX`, etc.). These name sets don't overlap, so wind combos were always filtered out.
- **Impact**: When user switches to "Load Combination" mode, only gravity (LC1, LC2) and SLS (SLS1-3) combos appeared. The 8 simplified wind combos were never selectable, even when wind load cases were solved.
- **Fix**: Auto-include `ULS_WIND` category combos from the simplified set regardless of sidebar selection. Gravity/SLS combos continue to respect sidebar checkboxes. Added `LoadCombinationCategory` import to `fem_views.py`.

```python
# Before (agent code):
selected_combinations = [
    comb for comb in simplified_combinations if comb.name in selected_names
]

# After (reviewer fix):
selected_combinations = [
    comb
    for comb in simplified_combinations
    if comb.name in selected_names
    or comb.category == LoadCombinationCategory.ULS_WIND
]
```

- **Tests**: All 36 Phase 10 tests + 203 regression tests pass after fix.

---

## 1. Problem Statement

The solver runs 7 individual load patterns (DL, SDL, LL, Wx+, Wx-, Wy+, Wy-), but:
- Results are not combined into factored load combinations (1.4DL + 1.4SDL + 1.6LL, etc.)
- The FEM page only shows individual unfactored load cases — no combination view
- There is no envelope across multiple combinations to find governing design forces

## 2. Scope

| # | Component | Risk |
|---|-----------|------|
| 1 | `combination_processor.py` — factored combination pipeline | Medium |
| 2 | FEM page combo selector (radio toggle + dropdown) | Medium |
| 3 | Reaction table enhancement for combined results | Low |
| 4 | Envelope computation across all selected combinations | Medium |

## 3. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Wind component mapping | New `LoadComponentType` members for Wx+/Wx-/Wy+/Wy- | W1-W24 are HK Code directional, NOT our solver cases |
| Combination selector | Radio toggle "Load Case" / "Load Combination" in FEM views | Reuses existing `st.selectbox("Load Case", ...)` location |
| Sidebar linkage | Gravity/SLS respect sidebar; wind combos auto-included when solved | Sidebar has W1-W24 names, not simplified Wx± names |
| Superposition method | Linear combination of `AnalysisResult` dictionaries | Valid for linear static analysis |
| Export format | CSV + existing Excel (already in `reaction_table.py`) | Reaction table ALREADY has CSV+Excel export |

---

## 4. CRITICAL CONTEXT (Reference)

### 4.1 The W1-W24 vs Wx±/Wy± Problem

`LoadComponentType` has W1-W24 (HK Code 2019's 24 wind direction/eccentricity cases). Our solver only runs 4 orthogonal wind cases: Wx+/Wx-/Wy+/Wy-.

`get_uls_wind_combinations()` generates 48 combos for W1-W24 — unusable by the solver.

**Solution implemented**: 4 new enum members (`WX_POS`, `WX_NEG`, `WY_POS`, `WY_NEG`) + `get_simplified_wind_combinations()` (8 combos) + `get_simplified_all_combinations()` (13 total: 2 gravity + 8 wind + 3 SLS).

### 4.2 The Superposition Algorithm

`COMPONENT_TO_SOLVER_KEY` maps `LoadComponentType` to solver result keys:
```
DL→"DL", SDL→"SDL", LL→"LL", WX_POS→"Wx+", WX_NEG→"Wx-", WY_POS→"Wy+", WY_NEG→"Wy-"
```

For each element/node, combined value = `sum(factor * case_value)` across all components. Missing components contribute 0.

### 4.3 What Was NOT Changed

solver.py, fem_engine.py, visualization.py, force_normalization.py, app.py, reaction_table.py (existing), sidebar.py

---

## 5. Files

| File | Action | Notes |
|------|--------|-------|
| `src/fem/combination_processor.py` | **NEW** | Core logic: superposition + envelope |
| `src/fem/load_combinations.py` | **MODIFY** | Add WX_POS/WX_NEG/WY_POS/WY_NEG + simplified combos + `to_equation()` update |
| `src/ui/views/fem_views.py` | **MODIFY** | Radio toggle + combo dropdown + reviewer wind-combo fix |
| `src/core/data_models.py` | **MODIFY** | Add `governing_*_case_name` fields to `EnvelopeValue` |
| `src/fem/results_processor.py` | **MODIFY** | Add `T_max/T_min` envelope fields |
| `tests/test_combination_processor.py` | **NEW** | 5 unit tests for superposition + envelope + filtering |
| `tests/verification/test_envelope_pipeline.py` | **NEW** | 1 integration test for full pipeline |
| `tests/ui/test_fem_views_state.py` | **NEW** | 1 test for combo cache invalidation |
| `tests/test_load_combinations.py` | **MODIFY** | Add simplified combination coverage |

---

## 6. Gate Criteria (Final)

- [x] All existing tests pass (regression gate) — 203 confirmed
- [x] `combine_results()` correctly sums `factor * case_result` — verified manually
- [x] Missing component contributes 0, no error — test coverage
- [x] Envelope tracks governing combination name — test coverage
- [x] Radio toggle switches modes correctly
- [x] Combo dropdown shows applicable combos (including wind when solved)
- [x] Force diagrams + tables update when combo selected
- [x] Reaction table shows combined results in combo mode
- [x] No changes to solver.py, fem_engine.py, visualization.py, force_normalization.py, app.py
- [x] Wind combos auto-appear when wind cases solved (reviewer fix)

---

## 7. Known Limitations & Phase 11 Considerations

### 7.1 Envelope UI Not Yet Surfaced

`compute_envelope()` is implemented and tested but has no UI panel. A future phase could add:
- Envelope summary table showing governing combo per element per force type
- "Envelope" option in the View Mode radio (alongside "Load Case" / "Load Combination")
- Color-coded plan/elevation views showing which combo governs where

### 7.2 opsvis Incompatible with Combo Mode

opsvis needs a single OpenSees load pattern to render force diagrams. A combined result has no single pattern. Current behavior: info message in combo mode. Options for future:
- Render Plotly force diagrams only (already works in combo mode)
- Synthetic pattern replay (build model with combined nodal forces — complex, low priority)

### 7.3 Sidebar Wind Combos Mismatch

The sidebar shows W1-W24 checkboxes from `get_all_combinations()`, but the FEM page uses `get_simplified_all_combinations()` with `LC_WXP_MAX` etc. These are different naming universes. Future options:
- Add a "Simplified Wind" section to the sidebar with the 8 Wx±/Wy± combos
- Or replace W1-W24 section with simplified combos when solver-level wind is the only option
- Current workaround (reviewer fix): auto-include ULS_WIND from simplified set

### 7.4 No Combined-Action Wind Combos (HK Code Case 2c)

HK Code Table 2.1 Case 2 also includes `1.2DL + 1.2SDL + 1.2LL + 1.2W` (gravity + live + wind combined action). The current simplified set only has `1.4G + 1.4W` (max gravity) and `1.0G + 1.4W` (min gravity) — no live load in wind combos. Phase 11 should add:
- `LC_WXP_COMB`: 1.2DL + 1.2SDL + 1.2LL + 1.2Wx+  (and for all 4 directions)
- This adds 4 more combos, bringing simplified total from 13 to 17

### 7.5 Combo Cache Keyed by Name Only

Current cache: `st.session_state["fem_combined_results_cache"][combo_name] = AnalysisResult`. This is fine because `_clear_analysis_state()` wipes the cache on model/input changes. If future workflows allow partial re-analysis (e.g., re-run only wind cases), the cache would serve stale gravity components. Fix: include a hash of `results_dict` keys in the cache key.

### 7.6 `ResultsProcessor` vs `combination_processor` Duality

Two separate envelope implementations exist:
- `results_processor.py:ResultsProcessor` — works with `LoadCaseResult` (data_models), used by nobody currently
- `combination_processor.py:compute_envelope()` — works with `AnalysisResult` (solver), actively used

Future cleanup: deprecate `ResultsProcessor.process_load_case_results()` or unify the two into a single interface.

### 7.7 No Displacement/Reaction Envelopes in `compute_envelope()`

Currently `compute_envelope()` only tracks **element force** envelopes (N, Vy, Vz, T, My, Mz). It does not envelope displacements or reactions. Phase 11 could extend it for:
- Displacement envelope (SLS deflection checks — max vertical deflection across SLS combos)
- Reaction envelope (foundation design — max/min Fz across ULS combos for uplift checks)
