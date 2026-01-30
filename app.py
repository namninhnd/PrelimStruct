"""
PrelimStruct - Streamlit Dashboard
AI-Assisted Preliminary Structural Design Platform
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

# Import core modules
from src.core.data_models import (
    ProjectData, GeometryInput, LoadInput, MaterialInput, LateralInput,
    SlabDesignInput, BeamDesignInput, ReinforcementInput,
    ExposureClass, TerrainCategory,
    CoreWallConfig, CoreWallGeometry, CoreWallSectionProperties,
    ColumnPosition, LoadCombination, PRESETS,
)
from src.core.constants import CARBON_FACTORS

# Import engines
from src.engines.slab_engine import SlabEngine
from src.engines.beam_engine import BeamEngine
from src.engines.column_engine import ColumnEngine
from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine

# Import FEM modules
from src.fem.core_wall_geometry import (
    ISectionCoreWall, TwoCFacingCoreWall, TwoCBackToBackCoreWall,
    TubeCenterOpeningCoreWall, TubeSideOpeningCoreWall,
)
from src.fem.coupling_beam import CouplingBeamGenerator
from src.fem.beam_trimmer import BeamTrimmer, BeamGeometry, BeamConnectionType
from src.fem.fem_engine import FEMModel
from src.fem.model_builder import (
    build_fem_model, 
    ModelBuilderOptions,
)
from src.fem.visualization import (
    create_plan_view,
    create_elevation_view,
    create_3d_view,
    VisualizationConfig,
    get_model_statistics,
)
from src.fem.solver import analyze_model
from src.fem.load_combinations import LoadCombinationDefinition

# Import report generator
from src.report.report_generator import ReportGenerator

# Import structural layout visualization functions
from src.ui.views.structural_layout import (
    create_framing_grid,
    build_preview_utilization_map,
    create_lateral_diagram,
    _analysis_result_to_displacements,
)

# Import sidebar and project builder
from src.ui.sidebar import render_sidebar
from src.ui.project_builder import build_project_from_inputs, get_override_params


# Page Configuration
st.set_page_config(
    page_title="PrelimStruct | Structural Design",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Status Badge Styles */
    .status-pass {
        background-color: #10B981;
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
    }
    .status-fail {
        background-color: #EF4444;
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
    }
    .status-warning {
        background-color: #F59E0B;
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
    }
    .status-pending {
        background-color: #6B7280;
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
    }

    /* Metric Card */
    .metric-card {
        background: linear-gradient(135deg, #1E3A5F 0%, #2D5A87 100%);
        border-radius: 12px;
        padding: 16px;
        color: white;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
    }
    .metric-label {
        font-size: 14px;
        opacity: 0.8;
        margin: 0;
    }

    /* Section Headers */
    .section-header {
        color: #1E3A5F;
        font-weight: 700;
        border-bottom: 2px solid #2D5A87;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    /* Element Summary Cards */
    .element-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .element-card strong {
        color: #1E3A5F;
        font-size: 15px;
    }
    .element-card small {
        color: #4A5568;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def get_status_badge(status: str, utilization: float = 0.0) -> str:
    """Generate HTML status badge based on status and utilization"""
    if status == "FAIL" or utilization > 1.0:
        return '<span class="status-fail">FAIL</span>'
    elif status == "WARNING" or utilization > 0.85:
        return '<span class="status-warning">WARN</span>'
    elif status == "PENDING":
        return '<span class="status-pending">--</span>'
    else:
        return '<span class="status-pass">OK</span>'


def calculate_carbon_emission(project: ProjectData) -> Tuple[float, float]:
    """Calculate concrete volume and carbon emission"""
    # Estimate concrete volumes (simplified)
    floor_area = project.geometry.bay_x * project.geometry.bay_y
    floors = project.geometry.floors

    # Slab volume
    slab_thickness = 0.2  # default 200mm
    if project.slab_result:
        slab_thickness = project.slab_result.thickness / 1000
    slab_volume = floor_area * slab_thickness * floors

    # Beam volumes (approximate)
    beam_depth = 0.5
    beam_width = 0.3
    if project.primary_beam_result:
        beam_depth = project.primary_beam_result.depth / 1000
        beam_width = project.primary_beam_result.width / 1000

    # Primary beams (along X direction)
    primary_beam_length = project.geometry.bay_x
    primary_beam_volume = beam_width * beam_depth * primary_beam_length * floors

    # Secondary beams (along Y direction)
    secondary_beam_volume = beam_width * beam_depth * project.geometry.bay_y * floors

    # Column volume
    col_size = 0.4  # default 400mm
    if project.column_result:
        col_size = project.column_result.dimension / 1000
    col_height = project.geometry.story_height * floors
    col_volume = col_size * col_size * col_height

    # Total volume
    total_volume = slab_volume + primary_beam_volume + secondary_beam_volume + col_volume

    # Carbon emission (weighted average of grades)
    avg_fcu = (project.materials.fcu_slab + project.materials.fcu_beam + project.materials.fcu_column) / 3
    carbon_factor = CARBON_FACTORS.get(int(avg_fcu), 340)  # default to C40 factor
    carbon_emission = total_volume * carbon_factor

    return total_volume, carbon_emission


def calculate_core_wall_properties(geometry: CoreWallGeometry) -> Optional[CoreWallSectionProperties]:
    """Calculate section properties for core wall geometry.

    Args:
        geometry: CoreWallGeometry with configuration and dimensions

    Returns:
        CoreWallSectionProperties or None if calculation fails
    """
    try:
        if geometry.config == CoreWallConfig.I_SECTION:
            core_wall = ISectionCoreWall(geometry)
            return core_wall.calculate_section_properties()
        elif geometry.config == CoreWallConfig.TWO_C_FACING:
            core_wall = TwoCFacingCoreWall(geometry)
            return core_wall.calculate_section_properties()
        elif geometry.config == CoreWallConfig.TWO_C_BACK_TO_BACK:
            core_wall = TwoCBackToBackCoreWall(geometry)
            return core_wall.calculate_section_properties()
        elif geometry.config == CoreWallConfig.TUBE_CENTER_OPENING:
            core_wall = TubeCenterOpeningCoreWall(geometry)
            return core_wall.calculate_section_properties()
        elif geometry.config == CoreWallConfig.TUBE_SIDE_OPENING:
            core_wall = TubeSideOpeningCoreWall(geometry)
            return core_wall.calculate_section_properties()
        else:
            return None
    except Exception as e:
        st.warning(f"Failed to calculate section properties: {str(e)}")
        return None


def run_calculations(project: ProjectData,
                     override_slab: int = 0,
                     override_pri_beam_w: int = 0,
                     override_pri_beam_d: int = 0,
                     override_sec_beam_w: int = 0,
                     override_sec_beam_d: int = 0,
                     override_col: int = 0,
                     secondary_along_x: bool = False,
                     num_secondary_beams: int = 3) -> ProjectData:
    """Run all structural calculations with optional overrides"""
    # Create engines
    slab_engine = SlabEngine(project)
    beam_engine = BeamEngine(project)
    column_engine = ColumnEngine(project)

    # Slab design
    project.slab_result = slab_engine.calculate()

    # Apply slab override if specified
    if override_slab > 0:
        project.slab_result.thickness = override_slab
        project.slab_result.self_weight = (override_slab / 1000) * 24.5
        project.slab_result.status = "OVERRIDE"
        # Recalculate utilization: compare to minimum required thickness
        min_span = min(project.geometry.bay_x, project.geometry.bay_y)
        min_required = (min_span * 1000) / 26  # Basic span/depth ratio
        project.slab_result.utilization = min_required / override_slab if override_slab > 0 else 1.0

    # Beam design - determine spans based on secondary beam direction
    # Secondary beams are INTERNAL to the bay, primary beams are on the perimeter
    if secondary_along_x:
        # Secondary beams along X (internal), Primary beams along Y (perimeter)
        # Secondary beams span in X-direction, supported by primary beams at Y=0 and Y=bay_y
        secondary_span = project.geometry.bay_x
        primary_span = project.geometry.bay_y
        # Tributary width for secondary beam = spacing between secondary beams
        if num_secondary_beams > 0:
            secondary_tributary = project.geometry.bay_y / (num_secondary_beams + 1)
        else:
            secondary_tributary = project.geometry.bay_y / 2
        # Primary beam carries load from secondary beams
        primary_tributary = project.geometry.bay_y / 2
    else:
        # Secondary beams along Y (internal), Primary beams along X (perimeter)
        # Secondary beams span in Y-direction, supported by primary beams at X=0 and X=bay_x
        secondary_span = project.geometry.bay_y
        primary_span = project.geometry.bay_x
        # Tributary width for secondary beam
        if num_secondary_beams > 0:
            secondary_tributary = project.geometry.bay_x / (num_secondary_beams + 1)
        else:
            secondary_tributary = project.geometry.bay_x / 2
        # Primary beam carries load from secondary beams
        primary_tributary = project.geometry.bay_x / 2

    project.primary_beam_result = beam_engine.calculate_primary_beam(primary_tributary)
    project.secondary_beam_result = beam_engine.calculate_secondary_beam(secondary_tributary)

    # Apply primary beam overrides if specified
    if override_pri_beam_w > 0 or override_pri_beam_d > 0:
        if override_pri_beam_w > 0:
            project.primary_beam_result.width = override_pri_beam_w
        if override_pri_beam_d > 0:
            project.primary_beam_result.depth = override_pri_beam_d
        project.primary_beam_result.status = "OVERRIDE"
        # Recalculate utilization based on moment capacity
        width = project.primary_beam_result.width
        depth = project.primary_beam_result.depth
        d_eff = depth - 50  # effective depth
        if d_eff > 0 and width > 0:
            # Moment capacity: M_cap = 0.156 * fcu * b * d^2
            fcu = project.materials.fcu_beam
            M_cap = 0.156 * fcu * width * (d_eff ** 2) / 1e6  # kNm
            moment = project.primary_beam_result.moment
            # Shear capacity check
            v = project.primary_beam_result.shear * 1000 / (width * d_eff)
            v_max = 0.8 * (fcu ** 0.5)
            shear_util = v / v_max if v_max > 0 else 0
            moment_util = moment / M_cap if M_cap > 0 else 1.0
            project.primary_beam_result.utilization = max(moment_util, shear_util)

    # Apply secondary beam overrides if specified
    if override_sec_beam_w > 0 or override_sec_beam_d > 0:
        if override_sec_beam_w > 0:
            project.secondary_beam_result.width = override_sec_beam_w
        if override_sec_beam_d > 0:
            project.secondary_beam_result.depth = override_sec_beam_d
        project.secondary_beam_result.status = "OVERRIDE"
        # Recalculate utilization based on moment capacity
        width = project.secondary_beam_result.width
        depth = project.secondary_beam_result.depth
        d_eff = depth - 50  # effective depth
        if d_eff > 0 and width > 0:
            fcu = project.materials.fcu_beam
            M_cap = 0.156 * fcu * width * (d_eff ** 2) / 1e6  # kNm
            moment = project.secondary_beam_result.moment
            v = project.secondary_beam_result.shear * 1000 / (width * d_eff)
            v_max = 0.8 * (fcu ** 0.5)
            shear_util = v / v_max if v_max > 0 else 0
            moment_util = moment / M_cap if M_cap > 0 else 1.0
            project.secondary_beam_result.utilization = max(moment_util, shear_util)

    # Column design (interior for now)
    project.column_result = column_engine.calculate(ColumnPosition.INTERIOR)

    # Apply column override if specified
    if override_col > 0:
        project.column_result.dimension = override_col
        project.column_result.status = "OVERRIDE"
        # Recalculate utilization based on axial capacity
        fcu = project.materials.fcu_column
        fy = 500  # Steel yield strength
        Ac = override_col * override_col  # Column area mm²
        # Axial capacity: N_cap = 0.35 * fcu * Ac + 0.67 * fy * 0.02 * Ac (2% steel)
        N_cap = (0.35 * fcu * Ac + 0.67 * fy * 0.02 * Ac) / 1000  # kN
        axial_load = project.column_result.axial_load
        project.column_result.utilization = axial_load / N_cap if N_cap > 0 else 1.0

    # Wind / Lateral analysis
    if project.lateral.building_width == 0:
        project.lateral.building_width = project.geometry.bay_x
    if project.lateral.building_depth == 0:
        project.lateral.building_depth = project.geometry.bay_y

    wind_engine = WindEngine(project)
    project.wind_result = wind_engine.calculate_wind_loads()

    # Core wall check and drift calculation (if core defined)
    if project.lateral.core_geometry:
        # Calculate drift using DriftEngine
        drift_engine = DriftEngine(project)
        project.wind_result = drift_engine.calculate_drift(project.wind_result)

        # Check core wall stresses
        core_engine = CoreWallEngine(project)
        project.core_wall_result = core_engine.check_core_wall(project.wind_result)
    else:
        # Moment frame system - distribute lateral loads to columns
        column_loads = wind_engine.distribute_lateral_to_columns(project.wind_result)
        if column_loads and project.column_result:
            # Update column with lateral loads
            first_col_load = list(column_loads.values())[0]
            project.column_result.lateral_shear = first_col_load[0]
            project.column_result.lateral_moment = first_col_load[1]
            project.column_result.has_lateral_loads = True

            # V3.5: check_combined_load() removed - combined_utilization set by ColumnEngine.calculate()

    # Calculate carbon emission
    project.concrete_volume, project.carbon_emission = calculate_carbon_emission(project)

    return project


def main():
    # Header
    st.markdown("""
    <h1 style="color: #1E3A5F; margin-bottom: 0;">PrelimStruct</h1>
    <p style="color: #64748B; margin-top: 0;">AI-Assisted Preliminary Structural Design Platform</p>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'project' not in st.session_state:
        st.session_state.project = ProjectData()

    # ===== SIDEBAR =====
    # Render sidebar and collect all inputs
    inputs = render_sidebar(st.session_state.project)
    
    # Build project from inputs
    project = build_project_from_inputs(inputs, st.session_state.project)
    
    # Get override parameters
    override_params = get_override_params(inputs)
    
    # Run calculations with overrides
    project = run_calculations(
        project,
        override_slab=override_params.get("override_slab", 0),
        override_pri_beam_w=override_params.get("override_pri_beam_w", 0),
        override_pri_beam_d=override_params.get("override_pri_beam_d", 0),
        override_sec_beam_w=override_params.get("override_sec_beam_w", 0),
        override_sec_beam_d=override_params.get("override_sec_beam_d", 0),
        override_col=override_params.get("override_col", 0),
        secondary_along_x=override_params.get("secondary_along_x", True),
        num_secondary_beams=override_params.get("num_secondary_beams", 3),
    )
    
    # Store updated project
    st.session_state.project = project
    
    # Extract values needed for main content display
    secondary_along_x = inputs.get("secondary_along_x", True)
    num_secondary_beams = inputs.get("num_secondary_beams", 3)
    selected_comb_label = inputs.get("selected_comb_label", "1.4DL + 1.6LL")
    selected_terrain_label = inputs.get("selected_terrain_label", "C: Urban")

    # ===== MAIN CONTENT =====

    # Status Badges Row
    st.markdown("### Design Status")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        slab_util = project.slab_result.utilization if project.slab_result else 0
        slab_status = "FAIL" if slab_util > 1.0 else "OK"
        st.markdown(f"""
        <div class="element-card">
            <strong>Slab</strong> {get_status_badge(slab_status, slab_util)}
            <br><small>{project.slab_result.thickness if project.slab_result else '--'}mm</small>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        beam_util = project.primary_beam_result.utilization if project.primary_beam_result else 0
        beam_status = "FAIL" if beam_util > 1.0 else ("WARNING" if project.primary_beam_result and project.primary_beam_result.is_deep_beam else "OK")
        size_str = f"{project.primary_beam_result.width}x{project.primary_beam_result.depth}" if project.primary_beam_result else "--"
        st.markdown(f"""
        <div class="element-card">
            <strong>Beam</strong> {get_status_badge(beam_status, beam_util)}
            <br><small>{size_str}mm</small>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        col_util = project.column_result.utilization if project.column_result else 0
        col_status = "FAIL" if col_util > 1.0 else ("WARNING" if project.column_result and project.column_result.is_slender else "OK")
        st.markdown(f"""
        <div class="element-card">
            <strong>Column</strong> {get_status_badge(col_status, col_util)}
            <br><small>{project.column_result.dimension if project.column_result else '--'}mm sq</small>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        if project.lateral.core_geometry and project.core_wall_result:
            core_util = max(project.core_wall_result.compression_check, project.core_wall_result.shear_check)
            core_status = "FAIL" if core_util > 1.0 else ("WARNING" if project.core_wall_result.requires_tension_piles else "OK")
        else:
            core_util = 0
            core_status = "PENDING"
        st.markdown(f"""
        <div class="element-card">
            <strong>Core</strong> {get_status_badge(core_status, core_util)}
            <br><small>{project.lateral.lateral_system if hasattr(project.lateral, 'lateral_system') else (project.wind_result.lateral_system if project.wind_result else '--')}</small>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        drift_status = "OK" if (project.wind_result and project.wind_result.drift_ok) else "FAIL"
        drift_val = f"{project.wind_result.drift_index:.5f}" if project.wind_result else "--"
        st.markdown(f"""
        <div class="element-card">
            <strong>Drift</strong> {get_status_badge(drift_status)}
            <br><small>Δ/H = {drift_val}</small>
        </div>
        """, unsafe_allow_html=True)

    # Key Metrics Row
    st.markdown("### Key Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Live Load",
            f"{project.loads.live_load:.1f} kPa",
            help="From HK Code Table 3.2"
        )

    with col2:
        design_load = project.get_design_load()
        st.metric(
            "Design Load",
            f"{design_load:.1f} kPa",
            help=f"Factored load ({selected_comb_label})"
        )

    with col3:
        st.metric(
            "Concrete Volume",
            f"{project.concrete_volume:.1f} m\u00b3",
            help="Estimated total concrete volume"
        )

    with col4:
        carbon_per_m2 = project.carbon_emission / (project.geometry.bay_x * project.geometry.bay_y * project.geometry.floors) if project.geometry.floors > 0 else 0
        st.metric(
            "Carbon Intensity",
            f"{carbon_per_m2:.0f} kgCO\u2082e/m\u00b2",
            help="Embodied carbon per floor area"
        )

    # ===== FEM VIEWS SECTION (Relocated below Key Metrics per Task 21.1) =====
    st.markdown("### FEM Views")

    # Build FEM model for visualization
    try:
        fem_options = ModelBuilderOptions(
            include_core_wall=True,
            trim_beams_at_core=True,
            apply_gravity_loads=True,
            apply_wind_loads=st.session_state.get("fem_include_wind", True),
            apply_rigid_diaphragms=True,
            secondary_beam_direction="X" if secondary_along_x else "Y",
            num_secondary_beams=num_secondary_beams,
            omit_columns_near_core=True,
            suggested_omit_columns=[col for col, omit in st.session_state.get("omit_columns", {}).items() if omit]
        )
        fem_model_views = build_fem_model(project, fem_options)
        fem_stats = get_model_statistics(fem_model_views)
        fem_floor_levels = fem_stats.get("floor_elevations", [])

        # Helper function to format floor labels in HK convention
        def format_floor_label(z: float, floor_levels: list) -> str:
            """Format floor elevation as HK convention: G/F, 1/F, 2/F, etc."""
            if not floor_levels:
                return f"Z = {z:.2f}m"
            # Sort levels and find index
            sorted_levels = sorted(floor_levels)
            try:
                floor_index = sorted_levels.index(z)
            except ValueError:
                return f"Z = {z:.2f}m"
            # Ground floor is index 0, then 1/F, 2/F, etc.
            if floor_index == 0:
                return f"G/F (+{z:.2f})"
            else:
                return f"{floor_index}/F (+{z:.2f})"

        # View selection buttons in horizontal row: Plan (Left), Elevation (Center), 3D (Right)
        view_col1, view_col2, view_col3, floor_col = st.columns([1, 1, 1, 1.5])

        with view_col1:
            plan_btn = st.button("Plan View", key="fem_view_plan_btn", use_container_width=True)
        with view_col2:
            elev_btn = st.button("Elevation View", key="fem_view_elev_btn", use_container_width=True)
        with view_col3:
            view3d_btn = st.button("3D View", key="fem_view_3d_btn", use_container_width=True)
        with floor_col:
            # Floor selection dropdown with HK convention labels
            if fem_floor_levels:
                floor_options = sorted(fem_floor_levels)
                floor_labels = [format_floor_label(z, floor_options) for z in floor_options]
                selected_floor_idx = st.selectbox(
                    "Floor",
                    options=range(len(floor_options)),
                    index=len(floor_options) - 1,  # Default to top floor
                    format_func=lambda i: floor_labels[i],
                    key="fem_view_floor_select"
                )
                selected_view_floor = floor_options[selected_floor_idx]
            else:
                selected_view_floor = None
                st.info("No floor levels available")

        # Update session state for active view
        if plan_btn:
            st.session_state["fem_active_view"] = "plan"
        elif elev_btn:
            st.session_state["fem_active_view"] = "elevation"
        elif view3d_btn:
            st.session_state["fem_active_view"] = "3d"

        # Default to plan view if not set
        active_view = st.session_state.get("fem_active_view", "plan")

        # Build utilization map for coloring
        view_util_map = build_preview_utilization_map(fem_model_views, project)

        # Visualization config (simplified for FEM Views section)
        views_config = VisualizationConfig(
            show_nodes=False,
            show_supports=True,
            show_loads=False,
            show_labels=False,
            show_slabs=True,
            show_slab_mesh_grid=False,
            show_ghost_columns=True,
            grid_spacing=1.0,
        )

        # Display active view
        if active_view == "plan":
            plan_fig = create_plan_view(
                fem_model_views,
                config=views_config,
                floor_elevation=selected_view_floor,
                utilization=view_util_map,
            )
            st.plotly_chart(plan_fig, use_container_width=True)
            # Legend at bottom
            st.caption("**Legend:** Blue = Columns | Red = Beams | Orange = Secondary Beams | Gray = Core Walls")

        elif active_view == "elevation":
            elev_direction = st.radio(
                "Direction",
                options=["X", "Y"],
                horizontal=True,
                key="fem_view_elev_dir"
            )
            elev_fig = create_elevation_view(
                fem_model_views,
                config=views_config,
                view_direction=elev_direction,
                utilization=view_util_map,
            )
            st.plotly_chart(elev_fig, use_container_width=True)
            # Legend at bottom
            st.caption("**Legend:** Blue = Columns | Red = Beams | Green = Supports | Dashed = Floor lines")

        elif active_view == "3d":
            view3d_fig = create_3d_view(
                fem_model_views,
                config=views_config,
                utilization=view_util_map,
            )
            st.plotly_chart(view3d_fig, use_container_width=True)
            # Legend at bottom
            st.caption("**Legend:** Blue = Columns | Red/Orange = Beams | Gray = Core Walls | Green = Supports")

    except Exception as exc:
        st.warning(f"FEM Views unavailable: {exc}")

    # Visualizations Row
    st.markdown("### Structural Layout")
    col1, col2 = st.columns(2)

    with col1:
        grid_fig = create_framing_grid(project, secondary_along_x, num_secondary_beams)
        st.plotly_chart(grid_fig, use_container_width=True)

    with col2:
        lateral_fig = create_lateral_diagram(project)
        st.plotly_chart(lateral_fig, use_container_width=True)

    # FEM Analysis & Preview
    st.markdown("### FEM Analysis")
    st.caption("Preview the FEM model and optionally overlay OpenSees analysis results.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_nodes = st.checkbox("Show nodes", value=False, key="fem_preview_show_nodes")
    with col2:
        show_supports = st.checkbox("Show supports", value=True, key="fem_preview_show_supports")
    with col3:
        show_loads = st.checkbox("Show loads", value=True, key="fem_preview_show_loads")
    with col4:
        show_labels = st.checkbox("Show labels", value=False, key="fem_preview_show_labels")

    col5, col6 = st.columns(2)
    with col5:
        show_slabs = st.checkbox("Show slab elements", value=True, key="fem_preview_show_slabs")
    with col6:
        show_slab_mesh = st.checkbox("Show mesh grid", value=True, key="fem_preview_show_slab_mesh")

    show_ghost_columns = st.checkbox(
        "Show omitted columns (ghost)", 
        value=True, 
        key="fem_preview_show_ghost"
    )

    include_wind = st.checkbox(
        "Include wind loads in preview",
        value=True,
        key="fem_preview_include_wind",
    )

    try:
        options = ModelBuilderOptions(
            include_core_wall=True,
            trim_beams_at_core=True,
            apply_gravity_loads=True,
            apply_wind_loads=include_wind,
            apply_rigid_diaphragms=True,
            secondary_beam_direction="X" if secondary_along_x else "Y",
            num_secondary_beams=num_secondary_beams,
            omit_columns_near_core=True, # Enable the logic
            suggested_omit_columns=[col for col, omit in st.session_state.get("omit_columns", {}).items() if omit]
        )
        fem_model = build_fem_model(project, options)
        stats = get_model_statistics(fem_model)
        floor_levels = stats.get("floor_elevations", [])
        if floor_levels:
            selected_floor = st.selectbox(
                "Floor elevation (m)",
                options=floor_levels,
                index=len(floor_levels) - 1,
                format_func=lambda z: f"Z = {z:.2f} m",
                key="fem_preview_floor_level",
            )
        else:
            selected_floor = None

        # Task 20.5a - Model Statistics and Slab Load Display
        st.markdown("#### Model Statistics")
        stat_cols = st.columns(6)
        stat_cols[0].metric("Nodes", stats["n_nodes"])
        stat_cols[1].metric("Elements", stats["n_elements"])
        stat_cols[2].metric("Loads", stats["n_loads"])
        stat_cols[3].metric("Surface Loads", stats.get("n_surface_loads", 0))

        # Add Slab Design Load Metric
        if fem_model and options.include_slabs and fem_model.surface_loads:
            # Get pressure from first surface load (assume uniform)
            pressure_pa = fem_model.surface_loads[0].pressure
            slab_load_kpa = pressure_pa / 1000.0  # Convert Pa -> kPa
            stat_cols[4].metric("Slab Load", f"{slab_load_kpa:.2f} kPa")
            
            # Also add to sidebar as requested
            st.sidebar.divider()
            st.sidebar.markdown("##### FEM Slab Load")
            st.sidebar.metric("Design Surface Load", f"{slab_load_kpa:.2f} kPa")

        # Visualization controls
        st.markdown("#### Visualization Settings")
        viz_col1, viz_col2 = st.columns(2)
        with viz_col1:
            view_color_mode = st.selectbox(
                "Color Scheme",
                options=["Element Type", "Utilization"],
                index=0,
                help="Select coloring based on Element Type (Geometry) or Utilization Ratio",
                key="fem_preview_color_mode"
            )
        with viz_col2:
            grid_spacing = st.slider(
                "Grid Spacing (m)",
                min_value=0.5,
                max_value=5.0,
                value=1.0,
                step=0.5,
                help="Adjust the spacing of grid lines in Plan and Elevation views",
                key="fem_preview_grid_spacing"
            )

        util_map = build_preview_utilization_map(fem_model, project)
        # If Element Type mode is selected, ignore utilization map for coloring
        if view_color_mode == "Element Type":
            util_map = {}
        preview_config = VisualizationConfig(
            show_nodes=show_nodes,
            show_supports=show_supports,
            show_loads=show_loads,
            show_labels=show_labels,
            show_slabs=show_slabs,
            show_slab_mesh_grid=show_slab_mesh,
            show_ghost_columns=show_ghost_columns,
            grid_spacing=grid_spacing,
        )

        analysis_col1, analysis_col2 = st.columns(2)
        with analysis_col1:
            overlay_analysis = st.checkbox(
                "Overlay OpenSees results (deflection/reactions)",
                value=False,
                key="fem_preview_overlay_analysis",
            )
        with analysis_col2:
            analysis_pattern = st.selectbox(
                "Analysis load pattern",
                options=[options.gravity_load_pattern, options.wind_load_pattern],
                index=0,
                key="fem_preview_analysis_pattern",
            )

        if st.button("Run FEM Analysis", key="fem_preview_run_analysis"):
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            status_text.text("Building FEM model...")
            progress_bar.progress(0.3)

            status_text.text("Running OpenSees analysis...")
            result = analyze_model(fem_model, load_pattern=analysis_pattern)
            progress_bar.progress(0.8)

            status_text.text("Extracting results...")
            progress_bar.progress(1.0)
            st.session_state["fem_preview_analysis_result"] = result
            st.session_state["fem_preview_analysis_message"] = result.message

        analysis_result = st.session_state.get("fem_preview_analysis_result")
        analysis_message = st.session_state.get("fem_preview_analysis_message")

        if analysis_message:
            status = "success" if analysis_result and analysis_result.success else "warning"
            if status == "success":
                st.success(analysis_message)
            else:
                st.warning(analysis_message)

        displaced_nodes = None
        reactions = None
        if overlay_analysis and analysis_result and analysis_result.success:
            displaced_nodes = _analysis_result_to_displacements(analysis_result)
            reactions = analysis_result.node_reactions

        plan_tab, elevation_tab, view3d_tab = st.tabs(
            ["Plan View", "Elevation View", "3D View"]
        )

        with plan_tab:
            plan_fig = create_plan_view(
                fem_model,
                config=preview_config,
                floor_elevation=selected_floor,
                utilization=util_map,
            )
            st.plotly_chart(plan_fig, use_container_width=True)
            if view_color_mode == "Utilization":
                st.caption("Color scale uses preliminary design utilizations.")
            else:
                st.caption("Colors represent element types (Primary=Blue, Secondary=Orange, Beams=Red).")

        with elevation_tab:
            view_direction = st.radio(
                "Elevation direction",
                options=["X", "Y"],
                horizontal=True,
                key="fem_preview_elevation_direction",
            )
            elev_fig = create_elevation_view(
                fem_model,
                config=preview_config,
                view_direction=view_direction,
                utilization=util_map,
                displaced_nodes=displaced_nodes,
                reactions=reactions,
            )
            st.plotly_chart(elev_fig, use_container_width=True)
            if displaced_nodes:
                st.caption("Deflected shape and reactions use OpenSees results.")
            elif view_color_mode == "Utilization":
                st.caption("Floor lines reflect preliminary design utilizations.")
            else:
                st.caption("Colors represent element types.")

        with view3d_tab:
            view3d_fig = create_3d_view(
                fem_model,
                config=preview_config,
                utilization=util_map,
                displaced_nodes=displaced_nodes,
                reactions=reactions,
            )
            st.plotly_chart(view3d_fig, use_container_width=True)
            if displaced_nodes:
                st.caption("3D view includes OpenSees deflected shape and reactions.")
            elif view_color_mode == "Utilization":
                st.caption("3D view uses preliminary design utilizations.")
            else:
                st.caption("Colors represent element types.")

        # Export images
        st.markdown("#### Export Visualization")
        export_view = st.selectbox(
            "Select view to export",
            options=["Plan View", "Elevation View", "3D View"],
            key="fem_export_view",
        )
        export_format = st.selectbox(
            "Image format",
            options=["png", "svg", "pdf"],
            index=0,
            key="fem_export_format",
        )
        export_fig = plan_fig if export_view == "Plan View" else elev_fig if export_view == "Elevation View" else view3d_fig
        try:
            from src.fem.visualization import export_plotly_figure_image
            image_bytes = export_plotly_figure_image(export_fig, format=export_format)
            st.download_button(
                label="Download Image",
                data=image_bytes,
                file_name=f"fem_{export_view.replace(' ', '_').lower()}.{export_format}",
                mime=f"image/{export_format}",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"Image export unavailable: {exc}")
    except Exception as exc:
        st.warning(f"FEM preview unavailable: {exc}")

    # Detailed Results
    st.markdown("### Detailed Results")

    tab1, tab2, tab3, tab4 = st.tabs(["Slab", "Beams", "Columns", "Lateral"])

    with tab1:
        if project.slab_result:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **Slab Design Summary**
                - Type: Solid Slab (One-Way)
                - Thickness: **{project.slab_result.thickness} mm**
                - Design Moment: {project.slab_result.moment:.1f} kNm/m
                - Reinforcement: {project.slab_result.reinforcement_area:.0f} mm²/m
                - Self Weight: {project.slab_result.self_weight:.2f} kPa
                """)
            with col2:
                st.markdown(f"""
                **Checks**
                - Deflection Ratio: {project.slab_result.deflection_ratio:.2f}
                - Utilization: {project.slab_result.utilization:.2%}
                - Status: {project.slab_result.status}
                """)

    with tab2:
        if project.primary_beam_result:
            # Determine beam direction labels based on configuration
            if secondary_along_x:
                pri_dir = "Y-direction"
                sec_dir = "X-direction"
                pri_span = project.geometry.bay_y
                sec_span = project.geometry.bay_x
            else:
                pri_dir = "X-direction"
                sec_dir = "Y-direction"
                pri_span = project.geometry.bay_x
                sec_span = project.geometry.bay_y

            col1, col2 = st.columns(2)
            with col1:
                primary_status = "PASS" if project.primary_beam_result.utilization <= 1.0 else "FAIL"
                primary_status_color = "#10B981" if primary_status == "PASS" else "#EF4444"
                st.markdown(f"""
                **Primary Beam ({pri_dir})**
                - Size: **{project.primary_beam_result.width} x {project.primary_beam_result.depth} mm**
                - Span: {pri_span:.1f} m
                - Design Moment: {project.primary_beam_result.moment:.1f} kNm
                - Design Shear: {project.primary_beam_result.shear:.1f} kN
                - Shear Capacity: {project.primary_beam_result.shear_capacity:.1f} kN
                - Shear Links: T10 @ {project.primary_beam_result.link_spacing} mm c/c

                **Checks**
                - Utilization: **{project.primary_beam_result.utilization:.1%}**
                - Status: <span style="color: {primary_status_color}; font-weight: bold;">{primary_status}</span>
                - Iterations: {project.primary_beam_result.iteration_count}
                """, unsafe_allow_html=True)
            with col2:
                secondary_status = "PASS" if project.secondary_beam_result.utilization <= 1.0 else "FAIL"
                secondary_status_color = "#10B981" if secondary_status == "PASS" else "#EF4444"
                st.markdown(f"""
                **Secondary Beam ({sec_dir})**
                - Size: **{project.secondary_beam_result.width} x {project.secondary_beam_result.depth} mm**
                - Span: {sec_span:.1f} m
                - Design Moment: {project.secondary_beam_result.moment:.1f} kNm
                - Design Shear: {project.secondary_beam_result.shear:.1f} kN
                - Shear Capacity: {project.secondary_beam_result.shear_capacity:.1f} kN

                **Checks**
                - Utilization: **{project.secondary_beam_result.utilization:.1%}**
                - Status: <span style="color: {secondary_status_color}; font-weight: bold;">{secondary_status}</span>
                - Iterations: {project.secondary_beam_result.iteration_count}
                """, unsafe_allow_html=True)

            if project.primary_beam_result.is_deep_beam or project.secondary_beam_result.is_deep_beam:
                st.warning("Deep beam detected (L/d < 2.0). Strut-and-Tie Model required.")

    with tab3:
        if project.column_result:
            st.markdown(f"""
            **Column Design Summary**
            - Size: **{project.column_result.dimension} x {project.column_result.dimension} mm**
            - Axial Load: {project.column_result.axial_load:.1f} kN
            - Design Moment: {project.column_result.moment:.1f} kNm
            - Slenderness: {project.column_result.slenderness:.1f} {'(Slender)' if project.column_result.is_slender else '(Short)'}
            - Utilization: {project.column_result.utilization:.2%}
            """)

            if project.column_result.has_lateral_loads:
                st.markdown(f"""
                **Lateral Load Effects (Moment Frame)**
                - Lateral Shear: {project.column_result.lateral_shear:.1f} kN
                - Lateral Moment: {project.column_result.lateral_moment:.1f} kNm
                - Combined Utilization: {project.column_result.combined_utilization:.2%}
                """)

    with tab4:
        if project.wind_result:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **Wind Load Analysis (HK Wind Code 2019)**
                - Terrain: {selected_terrain_label}
                - Building Height: {project.geometry.story_height * project.geometry.floors:.1f} m
                - Reference Pressure: {project.wind_result.reference_pressure:.2f} kPa
                - **Base Shear: {project.wind_result.base_shear:.1f} kN**
                - **Overturning Moment: {project.wind_result.overturning_moment:.1f} kNm**
                """)
            with col2:
                st.markdown(f"""
                **Drift Check**
                - Lateral System: {project.wind_result.lateral_system}
                - Top Drift: {project.wind_result.drift_mm:.1f} mm
                - Drift Index: {project.wind_result.drift_index:.6f}
                - Limit: 1/500 = 0.002
                - Status: {'PASS' if project.wind_result.drift_ok else 'FAIL'}
                """)

            if project.core_wall_result:
                st.markdown(f"""
                **Core Wall Check**
                - Compression Utilization: {project.core_wall_result.compression_check:.2%}
                - Shear Utilization: {project.core_wall_result.shear_check:.2%}
                - Tension Piles Required: {'Yes' if project.core_wall_result.requires_tension_piles else 'No'}
                """)

    # ===== REPORT GENERATION SECTION =====
    st.markdown("### Generate Report")
    st.markdown("""
    <p style="color: #64748B; font-size: 14px;">
        Generate a professional Magazine-Style HTML report with your design results.
    </p>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        ai_review_text = st.text_area(
            "AI Design Review (Optional)",
            placeholder="Enter design review commentary here, or leave blank for placeholder text...",
            height=100,
            help="This text will appear in the AI Design Review section of the report. Future versions will integrate AI-generated commentary."
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)

        # Project info for report
        report_project_name = st.text_input("Project Name", value=project.project_name or "Untitled Project")
        report_project_number = st.text_input("Project Number", value=project.project_number or "PROJ-001")
        report_engineer = st.text_input("Engineer", value=project.engineer or "Design Engineer")

    # Update project metadata
    project.project_name = report_project_name
    project.project_number = report_project_number
    project.engineer = report_engineer
    project.date = datetime.now().strftime("%Y-%m-%d")

    # Generate Report Button
    if st.button("Generate HTML Report", type="primary", use_container_width=True):
        with st.spinner("Generating report..."):
            # Generate the report
            generator = ReportGenerator(project)
            ai_review = ai_review_text if ai_review_text.strip() else None
            html_content = generator.generate(ai_review=ai_review)

            # Create download button
            st.download_button(
                label="Download Report (HTML)",
                data=html_content,
                file_name=f"{report_project_name.replace(' ', '_')}_Report.html",
                mime="text/html",
                use_container_width=True
            )

            st.success("Report generated successfully! Click the download button above to save.")

            # Show preview in expander
            with st.expander("Preview Report"):
                st.components.v1.html(html_content, height=800, scrolling=True)

    # Footer
    st.divider()
    st.markdown("""
    <p style="text-align: center; color: #94A3B8; font-size: 12px;">
        PrelimStruct v3.0 | FEM + AI-Assisted Design | HK Code 2013 + Wind Code 2019
    </p>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
