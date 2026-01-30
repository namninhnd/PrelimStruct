"""Structural layout visualization functions for PrelimStruct dashboard.

This module contains visualization functions for displaying structural framing plans,
lateral load diagrams, and utilization maps using Plotly.
"""

from typing import Dict, Any, Tuple, Optional

import plotly.graph_objects as go
import numpy as np

from src.core.data_models import ProjectData, CoreWallConfig
from src.fem.fem_engine import FEMModel
from src.fem.core_wall_helpers import get_core_wall_outline, get_coupling_beams
from src.fem.beam_trimmer import BeamTrimmer
from src.ui.utils import create_beam_geometries_from_project


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
        # Default to CENTER for visualization since core_location enum is removed
        cx = (total_x - core_x) / 2
        cy = (total_y - core_y) / 2

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
            except Exception:
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
