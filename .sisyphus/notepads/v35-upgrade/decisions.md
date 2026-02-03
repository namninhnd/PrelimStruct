# V3.5 Upgrade Decisions

## Architecture Decisions

### ADR-001: Pure FEM Architecture
**Decision**: Remove all simplified engines, use FEM-only
**Rationale**: Simplified methods no longer needed with shell element accuracy
**Impact**: Breaking change - v3.0 projects incompatible

### ADR-002: ShellMITC4 Elements
**Decision**: Use ShellMITC4 for both walls and slabs
**Rationale**: Industry standard for tall building analysis, validated against ETABS
**Impact**: Requires Plate Fiber Section for walls, Elastic Membrane Plate for slabs

### ADR-003: 30 Floor Limit
**Decision**: Hard limit of 30 floors maximum
**Rationale**: Conservative for preliminary design tool, ensures performance
**Impact**: Input validation needed in UI

### ADR-004: No AI Chat in v3.5
**Decision**: Defer AI Chat feature to v3.6
**Rationale**: Reduces scope and risk for v3.5 release
**Impact**: Users will use existing AI features (design review, optimization)

## UI/UX Decisions

### Colors
- Brand blue: #1E3A5F (NO PURPLE)
- Accent orange: TBD from wireframes
- Spacing scale: 8px base (4/8/16/32/64px)

### Layout
- FEM views must be above fold (no scrolling)
- Core wall selector visible on page load
- Load combinations in scrollable list with multi-select

## Pending Decisions
- [ ] Final color values from wireframes
- [ ] Mesh density for shell elements (elements per bay)
- [ ] ETABS validation tolerance (currently 10%)
