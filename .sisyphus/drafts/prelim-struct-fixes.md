# Draft: PrelimStruct FEM Analysis Fixes

## Requirements (confirmed)

### Issue 1: Reduce line elements to 5 nodes (equal spacing)
- **Current**: Beams and columns use `NUM_SUBDIVISIONS = 6` (creates 6 sub-elements, 7 nodes)
- **Location**: `src/fem/builders/beam_builder.py:134`, `src/fem/builders/column_builder.py:78`
- **Requested**: Change to 5 nodes (4 sub-elements or 5 equal-spaced nodes)
- **Clarification needed**: "5 nodes" likely means 4 subdivisions (creates 5 nodes total including endpoints)

### Issue 2: Fix slab mesh to match beam nodes
- **Current**: Slab mesh uses `beam_subdivision_count=6` (default in `slab_element.py:177`)
- **Location**: `src/fem/slab_element.py:170-204`, `src/fem/builders/slab_builder.py:136-144`
- **Problem**: Slab uses hardcoded 6 elements per direction, independent of beam subdivision
- **Solution**: Align slab mesh with beam subdivision points (use same count as beams)
- **Note**: `existing_nodes` dict is already used for node sharing, but element counts may mismatch

### Issue 3: Area loads on each mesh element
- **Current**: Surface loads are applied per slab element in `slab_builder.py:227-252`
- **Location**: `src/fem/builders/slab_builder.py:apply_surface_loads()`
- **Current behavior**: `apply_surface_loads()` iterates `slab_element_tags` and applies to each
- **User says**: "apply on each mesh, instead of the whole bay currently"
- **Need to verify**: May already be correct? Need to check if load is applied per element or accumulated

### Issue 4: Beam force diagram from table data
- **Current**: Force diagrams use `ResultsProcessor.extract_section_forces()` 
- **Location**: `src/fem/visualization.py:2520-2547`, `src/fem/visualization.py:1046-1300`
- **Requested**: Plot force diagram using the same data as the beam force table
- **Table component**: `src/ui/components/beam_forces_table.py`
- **Solution**: Create unified data extraction, use BeamForcesTable data for diagram

### Issue 5: Add Column Section Forces table + plot
- **Current**: Only beam forces table exists (`beam_forces_table.py`)
- **Location**: `src/ui/components/` - no column forces table
- **Requested**: Add similar table for columns, with force diagram plotting
- **Column parent tracking**: `parent_column_id` in `column_builder.py:127`
- **Solution**: Create `column_forces_table.py`, add to fem_views.py

### Issue 6: Fix reaction forces table for all load cases
- **Current**: `ReactionTable` in `src/ui/components/reaction_table.py`
- **Location**: `reaction_table.py:10-21`, `fem_views.py:808-814`
- **Problem**: "fails to show reaction forces" for some load cases
- **Results dict**: `fem_analysis_results_dict` stores all load case results
- **Possible issues**: 
  - `node_reactions` may be empty for some load cases
  - Solver may not extract reactions correctly for all patterns
- **Solver location**: `src/fem/solver.py:191-196`

### Issue 7: Rename "Element Overrides" to "Section Properties"
- **Current**: `_render_overrides()` in `src/ui/sidebar.py:632`
- **Label**: Line 638: `st.markdown("##### Section Properties")` - ALREADY CORRECT!
- **Requested behavior**: 
  - Show current sections selected (from calculation results)
  - Auto-update model when user changes properties (including self-weight in DL)
- **Current behavior**: Overrides affect FEM model build via options

### Issue 8: Allow rectangular column section input
- **Current**: `src/ui/sidebar.py:687-710` - has both width and depth inputs
- **Problem**: Line 710: `override_column_size = max(override_column_width, override_column_depth)`
- **This forces square!** The max() makes it effectively square
- **Solution**: Return both width and depth separately, use in column builder

## Technical Decisions

1. **5 nodes subdivision**: Use `NUM_SUBDIVISIONS = 4` to get 5 nodes (0, 0.25L, 0.5L, 0.75L, 1.0L)
2. **Slab mesh alignment**: Pass beam subdivision count to slab generator, ensure node sharing
3. **Force diagram consistency**: Create shared data extraction function used by both table and diagram
4. **Column forces**: Mirror BeamForcesTable pattern for columns
5. **Reaction table debug**: Add logging to trace why some load cases have empty reactions

## Research Findings

### Current Subdivision Structure
- `beam_builder.py`: NUM_SUBDIVISIONS = 6 (line 134)
- Creates nodes at 1/6, 2/6, 3/6, 4/6, 5/6 positions
- For 5 nodes: need nodes at 0, 0.25, 0.5, 0.75, 1.0 positions (4 sub-elements)

### Slab Mesh Generation
- `SlabMeshGenerator.generate_mesh()` accepts `elements_along_x` and `elements_along_y`
- Default uses `beam_subdivision_count` parameter (default 6)
- `SlabBuilder.create_slabs()` calculates elements based on bay proportions

### Force Data Flow
1. OpenSees `eleForce()` -> `solver.py:extract_results()` 
2. Results stored in `AnalysisResult.element_forces`
3. `ResultsProcessor.extract_section_forces()` for visualization
4. `BeamForcesTable._extract_beam_forces()` for table

### Reaction Forces Data Flow
1. `solver.py:193-196` extracts reactions: `ops.nodeReaction(node_tag)`
2. Stored in `result.node_reactions[node_tag]`
3. Only stored if `any(abs(r) > 1e-10 for r in reaction)`
4. `ReactionTable` reads from `results_dict`

## User Decisions (Confirmed)

1. **5 nodes clarification**: YES - 5 total nodes including endpoints = 4 sub-elements
   - Nodes at: 0, 0.25L, 0.5L, 0.75L, 1.0L

2. **Section Properties display**: Show current calculated sizes, allow user to edit
   - Display beam widths/depths from design calculation
   - Display column widths/depths from design calculation
   - User edits override calculated values

3. **Self-weight update behavior**: 
   - During LOCK stage: Users can edit section properties freely (no rebuild)
   - On UNLOCK: Model rebuilds with new section properties
   - Self-weight in DL case updates based on new section sizes
   - Analysis NOT auto-triggered (user must click "Run FEM Analysis")

## Scope Boundaries
- INCLUDE: All 8 issues as stated
- EXCLUDE: New features not mentioned
- EXCLUDE: Performance optimization unless directly related
