# Phase 11 Plan Review

## Status: REVIEWED (2026-02-11)

---

## Strategic Direction: CORRECT

Moving from the Phase 10 simplified workaround (`LC_WXP_*`) to canonical W1-W24 synthesis is the right call. The architecture is sound: solve 3 component basis cases → synthesize 24 → use existing `get_uls_wind_combinations()` which already generates the 48 combos.

## Execution Log (11B): SOLID

The gate structure (A→F), evidence ledger, risk log, and rollback plan are well-organized. Strict ordering prevents regressions.

---

## Authoritative W1-W24 Coefficient Matrix

Source: `windloadcombo.xlsx` (HK Wind Effects 2019, Table 2-1 expanded)

### Structure

3 dominance cases × 8 sign permutations = 24 W-cases.

Signs within each group of 8 follow binary counting on (±WX1, ±WX2, ±WTZ):
`(+,+,+), (+,+,-), (+,-,+), (+,-,-), (-,+,+), (-,+,-), (-,-,+), (-,-,-)`

### Full Matrix

```
Case 1 — WX1 dominant (|WX1|=1.00, |WX2|=0.55, |WTZ|=0.55)
         WX1     WX2     WTZ
W1       +1.00   +0.55   +0.55
W2       +1.00   +0.55   -0.55
W3       +1.00   -0.55   +0.55
W4       +1.00   -0.55   -0.55
W5       -1.00   +0.55   +0.55
W6       -1.00   +0.55   -0.55
W7       -1.00   -0.55   +0.55
W8       -1.00   -0.55   -0.55

Case 2 — WX2 dominant (|WX1|=0.55, |WX2|=1.00, |WTZ|=0.55)
         WX1     WX2     WTZ
W9       +0.55   +1.00   +0.55
W10      +0.55   +1.00   -0.55
W11      +0.55   -1.00   +0.55
W12      +0.55   -1.00   -0.55
W13      -0.55   +1.00   +0.55
W14      -0.55   +1.00   -0.55
W15      -0.55   -1.00   +0.55
W16      -0.55   -1.00   -0.55

Case 3 — WTZ dominant (|WX1|=0.55, |WX2|=0.55, |WTZ|=1.00)
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

### Synthesis Formula

For each W-case `i`:
```
W_i = coeff_wx1[i] * Wx_result + coeff_wx2[i] * Wy_result + coeff_wtz[i] * Wtz_result
```

Where `Wx_result`, `Wy_result`, `Wtz_result` are `AnalysisResult` objects from the 3 solver component runs.

---

## Critical Finding: WindLoadCase Enum Naming Mismatch

The `WindLoadCase` enum in `src/core/data_models.py:47-85` is organized as **8 directions × 3 eccentricities**:

```
W1  = W01_000_C  (labelled "0°, Center")
W2  = W02_000_P  (labelled "0°, Positive")
W3  = W03_000_N  (labelled "0°, Negative")
W4  = W04_045_C  (labelled "45°, Center")
...
W7  = W07_090_C  (labelled "90°, Center")
W9  = W09_090_N  (labelled "90°, Negative")
```

But the actual coefficient matrix is organized as **3 dominance cases × 8 sign permutations**:

```
W1-W8   = Case 1 (WX1 dominant), all 8 sign combos
W9-W16  = Case 2 (WX2 dominant), all 8 sign combos
W17-W24 = Case 3 (WTZ dominant), all 8 sign combos
```

**Example mismatch:** `W7` is labelled `W07_090_C` ("90° Center") but actually represents Case 1 with signs (-1.00·Wx, -0.55·Wy, +0.55·Wtz). `W9` is labelled `W09_090_N` ("90° Negative") but is actually the first Case 2 entry (+0.55·Wx, +1.00·Wy, +0.55·Wtz).

**Impact:** The enum VALUES ("W1"-"W24") are correct and used everywhere. The enum NAMES and comments are structurally wrong but cosmetic-only — no functional code reads the `_000_C` suffix.

**Action for Phase 11:** Correct the enum labels and comments to match the actual matrix structure (dominance case + sign permutation, not direction + eccentricity).

---

## Gap Resolution Status (Post-Matrix Review)

| Gap | Original Status | Updated Status |
|-----|----------------|----------------|
| 1. Coefficient matrix | BLOCKING | **RESOLVED** — full 24-row matrix from `windloadcombo.xlsx` above |
| 2. Component naming | AMBIGUOUS | **RESOLVED** — WX1 = X-direction wind force, WX2 = Y-direction wind force, WTZ = torsional moment about Z |
| 3. Wtz magnitude | UNSPECIFIED | **OPEN** — needs decision: unit torsion (cleaner) vs design eccentricity torsion |
| 4. Pattern map evolution | UNSPECIFIED | **OPEN** — need new pattern IDs and `COMPONENT_TO_SOLVER_KEY` bridge for synthesized W1-W24 |
| 5. `wind_calculator.py` | NOT MENTIONED | **OPEN** — needs to output per-floor torsional moments for Wtz component case |
| 6. Sidebar alignment | IMPLICIT | **NATURALLY RESOLVED** — canonical W1-W24 names match sidebar, Phase 10 auto-include workaround becomes unnecessary |

### Gap 3 Detail: Wtz Magnitude Decision

Two options for the Wtz solver component case:

**Option A — Unit torsion (recommended):**
- Solve Wtz with 1.0 N·m per floor at each diaphragm master
- In the synthesis matrix, scale by the actual eccentricity moment: `coeff_wtz[i] * (floor_shear * e)`
- Advantage: separates structural response from load calculation; coefficients are pure scaling factors
- Disadvantage: synthesis formula becomes `W_i = cx·Wx + cy·Wy + ct·e·Wtz` (eccentricity baked into synthesis, not solver)

**Option B — Design eccentricity torsion:**
- Compute `Mz_floor = floor_shear_x * 0.05 * building_depth` (for X-wind eccentricity) per floor
- Solve Wtz with these actual moments
- Advantage: synthesis coefficients stay as simple (±1.00, ±0.55) from the matrix
- Disadvantage: Wtz result is coupled to a specific eccentricity; changing `e` requires re-solving

**Recommendation:** Option B is simpler for the implementing agent — the synthesis formula stays exactly as the matrix says, with no additional eccentricity scaling. The Table 2-1 coefficients already encode the ±0.55/±1.00 weighting; the physical eccentricity is in the Wtz load magnitudes.

### Gap 4 Detail: Pattern Map and Bridge Evolution

**Solver patterns (proposed):**
```python
LOAD_CASE_PATTERN_MAP = {
    "DL": 1, "SDL": 2, "LL": 3,
    "Wx": 4, "Wy": 6, "Wtz": 8,    # 3 component cases
    # Wx-/Wy- (patterns 5, 7) become redundant — linearity
    # "combined": 0 stays for backward compat
}
```

**Bridge for synthesized results:**
W1-W24 are NOT solver cases. They are computed post-solve and injected into `results_dict`:
```python
results_dict["W1"] = synthesize(wx_result, wy_result, wtz_result, coeffs["W1"])
results_dict["W2"] = synthesize(wx_result, wy_result, wtz_result, coeffs["W2"])
...
```

Then `COMPONENT_TO_SOLVER_KEY` maps `LoadComponentType.W1 → "W1"` etc., and the existing `get_uls_wind_combinations()` (which references `LoadComponentType.W1`-`W24`) works naturally — no changes needed to the combination library.

### Gap 5 Detail: wind_calculator.py Torsion

`calculate_hk_wind()` currently returns `base_shear_x/y` but no torsion. For the Wtz component case, model_builder needs per-floor torsional moments. Simplest approach:

```python
# In model_builder.py wind application section:
# Compute eccentricity torsion per floor for Wtz component case
eccentricity_x = 0.05 * building_depth   # 5% eccentricity for X-wind
eccentricity_y = 0.05 * building_width   # 5% eccentricity for Y-wind
# Use the larger eccentricity effect as the Wtz magnitude:
torsional_moments = {elev: floor_shear * max(eccentricity_x, eccentricity_y)
                     for elev, floor_shear in floor_shears.items()}
```

Or extend `wind_calculator.py` to return `eccentricity_x/y` values alongside base shears.

---

## Minor Concerns

- **Diagonal cases resolved:** The matrix from `windloadcombo.xlsx` has no cos(45°)/sin(45°) scaling — all 24 cases use only the factors 1.00 and 0.55. The "8 directions" in the enum don't represent physical wind angles; they encode sign permutations. This eliminates the diagonal transcription risk.
- **Cross-wind effects:** Out of scope per the plan ("no wind tunnel/dynamic"). The Table 2-1 approach already implicitly accounts for cross-wind via the 0.55 coupling factors.

---

## Final Verdict

**Plan architecture: PASS.**
The 4-step flow (component cases → synthesis → rewire UI → retire simplified) is correct.

**Plan specificity for delegation: PASS (after matrix addition).**
With the 24-row coefficient matrix now available, Gaps 1-2 are resolved and Gap 6 is naturally resolved. The implementing agent needs the remaining open items (Gaps 3-5) specified in the Phase 11 plan before delegation.

**Mandatory additions to Phase 11 plan before delegation:**
1. Embed the full 24-row coefficient matrix (from this review) in a new Section 5.5
2. Specify Wtz magnitude approach (recommend Option B — design eccentricity torsion)
3. Specify new `LOAD_CASE_PATTERN_MAP` entries (Wx=4, Wy=6, Wtz=8)
4. Add `wind_calculator.py` or `model_builder.py` torsion computation to Step 1 file list
5. Correct `WindLoadCase` enum labels/comments (add to Step 1 or Step 4 actions)
