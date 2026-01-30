"""
Centralized session state management for PrelimStruct Streamlit application.

This module defines all session state keys with their default values and provides
helper functions for consistent state initialization and access.
"""

import streamlit as st
from src.core.data_models import ProjectData


# Default values for all session state keys
STATE_DEFAULTS = {
    # Core Data
    "project": None,  # ProjectData instance - initialized separately
    
    # User Preferences
    "selected_combinations": {"LC1", "SLS1"},  # Active load combinations
    "omit_columns": {},  # Column omission approvals: dict[str, bool]
    
    # FEM View State
    "fem_active_view": "plan",  # Current view mode: "plan" | "elevation" | "3d"
    "fem_include_wind": True,  # Include wind loads in FEM views
    "fem_view_elev_dir": "X",  # Elevation direction for FEM Views section
    
    # FEM Analysis Cache
    "fem_preview_analysis_result": None,  # Cached AnalysisResult from OpenSees
    "fem_preview_analysis_message": "",  # Analysis status message
    
    # FEM Preview Display Toggles
    "fem_preview_show_nodes": False,  # Show nodes in FEM preview
    "fem_preview_show_supports": True,  # Show supports in FEM preview
    "fem_preview_show_loads": True,  # Show loads in FEM preview
    "fem_preview_show_labels": False,  # Show labels in FEM preview
    "fem_preview_show_slabs": True,  # Show slab elements in FEM preview
    "fem_preview_show_slab_mesh": True,  # Show slab mesh grid in FEM preview
    "fem_preview_show_ghost": True,  # Show ghost columns near core wall
    
    # FEM Preview Model Options
    "fem_preview_include_wind": True,  # Include wind loads in FEM preview model
    
    # FEM Preview View Settings
    "fem_preview_color_mode": "Element Type",  # Color scheme: "Element Type" | "Utilization"
    "fem_preview_grid_spacing": 1.0,  # Grid spacing for plan/elevation views (0.5-5.0m)
    "fem_preview_elevation_direction": "X",  # Elevation view direction: "X" | "Y"
    
    # FEM Preview Analysis Controls
    "fem_preview_overlay_analysis": False,  # Overlay OpenSees deflection/reactions on visualization
    
    # FEM Export Options
    "fem_export_view": "Plan View",  # Export view selection
    "fem_export_format": "png",  # Export format: "png" | "svg" | "pdf"
}


# Keys that require runtime initialization (based on dynamic project data)
# These cannot have static defaults and must be initialized after project is created
DEFERRED_KEYS = [
    "fem_view_floor_select",  # Floor index selector for FEM Views section
    "fem_preview_floor_level",  # Selected floor elevation for plan view (m)
    "fem_preview_analysis_pattern",  # Analysis load pattern selection (gravity or wind)
]


def init_session_state() -> None:
    """
    Initialize all session state keys with their default values.
    
    This function should be called once at the start of the Streamlit app
    to ensure all required keys exist with appropriate defaults.
    
    Note:
        - Keys in STATE_DEFAULTS are initialized if not already present
        - project key receives a new ProjectData() instance if None
        - DEFERRED_KEYS are not initialized here (require runtime data)
    """
    # Initialize all static defaults
    for key, default in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
    
    # Initialize project if not already present
    if st.session_state.project is None:
        st.session_state.project = ProjectData()


def get_state(key: str, default=None):
    """
    Get session state value with fallback to default.
    
    Args:
        key: Session state key to retrieve
        default: Fallback value if key not found (defaults to None)
    
    Returns:
        Value from session state, STATE_DEFAULTS, or provided default
    
    Example:
        >>> wind_enabled = get_state("fem_include_wind", True)
        >>> project = get_state("project")
    """
    return st.session_state.get(key, STATE_DEFAULTS.get(key, default))


def set_state(key: str, value) -> None:
    """
    Set session state value.
    
    Args:
        key: Session state key to set
        value: Value to store
    
    Example:
        >>> set_state("fem_active_view", "elevation")
        >>> set_state("selected_combinations", {"LC1", "LC2"})
    """
    st.session_state[key] = value
