# Validation Report: ETABS Comparison

## Executive Summary

This report documents the validation of **PrelimStruct v3.5** shell element implementation (ShellMITC4) for core walls and slabs against **ETABS v21** benchmark results. The primary goal is to verify that the pure FEM-based analysis engine meets the accuracy target of **>95% match** with industry-standard software.

**Overall Status: PENDING**
(Validation methodology established; manual ETABS benchmarking in progress)

## 1. Methodology

The validation process compares key structural responses between PrelimStruct and ETABS for five representative building configurations.

### 1.1 Modeling Assumptions
To ensure a "like-for-like" comparison, the following modeling guidelines are strictly followed:

| Feature | PrelimStruct v3.5 | ETABS v21 |
|---------|-------------------|-----------|
| **Wall Elements** | ShellMITC4 | Shell-Thin (Layered) |
| **Slab Elements** | ShellMITC4 | Shell-Thin (Membrane) |
| **Sections** | Plate Fiber Section | Layered Section |
| **Materials** | HK Code 2013 (Materials.py) | Custom Concrete (HK Code 2013) |
| **Boundary Conditions** | Fixed Base (6 DOF) | Fixed Support |
| **Diaphragms** | Rigid Diaphragm | Rigid Diaphragm |
| **Solver** | OpenSeesPy (Linear Static) | Standard Linear Static |

### 1.2 Comparison Metrics
Success is measured by the percentage error between the two platforms:
- **Base Shear & Weight**: < 2-5% error target
- **Displacements & Moments**: < 10% error target (industry standard for preliminary tools)

### 1.3 Validation Tool
Comparisons are managed using the automated script:
```bash
python scripts/validate_shell_elements.py --report
```

---

## 2. Test Buildings

Five buildings were defined to cover a range of complexities and edge cases:

### Building 01: Simple 10-Story Office
- **Core Configuration**: I-Section
- **Complexity**: Simple
- **Focus**: Basic shell meshing and gravity distribution.
- **Status**: Methodology Verified | Results Pending

### Building 02: 20-Story Residential
- **Core Configuration**: Two-C-Facing
- **Complexity**: Medium
- **Focus**: Coupling beam behavior and moderate lateral loads.
- **Status**: Methodology Verified | Results Pending

### Building 03: 30-Story Office Tower
- **Core Configuration**: Tube Center Opening
- **Complexity**: High
- **Focus**: Maximum height limit and drift control (H/500).
- **Status**: Methodology Verified | Results Pending

### Building 04: 15-Story Podium (Maximum Bays)
- **Core Configuration**: Two-C-Back-to-Back
- **Complexity**: High (10x10 Grid)
- **Focus**: Mesh generation performance and large node count handling.
- **Status**: Methodology Verified | Results Pending

### Building 05: Minimum Configuration
- **Core Configuration**: Tube Side Opening
- **Complexity**: Edge Case (1x1 Bay, 3 Stories)
- **Focus**: Boundary condition handling and low-rise behavior.
- **Status**: Methodology Verified | Results Pending

---

## 3. Comparison Results

### 3.1 Global Metrics Comparison

| Building | Metric | ETABS | PrelimStruct | Error (%) | Status |
|----------|--------|-------|--------------|-----------|--------|
| **BLD_01** | Total Weight (kN) | TBD | TBD | - | PENDING |
| | Base Shear (kN) | TBD | TBD | - | PENDING |
| | Max Drift (mm) | TBD | TBD | - | PENDING |
| **BLD_02** | Total Weight (kN) | TBD | TBD | - | PENDING |
| | Base Shear (kN) | TBD | TBD | - | PENDING |
| | Max Drift (mm) | TBD | TBD | - | PENDING |
| **BLD_03** | Total Weight (kN) | TBD | TBD | - | PENDING |
| | Base Shear (kN) | TBD | TBD | - | PENDING |
| | Max Drift (mm) | TBD | TBD | - | PENDING |

### 3.2 Member Forces Comparison (Typical Floor)

| Building | Member | Metric | ETABS | PrelimStruct | Error (%) | Status |
|----------|--------|--------|-------|--------------|-----------|--------|
| **BLD_01** | Column (Base) | Axial Force (kN) | TBD | TBD | - | PENDING |
| | Beam (Mid-span) | Moment (kNm) | TBD | TBD | - | PENDING |
| **BLD_02** | Coupling Beam | Shear Force (kN) | TBD | TBD | - | PENDING |
| | Core Wall | Moment (kNm) | TBD | TBD | - | PENDING |

---

## 4. Conclusion

### Summary of Results
- **Accuracy Target**: >95% (10% max error per metric)
- **Buildings Passing**: 0 / 5
- **Buildings Pending**: 5 / 5

### Final Verdict: PENDING
The validation framework is fully implemented. The report will be updated with numerical results once the manual ETABS benchmarking process (Task 23.3.2) is completed by the structural engineering team.

---
*Last Updated: 2026-02-03*
*Validation Suite: scripts/validate_shell_elements.py*
