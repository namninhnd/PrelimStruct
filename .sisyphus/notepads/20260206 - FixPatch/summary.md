PrelimStruct v3-5 Patch Summary
Date: 2026-02-06

Scope
- Fixed repeated "No loads were applied / all-zero forces" warnings by running wind load cases only when wind is enabled, and by limiting UI load-case options to analyzed cases.
- Fixed Streamlit Arrow conversion crash caused by mixed index types (numeric node IDs + TOTAL row) in reaction table rendering.
- Corrected axial-force sign/display consistency so compression is shown positive and axial accumulation matches expected top-to-bottom behavior.
- Unified floor labels across selectors to HK-style format (e.g., G/F (+0.00), 1/F (+3.20)).
- Replaced "Element Overrides" concept with "Section Properties" and made section edits directly drive FEM inputs.
- Added rectangular column section input support (width/depth) and kept backward compatibility with square-column override.

Key File Changes
- `src/ui/views/fem_views.py`
  - Conditional load-case execution (DL/SDL/LL by default; wind cases only when enabled).
  - Load-case selector now shows only available result cases.
  - Floor label formatting now uses shared utility.
- `src/ui/components/reaction_table.py`
  - Cast display index to string before `st.dataframe` to avoid ArrowInvalid on mixed index types.
- `src/fem/visualization.py`
  - Added unified node-force display helper for i/j ends.
  - Normalized axial display to compression-positive in both elevation and plan force overlays.
- `src/ui/components/column_forces_table.py`
  - Axial values normalized to compression-positive.
  - Floor dropdown uses shared floor-label formatter.
- `src/ui/components/beam_forces_table.py`
  - Floor dropdown uses shared floor-label formatter.
- `src/ui/floor_labels.py`
  - New shared floor-label formatting utilities.
- `app.py`
  - "Element Overrides" replaced by always-on "Section Properties" with selected-section summary.
  - Added rectangular column width/depth controls.
  - `run_calculations` now applies section-property updates to project data (instead of no-op), including slab self-weight refresh for DL.

Validation Evidence
- `pytest tests/test_reaction_table.py tests/test_column_forces_table.py tests/test_multi_load_case.py -q` -> 18 passed
- `pytest tests/test_force_normalization.py tests/test_visualization_characterization.py -q` -> 38 passed
- `pytest tests/test_column_forces_table.py tests/test_reaction_table.py tests/test_multi_load_case.py tests/test_force_normalization.py -q` -> 37 passed
- `pytest tests/test_integration_e2e.py -k "fem_views or elevation_view_generation or plan_view_generation" -q` -> 2 passed
- `python -m compileall src` -> success
- `python -m compileall app.py src/ui/views/fem_views.py src/ui/components/beam_forces_table.py src/ui/components/column_forces_table.py src/ui/floor_labels.py && python -c "print('ok')"` -> ok

Environment Note
- LSP diagnostics are unavailable in this environment due known Windows + Bun v1.3.5 crash guard.
