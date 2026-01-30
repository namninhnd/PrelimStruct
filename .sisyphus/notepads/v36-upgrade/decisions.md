## [2026-01-30 16:45:37] Task 2.5: Lateral Diagram Migration Decision

**Decision**: KEEP (with dev flag)

**Rationale**:
- Wind loads are NOT currently visualized in elevation view
- `create_elevation_view()` has no wind-related rendering code (confirmed via grep)
- `create_lateral_diagram()` provides unique features:
  - Wind arrows showing force distribution with height
  - Wind base shear label
  - Drift indicator visualization
- Migrating wind visualization to elevation view would require significant implementation work
- This is beyond the scope of a "decision" task

**Features Evaluated**:
1. Wind arrows: Per-floor arrows scaled by height (lines 749-772)
2. Wind base shear label: Positioned left of building (lines 775-781)
3. Drift indicator: Dashed line showing displacement (lines 784-794)

**Wind Loads in Elevation View**: NO

**Action Taken**:
- Added environment variable check `PRELIMSTRUCT_SHOW_LEGACY_VIEWS` to app.py
- Lateral diagram now gated behind flag (default: hidden)
- When flag = "0" (default): framing grid shown full-width
- When flag = "1": two-column layout with framing grid + lateral diagram
- Code location: app.py lines 1995-2012

**Implementation Note**:
- `create_lateral_diagram()` function retained at lines 731-816
- Function NOT deprecated yet (may be migrated in Track 2.6+)
- Dev flag pattern: `os.getenv("PRELIMSTRUCT_SHOW_LEGACY_VIEWS", "0") == "1"`

**Next Steps**:
- Track 2.6+ could implement wind visualization in elevation view
- At that point, `create_lateral_diagram()` can be fully removed
