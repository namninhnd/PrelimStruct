# Draft: Local Axis Implementation for FEM Elements

## Requirements (confirmed)
- **Goal**: Consistent section axes — Mz = major-axis bending for ALL elements
- **Scope**: ALL element types — beams, columns, coupling beams, shell walls, shell slabs
- **Beam convention**: Strong axis (gravity bending) = Mz, with local z = vertical (Z-up)
- **Convention model**: ETABS-like — M33/Mz = major-axis bending always

## Technical Decisions (confirmed from prior session)
- **Fix approach**: Change vecxz per element (NOT swap Iy/Iz). Section property definitions stay as-is.
- **Coupling beams**: Same treatment as regular beams — same vecxz computation
- **Visualization**: Update labels + diagrams. Force values rounded to whole numbers for plotting (no decimals)
- **Verification**: Both ETABS benchmark comparison AND hand calculation tests

## Critical Research Finding: The Iy/Iz Mismatch Bug

### Current Bug (Compound Issue)
1. **vecxz vector** (misleadingly called `local_y` in code) is `(0,0,1)` for beams
   - With vecxz=(0,0,1): local_y = horizontal, local_z = vertical
   - My = gravity bending, Mz = lateral bending (in current orientation)

2. **Section properties** in `materials.py:328-329`:
   - `Iz = b * h³ / 12` (STRONG axis for h > b)
   - `Iy = h * b³ / 12` (WEAK axis)
   - Labels assume local_y = depth direction → inconsistent with vecxz=(0,0,1)

3. **Net effect for BEAMS**: My (gravity bending) uses Iy (weak axis) = WRONG stiffness

### Column-Specific Findings
- `local_y = (0, 1, 0)` hardcoded in `column_builder.py:126,150`
- Column local axes: local_x=(0,0,1), local_y=(1,0,0)=global X, local_z=(0,1,0)=global Y
- NO rotation angle in data model
- Width/depth have NO explicit mapping to global direction
- Cannot rotate column sections in plan

### Coupling Beam Findings
- `local_y = (0,0,1)` hardcoded at `beam_builder.py:575`
- Orientation detected (X vs Y spanning, line 533-554) but local_y NOT adjusted

### Shell Elements
- ShellMITC4: local axes from node ordering (no geomTransf) — already correct ✓
- Wall panels have `orientation` attribute (0° or 90°)

## Files Affected
1. `src/fem/materials.py` — Section property Iy/Iz assignment
2. `src/fem/fem_engine.py` — geomTransf setup
3. `src/fem/model_builder.py` — vecxz values
4. `src/fem/builders/beam_builder.py` — vecxz for beams + coupling beams
5. `src/fem/builders/column_builder.py` — vecxz for columns
6. `src/fem/force_normalization.py` — Sign convention
7. `src/fem/results_processor.py` — Force extraction
8. `src/fem/solver.py` — Force labeling
9. `src/ui/components/beam_forces_table.py` — Display
10. `src/ui/components/column_forces_table.py` — Display
11. `src/fem/visualization.py` — Force diagram rendering

## ETABS Convention Anchor (User-confirmed)
- **M33 = Mz = ALWAYS major axis bending** (non-negotiable)
- **M22 = My = ALWAYS minor axis bending**
- **I33 = Iz = strong axis MOI**, **I22 = Iy = weak axis MOI**
- This must hold for ALL element types: beams, columns, coupling beams

## Column Decision (CONFIRMED)
- **Convention**: Treat columns same as beams — ETABS standard
- **Depth (h)** = along local_y direction → Iz = b×h³/12 = STRONG axis → Mz = M33 = major-axis bending
- **Default orientation**: depth along default local_y (no rotation angle needed)
- **No rotation angle** will be added — fix only, no rotation ever
- **Square columns**: work naturally with any orientation

## Test Strategy Decision (CONFIRMED)
- **Infrastructure exists**: YES (pytest, 793 tests)
- **Automated tests**: TDD (Red-Green-Refactor)
- **Framework**: pytest
- **Existing test breakage**: Delete and rewrite affected tests (don't fix old wrong tests)
- **Benchmark**: Hand calculations primary, ETABS values later for cross-check
- **Agent-Executed QA**: ALWAYS (mandatory for all tasks)

## Sign Convention Decision (CONFIRMED)
- **Positive Mz = sagging** (tension at bottom) for ALL line elements (beams AND columns)
- Apply sign normalization in force_normalization.py after the axis fix

## Column Width/Depth Mapping (CONFIRMED)
- **Add explicit mapping**: b (width) and h (depth) clearly mapped to local axis directions
- Depth (h) aligns with local_y → Iz = b×h³/12 = STRONG axis MOI
- Width (b) aligns with local_z → Iy = h×b³/12 = WEAK axis MOI

## Visualization Scope (CONFIRMED - ALL FOUR)
1. **Axis labels on force diagrams** — e.g., "Mz (major)" instead of raw "My"/"Mz"
2. **Local axis arrows in views** — hidden by default, toggle to show in display options
3. **Force table headers** — update column headers/tooltips in beam & column forces tables
4. **Convention legend/annotation** — small reference showing local axis convention

## Scope Boundaries
- INCLUDE: Beam/column/coupling-beam local axis correction, section property mapping
- INCLUDE: Force result consistency (My, Mz, Vy, Vz physical meaning)
- INCLUDE: Shell wall/slab axes (already correct, just document)
- EXCLUDE: User-defined arbitrary rotation per-element
- EXCLUDE: Column rotation angle property
