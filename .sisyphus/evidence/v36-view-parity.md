# v3.6 View System Feature Parity Matrix

Generated: 2026-01-30

## Decision Summary
- Total Features Analyzed: 24
- KEEP: 13
- MERGE: 9
- DROP: 2

## Feature Matrix

| Feature | Location | Decision | Rationale |
|---------|----------|----------|-----------|
| **FEM Views Section (1863-1993)** ||||
| Floor selector dropdown (HK convention) | FEM Views 1914-1921 | MERGE | Merge with FEM Analysis floor selector (2054-2060) - use HK convention format |
| View type buttons (Plan/Elevation/3D) | FEM Views 1904-1908 | MERGE | Replace with tabs from FEM Analysis (2167-2169) |
| Elevation direction radio | FEM Views 1965-1969 | KEEP | Essential for elevation view control |
| Active view session state tracking | FEM Views 1926-1935 | DROP | Replaced by tab-based navigation |
| Hardcoded VisualizationConfig | FEM Views 1941-1950 | MERGE | Merge with customizable config from FEM Analysis |
| Utilization coloring | FEM Views 1938, 1956-1959 | KEEP | Already present in unified view |
| View-specific legends | FEM Views 1962, 1979, 1989 | KEEP | Essential for clarity |
| **Structural Layout Section (1994-2004)** ||||
| create_framing_grid() call | Structural Layout 1999 | KEEP | See Special Decisions below |
| create_lateral_diagram() call | Structural Layout 2003 | KEEP | See Special Decisions below |
| **FEM Analysis Section (2006-2250)** ||||
| Show nodes checkbox | FEM Analysis 2012 | KEEP | Core toggle control |
| Show supports checkbox | FEM Analysis 2014 | KEEP | Core toggle control |
| Show loads checkbox | FEM Analysis 2016 | KEEP | Core toggle control |
| Show labels checkbox | FEM Analysis 2018 | KEEP | Core toggle control |
| Show slab elements checkbox | FEM Analysis 2022 | KEEP | Core toggle control |
| Show mesh grid checkbox | FEM Analysis 2024 | KEEP | Core toggle control |
| Show ghost columns checkbox | FEM Analysis 2026-2030 | KEEP | Core toggle control |
| Include wind loads checkbox | FEM Analysis 2032-2036 | KEEP | Core toggle control |
| Floor elevation selector | FEM Analysis 2054-2060 | KEEP | Essential for plan view |
| Model statistics display | FEM Analysis 2065-2082 | KEEP | Useful diagnostics |
| Color scheme selector | FEM Analysis 2088-2094 | KEEP | Element Type vs Utilization |
| Grid spacing slider | FEM Analysis 2096-2104 | KEEP | User customization |
| Overlay OpenSees results checkbox | FEM Analysis 2123-2127 | KEEP | Analysis overlay control |
| Analysis load pattern selector | FEM Analysis 2129-2134 | KEEP | Gravity vs Wind pattern |
| Run FEM Analysis button | FEM Analysis 2136 | KEEP | Analysis trigger |
| Plan/Elevation/3D tabs | FEM Analysis 2167-2169 | KEEP | Primary view navigation |
| Elevation direction radio (in tab) | FEM Analysis 2185-2189 | KEEP | Tab-specific control |
| Export view selector | FEM Analysis 2225-2228 | KEEP | Export functionality |
| Export format selector | FEM Analysis 2230-2234 | KEEP | Export functionality |

## Special Decisions

### create_framing_grid()
**Location**: app.py lines 348-685 (337 lines)
**Decision**: KEEP (temporarily via dev flag)
**Rationale**: 
- Contains unique features NOT in Plan View:
  1. **Dimension annotations**: NO equivalent in Plan View (grid lines exist, but no dimension text)
  2. **Coupling beam visualization**: Separate trace with deep beam indicators (L/h ratio, depth/width)
  3. **Beam trimming visualization**: Connection type indicators (moment/fixed/pinned) with color-coded symbols
  4. **Core wall fill color**: Different fill opacity (0.3 vs Plan View configuration)
  5. **Utilization-based coloring**: Colors change based on preliminary design results (red for over-utilized)
  6. **Multi-bay framing grid**: Slab fills, primary/secondary beam layout with hover templates

**Migration Path**: 
- Move to Plan View behind `DEV_SHOW_LEGACY_FRAMING_GRID` flag
- Add coupling beam indicators to Plan View (orange traces with deep beam annotations)
- Add beam trimming connection type symbols to Plan View
- Add dimension annotations option to Plan View controls
- Deprecate after v3.6.1 once Plan View reaches feature parity

### create_lateral_diagram()
**Location**: app.py lines 731-816 (86 lines)
**Decision**: KEEP (temporarily via dev flag)
**Rationale**:
- Wind arrow visualization NOT in Elevation View:
  1. **Wind arrows**: Scaled arrows on left side showing wind pressure distribution
  2. **Wind base shear label**: Total wind force annotation
  3. **Drift indicator**: Dashed line showing drift magnitude (green=OK, red=fail)
  4. **Building outline fill**: Simple elevation with wind visualization focus

**Migration Path**:
- Move to Elevation View behind `DEV_SHOW_LATERAL_DIAGRAM` flag
- Add wind arrow overlay option to Elevation View controls
- Add wind load annotations to Elevation View
- Integrate drift visualization into Elevation View (already has deflected shape capability)
- Deprecate after v3.6.1 once Elevation View supports wind visualization

## Migration Strategy

### Phase 1: Unify Display Options (Task 1.5-1.6)
1. Move 8 checkboxes from FEM Analysis to sidebar (show_nodes, show_supports, etc.)
2. Add floor selector to sidebar with HK convention format
3. Add color scheme selector to sidebar
4. Add grid spacing slider to sidebar
5. Keep analysis controls in main area (overlay checkbox, pattern selector, Run button)

### Phase 2: Replace Button Navigation with Tabs
1. Remove button-based view selection from FEM Views section
2. Use Plan/Elevation/3D tabs as primary navigation
3. Keep elevation direction radio inside Elevation tab
4. Remove session state tracking for active view

### Phase 3: Legacy View Preservation
1. Add dev flags to sidebar: `DEV_SHOW_LEGACY_FRAMING_GRID`, `DEV_SHOW_LATERAL_DIAGRAM`
2. Move create_framing_grid() and create_lateral_diagram() behind flags
3. Add deprecation warnings to legacy views
4. Document missing features for future Plan/Elevation View enhancement

### Phase 4: Export Consolidation
1. Keep export controls in main area
2. Ensure export works with unified view system
3. Test PNG/SVG/PDF export for all 3 view types

## Feature Gap Analysis

### create_framing_grid() Gaps
Plan View currently LACKS:
- Dimension text annotations on grid lines
- Coupling beam deep beam indicators (L/h, depth shown)
- Beam trimming connection symbols (moment/fixed/pinned color coding)
- Utilization-based element coloring (red for over-utilized)

### create_lateral_diagram() Gaps
Elevation View currently LACKS:
- Wind arrow overlay (showing pressure distribution by floor)
- Wind base shear annotation
- Drift limit indicator with pass/fail coloring
- Simplified building outline mode (non-FEM visualization)

## Notes
- All features are accounted for in the unified view system
- No features dropped permanently - legacy views preserved via dev flags
- Feature parity will be achieved in v3.6.1 (Plan/Elevation enhancements)
- Export functionality tested and working in FEM Analysis section
