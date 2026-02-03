# ETABS Manual Validation Process

This document describes the manual process for creating ETABS benchmark results
to validate PrelimStruct v3.5 shell element implementation.

## Validation Target

**>95% match with ETABS benchmark** (per PRD.md Success Criteria)

Default tolerance: 10% (5% for base shear, 2% for weight)

## Test Buildings

| ID | Name | Floors | Core Config | Complexity |
|----|------|--------|-------------|------------|
| building_01 | Simple 10-Story Office | 10 | I-Section | Simple |
| building_02 | 20-Story Residential | 20 | Two-C-Facing | Medium |
| building_03 | 30-Story Office Tower | 30 | Tube Center Opening | High |
| building_04 | Maximum Bays Podium | 15 | Two-C-Back-to-Back | High (10x10 grid) |
| building_05 | Minimum Configuration | 3 | Tube Side Opening | Simple (edge case) |

## ETABS Modeling Guidelines

### Element Types
- Walls: **Shell-Thin** (equivalent to ShellMITC4)
- Slabs: **Shell-Thin** with membrane behavior
- Beams: **Frame** elements
- Columns: **Frame** elements

### Section Properties
- Walls: Use layered section (Plate Fiber Section equivalent)
- Slabs: Elastic membrane plate section
- Beams/Columns: Rectangular sections per building definition

### Boundary Conditions
- Base: **Fixed** (all 6 DOF restrained)
- Floors: **Rigid diaphragm** assigned at each floor level

### Load Cases
1. **Dead Load (DL)**: Self-weight + finishes
2. **Live Load (LL)**: Per HK Code Table 3.1
3. **Wind Loads (W1-W24)**: Per HK Wind Code 2019
   - 8 directions × 3 eccentricities = 24 cases

### Load Combinations
Per HK Code 2013 Table 2.1:
- ULS Gravity: 1.4DL + 1.6LL
- ULS Wind: 1.4DL + 1.4W
- SLS: 1.0DL + 1.0LL

## Results to Record

For each building, record the following in `{building_id}_etabs.json`:

```json
{
  "building_id": "building_01",
  "building_name": "Simple 10-Story Office Building with I-Section Core",
  "etabs_version": "ETABS v21.2.0",
  "analysis_date": "2026-02-03",
  "analyst": "Engineer Name",
  "etabs_file": "building_01.EDB",
  "notes": "Manual analysis notes...",
  "results": {
    "max_lateral_drift_mm": 25.4,
    "max_story_drift_ratio": 0.0018,
    "base_shear_kN": 1250.5,
    "overturning_moment_kNm": 45000.0,
    "max_column_axial_kN": 8500.0,
    "max_beam_moment_kNm": 450.0,
    "max_coupling_beam_shear_kN": 350.0,
    "first_mode_period_s": 1.25,
    "second_mode_period_s": 1.15,
    "total_weight_kN": 125000.0,
    "analysis_time_s": 45.0
  },
  "load_cases_analyzed": [
    "ULS_GRAVITY_1",
    "ULS_WIND_1",
    "SLS_CHARACTERISTIC"
  ],
  "model_info": {
    "element_type": "Shell-Thin",
    "mesh_size_m": 1.0,
    "total_nodes": 2450,
    "total_elements": 3200,
    "wall_section": "Layered Shell",
    "slab_section": "Shell-Thin"
  }
}
```

## File Storage

Save ETABS results in:
```
.sisyphus/validation/etabs_results/{building_id}_etabs.json
```

## Validation Commands

```bash
# List all test cases
python scripts/validate_shell_elements.py --list-cases

# Show template for a building
python scripts/validate_shell_elements.py --show-template building_01

# Validate specific building
python scripts/validate_shell_elements.py --validate building_01

# Validate all buildings
python scripts/validate_shell_elements.py --validate-all

# Generate full report
python scripts/validate_shell_elements.py --report
```

## Quality Checklist

Before recording results, verify:
- [ ] Material properties match building definition
- [ ] Geometry matches (bay sizes, story heights, floors)
- [ ] Core wall configuration matches
- [ ] Load values match HK Code tables
- [ ] Boundary conditions are correct (fixed base)
- [ ] Rigid diaphragms assigned
- [ ] Mesh is converged (test with finer mesh if needed)
- [ ] Analysis converges successfully

## HK Code References

- **Loads**: HK Code 2013 Table 3.1 (Live loads)
- **Load Factors**: HK Code 2013 Table 2.1
- **Drift Limit**: HK Code 2013 Cl 7.3.2 (H/500)
- **Wind**: COP Wind Effects 2019
