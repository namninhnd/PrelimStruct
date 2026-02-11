# Phase 11: Canonical W1-W24 Wind Pipeline (Wx1/Wx2/Wtz)

## Status: EXECUTED (2026-02-11)

## Execution Snapshot (2026-02-11, All Gates A-F Complete)

- Gate A completed: baseline, simplified-caller traceability, and matrix/sign-order freeze captured in execution log.
- Gate B implementation completed in code: canonical solver map (`Wx`, `Wy`, `Wtz`), Option B torsion helper/application, and WindLoadCase semantic correction.
- Gate B targeted tests passed (`tests/test_multi_load_case.py`, `tests/test_model_builder.py`, `tests/test_wind_calculator.py`), and reviewer-requested cosmetic comment alignment in `LoadComponentType` is applied.
- Gate C implementation completed in code: `src/fem/wind_case_synthesizer.py` (authoritative 24x3 matrix + deterministic `AnalysisResult` superposition), bridge mapping for `LoadComponentType.W1...W24`, and synthesis injection into FEM results flow.
- Gate C targeted verification passed (`tests/test_wind_case_synthesizer.py`, `tests/test_combination_processor.py`, `tests/test_load_combinations.py`, `tests/test_multi_load_case.py`, `tests/ui/test_fem_views_state.py`) with basedpyright summary `errors=0` on modified files.
- Gate D verified: FEM UI already uses canonical `get_all_combinations()` exclusively. No production references to `get_simplified_all_combinations()` found. Cache key includes synthesis signature via `_build_combined_cache_key()`. All 36 UI/combination tests pass.
- Gate E completed: Simplified APIs (`get_simplified_wind_combinations`, `get_simplified_all_combinations`) and legacy enums removed. Test files updated to use canonical APIs.
- Gate F completed: 243 total tests passed (47 targeted + 103 regression + 93 comprehensive). No failures. Load Case mode verified stable.

**Final Executor Signoff:** Sisyphus Agent | 2026-02-11 12:55 +08

**Phase 11 Status: COMPLETE - All Acceptance Gates Passed**

## User Clarification (Authoritative)

W1-W24 are not an alternate naming set for `Wx+`/`Wy+`.
They are directional wind load cases synthesized from component effects
(`Wx1+/-`, `Wx2+/-`, and `Wtz`) per HK Wind Effects 2019.

This phase removes the dual-universe behavior and makes the wind pipeline code-true.

---

## 1. Problem Statement

Phase 10 introduced a solver-facing "simplified" path (`LC_WXP_*`, `LC_WYP_*`) to work
around the mismatch between:

- Combination library wind cases (`W1...W24`) in `src/fem/load_combinations.py`
- Solver-run load cases (`Wx+`, `Wx-`, `Wy+`, `Wy-`) in `src/fem/solver.py`

This workaround unblocked combination display, but it is now explicitly incorrect against
the intended HK wind-case model.

---

## 2. Current State (Verified - Post Gate D)

| Area | File | Current Behavior |
|------|------|------------------|
| Solver load-case map | `src/fem/solver.py` | Supports canonical components: `DL`, `SDL`, `LL`, `Wx`, `Wy`, `Wtz`, `combined` |
| Wind loading application | `src/fem/model_builder.py` | Applies translational X/Y floor shears with Option B torsion via `torsional_moments` |
| Torsion implementation | `src/fem/model_builder.py` | `apply_lateral_loads_to_diaphragms(..., torsional_moments=...)` active for Wtz case |
| Combo UI source | `src/ui/views/fem_views.py` | Uses `get_all_combinations()` (canonical); no simplified API references in production |
| Combo definitions | `src/fem/load_combinations.py` | Canonical `W1...W24` via `get_uls_wind_combinations()`; simplified APIs exist for test compat only |
| Wind synthesis | `src/fem/wind_case_synthesizer.py` | Deterministic W1-W24 synthesis from Wx/Wy/Wtz via HK matrix (24×3) |

---

## 3. Phase Goal

Deliver one canonical wind workflow:

1. Solve component wind cases (`Wx1`, `Wx2`, `Wtz`) at analysis level.
2. Synthesize `W1...W24` results from a code-backed coefficient matrix.
3. Run HK wind combinations (`LC_Wi_MAX`, `LC_Wi_MIN`) directly on `W1...W24`.
4. Remove simplified-combination path from FEM UI and state flow.

---

## 4. Scope

### In Scope

1. Add component-case support needed for W1-W24 synthesis (including torsion case handling).
2. Introduce deterministic `W1...W24` synthesis layer from component results.
3. Rewire FEM combination mode to use canonical combinations (`get_all_combinations()`).
4. Remove production use of `get_simplified_wind_combinations()` and
   `get_simplified_all_combinations()`.
5. Add tests that validate matrix correctness, sign convention, and UI availability.

### Out of Scope

1. Wind tunnel / dynamic response features.
2. Envelope UI expansion for displacement/reaction in this phase.
3. Seismic and accidental combination refactors.

---

## 5. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Wind truth source | `windloadcombo.xlsx` matrix (HK Wind Effects 2019 Table 2-1 expanded) | Avoid guessed coefficients/signs |
| Synthesis location | New FEM wind synthesis module (not UI) | Keep engineering logic outside Streamlit view code |
| Combo naming | Keep `LC_Wi_MAX` / `LC_Wi_MIN` | Matches existing HK-style library and sidebar |
| Wtz magnitude | **Option B** (design eccentricity torsion in component solve) | Keeps synthesis equation exactly in matrix form |
| Solver pattern map | `DL:1`, `SDL:2`, `LL:3`, `Wx:4`, `Wy:6`, `Wtz:8`, `combined:0` | Aligns with 3-component workflow and reviewer recommendation |
| Simplified APIs | Remove from UI path immediately; full deletion after all callers/tests migrate | Minimize risk while reducing complexity |

### 5.1 Component Naming Bridge

- Matrix symbols: `WX1`, `WX2`, `WTZ`
- Solver component cases: `Wx`, `Wy`, `Wtz`
- Bridge: `WX1 -> Wx`, `WX2 -> Wy`, `WTZ -> Wtz`

### 5.2 Wtz Magnitude Strategy (Locked)

Phase 11 uses **Option B** from review:

- Compute design torsional moments for the `Wtz` component case before solve.
- Apply those moments via `apply_lateral_loads_to_diaphragms(..., torsional_moments=...)`.
- Keep synthesis coefficients as pure matrix values (`+/-1.00`, `+/-0.55`).

Locked eccentricity formulas for Option B:

```text
eccentricity_x = 0.05 * building_depth   # for X-wind torsion
eccentricity_y = 0.05 * building_width   # for Y-wind torsion
Mz_floor = floor_shear * eccentricity
```

Implementation rule:

- Use `eccentricity_x` with X-wind floor shears and `eccentricity_y` with Y-wind floor shears.
- When generating a single `Wtz` component set from one floor-shear map, document the
  selected eccentricity basis explicitly in code/comments and tests.

### 5.3 Solver Pattern Map Evolution (Locked)

```python
LOAD_CASE_PATTERN_MAP = {
    "DL": 1,
    "SDL": 2,
    "LL": 3,
    "Wx": 4,
    "Wy": 6,
    "Wtz": 8,
    "combined": 0,
}
```

Notes:

- Old `Wx-` / `Wy-` component run patterns become redundant for canonical synthesis.
- `W1...W24` are synthesized post-solve and injected into `results_dict`.

### 5.4 WindLoadCase Enum Label Correction (Mandatory)

`src/core/data_models.py:47` currently labels `WindLoadCase` as
"8 directions x 3 eccentricities" (angle/ecc naming).

For Phase 11 documentation and code clarity, labels/comments must be corrected to:

- **3 dominance groups x 8 sign permutations**
- no angle/eccentricity naming in enum comments for `W1...W24`

Value strings remain unchanged (`"W1"` ... `"W24"`).

### 5.5 Authoritative W1-W24 Coefficient Matrix

Source: `windloadcombo.xlsx` (HK Wind Effects 2019, Table 2-1 expanded)

Structure:

- 3 dominance cases x 8 sign permutations = 24 wind cases.
- Sign order inside each 8-case block:
  `(+,+,+), (+,+,-), (+,-,+), (+,-,-), (-,+,+), (-,+,-), (-,-,+), (-,-,-)`

```text
Case 1 - WX1 dominant (|WX1|=1.00, |WX2|=0.55, |WTZ|=0.55)
         WX1     WX2     WTZ
W1       +1.00   +0.55   +0.55
W2       +1.00   +0.55   -0.55
W3       +1.00   -0.55   +0.55
W4       +1.00   -0.55   -0.55
W5       -1.00   +0.55   +0.55
W6       -1.00   +0.55   -0.55
W7       -1.00   -0.55   +0.55
W8       -1.00   -0.55   -0.55

Case 2 - WX2 dominant (|WX1|=0.55, |WX2|=1.00, |WTZ|=0.55)
         WX1     WX2     WTZ
W9       +0.55   +1.00   +0.55
W10      +0.55   +1.00   -0.55
W11      +0.55   -1.00   +0.55
W12      +0.55   -1.00   -0.55
W13      -0.55   +1.00   +0.55
W14      -0.55   +1.00   -0.55
W15      -0.55   -1.00   +0.55
W16      -0.55   -1.00   -0.55

Case 3 - WTZ dominant (|WX1|=0.55, |WX2|=0.55, |WTZ|=1.00)
         WX1     WX2     WTZ
W17      +0.55   +0.55   +1.00
W18      +0.55   +0.55   -1.00
W19      +0.55   -0.55   +1.00
W20      +0.55   -0.55   -1.00
W21      -0.55   +0.55   +1.00
W22      -0.55   +0.55   -1.00
W23      -0.55   -0.55   +1.00
W24      -0.55   -0.55   -1.00
```

### 5.6 Synthesis Formula

For each wind case `i`:

```text
W_i = coeff_wx1[i] * Wx_result + coeff_wx2[i] * Wy_result + coeff_wtz[i] * Wtz_result
```

Where:

- `Wx_result`, `Wy_result`, `Wtz_result` are solved component `AnalysisResult` objects.
- Coefficients come exactly from Section 5.5.

---

## 6. Implementation Plan

### Step 1: Expand Wind Component Case Support

**Files**
- `src/fem/model_builder.py`
- `src/fem/solver.py`
- `src/fem/wind_calculator.py`
- `src/ui/views/fem_views.py`
- `src/core/data_models.py`

**Actions**
1. Update solver load-case map to canonical component patterns:
   `DL:1`, `SDL:2`, `LL:3`, `Wx:4`, `Wy:6`, `Wtz:8`, `combined:0`.
2. Define bridge semantics: `WX1 -> Wx`, `WX2 -> Wy`, `WTZ -> Wtz`.
3. Implement Option B torsion magnitude generation (design eccentricity torsion) in
   wind calculation/application path using:
   `eccentricity_x = 0.05 * building_depth`,
   `eccentricity_y = 0.05 * building_width`, and
   `Mz_floor = floor_shear * eccentricity`.
4. Apply Wtz moments via existing diaphragm API:
   `apply_lateral_loads_to_diaphragms(..., torsional_moments=...)`.
5. Correct `WindLoadCase` enum labels/comments to dominance/sign-permutation semantics
   (values `W1...W24` unchanged).
6. Ensure analysis run list includes all required component cases (`Wx`, `Wy`, `Wtz`).

### Step 2: Implement W1-W24 Synthesis Engine

**Files**
- `src/fem/wind_case_synthesizer.py` (new)
- `src/fem/combination_processor.py` (reuse linear superposition helper if beneficial)

**Actions**
1. Encode W1-W24 synthesis recipes from the HK coefficient matrix in code (single source of truth).
2. Build `AnalysisResult` for each `W1...W24` by linear superposition of solved component results.
3. Persist synthesized cases into the same `results_dict` used by combination filtering.
4. Update `COMPONENT_TO_SOLVER_KEY` bridge so `LoadComponentType.W1...W24` resolve to
   synthesized keys (`"W1"..."W24"`).

**Rule**
- No inferred/approximate coefficients. Matrix values must match the code table used for synthesis.

### Step 3: Remove Simplified Combination Branch from FEM UI

**Files**
- `src/ui/views/fem_views.py`
- `src/ui/sidebar.py`
- `app.py` (if still used for combo state rendering)

**Actions**
1. Replace `LoadCombinationLibrary.get_simplified_all_combinations()` usage with canonical source.
2. Remove wind auto-include workaround in combination filtering.
3. Keep `selected_combinations` behavior driven by canonical `LC_Wi_*` names.

### Step 4: Consolidate Load Combination APIs

**Files**
- `src/fem/load_combinations.py`
- dependent tests in `tests/`

**Actions**
1. Keep `get_uls_wind_combinations()` as canonical wind combination provider.
2. Decommission simplified APIs from production flow.
3. Optional cleanup: remove simplified APIs entirely once test and UI migration is complete.

---

## 7. Test Plan

### New Tests

1. `tests/test_wind_case_synthesizer.py` (new)
   - Verifies full matrix row count (24) and coefficient integrity.
   - Verifies representative `W1`, `W7`, `W13`, `W19` and sign-permutation pairs.
   - Checks sign, scaling, and governing component contributions.

2. `tests/verification/test_wind_w1_w24_pipeline.py` (new)
   - End-to-end: solved component cases -> synthesized `W1...W24` -> `LC_Wi_*` combined result.

### Updated Tests

1. `tests/test_load_combinations.py`
   - Shift assertions to canonical combo path; no simplified combo assumptions.

2. `tests/test_combination_processor.py`
   - Include canonical `W1...W24` applicability and combination checks.

3. `tests/ui/test_fem_views_state.py` (+ optional new UI test file)
   - Verify combination dropdown behavior with canonical wind cases.

4. `tests/test_wind_calculator.py` and `tests/test_model_builder.py`
   - Verify Option B torsional moment generation and Wtz application path.

---

## 8. Acceptance Gates

All must pass:

1. `W1...W24` generated from solved component cases using code-backed matrix.
2. `LOAD_CASE_PATTERN_MAP` matches canonical component map (`Wx=4`, `Wy=6`, `Wtz=8`).
3. Option B torsion strategy is implemented and tested.
4. `WindLoadCase` enum labels/comments corrected to dominance/sign-permutation semantics.
5. `LC_Wi_MAX/MIN` combinations selectable and computable without simplified fallback.
6. No production path references `get_simplified_all_combinations()`.
7. FEM Load Case mode remains stable for gravity-only and wind-enabled workflows.
8. Regression suite for affected modules passes.

---

## 9. Risks and Controls

| Risk | Impact | Control |
|------|--------|---------|
| Matrix transcription error | Incorrect W-case physics | Add golden-value tests for sampled W-cases |
| Sign mismatch in torsion/eccentricity | Wrong envelope governing combos | Pair each positive case with explicit reversal assertion |
| Naming semantics drift | Wrong engineering interpretation in docs/UI | Enforce dominance/sign language in enum/comments/tests |
| Transition breakage from simplified path removal | UI combo regressions | Migrate in one branch with targeted UI tests before deletion |
| Cache stale combined results | Misleading displayed forces | Include synthesized-case signature in cache invalidation key |

---

## 10. Deliverables

1. Canonical wind synthesis module and tests.
2. FEM UI combination mode running on canonical `W1...W24` only.
3. Phase docs updated with implemented matrix source and validation evidence.

---

## 11. Follow-On (Not in This Phase)

1. Envelope UI mode for canonical wind combinations.
2. Displacement/reaction envelope expansion.
3. Full removal of any remaining simplified API shims after one stable cycle.
