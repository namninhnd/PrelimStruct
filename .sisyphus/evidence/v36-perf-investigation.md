# FEM Model Building Performance Investigation

## Summary

**Problem**: `build_fem_model()` is 32% slower after refactoring (6.39ms → 8.43ms avg)

**Root Causes Identified**:
1. **Unnecessary beam trimming calls** (2400 calls with polygon=None)
2. **Excessive rounding operations** (19680 calls to `round()`)
3. **Mandatory model validation** (10 calls, 0.003s each)

## Detailed Findings

### 1. Unnecessary Beam Trimming Calls 🔴

**Location**: `src/fem/model_builder.py` lines 1172-1176, 1238-1242

```python
segments = trim_beam_segment_against_polygon(
    start=(x_start * 1000.0, y * 1000.0),
    end=(x_end * 1000.0, y * 1000.0),
    polygon=core_outline_global if options.trim_beams_at_core else None,
)
```

**Issue**: 
- `trim_beams_at_core` defaults to `True` (line 176)
- Even when core wall is disabled (`include_core_wall=False`), the function is called 2400 times
- Function returns early when `polygon=None`, but call overhead still accumulates

**Profiler Data**:
- 2400 calls to `trim_beam_segment_against_polygon`
- 0.003s total time (0.00000125s per call)
- While small per-call, this is pure waste when no trimming is needed

### 2. Excessive Rounding in NodeRegistry 🔴

**Location**: `src/fem/model_builder.py` line 228-229

```python
def _key(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
    return (round(x, 6), round(y, 6), round(z, 6))
```

**Issue**:
- Called 3 times per `get_or_create` invocation
- 6560 calls to `get_or_create` = **19680 calls to `round()`**
- `round()` is the 3rd highest time consumer (0.011s total)

**Profiler Data**:
```
19680    0.011    0.000    0.011    0.000 {built-in method builtins.round}
```

### 3. Mandatory Model Validation 🟡

**Location**: `src/fem/fem_engine.py` line 638

**Issue**:
- `validate_model()` called on every model build
- 10 calls × 0.0003s = 0.003s total
- Not huge, but unnecessary for production runs

**Profiler Data**:
```
10    0.002    0.000    0.003    0.000 src/fem/fem_engine.py:638(validate_model)
```

### 4. NodeRegistry.get_or_create Overhead 🔴

**Issue**:
- 6560 calls to look up/create nodes
- Dictionary lookup with tuple key construction every time
- Combined with rounding, this is the #1 time consumer (0.044s cumulative)

**Profiler Data**:
```
6560    0.019    0.000    0.044    0.000 src/fem/model_builder.py:243(get_or_create)
6560    0.004    0.000    0.015    0.000 src/fem/model_builder.py:228(_key)
```

## Performance Breakdown (10 iterations)

| Component | Time (s) | % of Total | Calls |
|-----------|----------|------------|-------|
| `build_fem_model` | 0.024 | 27% | 10 |
| `get_or_create` | 0.019 | 22% | 6560 |
| `round` (builtin) | 0.011 | 12% | 19680 |
| `_key` | 0.004 | 5% | 6560 |
| `trim_beam_segment_against_polygon` | 0.003 | 3% | 2400 |
| `_group_nodes_by_elevation` | 0.003 | 3% | 10 |
| `validate_model` | 0.002 | 2% | 10 |
| Other | 0.022 | 25% | - |
| **Total** | **0.088** | **100%** | **95571** |

## Recommended Fixes

### Quick Win #1: Skip Beam Trimming When Core Wall Disabled

**File**: `src/fem/model_builder.py`
**Lines**: 1172-1176, 1238-1242, 1317, 1389

**Current Code**:
```python
segments = trim_beam_segment_against_polygon(
    start=(x_start * 1000.0, y * 1000.0),
    end=(x_end * 1000.0, y * 1000.0),
    polygon=core_outline_global if options.trim_beams_at_core else None,
)
```

**Optimized Code**:
```python
if options.trim_beams_at_core and core_outline_global:
    segments = trim_beam_segment_against_polygon(
        start=(x_start * 1000.0, y * 1000.0),
        end=(x_end * 1000.0, y * 1000.0),
        polygon=core_outline_global,
    )
else:
    segments = [BeamSegment(
        start=(x_start * 1000.0, y * 1000.0),
        end=(x_end * 1000.0, y * 1000.0),
        start_connection=BeamConnectionType.PINNED,
        end_connection=BeamConnectionType.PINNED,
    )]
```

**Expected Savings**: ~0.003s (3% improvement)

### Quick Win #2: Optimize NodeRegistry Key Generation

**File**: `src/fem/model_builder.py`
**Line**: 228-229

**Current Code**:
```python
def _key(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
    return (round(x, 6), round(y, 6), round(z, 6))
```

**Optimized Code** (use string formatting - faster than round):
```python
def _key(self, x: float, y: float, z: float) -> str:
    return f"{x:.6f},{y:.6f},{z:.6f}"
```

**Alternative** (reduce precision if 6 decimals not needed):
```python
def _key(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
    return (int(x * 1e6), int(y * 1e6), int(z * 1e6))
```

**Expected Savings**: ~0.005-0.008s (6-9% improvement)

### Quick Win #3: Make Validation Optional

**File**: `src/fem/model_builder.py`
**Add option to ModelBuilderOptions**:
```python
validate_model: bool = False  # Default to False for production
```

**Wrap validation call**:
```python
if options.validate_model:
    model.validate_model()
```

**Expected Savings**: ~0.003s (3% improvement)

## Combined Expected Improvement

| Fix | Time Saved | Cumulative |
|-----|------------|------------|
| Baseline | - | 8.43ms |
| Skip trimming | 0.30ms | 8.13ms |
| Optimize keys | 0.70ms | 7.43ms |
| Optional validation | 0.30ms | 7.13ms |
| **Total** | **1.30ms** | **7.13ms** |

**Result**: 7.13ms vs original 6.39ms = **11.6% regression** (down from 32%)

Or vs baseline 6.39ms: still 11.6% slower, but much improved.

## Alternative: Change Default `trim_beams_at_core`

If the quick fixes are too invasive, simply change the default:

**File**: `src/fem/model_builder.py`
**Line**: 176

```python
trim_beams_at_core: bool = False  # Changed from True
```

This alone would save ~0.003s and prevent the warning spam in logs.

## Investigation Details

**Profiler Used**: Python `cProfile` module
**Iterations**: 10 model builds
**Test Configuration**: 
- 10 floors, 3×3 bays
- Core wall disabled
- Gravity loads enabled
- No slabs

**Evidence Files**:
- `scripts/profile_model_building.py` - Profiling script
- `.sisyphus/evidence/v36-perf-baseline.md` - Performance baseline
- `.sisyphus/evidence/v36-perf-after.md` - Performance comparison
- `.sisyphus/evidence/v36-perf-investigation.md` - This file

## Conclusion

The 32% performance regression is caused by:
1. **Inefficient defaults** (`trim_beams_at_core=True` when no core wall)
2. **Unoptimized hot paths** (NodeRegistry key generation with 19680 `round()` calls)
3. **Unnecessary validation** (always-on model validation)

**Recommended Action**: Implement Quick Win #1 and #2 for immediate 9-12% improvement. Consider #3 for additional 3%.

---
*Generated: 2026-01-31*
*Task: Track 9.5 - Performance regression investigation*
