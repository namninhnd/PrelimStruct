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
from src.fem.load_combinations import LoadCombinationLibrary
from src.fem.combination_processor import combine_results, get_applicable_combinations
from src.fem.wind_case_synthesizer import with_synthesized_w1_w24_cases
from src.fem.visualization import (
    create_plan_view,
    create_elevation_view,
    create_3d_view,
    VisualizationConfig,
    get_model_statistics,
    export_plotly_figure_image,
    create_opsvis_force_diagram,
    calculate_opsvis_scale,
)
from src.ui.components.reaction_table import ReactionTable
from src.ui.components.beam_forces_table import BeamForcesTable
from src.ui.components.column_forces_table import ColumnForcesTable
from src.ui.floor_labels import (
    format_floor_label_from_elevation,
    format_floor_label_from_floor_number,
)
from src.ui.wind_details import (
    build_wind_details_dataframe,
    build_wind_details_summary,
    has_complete_floor_wind_data,
)

logger = logging.getLogger(__name__)

# Session state keys
CACHE_KEY_MODEL = "fem_model_cache"
CACHE_KEY_HASH = "fem_model_hash"
KEY_VIEW_MODE = "fem_view_mode_tabs"
MODEL_CACHE_SCHEMA_VERSION = "2026-02-13-slab-node-filter"


def _get_cache_key(project: ProjectData, options: ModelBuilderOptions) -> str:
    """Generate a stable cache key for the FEM model based on inputs."""
    geo = project.geometry
    lat = project.lateral
    mat = project.materials
    cg = lat.core_geometry
    wind = project.wind_result
    
    key_parts = [
        f"schema:{MODEL_CACHE_SCHEMA_VERSION}",
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
        f"col_w:{project.column_result.width if project.column_result else 0}",
        f"col_d:{project.column_result.depth if project.column_result else 0}",
        f"wind:{options.apply_wind_loads}",
        f"wind_base:{wind.base_shear if wind else 0.0}",
        f"wind_base_x:{wind.base_shear_x if wind else 0.0}",
        f"wind_base_y:{wind.base_shear_y if wind else 0.0}",
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
        "fem_analysis_results_dict",  # Multi-load-case results dict
        "fem_combined_results_cache",  # Cached combination AnalysisResult objects
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
    st.session_state[CACHE_KEY_MODEL] = None
    st.session_state[CACHE_KEY_HASH] = ""
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


def _format_floor_label(z: float, floor_levels: List[float], story_height: float) -> str:
    """Format floor elevation as HK convention: G/F, 1/F, 2/F, etc."""
    if story_height > 1e-6:
        floor_number = int(round(z / story_height))
        return format_floor_label_from_floor_number(floor_number, story_height)
    return format_floor_label_from_elevation(z, floor_levels)


def _get_selected_canonical_combinations(selected_names: set[str]) -> List[Any]:
    all_combinations = LoadCombinationLibrary.get_all_combinations()
    return [comb for comb in all_combinations if comb.name in selected_names]


def _build_combined_cache_key(
    combination_name: str,
    results_dict: Dict[str, Any],
) -> Tuple[str, Tuple[Tuple[str, int], ...]]:
    signature = tuple(sorted((case_name, id(result)) for case_name, result in results_dict.items()))
    return combination_name, signature


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
        "fem_view_show_supports": False,
        "fem_view_show_mesh": True,
        "fem_view_show_loads": True,
        "fem_view_show_ghost": True,
        "fem_view_show_labels": False,
        "fem_view_show_diaphragms": False,
        "fem_view_show_diaphragm_master": False,
        "fem_view_show_beams": True,
        "fem_view_show_columns": True,
        "fem_view_show_walls": True,
        "fem_view_color_mode": "Element Type",
        "fem_view_show_deformed": False,
        "fem_view_show_reactions": False,
        "fem_view_force_type": "None",
        "fem_view_force_scale": 1.0,
        "fem_view_force_auto_scale": True,
        "fem_view_force_font_size": 12,
        "fem_view_grid_spacing": 1.0,
        "fem_view_use_opsvis": False,
        "fem_view_opsvis_label_mode": "Max abs",
        "fem_view_opsvis_label_stride": 1,
        "fem_view_result_mode": "Load Case",
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
    
    has_wind_result = project.wind_result is not None and (
        project.wind_result.base_shear > 0.0
        or project.wind_result.base_shear_x > 0.0
        or project.wind_result.base_shear_y > 0.0
    )

    with st.expander("Wind Loads (Read-only)", expanded=False):
        wind_result = project.wind_result
        if has_wind_result and wind_result is not None:
            st.write(
                f"Base Shear Vx: {wind_result.base_shear_x:.1f} kN"
            )
            st.write(
                f"Base Shear Vy: {wind_result.base_shear_y:.1f} kN"
            )
            st.write(
                f"Reference Pressure q0: {wind_result.reference_pressure:.2f} kPa"
            )
            st.write(
                f"Design Pressure: {wind_result.design_pressure:.2f} kPa"
            )

            st.markdown("**Calculation Traceability**")
            st.caption(wind_result.code_reference)

            if has_complete_floor_wind_data(wind_result):
                df = build_wind_details_dataframe(wind_result)
                summary = build_wind_details_summary(wind_result)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(
                    (
                        f"Floors: {int(summary['total_floors'])} | "
                        f"Sum Wx: {summary['sum_wx']:.1f} kN | "
                        f"Sum Wy: {summary['sum_wy']:.1f} kN | "
                        f"Sz: {summary['terrain_factor']:.2f} | "
                        f"Cf: {summary['force_coefficient']:.2f}"
                    )
                )
            elif any(
                (
                    wind_result.floor_elevations,
                    wind_result.floor_wind_x,
                    wind_result.floor_wind_y,
                    wind_result.floor_torsion_z,
                )
            ):
                st.warning("Per-floor wind load arrays are inconsistent. Recalculate wind loads.")
            else:
                st.info("Per-floor wind loads not available (legacy calculation without floor count).")
        else:
            st.caption("No wind loads configured in Lateral System.")

    include_wind = has_wind_result
    st.session_state["fem_include_wind"] = include_wind
    
    slab_thickness_m = 0.15
    if project.slab_result and project.slab_result.thickness > 0:
        slab_thickness_m = project.slab_result.thickness / 1000.0

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
        include_slabs=True,
        slab_thickness=slab_thickness_m,
    )
    
    # --- 2. Build or Retrieve Model ---
    model = _get_or_build_cached_model(project, options)
    
    # Get basic stats for controls
    stats = get_model_statistics(model)
    floor_levels = stats.get("floor_elevations", [])
    
    # --- 3. Prepare Visualization Config ---
    
    # Map display labels to internal force codes (ETABS convention: Mz = major axis)
    force_type_map = {
        "None": None,
        "N (Axial)": "N",
        "Vy (Major Shear)": "Vy",
        "Vz (Minor Shear)": "Vz",
        "Mz (Major Moment)": "Mz",
        "My (Minor Moment)": "My",
        "T (Torsion)": "T"
    }
    selected_force = st.session_state.fem_view_force_type
    force_code = force_type_map.get(selected_force)

    scale_factor = float(st.session_state.fem_view_force_scale)
    if st.session_state.fem_view_force_auto_scale:
        force_scale = -1.0
        deformed_exaggeration = 10.0
    else:
        force_scale = scale_factor
        deformed_exaggeration = max(0.1, scale_factor * 10.0)

    use_opsvis = bool(st.session_state.fem_view_use_opsvis)
    
    # Debug prints removed to prevent console spam and UI lag

    viz_config = VisualizationConfig(
        show_nodes=st.session_state.fem_view_show_nodes,
        show_supports=st.session_state.fem_view_show_supports,
        show_loads=st.session_state.fem_view_show_loads,
        show_labels=st.session_state.fem_view_show_labels,
        show_slabs=st.session_state.fem_view_show_slabs,
        show_slab_mesh_grid=st.session_state.fem_view_show_mesh,
        show_ghost_columns=st.session_state.fem_view_show_ghost,
        show_diaphragms=st.session_state.fem_view_show_diaphragms,
        show_diaphragm_master=st.session_state.fem_view_show_diaphragm_master,
        show_beams=st.session_state.fem_view_show_beams,
        show_columns=st.session_state.fem_view_show_columns,
        show_walls=st.session_state.fem_view_show_walls,
        grid_spacing=st.session_state.fem_view_grid_spacing,
        colorscale="RdYlGn_r",
        show_deformed=st.session_state.fem_view_show_deformed,
        show_reactions=st.session_state.fem_view_show_reactions,
        exaggeration=deformed_exaggeration,
        section_force_type=force_code,
        section_force_scale=force_scale,
        section_force_font_size=st.session_state.fem_view_force_font_size,
    )
    
    # Prepare Analysis Data
    displaced_nodes = None
    reactions = None
    
    # --- Result Selection: initialize from solved load cases before has_results check ---
    results_dict = st.session_state.get("fem_analysis_results_dict", {})
    all_load_cases = [
        "DL",
        "SDL",
        "LL",
        "Wx",
        "Wy",
        "Wtz",
        *[f"W{i}" for i in range(1, 25)],
    ]
    available_load_cases = [lc for lc in all_load_cases if lc in results_dict] if results_dict else ["DL", "SDL", "LL"]
    result_mode = st.session_state.get("fem_view_result_mode", "Load Case")
    selected_load_case = st.session_state.get("fem_view_load_case")
    selected_combination_name = st.session_state.get("fem_view_load_combination")
    current_result_label = selected_load_case

    if results_dict:
        if available_load_cases and selected_load_case not in available_load_cases:
            st.session_state["fem_view_load_case"] = available_load_cases[0]
            selected_load_case = available_load_cases[0]

        if selected_load_case in results_dict:
            analysis_result = results_dict[selected_load_case]
            current_result_label = selected_load_case

        if analysis_result is None or not getattr(analysis_result, "success", False):
            for load_case in available_load_cases:
                candidate = results_dict.get(load_case)
                if candidate is not None and getattr(candidate, "success", False):
                    st.session_state["fem_view_load_case"] = load_case
                    selected_load_case = load_case
                    analysis_result = candidate
                    current_result_label = load_case
                    break
    
    # Check for analysis results
    has_results = analysis_result is not None and getattr(analysis_result, "success", False)
    
    util_map = {}

    # Debug prints removed to prevent console spam and UI lag

    # --- Run Analysis / Lock Controls ---
    st.markdown("---")
    
    is_locked = _is_inputs_locked()
    
    col_run1, col_run2, col_run3, col_run4 = st.columns([1, 1, 1, 1])
    with col_run2:
        run_disabled = is_locked
        if st.button("🔧 Run FEM Analysis", key="fem_view_run_analysis", type="primary", disabled=run_disabled):
            from src.fem.solver import analyze_model
            
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            try:
                status_text.text("Running OpenSees analysis...")
                progress_bar.progress(0.3)
                
                run_load_cases = ["DL", "SDL", "LL"]
                if include_wind:
                    run_load_cases.extend(["Wx", "Wy", "Wtz"])

                results_dict = analyze_model(model, load_cases=run_load_cases)
                if include_wind:
                    results_dict = with_synthesized_w1_w24_cases(results_dict)
                progress_bar.progress(0.8)
                
                status_text.text("Analysis complete!")
                progress_bar.progress(1.0)
                
                result = results_dict.get("DL") or next(iter(results_dict.values()), None)
                st.session_state["fem_preview_analysis_result"] = result
                st.session_state["fem_analysis_results_dict"] = results_dict

                successful_cases = [
                    case
                    for case in run_load_cases
                    if getattr(results_dict.get(case), "success", False)
                ]
                failed_cases = [case for case in run_load_cases if case not in successful_cases]

                if failed_cases:
                    st.session_state["fem_analysis_status"] = "failed"
                    if successful_cases:
                        st.session_state["fem_analysis_message"] = (
                            f"{len(successful_cases)}/{len(run_load_cases)} load cases completed. "
                            f"Failed: {', '.join(failed_cases)}"
                        )
                    else:
                        first_failed = results_dict.get(failed_cases[0])
                        st.session_state["fem_analysis_message"] = getattr(
                            first_failed,
                            "message",
                            "Analysis failed",
                        )
                else:
                    st.session_state["fem_analysis_status"] = "success"
                    st.session_state["fem_analysis_message"] = f"All {len(run_load_cases)} load cases completed"
                _lock_inputs()
                st.rerun()
            except Exception as e:
                st.session_state["fem_analysis_status"] = "error"
                st.session_state["fem_analysis_message"] = str(e)
                st.rerun()
    
    with col_run3:
        if st.button(
            "🔓 Unlock to Modify",
            key="fem_view_unlock",
            type="secondary",
            disabled=not is_locked,
        ):
            _unlock_inputs()
            st.rerun()
    
    if has_results:
        result_mode = st.radio(
            "View Mode",
            options=["Load Case", "Load Combination"],
            key="fem_view_result_mode",
            horizontal=True,
        )

        if result_mode == "Load Case":
            selected_load_case = st.selectbox(
                "Load Case",
                options=available_load_cases,
                key="fem_view_load_case",
                help="Select load case to display in force diagrams",
            )
            if selected_load_case in results_dict:
                analysis_result = results_dict[selected_load_case]
                current_result_label = selected_load_case
        else:
            selected_names = st.session_state.get("selected_combinations", set())
            selected_combinations = _get_selected_canonical_combinations(selected_names)
            applicable_combinations = get_applicable_combinations(
                selected_combinations,
                available_load_cases,
            )

            if applicable_combinations:
                combination_by_name = {comb.name: comb for comb in applicable_combinations}
                combination_names = list(combination_by_name.keys())

                if selected_combination_name not in combination_names:
                    st.session_state["fem_view_load_combination"] = combination_names[0]

                selected_combination_name = st.selectbox(
                    "Load Combination",
                    options=combination_names,
                    key="fem_view_load_combination",
                    help="Select factored load combination to display",
                )

                combined_cache = st.session_state.setdefault("fem_combined_results_cache", {})
                cache_key = _build_combined_cache_key(selected_combination_name, results_dict)
                if cache_key not in combined_cache:
                    combined_cache[cache_key] = combine_results(
                        results_dict,
                        combination_by_name[selected_combination_name],
                    )

                analysis_result = combined_cache[cache_key]
                current_result_label = selected_combination_name
            else:
                st.info(
                    "No selected canonical combinations are applicable to the solved load cases. "
                    "Check sidebar combination selection."
                )

    # Recompute final result flags/data after load case/combination selection
    has_results = analysis_result is not None and getattr(analysis_result, "success", False)

    if has_results:
        if st.session_state.fem_view_show_deformed:
            displaced_nodes = _analysis_result_to_displacements(analysis_result)

        if st.session_state.fem_view_show_reactions:
            reactions = getattr(analysis_result, "node_reactions", None)

    if st.session_state.fem_view_color_mode == "Utilization":
        if not has_results:
            st.info("Run FEM Analysis to see element utilization")
        elif hasattr(analysis_result, "element_utilization"):
            util_map = analysis_result.element_utilization

    load_pattern_map = {
        "DL": options.dl_load_pattern,
        "SDL": options.sdl_load_pattern,
        "LL": options.ll_load_pattern,
        "Wx": options.wx_pattern,
        "Wy": options.wy_pattern,
        "Wtz": options.wtz_pattern,
    }
    active_load_case = current_result_label if has_results else None
    active_load_pattern = (
        load_pattern_map.get(active_load_case)
        if active_load_case and result_mode == "Load Case"
        else None
    )
    
    analysis_status = st.session_state.get("fem_analysis_status", None)
    analysis_message = st.session_state.get("fem_analysis_message", "")
    
    def _render_status_message(message: str) -> None:
        st.markdown(
            "<div style=\"background:#dcfce7; padding:0.75rem; border-radius:0.5rem; "
            "border:1px solid #86efac; text-align:center; font-weight:600; "
            "display:flex; align-items:center; justify-content:center;\">"
            f"{message}"
            "</div>",
            unsafe_allow_html=True,
        )

    if analysis_status == "success":
        lock_indicator = "🔒 " if is_locked else ""
        _render_status_message(f"{lock_indicator}Analysis Successful - {analysis_message}")
    elif analysis_status == "failed":
        st.warning(f"⚠️ **Analysis Failed** - {analysis_message}", icon="⚠️")
    elif analysis_status == "error":
        st.error(f"❌ **Error** - {analysis_message}", icon="❌")
    elif has_results:
        if getattr(analysis_result, "success", False):
            _render_status_message(f"Previous Analysis Available - {getattr(analysis_result, 'message', 'Success')}")
    
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
        if st.button(
            "Plan View",
            type="primary" if active_view == "Plan View" else "secondary",
            width="stretch",
            disabled=False,
        ):
            st.session_state.fem_active_view = "Plan View"
            st.rerun()
            
    with nav_cols[1]:
        if st.button(
            "Elevation View",
            type="primary" if active_view == "Elevation View" else "secondary",
            width="stretch",
            disabled=False,
        ):
            st.session_state.fem_active_view = "Elevation View"
            st.rerun()
            
    with nav_cols[2]:
        if st.button(
            "3D View",
            type="primary" if active_view == "3D View" else "secondary",
            width="stretch",
            disabled=False,
        ):
            st.session_state.fem_active_view = "3D View"
            st.rerun()
            
    active_fig = None
    active_view_name = active_view
    
    # Floor Selector (Plan View Only)
    selected_z = 0.0
    if active_view == "Plan View":
        with nav_cols[3]:
            if floor_levels:
                floor_labels = [
                    _format_floor_label(z, floor_levels, project.geometry.story_height)
                    for z in floor_levels
                ]
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
        
        # opsvis incompatible with ShellMITC4 elements - use Plotly
        plan_config = VisualizationConfig(
            show_nodes=viz_config.show_nodes,
            show_supports=viz_config.show_supports,
            show_loads=viz_config.show_loads,
            show_labels=viz_config.show_labels,
            show_slabs=viz_config.show_slabs,
            show_slab_mesh_grid=viz_config.show_slab_mesh_grid,
            show_ghost_columns=viz_config.show_ghost_columns,
            show_diaphragms=viz_config.show_diaphragms,
            show_diaphragm_master=viz_config.show_diaphragm_master,
            show_beams=viz_config.show_beams,
            show_columns=viz_config.show_columns,
            show_walls=viz_config.show_walls,
            grid_spacing=viz_config.grid_spacing,
            colorscale=viz_config.colorscale,
            show_deformed=viz_config.show_deformed,
            show_reactions=viz_config.show_reactions,
            exaggeration=viz_config.exaggeration,
            section_force_type=force_code if (force_code and has_results) else None,
            section_force_scale=viz_config.section_force_scale,
            section_force_font_size=viz_config.section_force_font_size,
            load_pattern=active_load_pattern,
            load_case_label=active_load_case,
        )
            
        fig_plan = create_plan_view(
            model, 
            config=plan_config,
            floor_elevation=selected_z,
            utilization=util_map,
            displaced_nodes=displaced_nodes,
            reactions=reactions,
            analysis_result=analysis_result
        )
        st.plotly_chart(
            fig_plan,
            width="stretch",
            key=(
                f"plan_view_{st.session_state.fem_view_force_type}_"
                f"{selected_z}_{st.session_state.fem_view_force_font_size}"
            ),
        )
        active_fig = fig_plan

    # --- Elevation View Render ---
    elif active_view == "Elevation View":
        st.session_state.fem_active_tab = "Elevation View"
        
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
            grid_opts = ["Custom"] + list(grid_map.keys())
            
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
            else:
                grid_coord = grid_map.get(selected_grid)
        
        # opsvis incompatible with ShellMITC4 elements - use Plotly
        elev_config = VisualizationConfig(
            show_nodes=viz_config.show_nodes,
            show_supports=viz_config.show_supports,
            show_loads=viz_config.show_loads,
            show_labels=viz_config.show_labels,
            show_slabs=viz_config.show_slabs,
            show_slab_mesh_grid=viz_config.show_slab_mesh_grid,
            show_ghost_columns=viz_config.show_ghost_columns,
            show_beams=viz_config.show_beams,
            show_columns=viz_config.show_columns,
            show_walls=viz_config.show_walls,
            grid_spacing=viz_config.grid_spacing,
            colorscale=viz_config.colorscale,
            show_deformed=viz_config.show_deformed,
            show_reactions=viz_config.show_reactions,
            exaggeration=viz_config.exaggeration,
            section_force_type=force_code if (force_code and has_results) else None,
            section_force_scale=viz_config.section_force_scale,
            section_force_font_size=viz_config.section_force_font_size,
            load_pattern=active_load_pattern,
            load_case_label=active_load_case,
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
        st.plotly_chart(
            fig_elev,
            width="stretch",
            key=(
                f"elev_view_{st.session_state.fem_view_force_type}_"
                f"{view_dir}_{grid_coord}_{st.session_state.fem_view_force_font_size}"
            ),
        )
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
            show_beams=viz_config.show_beams,
            show_columns=viz_config.show_columns,
            show_walls=viz_config.show_walls,
            grid_spacing=viz_config.grid_spacing,
            colorscale=viz_config.colorscale,
            show_deformed=viz_config.show_deformed,
            show_reactions=viz_config.show_reactions,
            exaggeration=viz_config.exaggeration,
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
        st.plotly_chart(
            fig_3d,
            width="stretch",
            key=f"3d_view_{st.session_state.fem_view_force_type}",
        )
        active_fig = fig_3d

    if use_opsvis and force_code and has_results and result_mode == "Load Case":
        st.divider()
        st.markdown("### opsvis Force Diagram")
        st.caption("Rebuilds the OpenSees model for the selected load case.")

        load_case = active_load_case or "DL"
        pattern_id = active_load_pattern or options.dl_load_pattern

        sfac = 1.0
        from src.fem.results_processor import ResultsProcessor
        opsvis_forces = ResultsProcessor.extract_section_forces(
            result=analysis_result,
            model=model,
            force_type=force_code,
        )
        base_scale = calculate_opsvis_scale(opsvis_forces, model)
        if st.session_state.fem_view_force_auto_scale:
            sfac = base_scale
        else:
            sfac = base_scale * st.session_state.fem_view_force_scale

        label_mode_map = {
            "Max abs": "max_abs",
            "Max/Min": "max_min",
            "Ends": "ends",
            "None": "none",
        }
        label_mode = label_mode_map.get(
            st.session_state.get("fem_view_opsvis_label_mode", "Max abs"),
            "max_abs",
        )
        label_stride = int(st.session_state.get("fem_view_opsvis_label_stride", 1))

        opsvis_fig = create_opsvis_force_diagram(
            sf_type=force_code,
            sfac=sfac,
            title=f"{selected_force} ({load_case})",
            model=model,
            run_analysis=True,
            load_pattern=pattern_id,
            forces=opsvis_forces,
            label_mode=label_mode,
            label_stride=label_stride,
            label_font_size=viz_config.section_force_font_size,
        )

        if opsvis_fig is None:
            error_msg = st.session_state.get("_opsvis_last_error")
            if error_msg:
                st.warning(f"opsvis force diagram failed: {error_msg}")
            else:
                st.warning("opsvis force diagram unavailable. Check opsvis/matplotlib installation.")
        else:
            if "_opsvis_last_error" in st.session_state:
                del st.session_state["_opsvis_last_error"]
            st.pyplot(opsvis_fig, clear_figure=True)
    elif use_opsvis and force_code and has_results and result_mode == "Load Combination":
        st.info("opsvis force diagram is available only in Load Case mode.")

    # --- 5. Display Options Panel (MOVED BELOW) ---
    st.divider()
    with st.expander("Display Options", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.checkbox("Label", key="fem_view_show_labels")
            st.checkbox("Nodes", key="fem_view_show_nodes")
            st.checkbox("Load", key="fem_view_show_loads")
            st.checkbox("Support", key="fem_view_show_supports")
            st.checkbox("Diaphragm", key="fem_view_show_diaphragms")
            st.checkbox("Diaphragm Master", key="fem_view_show_diaphragm_master")
        with col2:
            st.checkbox("Beam", key="fem_view_show_beams")
            st.checkbox("Column", key="fem_view_show_columns")
            st.checkbox("Omitted Column", key="fem_view_show_ghost")
            st.checkbox("Slab", key="fem_view_show_slabs")
            st.checkbox("Mesh", key="fem_view_show_mesh")
            st.checkbox("Wall", key="fem_view_show_walls")
        with col3:
            st.checkbox("Reaction (Base)", key="fem_view_show_reactions")
            st.checkbox("Deformed Shape", key="fem_view_show_deformed")

        st.divider()
        force_col, style_col = st.columns(2)
        with force_col:
            st.write("**Section Forces:**")
            st.radio(
                "Force Type",
                options=list(force_type_map.keys()),
                key="fem_view_force_type",
                label_visibility="collapsed"
            )

            st.checkbox(
                "Use opsvis force diagram (experimental)",
                key="fem_view_use_opsvis",
                help="Uses opsvis and Matplotlib instead of Plotly overlays."
            )

            if st.session_state.fem_view_use_opsvis:
                st.selectbox(
                    "opsvis labels",
                    options=["Max abs", "Max/Min", "Ends", "None"],
                    key="fem_view_opsvis_label_mode",
                )
                if st.session_state.fem_view_opsvis_label_mode != "None":
                    st.slider(
                        "Label every N elements",
                        min_value=1,
                        max_value=10,
                        value=int(st.session_state.fem_view_opsvis_label_stride),
                        step=1,
                        key="fem_view_opsvis_label_stride",
                    )

            if st.session_state.fem_view_force_type != "None" or st.session_state.fem_view_show_deformed:
                use_auto = st.checkbox(
                    "Auto Scale",
                    value=True,
                    key="fem_view_force_auto_scale",
                    help="Shared scaling for section-force diagrams and deformed-shape exaggeration"
                )

                if st.session_state.fem_view_force_type != "None":
                    st.slider(
                        "Label Font Size",
                        min_value=6,
                        max_value=24,
                        step=1,
                        key="fem_view_force_font_size",
                        help="Font size for force diagram labels (Plotly and opsvis)"
                    )
                
                if not use_auto:
                    st.slider(
                        "Manual Scale",
                        min_value=0.01,
                        max_value=2.0,
                        value=0.5,
                        step=0.01,
                        key="fem_view_force_scale",
                        help="Shared manual scale for section-force diagrams and deformed-shape exaggeration"
                    )
        with style_col:
            st.slider(
                "Grid spacing (m)",
                min_value=0.5,
                max_value=10.0,
                step=0.5,
                key="fem_view_grid_spacing",
                help="Controls plot grid interval for plan and elevation views"
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
            if result_mode == "Load Combination" and selected_combination_name:
                reaction_table = ReactionTable({selected_combination_name: analysis_result})
            elif results_dict_for_table:
                reaction_table = ReactionTable(results_dict_for_table)
            else:
                reaction_table = ReactionTable(analysis_result)
            reaction_table.render()
    
    # --- 6b. Beam Forces Table ---
    if has_results:
        with st.expander("Beam Section Forces", expanded=False):
            current_load_case = current_result_label if current_result_label else "DL"
            beam_forces_table = BeamForcesTable(
                model=model,
                analysis_result=analysis_result,
                force_type=force_code if force_code else "My",
                story_height=project.geometry.story_height,
                load_case=current_load_case
            )
            current_floor = int(round(selected_z / project.geometry.story_height)) if selected_z else None
            beam_forces_table.render(floor_filter=current_floor)

    # --- 6c. Column Forces Table ---
    if has_results:
        with st.expander("Column Section Forces", expanded=False):
            current_load_case = current_result_label if current_result_label else "DL"
            column_forces_table = ColumnForcesTable(
                model=model,
                analysis_result=analysis_result,
                force_type=force_code if force_code else "N",
                story_height=project.geometry.story_height,
                load_case=current_load_case
            )
            current_floor = int(round(selected_z / project.geometry.story_height)) if selected_z else None
            column_forces_table.render(floor_filter=current_floor)

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
