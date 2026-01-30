# v3.6 Session State Keys Inventory

**Generated:** 2026-01-30  
**Total Keys:** 24

## Summary

This inventory catalogs all session state keys used in `app.py` for state management across Streamlit reruns. Keys are categorized by function and documented with their data types, usage locations, and purposes.

## Session State Keys

| Key | Lines | Type | Purpose |
|-----|-------|------|---------|
| project | 981-982, 1002-1003, 1013, 1016, 1021, 1025, 1031, 1034, 1048, 1065, 1083, 1092, 1105, 1108, 1111, 1124, 1161, 1166, 1184, 1713, 1766 | ProjectData | Main project data container; initialized at startup; stores all geometry, loads, materials, and lateral system configuration |
| omit_columns | 1517-1518, 1522-1523, 1530, 1533, 1877, 2048 | dict[str, bool] | Column omission approvals near core wall; maps column IDs (e.g., "C1") to boolean approval status |
| selected_combinations | 1597-1599, 1625, 1634, 1639, 1650, 1655, 1657, 1664, 1668, 1670, 1682, 1690 | set[str] | Active load combinations for analysis; defaults to {"LC1", "SLS1"}; user toggles via checkboxes |
| fem_include_wind | 1872 | bool | Include wind loads in FEM views; accessed via .get() with default True |
| fem_active_view | 1928, 1930, 1932, 1935 | str | Active FEM view type; values: "plan", "elevation", "3d"; defaults to "plan" |
| fem_preview_analysis_result | 2148, 2151 | AnalysisResult \| None | Cached FEM analysis result object from OpenSees solver |
| fem_preview_analysis_message | 2149, 2152 | str \| None | Analysis status message (success/warning text) |
| fem_preview_show_nodes | 2012 | bool | Widget key: Show nodes in FEM preview (default: False) |
| fem_preview_show_supports | 2014 | bool | Widget key: Show supports in FEM preview (default: True) |
| fem_preview_show_loads | 2016 | bool | Widget key: Show loads in FEM preview (default: True) |
| fem_preview_show_labels | 2018 | bool | Widget key: Show labels in FEM preview (default: False) |
| fem_preview_show_slabs | 2022 | bool | Widget key: Show slab elements in FEM preview (default: True) |
| fem_preview_show_slab_mesh | 2024 | bool | Widget key: Show slab mesh grid in FEM preview (default: True) |
| fem_preview_show_ghost | 2029 | bool | Widget key: Show ghost columns near core wall (default: True) |
| fem_preview_include_wind | 2035 | bool | Widget key: Include wind loads in FEM preview model (default: True) |
| fem_preview_floor_level | 2059 | float | Widget key: Selected floor elevation for plan view (m) |
| fem_preview_color_mode | 2093 | str | Widget key: Color scheme selection ("Element Type" or "Utilization") |
| fem_preview_grid_spacing | 2103 | float | Widget key: Grid spacing for plan/elevation views (0.5-5.0m, default: 1.0) |
| fem_preview_overlay_analysis | 2126 | bool | Widget key: Overlay OpenSees deflection/reactions on visualization (default: False) |
| fem_preview_analysis_pattern | 2133 | str | Widget key: Analysis load pattern selection (gravity or wind) |
| fem_preview_run_analysis | 2136 | N/A | Widget key: Button to trigger FEM analysis (no state storage) |
| fem_preview_elevation_direction | 2189 | str | Widget key: Elevation view direction ("X" or "Y") |
| fem_view_floor_select | 1919 | int | Widget key: Floor index selector for FEM Views section |
| fem_view_elev_dir | 1969 | str | Widget key: Elevation direction for FEM Views section ("X" or "Y") |

## Key Categories

### Core Data
- **project**: Primary data model (ProjectData)

### User Preferences
- **omit_columns**: Column omission map (dict)
- **selected_combinations**: Load combination selections (set)

### FEM View State
- **fem_active_view**: Current view mode (str: plan/elevation/3d)
- **fem_include_wind**: Wind load inclusion flag (bool)

### FEM Analysis Cache
- **fem_preview_analysis_result**: Cached analysis results (AnalysisResult)
- **fem_preview_analysis_message**: Status message (str)

### Widget Keys (FEM Preview Controls)
13 keys prefixed with `fem_preview_` control visualization settings:
- Display toggles: show_nodes, show_supports, show_loads, show_labels, show_slabs, show_slab_mesh, show_ghost
- Model options: include_wind
- View settings: floor_level, color_mode, grid_spacing, elevation_direction
- Analysis controls: overlay_analysis, analysis_pattern, run_analysis

### Widget Keys (FEM Views Section)
2 keys prefixed with `fem_view_` for relocated FEM Views UI:
- floor_select: Floor selection dropdown
- elev_dir: Elevation view direction

## Notes

1. **Streamlit Widget Keys**: Many keys (prefixed `fem_preview_*`, `fem_view_*`) are widget keys that Streamlit manages internally. These don't require manual `.session_state` reads but appear in grep output due to `key=` parameters.

2. **Access Patterns**:
   - `.get()` method: Used for optional keys with defaults (e.g., `fem_include_wind`, `omit_columns`)
   - Direct access: Used for required keys (e.g., `project`)
   - Bracket notation: Used for setting values (e.g., `st.session_state["fem_active_view"] = "plan"`)

3. **Initialization**: Only 3 keys are explicitly initialized:
   - `project` (line 981-982)
   - `omit_columns` (line 1517-1518)
   - `selected_combinations` (line 1597-1599)

4. **v3.6 Migration Impact**: The relocation of FEM Views (Task 21) introduced duplicate widget keys for floor selection and elevation direction. Future refactoring may consolidate these.

## Verification

```bash
# Count table rows (excluding header and dividers)
grep -c "^| [^-]" .sisyphus/evidence/v36-session-keys.md
# Expected: >= 24
```

**Result:** 24 keys documented ✓
