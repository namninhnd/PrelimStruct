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
    SlabType, SpanDirection, ExposureClass, TerrainCategory,
    CoreLocation, ColumnPosition, LoadCombination, PRESETS,
)
from src.core.constants import CARBON_FACTORS
from src.core.load_tables import LIVE_LOAD_TABLE

# Import engines
from src.engines.slab_engine import SlabEngine
from src.engines.beam_engine import BeamEngine
from src.engines.column_engine import ColumnEngine
from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine

# Import report generator
from src.report.report_generator import ReportGenerator


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


def create_framing_grid(project: ProjectData) -> go.Figure:
    """Create interactive framing grid visualization"""
    bay_x = project.geometry.bay_x
    bay_y = project.geometry.bay_y

    # Create figure
    fig = go.Figure()

    # Grid lines (beams)
    # Primary beams (horizontal)
    for y in [0, bay_y]:
        color = "#EF4444" if (project.primary_beam_result and
                             project.primary_beam_result.utilization > 1.0) else "#2D5A87"
        fig.add_trace(go.Scatter(
            x=[0, bay_x], y=[y, y],
            mode='lines',
            line=dict(color=color, width=6),
            name='Primary Beam',
            showlegend=(y == 0),
            hovertemplate=f"Primary Beam<br>Span: {bay_x:.1f}m<extra></extra>"
        ))

    # Secondary beams (vertical)
    for x in [0, bay_x]:
        color = "#EF4444" if (project.secondary_beam_result and
                             project.secondary_beam_result.utilization > 1.0) else "#4CAF50"
        fig.add_trace(go.Scatter(
            x=[x, x], y=[0, bay_y],
            mode='lines',
            line=dict(color=color, width=4),
            name='Secondary Beam',
            showlegend=(x == 0),
            hovertemplate=f"Secondary Beam<br>Span: {bay_y:.1f}m<extra></extra>"
        ))

    # Columns (at corners)
    col_positions = [(0, 0), (bay_x, 0), (0, bay_y), (bay_x, bay_y)]
    col_labels = ['Corner', 'Corner', 'Corner', 'Corner']

    for (x, y), label in zip(col_positions, col_labels):
        color = "#EF4444" if (project.column_result and
                             project.column_result.utilization > 1.0) else "#1E3A5F"
        size_text = f"{project.column_result.dimension}mm" if project.column_result else "TBD"
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode='markers',
            marker=dict(size=20, color=color, symbol='square'),
            name='Column',
            showlegend=(x == 0 and y == 0),
            hovertemplate=f"Column ({label})<br>Size: {size_text}<extra></extra>"
        ))

    # Slab hatch (fill area)
    slab_color = "rgba(45, 90, 135, 0.1)"
    if project.slab_result and project.slab_result.utilization > 1.0:
        slab_color = "rgba(239, 68, 68, 0.2)"

    fig.add_trace(go.Scatter(
        x=[0, bay_x, bay_x, 0, 0],
        y=[0, 0, bay_y, bay_y, 0],
        fill="toself",
        fillcolor=slab_color,
        line=dict(color="rgba(0,0,0,0)"),
        name='Slab',
        hovertemplate=f"Slab<br>Thickness: {project.slab_result.thickness if project.slab_result else 'TBD'}mm<extra></extra>"
    ))

    # Core wall (if defined)
    if project.lateral.core_dim_x > 0 and project.lateral.core_dim_y > 0:
        core_x = project.lateral.core_dim_x
        core_y = project.lateral.core_dim_y

        # Position based on core location
        if project.lateral.core_location == CoreLocation.CENTER:
            cx = (bay_x - core_x) / 2
            cy = (bay_y - core_y) / 2
        elif project.lateral.core_location == CoreLocation.SIDE:
            cx = bay_x - core_x - 0.5
            cy = (bay_y - core_y) / 2
        else:  # CORNER
            cx = bay_x - core_x - 0.5
            cy = bay_y - core_y - 0.5

        fig.add_trace(go.Scatter(
            x=[cx, cx + core_x, cx + core_x, cx, cx],
            y=[cy, cy, cy + core_y, cy + core_y, cy],
            fill="toself",
            fillcolor="rgba(30, 58, 95, 0.5)",
            line=dict(color="#1E3A5F", width=3),
            name='Core Wall',
            hovertemplate=f"Core Wall<br>Size: {core_x:.1f}m x {core_y:.1f}m<extra></extra>"
        ))

    # Layout
    fig.update_layout(
        title=dict(
            text="Framing Plan (Single Bay)",
            font=dict(size=16, color="#1E3A5F")
        ),
        xaxis=dict(
            title="X (m)",
            range=[-1, bay_x + 1],
            scaleanchor="y",
            constrain="domain"
        ),
        yaxis=dict(
            title="Y (m)",
            range=[-1, bay_y + 1],
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        height=400,
        margin=dict(l=40, r=40, t=60, b=60)
    )

    return fig


def create_lateral_diagram(project: ProjectData) -> go.Figure:
    """Create wind load and lateral system diagram"""
    height = project.geometry.story_height * project.geometry.floors
    width = project.lateral.building_width or project.geometry.bay_x

    fig = go.Figure()

    # Building outline
    fig.add_trace(go.Scatter(
        x=[0, width, width, 0, 0],
        y=[0, 0, height, height, 0],
        mode='lines',
        line=dict(color="#1E3A5F", width=3),
        name='Building',
        fill='toself',
        fillcolor='rgba(45, 90, 135, 0.1)'
    ))

    # Wind arrows
    wind_base_shear = project.wind_result.base_shear if project.wind_result else 0
    arrow_scale = min(width * 0.3, 2)  # Scale arrows based on building width

    for i in range(project.geometry.floors):
        y_pos = (i + 0.5) * project.geometry.story_height
        # Arrow size increases with height (simplified)
        arrow_length = arrow_scale * (0.5 + 0.5 * (i + 1) / project.geometry.floors)

        fig.add_annotation(
            x=-arrow_length,
            y=y_pos,
            ax=-arrow_length - 1.5,
            ay=y_pos,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor="#F59E0B"
        )

    # Add wind label
    fig.add_annotation(
        x=-3,
        y=height / 2,
        text=f"Wind<br>{wind_base_shear:.0f} kN",
        showarrow=False,
        font=dict(size=12, color="#F59E0B")
    )

    # Drift indicator (if available)
    if project.wind_result and project.wind_result.drift_mm > 0:
        drift = project.wind_result.drift_mm
        drift_color = "#10B981" if project.wind_result.drift_ok else "#EF4444"

        fig.add_trace(go.Scatter(
            x=[width, width + drift/100],  # Scale drift for visibility
            y=[0, height],
            mode='lines',
            line=dict(color=drift_color, width=2, dash='dash'),
            name=f'Drift ({drift:.1f}mm)'
        ))

    # Layout
    fig.update_layout(
        title=dict(
            text="Lateral Load Diagram",
            font=dict(size=16, color="#1E3A5F")
        ),
        xaxis=dict(
            title="Width (m)",
            range=[-5, width + 3],
            scaleanchor="y"
        ),
        yaxis=dict(
            title="Height (m)",
            range=[-1, height + 2]
        ),
        showlegend=True,
        height=400,
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return fig


def run_calculations(project: ProjectData) -> ProjectData:
    """Run all structural calculations"""
    # Create engines
    slab_engine = SlabEngine(project)
    beam_engine = BeamEngine(project)
    column_engine = ColumnEngine(project)

    # Slab design
    project.slab_result = slab_engine.calculate()

    # Beam design
    tributary_width = project.geometry.bay_y / 2  # Half bay each side
    project.primary_beam_result = beam_engine.calculate_primary_beam(tributary_width)
    project.secondary_beam_result = beam_engine.calculate_secondary_beam(tributary_width)

    # Column design (interior for now)
    project.column_result = column_engine.calculate(ColumnPosition.INTERIOR)

    # Wind / Lateral analysis
    if project.lateral.building_width == 0:
        project.lateral.building_width = project.geometry.bay_x
    if project.lateral.building_depth == 0:
        project.lateral.building_depth = project.geometry.bay_y

    wind_engine = WindEngine(project)
    project.wind_result = wind_engine.calculate_wind_loads()

    # Core wall check and drift calculation (if core defined)
    if project.lateral.core_dim_x > 0 and project.lateral.core_dim_y > 0:
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

            # Check combined P+M (returns tuple: utilization, status, warnings)
            utilization, status, warnings = column_engine.check_combined_load(
                project.column_result.axial_load,
                first_col_load[1],
                project.column_result.dimension,
                project.materials.fcu_column
            )
            project.column_result.combined_utilization = utilization

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
    with st.sidebar:
        st.markdown("### Project Settings")

        # Quick Scheme Presets
        st.markdown("##### Quick Presets")
        preset_options = ["Custom"] + [PRESETS[k]["name"] for k in PRESETS.keys()]
        preset_keys = ["custom"] + list(PRESETS.keys())

        selected_preset_name = st.selectbox(
            "Building Type",
            options=preset_options,
            help="Select a preset to auto-fill typical values"
        )
        selected_preset = preset_keys[preset_options.index(selected_preset_name)]

        if selected_preset != "custom" and st.button("Apply Preset"):
            preset = PRESETS[selected_preset]
            st.session_state.project.loads = preset["loads"]
            st.session_state.project.materials = preset["materials"]
            st.rerun()

        st.divider()

        # Geometry Inputs
        st.markdown("##### Geometry")
        col1, col2 = st.columns(2)
        with col1:
            bay_x = st.number_input("Bay X (m)", min_value=3.0, max_value=15.0,
                                   value=float(st.session_state.project.geometry.bay_x), step=0.5)
        with col2:
            bay_y = st.number_input("Bay Y (m)", min_value=3.0, max_value=15.0,
                                   value=float(st.session_state.project.geometry.bay_y), step=0.5)

        col1, col2 = st.columns(2)
        with col1:
            floors = st.number_input("Floors", min_value=1, max_value=50,
                                    value=st.session_state.project.geometry.floors, step=1)
        with col2:
            story_height = st.number_input("Story Height (m)", min_value=2.5, max_value=6.0,
                                          value=float(st.session_state.project.geometry.story_height), step=0.1)

        st.divider()

        # Loading Inputs
        st.markdown("##### Loading")

        # Live load class selection
        class_options = [(k, v["name"]) for k, v in LIVE_LOAD_TABLE.items()]
        class_labels = [f"{k}: {name}" for k, name in class_options]
        class_keys = [k for k, _ in class_options]

        selected_class_label = st.selectbox(
            "Live Load Class",
            options=class_labels,
            index=class_keys.index(st.session_state.project.loads.live_load_class) if st.session_state.project.loads.live_load_class in class_keys else 1
        )
        selected_class = class_keys[class_labels.index(selected_class_label)]

        # Live load subdivision
        if selected_class in LIVE_LOAD_TABLE:
            sub_options = [(e.code, e.description, e.get_load()) for e in LIVE_LOAD_TABLE[selected_class]["loads"]]
            sub_labels = [f"{code}: {desc} ({load:.1f} kPa)" for code, desc, load in sub_options]
            sub_codes = [code for code, _, _ in sub_options]

            current_sub = st.session_state.project.loads.live_load_sub
            default_idx = sub_codes.index(current_sub) if current_sub in sub_codes else 0

            selected_sub_label = st.selectbox("Subdivision", options=sub_labels, index=default_idx)
            selected_sub = sub_codes[sub_labels.index(selected_sub_label)]
        else:
            selected_sub = "2.5"

        dead_load = st.number_input("SDL (kPa)", min_value=0.5, max_value=10.0,
                                   value=float(st.session_state.project.loads.dead_load), step=0.5,
                                   help="Superimposed Dead Load (finishes, services)")

        st.divider()

        # Material Inputs
        st.markdown("##### Materials")

        concrete_grades = [25, 30, 35, 40, 45, 50, 55, 60]

        col1, col2 = st.columns(2)
        with col1:
            fcu_slab = st.selectbox("Slab fcu", options=concrete_grades,
                                   index=concrete_grades.index(st.session_state.project.materials.fcu_slab))
        with col2:
            fcu_beam = st.selectbox("Beam fcu", options=concrete_grades,
                                   index=concrete_grades.index(st.session_state.project.materials.fcu_beam))

        fcu_column = st.selectbox("Column fcu", options=concrete_grades,
                                 index=concrete_grades.index(st.session_state.project.materials.fcu_column))

        exposure_options = {
            ExposureClass.MILD: "1: Mild (Interior)",
            ExposureClass.MODERATE: "2: Moderate (Sheltered)",
            ExposureClass.SEVERE: "3: Severe (Exposed)",
            ExposureClass.VERY_SEVERE: "4: Very Severe (Marine)",
            ExposureClass.ABRASIVE: "5: Abrasive (Chemical)"
        }

        selected_exposure_label = st.selectbox(
            "Exposure Class",
            options=list(exposure_options.values()),
            index=list(exposure_options.keys()).index(st.session_state.project.materials.exposure)
        )
        selected_exposure = list(exposure_options.keys())[list(exposure_options.values()).index(selected_exposure_label)]

        st.divider()

        # Lateral System
        st.markdown("##### Lateral System")

        terrain_options = {
            TerrainCategory.OPEN_SEA: "A: Open Sea",
            TerrainCategory.OPEN_COUNTRY: "B: Open Country",
            TerrainCategory.URBAN: "C: Urban",
            TerrainCategory.CITY_CENTRE: "D: City Centre"
        }

        selected_terrain_label = st.selectbox(
            "Terrain Category",
            options=list(terrain_options.values()),
            index=list(terrain_options.keys()).index(st.session_state.project.lateral.terrain)
        )
        selected_terrain = list(terrain_options.keys())[list(terrain_options.values()).index(selected_terrain_label)]

        has_core = st.checkbox("Core Wall System",
                              value=st.session_state.project.lateral.core_dim_x > 0)

        if has_core:
            col1, col2 = st.columns(2)
            with col1:
                core_x = st.number_input("Core X (m)", min_value=2.0, max_value=15.0,
                                        value=max(4.0, float(st.session_state.project.lateral.core_dim_x)), step=0.5)
            with col2:
                core_y = st.number_input("Core Y (m)", min_value=2.0, max_value=15.0,
                                        value=max(4.0, float(st.session_state.project.lateral.core_dim_y)), step=0.5)

            core_location_options = {
                CoreLocation.CENTER: "Center",
                CoreLocation.SIDE: "Side",
                CoreLocation.CORNER: "Corner"
            }
            selected_core_loc_label = st.selectbox(
                "Core Location",
                options=list(core_location_options.values()),
                index=list(core_location_options.keys()).index(st.session_state.project.lateral.core_location)
            )
            selected_core_location = list(core_location_options.keys())[list(core_location_options.values()).index(selected_core_loc_label)]
        else:
            core_x = 0.0
            core_y = 0.0
            selected_core_location = CoreLocation.CENTER

        st.divider()

        # Load Combination Toggle
        st.markdown("##### Load Combination")
        load_comb_options = {
            LoadCombination.ULS_GRAVITY: "ULS: 1.4Gk + 1.6Qk",
            LoadCombination.ULS_WIND: "ULS: 1.0Gk + 1.4Wk",
            LoadCombination.SLS_DEFLECTION: "SLS: 1.0Gk + 1.0Qk"
        }

        selected_comb_label = st.selectbox(
            "Active Combination",
            options=list(load_comb_options.values()),
            index=list(load_comb_options.keys()).index(st.session_state.project.load_combination)
        )
        selected_load_comb = list(load_comb_options.keys())[list(load_comb_options.values()).index(selected_comb_label)]

    # Update project data
    project = st.session_state.project
    project.geometry = GeometryInput(bay_x, bay_y, floors, story_height)
    project.loads = LoadInput(selected_class, selected_sub, dead_load)
    project.materials = MaterialInput(fcu_slab, fcu_beam, fcu_column, exposure=selected_exposure)
    project.lateral = LateralInput(
        core_dim_x=core_x,
        core_dim_y=core_y,
        core_location=selected_core_location,
        terrain=selected_terrain,
        building_width=bay_x,  # Single bay for now
        building_depth=bay_y
    )
    project.load_combination = selected_load_comb

    # Run calculations
    project = run_calculations(project)
    st.session_state.project = project

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
        if project.lateral.core_dim_x > 0 and project.core_wall_result:
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

    # Visualizations Row
    st.markdown("### Structural Layout")
    col1, col2 = st.columns(2)

    with col1:
        grid_fig = create_framing_grid(project)
        st.plotly_chart(grid_fig, use_container_width=True)

    with col2:
        lateral_fig = create_lateral_diagram(project)
        st.plotly_chart(lateral_fig, use_container_width=True)

    # Detailed Results
    st.markdown("### Detailed Results")

    tab1, tab2, tab3, tab4 = st.tabs(["Slab", "Beams", "Columns", "Lateral"])

    with tab1:
        if project.slab_result:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **Slab Design Summary**
                - Type: {project.slab_design.slab_type.value}
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
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **Primary Beam (X-direction)**
                - Size: **{project.primary_beam_result.width} x {project.primary_beam_result.depth} mm**
                - Span: {project.geometry.bay_x:.1f} m
                - Design Moment: {project.primary_beam_result.moment:.1f} kNm
                - Design Shear: {project.primary_beam_result.shear:.1f} kN
                - Shear Links: T10 @ {project.primary_beam_result.link_spacing} mm c/c
                """)
            with col2:
                st.markdown(f"""
                **Secondary Beam (Y-direction)**
                - Size: **{project.secondary_beam_result.width} x {project.secondary_beam_result.depth} mm**
                - Span: {project.geometry.bay_y:.1f} m
                - Design Moment: {project.secondary_beam_result.moment:.1f} kNm
                - Design Shear: {project.secondary_beam_result.shear:.1f} kN
                """)

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
        PrelimStruct v2.1 | HK Code 2013 + Wind Code 2019 | For preliminary design only
    </p>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
