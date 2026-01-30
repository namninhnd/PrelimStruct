# Performance Benchmark Comparison - v36 After Refactor

## Summary

| Metric | Baseline | After Refactor | Change | % Change |
|--------|----------|----------------|--------|----------|
| **Date/Time** | 2026-01-30 | 2026-01-31 | - | - |
| **Platform** | Windows-10-10.0.26200-SP0 | Windows-10-10.0.26200-SP0 | - | - |

## Detailed Performance Comparison

### build_fem_model (ms)

| Stat | Baseline | After Refactor | Change | % Change |
|------|----------|----------------|--------|----------|
| Min | 5.11 | 6.36 | +1.25 | **+24.5%** 🔴 |
| Avg | 6.39 | 8.43 | +2.04 | **+32.0%** 🔴 |
| Max | 6.99 | 10.98 | +3.99 | **+57.1%** 🔴 |

### create_plan_view (ms)

| Stat | Baseline | After Refactor | Change | % Change |
|------|----------|----------------|--------|----------|
| Min | 27.78 | 25.70 | -2.08 | **-7.5%** 🟢 |
| Avg | 61.72 | 55.37 | -6.35 | **-10.3%** 🟢 |
| Max | 172.51 | 163.68 | -8.83 | **-5.1%** 🟢 |

### create_elevation_view (ms)

| Stat | Baseline | After Refactor | Change | % Change |
|------|----------|----------------|--------|----------|
| Min | 127.62 | 137.79 | +10.17 | **+8.0%** 🔴 |
| Avg | 139.47 | 150.60 | +11.13 | **+8.0%** 🔴 |
| Max | 160.95 | 164.61 | +3.66 | **+2.3%** 🔴 |

### create_3d_view (ms)

| Stat | Baseline | After Refactor | Change | % Change |
|------|----------|----------------|--------|----------|
| Min | 33.66 | 34.26 | +0.60 | **+1.8%** 🟡 |
| Avg | 42.36 | 41.83 | -0.53 | **-1.3%** 🟢 |
| Max | 68.98 | 61.95 | -7.03 | **-10.2%** 🟢 |

## Key Findings

### 🟢 Improvements
1. **Plan View**: 10.3% faster on average (61.72ms → 55.37ms)
2. **3D View Max**: 10.2% faster worst-case (68.98ms → 61.95ms)
3. **3D View Avg**: 1.3% faster on average (42.36ms → 41.83ms)

### 🔴 Regressions
1. **FEM Model Building**: 32.0% slower on average (6.39ms → 8.43ms)
   - Min: +24.5%
   - Max: +57.1% (significant worst-case regression)
2. **Elevation View**: 8.0% slower on average (139.47ms → 150.60ms)
   - Min: +8.0%
   - Max: +2.3%

### 🟡 Neutral
- 3D View Min: Nearly unchanged (+1.8%)

## Analysis

### Why FEM Model Building Got Slower
The regression in `build_fem_model` is likely due to:
1. **New beam release logic** - Additional processing for beam end releases
2. **Enhanced geometry handling** - More robust coordinate transformations
3. **Additional validation** - Better error checking and logging

### Why Plan View Got Faster
The improvement in `create_plan_view` suggests:
1. **Optimized rendering pipeline** - More efficient Plotly figure generation
2. **Reduced redundant calculations** - Better caching of view state
3. **Streamlined data flow** - Less overhead in view configuration

### Why Elevation View Got Slower
The elevation view regression may be due to:
1. **Enhanced coordinate handling** - More complex 3D-to-2D projection
2. **Additional element support** - Processing more element types
3. **Improved deflected shape rendering** - More accurate deformation visualization

## Benchmark Configuration

| Parameter | Value |
|-----------|-------|
| **Building** | 10 floors, 3×3 bays |
| **Bay Size** | 6.0m × 5.0m |
| **Story Height** | 3.0m |
| **Core Wall** | Disabled |
| **Slabs** | Disabled |
| **Wind Loads** | Disabled |
| **Gravity Loads** | Enabled |
| **Iterations** | 5 runs per operation |

## Overall Assessment

| Category | Score | Notes |
|----------|-------|-------|
| **Plan View** | ✅ Excellent | 10% improvement |
| **3D View** | ✅ Good | Near-neutral with better worst-case |
| **Elevation View** | ⚠️ Acceptable | 8% regression but still performant |
| **FEM Model Building** | ⚠️ Monitor | 32% regression needs attention |

## Recommendations

1. **Investigate FEM model building performance** - Profile the new beam release and geometry handling code
2. **Consider caching** - FEM model structure could be cached for repeated visualizations
3. **Acceptable trade-off** - View improvements may justify model building overhead

## Evidence Files

| File | Description |
|------|-------------|
| `.sisyphus/evidence/v36-perf-baseline.md` | Updated with latest benchmark results |
| `.sisyphus/evidence/v36-perf-after.md` | This comparison summary |
| `scripts/bench_v36.py` | Benchmark script (not modified) |

---
*Generated: 2026-01-31*
*Task: Track 9.2 - Performance benchmark comparison*
