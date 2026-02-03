"""
Specialized Renderers Module.

This module provides specialized rendering functions for:
- Slab panels with mesh grids
- Ghost columns (omitted columns)
- Custom annotations
"""

from typing import Dict, List, Optional, Tuple

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None  # type: ignore

from src.fem.fem_engine import Node, Element
from src.fem.visualization.element_renderer import COLORS


def render_slab_mesh(
    nodes: Dict[int, Node],
    element: Element,
    target_z: float,
    tolerance: float = 0.01,
) -> Optional[go.Scatter]:
    """Render a single slab element as a filled polygon.

    Args:
        nodes: Dictionary of nodes
        element: Slab element (4-node shell)
        target_z: Target elevation
        tolerance: Elevation tolerance

    Returns:
        Plotly trace for the slab panel, or None if not at elevation
    """
    if not PLOTLY_AVAILABLE or len(element.node_tags) != 4:
        return None

    # Get nodes for this element
    elem_nodes = []
    for tag in element.node_tags:
        node = nodes.get(tag)
        if node is None:
            return None
        elem_nodes.append(node)

    # Check if element is at target elevation
    avg_z = sum(n.z for n in elem_nodes) / 4
    if abs(avg_z - target_z) >= tolerance:
        return None

    # Create polygon
    x_coords = [n.x for n in elem_nodes] + [elem_nodes[0].x]  # Close the polygon
    y_coords = [n.y for n in elem_nodes] + [elem_nodes[0].y]

    return go.Scatter(
        x=x_coords,
        y=y_coords,
        mode='lines',
        fill='toself',
        fillcolor=COLORS["slab"],
        line=dict(color=COLORS["beam"], width=1),
        name='Slab',
        hoverinfo='skip',
        showlegend=False,
    )


def render_slab_grid_lines(
    nodes: Dict[int, Node],
    element: Element,
    target_z: float,
    tolerance: float = 0.01,
) -> Optional[go.Scatter]:
    """Render grid lines for a slab element.

    Args:
        nodes: Dictionary of nodes
        element: Slab element (4-node shell)
        target_z: Target elevation
        tolerance: Elevation tolerance

    Returns:
        Plotly trace for grid lines, or None if not at elevation
    """
    if not PLOTLY_AVAILABLE or len(element.node_tags) != 4:
        return None

    # Get nodes for this element
    elem_nodes = []
    for tag in element.node_tags:
        node = nodes.get(tag)
        if node is None:
            return None
        elem_nodes.append(node)

    # Check if element is at target elevation
    avg_z = sum(n.z for n in elem_nodes) / 4
    if abs(avg_z - target_z) >= tolerance:
        return None

    # Create grid lines (diagonals)
    x_coords = [
        elem_nodes[0].x, elem_nodes[2].x, None,
        elem_nodes[1].x, elem_nodes[3].x, None
    ]
    y_coords = [
        elem_nodes[0].y, elem_nodes[2].y, None,
        elem_nodes[1].y, elem_nodes[3].y, None
    ]

    return go.Scatter(
        x=x_coords,
        y=y_coords,
        mode='lines',
        line=dict(color=COLORS["beam"], width=1, dash='dot'),
        name='Slab Grid',
        hoverinfo='skip',
        showlegend=False,
    )


def render_slabs(
    model,
    element_tags: List[int],
    target_z: float,
    show_mesh_grid: bool = True,
    tolerance: float = 0.01,
) -> List[go.Scatter]:
    """Render all slab elements at a specific elevation.

    Args:
        model: Model with nodes and elements
        element_tags: List of slab element tags
        target_z: Target elevation
        show_mesh_grid: Whether to show mesh grid lines
        tolerance: Elevation tolerance

    Returns:
        List of Plotly traces
    """
    traces = []

    for tag in element_tags:
        elem = model.elements.get(tag)
        if elem is None:
            continue

        # Render slab fill
        slab_trace = render_slab_mesh(
            model.nodes, elem, target_z, tolerance
        )
        if slab_trace:
            traces.append(slab_trace)

        # Render grid lines if requested
        if show_mesh_grid:
            grid_trace = render_slab_grid_lines(
                model.nodes, elem, target_z, tolerance
            )
            if grid_trace:
                traces.append(grid_trace)

    return traces


def render_ghost_column_3d(
    x: float,
    y: float,
    z_base: float,
    z_top: float,
    column_id: str,
) -> List[go.Scatter3d]:
    """Render a ghost column in 3D view.

    Args:
        x: X coordinate
        y: Y coordinate
        z_base: Base elevation
        z_top: Top elevation
        column_id: Column identifier

    Returns:
        List of 3D Plotly traces
    """
    if not PLOTLY_AVAILABLE:
        return []

    # Create dashed line for ghost column
    line_trace = go.Scatter3d(
        x=[x, x],
        y=[y, y],
        z=[z_base, z_top],
        mode='lines',
        line=dict(
            color=COLORS["ghost_column"],
            width=4,
            dash='dash',
        ),
        name='Ghost Column',
        hovertemplate=f'Ghost {column_id}<extra></extra>',
        showlegend=False,
    )

    # Add X marker at base
    marker_trace = go.Scatter3d(
        x=[x],
        y=[y],
        z=[z_base],
        mode='markers',
        marker=dict(
            symbol='x',
            size=8,
            color=COLORS["ghost_column"],
        ),
        name='Ghost Base',
        hoverinfo='skip',
        showlegend=False,
    )

    return [line_trace, marker_trace]


__all__ = [
    "render_slab_mesh",
    "render_slab_grid_lines",
    "render_slabs",
    "render_ghost_column_3d",
]
