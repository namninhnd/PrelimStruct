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
from src.core.load_tables import LIVE_LOAD_TABLE

# V3.5: Engine imports removed - FEM-only architecture
# from src.engines.slab_engine import SlabEngine
# from src.engines.beam_engine import BeamEngine
# from src.engines.column_engine import ColumnEngine
# from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine

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
    get_column_omission_suggestions
)
from src.ui.views.fem_views import render_unified_fem_views, _is_inputs_locked, _unlock_inputs
from src.fem.visualization import VisualizationConfig, get_model_statistics
from src.fem.solver import analyze_model
from src.fem.load_combinations import (
    LoadCombinationLibrary,
    LoadCombinationCategory,
    LoadCombinationDefinition,
)

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


def get_core_wall_outline(geometry: CoreWallGeometry) -> Optional[list]:
    """Get outline coordinates for core wall visualization.

    Args:
        geometry: CoreWallGeometry with configuration and dimensions

    Returns:
        List of (x, y) tuples or None if generation fails
    """
    try:
        if geometry.config == CoreWallConfig.I_SECTION:
            core_wall = ISectionCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        elif geometry.config == CoreWallConfig.TWO_C_FACING:
            core_wall = TwoCFacingCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        elif geometry.config == CoreWallConfig.TWO_C_BACK_TO_BACK:
            core_wall = TwoCBackToBackCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        elif geometry.config == CoreWallConfig.TUBE_CENTER_OPENING:
            core_wall = TubeCenterOpeningCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        elif geometry.config == CoreWallConfig.TUBE_SIDE_OPENING:
            core_wall = TubeSideOpeningCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        else:
            return None
    except Exception as e:
        st.warning(f"Failed to generate core wall outline: {str(e)}")
        return None


def get_coupling_beams(geometry: CoreWallGeometry, story_height: float = 3000.0) -> list:
    """Generate coupling beams for core wall openings.

    Args:
        geometry: CoreWallGeometry with configuration and dimensions
        story_height: Story height in mm (default 3000mm)

    Returns:
        List of CouplingBeam objects or empty list if none
    """
    try:
        generator = CouplingBeamGenerator(geometry)
        return generator.generate_coupling_beams(story_height=story_height)
    except Exception as e:
        st.warning(f"Failed to generate coupling beams: {str(e)}")
        return []


def create_beam_geometries_from_project(project: ProjectData, core_offset_x: float, core_offset_y: float) -> list:
    """Create BeamGeometry objects from project framing layout.

    Args:
        project: ProjectData with geometry configuration
        core_offset_x: Core wall X offset in meters
        core_offset_y: Core wall Y offset in meters

    Returns:
        List of BeamGeometry objects representing all beams in plan
    """
    bay_x = project.geometry.bay_x
    bay_y = project.geometry.bay_y
    num_bays_x = project.geometry.num_bays_x
    num_bays_y = project.geometry.num_bays_y
    total_x = bay_x * num_bays_x
    total_y = bay_y * num_bays_y

    beams = []

    # Horizontal beams (along X direction)
    for iy in range(num_bays_y + 1):
        y_pos = iy * bay_y * 1000  # Convert to mm
        beam = BeamGeometry(
            start_x=0,
            start_y=y_pos,
            end_x=total_x * 1000,
            end_y=y_pos,
            width=300.0,
            beam_id=f"H{iy}"
        )
        beams.append(beam)

    # Vertical beams (along Y direction)
    for ix in range(num_bays_x + 1):
        x_pos = ix * bay_x * 1000  # Convert to mm
        beam = BeamGeometry(
            start_x=x_pos,
            start_y=0,
            end_x=x_pos,
            end_y=total_y * 1000,
            width=300.0,
            beam_id=f"V{ix}"
        )
        beams.append(beam)

    return beams


def create_framing_grid(project: ProjectData, secondary_along_x: bool = False, num_secondary_beams: int = 3) -> go.Figure:
    """Create interactive framing grid visualization with multi-bay support"""
    bay_x = project.geometry.bay_x
    bay_y = project.geometry.bay_y
    num_bays_x = project.geometry.num_bays_x
    num_bays_y = project.geometry.num_bays_y
    total_x = bay_x * num_bays_x
    total_y = bay_y * num_bays_y

    # Create figure
    fig = go.Figure()

    # Colors based on utilization
    pri_color = "#EF4444" if (project.primary_beam_result and
                             project.primary_beam_result.utilization > 1.0) else "#2D5A87"
    sec_color = "#EF4444" if (project.secondary_beam_result and
                             project.secondary_beam_result.utilization > 1.0) else "#4CAF50"

    # Draw slab fills for each bay first (so they're behind beams)
    slab_color = "rgba(45, 90, 135, 0.1)"
    if project.slab_result and project.slab_result.utilization > 1.0:
        slab_color = "rgba(239, 68, 68, 0.2)"

    first_slab = True
    for ix in range(num_bays_x):
        for iy in range(num_bays_y):
            x0 = ix * bay_x
            y0 = iy * bay_y
            fig.add_trace(go.Scatter(
                x=[x0, x0 + bay_x, x0 + bay_x, x0, x0],
                y=[y0, y0, y0 + bay_y, y0 + bay_y, y0],
                fill="toself",
                fillcolor=slab_color,
                line=dict(color="rgba(0,0,0,0)"),
                name='Slab',
                showlegend=first_slab,
                hovertemplate=f"Slab<br>Thickness: {project.slab_result.thickness if project.slab_result else 'TBD'}mm<extra></extra>"
            ))
            first_slab = False

    # Primary beams - horizontal gridlines (at all y positions)
    first_pri = True
    for iy in range(num_bays_y + 1):
        y_pos = iy * bay_y
        fig.add_trace(go.Scatter(
            x=[0, total_x], y=[y_pos, y_pos],
            mode='lines',
            line=dict(color=pri_color, width=6),
            name='Primary Beam',
            showlegend=first_pri,
            hovertemplate=f"Primary Beam<br>Span: {bay_x:.1f}m<extra></extra>"
        ))
        first_pri = False

    # Primary beams - vertical gridlines (at all x positions)
    for ix in range(num_bays_x + 1):
        x_pos = ix * bay_x
        fig.add_trace(go.Scatter(
            x=[x_pos, x_pos], y=[0, total_y],
            mode='lines',
            line=dict(color=pri_color, width=6),
            name='Primary Beam',
            showlegend=False,
            hovertemplate=f"Primary Beam<br>Span: {bay_y:.1f}m<extra></extra>"
        ))

    # Secondary beams - internal beams in each bay
    first_sec = True
    for ix in range(num_bays_x):
        for iy in range(num_bays_y):
            x0 = ix * bay_x
            y0 = iy * bay_y

            if secondary_along_x:
                # Secondary beams along X (internal horizontal beams)
                if num_secondary_beams > 0:
                    spacing = bay_y / (num_secondary_beams + 1)
                    for i in range(num_secondary_beams):
                        y_pos = y0 + spacing * (i + 1)
                        fig.add_trace(go.Scatter(
                            x=[x0, x0 + bay_x], y=[y_pos, y_pos],
                            mode='lines',
                            line=dict(color=sec_color, width=4),
                            name='Secondary Beam',
                            showlegend=first_sec,
                            hovertemplate=f"Secondary Beam<br>Span: {bay_x:.1f}m<extra></extra>"
                        ))
                        first_sec = False
            else:
                # Secondary beams along Y (internal vertical beams)
                if num_secondary_beams > 0:
                    spacing = bay_x / (num_secondary_beams + 1)
                    for i in range(num_secondary_beams):
                        x_pos = x0 + spacing * (i + 1)
                        fig.add_trace(go.Scatter(
                            x=[x_pos, x_pos], y=[y0, y0 + bay_y],
                            mode='lines',
                            line=dict(color=sec_color, width=4),
                            name='Secondary Beam',
                            showlegend=first_sec,
                            hovertemplate=f"Secondary Beam<br>Span: {bay_y:.1f}m<extra></extra>"
                        ))
                        first_sec = False

    # Columns at all grid intersections
    first_col = True
    for ix in range(num_bays_x + 1):
        for iy in range(num_bays_y + 1):
            x_pos = ix * bay_x
            y_pos = iy * bay_y
            color = "#EF4444" if (project.column_result and
                                 project.column_result.utilization > 1.0) else "#1E3A5F"
            size_text = f"{project.column_result.dimension}mm" if project.column_result else "TBD"
            fig.add_trace(go.Scatter(
                x=[x_pos], y=[y_pos],
                mode='markers',
                marker=dict(size=20, color=color, symbol='square'),
                name='Column',
                showlegend=first_col,
                hovertemplate=f"Column<br>Size: {size_text}<extra></extra>"
            ))
            first_col = False

    # Core wall (if defined) - positioned relative to full building
    if project.lateral.core_geometry:
        # Extract dimensions from geometry (mm -> m)
        core_x = project.lateral.core_geometry.length_x / 1000.0 if project.lateral.core_geometry.length_x else 0.0
        core_y = project.lateral.core_geometry.length_y / 1000.0 if project.lateral.core_geometry.length_y else 0.0

        # Position based on core location (relative to total building)
        # Position based on core location (relative to total building)
        # Default to CENTER for visualization since core_location enum is removed
        cx = (total_x - core_x) / 2
        cy = (total_y - core_y) / 2
        
        # If we had legacy side/corner logic:
        # if project.lateral.core_location == "side":
        #    cx = total_x - core_x - 0.5
        #    cy = (total_y - core_y) / 2
        # elif project.lateral.core_location == "corner":
        #    cx = total_x - core_x - 0.5
        #    cy = total_y - core_y - 0.5

        # Get core wall outline from geometry if available
        if project.lateral.core_geometry:
            outline_coords = get_core_wall_outline(project.lateral.core_geometry)

            if outline_coords:
                # Convert mm to m and offset by core wall position
                outline_x = [cx + (coord[0] / 1000) for coord in outline_coords]
                outline_y = [cy + (coord[1] / 1000) for coord in outline_coords]

                # Add outline trace
                fig.add_trace(go.Scatter(
                    x=outline_x,
                    y=outline_y,
                    fill="toself",
                    fillcolor="rgba(30, 58, 95, 0.3)",
                    line=dict(color="#1E3A5F", width=3),
                    name='Core Wall',
                    hovertemplate=f"Core Wall<br>Config: {project.lateral.core_wall_config.value if project.lateral.core_wall_config else 'N/A'}<br>Wall Thickness: {project.lateral.wall_thickness}mm<extra></extra>"
                ))
            else:
                # Fallback to simple rectangle if outline generation fails
                fig.add_trace(go.Scatter(
                    x=[cx, cx + core_x, cx + core_x, cx, cx],
                    y=[cy, cy, cy + core_y, cy + core_y, cy],
                    fill="toself",
                    fillcolor="rgba(30, 58, 95, 0.3)",
                    line=dict(color="#1E3A5F", width=3),
                    name='Core Wall',
                    hovertemplate=f"Core Wall<br>Size: {core_x:.1f}m x {core_y:.1f}m<extra></extra>"
                ))
        else:
            # Legacy visualization (simple rectangle) for backward compatibility
            fig.add_trace(go.Scatter(
                x=[cx, cx + core_x, cx + core_x, cx, cx],
                y=[cy, cy, cy + core_y, cy + core_y, cy],
                fill="toself",
                fillcolor="rgba(30, 58, 95, 0.3)",
                line=dict(color="#1E3A5F", width=3),
                name='Core Wall',
                hovertemplate=f"Core Wall<br>Size: {core_x:.1f}m x {core_y:.1f}m<extra></extra>"
            ))

        # Coupling beams (if core geometry available)
        if project.lateral.core_geometry:
            coupling_beams = get_coupling_beams(
                project.lateral.core_geometry,
                story_height=project.geometry.story_height * 1000  # Convert to mm
            )

            if coupling_beams:
                first_coupling = True
                for cb in coupling_beams:
                    # Convert coupling beam coordinates from mm to m and apply offset
                    cb_x = cx + (cb.location_x / 1000)
                    cb_y = cy + (cb.location_y / 1000)
                    cb_span = cb.clear_span / 1000  # m
                    cb_width = cb.width / 1000  # m

                    # Draw coupling beam as thick line (simplified visualization)
                    # For more precise visualization, would need actual start/end coordinates
                    fig.add_trace(go.Scatter(
                        x=[cb_x - cb_span/2, cb_x + cb_span/2],
                        y=[cb_y, cb_y],
                        mode='lines+markers',
                        line=dict(color='#F59E0B', width=8),
                        marker=dict(size=10, color='#F59E0B', symbol='square'),
                        name='Coupling Beam',
                        showlegend=first_coupling,
                        hovertemplate=(
                            f"Coupling Beam<br>"
                            f"Span: {cb.clear_span:.0f}mm<br>"
                            f"Depth: {cb.depth:.0f}mm<br>"
                            f"Width: {cb.width:.0f}mm<br>"
                            f"L/h: {cb.span_to_depth_ratio:.2f}<br>"
                            f"Deep Beam: {'Yes' if cb.is_deep_beam else 'No'}"
                            f"<extra></extra>"
                        )
                    ))
                    first_coupling = False

        # Beam trimming visualization (if core geometry available)
        if project.lateral.core_geometry:
            try:
                # Create beam geometries from framing grid
                beam_geometries = create_beam_geometries_from_project(project, cx, cy)

                # Initialize beam trimmer with offset core geometry
                # Note: BeamTrimmer works in mm, so we need to adjust coordinates
                trimmer = BeamTrimmer(project.lateral.core_geometry)

                # Trim beams
                trimmed_beams = trimmer.trim_multiple_beams(beam_geometries)

                # Visualize trimmed beams and connection types
                connection_symbols = []
                connection_x = []
                connection_y = []
                connection_types = []
                connection_labels = []

                for tb in trimmed_beams:
                    if tb.trimmed_start or tb.trimmed_end:
                        # Add connection indicators at trimmed ends
                        if tb.trimmed_start:
                            # Convert from mm to m and apply offset
                            x_m = cx + (tb.trimmed_geometry.start_x / 1000)
                            y_m = cy + (tb.trimmed_geometry.start_y / 1000)
                            connection_x.append(x_m)
                            connection_y.append(y_m)
                            connection_types.append(tb.start_connection.value)
                            connection_labels.append(
                                f"Trimmed Start<br>"
                                f"Connection: {tb.start_connection.value.upper()}<br>"
                                f"Original Length: {tb.original_length:.0f}mm<br>"
                                f"Trimmed Length: {tb.trimmed_length:.0f}mm"
                            )

                        if tb.trimmed_end:
                            # Convert from mm to m and apply offset
                            x_m = cx + (tb.trimmed_geometry.end_x / 1000)
                            y_m = cy + (tb.trimmed_geometry.end_y / 1000)
                            connection_x.append(x_m)
                            connection_y.append(y_m)
                            connection_types.append(tb.end_connection.value)
                            connection_labels.append(
                                f"Trimmed End<br>"
                                f"Connection: {tb.end_connection.value.upper()}<br>"
                                f"Original Length: {tb.original_length:.0f}mm<br>"
                                f"Trimmed Length: {tb.trimmed_length:.0f}mm"
                            )

                # Add connection type indicators
                if connection_x:
                    # Color code by connection type
                    connection_colors = []
                    connection_symbols_list = []
                    for ct in connection_types:
                        if ct == 'moment':
                            connection_colors.append('#EF4444')  # Red for moment
                            connection_symbols_list.append('diamond')
                        elif ct == 'fixed':
                            connection_colors.append('#7C3AED')  # Purple for fixed
                            connection_symbols_list.append('square')
                        else:  # pinned
                            connection_colors.append('#10B981')  # Green for pinned
                            connection_symbols_list.append('circle')

                    fig.add_trace(go.Scatter(
                        x=connection_x,
                        y=connection_y,
                        mode='markers',
                        marker=dict(
                            size=12,
                            color=connection_colors,
                            symbol=connection_symbols_list,
                            line=dict(width=2, color='white')
                        ),
                        name='Beam Connection',
                        text=connection_labels,
                        hovertemplate='%{text}<extra></extra>'
                    ))
            except Exception as e:
                # Silently skip if beam trimming fails (optional feature)
                pass

    # Layout
    title_text = f"Framing Plan ({num_bays_x}×{num_bays_y} bays)" if num_bays_x > 1 or num_bays_y > 1 else "Framing Plan (Single Bay)"
    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=16, color="#1E3A5F")
        ),
        xaxis=dict(
            title=dict(text="X (m)", standoff=25),
            range=[-1, total_x + 1],
            scaleanchor="y",
            constrain="domain"
        ),
        yaxis=dict(
            title="Y (m)",
            range=[-1, total_y + 1],
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        height=450,
        margin=dict(l=40, r=40, t=60, b=100)
    )

    return fig


def build_preview_utilization_map(model: FEMModel, project: ProjectData) -> Dict[int, float]:
    """Build approximate utilization map for FEM preview using preliminary design results."""
    utilization_map: Dict[int, float] = {}
    tolerance = 0.01
    primary_along_x = project.geometry.bay_x >= project.geometry.bay_y

    pri_util = project.primary_beam_result.utilization if project.primary_beam_result else 0.0
    sec_util = project.secondary_beam_result.utilization if project.secondary_beam_result else 0.0
    col_util = project.column_result.utilization if project.column_result else 0.0

    for elem in model.elements.values():
        if len(elem.node_tags) < 2:
            continue
        node_i = model.nodes[elem.node_tags[0]]
        node_j = model.nodes[elem.node_tags[1]]

        is_vertical = (abs(node_i.z - node_j.z) > tolerance and
                       abs(node_i.x - node_j.x) < tolerance and
                       abs(node_i.y - node_j.y) < tolerance)
        if is_vertical:
            utilization_map[elem.tag] = col_util
            continue

        is_horizontal = abs(node_i.z - node_j.z) < tolerance
        if is_horizontal:
            along_x = abs(node_i.y - node_j.y) < tolerance
            if primary_along_x:
                utilization_map[elem.tag] = pri_util if along_x else sec_util
            else:
                utilization_map[elem.tag] = sec_util if along_x else pri_util

    return utilization_map


def _analysis_result_to_displacements(result) -> Dict[int, Tuple[float, float, float]]:
    """Extract translational displacements from AnalysisResult."""
    displaced: Dict[int, Tuple[float, float, float]] = {}
    for node_tag, values in result.node_displacements.items():
        if len(values) >= 3:
            displaced[node_tag] = (values[0], values[1], values[2])
    return displaced


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

    # Add wind label (positioned further left to avoid arrows)
    fig.add_annotation(
        x=-7,
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
            range=[-10, width + 5],  # Expanded range for wind label
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


def run_calculations(project: ProjectData,
                     override_slab: int = 0,
                     override_pri_beam_w: int = 0,
                     override_pri_beam_d: int = 0,
                     override_sec_beam_w: int = 0,
                     override_sec_beam_d: int = 0,
                     override_col: int = 0,
                     secondary_along_x: bool = False,
                     num_secondary_beams: int = 3) -> ProjectData:
    """DEPRECATED IN V3.5: Run all structural calculations with optional overrides
    
    This function is deprecated as part of the FEM-only architecture.
    Use FEM analysis workflow instead of simplified calculations.
    """
    raise DeprecationWarning(
        "run_calculations() is deprecated in v3.5. "
        "Use FEM analysis workflow instead of simplified calculation engines. "
        "run_calculations() is deprecated in v3.5. "
        "Use FEM analysis workflow instead of simplified calculation engines. "
        "Engines (SlabEngine, BeamEngine, ColumnEngine, WindEngine) have been removed."
    )


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
        
        inputs_locked = _is_inputs_locked()
        if inputs_locked:
            st.warning("🔒 **Inputs locked** - Analysis results active. Click 'Unlock to Modify' in FEM section to change inputs.")

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
                                   value=float(st.session_state.project.geometry.bay_x), step=0.5,
                                   disabled=inputs_locked)
        with col2:
            bay_y = st.number_input("Bay Y (m)", min_value=3.0, max_value=15.0,
                                   value=float(st.session_state.project.geometry.bay_y), step=0.5,
                                   disabled=inputs_locked)

        col1, col2 = st.columns(2)
        with col1:
            num_bays_x = st.number_input("Bays in X", min_value=1, max_value=10,
                                        value=st.session_state.project.geometry.num_bays_x, step=1,
                                        help="Number of bays in X direction",
                                        disabled=inputs_locked)
        with col2:
            num_bays_y = st.number_input("Bays in Y", min_value=1, max_value=10,
                                        value=st.session_state.project.geometry.num_bays_y, step=1,
                                        help="Number of bays in Y direction",
                                        disabled=inputs_locked)

        col1, col2 = st.columns(2)
        with col1:
            floors = st.number_input("Floors", min_value=1, max_value=50,
                                    value=st.session_state.project.geometry.floors, step=1,
                                    disabled=inputs_locked)
        with col2:
            story_height = st.number_input("Story Height (m)", min_value=2.5, max_value=6.0,
                                          value=float(st.session_state.project.geometry.story_height), step=0.1,
                                          disabled=inputs_locked)

        st.divider()

        # Loading Inputs
        st.markdown("##### Loading")

        # Live load class selection - include "9: Other (Custom)" option
        class_options = [(k, v["name"]) for k, v in LIVE_LOAD_TABLE.items()]
        class_options.append(("9", "Other (Custom)"))  # Add custom option as Class 9
        class_labels = [f"{k}: {name}" for k, name in class_options]
        class_keys = [k for k, _ in class_options]

        # Get current class, default to "2" if not in valid options
        current_class = st.session_state.project.loads.live_load_class
        if current_class in class_keys:
            default_class_idx = class_keys.index(current_class)
        else:
            default_class_idx = class_keys.index("2") if "2" in class_keys else 0

        selected_class_label = st.selectbox(
            "Live Load Class",
            options=class_labels,
            index=default_class_idx
        )
        selected_class = class_keys[class_labels.index(selected_class_label)]

        # Custom live load input when "9: Other (Custom)" is selected
        custom_live_load_value: Optional[float] = None
        if selected_class == "9":
            # Show custom kPa input with validation (0.5 - 20.0 kPa)
            current_custom = st.session_state.project.loads.custom_live_load
            default_custom = current_custom if current_custom is not None else 5.0
            custom_live_load_value = st.number_input(
                "Custom Live Load (kPa)",
                min_value=0.5,
                max_value=20.0,
                value=float(default_custom),
                step=0.5,
                help="Enter custom live load value (0.5 - 20.0 kPa) for special loading conditions"
            )
            selected_sub = "9.0"  # Placeholder subdivision for custom
        else:
            # Live load subdivision from HK Code tables
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

        current_exposure = st.session_state.project.materials.exposure
        try:
            current_index = list(exposure_options.keys()).index(current_exposure)
        except (ValueError, AttributeError):
            current_index = 1

        selected_exposure_label = st.selectbox(
            "Exposure Class",
            options=list(exposure_options.values()),
            index=current_index
        )
        selected_exposure = list(exposure_options.keys())[list(exposure_options.values()).index(selected_exposure_label)]

        st.divider()

        # Beam Configuration
        st.markdown("##### Beam Configuration")
        secondary_beam_dir = st.radio(
            "Secondary Beam Direction",
            options=["Along Y (default)", "Along X"],
            index=0,
            help="Direction of secondary beams (internal beams). Primary beams are on the perimeter.",
            key="secondary_beam_direction_radio",
            disabled=inputs_locked
        )
        secondary_along_x = secondary_beam_dir == "Along X"
        st.session_state["secondary_along_x"] = secondary_along_x

        num_secondary_beams = st.number_input(
            "Number of Secondary Beams",
            min_value=0, max_value=10, value=3, step=1,
            help="Number of internal secondary beams equally spaced within the bay (0 = no secondary beams)",
            key="num_secondary_beams",
            disabled=inputs_locked
        )

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
                              value=st.session_state.project.lateral.core_wall_config is not None)

        # Initialize core wall location variables with defaults
        selected_core_location = "Center"
        custom_x = None
        custom_y = None

        if has_core:
            # Core wall configuration dropdown
            config_options = {
                CoreWallConfig.I_SECTION: "I-Section (2 Walls Blended)",
                CoreWallConfig.TWO_C_FACING: "Two C-Walls Facing",
                CoreWallConfig.TWO_C_BACK_TO_BACK: "Two C-Walls Back-to-Back",
                CoreWallConfig.TUBE_CENTER_OPENING: "Tube with Center Opening",
                CoreWallConfig.TUBE_SIDE_OPENING: "Tube with Side Opening"
            }

            # Get current config or default to I_SECTION
            current_config = st.session_state.project.lateral.core_wall_config or CoreWallConfig.I_SECTION
            selected_config_label = st.selectbox(
                "Core Wall Configuration",
                options=list(config_options.values()),
                index=list(config_options.keys()).index(current_config),
                help="Select the core wall configuration type for FEM modeling"
            )
            selected_core_wall_config = list(config_options.keys())[list(config_options.values()).index(selected_config_label)]

            # Wall thickness input
            wall_thickness = st.number_input(
                "Wall Thickness (mm)",
                min_value=200, max_value=1000, value=500, step=50,
                help="Core wall thickness in millimeters (typical: 500mm)"
            )

            # Dimension inputs depend on configuration type
            if selected_core_wall_config in [CoreWallConfig.I_SECTION, CoreWallConfig.TWO_C_FACING, CoreWallConfig.TWO_C_BACK_TO_BACK]:
                st.caption("I-Section / C-Wall Dimensions")
                col1, col2 = st.columns(2)
                with col1:
                    flange_width = st.number_input(
                        "Flange Width (m)", min_value=2.0, max_value=15.0, value=6.0, step=0.5,
                        help="Width of horizontal flange"
                    )
                with col2:
                    web_length = st.number_input(
                        "Web Length (m)", min_value=2.0, max_value=20.0, value=8.0, step=0.5,
                        help="Length of vertical web"
                    )

                # For C-walls, add opening width
                if selected_core_wall_config in [CoreWallConfig.TWO_C_FACING, CoreWallConfig.TWO_C_BACK_TO_BACK]:
                    opening_width = st.number_input(
                        "Opening Width (m)", min_value=1.0, max_value=10.0, value=3.0, step=0.5,
                        help="Width of opening between/within C-walls"
                    )
                else:
                    opening_width = None

                # Set core_x and core_y from dimensions
                core_x = flange_width
                core_y = web_length
                length_x = flange_width
                length_y = web_length
                opening_height = None

                # Core Position UI (Task 17.2)
                st.caption("Core Position")
                col_loc1, col_loc2 = st.columns(2)
                with col_loc1:
                    core_loc_type = st.radio(
                        "Position Type",
                        options=["Center", "Custom"],
                        index=0,
                        horizontal=True,
                        help="Place core at building center or define specific coordinates. "
                             "Coordinate system: Origin (0,0) at bottom-left corner of building, "
                             "X increases to the right, Y increases upward.",
                        key="i_section_position_type"
                    )
                
                custom_x = None
                custom_y = None
                
                if core_loc_type == "Custom":
                    b_width = bay_x * num_bays_x
                    b_depth = bay_y * num_bays_y
                    
                    with col_loc2:
                        st.caption(f"Building: {b_width:.1f}m x {b_depth:.1f}m")
                    
                    # Coordinate system tooltip
                    st.info(
                        "**Coordinate System:** Origin (0, 0) is at the bottom-left corner. "
                        "X-axis runs left-to-right, Y-axis runs bottom-to-top."
                    )
                        
                    l_col, r_col = st.columns(2)
                    
                    # Calculate safe min/max to ensure core fits within building
                    # Use flange_width and web_length for I-Section/C-Wall
                    half_core_x = flange_width / 2.0
                    half_core_y = web_length / 2.0
                    min_x = half_core_x
                    max_x = b_width - half_core_x
                    min_y = half_core_y
                    max_y = b_depth - half_core_y
                    
                    # Clamp to ensure valid range
                    min_x = max(0.0, min_x)
                    max_x = max(min_x + 0.1, max_x)
                    min_y = max(0.0, min_y)
                    max_y = max(min_y + 0.1, max_y)
                    
                    with l_col:
                        custom_x = st.number_input(
                            "Center X (m)", 
                            min_value=0.0, 
                            max_value=float(b_width), 
                            value=float(b_width/2), 
                            step=1.0,
                            help=f"X-coordinate of the core wall centroid (valid range: {min_x:.1f}m - {max_x:.1f}m)"
                        )
                    with r_col:
                        custom_y = st.number_input(
                            "Center Y (m)", 
                            min_value=0.0, 
                            max_value=float(b_depth), 
                            value=float(b_depth/2), 
                            step=1.0,
                            help=f"Y-coordinate of the core wall centroid (valid range: {min_y:.1f}m - {max_y:.1f}m)"
                        )
                    
                    # Validation warning for edge cases
                    if custom_x < min_x or custom_x > max_x:
                        st.warning(f"Core wall may extend outside building in X direction. "
                                   f"Recommended X range: {min_x:.1f}m - {max_x:.1f}m")
                    if custom_y < min_y or custom_y > max_y:
                        st.warning(f"Core wall may extend outside building in Y direction. "
                                   f"Recommended Y range: {min_y:.1f}m - {max_y:.1f}m")
                        
                    selected_core_location = "Custom"
                else:
                    selected_core_location = "Center"

            else:  # TUBE configurations
                st.caption("Tube Dimensions")
                col1, col2 = st.columns(2)
                with col1:
                    length_x = st.number_input(
                        "Length X (m)", min_value=2.0, max_value=15.0, value=6.0, step=0.5,
                        help="Outer dimension in X direction"
                    )
                with col2:
                    length_y = st.number_input(
                        "Length Y (m)", min_value=2.0, max_value=15.0, value=6.0, step=0.5,
                        help="Outer dimension in Y direction"
                    )

                st.caption("Opening Dimensions")
                col1, col2 = st.columns(2)
                with col1:
                    opening_width = st.number_input(
                        "Opening Width (m)", min_value=0.5, max_value=5.0, value=2.0, step=0.5,
                        help="Width of opening"
                    )
                with col2:
                    opening_height = st.number_input(
                        "Opening Height (m)", min_value=0.5, max_value=5.0, value=2.0, step=0.5,
                        help="Height of opening"
                    )

                # Set core_x and core_y from tube dimensions
                core_x = length_x
                core_y = length_y
                flange_width = None
                web_length = None

                # Core Position UI for TUBE configurations (Task 17.2)
                st.caption("Core Position")
                col_loc1, col_loc2 = st.columns(2)
                with col_loc1:
                    core_loc_type = st.radio(
                        "Position Type",
                        options=["Center", "Custom"],
                        index=0,
                        horizontal=True,
                        help="Place core at building center or define specific coordinates. "
                             "Coordinate system: Origin (0,0) at bottom-left corner of building, "
                             "X increases to the right, Y increases upward.",
                        key="tube_position_type"
                    )
                
                custom_x = None
                custom_y = None
                
                if core_loc_type == "Custom":
                    b_width = bay_x * num_bays_x
                    b_depth = bay_y * num_bays_y
                    
                    with col_loc2:
                        st.caption(f"Building: {b_width:.1f}m x {b_depth:.1f}m")
                    
                    # Coordinate system tooltip
                    st.info(
                        "**Coordinate System:** Origin (0, 0) is at the bottom-left corner. "
                        "X-axis runs left-to-right, Y-axis runs bottom-to-top."
                    )
                        
                    l_col, r_col = st.columns(2)
                    
                    # Calculate safe min/max to ensure core fits within building
                    half_core_x = length_x / 2.0
                    half_core_y = length_y / 2.0
                    min_x = half_core_x
                    max_x = b_width - half_core_x
                    min_y = half_core_y
                    max_y = b_depth - half_core_y
                    
                    # Clamp to ensure valid range
                    min_x = max(0.0, min_x)
                    max_x = max(min_x + 0.1, max_x)
                    min_y = max(0.0, min_y)
                    max_y = max(min_y + 0.1, max_y)
                    
                    with l_col:
                        custom_x = st.number_input(
                            "Center X (m)", 
                            min_value=0.0, 
                            max_value=float(b_width), 
                            value=float(b_width/2), 
                            step=1.0,
                            help=f"X-coordinate of the core wall centroid (valid range: {min_x:.1f}m - {max_x:.1f}m)"
                        )
                    with r_col:
                        custom_y = st.number_input(
                            "Center Y (m)", 
                            min_value=0.0, 
                            max_value=float(b_depth), 
                            value=float(b_depth/2), 
                            step=1.0,
                            help=f"Y-coordinate of the core wall centroid (valid range: {min_y:.1f}m - {max_y:.1f}m)"
                        )
                    
                    # Validation warning for edge cases
                    if custom_x < min_x or custom_x > max_x:
                        st.warning(f"Core wall may extend outside building in X direction. "
                                   f"Recommended X range: {min_x:.1f}m - {max_x:.1f}m")
                    if custom_y < min_y or custom_y > max_y:
                        st.warning(f"Core wall may extend outside building in Y direction. "
                                   f"Recommended Y range: {min_y:.1f}m - {max_y:.1f}m")
                        
                    selected_core_location = "Custom"
                else:
                    selected_core_location = "Center"
            
            # Calculate and display section properties
            st.caption("Calculated Section Properties")
            temp_geometry = CoreWallGeometry(
                config=selected_core_wall_config,
                wall_thickness=wall_thickness,
                length_x=length_x * 1000 if length_x else 6000.0,
                length_y=length_y * 1000 if length_y else 6000.0,
                opening_width=opening_width * 1000 if opening_width else None,
                opening_height=opening_height * 1000 if opening_height else None,
                flange_width=flange_width * 1000 if flange_width else None,
                web_length=web_length * 1000 if web_length else None,
            )

            section_props = calculate_core_wall_properties(temp_geometry)

            if section_props:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Area", f"{section_props.A / 1e6:.2f} m²", help="Cross-sectional area")
                    st.metric("Ixx", f"{section_props.I_xx / 1e12:.2f} m⁴", help="Moment of inertia about X-axis")
                    st.metric("Iyy", f"{section_props.I_yy / 1e12:.2f} m⁴", help="Moment of inertia about Y-axis")
                with col2:
                    st.metric("Centroid X", f"{section_props.centroid_x / 1000:.2f} m", help="Centroid X-coordinate")
                    st.metric("Centroid Y", f"{section_props.centroid_y / 1000:.2f} m", help="Centroid Y-coordinate")
                    st.metric("J", f"{section_props.J / 1e12:.3f} m⁴", help="Torsional constant")

                if abs(section_props.I_xy) > 1e6:  # Show only if non-negligible
                    st.metric("Ixy", f"{section_props.I_xy / 1e12:.3f} m⁴", help="Product of inertia (asymmetric sections)")
        else:
            core_x = 0.0
            core_y = 0.0
            selected_core_location = "Center"
            selected_core_wall_config = None
            wall_thickness = 500.0
            flange_width = None
            web_length = None
            length_x = None
            length_y = None
            opening_width = None
            opening_height = None
            custom_x = None
            custom_y = None

        # Column Omission Suggestion Review (Task 17.3)
        if has_core and selected_core_wall_config:
            # We need to temporarily update project geometry/lateral for the suggestion function to work
            # logic is similar to lines 1346-1380 but we need it here for the UI
            
            # Create a localized project definition for calculation
            # (Standard project update happens at end of sidebar, so we use session state or temp obj)
            
            # Simple approach: Check if we have enough info to run suggestion
            st.divider()
            with st.expander("🔍 Column Omission Review", expanded=False):
                st.info("Columns within 0.5m of core walls can be omitted to avoid conflicts.")
                
                # We need a temporary project object with CURRENT inputs for the checker
                # Reusing existing project structure but updating lateral/geometry locally
                temp_project = ProjectData()  # Copy or new
                # Copy essential data from session state
                temp_project.geometry = GeometryInput(bay_x, bay_y, floors, story_height, num_bays_x, num_bays_y)
                
                temp_core_geo = CoreWallGeometry(
                    config=selected_core_wall_config,
                    wall_thickness=wall_thickness,
                    length_x=length_x * 1000 if length_x else 6000.0,
                    length_y=length_y * 1000 if length_y else 6000.0,
                    opening_width=opening_width * 1000 if opening_width else None,
                    opening_height=opening_height * 1000 if opening_height else None,
                    flange_width=flange_width * 1000 if flange_width else None,
                    web_length=web_length * 1000 if web_length else None,
                )
                
                # We need the calculated centroid to position the core correctly in the checker
                # The checker uses project.lateral.core_geometry
                temp_project.lateral = LateralInput(
                    terrain=selected_terrain, # Not used for omission
                    building_width=bay_x * num_bays_x,
                    building_depth=bay_y * num_bays_y,
                    core_wall_config=selected_core_wall_config,
                    wall_thickness=wall_thickness,
                    core_geometry=temp_core_geo
                )
                
                # Get suggestions
                try:
                    suggestions = get_column_omission_suggestions(
                        project=temp_project,
                        threshold_m=0.5
                    )
                    
                    if suggestions:
                        st.write(f"**{len(suggestions)} columns suggested for omission:**")
                        
                        # Initialize session state for omissions if not exists
                        # We use a set of approved omissions
                        if "omit_columns" not in st.session_state:
                            st.session_state.omit_columns = {col_id: True for col_id in suggestions}
                        else:
                            # Add new suggestions as True, keep existing preference
                            for col_id in suggestions:
                                if col_id not in st.session_state.omit_columns:
                                    st.session_state.omit_columns[col_id] = True
                                    
                        # Display checkboxes
                        cols = st.columns(3)
                        approved_count = 0
                        for i, col_id in enumerate(sorted(suggestions)):
                            col_idx = i % 3
                            is_checked = st.session_state.omit_columns.get(col_id, True)
                            with cols[col_idx]:
                                new_val = st.checkbox(f"{col_id}", value=is_checked, key=f"omit_chk_{col_id}")
                                st.session_state.omit_columns[col_id] = new_val
                                if new_val:
                                    approved_count += 1
                        
                        st.caption(f"✅ {approved_count} columns set to be omitted.")
                    else:
                        st.success("No columns detected near core wall.")
                        
                except Exception as e:
                    st.error(f"Could not calculate omissions: {str(e)}")


        st.divider()

        # Element Overrides (Advanced)
        st.markdown("##### Element Overrides")
        use_overrides = st.checkbox("Override calculated sizes", value=False,
                                   help="Enable manual override of structural element sizes")

        if use_overrides:
            st.caption("Leave at 0 to use calculated values")
            override_slab_thickness = st.number_input(
                "Slab Thickness (mm)", min_value=0, value=0, step=25,
                help="Override slab thickness (0 = auto)")

            st.caption("Primary Beam")
            col1, col2 = st.columns(2)
            with col1:
                override_pri_beam_width = st.number_input(
                    "Pri. Width (mm)", min_value=0, value=0, step=25,
                    help="Primary beam width (0 = auto)")
            with col2:
                override_pri_beam_depth = st.number_input(
                    "Pri. Depth (mm)", min_value=0, value=0, step=50,
                    help="Primary beam depth (0 = auto)")

            st.caption("Secondary Beam")
            col1, col2 = st.columns(2)
            with col1:
                override_sec_beam_width = st.number_input(
                    "Sec. Width (mm)", min_value=0, value=0, step=25,
                    help="Secondary beam width (0 = auto)")
            with col2:
                override_sec_beam_depth = st.number_input(
                    "Sec. Depth (mm)", min_value=0, value=0, step=50,
                    help="Secondary beam depth (0 = auto)")

            override_column_size = st.number_input(
                "Column Size (mm)", min_value=0, value=0, step=25,
                help="Override column dimension (0 = auto)")
        else:
            override_slab_thickness = 0
            override_pri_beam_width = 0
            override_pri_beam_depth = 0
            override_sec_beam_width = 0
            override_sec_beam_depth = 0
            override_column_size = 0

        st.divider()

        # ===== LOAD COMBINATION UI (Task 20.3) =====
        st.markdown("##### Load Combinations")
        
        # Initialize session state for load combination selections if not exists
        if "selected_combinations" not in st.session_state:
            # Default: select LC1 (gravity) and SLS1
            st.session_state.selected_combinations = {"LC1", "SLS1"}
        
        # Get all available combinations from library
        all_combinations = LoadCombinationLibrary.get_all_combinations()
        
        # Group combinations by category
        gravity_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.ULS_GRAVITY]
        wind_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.ULS_WIND]
        seismic_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.ULS_SEISMIC]
        accidental_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.ULS_ACCIDENTAL]
        sls_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.SLS]
        
        # Helper function to render category section
        def render_combo_category(
            category_name: str,
            combos: list,
            category_key: str,
            expanded: bool = False
        ) -> int:
            """Render a collapsible category section with checkboxes.
            
            Returns the count of selected combinations in this category.
            """
            if not combos:
                return 0
            
            selected_count = sum(1 for c in combos if c.name in st.session_state.selected_combinations)
            total_count = len(combos)
            
            with st.expander(f"{category_name} ({selected_count}/{total_count})", expanded=expanded):
                # Select All / Select None buttons
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
                with btn_col1:
                    if st.button("All", key=f"select_all_{category_key}", use_container_width=True):
                        for c in combos:
                            st.session_state.selected_combinations.add(c.name)
                        st.rerun()
                with btn_col2:
                    if st.button("None", key=f"select_none_{category_key}", use_container_width=True):
                        for c in combos:
                            st.session_state.selected_combinations.discard(c.name)
                        st.rerun()
                
                # Scrollable container for combinations (using container with max height)
                # For wind combos (many), display in 3 columns; others in 2 columns
                if len(combos) > 10:
                    combo_container = st.container(height=300)
                else:
                    combo_container = st.container()
                
                with combo_container:
                    if len(combos) > 10:
                        # Wind combos - use 3 columns for compact display
                        cols = st.columns(3)
                        for i, combo in enumerate(combos):
                            col_idx = i % 3
                            with cols[col_idx]:
                                is_selected = combo.name in st.session_state.selected_combinations
                                # Shorter label for wind combos
                                label = f"{combo.name}"
                                if st.checkbox(label, value=is_selected, key=f"combo_{combo.name}", 
                                              help=combo.to_equation()):
                                    st.session_state.selected_combinations.add(combo.name)
                                else:
                                    st.session_state.selected_combinations.discard(combo.name)
                    else:
                        # Other categories - use 2 columns
                        cols = st.columns(2) if len(combos) > 1 else st.columns(1)
                        for i, combo in enumerate(combos):
                            col_idx = i % len(cols)
                            with cols[col_idx]:
                                is_selected = combo.name in st.session_state.selected_combinations
                                label = f"{combo.name}: {combo.to_equation()}"
                                if st.checkbox(label, value=is_selected, key=f"combo_{combo.name}",
                                              help=combo.description):
                                    st.session_state.selected_combinations.add(combo.name)
                                else:
                                    st.session_state.selected_combinations.discard(combo.name)
            
            return selected_count
        
        # Render each category
        gravity_selected = render_combo_category("Gravity (ULS)", gravity_combos, "gravity", expanded=True)
        wind_selected = render_combo_category("Wind (ULS)", wind_combos, "wind", expanded=False)
        seismic_selected = render_combo_category("Seismic (ULS)", seismic_combos, "seismic", expanded=False)
        accidental_selected = render_combo_category("Accidental (ULS)", accidental_combos, "accidental", expanded=False)
        sls_selected = render_combo_category("Serviceability (SLS)", sls_combos, "sls", expanded=True)
        
        # Total count display
        total_selected = len(st.session_state.selected_combinations)
        total_available = len(all_combinations)
        st.caption(f"**Total: {total_selected}/{total_available} combinations selected**")
        
        # Active combination for simplified design (backwards compatibility)
        # Use the first selected gravity combo, or first selected combo
        active_combo_options = {}
        for c in all_combinations:
            if c.name in st.session_state.selected_combinations:
                active_combo_options[c.combination_type] = f"{c.name}: {c.to_equation()}"
        
        if active_combo_options:
            st.markdown("**Active Combination for Design:**")
            selected_comb_label = st.selectbox(
                "Active Combination",
                options=list(active_combo_options.values()),
                index=0,
                label_visibility="collapsed",
                help="This combination is used for the simplified design calculations"
            )
            # Find the LoadCombination enum for the selected label
            selected_load_comb = list(active_combo_options.keys())[
                list(active_combo_options.values()).index(selected_comb_label)
            ]
        else:
            # Fallback to default if nothing selected
            selected_load_comb = LoadCombination.ULS_GRAVITY_1
            selected_comb_label = "LC1: 1.4DL + 1.4SDL + 1.6LL"
            st.warning("No combinations selected. Using default ULS Gravity combination.")

    # Update project data
    project = st.session_state.project
    project.geometry = GeometryInput(bay_x, bay_y, floors, story_height, num_bays_x, num_bays_y)
    project.loads = LoadInput(selected_class, selected_sub, dead_load, custom_live_load=custom_live_load_value)
    project.materials = MaterialInput(fcu_slab, fcu_beam, fcu_column, exposure=selected_exposure)
    # Use total building dimensions for lateral analysis
    total_width_x = bay_x * num_bays_x
    total_width_y = bay_y * num_bays_y

    # Create CoreWallGeometry if core wall system is enabled
    core_geometry = None
    section_properties = None
    if has_core and selected_core_wall_config:
        core_geometry = CoreWallGeometry(
            config=selected_core_wall_config,
            wall_thickness=wall_thickness,
            length_x=length_x * 1000 if length_x else 6000.0,
            length_y=length_y * 1000 if length_y else 6000.0,
            opening_width=opening_width * 1000 if opening_width else None,
            opening_height=opening_height * 1000 if opening_height else None,
            flange_width=flange_width * 1000 if flange_width else None,
            web_length=web_length * 1000 if web_length else None,
        )

        # Calculate section properties
        section_properties = calculate_core_wall_properties(core_geometry)

    project.lateral = LateralInput(
        terrain=selected_terrain,
        building_width=total_width_x,
        building_depth=total_width_y,
        core_wall_config=selected_core_wall_config if has_core else None,
        wall_thickness=wall_thickness,
        core_geometry=core_geometry,
        section_properties=section_properties,
        # Task 17.2: Pass custom core wall position
        location_type=selected_core_location if has_core else "Center",
        custom_center_x=custom_x if has_core and selected_core_location == "Custom" else None,
        custom_center_y=custom_y if has_core and selected_core_location == "Custom" else None,
    )
    project.load_combination = selected_load_comb

    # Run calculations with optional overrides
    project = run_calculations(
        project,
        override_slab=override_slab_thickness,
        override_pri_beam_w=override_pri_beam_width,
        override_pri_beam_d=override_pri_beam_depth,
        override_sec_beam_w=override_sec_beam_width,
        override_sec_beam_d=override_sec_beam_depth,
        override_col=override_column_size,
        secondary_along_x=secondary_along_x,
        num_secondary_beams=num_secondary_beams
    )
    st.session_state.project = project

    # ===== MAIN CONTENT =====

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

    # FEM Analysis & Preview
    st.markdown("### FEM Analysis")
    st.caption("Preview the FEM model and optionally overlay OpenSees analysis results.")

    try:
        render_unified_fem_views(
            project=project,
            analysis_result=st.session_state.get('fem_preview_analysis_result'),
            config_overrides={}
        )
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
                if project.secondary_beam_result:
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
                else:
                    st.info("No secondary beams defined")

            if project.primary_beam_result.is_deep_beam or (project.secondary_beam_result and project.secondary_beam_result.is_deep_beam):
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
