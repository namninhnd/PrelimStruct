"""
Unified FEM Views Module for PrelimStruct v3.5.

This module provides a consolidated interface for FEM visualization,
combining model building, view controls, and analysis result overlays
into a single reusable component.
"""

import streamlit as st
import logging
from typing import Optional, Dict, Any, List, Tuple

from src.core.data_models import ProjectData
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.fem_engine import FEMModel
from src.fem.visualization import (
    create_plan_view,
    create_elevation_view,
    create_3d_view,
    VisualizationConfig,
    get_model_statistics,
    export_plotly_figure_image
)
from src.ui.components.reaction_table import ReactionTable

logger = logging.getLogger(__name__)

# Session state keys
CACHE_KEY_MODEL = "fem_model_cache"
CACHE_KEY_HASH = "fem_model_hash"
KEY_VIEW_MODE = "fem_view_mode_tabs"


def _get_cache_key(project: ProjectData, options: ModelBuilderOptions) -> str:
    """Generate a stable cache key for the FEM model based on inputs."""
    geo = project.geometry
    lat = project.lateral
    mat = project.materials
    cg = lat.core_geometry
    
    key_parts = [
        f"floors:{geo.floors}",
        f"story_height:{geo.story_height}",
        f"bays_x:{geo.num_bays_x}",
        f"bays_y:{geo.num_bays_y}",
        f"bay_x:{geo.bay_x}",
        f"bay_y:{geo.bay_y}",
        f"fcu_slab:{mat.fcu_slab}",
        f"fcu_beam:{mat.fcu_beam}",
        f"fcu_column:{mat.fcu_column}",
        f"core_config:{cg.config if cg else 'None'}",
        f"core_lx:{cg.length_x if cg else 0}",
        f"core_ly:{cg.length_y if cg else 0}",
        f"core_thick:{cg.wall_thickness if cg else 0}",
        f"core_flange:{cg.flange_width if cg else 0}",
        f"core_opening:{cg.opening_width if cg else 0}",
        f"core_cx:{lat.custom_center_x if lat else 0}",
        f"core_cy:{lat.custom_center_y if lat else 0}",
        f"beam_w:{project.primary_beam_result.width if project.primary_beam_result else 0}",
        f"beam_d:{project.primary_beam_result.depth if project.primary_beam_result else 0}",
        f"col_dim:{project.column_result.dimension if project.column_result else 0}",
        f"wind:{options.apply_wind_loads}",
        f"slabs:{options.include_slabs}",
        f"sec_dir:{options.secondary_beam_direction}",
        f"sec_num:{options.num_secondary_beams}",
        f"omit_cols:{sorted(list(options.suggested_omit_columns))}",
        f"trim:{options.trim_beams_at_core}",
    ]
    
    return "|".join(key_parts)


def _get_or_build_cached_model(project: ProjectData, options: ModelBuilderOptions) -> FEMModel:
    """Retrieve FEM model from cache or build a new one if inputs changed."""
    current_hash = _get_cache_key(project, options)
    
    # Initialize cache if needed
    if CACHE_KEY_MODEL not in st.session_state:
        st.session_state[CACHE_KEY_MODEL] = None
    if CACHE_KEY_HASH not in st.session_state:
        st.session_state[CACHE_KEY_HASH] = ""
        
    cached_model = st.session_state[CACHE_KEY_MODEL]
    cached_hash = st.session_state[CACHE_KEY_HASH]
    
    # Check if rebuild needed
    if cached_model is None or cached_hash != current_hash:
        with st.spinner("Building FEM model..."):
            model = build_fem_model(project, options)
            st.session_state[CACHE_KEY_MODEL] = model
            st.session_state[CACHE_KEY_HASH] = current_hash
            logger.info(f"Rebuilt FEM model with hash: {current_hash[:20]}...")
            
            # Clear stale analysis results when model changes (prevents mismatch)
            _clear_analysis_state()
            
            return model
            
    return cached_model


def _clear_analysis_state() -> None:
    """Clear all FEM analysis state to prevent stale data."""
    keys_to_clear = [
        "fem_preview_analysis_result",
        "fem_analysis_status", 
        "fem_analysis_message",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    # Also unlock inputs when analysis is cleared
    st.session_state["fem_inputs_locked"] = False


def _is_inputs_locked() -> bool:
    """Check if FEM inputs are locked (analysis has been run)."""
    return st.session_state.get("fem_inputs_locked", False)


def _lock_inputs() -> None:
    """Lock FEM inputs after analysis runs."""
    st.session_state["fem_inputs_locked"] = True


def _unlock_inputs() -> None:
    """Unlock FEM inputs and clear analysis state."""
    _clear_analysis_state()
    st.session_state["fem_inputs_locked"] = False


def _analysis_result_to_displacements(result: Any) -> Optional[Dict[int, Tuple[float, float, float]]]:
    """Convert analysis result to displacement format expected by visualization."""
    if not result or not hasattr(result, "node_displacements") or not result.node_displacements:
        return None
        
    displacements = {}
    for node_tag, values in result.node_displacements.items():
        if len(values) >= 3:
            # Take only dx, dy, dz translation
            displacements[node_tag] = (values[0], values[1], values[2])
            
    return displacements


def _format_floor_label(z: float, floor_levels: List[float]) -> str:
    """Format floor elevation as HK convention: G/F, 1/F, 2/F, etc."""
    if not floor_levels:
        return f"Z = {z:.2f}m"
        
    # Sort levels and find index with tolerance
    sorted_levels = sorted(floor_levels)
    floor_index = -1
    
    for i, level in enumerate(sorted_levels):
        if abs(level - z) < 0.01:
            floor_index = i
            break
            
    if floor_index == -1:
        return f"Z = {z:.2f}m"
        
    # Ground floor is index 0, then 1/F, 2/F, etc.
    if floor_index == 0:
        return f"G/F (+{z:.2f})"
    else:
        return f"{floor_index}/F (+{z:.2f})"


def render_unified_fem_views(
    project: ProjectData,
    analysis_result: Any = None,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Render unified FEM visualization with all controls.
    
    Args:
        project: The project data containing geometry and settings.
        analysis_result: Optional result object from OpenSees analysis.
        config_overrides: Optional dictionary to override default visualization config.
    """
    if config_overrides is None:
        config_overrides = {}

    # --- 0. Initialize Session State Defaults ---
    default_view_settings = {
        "fem_view_show_nodes": False,
        "fem_view_show_slabs": True,
        "fem_view_show_supports": True,
        "fem_view_show_mesh": True,
        "fem_view_show_loads": True,
        "fem_view_show_ghost": True,
        "fem_view_show_labels": False,
        "fem_view_color_mode": "Element Type",
        "fem_view_show_deformed": False,
        "fem_view_show_reactions": False,
        "fem_view_force_type": "None",
        "fem_view_force_scale": 1.0,
        "fem_view_force_auto_scale": True,
        "fem_active_tab": "Plan View",  # Track active tab for force rendering optimization
    }
    
    for key, default in default_view_settings.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # --- 1. Sidebar Controls / Builder Options ---
    # These affect the model build itself, so we check them first
    
    # Secondary beams settings (often from sidebar state in app.py)
    secondary_along_x = st.session_state.get("secondary_along_x", False)
    num_secondary_beams = st.session_state.get("num_secondary_beams", 0)
    
    # Omitted columns
    omit_columns_map = st.session_state.get("omit_columns", {})
    suggested_omit = [col for col, omit in omit_columns_map.items() if omit]
    
    # Wind toggle (triggers rebuild) - only enable if wind_result exists
    # V3.5: Default to False since WindEngine was removed
    has_wind_result = project.wind_result is not None
    include_wind = st.session_state.get("fem_include_wind", False) and has_wind_result
    
    options = ModelBuilderOptions(
        include_core_wall=True,
        trim_beams_at_core=True,
        apply_gravity_loads=True,
        apply_wind_loads=include_wind,
        apply_rigid_diaphragms=True,
        secondary_beam_direction="X" if secondary_along_x else "Y",
        num_secondary_beams=num_secondary_beams,
        omit_columns_near_core=True,
        suggested_omit_columns=tuple(suggested_omit), # Tuple for immutability/hashing
        include_slabs=True
    )
    
    # --- 2. Build or Retrieve Model ---
    model = _get_or_build_cached_model(project, options)
    
    # Get basic stats for controls
    stats = get_model_statistics(model)
    floor_levels = stats.get("floor_elevations", [])
    
    # --- 3. Prepare Visualization Config ---
    
    # Map friendly force names to codes
    force_type_map = {
        "None": None,
        "N (Normal)": "N",
        "Vy (Shear Y)": "Vy",
        "Vz (Shear Z)": "Vz",
        "My (Moment Y)": "My",
        "Mz (Moment Z)": "Mz",
        "T (Torsion)": "T"
    }
    selected_force = st.session_state.fem_view_force_type
    force_code = force_type_map.get(selected_force)

    force_scale = st.session_state.fem_view_force_scale
    if st.session_state.fem_view_force_auto_scale:
        force_scale = -1.0
    
    # Debug prints removed to prevent console spam and UI lag

    viz_config = VisualizationConfig(
        show_nodes=st.session_state.fem_view_show_nodes,
        show_supports=st.session_state.fem_view_show_supports,
        show_loads=st.session_state.fem_view_show_loads,
        show_labels=st.session_state.fem_view_show_labels,
        show_slabs=st.session_state.fem_view_show_slabs,
        show_slab_mesh_grid=st.session_state.fem_view_show_mesh,
        show_ghost_columns=st.session_state.fem_view_show_ghost,
        grid_spacing=None,
        colorscale="RdYlGn_r",
        show_deformed=st.session_state.fem_view_show_deformed,
        show_reactions=st.session_state.fem_view_show_reactions,
        section_force_type=force_code,
        section_force_scale=force_scale,
    )
    
    # Prepare Analysis Data
    displaced_nodes = None
    reactions = None
    
    # Check for analysis results
    has_results = analysis_result is not None and getattr(analysis_result, "success", False)
    
    # In unified view, we handle overlays via config logic or explicit passing
    # Previously show_overlay was a toggle, now we have specific toggles
    
    if has_results:
        # If show_deformed is on, pass displacements
        if st.session_state.fem_view_show_deformed:
            displaced_nodes = _analysis_result_to_displacements(analysis_result)
        
        # If show_reactions is on, pass reactions
        if st.session_state.fem_view_show_reactions:
            reactions = getattr(analysis_result, "node_reactions", None)

    # Utilization Map
    util_map = {}
    if st.session_state.fem_view_color_mode == "Utilization":
        if not has_results:
            st.info("Run FEM Analysis to see element utilization")
        elif hasattr(analysis_result, "element_utilization"):
             util_map = analysis_result.element_utilization

    # Debug prints removed to prevent console spam and UI lag

    # --- Run Analysis / Lock Controls ---
    st.markdown("---")
    
    is_locked = _is_inputs_locked()
    
    LOAD_COMBINATIONS = [
        ("LC1: 1.4G + 1.6Q", "ULS Gravity (Max)"),
        ("LC2: 1.0G + 1.6Q", "ULS Gravity (Min Dead)"),
        ("LC3: 1.4G + 1.4W", "ULS Wind"),
        ("SLS: 1.0G + 1.0Q", "SLS Characteristic"),
    ]
    
    col_run1, col_run2 = st.columns([1, 1])
    with col_run1:
        run_disabled = is_locked
        if st.button("🔧 Run FEM Analysis", key="fem_view_run_analysis", type="primary", disabled=run_disabled):
            from src.fem.solver import analyze_model
            
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            try:
                status_text.text("Running OpenSees analysis...")
                progress_bar.progress(0.3)
                
                result = analyze_model(model, load_pattern=1)
                progress_bar.progress(0.8)
                
                status_text.text("Analysis complete!")
                progress_bar.progress(1.0)
                
                results_dict = {combo[0]: result for combo in LOAD_COMBINATIONS}
                st.session_state["fem_preview_analysis_result"] = result
                st.session_state["fem_analysis_results_dict"] = results_dict
                st.session_state["fem_analysis_status"] = "success" if getattr(result, "success", False) else "failed"
                st.session_state["fem_analysis_message"] = getattr(result, "message", "Analysis completed")
                _lock_inputs()
                st.rerun()
            except Exception as e:
                st.session_state["fem_analysis_status"] = "error"
                st.session_state["fem_analysis_message"] = str(e)
                st.rerun()
    
    with col_run2:
        if is_locked:
            if st.button("🔓 Unlock to Modify", key="fem_view_unlock", type="secondary"):
                _unlock_inputs()
                st.rerun()
        else:
            st.caption("Run analysis to lock inputs")
    
    if has_results:
        combo_options = [combo[0] for combo in LOAD_COMBINATIONS]
        selected_combo = st.selectbox(
            "Load Combination for Force Display",
            options=combo_options,
            key="fem_view_load_combo",
            help="Select load combination for force diagrams and reactions"
        )
        
        results_dict = st.session_state.get("fem_analysis_results_dict", {})
        if selected_combo in results_dict:
            analysis_result = results_dict[selected_combo]
    
    analysis_status = st.session_state.get("fem_analysis_status", None)
    analysis_message = st.session_state.get("fem_analysis_message", "")
    
    if analysis_status == "success":
        lock_indicator = "🔒 " if is_locked else ""
        st.success(f"✅ {lock_indicator}**Analysis Successful** - {analysis_message}", icon="✅")
    elif analysis_status == "failed":
        st.warning(f"⚠️ **Analysis Failed** - {analysis_message}", icon="⚠️")
    elif analysis_status == "error":
        st.error(f"❌ **Error** - {analysis_message}", icon="❌")
    elif has_results:
        if getattr(analysis_result, "success", False):
            st.success(f"✅ **Previous Analysis Available** - {getattr(analysis_result, 'message', 'Success')}", icon="✅")
    
    st.markdown("---")

    # --- 4. Main View Navigation ---
    
    # Ensure active view state exists
    if "fem_active_view" not in st.session_state:
        st.session_state.fem_active_view = "Plan View"
    
    active_view = st.session_state.fem_active_view
    
    # Navigation Buttons & Floor Selector
    # Arrange: Plan | Elevation | 3D | [Space/Selector]
    nav_cols = st.columns([1, 1, 1, 2])
    
    with nav_cols[0]:
        if st.button("Plan View", type="primary" if active_view == "Plan View" else "secondary", use_container_width=True):
            st.session_state.fem_active_view = "Plan View"
            st.rerun()
            
    with nav_cols[1]:
        if st.button("Elevation View", type="primary" if active_view == "Elevation View" else "secondary", use_container_width=True):
            st.session_state.fem_active_view = "Elevation View"
            st.rerun()
            
    with nav_cols[2]:
        if st.button("3D View", type="primary" if active_view == "3D View" else "secondary", use_container_width=True):
            st.session_state.fem_active_view = "3D View"
            st.rerun()
            
    active_fig = None
    active_view_name = active_view
    
    # Floor Selector (Plan View Only)
    selected_z = 0.0
    if active_view == "Plan View":
        with nav_cols[3]:
            if floor_levels:
                floor_labels = [_format_floor_label(z, floor_levels) for z in floor_levels]
                default_idx = len(floor_levels) - 1
                selected_idx = st.selectbox(
                    "Floor Level",
                    options=range(len(floor_levels)),
                    index=default_idx,
                    format_func=lambda i: floor_labels[i],
                    key="fem_view_plan_floor_nav",
                    label_visibility="collapsed"
                )
                selected_z = floor_levels[selected_idx]
            else:
                st.warning("No floors found")

    # --- Plan View Render ---
    if active_view == "Plan View":
        st.session_state.fem_active_tab = "Plan View"
        
        render_forces_here = (selected_force != "None")
        
        plan_config = VisualizationConfig(
            show_nodes=viz_config.show_nodes,
            show_supports=viz_config.show_supports,
            show_loads=viz_config.show_loads,
            show_labels=viz_config.show_labels,
            show_slabs=viz_config.show_slabs,
            show_slab_mesh_grid=viz_config.show_slab_mesh_grid,
            show_ghost_columns=viz_config.show_ghost_columns,
            grid_spacing=viz_config.grid_spacing,
            colorscale=viz_config.colorscale,
            show_deformed=viz_config.show_deformed,
            show_reactions=viz_config.show_reactions,
            section_force_type=force_code if render_forces_here else None,
            section_force_scale=viz_config.section_force_scale,
        )
            
        fig_plan = create_plan_view(
            model, 
            config=plan_config,
            floor_elevation=selected_z,
            utilization=util_map,
            analysis_result=analysis_result
        )
        st.plotly_chart(fig_plan, use_container_width=True, key=f"plan_view_{st.session_state.fem_view_force_type}_{selected_z}")
        active_fig = fig_plan

    # --- Elevation View Render ---
    elif active_view == "Elevation View":
        st.session_state.fem_active_tab = "Elevation View"
        
        # DEBUG: Show force diagram status
        ef_count = len(getattr(analysis_result, 'element_forces', {})) if analysis_result else 0
        st.caption(f"[DEBUG] force_code={force_code}, has_results={has_results}, element_forces={ef_count}")
        
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            elev_mode = st.selectbox(
                "View Direction", 
                options=["X-Direction (XZ Plane)", "Y-Direction (YZ Plane)"],
                key="fem_view_elev_mode"
            )
        
        if "X-Direction" in elev_mode:
            view_dir = "X"
            gridlines = project.geometry.y_gridlines
            axis_label = "Y"
        else:
            view_dir = "Y"
            gridlines = project.geometry.x_gridlines
            axis_label = "X"
            
        with col_e2:
            grid_map = {f"{axis_label}={val:.1f}m": val for val in gridlines}
            grid_opts = ["All (Projected)", "Custom"] + list(grid_map.keys())
            
            selected_grid = st.selectbox(
                "Gridline Preset",
                options=grid_opts,
                key="fem_view_elev_grid"
            )
            
            grid_coord = None
            if selected_grid == "Custom":
                grid_coord = st.number_input(
                    f"Custom {axis_label} Coordinate (m)",
                    value=0.0,
                    step=0.5,
                    key="fem_view_elev_custom_grid"
                )
            elif selected_grid != "All (Projected)":
                grid_coord = grid_map[selected_grid]
        
        render_forces_here = (selected_force != "None")
        
        elev_config = VisualizationConfig(
            show_nodes=viz_config.show_nodes,
            show_supports=viz_config.show_supports,
            show_loads=viz_config.show_loads,
            show_labels=viz_config.show_labels,
            show_slabs=viz_config.show_slabs,
            show_slab_mesh_grid=viz_config.show_slab_mesh_grid,
            show_ghost_columns=viz_config.show_ghost_columns,
            grid_spacing=viz_config.grid_spacing,
            colorscale=viz_config.colorscale,
            show_deformed=viz_config.show_deformed,
            show_reactions=viz_config.show_reactions,
            section_force_type=force_code if render_forces_here else None,
            section_force_scale=viz_config.section_force_scale,
        )
        
        fig_elev = create_elevation_view(
            model,
            config=elev_config,
            view_direction=view_dir,
            gridline_coord=grid_coord,
            utilization=util_map,
            displaced_nodes=displaced_nodes,
            reactions=reactions,
            analysis_result=analysis_result
        )
        st.plotly_chart(fig_elev, use_container_width=True, key=f"elev_view_{st.session_state.fem_view_force_type}_{view_dir}_{grid_coord}")
        active_fig = fig_elev
        
    # --- 3D View Render ---
    elif active_view == "3D View":
        st.session_state.fem_active_tab = "3D View"
        
        render_forces_here = False  # 3D view doesn't support force diagrams yet
        
        view_3d_config = VisualizationConfig(
            show_nodes=viz_config.show_nodes,
            show_supports=viz_config.show_supports,
            show_loads=viz_config.show_loads,
            show_labels=viz_config.show_labels,
            show_slabs=viz_config.show_slabs,
            show_slab_mesh_grid=viz_config.show_slab_mesh_grid,
            show_ghost_columns=viz_config.show_ghost_columns,
            grid_spacing=viz_config.grid_spacing,
            colorscale=viz_config.colorscale,
            show_deformed=viz_config.show_deformed,
            show_reactions=viz_config.show_reactions,
            section_force_type=None,
            section_force_scale=viz_config.section_force_scale,
        )
        
        fig_3d = create_3d_view(
            model,
            config=view_3d_config,
            utilization=util_map,
            displaced_nodes=displaced_nodes,
            reactions=reactions
        )
        st.plotly_chart(fig_3d, use_container_width=True, key=f"3d_view_{st.session_state.fem_view_force_type}")
        active_fig = fig_3d

    # --- 5. Display Options Panel (MOVED BELOW) ---
    st.divider()
    with st.expander("Display Options", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.checkbox("Show nodes", key="fem_view_show_nodes")
            st.checkbox("Show slabs", key="fem_view_show_slabs")
            st.checkbox("Show Deformed Shape", key="fem_view_show_deformed")
        with col2:
            st.checkbox("Show supports", key="fem_view_show_supports")
            st.checkbox("Show mesh", key="fem_view_show_mesh")
            st.checkbox("Show Reactions (Base)", key="fem_view_show_reactions")
        with col3:
            st.checkbox("Show loads", key="fem_view_show_loads")
            st.checkbox("Show ghost cols", key="fem_view_show_ghost")
            st.checkbox("Show labels", key="fem_view_show_labels")
        with col4:
            st.write("**Section Forces:**")
            st.radio(
                "Force Type",
                options=list(force_type_map.keys()),
                key="fem_view_force_type",
                label_visibility="collapsed"
            )
            
            if st.session_state.fem_view_force_type != "None":
                use_auto = st.checkbox(
                    "Auto Scale",
                    value=True,
                    key="fem_view_force_auto_scale",
                    help="Automatically calculate optimal scale based on building dimensions"
                )
                
                if not use_auto:
                    st.slider(
                        "Manual Scale",
                        min_value=0.01,
                        max_value=2.0,
                        value=0.5,
                        step=0.01,
                        key="fem_view_force_scale",
                        help="Manual scale factor for force diagram size"
                    )
            
        st.divider()
        st.selectbox(
            "Color Scheme",
            options=["Element Type", "Utilization"],
            key="fem_view_color_mode"
        )

    # --- 6. Reaction Table ---
    if has_results:
        st.divider()
        with st.expander("Reaction Forces Table", expanded=False):
            results_dict_for_table = st.session_state.get("fem_analysis_results_dict", {})
            if results_dict_for_table:
                reaction_table = ReactionTable(results_dict_for_table)
            else:
                reaction_table = ReactionTable(analysis_result)
            reaction_table.render()

    # --- 7. Model Statistics & Export ---
    
    st.markdown("### Model Statistics")
    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
    col_s1.metric("Nodes", stats["n_nodes"])
    col_s2.metric("Elements", stats["n_elements"])
    col_s3.metric("Loads", stats["n_loads"])
    col_s4.metric("Diaphragms", len(model.diaphragms))
    
    # Slab load metric
    slab_load_str = "N/A"
    if model.surface_loads:
        pressure = model.surface_loads[0].pressure / 1000.0 # Pa -> kPa
        slab_load_str = f"{pressure:.2f} kPa"
    col_s5.metric("Slab Load", slab_load_str)

    # --- Export Controls ---
    st.markdown("### Export Visualization")
    
    xc1, xc2, xc3 = st.columns([2, 1, 1])
    with xc1:
        st.text(f"Current View: {active_view}")
    with xc2:
        export_fmt = st.selectbox(
            "Format",
            options=["png", "svg", "pdf"],
            key="fem_view_export_fmt"
        )
    
    target_fig_dl = active_fig
    
    with xc3:
        if st.button("Generate Export Image", key="fem_view_gen_export"):
            try:
                with st.spinner("Generating image..."):
                    img_data = export_plotly_figure_image(target_fig_dl, format=export_fmt)
                    
                st.download_button(
                    label="Click to Download",
                    data=img_data,
                    file_name=f"fem_{active_view.split()[0].lower()}.{export_fmt}",
                    mime=f"image/{export_fmt}",
                    key="fem_view_dl_final"
                )
            except Exception as e:
                err_msg = str(e)
                if "kaleido" in err_msg.lower():
                    st.error("Export Error: `kaleido` package missing. Run `pip install -U kaleido`.")
                else:
                    st.error(f"Export Error: {err_msg}")
