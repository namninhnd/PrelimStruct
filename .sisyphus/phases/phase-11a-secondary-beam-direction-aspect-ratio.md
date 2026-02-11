# Phase 11A: Secondary Beam Direction Aspect-Ratio Fix

## Status: EXECUTED (2026-02-10)

---

## 1. Problem

When users switch secondary beam direction (especially Y <-> X), slab shell mesh quality can degrade and trigger warnings such as:

- `Slab mesh 'S10_2_1_1' has high aspect ratio 6.00 > 5`
- `Shell element 60000 has excessive aspect ratio 6.00 (max 5.00)`

This appeared on Page 2 during FEM analysis runs and was reproducible from model build/validation logs.

---

## 2. Findings

### 2.1 Warning Emitters

- Slab-level warning: `src/fem/slab_element.py:304`
- Shell validation warning: `src/fem/fem_engine.py:773`, `src/fem/fem_engine.py:797`

### 2.2 Root Cause

The model had a direction-consistency mismatch:

- Secondary beam creation semantics in `src/fem/model_builder.py:1552` mean:
  - `secondary_beam_direction == "Y"` -> beams at varying X positions (run along Y)
  - `secondary_beam_direction == "X"` -> beams at varying Y positions (run along X)
- But slab sub-panel splitting in `src/fem/model_builder.py:1966` previously used the opposite axis mapping.

So beam direction and slab strip direction were inconsistent, creating elongated slab quads in some configurations.

### 2.3 Numeric Evidence (Reproduced)

For a reproduced case with `bay_x=9`, `bay_y=6`, `num_secondary_beams=3`, direction `Y`:

- Old sub-panel size became `9.0 x 1.5`
- Mesh divisions were `4 x 4`
- Element sizes: `dx=2.25`, `dy=0.375`
- Aspect ratio = `2.25 / 0.375 = 6.00`

This matched shell edge-length checks for early slab shell elements (e.g., element 60000 family).

---

## 3. Solution

Apply a minimal, surgical fix: align slab strip axis with beam generation semantics.

- If `secondary_beam_direction == "Y"`: split slab in X (vertical strips)
- If `secondary_beam_direction == "X"`: split slab in Y (horizontal strips)

No unrelated changes to solver logic, load patterns, or FEM engine thresholds.

---

## 4. Fixes Applied

### 4.1 Code Fix

Updated slab sub-panel splitting in:

- `src/fem/model_builder.py:1966`

Changes made:

- `Y` branch now uses:
  - `strip_width = geometry.bay_x / num_strips`
  - `origin = (base_origin_x + k * strip_width, base_origin_y)`
  - `dims = (strip_width, geometry.bay_y)`
- `X` branch now uses:
  - `strip_width = geometry.bay_y / num_strips`
  - `origin = (base_origin_x, base_origin_y + k * strip_width)`
  - `dims = (geometry.bay_x, strip_width)`

### 4.2 Regression Tests

Added to `tests/test_slab_mesh_alignment.py`:

- Helper: `_max_shell_aspect_ratio(model)` (`tests/test_slab_mesh_alignment.py:40`)
- Test 1: `test_secondary_y_direction_mesh_aspect_ratio_within_limit` (`tests/test_slab_mesh_alignment.py:148`)
  - Case: `9 x 6`, `3` secondary beams, direction `Y`
  - Expectation: max shell AR `<= 5.0`
- Test 2: `test_secondary_x_direction_mesh_aspect_ratio_within_limit` (`tests/test_slab_mesh_alignment.py:178`)
  - Case: `6 x 18`, `1` secondary beam, direction `X`
  - Expectation: max shell AR `<= 5.0`

### 4.3 Follow-up Fix: Over-Segmentation in Split Axis

After the initial direction-consistency fix, users still observed visually thin/over-segmented mesh strips when switching beam direction.

Root cause: per-strip mesh counts reused the full-bay LCM division on the split axis, then applied it again inside each strip. This multiplied segmentation density by `sec_div`.

Updated in `src/fem/model_builder.py`:

- Compute global split-axis alignment once:
  - `split_axis_global_div = lcm(beam_div, sec_div)`
- Use per-strip split-axis divisions:
  - `split_axis_div_per_strip = split_axis_global_div // sec_div`
- Apply per strip:
  - if direction `Y`: `elements_along_x = split_axis_div_per_strip`
  - if direction `X`: `elements_along_y = split_axis_div_per_strip`

Effect: preserves beam-node alignment while avoiding excess segments in each strip.

### 4.4 Follow-up Fix: Shell Aspect-Ratio Warning Spam

Updated shell validation logging in `src/fem/fem_engine.py`:

- Previously: emitted one warning per offending shell element.
- Now: emits one summary warning with:
  - count of offending shells
  - threshold
  - worst element tag/aspect ratio
  - short sample list of tags/ratios

Added test in `tests/test_fem_engine.py`:

- `test_validate_model_logs_shell_aspect_ratio_warning_once`
  - Verifies a single summarized warning entry for multiple bad shell elements.

### 4.5 Follow-up Fix: Slab Panel Aspect-Ratio Warning Spam

Updated slab mesh warning behavior in `src/fem/slab_element.py` and `src/fem/model_builder.py`:

- Previously: each high-AR slab panel emitted its own warning line.
- Now: `SlabMeshGenerator` accumulates high-AR panels and emits one summary warning via
  `flush_high_aspect_ratio_warnings()` after slab generation in model builder.

Added test in `tests/test_slab_element.py`:

- `test_high_aspect_ratio_warning_summarized_once`
  - Verifies warnings are deferred and emitted once as a summary.

---

## 5. Verification Evidence

### 5.1 Targeted Regression

```bash
pytest tests/test_slab_mesh_alignment.py tests/test_slab_subdivision.py -q
```

Result: `10 passed`

### 5.2 Model Builder Regression

```bash
pytest tests/test_model_builder.py -q
```

Result: `40 passed`

### 5.3 Extended FEM Regression (including warning summary behavior)

```bash
pytest tests/test_slab_mesh_alignment.py tests/test_slab_subdivision.py tests/test_model_builder.py tests/test_fem_engine.py -q
```

Result: `98 passed`

### 5.4 Scenario Check (Post-Fix)

Direct check of max shell AR values after fix:

- `Y, bay 9x6, n=3` -> `max_ar=1.5`
- `X, bay 6x18, n=1` -> `max_ar=3.0`

Visual segmentation check (user-facing X-direction scenario):

- `X, bay 9x6, n=3` -> shell elements `16`, y-levels `[0.0, 1.5, 3.0, 4.5, 6.0]`

Both are below the quality threshold of `5.0`.

### 5.5 Syntax Check

```bash
python -m compileall src/fem/model_builder.py tests/test_slab_mesh_alignment.py
```

No syntax failures.

---

## 6. Impact and Risk

- Impacted scope is limited to slab sub-panel axis mapping plus targeted tests.
- Existing division/refinement rules were preserved.
- Mesh quality improves for direction-switch scenarios without widening system risk.

---

## 7. Reviewer Note (2026-02-11)

**Verdict: PASS** — code fix, over-segmentation fix, warning consolidation, and tests all correct. Full suite RC=0.

**Section 5.4 AR numbers need correction.** Independent verification (script + hand calc) shows:

| Scenario | Doc claims | Actual (verified) | Hand calc |
|----------|-----------|-------------------|-----------|
| Y, bay 9x6, n=3 | 2.667 | **1.500** | strip 2.25x6, elems 2.25x1.5, AR=1.5 |
| X, bay 6x18, n=1 | 1.5 | **3.000** | strip 6x9, elems 1.5x4.5, AR=3.0 |

Both remain well below the 5.0 threshold — no functional issue, documentation-only correction needed.

**Addressed:** Section 5.4 values have been corrected to match verified/hand-calculated AR values.

---

## 8. Follow-Up

- Optional UI enhancement: expose slab mesh refinement (`slab_elements_per_bay`) for advanced tuning.
- Keep new AR regression tests as a permanent guardrail for future refactors.
