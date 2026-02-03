"""
Overlay Renderers Module.

This module provides rendering functions for overlays:
- Support symbols (fixed, pinned, roller)
- Load indicators (gravity, lateral)
- Node labels
- Ghost columns
"""

from typing import Dict, List, Optional, Tuple

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None  # type: ignore

from src.fem.fem_engine import Node, Load, UniformLoad, SurfaceLoad, RigidDiaphragm
from src.fem.visualization.element_renderer import COLORS


def render_supports(
    nodes: Dict[int, Node],
    node_tags: List[int],
    support_size: int = 15,
) -> List[go.Scatter]:
    """Render support symbols at specified nodes.

    Args:
        nodes: Dictionary of nodes
        node_tags: List of node tags to check for supports
        support_size: Size of support markers

    Returns:
        List of Plotly traces for supports
    """
    if not PLOTLY_AVAILABLE:
        return []

    fixed_x, fixed_y = [], []
    pinned_x, pinned_y = [], []
    other_x, other_y = [], []

    for tag in node_tags:
        node = nodes.get(tag)
        if node is None:
            continue

        if node.is_fixed:
            fixed_x.append(node.x)
            fixed_y.append(node.y)
        elif node.is_pinned:
            pinned_x.append(node.x)
            pinned_y.append(node.y)
        elif any(r == 1 for r in node.restraints):
            other_x.append(node.x)
            other_y.append(node.y)

    traces = []

    if fixed_x:
        traces.append(go.Scatter(
            x=fixed_x,
            y=fixed_y,
            mode='markers',
            marker=dict(
                symbol='square',
                size=support_size,
                color=COLORS["support_fixed"],
            ),
            name='Fixed Support',
            hovertemplate='Fixed Support<br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>',
        ))

    if pinned_x:
        traces.append(go.Scatter(
            x=pinned_x,
            y=pinned_y,
            mode='markers',
            marker=dict(
                symbol='triangle-up',
                size=support_size,
                color=COLORS["support_pinned"],
            ),
            name='Pinned Support',
            hovertemplate='Pinned Support<br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>',
        ))

    if other_x:
        traces.append(go.Scatter(
            x=other_x,
            y=other_y,
            mode='markers',
            marker=dict(
                symbol='circle',
                size=support_size // 2,
                color=COLORS["support_roller"],
            ),
            name='Other Restraint',
            hovertemplate='Restraint<br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>',
        ))

    return traces


def render_nodes(
    nodes: Dict[int, Node],
    node_tags: List[int],
    node_size: int = 8,
    show_labels: bool = False,
) -> List[go.Scatter]:
    """Render node markers.

    Args:
        nodes: Dictionary of nodes
        node_tags: List of node tags to render
        node_size: Size of node markers
        show_labels: Whether to show node labels

    Returns:
        List of Plotly traces for nodes
    """
    if not PLOTLY_AVAILABLE:
        return []

    x_coords = []
    y_coords = []
    labels = []

    for tag in node_tags:
        node = nodes.get(tag)
        if node is None:
            continue
        x_coords.append(node.x)
        y_coords.append(node.y)
        if show_labels:
            labels.append(f"Node {tag}")

    if not x_coords:
        return []

    return [go.Scatter(
        x=x_coords,
        y=y_coords,
        mode='markers+text' if show_labels else 'markers',
        marker=dict(
            symbol='circle',
            size=node_size,
            color=COLORS["node"],
        ),
        text=labels if show_labels else None,
        textposition='top center',
        name='Nodes',
        hovertemplate='Node %{text}<br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>' if show_labels else 'X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>',
    )]


def render_loads(
    nodes: Dict[int, Node],
    loads: List[Load],
    uniform_loads: List[UniformLoad],
    load_scale: float = 1.0,
) -> List[go.Scatter]:
    """Render load indicators.

    Args:
        nodes: Dictionary of nodes
        loads: List of point loads
        uniform_loads: List of uniform loads
        load_scale: Scale factor for load arrows

    Returns:
        List of Plotly traces for loads
    """
    if not PLOTLY_AVAILABLE:
        return []

    traces = []

    # Render point loads
    for load in loads:
        node = nodes.get(load.node_tag)
        if node is None:
            continue

        # Determine load direction and magnitude
        fx, fy, fz = load.load_values[0], load.load_values[1], load.load_values[2]
        magnitude = (fx**2 + fy**2 + fz**2) ** 0.5

        if magnitude < 0.001:
            continue

        # Scale arrow length
        arrow_length = magnitude * load_scale * 0.1

        # Determine color based on load type
        if abs(fz) > abs(fx) and abs(fz) > abs(fy):
            color = COLORS["load_gravity"]
            name = "Gravity Load"
        else:
            color = COLORS["load_lateral"]
            name = "Lateral Load"

        # Create arrow (simple line for now)
        # Direction is primarily in XY for plan view
        dx = fx / magnitude * arrow_length
        dy = fy / magnitude * arrow_length

        traces.append(go.Scatter(
            x=[node.x, node.x + dx],
            y=[node.y, node.y + dy],
            mode='lines+markers',
            line=dict(color=color, width=2),
            marker=dict(symbol='arrow', size=10, color=color),
            name=name,
            showlegend=False,
            hovertemplate=f'{name}<br>Magnitude: {magnitude:.2f} kN<extra></extra>',
        ))

    return traces


def render_ghost_columns(
    ghost_columns: List[Dict[str, any]],
    target_z: float,
    tolerance: float = 0.01,
) -> List[go.Scatter]:
    """Render ghost columns (omitted columns) at a specific elevation.

    Args:
        ghost_columns: List of ghost column dictionaries with 'x', 'y', 'id'
        target_z: Target elevation
        tolerance: Elevation tolerance

    Returns:
        List of Plotly traces for ghost columns
    """
    if not PLOTLY_AVAILABLE or not ghost_columns:
        return []

    x_coords = []
    y_coords = []
    labels = []

    for col in ghost_columns:
        # For plan view, ghost columns appear at all levels
        # In a real implementation, you'd need to track which floor each ghost column belongs to
        x_coords.append(col['x'])
        y_coords.append(col['y'])
        labels.append(f"Ghost {col['id']}")

    if not x_coords:
        return []

    return [go.Scatter(
        x=x_coords,
        y=y_coords,
        mode='markers',
        marker=dict(
            symbol='x',
            size=12,
            color=COLORS["ghost_column"],
            line=dict(width=2),
        ),
        name='Ghost Columns (Omitted)',
        text=labels,
        hovertemplate='%{text}<br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>',
    )]


def render_slabs(
    nodes: Dict[int, Node],
    element_tags: List[int],
    target_z: float,
    tolerance: float = 0.01,
) -> List[go.Scatter]:
    """Render slab panels at a specific elevation.

    Args:
        nodes: Dictionary of nodes
        element_tags: List of slab element tags (4-node shells)
        target_z: Target elevation
        tolerance: Elevation tolerance

    Returns:
        List of Plotly traces for slabs
    """
    if not PLOTLY_AVAILABLE or not element_tags:
        return []

    traces = []

    for elem_tag in element_tags:
        # Note: In the actual implementation, you'd need to look up the element
        # and get its node tags, then create a filled polygon
        # This is a simplified version
        pass

    return traces


__all__ = [
    "render_supports",
    "render_nodes",
    "render_loads",
    "render_ghost_columns",
    "render_slabs",
]
