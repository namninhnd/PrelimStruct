# Phase 4: Envelope Separation (Mz/My, Vy/Vz)

## Prerequisite
Phases 0-3 must be complete. All vecxz fixes are verified and tested.

## Objective
Separate the collapsed force envelopes:
- `M` (single) → `Mz` (major-axis moment) + `My` (minor-axis moment)
- `V` (single) → `Vy` (major-axis shear) + `Vz` (minor-axis shear)

After Phases 1-3, `Mz = major axis` and `My = minor axis` for all elements. The envelope should preserve this distinction instead of collapsing them.

## Current State

### `ElementForceEnvelope` dataclass (`results_processor.py:70-88`):
```python
@dataclass
class ElementForceEnvelope:
    element_id: int
    N_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    N_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    V_max: EnvelopeValue = field(default_factory=EnvelopeValue)  # Collapsed Vy+Vz
    V_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    M_max: EnvelopeValue = field(default_factory=EnvelopeValue)  # Collapsed My+Mz
    M_min: EnvelopeValue = field(default_factory=EnvelopeValue)
```

### Envelope computation (`results_processor.py:177-184`):
```python
V = max(
    abs(forces.get('Vy_i', 0.0)), abs(forces.get('Vy_j', 0.0)),
    abs(forces.get('Vz_i', 0.0)), abs(forces.get('Vz_j', 0.0))
)
M = max(
    abs(forces.get('My_i', 0.0)), abs(forces.get('My_j', 0.0)),
    abs(forces.get('Mz_i', 0.0)), abs(forces.get('Mz_j', 0.0))
)
```

### Consumers of old V_max, M_max fields:

**In `src/fem/results_processor.py`:**
1. **Lines 200-227** — Updates envelope values (V_max, V_min, M_max, M_min)
2. **Lines 409-417** — `get_critical_elements()` reads `M_max`, `V_max`
3. **Lines 444-450** — `export_envelope_summary()` reads `M_max`, `V_max`

**In `tests/test_results_processor.py` (23 references — MUST update):**
4. **Lines 34-37** — isinstance checks for `V_max`, `V_min`, `M_max`, `M_min`
5. **Lines 67-68** — Default value checks `V_max.max_value`, `M_min.max_value`
6. **Lines 298, 300** — 3D pipeline assertion: `V_max = 50`, `M_max = 200`
7. **Lines 314, 316** — 2D pipeline assertion: `V_max = 75`, `M_max = 300`
8. **Lines 359-360** — Max tracking: `V_max = 100`, `M_max = 400`
9. **Lines 402, 404** — Governing case: `V_max.governing_max_case`, `M_max.governing_max_case`
10. **Lines 661-670** — Critical elements by moment: direct-set `M_max.max_value`
11. **Lines 687-696** — Critical elements by shear: direct-set `V_max.max_value`
12. **Lines 739, 754** — Critical elements limit/invalid: `M_max.max_value`
13. **Lines 784-785** — Export summary with data: `M_max.max_value`, `V_max.max_value`
14. **Lines 806-808** — Summary format assertions: `"Maximum moment: 200.00"`, `"Maximum shear: 150.00"`

## Changes

### 1. Update `ElementForceEnvelope` dataclass

**File: `src/fem/results_processor.py`, lines 70-88**

```python
# BEFORE:
@dataclass
class ElementForceEnvelope:
    element_id: int
    N_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    N_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    V_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    V_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    M_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    M_min: EnvelopeValue = field(default_factory=EnvelopeValue)

# AFTER:
@dataclass
class ElementForceEnvelope:
    """Envelope of element forces across load combinations.

    Attributes:
        element_id: Element identifier
        N_max/N_min: Axial force envelope
        Vy_max/Vy_min: Major-axis shear envelope (gravity direction for beams)
        Vz_max/Vz_min: Minor-axis shear envelope
        Mz_max/Mz_min: Major-axis moment envelope (Mz = M33 = ETABS convention)
        My_max/My_min: Minor-axis moment envelope (My = M22)
    """
    element_id: int
    N_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    N_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    Vy_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Vy_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    Vz_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Vz_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    Mz_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Mz_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    My_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    My_min: EnvelopeValue = field(default_factory=EnvelopeValue)
```

### 2. Update `_update_element_force_envelope` method

**File: `src/fem/results_processor.py`, lines 173-227**

Replace the collapsed V and M computation with separated values:

```python
# BEFORE (3D path, lines 176-187):
N = max(abs(forces.get('N_i', 0.0)), abs(forces.get('N_j', 0.0)))
V = max(
    abs(forces.get('Vy_i', 0.0)), abs(forces.get('Vy_j', 0.0)),
    abs(forces.get('Vz_i', 0.0)), abs(forces.get('Vz_j', 0.0))
)
M = max(
    abs(forces.get('My_i', 0.0)), abs(forces.get('My_j', 0.0)),
    abs(forces.get('Mz_i', 0.0)), abs(forces.get('Mz_j', 0.0))
)
N_signed = (forces.get('N_i', 0.0) + forces.get('N_j', 0.0)) / 2
V_signed = (forces.get('Vy_i', 0.0) + forces.get('Vy_j', 0.0)) / 2
M_signed = (forces.get('My_i', 0.0) + forces.get('My_j', 0.0)) / 2

# AFTER:
N = max(abs(forces.get('N_i', 0.0)), abs(forces.get('N_j', 0.0)))
Vy = max(abs(forces.get('Vy_i', 0.0)), abs(forces.get('Vy_j', 0.0)))
Vz = max(abs(forces.get('Vz_i', 0.0)), abs(forces.get('Vz_j', 0.0)))
Mz = max(abs(forces.get('Mz_i', 0.0)), abs(forces.get('Mz_j', 0.0)))
My = max(abs(forces.get('My_i', 0.0)), abs(forces.get('My_j', 0.0)))
N_signed = (forces.get('N_i', 0.0) + forces.get('N_j', 0.0)) / 2
Vy_signed = (forces.get('Vy_i', 0.0) + forces.get('Vy_j', 0.0)) / 2
Vz_signed = (forces.get('Vz_i', 0.0) + forces.get('Vz_j', 0.0)) / 2
Mz_signed = (forces.get('Mz_i', 0.0) + forces.get('Mz_j', 0.0)) / 2
My_signed = (forces.get('My_i', 0.0) + forces.get('My_j', 0.0)) / 2
```

Update the envelope update block (lines 209-227) from:
```python
# Update shear force envelope
if V > envelope.V_max.max_value: ...
if V_signed < envelope.V_min.min_value: ...

# Update moment envelope
if M > envelope.M_max.max_value: ...
if M_signed < envelope.M_min.min_value: ...
```

To:
```python
# Update major-axis shear (Vy) envelope
if Vy > envelope.Vy_max.max_value:
    envelope.Vy_max.max_value = Vy
    envelope.Vy_max.governing_max_case = result.combination
    envelope.Vy_max.governing_max_location = elem_id
if Vy_signed < envelope.Vy_min.min_value or envelope.Vy_min.min_value == 0.0:
    envelope.Vy_min.min_value = Vy_signed
    envelope.Vy_min.governing_min_case = result.combination
    envelope.Vy_min.governing_min_location = elem_id

# Update minor-axis shear (Vz) envelope
if Vz > envelope.Vz_max.max_value:
    envelope.Vz_max.max_value = Vz
    envelope.Vz_max.governing_max_case = result.combination
    envelope.Vz_max.governing_max_location = elem_id
if Vz_signed < envelope.Vz_min.min_value or envelope.Vz_min.min_value == 0.0:
    envelope.Vz_min.min_value = Vz_signed
    envelope.Vz_min.governing_min_case = result.combination
    envelope.Vz_min.governing_min_location = elem_id

# Update major-axis moment (Mz) envelope
if Mz > envelope.Mz_max.max_value:
    envelope.Mz_max.max_value = Mz
    envelope.Mz_max.governing_max_case = result.combination
    envelope.Mz_max.governing_max_location = elem_id
if Mz_signed < envelope.Mz_min.min_value or envelope.Mz_min.min_value == 0.0:
    envelope.Mz_min.min_value = Mz_signed
    envelope.Mz_min.governing_min_case = result.combination
    envelope.Mz_min.governing_min_location = elem_id

# Update minor-axis moment (My) envelope
if My > envelope.My_max.max_value:
    envelope.My_max.max_value = My
    envelope.My_max.governing_max_case = result.combination
    envelope.My_max.governing_max_location = elem_id
if My_signed < envelope.My_min.min_value or envelope.My_min.min_value == 0.0:
    envelope.My_min.min_value = My_signed
    envelope.My_min.governing_min_case = result.combination
    envelope.My_min.governing_min_location = elem_id
```

### 3. Update `get_critical_elements` method

**File: `src/fem/results_processor.py`, lines 409-417**

```python
# BEFORE:
if criterion == "moment":
    value = envelope.M_max.max_value
    case = envelope.M_max.governing_max_case
elif criterion == "shear":
    value = envelope.V_max.max_value
    case = envelope.V_max.governing_max_case

# AFTER:
if criterion == "moment":
    value = envelope.Mz_max.max_value  # Major-axis moment
    case = envelope.Mz_max.governing_max_case
elif criterion == "shear":
    value = envelope.Vy_max.max_value  # Major-axis shear
    case = envelope.Vy_max.governing_max_case
```

### 4. Update `export_envelope_summary` method

**File: `src/fem/results_processor.py`, lines 444-450**

```python
# BEFORE:
max_M = max(env.M_max.max_value for env in self.element_force_envelopes.values())
max_V = max(env.V_max.max_value for env in self.element_force_envelopes.values())
max_N = max(env.N_max.max_value for env in self.element_force_envelopes.values())

lines.append(f"  Maximum moment: {max_M/1e6:.2f} kN-m")
lines.append(f"  Maximum shear: {max_V/1e3:.2f} kN")
lines.append(f"  Maximum axial: {max_N/1e3:.2f} kN")

# AFTER:
max_Mz = max(env.Mz_max.max_value for env in self.element_force_envelopes.values())
max_My = max(env.My_max.max_value for env in self.element_force_envelopes.values())
max_Vy = max(env.Vy_max.max_value for env in self.element_force_envelopes.values())
max_Vz = max(env.Vz_max.max_value for env in self.element_force_envelopes.values())
max_N = max(env.N_max.max_value for env in self.element_force_envelopes.values())

lines.append(f"  Maximum Mz (major): {max_Mz/1e6:.2f} kN-m")
lines.append(f"  Maximum My (minor): {max_My/1e6:.2f} kN-m")
lines.append(f"  Maximum Vy (major shear): {max_Vy/1e3:.2f} kN")
lines.append(f"  Maximum Vz (minor shear): {max_Vz/1e3:.2f} kN")
lines.append(f"  Maximum axial: {max_N/1e3:.2f} kN")
```

### 5. Handle 2D fallback

The 2D path at lines 189-195 uses `V_i`, `M_i` keys. For 2D elements there's only one bending axis, so map them to the major-axis fields:

```python
elif 'V_i' in forces:
    N = max(abs(forces.get('N_i', 0.0)), abs(forces.get('N_j', 0.0)))
    Vy = max(abs(forces.get('V_i', 0.0)), abs(forces.get('V_j', 0.0)))
    Vz = 0.0
    Mz = max(abs(forces.get('M_i', 0.0)), abs(forces.get('M_j', 0.0)))
    My = 0.0
    N_signed = (forces.get('N_i', 0.0) + forces.get('N_j', 0.0)) / 2
    Vy_signed = (forces.get('V_i', 0.0) + forces.get('V_j', 0.0)) / 2
    Vz_signed = 0.0
    Mz_signed = (forces.get('M_i', 0.0) + forces.get('M_j', 0.0)) / 2
    My_signed = 0.0
```

**NOTE:** The current 2D condition is `elif 'N_i' in forces or 'V_i' in forces:` (line 189). Since the 3D path already catches `'N_i' in forces` at line 175, this 2D elif only triggers when `'N_i'` is NOT present but `'V_i'` is. Simplify the condition to just `elif 'V_i' in forces:` for clarity.

### 6. Update existing tests in `tests/test_results_processor.py`

**This is a CRITICAL step — the existing test file has ~23 references to old field names that will BREAK.**

Two categories of renames:

#### Category A: Direct-set tests (critical elements, export summary)
These directly set `env.M_max.max_value` etc. Simple rename:

| Old Field | New Field | Lines |
|-----------|-----------|-------|
| `M_max` | `Mz_max` | 661, 662, 665, 666, 669, 670, 739, 754, 784 |
| `V_max` | `Vy_max` | 687, 688, 691, 692, 695, 696, 785 |

#### Category B: Pipeline tests (process force data, then assert)
These run force data through the pipeline and assert the result. The rename depends on WHERE the fixture data places its forces.

**3D fixture** (`sample_load_case_3d`, lines 183-198):
```python
# Fixture has: Vy_i=50, Vz_i=0, My_i=200, Mz_i=0
# Old: V_max = max(50,50,0,0) = 50,  M_max = max(200,200,0,0) = 200
# New: Vy_max = 50, Vz_max = 0,      My_max = 200, Mz_max = 0
```

So the 3D pipeline assertions rename:
| Old Assertion | New Assertion | Line |
|---------------|---------------|------|
| `envelope.V_max.max_value == 50.0` | `envelope.Vy_max.max_value == 50.0` | 298 |
| `envelope.M_max.max_value == 200.0` | `envelope.My_max.max_value == 200.0` | 300 |
| `envelope.V_max.max_value == 100.0` | `envelope.Vy_max.max_value == 100.0` | 359 |
| `envelope.M_max.max_value == 400.0` | `envelope.My_max.max_value == 400.0` | 360 |
| `envelope.V_max.governing_max_case` | `envelope.Vy_max.governing_max_case` | 402 |
| `envelope.M_max.governing_max_case` | `envelope.My_max.governing_max_case` | 404 |

**2D fixture** (`sample_load_case_2d`, lines 201-219):
```python
# Fixture has: V_i=75, M_i=300 (no N_i)
# 2D fallback maps: V → Vy, M → Mz
# New: Vy_max = 75, Mz_max = 300
```

So the 2D pipeline assertions rename:
| Old Assertion | New Assertion | Line |
|---------------|---------------|------|
| `envelope.V_max.max_value == 75.0` | `envelope.Vy_max.max_value == 75.0` | 314 |
| `envelope.M_max.max_value == 300.0` | `envelope.Mz_max.max_value == 300.0` | 316 |

#### Category C: Dataclass structure tests

| Old | New | Line |
|-----|-----|------|
| `isinstance(envelope.V_max, EnvelopeValue)` | `isinstance(envelope.Vy_max, EnvelopeValue)` | 34 |
| `isinstance(envelope.V_min, EnvelopeValue)` | `isinstance(envelope.Vy_min, EnvelopeValue)` | 35 |
| `isinstance(envelope.M_max, EnvelopeValue)` | `isinstance(envelope.Mz_max, EnvelopeValue)` | 36 |
| `isinstance(envelope.M_min, EnvelopeValue)` | `isinstance(envelope.Mz_min, EnvelopeValue)` | 37 |
| `envelope.V_max.max_value == 0.0` | `envelope.Vy_max.max_value == 0.0` | 67 |
| `envelope.M_min.max_value == 0.0` | `envelope.Mz_min.max_value == 0.0` | 68 |

Also add new assertions for the additional fields (Vz_max, Vz_min, My_max, My_min) in `test_element_force_envelope_creation`.

#### Summary format assertions (lines 806-808)
| Old | New |
|-----|-----|
| `"Maximum moment: 200.00 kN-m"` | `"Maximum Mz (major): 200.00 kN-m"` |
| `"Maximum shear: 150.00 kN"` | `"Maximum Vy (major shear): 150.00 kN"` |

### 7. Search for Other Consumers

Run this grep to verify NO other code references the old field names:
```
grep -rn "\.V_max\|\.V_min\|\.M_max\|\.M_min" src/ tests/
```

After all updates, this should return **zero matches**.

## Test

### Update existing tests (mandatory)
All ~23 references in `tests/test_results_processor.py` must be renamed per the mapping tables above.

### Create new tests in `tests/test_envelope_separation.py`:

```python
def test_envelope_separates_major_minor_moment():
    """After the axis fix, Mz (major) should dominate under gravity, My (minor) should be near-zero."""
    # Build a simple beam model with gravity load
    # Run analysis
    # Check: envelope.Mz_max.max_value >> envelope.My_max.max_value

def test_envelope_separates_major_minor_shear():
    """Vy (gravity shear) should dominate, Vz should be near-zero."""
    # Same model
    # Check: envelope.Vy_max.max_value >> envelope.Vz_max.max_value

def test_2d_fallback_maps_to_major():
    """2D elements should map single M → Mz_max, V → Vy_max."""

def test_3d_forces_separate_into_correct_fields():
    """3D element with forces in both Vy and Vz should populate both Vy_max and Vz_max independently."""
    # Use force data with non-zero values in BOTH axes to verify separation
```

## Acceptance Criteria
1. `ElementForceEnvelope` has 10 fields: N_max, N_min, Vy_max, Vy_min, Vz_max, Vz_min, Mz_max, Mz_min, My_max, My_min
2. No code references old `V_max`, `V_min`, `M_max`, `M_min` fields — grep across BOTH `src/` AND `tests/` returns zero matches
3. `get_critical_elements("moment")` returns major-axis moment (Mz)
4. `get_critical_elements("shear")` returns major-axis shear (Vy)
5. `export_envelope_summary()` shows all 5 values (Mz, My, Vy, Vz, N)
6. 2D fallback maps V→Vy, M→Mz
7. All existing tests in `tests/test_results_processor.py` updated and passing
8. All tests pass (same exclusion policy: `pytest tests/ --ignore=tests/verification/test_beam_shear_1x1.py -x --tb=short`)

## Guardrails
- **DO NOT** modify solver.py, fem_engine.py, or force_normalization.py
- **DO NOT** modify visualization.py or UI tables (that's Phase 5)
- **DO NOT** change the force keys in the element_forces dict (N_i, Vy_i, etc.) — only the envelope dataclass fields
- **DO NOT** add backward-compatibility aliases (no `V_max = property(lambda self: self.Vy_max)`) — just rename all references cleanly
- In `tests/test_results_processor.py`, pay attention to whether the test data goes through the 3D path (has `N_i`) or 2D path (has `V_i` only) — the rename is DIFFERENT for each:
  - 3D data with `My` forces → assert `My_max` (not `Mz_max`)
  - 2D data with `M` forces → assert `Mz_max` (2D fallback maps M→Mz)

## Phase 3 Findings (Context for This Phase)
- All line elements (beams, columns, coupling beams) now have correct vecxz
- Coupling beam vecxz computed in both beam_builder.py and model_builder.py
- `math.hypot` used consistently across all vecxz computations
- No changes were made to results_processor.py in Phases 1-3, so ALL line numbers in this file remain accurate
- Phase 1 confirmed positive Mz = sagging for simply-supported beams under gravity

## Commit Message
```
feat(fem): separate force envelopes into major/minor axes

Split collapsed V→Vy/Vz and M→Mz/My envelopes to preserve
axis distinction. Mz = major-axis (ETABS M33), My = minor-axis.
Critical elements and summary reports use major-axis values.
Update all existing test assertions for new field names.
```

## Execution Log

### Status
- Completed on 2026-02-08.

### Changes Applied
- `src/fem/results_processor.py`
  - Refactored `ElementForceEnvelope` fields from collapsed envelopes to axis-separated envelopes:
    - `N_max/N_min`, `Vy_max/Vy_min`, `Vz_max/Vz_min`, `Mz_max/Mz_min`, `My_max/My_min`.
  - Updated `_update_element_force_envelope`:
    - 3D path now computes and tracks Vy, Vz, Mz, My independently.
    - 2D fallback condition simplified to `elif 'V_i' in forces:`.
    - 2D mapping implemented as required: `V -> Vy`, `M -> Mz`, with `Vz=0`, `My=0`.
  - Updated `get_critical_elements` to use major-axis defaults:
    - `criterion='moment'` -> `Mz_max`
    - `criterion='shear'` -> `Vy_max`.
  - Updated `export_envelope_summary` to report all 5 values:
    - `Mz`, `My`, `Vy`, `Vz`, `N`.
- `tests/test_results_processor.py`
  - Updated all legacy envelope field references (`V_max/V_min/M_max/M_min`) to new axis-separated fields.
  - Updated 3D-path assertions to validate `Vy` and `My` behavior from fixture force data.
  - Updated 2D-path assertions to validate fallback mapping into `Vy` and `Mz`.
  - Updated summary-format assertions to new output labels.
- `tests/test_envelope_separation.py` (new)
  - Added dedicated envelope-separation coverage:
    - major/minor moment separation,
    - major/minor shear separation,
    - 2D fallback mapping,
    - 3D independent axis population.

### Verification Evidence
- Legacy field-reference cleanup check:
  - `grep -rn "\.V_max\|\.V_min\|\.M_max\|\.M_min" src tests`
  - Result: **zero matches**.
- Targeted Phase 4 tests:
  - `pytest tests/test_results_processor.py tests/test_envelope_separation.py -x --tb=short`
  - Result: **36 passed**.
- Full regression gate (same exclusion policy):
  - `pytest tests/ --ignore=tests/verification/test_beam_shear_1x1.py -x --tb=short`
  - Result: exit code **0**.
- Known-affected check file status:
  - `pytest tests/verification/test_beam_shear_1x1.py -x --tb=short`
  - Result: **6 passed**.
- Syntax/build sanity:
  - `python -m compileall src tests`
  - Result: completed successfully.

### Acceptance Criteria Mapping
- `ElementForceEnvelope` now has 10 axis-separated fields as required.
- Old envelope field references are removed from `src/` and `tests/`.
- `get_critical_elements("moment")` now uses `Mz` (major-axis).
- `get_critical_elements("shear")` now uses `Vy` (major-axis).
- `export_envelope_summary()` now shows `Mz`, `My`, `Vy`, `Vz`, and `N`.
- 2D fallback maps `V->Vy` and `M->Mz`.
- Existing results-processor tests were fully updated and pass.

### Notes
- `lsp_diagnostics` could not be executed in this environment because `basedpyright-langserver` is not installed on PATH.
- No changes were made to `solver.py`, `fem_engine.py`, or `force_normalization.py`.

## Next Phase Actions (Phase 5)
- Execute `phase-5-visualization-tables.md`:
  - Update force display labels in `src/fem/visualization.py`:
    - `Mz -> "Mz (Major Moment)"`, `My -> "My (Minor Moment)"`, and explicit Vy/Vz labels.
  - Update table headers and highlight defaults in:
    - `src/ui/components/beam_forces_table.py`
    - `src/ui/components/column_forces_table.py`
  - Add local-axis arrow toggle (default off) and force-convention legend annotation in visualization output.
  - Add/update tests for label mappings and default highlight behavior.
