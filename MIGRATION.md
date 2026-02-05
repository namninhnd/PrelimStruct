# PrelimStruct V3.0 to V3.5 Migration Guide

This document outlines the breaking changes, removed features, and new capabilities introduced in PrelimStruct V3.5. 

**V3.5 is a major architectural shift from a hybrid simplified/FEM approach to a pure FEM-based platform.**

---

## 🚨 Breaking Changes

### 1. Pure FEM-Only Architecture
V3.5 removes the "Simplified Method" entirely. All structural analysis and member design are now driven by the OpenSeesPy FEM engine. 

### 2. Project File Incompatibility
Projects saved in V3.0 **cannot be loaded** in V3.5. 
- **Why?**: The internal `ProjectData` schema has been refactored to support advanced shell elements, 60+ load combinations, and a new node numbering scheme. Simplified-only fields have been removed to clean up the codebase.
- **Action**: We recommend manually re-entering your building parameters into the new version.

### 3. Shell Element Transition
- **Walls**: Transitioned from beam elements to `ShellMITC4` elements with Plate Fiber Sections.
- **Slabs**: Transitioned from nodal load distribution on rigid diaphragms to `ShellMITC4` elements with Elastic Membrane Plate Sections.

### 4. Visualization Library Switch
- V3.5 replaces the `vfo` library with `opsvis` for more robust FEM visualization data extraction and Plotly integration.

---

## 🗑️ Removed Features

The following features from V3.0 have been removed to improve consistency and reduce user confusion:

- **Simplified Calculation Engines**: `SlabEngine`, `BeamEngine`, and `ColumnEngine` no longer support simplified calculation paths (HK Code Cl 6.1/6.2 simplified methods).
- **Comparison Views**: The "FEM vs Simplified" comparison table and associated visualizations have been removed.
- **Mixed UI Sections**: UI elements dedicated to simplified results have been purged from the dashboard.
- **Nodal Slab Loads**: Slabs now use area-based nodal distribution (equivalent to surface loads) compatible with shell elements.

---

## ✨ New Features in V3.5

### 1. Advanced Shell Modeling
- **ShellMITC4 Walls**: Proper stress distribution in core walls and coupled wall systems.
- **ShellMITC4 Slabs**: Accurate load distribution and membrane/plate behavior.
- **Auto-Mesh Generation**: Rule-based meshing for irregular panels and openings.

### 2. Full HK COP Wind Load Cases
- Implementation of all **24 wind directions** per HK Code of Practice on Wind Effects 2019.
- Automatic generation of **48 wind load combinations** (+/- directions).
- Total of **60+ load combinations** supported (ULS Gravity, ULS Wind, SLS).

### 3. Reaction Export Table
- New results section showing reactions (Fx, Fy, Fz, Mx, My, Mz) for all base nodes.
- **Export to CSV/Excel**: Download full reaction tables for foundation design.
- **Summation**: Automatic calculation of total building reactions per load case.

### 4. Professional UI/UX Overhaul
- **Meinhardt-Style Aesthetic**: Professional color palette (Blue #1E3A5F + Orange #F59E0B).
- **Optimized Layout**: FEM views are now prominent and "above the fold."
- **Scrollable Combinations**: Better management of large load case lists via scrollable containers with multi-select.
- **Mobile Guard**: Desktop-first design with mobile warning banners and collapsed sidebars for better accessibility.

### 5. Geometry Improvements
- **Secondary Beam Fix**: Secondary beams are now properly modeled in FEM and visible in all views.
- **Core Wall Centroid**: Ability to specify custom X, Y coordinates for core wall centroids.
- **Auto-Omit Columns**: Intelligent detection and removal of columns located within or very near core walls (1m threshold).

---

## 🛠️ Manual Migration Steps

Since project files are incompatible, follow these steps to migrate your design:

1. **Document V3.0 Inputs**: Open your project in V3.0 and note down:
   - Bay spans (X and Y)
   - Number of floors and floor heights
   - Live load class and SDL
   - Concrete grades (fcu) for all members
   - Core wall dimensions and location
2. **Re-enter in V3.5**: Open V3.5 and input the documented parameters.
3. **Verify Results**: Run the new FEM Analysis. You may notice slight differences in results due to the increased accuracy of shell elements compared to the old simplified/beam model.

---

## ❓ FAQ

### Q: Why can't I load my old projects?
**A:** V3.5 introduced a completely new data structure to handle shell elements and expanded load cases. Maintaining backward compatibility would have introduced significant technical debt and limited the performance of the new FEM-only architecture.

### Q: Is there an automated migration tool?
**A:** No. Due to the fundamental shift in how geometry is represented (Shell vs Beam), manual re-entry is required to ensure design integrity.

### Q: Why were simplified methods removed?
**A:** Having two sets of results (Simplified vs FEM) created confusion. By focusing on a pure FEM approach, we provide more accurate, code-compliant results that engineers can trust for preliminary design.

### Q: What is the maximum building height?
**A:** V3.5 is optimized for buildings up to **30 floors**. This limit ensures stable performance and reliable preliminary assumptions.

### Q: How do I export my results for foundation design?
**A:** Use the new **Reaction Forces Table** in the results section. You can download the data directly to Excel or CSV.

---

*Last Updated: 2026-02-03*
*Version: 3.5 Release*
