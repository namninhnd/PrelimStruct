
## Load Combination UI Implementation
- **Scrollable Lists**: Streamlit v1.30.0+ supports `st.container(height=...)` which creates a fixed-height scrollable container. This is essential for managing large lists like 48 wind load combinations. I implemented this in `app.py` and `src/ui/sidebar.py`.
- **Session State**: Using `st.session_state` to store a Set of selected IDs is efficient for multi-select.
- **Code Duplication**: `app.py` duplicates logic from `src/ui/sidebar.py`. I updated both to maintain consistency, but future refactoring should consolidate this by importing `render_sidebar` in `app.py`.
- **Active vs Selected**: `ProjectData.load_combination` stores a SINGLE active combination (for simplified display), while `FEMAnalysisSettings.load_combinations` (list) should store the full selection for analysis. The current UI handles both: multi-select for the list, and a dropdown for the single "active" combination.
