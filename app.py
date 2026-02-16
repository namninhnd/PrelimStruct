"""
PrelimStruct - Streamlit Dashboard
AI-Assisted Preliminary Structural Design Platform
"""

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

# Import core modules
from src.core.data_models import (
    ProjectData, GeometryInput, LoadInput, MaterialInput, LateralInput,
    SlabDesignInput, BeamDesignInput, ReinforcementInput,
    ExposureClass, TerrainCategory,
    CoreWallConfig, CoreWallGeometry, CoreWallSectionProperties,
    CoreLocationPreset, TubeOpeningPlacement,
    ColumnPosition, LoadCombination, WindResult,
    SlabResult, BeamResult, ColumnResult,
)
from src.core.constants import CARBON_FACTORS, CONCRETE_DENSITY
from src.core.load_tables import LIVE_LOAD_TABLE

# V3.5: Engine imports removed - FEM-only architecture
# from src.engines.slab_engine import SlabEngine
# from src.engines.beam_engine import BeamEngine
# from src.engines.column_engine import ColumnEngine
# from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine

# Import FEM modules (may fail on cloud if openseespy native libs unavailable)
try:
    from src.fem.core_wall_geometry import (
        ISectionCoreWall,
        TubeWithOpeningsCoreWall,
    )
    from src.fem.coupling_beam import CouplingBeamGenerator
    from src.fem.beam_trimmer import BeamTrimmer, BeamGeometry, BeamConnectionType
    from src.fem.fem_engine import FEMModel
    from src.fem.wind_calculator import calculate_hk_wind
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
    FEM_AVAILABLE = True
except ImportError:
    FEM_AVAILABLE = False
    logging.warning("FEM modules unavailable — openseespy native libraries not found")
from src.ui.components.core_wall_selector import render_core_wall_selector
from src.ui.wind_details import (
    build_wind_details_dataframe,
    build_wind_details_summary,
    has_complete_floor_wind_data,
)
from src.ui.utils import format_column_size_mm

# Import report generator
from src.report.report_generator import ReportGenerator


logger = logging.getLogger(__name__)


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
    /* Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;700&family=Lexend:wght@400;600;700&display=swap');

    :root {
        /* Colors */
        --primary-blue: #1E3A5F;
        --primary-blue-dark: #152943;
        --accent-orange: #F59E0B;
        --accent-orange-hover: #D97706;
        --neutral-50: #F8FAFC;
        --neutral-100: #F1F5F9;
        --neutral-200: #E2E8F0;
        --neutral-300: #CBD5E1;
        --neutral-400: #94A3B8;
        --neutral-500: #64748B;
        --neutral-800: #1E293B;
        --neutral-900: #0F172A;

        /* Spacing */
        --space-4: 4px;
        --space-8: 8px;
        --space-12: 12px;
        --space-16: 16px;
        --space-24: 24px;
        --space-32: 32px;
        --space-64: 64px;
    }

    /* Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: var(--neutral-800);
    }

    h1, h2, h3, .section-header {
        font-family: 'Lexend', sans-serif;
        color: var(--primary-blue);
        font-weight: 700;
    }
    
    h1 { font-size: 32px; }
    h2 { font-size: 24px; }
    h3 { font-size: 20px; }

    code, .metric-value {
        font-family: 'JetBrains Mono', monospace;
    }

    /* Layout adjustments */
    .block-container {
        padding-top: var(--space-32);
        padding-bottom: var(--space-64);
        max-width: 1200px;
    }

    /* Status Badge Styles */
    .status-pass {
        background-color: #10B981;
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
        font-family: 'Inter', sans-serif;
    }
    .status-fail {
        background-color: #EF4444;
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
        font-family: 'Inter', sans-serif;
    }
    .status-warning {
        background-color: var(--accent-orange);
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
        font-family: 'Inter', sans-serif;
    }
    .status-pending {
        background-color: var(--neutral-500);
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
        font-family: 'Inter', sans-serif;
    }

    /* Metric Card */
    .metric-card {
        background: white;
        border: 1px solid var(--neutral-200);
        border-radius: 8px;
        padding: var(--space-16);
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: var(--space-8);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--primary-blue);
        margin: 0;
    }
    .metric-label {
        font-size: 14px;
        color: var(--neutral-500);
        margin: 0;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Section Headers */
    .section-header {
        color: var(--primary-blue);
        font-weight: 700;
        border-bottom: 2px solid var(--neutral-200);
        padding-bottom: var(--space-8);
        margin-bottom: var(--space-16);
        margin-top: var(--space-32);
    }

    /* Element Summary Cards */
    .element-card {
        background: var(--neutral-50);
        border: 1px solid var(--neutral-200);
        border-radius: 8px;
        padding: var(--space-12);
        margin-bottom: var(--space-8);
    }
    .element-card strong {
        color: var(--primary-blue);
        font-size: 15px;
        font-family: 'Lexend', sans-serif;
    }
    .element-card small {
        color: var(--neutral-500);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: var(--neutral-50);
        border-right: 1px solid var(--neutral-200);
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: var(--primary-blue);
    }

    /* Button Styling */
    div.stButton > button {
        background-color: var(--primary-blue);
        color: white;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: var(--primary-blue-dark);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-blue-dark);
    }
    div.stButton > button:focus {
        box-shadow: 0 0 0 2px var(--neutral-200), 0 0 0 4px var(--primary-blue);
        border-color: var(--primary-blue);
    }
    div.stButton > button:active {
        background-color: var(--primary-blue-dark);
    }
    
    /* Inputs */
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input, 
    .stSelectbox > div > div {
        border-radius: 6px;
        border-color: var(--neutral-200);
        font-family: 'Inter', sans-serif;
    }
    .stTextInput > div > div > input:focus, 
    .stNumberInput > div > div > input:focus, 
    .stSelectbox > div > div:focus-within {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 1px var(--primary-blue);
    }
    
    /* Remove purple from sliders/checks if possible */
    .stCheckbox span[role="checkbox"][aria-checked="true"] {
        background-color: var(--primary-blue) !important;
        border-color: var(--primary-blue) !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Mobile viewport handling (<768px) */
    @media (max-width: 768px) {
        /* Collapse sidebar by default on mobile to prevent content overlay */
        [data-testid="stSidebar"] {
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
        }
        
        /* Ensure main content uses full width when sidebar collapsed */
        .main .block-container {
            max-width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Mobile warning banner */
        .mobile-warning {
            background: #FFF3CD;
            border: 2px solid #F59E0B;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 16px;
            color: #856404;
            font-size: 14px;
        }
    }
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
        elif geometry.config == CoreWallConfig.TUBE_WITH_OPENINGS:
            core_wall = TubeWithOpeningsCoreWall(geometry)
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
        elif geometry.config == CoreWallConfig.TUBE_WITH_OPENINGS:
            core_wall = TubeWithOpeningsCoreWall(geometry)
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
                            connection_colors.append('#334155')  # Dark Slate for fixed
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
                     override_col_w: int = 0,
                     override_col_d: int = 0,
                     secondary_along_x: bool = False,
                     num_secondary_beams: int = 3) -> ProjectData:
    """Apply section-property updates in FEM-only mode.

    In v3.5, simplified design engines are removed. This function now updates
    section properties on project results so FEM model generation reflects
    sidebar edits immediately.
    """
    _ = secondary_along_x
    _ = num_secondary_beams

    def _resolve_dimension(override_value: int, fallback: int) -> int:
        if override_value and override_value > 0:
            return int(override_value)
        return int(fallback)

    # Slab thickness (affects DL self-weight)
    if override_slab and override_slab > 0:
        slab_thickness = int(override_slab)
        slab_self_weight = (slab_thickness / 1000.0) * CONCRETE_DENSITY
        if project.slab_result is not None:
            project.slab_result.thickness = slab_thickness
            project.slab_result.self_weight = slab_self_weight
            project.slab_result.size = f"{slab_thickness} mm"
        else:
            project.slab_result = SlabResult(
                element_type="Slab",
                size=f"{slab_thickness} mm",
                thickness=slab_thickness,
                self_weight=slab_self_weight,
            )

    # Primary beam section
    if (override_pri_beam_w and override_pri_beam_w > 0) or (override_pri_beam_d and override_pri_beam_d > 0):
        existing_w = project.primary_beam_result.width if project.primary_beam_result else 300
        existing_d = project.primary_beam_result.depth if project.primary_beam_result else 600
        width = _resolve_dimension(override_pri_beam_w, existing_w)
        depth = _resolve_dimension(override_pri_beam_d, existing_d)

        if project.primary_beam_result is not None:
            project.primary_beam_result.width = width
            project.primary_beam_result.depth = depth
            project.primary_beam_result.size = f"{width} x {depth} mm"
        else:
            project.primary_beam_result = BeamResult(
                element_type="Primary Beam",
                size=f"{width} x {depth} mm",
                width=width,
                depth=depth,
            )

    # Secondary beam section
    if (override_sec_beam_w and override_sec_beam_w > 0) or (override_sec_beam_d and override_sec_beam_d > 0):
        existing_w = project.secondary_beam_result.width if project.secondary_beam_result else 300
        existing_d = project.secondary_beam_result.depth if project.secondary_beam_result else 500
        width = _resolve_dimension(override_sec_beam_w, existing_w)
        depth = _resolve_dimension(override_sec_beam_d, existing_d)

        if project.secondary_beam_result is not None:
            project.secondary_beam_result.width = width
            project.secondary_beam_result.depth = depth
            project.secondary_beam_result.size = f"{width} x {depth} mm"
        else:
            project.secondary_beam_result = BeamResult(
                element_type="Secondary Beam",
                size=f"{width} x {depth} mm",
                width=width,
                depth=depth,
            )

    # Column section (supports rectangular and legacy square override)
    if (
        (override_col and override_col > 0)
        or (override_col_w and override_col_w > 0)
        or (override_col_d and override_col_d > 0)
    ):
        existing_w = 400
        existing_d = 400
        if project.column_result is not None:
            existing_w = project.column_result.width or project.column_result.dimension or existing_w
            existing_d = project.column_result.depth or project.column_result.dimension or existing_d

        square_override = int(override_col) if override_col and override_col > 0 else 0
        width_override = int(override_col_w) if override_col_w and override_col_w > 0 else square_override
        depth_override = int(override_col_d) if override_col_d and override_col_d > 0 else square_override

        width = _resolve_dimension(width_override, existing_w)
        depth = _resolve_dimension(depth_override, existing_d)
        dimension = max(width, depth)

        if project.column_result is not None:
            project.column_result.width = width
            project.column_result.depth = depth
            project.column_result.dimension = dimension
            project.column_result.size = f"{width} x {depth} mm"
        else:
            project.column_result = ColumnResult(
                element_type="Column",
                size=f"{width} x {depth} mm",
                width=width,
                depth=depth,
                dimension=dimension,
            )

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
        # --- AI Chat ---
        with st.expander("💬 AI Assistant", expanded=False):
            # Lazy-init assistant and chat history
            if "ai_chat_history" not in st.session_state:
                st.session_state.ai_chat_history = []
            if "ai_assistant" not in st.session_state:
                try:
                    from src.ai.model_builder_assistant import ModelBuilderAssistant
                    try:
                        from src.ai.config import AIConfig
                        from src.ai.llm_service import AIService
                        import os
                        env_path = os.path.join(os.path.dirname(__file__), ".env")
                        config = AIConfig.from_env(env_file=env_path if os.path.exists(env_path) else None)
                        service = AIService(config)
                        st.session_state.ai_assistant = ModelBuilderAssistant(ai_service=service)
                    except Exception as _init_err:
                        logger.warning(f"AI service init failed ({_init_err}), using regex-only mode")
                        st.session_state.ai_assistant = ModelBuilderAssistant()
                        st.session_state.ai_init_local_mode = True
                except ImportError:
                    st.session_state.ai_assistant = None

            assistant = st.session_state.ai_assistant
            if assistant is None:
                st.info("AI assistant not available.")
            else:
                if st.session_state.get("ai_init_local_mode"):
                    st.caption("Running in local mode — set API key in .env for AI-enhanced responses")
                # Show chat history
                for msg in st.session_state.ai_chat_history:
                    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
                        st.markdown(msg["content"])

                # Simple chat input
                user_msg = st.chat_input(
                    "Describe your building, e.g. '20-storey office, 8m x 9m bays'",
                    key="ai_chat_input",
                )

                if user_msg:
                    # Show user message
                    st.session_state.ai_chat_history.append(
                        {"role": "user", "content": user_msg}
                    )

                    # Process message
                    with st.spinner("Thinking..."):
                        result = assistant.process_message(user_msg)
                    extracted = result.get("extracted_params", {})
                    response = result.get("response", "")

                    st.session_state["ai_pending_extract"] = extracted

                    reply = response or "Got it."
                    if extracted:
                        preview = assistant.get_config_preview()
                        reply += f"\n\n### Preview\n{preview}\n\nClick **Apply Extracted Parameters** to update project inputs."

                    st.session_state.ai_chat_history.append(
                        {"role": "assistant", "content": reply}
                    )
                    st.rerun()

                pending_extract = st.session_state.get("ai_pending_extract", {})
                if pending_extract:
                    if st.button("✅ Apply Extracted Parameters", key="ai_chat_apply", type="primary"):
                        import copy

                        st.session_state["ai_undo_project"] = copy.deepcopy(st.session_state.project)
                        p = st.session_state.project
                        applied = []
                        geo_map = {
                            "bay_x": "bay_x", "bay_y": "bay_y",
                            "num_bays_x": "num_bays_x", "num_bays_y": "num_bays_y",
                            "num_floors": "floors", "floor_height": "story_height",
                        }
                        for src_key, dst_attr in geo_map.items():
                            if src_key in pending_extract and pending_extract[src_key] is not None:
                                setattr(p.geometry, dst_attr, pending_extract[src_key])
                                applied.append(f"{src_key}={pending_extract[src_key]}")

                        # Apply building type preset (loads + materials)
                        btype = pending_extract.get("building_type")
                        if btype:
                            from src.core.data_models import PRESETS
                            preset = PRESETS.get(btype)
                            if preset:
                                p.loads = copy.deepcopy(preset["loads"])
                                p.materials = copy.deepcopy(preset["materials"])
                                applied.append(f"type={btype}")

                        # Apply concrete grade override
                        cgrade = pending_extract.get("concrete_grade")
                        if cgrade:
                            grade_val = int(cgrade.replace("C", ""))
                            p.materials.fcu_slab = grade_val
                            p.materials.fcu_beam = grade_val
                            p.materials.fcu_column = grade_val
                            applied.append(f"concrete={cgrade}")

                        st.session_state["ai_pending_extract"] = {}
                        if applied:
                            st.session_state.ai_chat_history.append(
                                {"role": "assistant", "content": f"✅ Applied: {', '.join(applied)}"}
                            )
                        st.rerun()

                # Undo button (only shown when there's something to undo)
                if "ai_undo_project" in st.session_state:
                    if st.button("↩️ Undo last change", key="ai_chat_undo", type="secondary"):
                        st.session_state.project = st.session_state.ai_undo_project
                        del st.session_state["ai_undo_project"]
                        st.session_state.ai_chat_history.append(
                            {"role": "assistant", "content": "↩️ Changes reverted."}
                        )
                        st.rerun()

                if st.button("🧹 Reset AI chat", key="ai_chat_reset", type="secondary"):
                    assistant.reset()
                    st.session_state.ai_chat_history = []
                    st.session_state["ai_pending_extract"] = {}
                    st.rerun()

        st.divider()
        st.markdown("### Project Settings")
        
        inputs_locked = _is_inputs_locked() if FEM_AVAILABLE else False
        if inputs_locked:
            st.warning("🔒 **Inputs locked** - Analysis results active. Click 'Unlock to Modify' in FEM section to change inputs.")

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

        current_terrain = st.session_state.project.lateral.terrain
        if current_terrain in terrain_options:
            terrain_index = list(terrain_options.keys()).index(current_terrain)
        else:
            terrain_index = list(terrain_options.keys()).index(TerrainCategory.URBAN)

        selected_terrain_label = st.selectbox(
            "Terrain Category",
            options=list(terrain_options.values()),
            index=terrain_index,
            disabled=inputs_locked,
        )
        selected_terrain = list(terrain_options.keys())[list(terrain_options.values()).index(selected_terrain_label)]

        width_x = bay_x * num_bays_x
        width_y = bay_y * num_bays_y
        existing_wind = st.session_state.project.wind_result
        default_vx = 0.0
        default_vy = 0.0
        default_reference_pressure = 3.0
        default_force_coefficient = 1.3
        if existing_wind is not None:
            if existing_wind.base_shear_x > 0.0 or existing_wind.base_shear_y > 0.0:
                default_vx = existing_wind.base_shear_x
                default_vy = existing_wind.base_shear_y
            else:
                default_vx = existing_wind.base_shear
                default_vy = existing_wind.base_shear
            if existing_wind.reference_pressure > 0.0:
                default_reference_pressure = existing_wind.reference_pressure

        wind_input_mode = st.radio(
            "Wind Input Mode",
            options=["Manual", "HK Code Calculator"],
            key="sidebar_wind_input_mode",
            horizontal=True,
            disabled=inputs_locked,
        )

        if wind_input_mode == "Manual":
            base_shear_x = st.number_input(
                "Base Shear Vx (kN)",
                min_value=0.0,
                value=float(default_vx),
                step=10.0,
                key="sidebar_wind_base_shear_x",
                disabled=inputs_locked,
            )
            base_shear_y = st.number_input(
                "Base Shear Vy (kN)",
                min_value=0.0,
                value=float(default_vy),
                step=10.0,
                key="sidebar_wind_base_shear_y",
                disabled=inputs_locked,
            )
            reference_pressure = st.number_input(
                "Reference Pressure q0 (kPa)",
                min_value=0.0,
                value=float(default_reference_pressure),
                step=0.1,
                key="sidebar_wind_reference_pressure_manual",
                disabled=inputs_locked,
            )

            if base_shear_x > 0.0 or base_shear_y > 0.0:
                project_wind_result = WindResult(
                    base_shear=max(base_shear_x, base_shear_y),
                    base_shear_x=base_shear_x,
                    base_shear_y=base_shear_y,
                    reference_pressure=reference_pressure,
                    lateral_system="CORE_WALL",
                )
            else:
                project_wind_result = None
        else:
            reference_pressure = st.number_input(
                "Reference Pressure q0 (kPa)",
                min_value=0.0,
                value=float(default_reference_pressure),
                step=0.1,
                key="sidebar_wind_reference_pressure_calc",
                disabled=inputs_locked,
            )
            force_coefficient = st.number_input(
                "Force Coefficient Cf",
                min_value=0.0,
                value=float(default_force_coefficient),
                step=0.1,
                key="sidebar_wind_force_coefficient",
                disabled=inputs_locked,
            )

            project_wind_result = calculate_hk_wind(
                total_height=floors * story_height,
                building_width_x=width_x,
                building_width_y=width_y,
                terrain=selected_terrain,
                reference_pressure=reference_pressure,
                force_coefficient=force_coefficient,
                num_floors=floors,
                story_height=story_height,
            )
            st.info(
                f"Vx = {project_wind_result.base_shear_x:.1f} kN, "
                f"Vy = {project_wind_result.base_shear_y:.1f} kN"
            )

        has_core = st.checkbox("Core Wall System",
                              value=st.session_state.project.lateral.core_wall_config is not None,
                              disabled=inputs_locked)

        # Initialize core wall location variables with defaults
        selected_core_location = CoreLocationPreset.CENTER
        selected_opening_placement = TubeOpeningPlacement.TOP_BOT
        custom_x = None
        custom_y = None

        if has_core:
            # Get current config or default to I_SECTION
            current_config = st.session_state.project.lateral.core_wall_config or CoreWallConfig.I_SECTION

            if inputs_locked:
                selected_core_wall_config = current_config
                st.caption(f"Core wall configuration locked: {current_config.value}")
            else:
                selected_core_wall_config = render_core_wall_selector(current_config)
            
            # Wall thickness input
            wall_thickness = st.number_input(
                "Wall Thickness (mm)",
                min_value=200, max_value=1000, value=500, step=50,
                help="Core wall thickness in millimeters (typical: 500mm)",
                disabled=inputs_locked,
            )

            # Dimension inputs depend on configuration type
            if selected_core_wall_config == CoreWallConfig.I_SECTION:
                st.caption("I-Section Dimensions")
                col1, col2 = st.columns(2)
                with col1:
                    flange_width = st.number_input(
                        "Flange Width (m)", min_value=2.0, max_value=15.0, value=3.0, step=0.5,
                        help="Width of horizontal flange",
                        disabled=inputs_locked,
                    )
                with col2:
                    web_length = st.number_input(
                        "Web Length (m)", min_value=2.0, max_value=20.0, value=3.0, step=0.5,
                        help="Length of vertical web",
                        disabled=inputs_locked,
                    )

                opening_width = None
                core_x = flange_width
                core_y = web_length
                length_x = flange_width
                length_y = web_length
                opening_height = None

            else:  # TUBE_WITH_OPENINGS
                st.caption("Tube Dimensions")
                col1, col2 = st.columns(2)
                with col1:
                    length_x = st.number_input(
                        "Length X (m)", min_value=2.0, max_value=15.0, value=3.0, step=0.5,
                        help="Outer dimension in X direction",
                        disabled=inputs_locked,
                    )
                with col2:
                    length_y = st.number_input(
                        "Length Y (m)", min_value=2.0, max_value=15.0, value=3.0, step=0.5,
                        help="Outer dimension in Y direction",
                        disabled=inputs_locked,
                    )

                placement_labels = {
                    TubeOpeningPlacement.TOP_BOT: "Top-Bot",
                    TubeOpeningPlacement.NONE: "None",
                }
                selected_placement_label = st.selectbox(
                    "Opening Placement",
                    options=list(placement_labels.values()),
                    index=0,
                    help="Choose where tube core openings are placed.",
                    key="runtime_opening_placement",
                    disabled=inputs_locked,
                )
                selected_opening_placement = list(placement_labels.keys())[
                    list(placement_labels.values()).index(selected_placement_label)
                ]

                st.caption("Opening Dimension")
                opening_size = st.number_input(
                    "Opening Size (m)",
                    min_value=0.5,
                    max_value=5.0,
                    value=1.0,
                    step=0.5,
                    help="Single opening dimension used for top and bottom openings.",
                    disabled=inputs_locked or selected_opening_placement == TubeOpeningPlacement.NONE,
                )
                opening_width = (
                    None
                    if selected_opening_placement == TubeOpeningPlacement.NONE
                    else opening_size
                )
                opening_height = None

                core_x = length_x
                core_y = length_y
                flange_width = None
                web_length = None

            # Core Location Preset (9 positions)
            st.caption("Core Position")
            preset_labels = {
                CoreLocationPreset.CENTER: "Center",
                CoreLocationPreset.NORTH: "North",
                CoreLocationPreset.SOUTH: "South",
                CoreLocationPreset.EAST: "East",
                CoreLocationPreset.WEST: "West",
                CoreLocationPreset.NORTHEAST: "Northeast",
                CoreLocationPreset.NORTHWEST: "Northwest",
                CoreLocationPreset.SOUTHEAST: "Southeast",
                CoreLocationPreset.SOUTHWEST: "Southwest",
            }
            selected_preset_label = st.selectbox(
                "Location Preset",
                options=list(preset_labels.values()),
                index=0,
                help="Select core wall placement in floor plan. All presets enforce bounding-box clearance.",
                key="runtime_core_location_preset",
                disabled=inputs_locked,
            )
            selected_core_location = list(preset_labels.keys())[
                list(preset_labels.values()).index(selected_preset_label)
            ]
            custom_x = None
            custom_y = None
            
            # Calculate and display section properties
            st.caption("Calculated Section Properties")
            temp_geometry = CoreWallGeometry(
                config=selected_core_wall_config,
                wall_thickness=wall_thickness,
                length_x=length_x * 1000 if length_x else 6000.0,
                length_y=length_y * 1000 if length_y else 6000.0,
                opening_width=opening_width * 1000 if opening_width else None,
                opening_height=None,
                flange_width=flange_width * 1000 if flange_width else None,
                web_length=web_length * 1000 if web_length else None,
                opening_placement=selected_opening_placement,
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
            selected_core_location = CoreLocationPreset.CENTER
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
                    opening_height=None,
                    flange_width=flange_width * 1000 if flange_width else None,
                    web_length=web_length * 1000 if web_length else None,
                    opening_placement=selected_opening_placement,
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

        # Section Properties
        st.markdown("##### Section Properties")
        st.caption("Selected sections used by FEM model. Changes auto-update the model and DL self-weight.")

        current_project = st.session_state.project

        slab_default = 200
        if current_project.slab_result and current_project.slab_result.thickness > 0:
            slab_default = int(current_project.slab_result.thickness)

        override_slab_thickness = st.number_input(
            "Slab Thickness (mm)",
            min_value=100,
            max_value=500,
            value=slab_default,
            step=25,
            help="Used directly for FEM slab self-weight in DL.",
            disabled=inputs_locked,
        )

        st.caption("Primary Beam")
        col1, col2 = st.columns(2)
        with col1:
            pri_width_default = 300
            if current_project.primary_beam_result and current_project.primary_beam_result.width > 0:
                pri_width_default = int(current_project.primary_beam_result.width)
            override_pri_beam_width = st.number_input(
                "Pri. Width (mm)",
                min_value=150,
                max_value=1200,
                value=pri_width_default,
                step=25,
                help="Primary beam section width.",
                disabled=inputs_locked,
            )
        with col2:
            pri_depth_default = 600
            if current_project.primary_beam_result and current_project.primary_beam_result.depth > 0:
                pri_depth_default = int(current_project.primary_beam_result.depth)
            override_pri_beam_depth = st.number_input(
                "Pri. Depth (mm)",
                min_value=250,
                max_value=1500,
                value=pri_depth_default,
                step=50,
                help="Primary beam section depth.",
                disabled=inputs_locked,
            )

        st.caption("Secondary Beam")
        col1, col2 = st.columns(2)
        with col1:
            sec_width_default = 300
            if current_project.secondary_beam_result and current_project.secondary_beam_result.width > 0:
                sec_width_default = int(current_project.secondary_beam_result.width)
            override_sec_beam_width = st.number_input(
                "Sec. Width (mm)",
                min_value=150,
                max_value=1200,
                value=sec_width_default,
                step=25,
                help="Secondary beam section width.",
                disabled=inputs_locked,
            )
        with col2:
            sec_depth_default = 500
            if current_project.secondary_beam_result and current_project.secondary_beam_result.depth > 0:
                sec_depth_default = int(current_project.secondary_beam_result.depth)
            override_sec_beam_depth = st.number_input(
                "Sec. Depth (mm)",
                min_value=250,
                max_value=1500,
                value=sec_depth_default,
                step=50,
                help="Secondary beam section depth.",
                disabled=inputs_locked,
            )

        st.caption("Column (Rectangular)")
        col1, col2 = st.columns(2)
        with col1:
            col_width_default = 400
            if current_project.column_result:
                col_width_default = int(
                    current_project.column_result.width
                    or current_project.column_result.dimension
                    or col_width_default
                )
            override_column_width = st.number_input(
                "Column Width (mm)",
                min_value=200,
                max_value=2000,
                value=col_width_default,
                step=25,
                help="Column section width (X).",
                disabled=inputs_locked,
            )
        with col2:
            col_depth_default = 400
            if current_project.column_result:
                col_depth_default = int(
                    current_project.column_result.depth
                    or current_project.column_result.dimension
                    or col_depth_default
                )
            override_column_depth = st.number_input(
                "Column Depth (mm)",
                min_value=200,
                max_value=2000,
                value=col_depth_default,
                step=25,
                help="Column section depth (Y).",
                disabled=inputs_locked,
            )

        override_column_size = max(override_column_width, override_column_depth)

        # Coupling Beam (only when Core Wall is enabled)
        coupling_beam_width = int(wall_thickness) if has_core else 500
        coupling_beam_depth = 800
        coupling_beam_span = 1500
        if has_core and selected_core_wall_config:
            st.caption("Coupling Beam")
            cb_col1, cb_col2, cb_col3 = st.columns(3)
            with cb_col1:
                coupling_beam_width = st.number_input(
                    "CB Width (mm)", min_value=200, max_value=1000,
                    value=st.session_state.get("coupling_beam_width", int(wall_thickness)),
                    step=50, key="cb_width_input",
                    help="Coupling beam width (typically matches wall thickness)",
                    disabled=inputs_locked,
                )
                st.session_state.coupling_beam_width = coupling_beam_width
            with cb_col2:
                coupling_beam_depth = st.number_input(
                    "CB Depth (mm)", min_value=300, max_value=2000,
                    value=st.session_state.get("coupling_beam_depth", 800),
                    step=50, key="cb_depth_input",
                    help="Coupling beam depth (typical: 600-1200mm)",
                    disabled=inputs_locked,
                )
                st.session_state.coupling_beam_depth = coupling_beam_depth
            with cb_col3:
                cb_span_default = int((opening_width * 1000) if opening_width else 1500)
                coupling_beam_span = st.number_input(
                    "CB Span (mm)", min_value=500, max_value=5000,
                    value=st.session_state.get("coupling_beam_span", cb_span_default),
                    step=100, key="cb_span_input",
                    help="Clear span between wall piers (= opening width)",
                    disabled=inputs_locked,
                )
                st.session_state.coupling_beam_span = coupling_beam_span

            cb_ld = coupling_beam_span / coupling_beam_depth if coupling_beam_depth > 0 else 0
            if cb_ld < 2.0:
                st.caption(f"L/d = {cb_ld:.1f} → Deep beam (diagonal reinforcement)")
            else:
                st.caption(f"L/d = {cb_ld:.1f} → Conventional beam")

        summary_parts = [
            f"Slab {override_slab_thickness} mm",
            f"Pri {override_pri_beam_width}×{override_pri_beam_depth} mm",
            f"Sec {override_sec_beam_width}×{override_sec_beam_depth} mm",
            f"Col {override_column_width}×{override_column_depth} mm",
        ]
        if has_core and selected_core_wall_config:
            summary_parts.append(f"CB {coupling_beam_width}×{coupling_beam_depth} mm")
        st.caption("Selected: " + " | ".join(summary_parts))

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
                help="This combination is used for the FEM design checks"
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
            opening_height=None,
            flange_width=flange_width * 1000 if flange_width else None,
            web_length=web_length * 1000 if web_length else None,
            opening_placement=selected_opening_placement,
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
        location_preset=selected_core_location if has_core else CoreLocationPreset.CENTER,
        custom_center_x=custom_x if has_core else None,
        custom_center_y=custom_y if has_core else None,
    )
    project.wind_result = project_wind_result
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
        override_col_w=override_column_width,
        override_col_d=override_column_depth,
        secondary_along_x=secondary_along_x,
        num_secondary_beams=num_secondary_beams
    )

    setattr(project, "coupling_beam_width_mm", st.session_state.get("coupling_beam_width", coupling_beam_width))
    setattr(project, "coupling_beam_depth_mm", st.session_state.get("coupling_beam_depth", coupling_beam_depth))
    setattr(project, "coupling_beam_span_mm", st.session_state.get("coupling_beam_span", coupling_beam_span))

    st.session_state.project = project

    # ===== MAIN CONTENT =====

    # FEM Analysis & Preview
    if FEM_AVAILABLE:
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
    else:
        st.markdown("### FEM Analysis")
        st.info("FEM Analysis requires OpenSeesPy (available on local install only).")




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
            setattr(project, "_fem_model", st.session_state.get("fem_model_cache"))
            setattr(project, "_fem_results_by_case", st.session_state.get("fem_analysis_results_dict", {}))
            setattr(project, "_selected_combinations", sorted(st.session_state.get("selected_combinations", set())))

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
                components.html(html_content, height=800, scrolling=True)

    # Footer
    st.divider()
    st.markdown("""
    <p style="text-align: center; color: #94A3B8; font-size: 12px;">
        PrelimStruct v3.0 | FEM + AI-Assisted Design | HK Code 2013 + Wind Code 2019
    </p>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
