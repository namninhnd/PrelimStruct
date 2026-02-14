"""
Element Renderer Module.

This module provides rendering functions for structural elements:
- Beams (primary and secondary)
- Columns
- Core walls (shell elements)
- Coupling beams
- Slabs

All renderers return Plotly traces that can be added to a Figure.
"""

from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass

try:
    import plotly.graph_objects as go
    from plotly import colors as plotly_colors
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None  # type: ignore
    plotly_colors = None  # type: ignore

from src.fem.fem_engine import Node, Element, ElementType


# Color scheme consistent with original visualization.py
COLORS = {
    "column": "#EF4444",        # Red
    "beam": "#1f77b4",          # Blue (primary beams)
    "beam_secondary": "#aec7e8", # Light Blue (secondary beams)
    "core_wall": "#64748B",     # Grey
    "coupling_beam": "#F59E0B", # Orange (Amber)
    "support_fixed": "#EF4444", # Red
    "support_pinned": "#10B981", # Green
    "support_roller": "#3B82F6", # Blue
    "load_gravity": "#6366F1",  # Indigo
    "load_lateral": "#EC4899",  # Pink
    "node": "#374151",          # Gray
    "slab": "rgba(59, 130, 246, 0.1)", # Light Blue with opacity
    "ghost_column": "#9CA3AF",  # Grey for omitted columns
}


@dataclass
class RenderConfig:
    """Configuration for element rendering."""
    element_width: int = 3
    node_size: int = 8
    show_labels: bool = False
    colorscale: str = "RdYlGn_r"


class ModelLike(Protocol):
    """Protocol for models that can be visualized."""
    nodes: Dict[int, Node]
    elements: Dict[int, Element]


def _clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value within [min_value, max_value]."""
    return max(min_value, min(value, max_value))


def _get_utilization_color(utilization: float, colorscale: str) -> str:
    """Map utilization ratio to a colorscale color."""
    if plotly_colors is None:
        return COLORS["beam"]
    util = _clamp(utilization, 0.0, 1.2)
    normalized = util / 1.2
    scale = plotly_colors.get_colorscale(colorscale)
    rgb = plotly_colors.sample_colorscale(scale, normalized)[0]
    # Convert rgb(r, g, b) to hex
    import re
    match = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", rgb)
    if match:
        r, g, b = map(int, match.groups())
        return f"#{r:02x}{g:02x}{b:02x}"
    return rgb


def classify_elements(model: ModelLike) -> Dict[str, List[int]]:
    """Classify elements by type for visualization grouping.

    Returns:
        Dictionary mapping element type names to lists of element tags
    """
    classification: Dict[str, List[int]] = {
        "columns": [],
        "beams": [],
        "beams_secondary": [],
        "core_walls": [],
        "coupling_beams": [],
        "slabs": [],
        "other": [],
    }

    for elem in model.elements.values():
        if len(elem.node_tags) < 2:
            continue

        if elem.element_type in (ElementType.SHELL, ElementType.SHELL_MITC4, ElementType.SHELL_DKGT):
            if elem.section_tag == 5:
                classification["slabs"].append(elem.tag)
            else:
                classification["core_walls"].append(elem.tag)
            continue

        node_i = model.nodes[elem.node_tags[0]]
        node_j = model.nodes[elem.node_tags[1]]

        # Check if vertical (column) or horizontal (beam)
        is_vertical = (abs(node_i.z - node_j.z) > 0.01 and
                      abs(node_i.x - node_j.x) < 0.01 and
                      abs(node_i.y - node_j.y) < 0.01)

        if elem.element_type == ElementType.COUPLING_BEAM:
            classification["coupling_beams"].append(elem.tag)
        elif is_vertical:
            classification["columns"].append(elem.tag)
        else:
            if elem.section_tag == 2:
                classification["beams_secondary"].append(elem.tag)
            else:
                classification["beams"].append(elem.tag)

    return classification


def render_beams(
    model: ModelLike,
    element_tags: List[int],
    config: RenderConfig,
    is_secondary: bool = False,
    utilization: Optional[Dict[int, float]] = None,
) -> List[go.Scatter]:
    """Render beam elements.

    Args:
        model: Model containing nodes and elements
        element_tags: List of beam element tags to render
        config: Rendering configuration
        is_secondary: True if these are secondary beams
        utilization: Optional utilization data for coloring

    Returns:
        List of Plotly traces
    """
    if not PLOTLY_AVAILABLE or not element_tags:
        return []

    traces = []
    use_utilization = utilization is not None and len(utilization) > 0

    x_coords: List[Optional[float]] = []
    y_coords: List[Optional[float]] = []
    text_labels: List[str] = []
    legend_added = False

    color = COLORS["beam_secondary"] if is_secondary else COLORS["beam"]
    name = "Secondary Beam" if is_secondary else "Primary Beam"

    for elem_tag in element_tags:
        elem = model.elements.get(elem_tag)
        if elem is None or len(elem.node_tags) < 2:
            continue

        node_i = model.nodes.get(elem.node_tags[0])
        node_j = model.nodes.get(elem.node_tags[1])
        if node_i is None or node_j is None:
            continue

        if use_utilization:
            util = utilization.get(elem_tag, 0.0)
            color = _get_utilization_color(util, config.colorscale)
            traces.append(go.Scatter(
                x=[node_i.x, node_j.x],
                y=[node_i.y, node_j.y],
                mode='lines',
                line=dict(color=color, width=config.element_width),
                name=name,
                showlegend=not legend_added,
                legendgroup=name,
                customdata=[[elem_tag, util]],
                hovertemplate=(
                    f"{name} %{{customdata[0]}}<br>"
                    f"Util: %{{customdata[1]:.1%}}<extra></extra>"
                ),
            ))
            legend_added = True
        else:
            x_coords.extend([node_i.x, node_j.x, None])
            y_coords.extend([node_i.y, node_j.y, None])
            if config.show_labels:
                text_labels.append(f"Beam {elem_tag}")

    if not use_utilization and x_coords:
        traces.append(go.Scatter(
            x=x_coords,
            y=y_coords,
            mode='lines',
            line=dict(color=color, width=config.element_width),
            name=name,
            hoverinfo='text' if text_labels else 'none',
            text=text_labels * (len(x_coords) // 3) if text_labels else None,
            legendgroup=name,
        ))

    return traces


def render_columns(
    model: ModelLike,
    element_tags: List[int],
    config: RenderConfig,
    utilization: Optional[Dict[int, float]] = None,
) -> List[go.Scatter]:
    """Render column elements.

    Args:
        model: Model containing nodes and elements
        element_tags: List of column element tags to render
        config: Rendering configuration
        utilization: Optional utilization data for coloring

    Returns:
        List of Plotly traces
    """
    if not PLOTLY_AVAILABLE or not element_tags:
        return []

    traces = []
    use_utilization = utilization is not None and len(utilization) > 0

    x_coords: List[Optional[float]] = []
    y_coords: List[Optional[float]] = []
    text_labels: List[str] = []
    legend_added = False

    for elem_tag in element_tags:
        elem = model.elements.get(elem_tag)
        if elem is None or len(elem.node_tags) < 2:
            continue

        node_i = model.nodes.get(elem.node_tags[0])
        node_j = model.nodes.get(elem.node_tags[1])
        if node_i is None or node_j is None:
            continue

        if use_utilization:
            util = utilization.get(elem_tag, 0.0)
            color = _get_utilization_color(util, config.colorscale)
            traces.append(go.Scatter(
                x=[node_i.x, node_j.x],
                y=[node_i.y, node_j.y],
                mode='lines',
                line=dict(color=color, width=config.element_width),
                name='Columns',
                showlegend=not legend_added,
                legendgroup='columns',
                customdata=[[elem_tag, util]],
                hovertemplate=(
                    "Column %{customdata[0]}<br>"
                    "Util: %{customdata[1]:.1%}<extra></extra>"
                ),
            ))
            legend_added = True
        else:
            x_coords.extend([node_i.x, node_j.x, None])
            y_coords.extend([node_i.y, node_j.y, None])
            if config.show_labels:
                text_labels.append(f"Column {elem_tag}")

    if not use_utilization and x_coords:
        traces.append(go.Scatter(
            x=x_coords,
            y=y_coords,
            mode='lines',
            line=dict(color=COLORS["column"], width=config.element_width),
            name='Columns',
            hoverinfo='text' if text_labels else 'none',
            text=text_labels * (len(x_coords) // 3) if text_labels else None,
            legendgroup='columns',
        ))

    return traces


def render_core_walls(
    model: ModelLike,
    element_tags: List[int],
    config: RenderConfig,
    target_z: float,
    tolerance: float = 0.01,
    utilization: Optional[Dict[int, float]] = None,
) -> List[go.Scatter]:
    """Render core wall elements at a specific elevation.

    Args:
        model: Model containing nodes and elements
        element_tags: List of core wall element tags
        config: Rendering configuration
        target_z: Target elevation for plan view
        tolerance: Elevation tolerance
        utilization: Optional utilization data for coloring

    Returns:
        List of Plotly traces
    """
    if not PLOTLY_AVAILABLE or not element_tags:
        return []

    traces = []
    use_utilization = utilization is not None and len(utilization) > 0

    x_coords: List[Optional[float]] = []
    y_coords: List[Optional[float]] = []
    text_labels: List[str] = []
    legend_added = False

    for elem_tag in element_tags:
        elem = model.elements.get(elem_tag)
        if elem is None or len(elem.node_tags) < 3:
            continue

        nodes = [model.nodes.get(tag) for tag in elem.node_tags]
        if None in nodes:
            continue

        for i in range(len(nodes)):
            n1 = nodes[i]
            n2 = nodes[(i + 1) % len(nodes)]

            if (abs(n1.z - target_z) < tolerance and
                abs(n2.z - target_z) < tolerance):

                if use_utilization:
                    util = utilization.get(elem_tag, 0.0)
                    color = _get_utilization_color(util, config.colorscale)
                    traces.append(go.Scatter(
                        x=[n1.x, n2.x],
                        y=[n1.y, n2.y],
                        mode='lines',
                        line=dict(color=color, width=config.element_width + 4),
                        name='Core Walls',
                        showlegend=not legend_added,
                        legendgroup='core_walls',
                        customdata=[[elem_tag, util]],
                        hovertemplate=(
                            "Core Wall %{customdata[0]}<br>"
                            "Util: %{customdata[1]:.1%}<extra></extra>"
                        ),
                    ))
                    legend_added = True
                else:
                    x_coords.extend([n1.x, n2.x, None])
                    y_coords.extend([n1.y, n2.y, None])
                    if config.show_labels:
                        text_labels.append(f"Core Wall {elem_tag}")

    if not use_utilization and x_coords:
        traces.append(go.Scatter(
            x=x_coords,
            y=y_coords,
            mode='lines',
            line=dict(color=COLORS["core_wall"], width=config.element_width + 4),
            name='Core Walls',
            hoverinfo='text' if text_labels else 'none',
            text=text_labels * (len(x_coords) // 3) if text_labels else None,
            legendgroup='core_walls',
        ))

    return traces


__all__ = [
    "COLORS",
    "RenderConfig",
    "classify_elements",
    "render_beams",
    "render_columns",
    "render_core_walls",
    "_get_utilization_color",
]
