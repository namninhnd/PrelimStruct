"""
FEM Model Visualization Module.

This module provides visualization functions for FEM models using Plotly,
enabling Plan View, Elevation View, and 3D View rendering of structural models.

The module extracts geometry from FEMModel objects or OpenSeesPy models and
renders interactive visualizations without requiring OpenSeesPy to be running.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Protocol, Set, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from src.fem.results_processor import SectionForcesData

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from plotly import colors as plotly_colors
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None  # type: ignore
    plotly_colors = None  # type: ignore

try:
    import opsvis as opsv
    OPSVIS_AVAILABLE = True
except Exception:
    opsv = None  # type: ignore
    OPSVIS_AVAILABLE = False

try:
    import vfo
    VFO_AVAILABLE = True
except Exception:
    vfo = None  # type: ignore
    VFO_AVAILABLE = False

from src.fem.fem_engine import (
    FEMModel,
    ElementType,
    Node,
    Element,
    Load,
    UniformLoad,
    SurfaceLoad,
    RigidDiaphragm,
)


class VisualizationBackend(Enum):
    """Visualization data extraction backend."""
    AUTO = "auto"
    OPSVIS = "opsvis"
    VFO = "vfo"
    OPENSEES = "opensees"


@dataclass
class VisualizationExtractionConfig:
    """Configuration options for visualization data extraction.

    Attributes:
        backend: Backend to use (auto-selects when AUTO)
        default_element_type: Element type assigned when unknown
        fixed_node_tags: Optional list of fully fixed node tags
        pinned_node_tags: Optional list of pinned node tags
        allow_fallback: Allow fallback to OpenSees extraction on backend failure
    """
    backend: VisualizationBackend = VisualizationBackend.AUTO
    default_element_type: ElementType = ElementType.ELASTIC_BEAM
    fixed_node_tags: Optional[List[int]] = None
    pinned_node_tags: Optional[List[int]] = None
    allow_fallback: bool = True


@dataclass
class VisualizationData:
    """Lightweight visualization data snapshot.

    This structure mirrors the core attributes of FEMModel for visualization
    without requiring the full FEMModel to be present.
    """
    nodes: Dict[int, Node] = field(default_factory=dict)
    elements: Dict[int, Element] = field(default_factory=dict)
    loads: List[Load] = field(default_factory=list)
    uniform_loads: List[UniformLoad] = field(default_factory=list)
    surface_loads: List[SurfaceLoad] = field(default_factory=list)
    diaphragms: List[RigidDiaphragm] = field(default_factory=list)
    omitted_columns: List[Dict] = field(default_factory=list)
    source: str = "unknown"
    _is_built: bool = True

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for visualization datasets."""
        return {
            "n_nodes": len(self.nodes),
            "n_elements": len(self.elements),
            "n_materials": 0,
            "n_sections": 0,
            "n_loads": len(self.loads),
            "n_uniform_loads": len(self.uniform_loads),
            "n_surface_loads": len(self.surface_loads),
            "n_fixed_nodes": len([node for node in self.nodes.values() if node.is_fixed]),
            "n_omitted_columns": len(self.omitted_columns),
            "is_built": self._is_built,
        }


class ModelLike(Protocol):
    """Structural model protocol for visualization functions."""
    nodes: Dict[int, Node]
    elements: Dict[int, Element]
    loads: List[Load]
    uniform_loads: List[UniformLoad]
    surface_loads: List[SurfaceLoad]
    diaphragms: List[RigidDiaphragm]
    omitted_columns: List[Dict[str, float]]
    _is_built: bool

    def get_summary(self) -> Dict[str, Any]:
        """Return summary statistics."""
        ...


class ViewType(Enum):
    """Visualization view types."""
    PLAN = "plan"           # Top-down XY view
    ELEVATION_X = "elev_x"  # Elevation along X (XZ view)
    ELEVATION_Y = "elev_y"  # Elevation along Y (YZ view)
    VIEW_3D = "3d"          # Isometric 3D view


@dataclass
class VisualizationConfig:
    """Configuration options for FEM visualization.

    Attributes:
        show_nodes: Display node markers
        show_elements: Display element lines
        show_supports: Display support symbols
        show_loads: Display load arrows
        show_labels: Display node/element labels
        node_size: Size of node markers
        element_width: Line width for elements
        support_size: Size of support symbols
        load_scale: Scale factor for load arrow lengths
        colorscale: Color scale for stress/utilization plots
        floor_level: Specific floor level for plan view (None = all floors)
        exaggeration: Displacement exaggeration factor
        show_slabs: Display slab elements
        show_slab_mesh_grid: Display slab mesh grid lines
    """
    show_nodes: bool = True
    show_elements: bool = True
    show_supports: bool = True
    show_loads: bool = True
    show_labels: bool = False
    node_size: int = 8
    element_width: int = 3
    support_size: int = 15
    load_scale: float = 1.0
    colorscale: str = "RdYlGn_r"
    floor_level: Optional[float] = None
    exaggeration: float = 10.0
    show_slabs: bool = True
    show_slab_mesh_grid: bool = True
    show_ghost_columns: bool = True
    grid_spacing: Optional[float] = None
    show_deformed: bool = False
    show_reactions: bool = False
    section_force_type: Optional[str] = None
    section_force_scale: float = 1.0


def build_visualization_data_from_fem_model(model: FEMModel) -> VisualizationData:
    """Create a visualization snapshot from a FEMModel instance.

    Args:
        model: FEMModel to snapshot

    Returns:
        VisualizationData containing model geometry and loads
    """
    return VisualizationData(
        nodes=dict(model.nodes),
        elements=dict(model.elements),
        loads=list(model.loads),
        uniform_loads=list(model.uniform_loads),
        surface_loads=list(model.surface_loads),
        diaphragms=list(model.diaphragms),
        omitted_columns=list(model.omitted_columns),
        source="fem_model",
        _is_built=model._is_built,
    )


def _resolve_ops_module(ops_module: Optional[Any]) -> Any:
    """Resolve OpenSeesPy module, raising ImportError if unavailable."""
    if ops_module is not None:
        return ops_module
    try:
        import openseespy.opensees as ops
    except ImportError as exc:
        raise ImportError(
            "openseespy is required for OpenSees visualization extraction. "
            "Install with: pip install openseespy>=3.5.0"
        ) from exc
    return ops


def _select_backend(backend: VisualizationBackend) -> VisualizationBackend:
    """Select available visualization backend."""
    if backend == VisualizationBackend.AUTO:
        if OPSVIS_AVAILABLE:
            return VisualizationBackend.OPSVIS
        if VFO_AVAILABLE:
            return VisualizationBackend.VFO
        return VisualizationBackend.OPENSEES
    return backend


def _normalize_coords(coords: Any) -> Tuple[float, float, float]:
    """Normalize node coordinates to 3D tuple."""
    if coords is None:
        raise ValueError("Missing node coordinates for visualization")

    if isinstance(coords, (list, tuple, np.ndarray)):
        coord_list = list(coords)
    else:
        coord_list = [coords]

    if len(coord_list) == 2:
        return (float(coord_list[0]), 0.0, float(coord_list[1]))
    if len(coord_list) == 3:
        return (float(coord_list[0]), float(coord_list[1]), float(coord_list[2]))
    raise ValueError(f"Unexpected coordinate length: {len(coord_list)}")


def _resolve_fixed_nodes(ops: Any, config: VisualizationExtractionConfig) -> Set[int]:
    """Resolve fixed node tags from config or OpenSees."""
    if config.fixed_node_tags is not None:
        return set(config.fixed_node_tags)
    if hasattr(ops, "getFixedNodes"):
        try:
            return set(ops.getFixedNodes())
        except Exception:
            return set()
    return set()


def _resolve_pinned_nodes(config: VisualizationExtractionConfig) -> Set[int]:
    """Resolve pinned node tags from config."""
    if config.pinned_node_tags is not None:
        return set(config.pinned_node_tags)
    return set()


def _restraints_for_node(node_tag: int,
                         fixed_nodes: Set[int],
                         pinned_nodes: Set[int]) -> List[int]:
    """Return restraint flags for a node tag."""
    if node_tag in fixed_nodes:
        return [1, 1, 1, 1, 1, 1]
    if node_tag in pinned_nodes:
        return [1, 1, 1, 0, 0, 0]
    return [0, 0, 0, 0, 0, 0]


def _build_nodes_from_data(node_tags: List[int],
                           coord_data: Any,
                           fixed_nodes: Set[int],
                           pinned_nodes: Set[int]) -> Dict[int, Node]:
    """Build Node mapping from coordinates data."""
    nodes: Dict[int, Node] = {}

    if isinstance(coord_data, dict):
        items = coord_data.items()
    else:
        items = zip(node_tags, coord_data)

    for tag, coords in items:
        x, y, z = _normalize_coords(coords)
        nodes[int(tag)] = Node(
            tag=int(tag),
            x=x,
            y=y,
            z=z,
            restraints=_restraints_for_node(int(tag), fixed_nodes, pinned_nodes),
        )
    return nodes


def _build_elements_from_data(elem_tags: List[int],
                              elem_data: Any,
                              default_element_type: ElementType) -> Dict[int, Element]:
    """Build Element mapping from connectivity data."""
    elements: Dict[int, Element] = {}

    if isinstance(elem_data, dict):
        items = elem_data.items()
    else:
        items = zip(elem_tags, elem_data)

    for tag, nodes in items:
        node_list = [int(node_tag) for node_tag in nodes]
        elements[int(tag)] = Element(
            tag=int(tag),
            element_type=default_element_type,
            node_tags=node_list,
            material_tag=0,
            section_tag=None,
        )
    return elements


def _extract_from_opensees(ops: Any,
                           config: VisualizationExtractionConfig) -> VisualizationData:
    """Extract visualization data directly from OpenSeesPy."""
    node_tags = list(ops.getNodeTags())
    elem_tags = list(ops.getEleTags())

    fixed_nodes = _resolve_fixed_nodes(ops, config)
    pinned_nodes = _resolve_pinned_nodes(config)

    nodes: Dict[int, Node] = {}
    for tag in node_tags:
        coords = ops.nodeCoord(tag)
        x, y, z = _normalize_coords(coords)
        nodes[int(tag)] = Node(
            tag=int(tag),
            x=x,
            y=y,
            z=z,
            restraints=_restraints_for_node(int(tag), fixed_nodes, pinned_nodes),
        )

    elements: Dict[int, Element] = {}
    for tag in elem_tags:
        node_list: List[int] = []
        if hasattr(ops, "eleNodes"):
            try:
                node_list = [int(n) for n in ops.eleNodes(tag)]
            except Exception:
                node_list = []
        if not node_list:
            continue
        elements[int(tag)] = Element(
            tag=int(tag),
            element_type=config.default_element_type,
            node_tags=node_list,
            material_tag=0,
            section_tag=None,
        )

    return VisualizationData(
        nodes=nodes,
        elements=elements,
        source="opensees",
        _is_built=True,
    )


def _extract_from_opsvis(ops: Any,
                         config: VisualizationExtractionConfig
                         ) -> Optional[VisualizationData]:
    """Extract visualization data using opsvis (if available)."""
    if not OPSVIS_AVAILABLE or opsv is None:
        return None

    if not hasattr(opsv, "get_model_nodes") or not hasattr(opsv, "get_model_elements"):
        return None

    try:
        node_data = opsv.get_model_nodes()
        elem_data = opsv.get_model_elements()
    except Exception:
        return None

    fixed_nodes = _resolve_fixed_nodes(ops, config)
    pinned_nodes = _resolve_pinned_nodes(config)

    node_tags = list(ops.getNodeTags()) if hasattr(ops, "getNodeTags") else []
    elem_tags = list(ops.getEleTags()) if hasattr(ops, "getEleTags") else []

    nodes = _build_nodes_from_data(node_tags, node_data, fixed_nodes, pinned_nodes)
    elements = _build_elements_from_data(elem_tags, elem_data, config.default_element_type)

    return VisualizationData(
        nodes=nodes,
        elements=elements,
        source="opsvis",
        _is_built=True,
    )


def _extract_from_vfo(ops: Any,
                      config: VisualizationExtractionConfig) -> Optional[VisualizationData]:
    """Extract visualization data using vfo (if available)."""
    if not VFO_AVAILABLE or vfo is None:
        return None

    get_nodes = getattr(vfo, "get_model_nodes", None) or getattr(vfo, "get_nodes", None)
    get_elements = getattr(vfo, "get_model_elements", None) or getattr(vfo, "get_elements", None)

    if get_nodes is None or get_elements is None:
        return None

    try:
        node_data = get_nodes()
        elem_data = get_elements()
    except Exception:
        return None

    fixed_nodes = _resolve_fixed_nodes(ops, config)
    pinned_nodes = _resolve_pinned_nodes(config)

    node_tags = list(ops.getNodeTags()) if hasattr(ops, "getNodeTags") else []
    elem_tags = list(ops.getEleTags()) if hasattr(ops, "getEleTags") else []

    nodes = _build_nodes_from_data(node_tags, node_data, fixed_nodes, pinned_nodes)
    elements = _build_elements_from_data(elem_tags, elem_data, config.default_element_type)

    return VisualizationData(
        nodes=nodes,
        elements=elements,
        source="vfo",
        _is_built=True,
    )


def extract_visualization_data_from_opensees(
    ops_module: Optional[Any] = None,
    config: Optional[VisualizationExtractionConfig] = None,
) -> VisualizationData:
    """Extract visualization data from an OpenSeesPy model.

    Args:
        ops_module: Optional OpenSeesPy module (for testing/mocking)
        config: Extraction configuration

    Returns:
        VisualizationData snapshot
    """
    ops = _resolve_ops_module(ops_module)
    config = config or VisualizationExtractionConfig()

    backend = _select_backend(config.backend)
    if backend == VisualizationBackend.OPSVIS:
        data = _extract_from_opsvis(ops, config)
        if data is not None:
            return data
        if not config.allow_fallback:
            raise RuntimeError("opsvis extraction failed and fallback is disabled")
    elif backend == VisualizationBackend.VFO:
        data = _extract_from_vfo(ops, config)
        if data is not None:
            return data
        if not config.allow_fallback:
            raise RuntimeError("vfo extraction failed and fallback is disabled")

    return _extract_from_opensees(ops, config)


# Color scheme consistent with app.py
COLORS = {
    "column": "#EF4444",        # Red
    "beam": "#3B82F6",          # Blue
    "beam_secondary": "#F97316", # Orange
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


def _check_plotly():
    """Check if plotly is available."""
    if not PLOTLY_AVAILABLE:
        raise ImportError(
            "plotly is required for visualization. "
            "Install with: pip install plotly"
        )


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
    return plotly_colors.sample_colorscale(scale, normalized)[0]


def _get_element_color(element: Element) -> str:
    """Get element color based on element type."""
    if element.element_type == ElementType.COUPLING_BEAM:
        return COLORS["coupling_beam"]
    elif element.element_type == ElementType.SHELL:
        return COLORS["core_wall"]
    else:
        return COLORS["beam"]


def _get_element_endpoints(model: ModelLike, element: Element) -> Tuple[Node, Node]:
    """Get start and end nodes for a 2-node element."""
    if len(element.node_tags) != 2:
        raise ValueError(f"Element {element.tag} must have exactly 2 nodes, has {len(element.node_tags)}")
    node_i = model.nodes[element.node_tags[0]]
    node_j = model.nodes[element.node_tags[1]]
    return node_i, node_j


def _classify_elements(model: ModelLike) -> Dict[str, List[int]]:
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

        # Shell elements (4-node quads) - classify as slabs or core walls
        if elem.element_type in (ElementType.SHELL, ElementType.SHELL_MITC4):
            # Section tag 5 = slab, section tag 4 = core wall
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
            # Differentiate primary (section_tag=1) vs secondary (section_tag=2) beams
            if elem.section_tag == 2:
                classification["beams_secondary"].append(elem.tag)
            else:
                classification["beams"].append(elem.tag)

    return classification


def _get_support_symbol(node: Node) -> Tuple[str, str]:
    """Get marker symbol and color for support node.

    Returns:
        Tuple of (symbol, color) for the support type
    """
    if node.is_fixed:
        return "square", COLORS["support_fixed"]
    elif node.is_pinned:
        return "triangle-up", COLORS["support_pinned"]
    elif any(r == 1 for r in node.restraints):
        return "circle", COLORS["support_roller"]
    return "circle", COLORS["node"]


def _get_floor_elevations(model: ModelLike, tolerance: float = 0.01) -> List[float]:
    """Get unique floor elevations from model nodes.

    Returns:
        Sorted list of unique z-elevations
    """
    elevations: List[float] = []
    for node in model.nodes.values():
        z = node.z
        if not any(abs(z - e) < tolerance for e in elevations):
            elevations.append(z)
    return sorted(elevations)


def calculate_auto_scale_factor(
    forces: "SectionForcesData",
    model: "ModelLike",
    view_direction: str,
    target_ratio: float = 0.5
) -> float:
    """Calculate automatic scale factor for force diagrams.
    
    Goal: Force diagram magnitude should be ~15% of typical element length.
    
    Args:
        forces: SectionForcesData with min/max values
        model: FEMModel with node/element data
        view_direction: 'X' or 'Y' for elevation views
        target_ratio: Target ratio of force diagram to element length
        
    Returns:
        scale_factor: Multiplier for force values to get diagram offset in meters
    """
    if not forces.elements:
        return 0.001
    
    # Get max absolute force value
    max_abs_force = max(abs(forces.min_value), abs(forces.max_value))
    
    if max_abs_force < 1e-6:
        return 0.001
    
    # Estimate typical element length from model
    typical_length = 3.0  # Default fallback (meters)
    
    if model.elements:
        lengths = []
        for elem_id, elem_info in model.elements.items():
            if len(elem_info.node_tags) == 2:
                n_tags = elem_info.node_tags
                if n_tags[0] in model.nodes and n_tags[1] in model.nodes:
                    ni = model.nodes[n_tags[0]]
                    nj = model.nodes[n_tags[1]]
                    dx = nj.x - ni.x
                    dy = nj.y - ni.y
                    dz = nj.z - ni.z
                    L = (dx**2 + dy**2 + dz**2)**0.5
                    if L > 1e-6:
                        lengths.append(L)
        
        if lengths:
            import statistics
            typical_length = statistics.median(lengths)
    
    # Scale factor: (target_diagram_size) / (max_force_value)
    target_diagram_size = typical_length * target_ratio
    scale_factor = target_diagram_size / max_abs_force
    
    print(f"[DEBUG AUTO-SCALE] view={view_direction}, max_force={max_abs_force:.2f}, typical_len={typical_length:.2f}, target_ratio={target_ratio}, scale={scale_factor:.6f}")
    
    return scale_factor


def render_section_forces(
    fig: "go.Figure",
    model: "ModelLike",
    forces: "SectionForcesData",
    view_direction: str,
    scale_factor: float = 0.001
) -> None:
    """Render section force diagrams on Plotly figure (opsvis-style).
    
    Draws unfilled force distribution curves with perpendicular reference lines
    and numerical annotations at element ends.
    
    Args:
        fig: Plotly Figure object to add traces to
        model: FEMModel containing element and node data
        forces: SectionForcesData with extracted force values
        view_direction: 'X' for YZ plane, 'Y' for XZ plane
        scale_factor: Scale factor for force diagram magnitudes
    """
    if not forces.elements:
        return
    
    # Determine coordinate mapping based on view
    if view_direction.upper() == 'X':
        h_idx, v_idx = 1, 2  # Y, Z
    else:  # 'Y'
        h_idx, v_idx = 0, 2  # X, Z
    
    is_first_trace = True
    
    for elem_id, elem_force in forces.elements.items():
        if elem_id not in model.elements:
            continue
        
        elem_info = model.elements[elem_id]
        
        if len(elem_info.node_tags) != 2:
            continue
        
        node_i_tag, node_j_tag = elem_info.node_tags
        
        if node_i_tag not in model.nodes or node_j_tag not in model.nodes:
            continue
        
        node_i = model.nodes[node_i_tag]
        node_j = model.nodes[node_j_tag]
        
        # Element vector
        coords_i = np.array([node_i.x, node_i.y, node_i.z])
        coords_j = np.array([node_j.x, node_j.y, node_j.z])
        L_vec = coords_j - coords_i
        L = np.linalg.norm(L_vec)
        
        if L < 1e-6:
            continue
        
        # Direction cosines
        cosa, cosb, cosc = L_vec / L
        
        # Evaluation points along element
        nep = 17
        xl = np.linspace(0, L, nep)
        
        # Linear interpolation of forces
        force_i = elem_force.force_i
        force_j = elem_force.force_j
        forces_interp = force_i + (force_j - force_i) * (xl / L)
        forces_scaled = forces_interp * scale_factor
        
        # Baseline coordinates (element centerline)
        s_0 = np.zeros((nep, 3))
        s_0[:, 0] = node_i.x + xl * cosa
        s_0[:, 1] = node_i.y + xl * cosb
        s_0[:, 2] = node_i.z + xl * cosc
        
        # Offset coordinates (perpendicular to element)
        s_p = np.copy(s_0)
        
        if view_direction.upper() == 'X':
            s_p[:, 1] -= forces_scaled * cosc
            s_p[:, 2] += forces_scaled * cosb
        else:  # 'Y'
            s_p[:, 0] -= forces_scaled * cosc
            s_p[:, 2] += forces_scaled * cosa
        
        # Extract coordinates for plotting
        h_baseline = s_0[:, h_idx]
        v_baseline = s_0[:, v_idx]
        h_force = s_p[:, h_idx]
        v_force = s_p[:, v_idx]
        
        # Draw force curve (red unfilled line)
        fig.add_trace(go.Scatter(
            x=h_force.tolist(),
            y=v_force.tolist(),
            mode='lines',
            line=dict(color='red', width=1.5),
            name=f'{forces.force_type} [{forces.unit}]',
            showlegend=is_first_trace,
            legendgroup=forces.force_type,
            hoverinfo='skip'
        ))
        
        is_first_trace = False
        
        # Reference lines at ends
        for i in [0, -1]:
            fig.add_trace(go.Scatter(
                x=[h_baseline[i], h_force[i]],
                y=[v_baseline[i], v_force[i]],
                mode='lines',
                line=dict(color='red', width=0.5, dash='dot'),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Annotations at 3 points (ends + midpoint)
        for pos_frac in [0.0, 0.5, 1.0]:
            force_at_pos = force_i + pos_frac * (force_j - force_i)
            
            if abs(force_at_pos) < 1e-9:
                continue
            
            idx = int(pos_frac * (nep - 1))
            
            fig.add_annotation(
                x=h_force[idx],
                y=v_force[idx],
                text=f'{force_at_pos:.1f}',
                showarrow=False,
                font=dict(size=8, color='red'),
                xanchor='left',
                yanchor='bottom'
            )


def render_section_forces_plan(
    fig: "go.Figure",
    model: "ModelLike",
    forces: "SectionForcesData",
    floor_z: float,
    scale_factor: float = 0.001,
    tolerance: float = 0.5
) -> None:
    """Render section force diagrams on Plan View (XY plane).
    
    Only renders elements at the specified floor elevation.
    Forces are drawn perpendicular to elements in the XY plane.
    """
    if not forces.elements:
        return
    
    is_first_trace = True
    
    for elem_id, elem_force in forces.elements.items():
        if elem_id not in model.elements:
            continue
        
        elem_info = model.elements[elem_id]
        
        if len(elem_info.node_tags) != 2:
            continue
        
        node_i_tag, node_j_tag = elem_info.node_tags
        
        if node_i_tag not in model.nodes or node_j_tag not in model.nodes:
            continue
        
        node_i = model.nodes[node_i_tag]
        node_j = model.nodes[node_j_tag]
        
        # Filter by floor elevation - both nodes must be at target floor
        if abs(node_i.z - floor_z) > tolerance or abs(node_j.z - floor_z) > tolerance:
            continue
        
        # Element vector in XY plane
        dx = node_j.x - node_i.x
        dy = node_j.y - node_i.y
        L = np.sqrt(dx**2 + dy**2)
        
        if L < 1e-6:
            continue
        
        # Direction cosines in XY
        cosa = dx / L
        cosb = dy / L
        
        # Perpendicular direction in XY plane (rotate 90 degrees)
        perp_x = -cosb
        perp_y = cosa
        
        # Evaluation points
        nep = 17
        xl = np.linspace(0, L, nep)
        
        # Linear interpolation of forces
        force_i = elem_force.force_i
        force_j = elem_force.force_j
        forces_interp = force_i + (force_j - force_i) * (xl / L)
        forces_scaled = forces_interp * scale_factor
        
        # Baseline coordinates (element centerline)
        x_baseline = node_i.x + xl * cosa
        y_baseline = node_i.y + xl * cosb
        
        # Offset coordinates (perpendicular to element)
        x_force = x_baseline + forces_scaled * perp_x
        y_force = y_baseline + forces_scaled * perp_y
        
        # Draw force curve
        fig.add_trace(go.Scatter(
            x=x_force.tolist(),
            y=y_force.tolist(),
            mode='lines',
            line=dict(color='red', width=1.5),
            name=f'{forces.force_type} [{forces.unit}]',
            showlegend=is_first_trace,
            legendgroup=forces.force_type,
            hoverinfo='skip'
        ))
        
        is_first_trace = False
        
        # Reference lines at ends
        for i in [0, -1]:
            fig.add_trace(go.Scatter(
                x=[x_baseline[i], x_force[i]],
                y=[y_baseline[i], y_force[i]],
                mode='lines',
                line=dict(color='red', width=0.5, dash='dot'),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        # Annotations at 3 points (ends + midpoint)
        for pos_frac in [0.0, 0.5, 1.0]:
            force_at_pos = force_i + pos_frac * (force_j - force_i)
            
            if abs(force_at_pos) < 1e-9:
                continue
            
            idx = int(pos_frac * (nep - 1))
            
            fig.add_annotation(
                x=x_force[idx],
                y=y_force[idx],
                text=f'{force_at_pos:.1f}',
                showarrow=False,
                font=dict(size=8, color='red'),
                xanchor='left',
                yanchor='bottom'
            )


def create_plan_view(model: ModelLike,
                     config: Optional[VisualizationConfig] = None,
                     floor_elevation: Optional[float] = None,
                     utilization: Optional[Dict[int, float]] = None,
                     analysis_result: Optional[Any] = None) -> "go.Figure":
    """Create plan view (XY) visualization of FEM model.

    Args:
        model: Structural model data to visualize
        config: Visualization configuration
        floor_elevation: Specific floor elevation to show (None = top floor)
        utilization: Optional dict of element tag -> utilization ratio for coloring
        analysis_result: Optional analysis results (currently unused, for API compatibility)

    Returns:
        Plotly Figure object
    """
    _check_plotly()
    config = config or VisualizationConfig()

    # Determine floor elevation
    floors = _get_floor_elevations(model)
    if floor_elevation is not None:
        target_z = floor_elevation
    elif floors:
        target_z = floors[-1]  # Top floor
    else:
        target_z = 0.0

    tolerance = 0.01
    classification = _classify_elements(model)

    fig = go.Figure()

    # Get nodes at this floor level
    floor_nodes = {
        tag: node for tag, node in model.nodes.items()
        if abs(node.z - target_z) < tolerance
    }

    use_utilization = utilization is not None and len(utilization) > 0

    # Draw core walls (vertical shell elements intersecting this floor)
    wall_x: List[Optional[float]] = []
    wall_y: List[Optional[float]] = []
    wall_text: List[str] = []
    wall_trace_added = False
    
    for elem_tag in classification["core_walls"]:
        elem = model.elements[elem_tag]
        if len(elem.node_tags) != 4:
            continue
            
        nodes = [model.nodes[tag] for tag in elem.node_tags]
        
        # Check edges (0-1, 1-2, 2-3, 3-0)
        # If an edge lies entirely on the target_z plane, draw it
        for i in range(4):
            n1 = nodes[i]
            n2 = nodes[(i + 1) % 4]
            
            if (abs(n1.z - target_z) < tolerance and 
                abs(n2.z - target_z) < tolerance):
                
                if use_utilization:
                    util = utilization.get(elem_tag, 0.0)
                    color = _get_utilization_color(util, config.colorscale)
                    fig.add_trace(go.Scatter(
                        x=[n1.x, n2.x],
                        y=[n1.y, n2.y],
                        mode='lines',
                        line=dict(color=color, width=config.element_width + 4), # Thicker than beams
                        name='Core Walls',
                        showlegend=not wall_trace_added,
                        customdata=[[elem_tag, util]],
                        hovertemplate=(
                            "Core Wall %{customdata[0]}<br>"
                            "Util: %{customdata[1]:.1%}<extra></extra>"
                        ),
                    ))
                    wall_trace_added = True
                else:
                    wall_x.extend([n1.x, n2.x, None])
                    wall_y.extend([n1.y, n2.y, None])
                    wall_text.append(f"Core Wall {elem_tag}")

    if wall_x and not use_utilization:
        fig.add_trace(go.Scatter(
            x=wall_x,
            y=wall_y,
            mode='lines',
            line=dict(color=COLORS["core_wall"], width=config.element_width + 4),
            name='Core Walls',
            hoverinfo='text',
            text=wall_text * (len(wall_x) // 3) if wall_text else None,
        ))


    # Draw beams (horizontal elements at this floor)
    beam_x: List[Optional[float]] = []
    beam_y: List[Optional[float]] = []
    beam_text: List[str] = []
    beam_label_x: List[float] = []
    beam_label_y: List[float] = []
    beam_label_text: List[str] = []
    beam_trace_added = False

    for elem_tag in classification["beams"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)

        # Check if both nodes are at this floor level
        if (abs(node_i.z - target_z) < tolerance and
            abs(node_j.z - target_z) < tolerance):
            length = float(np.hypot(node_j.x - node_i.x, node_j.y - node_i.y))
            util = utilization.get(elem_tag, 0.0) if use_utilization else 0.0
            hover_text = (
                f"Primary Beam {elem_tag}<br>Length: {length:.2f} m<br>Util: {util:.1%}"
                if use_utilization else f"Primary Beam {elem_tag}<br>Length: {length:.2f} m"
            )

            if use_utilization:
                color = _get_utilization_color(util, config.colorscale)
                fig.add_trace(go.Scatter(
                    x=[node_i.x, node_j.x],
                    y=[node_i.y, node_j.y],
                    mode='lines',
                    line=dict(color=color, width=config.element_width),
                    name='Primary Beams',
                    showlegend=not beam_trace_added,
                    customdata=[[elem_tag, length, util]],
                    hovertemplate=(
                        "Beam %{customdata[0]}<br>"
                        "Length: %{customdata[1]:.2f} m<br>"
                        "Util: %{customdata[2]:.1%}<extra></extra>"
                    ),
                ))
                beam_trace_added = True
            else:
                beam_x.extend([node_i.x, node_j.x, None])
                beam_y.extend([node_i.y, node_j.y, None])
                beam_text.append(hover_text)

            if config.show_labels:
                beam_label_x.append((node_i.x + node_j.x) / 2)
                beam_label_y.append((node_i.y + node_j.y) / 2)
                beam_label_text.append(f"B{elem_tag} {length:.2f} m")

    if beam_x and not use_utilization:
        fig.add_trace(go.Scatter(
            x=beam_x,
            y=beam_y,
            mode='lines',
            line=dict(color=COLORS["beam"], width=config.element_width),
            name='Primary Beams',
            hoverinfo='text',
            text=beam_text * (len(beam_x) // 3) if beam_text else None,
        ))

    if use_utilization and beam_trace_added:
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                colorscale=config.colorscale,
                color=[0.0, 1.2],
                showscale=True,
                cmin=0.0,
                cmax=1.2,
                colorbar=dict(title="Utilization"),
                size=0.1,
            ),
            showlegend=False,
            hoverinfo='none',
        ))

    if config.show_labels and beam_label_x:
        fig.add_trace(go.Scatter(
            x=beam_label_x,
            y=beam_label_y,
            mode='text',
            text=beam_label_text,
            textposition='top center',
            name='Beam Labels',
            showlegend=False,
            hoverinfo='skip',
        ))

    # Draw secondary beams (horizontal elements with section_tag=2)
    sec_beam_x: List[Optional[float]] = []
    sec_beam_y: List[Optional[float]] = []
    sec_beam_text: List[str] = []
    sec_beam_label_x: List[float] = []
    sec_beam_label_y: List[float] = []
    sec_beam_label_text: List[str] = []
    sec_beam_trace_added = False

    for elem_tag in classification["beams_secondary"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)

        # Check if both nodes are at this floor level
        if (abs(node_i.z - target_z) < tolerance and
            abs(node_j.z - target_z) < tolerance):
            length = float(np.hypot(node_j.x - node_i.x, node_j.y - node_i.y))
            util = utilization.get(elem_tag, 0.0) if use_utilization else 0.0
            hover_text = (
                f"Secondary Beam {elem_tag}<br>Length: {length:.2f} m<br>Util: {util:.1%}"
                if use_utilization else f"Secondary Beam {elem_tag}<br>Length: {length:.2f} m"
            )

            if use_utilization:
                color = _get_utilization_color(util, config.colorscale)
                fig.add_trace(go.Scatter(
                    x=[node_i.x, node_j.x],
                    y=[node_i.y, node_j.y],
                    mode='lines',
                    line=dict(color=color, width=config.element_width),
                    name='Secondary Beams',
                    showlegend=not sec_beam_trace_added,
                    customdata=[[elem_tag, length, util]],
                    hovertemplate=(
                        "Secondary Beam %{customdata[0]}<br>"
                        "Length: %{customdata[1]:.2f} m<br>"
                        "Util: %{customdata[2]:.1%}<extra></extra>"
                    ),
                ))
                sec_beam_trace_added = True
            else:
                sec_beam_x.extend([node_i.x, node_j.x, None])
                sec_beam_y.extend([node_i.y, node_j.y, None])
                sec_beam_text.append(hover_text)

            if config.show_labels:
                sec_beam_label_x.append((node_i.x + node_j.x) / 2)
                sec_beam_label_y.append((node_i.y + node_j.y) / 2)
                sec_beam_label_text.append(f"SB{elem_tag} {length:.2f} m")

    if sec_beam_x and not use_utilization:
        fig.add_trace(go.Scatter(
            x=sec_beam_x,
            y=sec_beam_y,
            mode='lines',
            line=dict(color=COLORS["beam_secondary"], width=config.element_width),
            name='Secondary Beams',
            hoverinfo='text',
            text=sec_beam_text * (len(sec_beam_x) // 3) if sec_beam_text else None,
        ))

    if config.show_labels and sec_beam_label_x:
        fig.add_trace(go.Scatter(
            x=sec_beam_label_x,
            y=sec_beam_label_y,
            mode='text',
            text=sec_beam_label_text,
            textposition='top center',
            name='Secondary Beam Labels',
            showlegend=False,
            hoverinfo='skip',
        ))

    # Render ghost columns (omitted columns)
    if config.show_ghost_columns and hasattr(model, 'omitted_columns'):
        ghost_x = []
        ghost_y = []
        ghost_text = []
        
        for ghost in model.omitted_columns:
            # model.omitted_columns is a list of dicts: {"x": x, "y": y, "id": col_id}
            # Or if passing from VisualizationData, it's also a list of dicts or tuples
            # Let's handle dict format as per model_builder.py
            if isinstance(ghost, dict):
                x, y, col_id = ghost.get("x"), ghost.get("y"), ghost.get("id")
            else:
                continue

            if x is not None and y is not None:
                ghost_x.append(x)
                ghost_y.append(y)
                ghost_text.append(f"Omitted: {col_id}")
        
        if ghost_x:
            fig.add_trace(go.Scatter(
                x=ghost_x,
                y=ghost_y,
                mode='markers',
                marker=dict(
                    size=12,
                    color='rgba(150, 150, 150, 0.3)',  # Light grey
                    symbol='circle-open', # Dashed effect via open circle + line width
                    line=dict(color='rgba(100, 100, 100, 0.6)', width=2) 
                ),
                name='Omitted Columns',
                text=ghost_text,
                hoverinfo='text',
                showlegend=True,
            ))


    # Draw coupling beams
    cb_x: List[Optional[float]] = []
    cb_y: List[Optional[float]] = []
    cb_label_x: List[float] = []
    cb_label_y: List[float] = []
    cb_label_text: List[str] = []

    for elem_tag in classification["coupling_beams"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)

        if (abs(node_i.z - target_z) < tolerance and
            abs(node_j.z - target_z) < tolerance):
            cb_x.extend([node_i.x, node_j.x, None])
            cb_y.extend([node_i.y, node_j.y, None])
            if config.show_labels:
                length = float(np.hypot(node_j.x - node_i.x, node_j.y - node_i.y))
                cb_label_x.append((node_i.x + node_j.x) / 2)
                cb_label_y.append((node_i.y + node_j.y) / 2)
                cb_label_text.append(f"CB{elem_tag} {length:.2f} m")

    if cb_x:
        fig.add_trace(go.Scatter(
            x=cb_x,
            y=cb_y,
            mode='lines',
            line=dict(color=COLORS["coupling_beam"], width=config.element_width + 3),
            name='Coupling Beams',
        ))

    if config.show_labels and cb_label_x:
        fig.add_trace(go.Scatter(
            x=cb_label_x,
            y=cb_label_y,
            mode='text',
            text=cb_label_text,
            textposition='bottom center',
            name='Coupling Beam Labels',
            showlegend=False,
            hoverinfo='skip',
        ))

    # Draw columns as markers (intersection points)
    column_points: Dict[Tuple[float, float], Dict[str, Any]] = {}

    for elem_tag in classification["columns"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)

        # Show column at floor level
        for node in [node_i, node_j]:
            if abs(node.z - target_z) < tolerance:
                key = (round(node.x, 4), round(node.y, 4))
                util = utilization.get(elem_tag, 0.0) if use_utilization else 0.0
                if key not in column_points:
                    column_points[key] = {
                        "x": node.x,
                        "y": node.y,
                        "util": util,
                        "labels": [elem_tag],
                    }
                else:
                    column_points[key]["util"] = max(column_points[key]["util"], util)
                    column_points[key]["labels"].append(elem_tag)

    if column_points:
        col_x: List[float] = []
        col_y: List[float] = []
        col_text: List[str] = []
        col_colors: List[str] = []
        col_label_x: List[float] = []
        col_label_y: List[float] = []
        col_label_text: List[str] = []

        for data in column_points.values():
            col_x.append(data["x"])
            col_y.append(data["y"])
            if use_utilization:
                col_colors.append(_get_utilization_color(data["util"], config.colorscale))
                col_text.append(
                    f"Column<br>Util: {data['util']:.1%}<br>"
                    f"({data['x']:.1f}, {data['y']:.1f})"
                )
            else:
                col_colors.append(COLORS["column"])
                col_text.append(f"Column at ({data['x']:.1f}, {data['y']:.1f})")

            if config.show_labels:
                col_label_x.append(data["x"])
                col_label_y.append(data["y"])
                col_label_text.append("C" + ",".join(str(tag) for tag in data["labels"]))

        fig.add_trace(go.Scatter(
            x=col_x,
            y=col_y,
            mode='markers',
            marker=dict(size=config.node_size + 4, color=col_colors, symbol='square'),
            name='Columns',
            text=col_text,
            hoverinfo='text',
        ))

        if config.show_labels and col_label_x:
            fig.add_trace(go.Scatter(
                x=col_label_x,
                y=col_label_y,
                mode='text',
                text=col_label_text,
                textposition='middle right',
                name='Column Labels',
                showlegend=False,
                hoverinfo='skip',
            ))

    # Draw ghost columns (omitted columns near core wall)
    if hasattr(model, 'omitted_columns') and model.omitted_columns:
        ghost_col_x: List[float] = []
        ghost_col_y: List[float] = []
        ghost_col_text: List[str] = []
        
        for ghost_col in model.omitted_columns:
            ghost_col_x.append(ghost_col["x"])
            ghost_col_y.append(ghost_col["y"])
            ghost_col_text.append(f"Column {ghost_col['id']} (Omitted)\u003cbr\u003e({ghost_col['x']:.1f}, {ghost_col['y']:.1f})")
        
        if ghost_col_x:
            fig.add_trace(go.Scatter(
                x=ghost_col_x,
                y=ghost_col_y,
                mode='markers',
                marker=dict(
                    size=config.node_size + 4,
                    color=COLORS["ghost_column"],
                    symbol='square',
                    line=dict(color=COLORS["ghost_column"], width=2),
                ),
                name='Omitted Columns',
                text=ghost_col_text,
                hoverinfo='text',
                opacity=0.5,
            ))

    # Draw slab elements (SHELL_MITC4 quads at this floor level)
    if config.show_slabs and classification["slabs"]:
        slab_fill_added = False
        slab_mesh_added = False
        
        # Collect mesh grid lines (all quad edges batched)
        mesh_x: List[Optional[float]] = []
        mesh_y: List[Optional[float]] = []
        
        for elem_tag in classification["slabs"]:
            elem = model.elements[elem_tag]
            
            # Slab quads have 4 nodes
            if len(elem.node_tags) != 4:
                continue
            
            # Get all 4 nodes
            nodes = [model.nodes[tag] for tag in elem.node_tags]
            
            # Check if all nodes are at this floor level
            if not all(abs(node.z - target_z) < tolerance for node in nodes):
                continue
            
            # Extract node coordinates (CCW order from slab_element.py)
            quad_x = [node.x for node in nodes]
            quad_y = [node.y for node in nodes]
            
            # Get section properties for hover tooltip
            section_tag = elem.section_tag
            thickness = 0.0
            fcu = 0.0
            if section_tag in model.sections:
                section = model.sections[section_tag]
                thickness = section.get('h', 0.0)  # thickness in meters
                # Material fcu estimated from E (E = 3.46*sqrt(fcu) + 3.21 GPa)
                E_gpa = section.get('E', 0) / 1e9
                if E_gpa > 3.21:
                    fcu = ((E_gpa - 3.21) / 3.46) ** 2
            
            # Parse panel ID from element tag pattern (60000 + index)
            # Actual panel ID would need to be stored if available
            panel_id = f"Element {elem_tag}"
            
            # Find surface load for this slab element
            surface_load_kpa = None
            for sload in model.surface_loads:
                if sload.element_tag == elem.tag:
                    # CRITICAL: Convert Pa -> kPa for display
                    surface_load_kpa = sload.pressure / 1000.0
                    break

            # Create hover text
            hover_text = (
                f"Slab {elem_tag}<br>"
                f"Thickness: {thickness:.3f} m<br>"
                f"Panel: {panel_id}<br>"
                f"fcu: {fcu:.1f} MPa"
            )
            
            if surface_load_kpa is not None:
                hover_text += f"<br><b>Surface Load: {surface_load_kpa:.2f} kPa</b>"
            
            # Add filled quad trace (individual trace for hover)
            if config.show_slabs:
                fig.add_trace(go.Scatter(
                    x=quad_x + [quad_x[0]],  # Close the polygon
                    y=quad_y + [quad_y[0]],
                    mode='lines',
                    fill='toself',
                    fillcolor=COLORS["slab"],
                    line=dict(width=0),  # No outline, just fill
                    name='Slabs',
                    showlegend=not slab_fill_added,
                    text=hover_text,
                    hoverinfo='text',
                    opacity=1.0,
                ))
                slab_fill_added = True
            
            # Add edges to mesh grid batch
            if config.show_slab_mesh_grid:
                for i in range(4):
                    mesh_x.extend([nodes[i].x, nodes[(i + 1) % 4].x, None])
                    mesh_y.extend([nodes[i].y, nodes[(i + 1) % 4].y, None])
        
        # Draw mesh grid lines (batched for performance)
        if config.show_slab_mesh_grid and mesh_x:
            fig.add_trace(go.Scatter(
                x=mesh_x,
                y=mesh_y,
                mode='lines',
                line=dict(color='rgba(45, 90, 135, 0.3)', width=1),
                name='Slab Mesh',
                showlegend=not slab_mesh_added,
                hoverinfo='skip',
            ))

    # Draw support nodes (at base level only, but show in plan for reference)
    if config.show_supports:
        support_x: List[float] = []
        support_y: List[float] = []
        support_colors: List[str] = []
        support_symbols: List[str] = []

        for node in model.nodes.values():
            if node.is_fixed or node.is_pinned or any(r == 1 for r in node.restraints):
                # Find if this location has a node at current floor
                has_floor_node = any(
                    abs(n.x - node.x) < tolerance and
                    abs(n.y - node.y) < tolerance and
                    abs(n.z - target_z) < tolerance
                    for n in model.nodes.values()
                )
                if has_floor_node:
                    symbol, color = _get_support_symbol(node)
                    support_x.append(node.x)
                    support_y.append(node.y)
                    support_colors.append(color)
                    support_symbols.append(symbol)

        # Add support markers (unique positions only)
        unique_supports: Dict[Tuple[float, float], Tuple[str, str]] = {}
        for x, y, sym, col in zip(support_x, support_y, support_symbols, support_colors):
            key = (round(x, 3), round(y, 3))
            if key not in unique_supports:
                unique_supports[key] = (sym, col)

        if unique_supports:
            fig.add_trace(go.Scatter(
                x=[k[0] for k in unique_supports.keys()],
                y=[k[1] for k in unique_supports.keys()],
                mode='markers',
                marker=dict(
                    size=config.support_size,
                    color=[v[1] for v in unique_supports.values()],
                    symbol=[v[0] for v in unique_supports.values()],
                    line=dict(width=2, color='white'),
                ),
                name='Supports',
                hoverinfo='name',
            ))

    # Draw nodes
    if config.show_nodes:
        node_x = [n.x for n in floor_nodes.values()]
        node_y = [n.y for n in floor_nodes.values()]
        node_text = [f"Node {tag}<br>({n.x:.2f}, {n.y:.2f})"
                     for tag, n in floor_nodes.items()]

        fig.add_trace(go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers',
            marker=dict(size=config.node_size, color=COLORS["node"], opacity=0.5),
            name='Nodes',
            text=node_text,
            hoverinfo='text',
        ))

    # Draw loads
    if config.show_loads:
        load_x: List[float] = []
        load_y: List[float] = []
        load_arrows_x: List[float] = []
        load_arrows_y: List[float] = []
        load_text: List[str] = []

        for load in model.loads:
            if load.node_tag in floor_nodes:
                node = floor_nodes[load.node_tag]
                fx, fy = load.load_values[0], load.load_values[1]
                fz = load.load_values[2]
                if abs(fx) > 1e-6 or abs(fy) > 1e-6:
                    load_x.append(node.x)
                    load_y.append(node.y)
                    # Scale arrows
                    max_load = max(abs(fx), abs(fy), 1e-6)
                    scale = config.load_scale * 0.5 / max_load
                    load_arrows_x.append(fx * scale)
                    load_arrows_y.append(fy * scale)
                    load_text.append(
                        f"Node Load<br>Fx: {fx:.2f} N<br>Fy: {fy:.2f} N<br>Fz: {fz:.2f} N"
                    )

        if load_x:
            # Draw load arrows using annotations
            for x, y, ax, ay in zip(load_x, load_y, load_arrows_x, load_arrows_y):
                fig.add_annotation(
                    x=x + ax, y=y + ay,
                    ax=x, ay=y,
                    xref='x', yref='y',
                    axref='x', ayref='y',
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1.5,
                    arrowwidth=2,
                    arrowcolor=COLORS["load_lateral"],
                )

            fig.add_trace(go.Scatter(
                x=load_x,
                y=load_y,
                mode='markers',
                marker=dict(size=config.node_size + 2, color=COLORS["load_lateral"],
                            symbol='triangle-up'),
                name='Point Loads',
                text=load_text,
                hoverinfo='text',
            ))

        # Uniform load markers along elements
        if model.uniform_loads:
            uload_x: List[float] = []
            uload_y: List[float] = []
            uload_text: List[str] = []
            uload_colors: List[str] = []

            for uniform_load in model.uniform_loads:
                elem = model.elements.get(uniform_load.element_tag)
                if elem is None:
                    continue
                node_i, node_j = _get_element_endpoints(model, elem)
                if (abs(node_i.z - target_z) < tolerance and
                    abs(node_j.z - target_z) < tolerance):
                    mid_x = (node_i.x + node_j.x) / 2
                    mid_y = (node_i.y + node_j.y) / 2
                    uload_x.append(mid_x)
                    uload_y.append(mid_y)
                    uload_text.append(
                        f"Uniform Load<br>Type: {uniform_load.load_type}<br>"
                        f"Mag: {uniform_load.magnitude:.2f}"
                    )
                    color = COLORS["load_gravity"]
                    if uniform_load.load_type.lower() in ("x", "y"):
                        color = COLORS["load_lateral"]
                    uload_colors.append(color)

            if uload_x:
                fig.add_trace(go.Scatter(
                    x=uload_x,
                    y=uload_y,
                    mode='markers',
                    marker=dict(size=config.node_size, color=uload_colors, symbol='triangle-down'),
                    name='Uniform Loads',
                    text=uload_text,
                    hoverinfo='text',
                ))

    if config.section_force_type and analysis_result:
        from src.fem.results_processor import ResultsProcessor
        
        forces = ResultsProcessor.extract_section_forces(
            result=analysis_result,
            model=model,
            force_type=config.section_force_type
        )
        
        auto_scale = calculate_auto_scale_factor(
            forces=forces,
            model=model,
            view_direction="PLAN",
            target_ratio=0.5
        )
        
        if config.section_force_scale < 0:
            scale = auto_scale
        else:
            scale = auto_scale * config.section_force_scale
        
        render_section_forces_plan(
            fig=fig,
            model=model,
            forces=forces,
            floor_z=target_z,
            scale_factor=scale
        )

    # Layout
    fig.update_layout(
        title=f"Plan View (Floor Z = {target_z:.2f} m)",
        xaxis_title="X (m)",
        yaxis_title="Y (m)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(l=50, r=50, t=50, b=100),
        hovermode='closest',
        plot_bgcolor='white',
        xaxis=dict(
            scaleanchor='y',
            scaleratio=1,
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='gray',
            dtick=config.grid_spacing,
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='gray',
            dtick=config.grid_spacing,
        ),
    )

    return fig


def create_elevation_view(model: ModelLike,
                          config: Optional[VisualizationConfig] = None,
                          view_direction: str = "X",
                          gridline_coord: Optional[float] = None,
                          utilization: Optional[Dict[int, float]] = None,
                          displaced_nodes: Optional[Dict[int, Tuple[float, float, float]]] = None,
                          reactions: Optional[Dict[int, List[float]]] = None,
                          analysis_result: Optional[Any] = None) -> "go.Figure":
    """Create elevation view visualization of FEM model.

    Args:
        model: Structural model data to visualize
        config: Visualization configuration
        view_direction: "X" for XZ view (looking along Y), "Y" for YZ view (looking along X)
        gridline_coord: Optional gridline coordinate filter. When view_direction="X",
                       this filters by Y coordinate. When view_direction="Y", filters by X.
                       If None, all elements are projected (flattened).
        utilization: Optional dict of element tag -> utilization ratio for coloring
        displaced_nodes: Optional dict of node tag -> (dx, dy, dz) displacements
        reactions: Optional dict of node tag -> [Fx, Fy, Fz, Mx, My, Mz] reactions
        analysis_result: Optional analysis results (for API compatibility)

    Returns:
        Plotly Figure object
    """
    _check_plotly()
    config = config or VisualizationConfig()

    classification = _classify_elements(model)
    view_direction = view_direction.upper()

    fig = go.Figure()
    use_utilization = utilization is not None and len(utilization) > 0
    
    # Gridline filtering tolerance (m)
    gridline_tol = 0.5

    # Select coordinate mapping based on view direction
    if view_direction == "X":
        get_h = lambda n: n.x  # Horizontal axis
        get_v = lambda n: n.z  # Vertical axis
        get_filter_coord = lambda n: n.y  # Filter by Y when viewing XZ plane
        h_label = "X (m)"
    else:
        get_h = lambda n: n.y
        get_v = lambda n: n.z
        get_filter_coord = lambda n: n.x  # Filter by X when viewing YZ plane
        h_label = "Y (m)"
    
    def element_passes_filter(node_i: Node, node_j: Node) -> bool:
        """Check if element passes gridline filter."""
        if gridline_coord is None:
            return True  # No filter, show all
        # Check if both nodes are on or near the gridline
        coord_i = get_filter_coord(node_i)
        coord_j = get_filter_coord(node_j)
        return (abs(coord_i - gridline_coord) < gridline_tol and 
                abs(coord_j - gridline_coord) < gridline_tol)

    # Draw columns (vertical elements)
    col_h: List[Optional[float]] = []
    col_v: List[Optional[float]] = []
    col_text: List[str] = []
    col_trace_added = False

    for elem_tag in classification["columns"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)
        
        if not element_passes_filter(node_i, node_j):
            continue

        if use_utilization:
            util = utilization.get(elem_tag, 0.0)
            color = _get_utilization_color(util, config.colorscale)
            fig.add_trace(go.Scatter(
                x=[get_h(node_i), get_h(node_j)],
                y=[get_v(node_i), get_v(node_j)],
                mode='lines',
                line=dict(color=color, width=config.element_width + 1),
                name='Columns',
                showlegend=not col_trace_added,
                customdata=[[elem_tag, util]],
                hovertemplate=(
                    "Column %{customdata[0]}<br>"
                    "Util: %{customdata[1]:.1%}<extra></extra>"
                ),
            ))
            col_trace_added = True
        else:
            col_h.extend([get_h(node_i), get_h(node_j), None])
            col_v.extend([get_v(node_i), get_v(node_j), None])
            col_text.append(f"Column {elem_tag}")

    if col_h and not use_utilization:
        fig.add_trace(go.Scatter(
            x=col_h,
            y=col_v,
            mode='lines',
            line=dict(color=COLORS["column"], width=config.element_width + 1),
            name='Columns',
            text=col_text * (len(col_h) // 3) if col_text else None,
            hoverinfo='text' if col_text else 'skip',
        ))

    # Render ghost columns (omitted columns)
    if config.show_ghost_columns and hasattr(model, 'omitted_columns') and not use_utilization:
        ghost_h: List[Optional[float]] = []
        ghost_v: List[Optional[float]] = []
        ghost_text: List[str] = []
        
        # Determine vertical extent from existing nodes
        if model.nodes:
            z_values = [n.z for n in model.nodes.values()]
            z_min, z_max = min(z_values), max(z_values)
        else:
            z_min, z_max = 0.0, 0.0

        for ghost in model.omitted_columns:
            if isinstance(ghost, dict):
                gx, gy, gid = ghost.get("x"), ghost.get("y"), ghost.get("id")
            else:
                continue
            
            if gx is not None and gy is not None:
                filter_val = gy if view_direction == "X" else gx
                if gridline_coord is not None and abs(filter_val - gridline_coord) >= gridline_tol:
                    continue
                    
                h_val = gx if view_direction == "X" else gy
                ghost_h.extend([h_val, h_val, None])
                ghost_v.extend([z_min, z_max, None])
                ghost_text.append(f"Omitted Column {gid}")
        
        if ghost_h:
            fig.add_trace(go.Scatter(
                x=ghost_h,
                y=ghost_v,
                mode='lines',
                line=dict(color='rgba(150, 150, 150, 0.4)', width=config.element_width, dash='dash'),
                name='Omitted Columns',
                text=ghost_text * (len(ghost_h) // 3),
                hoverinfo='text',
                showlegend=True,
            ))

    # Draw beams (horizontal elements)
    beam_h: List[Optional[float]] = []
    beam_v: List[Optional[float]] = []
    beam_trace_added = False

    for elem_tag in classification["beams"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)
        
        if not element_passes_filter(node_i, node_j):
            continue

        # Project beams based on view direction
        if view_direction == "X":
            # Show beams along X direction (same Y coordinate)
            if abs(node_i.y - node_j.y) < 0.01:
                if use_utilization:
                    util = utilization.get(elem_tag, 0.0)
                    color = _get_utilization_color(util, config.colorscale)
                    fig.add_trace(go.Scatter(
                        x=[get_h(node_i), get_h(node_j)],
                        y=[get_v(node_i), get_v(node_j)],
                        mode='lines',
                        line=dict(color=color, width=config.element_width),
                        name='Beams',
                        showlegend=not beam_trace_added,
                        customdata=[[elem_tag, util]],
                        hovertemplate=(
                            "Beam %{customdata[0]}<br>"
                            "Util: %{customdata[1]:.1%}<extra></extra>"
                        ),
                    ))
                    beam_trace_added = True
                else:
                    beam_h.extend([get_h(node_i), get_h(node_j), None])
                    beam_v.extend([get_v(node_i), get_v(node_j), None])
        else:
            # Show beams along Y direction (same X coordinate)
            if abs(node_i.x - node_j.x) < 0.01:
                if use_utilization:
                    util = utilization.get(elem_tag, 0.0)
                    color = _get_utilization_color(util, config.colorscale)
                    fig.add_trace(go.Scatter(
                        x=[get_h(node_i), get_h(node_j)],
                        y=[get_v(node_i), get_v(node_j)],
                        mode='lines',
                        line=dict(color=color, width=config.element_width),
                        name='Beams',
                        showlegend=not beam_trace_added,
                        customdata=[[elem_tag, util]],
                        hovertemplate=(
                            "Beam %{customdata[0]}<br>"
                            "Util: %{customdata[1]:.1%}<extra></extra>"
                        ),
                    ))
                    beam_trace_added = True
                else:
                    beam_h.extend([get_h(node_i), get_h(node_j), None])
                    beam_v.extend([get_v(node_i), get_v(node_j), None])

    if beam_h and not use_utilization:
        fig.add_trace(go.Scatter(
            x=beam_h,
            y=beam_v,
            mode='lines',
            line=dict(color=COLORS["beam"], width=config.element_width),
            name='Primary Beams',
        ))

    # Draw coupling beams
    cb_h: List[Optional[float]] = []
    cb_v: List[Optional[float]] = []

    for elem_tag in classification["coupling_beams"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)
        
        if not element_passes_filter(node_i, node_j):
            continue
            
        cb_h.extend([get_h(node_i), get_h(node_j), None])
        cb_v.extend([get_v(node_i), get_v(node_j), None])

    if cb_h:
        fig.add_trace(go.Scatter(
            x=cb_h,
            y=cb_v,
            mode='lines',
            line=dict(color=COLORS["coupling_beam"], width=config.element_width + 2),
            name='Coupling Beams',
        ))

    # Draw supports at base
    if config.show_supports:
        support_h: List[float] = []
        support_v: List[float] = []
        support_symbols: List[str] = []
        support_colors: List[str] = []

        for node in model.nodes.values():
            if node.z < 0.01 and (node.is_fixed or node.is_pinned or
                                   any(r == 1 for r in node.restraints)):
                symbol, color = _get_support_symbol(node)
                support_h.append(get_h(node))
                support_v.append(get_v(node))
                support_symbols.append(symbol)
                support_colors.append(color)

        if support_h:
            fig.add_trace(go.Scatter(
                x=support_h,
                y=support_v,
                mode='markers',
                marker=dict(
                    size=config.support_size,
                    color=support_colors,
                    symbol=support_symbols,
                    line=dict(width=2, color='white'),
                ),
                name='Supports',
            ))

    # Draw floor lines with optional utilization
    floors = _get_floor_elevations(model)
    h_min = min(n.x if view_direction == "X" else n.y for n in model.nodes.values())
    h_max = max(n.x if view_direction == "X" else n.y for n in model.nodes.values())

    if use_utilization:
        floor_utilization: Dict[float, List[float]] = {}
        for elem_tag, util in utilization.items():
            elem = model.elements.get(elem_tag)
            if elem is None or len(elem.node_tags) < 2:
                continue
            node_i, node_j = _get_element_endpoints(model, elem)
            if abs(node_i.z - node_j.z) < 0.01:
                level = round(node_i.z, 4)
                floor_utilization.setdefault(level, []).append(util)

        first_floor = True
        for floor_z in floors:
            level = round(floor_z, 4)
            util_values = floor_utilization.get(level, [])
            avg_util = sum(util_values) / len(util_values) if util_values else 0.0
            color = _get_utilization_color(avg_util, config.colorscale)
            fig.add_trace(go.Scatter(
                x=[h_min - 0.5, h_max + 0.5],
                y=[floor_z, floor_z],
                mode='lines',
                line=dict(color=color, width=2, dash="dot"),
                name='Floor Utilization',
                showlegend=first_floor,
                customdata=[[floor_z, avg_util]],
                hovertemplate="Floor Z=%{customdata[0]:.2f} m<br>Util: %{customdata[1]:.1%}<extra></extra>",
            ))
            first_floor = False
    else:
        for floor_z in floors:
            fig.add_shape(
                type="line",
                x0=h_min - 0.5, y0=floor_z,
                x1=h_max + 0.5, y1=floor_z,
                line=dict(color="lightgray", width=1, dash="dot"),
            )

    if use_utilization:
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                colorscale=config.colorscale,
                color=[0.0, 1.2],
                showscale=True,
                cmin=0.0,
                cmax=1.2,
                colorbar=dict(title="Utilization"),
                size=0.1,
            ),
            showlegend=False,
            hoverinfo='none',
        ))

    # Deflected shape overlay
    if displaced_nodes:
        def_h: List[Optional[float]] = []
        def_v: List[Optional[float]] = []

        def get_deflected(node: Node) -> Tuple[float, float]:
            dx, dy, dz = displaced_nodes.get(node.tag, (0.0, 0.0, 0.0))
            if view_direction == "X":
                return (node.x + dx * config.exaggeration,
                        node.z + dz * config.exaggeration)
            return (node.y + dy * config.exaggeration,
                    node.z + dz * config.exaggeration)

        for elem_group in ("columns", "beams", "coupling_beams"):
            for elem_tag in classification[elem_group]:
                elem = model.elements[elem_tag]
                node_i, node_j = _get_element_endpoints(model, elem)
                hi, vi = get_deflected(node_i)
                hj, vj = get_deflected(node_j)
                def_h.extend([hi, hj, None])
                def_v.extend([vi, vj, None])

        if def_h:
            fig.add_trace(go.Scatter(
                x=def_h,
                y=def_v,
                mode='lines',
                line=dict(color="rgba(239, 68, 68, 0.7)", width=2, dash="dash"),
                name='Deflected Shape',
            ))

    # Reaction forces at supports
    if reactions and config.show_supports:
        base_nodes = [n for n in model.nodes.values() if n.z < 0.01]
        max_reaction = 1e-6
        for node in base_nodes:
            reaction = reactions.get(node.tag)
            if reaction:
                rx = reaction[0] if view_direction == "X" else reaction[1]
                rz = reaction[2]
                max_reaction = max(max_reaction, abs(rx), abs(rz))

        scale = config.load_scale * 0.5 / max_reaction
        reaction_x: List[float] = []
        reaction_y: List[float] = []
        reaction_text: List[str] = []

        for node in base_nodes:
            reaction = reactions.get(node.tag)
            if not reaction:
                continue
            rx = reaction[0] if view_direction == "X" else reaction[1]
            rz = reaction[2]
            if abs(rx) < 1e-6 and abs(rz) < 1e-6:
                continue
            x0 = get_h(node)
            y0 = get_v(node)
            x1 = x0 + rx * scale
            y1 = y0 + rz * scale
            fig.add_annotation(
                x=x1, y=y1,
                ax=x0, ay=y0,
                xref='x', yref='y',
                axref='x', ayref='y',
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor=COLORS["support_fixed"],
            )
            reaction_x.append(x0)
            reaction_y.append(y0)
            reaction_text.append(
                f"Reaction<br>Fx: {reaction[0]:.2f} N<br>"
                f"Fy: {reaction[1]:.2f} N<br>Fz: {reaction[2]:.2f} N"
            )

        if reaction_x:
            fig.add_trace(go.Scatter(
                x=reaction_x,
                y=reaction_y,
                mode='markers',
                marker=dict(size=config.node_size + 2, color=COLORS["support_fixed"],
                            symbol='triangle-down'),
                name='Reactions',
                text=reaction_text,
                hoverinfo='text',
            ))

    if config.section_force_type and analysis_result:
        from src.fem.results_processor import ResultsProcessor
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(f"[FORCE_DIAG_ELEV] force_type={config.section_force_type}")
        _logger.warning(f"[FORCE_DIAG_ELEV] element_forces_count={len(getattr(analysis_result, 'element_forces', {}))}")
        
        forces = ResultsProcessor.extract_section_forces(
            result=analysis_result,
            model=model,
            force_type=config.section_force_type
        )
        _logger.warning(f"[FORCE_DIAG_ELEV] extracted_elements={len(forces.elements)}")
        
        auto_scale = calculate_auto_scale_factor(
            forces=forces,
            model=model,
            view_direction=view_direction,
            target_ratio=0.5
        )
        
        if config.section_force_scale < 0:
            scale = auto_scale
        else:
            scale = auto_scale * config.section_force_scale
        
        render_section_forces(
            fig=fig,
            model=model,
            forces=forces,
            view_direction=view_direction,
            scale_factor=scale
        )

    # Layout
    fig.update_layout(
        title=f"Elevation View ({view_direction} Direction)",
        xaxis_title=h_label,
        yaxis_title="Z (m)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(l=50, r=50, t=50, b=100),
        hovermode='closest',
        plot_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='gray',
            dtick=config.grid_spacing,
        ),
        yaxis=dict(
            scaleanchor='x',
            scaleratio=1,
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='gray',
            dtick=config.grid_spacing,
        ),
    )

    return fig


def create_3d_view(model: ModelLike,
                   config: Optional[VisualizationConfig] = None,
                   utilization: Optional[Dict[int, float]] = None,
                   displaced_nodes: Optional[Dict[int, Tuple[float, float, float]]] = None,
                   reactions: Optional[Dict[int, List[float]]] = None) -> "go.Figure":
    """Create 3D isometric visualization of FEM model.

    Args:
        model: Structural model data to visualize
        config: Visualization configuration
        utilization: Optional dict of element tag -> utilization ratio for coloring
        displaced_nodes: Optional dict of node tag -> (dx, dy, dz) displacements
        reactions: Optional dict of node tag -> [Fx, Fy, Fz, Mx, My, Mz] reactions

    Returns:
        Plotly Figure object
    """
    _check_plotly()
    config = config or VisualizationConfig()

    classification = _classify_elements(model)
    use_utilization = utilization is not None and len(utilization) > 0

    fig = go.Figure()

    # Helper to get node coordinates (original)
    def get_coords(node: Node) -> Tuple[float, float, float]:
        return (node.x, node.y, node.z)

    # Helper to get deflected coordinates
    def get_deflected_coords(node: Node) -> Tuple[float, float, float]:
        if displaced_nodes and node.tag in displaced_nodes:
            dx, dy, dz = displaced_nodes[node.tag]
            return (
                node.x + dx * config.exaggeration,
                node.y + dy * config.exaggeration,
                node.z + dz * config.exaggeration,
            )
        return (node.x, node.y, node.z)

    # Draw columns
    col_x: List[Optional[float]] = []
    col_y: List[Optional[float]] = []
    col_z: List[Optional[float]] = []
    col_trace_added = False

    for elem_tag in classification["columns"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)
        xi, yi, zi = get_coords(node_i)
        xj, yj, zj = get_coords(node_j)

        if use_utilization:
            util = utilization.get(elem_tag, 0.0)
            color = _get_utilization_color(util, config.colorscale)
            fig.add_trace(go.Scatter3d(
                x=[xi, xj],
                y=[yi, yj],
                z=[zi, zj],
                mode='lines',
                line=dict(color=color, width=config.element_width + 2),
                name='Columns',
                showlegend=not col_trace_added,
                customdata=[[elem_tag, util]],
                hovertemplate=(
                    "Column %{customdata[0]}<br>"
                    "Util: %{customdata[1]:.1%}<extra></extra>"
                ),
            ))
            col_trace_added = True
        else:
            col_x.extend([xi, xj, None])
            col_y.extend([yi, yj, None])
            col_z.extend([zi, zj, None])

    if col_x and not use_utilization:
        fig.add_trace(go.Scatter3d(
            x=col_x,
            y=col_y,
            z=col_z,
            mode='lines',
            line=dict(color=COLORS["column"], width=config.element_width + 2),
            name='Columns',
        ))

    # Draw core walls (vertical shell elements) - Wireframe
    wall_x: List[Optional[float]] = []
    wall_y: List[Optional[float]] = []
    wall_z: List[Optional[float]] = []
    wall_trace_added = False

    for elem_tag in classification["core_walls"]:
        elem = model.elements[elem_tag]
        if len(elem.node_tags) != 4:
            continue
            
        nodes = [model.nodes[tag] for tag in elem.node_tags]
        # Draw quad outline (0-1-2-3-0)
        # We can just draw the loop for each element
        
        # Collect coordinates
        wx = [n.x for n in nodes] + [nodes[0].x] + [None]
        wy = [n.y for n in nodes] + [nodes[0].y] + [None]
        wz = [n.z for n in nodes] + [nodes[0].z] + [None]
        
        if use_utilization:
            util = utilization.get(elem_tag, 0.0)
            color = _get_utilization_color(util, config.colorscale)
            fig.add_trace(go.Scatter3d(
                x=wx[:-1], # plotly handles connected lines; we generally use None to separate, but here we can add trace per element if coloring/performance permits.
                           # Optimization: separating traces is heavy for many elements.
                           # Better: single trace with None separators if same color.
                           # For utilization, we MUST use segments or individual traces.
                           # Let's use the individual trace approach for utilization (slower but correct) or Line segments with custom colors? Plotly Scatter3d single trace doesn't support varying line colors easily without a specialized array, which is complex.
                           # Given standard model size, adding traces per wall element is acceptable (couple hundred elements max).
                y=wy[:-1],
                z=wz[:-1],
                mode='lines',
                line=dict(color=color, width=config.element_width),
                name='Core Walls',
                showlegend=not wall_trace_added,
                customdata=[[elem_tag, util]],
                hovertemplate=(
                    "Core Wall %{customdata[0]}<br>"
                    "Util: %{customdata[1]:.1%}<extra></extra>"
                ),
            ))
            wall_trace_added = True
        else:
            wall_x.extend(wx)
            wall_y.extend(wy)
            wall_z.extend(wz)

    if wall_x and not use_utilization:
        fig.add_trace(go.Scatter3d(
            x=wall_x,
            y=wall_y,
            z=wall_z,
            mode='lines',
            line=dict(color=COLORS["core_wall"], width=config.element_width),
            name='Core Walls',
        ))

    # Render ghost columns (omitted columns)
    if config.show_ghost_columns and hasattr(model, 'omitted_columns') and not use_utilization:
        ghost_x: List[Optional[float]] = []
        ghost_y: List[Optional[float]] = []
        ghost_z: List[Optional[float]] = []
        
        # Determine vertical extent from existing nodes
        if model.nodes:
            z_values = [n.z for n in model.nodes.values()]
            z_min, z_max = min(z_values), max(z_values)
        else:
            z_min, z_max = 0.0, 0.0
            
        for ghost in model.omitted_columns:
            if isinstance(ghost, dict):
                gx, gy, gid = ghost.get("x"), ghost.get("y"), ghost.get("id")
            else:
                continue
                
            if gx is not None and gy is not None:
                ghost_x.extend([gx, gx, None])
                ghost_y.extend([gy, gy, None])
                ghost_z.extend([z_min, z_max, None])
        
        if ghost_x:
            fig.add_trace(go.Scatter3d(
                x=ghost_x,
                y=ghost_y,
                z=ghost_z,
                mode='lines',
                line=dict(color='rgba(150, 150, 150, 0.4)', width=config.element_width, dash='dash'),
                name='Omitted Columns',
                showlegend=True,
                hoverinfo='name',
            ))

    # Draw beams
    beam_x: List[Optional[float]] = []
    beam_y: List[Optional[float]] = []
    beam_z: List[Optional[float]] = []
    beam_trace_added = False

    for elem_tag in classification["beams"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)
        xi, yi, zi = get_coords(node_i)
        xj, yj, zj = get_coords(node_j)

        if use_utilization:
            util = utilization.get(elem_tag, 0.0)
            color = _get_utilization_color(util, config.colorscale)
            fig.add_trace(go.Scatter3d(
                x=[xi, xj],
                y=[yi, yj],
                z=[zi, zj],
                mode='lines',
                line=dict(color=color, width=config.element_width),
                name='Primary Beams',
                showlegend=not beam_trace_added,
                customdata=[[elem_tag, util]],
                hovertemplate=(
                    "Beam %{customdata[0]}<br>"
                    "Util: %{customdata[1]:.1%}<extra></extra>"
                ),
            ))
            beam_trace_added = True
        else:
            beam_x.extend([xi, xj, None])
            beam_y.extend([yi, yj, None])
            beam_z.extend([zi, zj, None])

    if beam_x and not use_utilization:
        fig.add_trace(go.Scatter3d(
            x=beam_x,
            y=beam_y,
            z=beam_z,
            mode='lines',
            line=dict(color=COLORS["beam"], width=config.element_width),
            name='Primary Beams',
        ))

    # Draw secondary beams
    sec_beam_x: List[Optional[float]] = []
    sec_beam_y: List[Optional[float]] = []
    sec_beam_z: List[Optional[float]] = []
    sec_beam_trace_added = False

    for elem_tag in classification["beams_secondary"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)
        xi, yi, zi = get_coords(node_i)
        xj, yj, zj = get_coords(node_j)

        if use_utilization:
            util = utilization.get(elem_tag, 0.0)
            color = _get_utilization_color(util, config.colorscale)
            fig.add_trace(go.Scatter3d(
                x=[xi, xj],
                y=[yi, yj],
                z=[zi, zj],
                mode='lines',
                line=dict(color=color, width=config.element_width),
                name='Secondary Beams',
                showlegend=not sec_beam_trace_added,
                customdata=[[elem_tag, util]],
                hovertemplate=(
                    "Secondary Beam %{customdata[0]}<br>"
                    "Util: %{customdata[1]:.1%}<extra></extra>"
                ),
            ))
            sec_beam_trace_added = True
        else:
            sec_beam_x.extend([xi, xj, None])
            sec_beam_y.extend([yi, yj, None])
            sec_beam_z.extend([zi, zj, None])

    if sec_beam_x and not use_utilization:
        fig.add_trace(go.Scatter3d(
            x=sec_beam_x,
            y=sec_beam_y,
            z=sec_beam_z,
            mode='lines',
            line=dict(color=COLORS["beam_secondary"], width=config.element_width),
            name='Secondary Beams',
        ))


    # Draw coupling beams
    cb_x: List[Optional[float]] = []
    cb_y: List[Optional[float]] = []
    cb_z: List[Optional[float]] = []

    for elem_tag in classification["coupling_beams"]:
        elem = model.elements[elem_tag]
        node_i, node_j = _get_element_endpoints(model, elem)
        xi, yi, zi = get_coords(node_i)
        xj, yj, zj = get_coords(node_j)

        cb_x.extend([xi, xj, None])
        cb_y.extend([yi, yj, None])
        cb_z.extend([zi, zj, None])

    if cb_x:
        fig.add_trace(go.Scatter3d(
            x=cb_x,
            y=cb_y,
            z=cb_z,
            mode='lines',
            line=dict(color=COLORS["coupling_beam"], width=config.element_width + 3),
            name='Coupling Beams',
        ))

    # Draw slab elements (SHELL_MITC4 quads as 3D mesh surfaces)
    if config.show_slabs and classification["slabs"]:
        # Collect all unique vertices and build face index list
        vertices: Dict[int, Tuple[float, float, float]] = {}
        faces: List[Tuple[int, int, int]] = []  # Triangles for Mesh3d
        
        for elem_tag in classification["slabs"]:
            elem = model.elements[elem_tag]
            
            # Slab quads have 4 nodes
            if len(elem.node_tags) != 4:
                continue
            
            # Get quad vertices
            node_tags = elem.node_tags
            for ntag in node_tags:
                if ntag not in vertices:
                    node = model.nodes[ntag]
                    vertices[ntag] = get_coords(node)
            
            # Create vertex index list for this quad
            v_indices = [list(vertices.keys()).index(ntag) for ntag in node_tags]
            
            # Triangulate quad: split into two triangles
            # Triangle 1: v0, v1, v2
            faces.append((v_indices[0], v_indices[1], v_indices[2]))
            # Triangle 2: v0, v2, v3
            faces.append((v_indices[0], v_indices[2], v_indices[3]))
       #  Build separate  vertex lists for Mesh3d
        v_list = list(vertices.values())
        if v_list and faces:
            x_vertices = [v[0] for v in v_list]
            y_vertices = [v[1] for v in v_list]
            z_vertices = [v[2] for v in v_list]
            
            # Unpack face indices
            i_faces = [f[0] for f in faces]
            j_faces = [f[1] for f in faces]
            k_faces = [f[2] for f in faces]
            
            fig.add_trace(go.Mesh3d(
                x=x_vertices,
                y=y_vertices,
                z=z_vertices,
                i=i_faces,
                j=j_faces,
                k=k_faces,
                color=COLORS["slab"],
                opacity=0.3,
                name='Slabs',
                showlegend=True,
                hoverinfo='name',
            ))

    # Draw supports
    if config.show_supports:
        support_x: List[float] = []
        support_y: List[float] = []
        support_z: List[float] = []
        support_colors: List[str] = []
        support_symbols: List[str] = []

        for node in model.nodes.values():
            if node.is_fixed or node.is_pinned or any(r == 1 for r in node.restraints):
                x, y, z = get_coords(node)
                symbol, color = _get_support_symbol(node)
                support_x.append(x)
                support_y.append(y)
                support_z.append(z)
                support_colors.append(color)
                support_symbols.append(symbol)

        if support_x:
            fig.add_trace(go.Scatter3d(
                x=support_x,
                y=support_y,
                z=support_z,
                mode='markers',
                marker=dict(
                    size=config.support_size // 2,
                    color=support_colors,
                    symbol=['square' if s == 'square' else 'circle' for s in support_symbols],
                ),
                name='Supports',
            ))

    # Deflected shape overlay
    if displaced_nodes:
        def_x: List[Optional[float]] = []
        def_y: List[Optional[float]] = []
        def_z: List[Optional[float]] = []

        for elem_group in ("columns", "beams", "coupling_beams"):
            for elem_tag in classification[elem_group]:
                elem = model.elements[elem_tag]
                node_i, node_j = _get_element_endpoints(model, elem)
                xi, yi, zi = get_deflected_coords(node_i)
                xj, yj, zj = get_deflected_coords(node_j)
                def_x.extend([xi, xj, None])
                def_y.extend([yi, yj, None])
                def_z.extend([zi, zj, None])

        if def_x:
            fig.add_trace(go.Scatter3d(
                x=def_x,
                y=def_y,
                z=def_z,
                mode='lines',
                line=dict(color="rgba(239, 68, 68, 0.7)", width=config.element_width),
                name='Deflected Shape',
            ))

    # Reaction forces at supports
    if reactions and config.show_supports:
        base_nodes = [n for n in model.nodes.values() if n.z < 0.01]
        max_reaction = 1e-6
        for node in base_nodes:
            reaction = reactions.get(node.tag)
            if reaction:
                max_reaction = max(max_reaction, abs(reaction[0]), abs(reaction[1]),
                                   abs(reaction[2]))
        scale = config.load_scale * 0.5 / max_reaction
        r_x: List[Optional[float]] = []
        r_y: List[Optional[float]] = []
        r_z: List[Optional[float]] = []
        r_text: List[str] = []

        for node in base_nodes:
            reaction = reactions.get(node.tag)
            if not reaction:
                continue
            fx, fy, fz = reaction[0], reaction[1], reaction[2]
            if abs(fx) < 1e-6 and abs(fy) < 1e-6 and abs(fz) < 1e-6:
                continue
            x0, y0, z0 = get_coords(node)
            x1 = x0 + fx * scale
            y1 = y0 + fy * scale
            z1 = z0 + fz * scale
            r_x.extend([x0, x1, None])
            r_y.extend([y0, y1, None])
            r_z.extend([z0, z1, None])
            r_text.append(
                f"Reaction<br>Fx: {fx:.2f} N<br>Fy: {fy:.2f} N<br>Fz: {fz:.2f} N"
            )

        if r_x:
            fig.add_trace(go.Scatter3d(
                x=r_x,
                y=r_y,
                z=r_z,
                mode='lines',
                line=dict(color=COLORS["support_fixed"], width=3),
                name='Reactions',
                hoverinfo='skip',
            ))
            fig.add_trace(go.Scatter3d(
                x=[coord for coord in r_x if coord is not None][::2],
                y=[coord for coord in r_y if coord is not None][::2],
                z=[coord for coord in r_z if coord is not None][::2],
                mode='markers',
                marker=dict(size=config.node_size // 2, color=COLORS["support_fixed"],
                            symbol='diamond'),
                name='Reaction Points',
                text=r_text,
                hoverinfo='text',
                showlegend=False,
            ))

    # Draw nodes
    if config.show_nodes:
        node_x = [get_coords(n)[0] for n in model.nodes.values()]
        node_y = [get_coords(n)[1] for n in model.nodes.values()]
        node_z = [get_coords(n)[2] for n in model.nodes.values()]

        fig.add_trace(go.Scatter3d(
            x=node_x,
            y=node_y,
            z=node_z,
            mode='markers',
            marker=dict(size=config.node_size // 2, color=COLORS["node"], opacity=0.3),
            name='Nodes',
        ))

    # Layout
    x_range = [min(n.x for n in model.nodes.values()), max(n.x for n in model.nodes.values())]
    y_range = [min(n.y for n in model.nodes.values()), max(n.y for n in model.nodes.values())]
    z_range = [min(n.z for n in model.nodes.values()), max(n.z for n in model.nodes.values())]

    max_range = max(
        x_range[1] - x_range[0],
        y_range[1] - y_range[0],
        z_range[1] - z_range[0],
    )

    fig.update_layout(
        title="3D Model View",
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Z (m)",
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.0),
                up=dict(x=0, y=0, z=1),
            ),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=40, b=80),
    )

    if use_utilization:
        fig.add_trace(go.Scatter3d(
            x=[None],
            y=[None],
            z=[None],
            mode='markers',
            marker=dict(
                colorscale=config.colorscale,
                color=[0.0, 1.2],
                showscale=True,
                cmin=0.0,
                cmax=1.2,
                colorbar=dict(title="Utilization"),
                size=0.1,
            ),
            showlegend=False,
            hoverinfo='none',
        ))

    return fig


def create_model_summary_figure(model: ModelLike,
                                 config: Optional[VisualizationConfig] = None) -> "go.Figure":
    """Create a multi-panel summary figure with plan, elevation, and 3D views.

    Args:
        model: Structural model data to visualize
        config: Visualization configuration

    Returns:
        Plotly Figure with subplots
    """
    _check_plotly()
    config = config or VisualizationConfig()

    # Create individual figures
    plan_fig = create_plan_view(model, config)
    elev_x_fig = create_elevation_view(model, config, view_direction="X")
    view_3d_fig = create_3d_view(model, config)

    # Create subplot figure
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Plan View", "Elevation View (X)", "3D View", "Model Summary"),
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "scene"}, {"type": "table"}],
        ],
    )

    # Add traces from individual figures
    for trace in plan_fig.data:
        trace.legendgroup = "plan"
        trace.showlegend = False
        fig.add_trace(trace, row=1, col=1)

    for trace in elev_x_fig.data:
        trace.legendgroup = "elev"
        trace.showlegend = False
        fig.add_trace(trace, row=1, col=2)

    for trace in view_3d_fig.data:
        trace.legendgroup = "3d"
        trace.showlegend = False
        fig.add_trace(trace, row=2, col=1)

    # Add summary table
    summary = model.get_summary()
    fig.add_trace(
        go.Table(
            header=dict(values=["Property", "Value"]),
            cells=dict(values=[
                ["Nodes", "Elements", "Materials", "Sections", "Loads", "Fixed Supports"],
                [summary['n_nodes'], summary['n_elements'], summary['n_materials'],
                 summary['n_sections'], summary['n_loads'], summary['n_fixed_nodes']],
            ]),
        ),
        row=2, col=2,
    )

    fig.update_layout(
        title="FEM Model Summary",
        height=800,
        showlegend=False,
    )

    return fig


def get_model_statistics(model: ModelLike) -> Dict[str, Any]:
    """Get detailed statistics about the FEM model for visualization.

    Args:
        model: Structural model data to analyze

    Returns:
        Dictionary with model statistics
    """
    classification = _classify_elements(model)
    floors = _get_floor_elevations(model)

    # Calculate bounding box
    if model.nodes:
        x_coords = [n.x for n in model.nodes.values()]
        y_coords = [n.y for n in model.nodes.values()]
        z_coords = [n.z for n in model.nodes.values()]

        bbox = {
            "x_min": min(x_coords),
            "x_max": max(x_coords),
            "y_min": min(y_coords),
            "y_max": max(y_coords),
            "z_min": min(z_coords),
            "z_max": max(z_coords),
        }
    else:
        bbox = {k: 0.0 for k in ["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]}

    return {
        "n_nodes": len(model.nodes),
        "n_elements": len(model.elements),
        "n_columns": len(classification["columns"]),
        "n_beams": len(classification["beams"]),
        "n_coupling_beams": len(classification["coupling_beams"]),
        "n_core_wall_elements": len(classification["core_walls"]),
        "n_slab_elements": len(classification["slabs"]),
        "n_floors": len(floors),
        "floor_elevations": floors,
        "n_supports": len([n for n in model.nodes.values() if n.is_fixed or n.is_pinned]),
        "n_loads": len(model.loads),
        "n_uniform_loads": len(model.uniform_loads),
        "n_surface_loads": len(model.surface_loads),
        "n_diaphragms": len(model.diaphragms),
        "bounding_box": bbox,
        "is_built": model._is_built,
    }


def export_plotly_figure_image(fig: "go.Figure",
                               format: str = "png",
                               width: int = 1200,
                               height: int = 900,
                               scale: float = 2.0) -> bytes:
    """Export a Plotly figure to an image buffer.

    Args:
        fig: Plotly figure instance
        format: Image format (png, jpg, svg, pdf)
        width: Image width in pixels
        height: Image height in pixels
        scale: Resolution scaling factor

    Returns:
        Image bytes
    """
    _check_plotly()
    try:
        import plotly.io as pio
    except ImportError as exc:
        raise ImportError(
            "plotly.io is required to export images. "
            "Install kaleido: pip install -U kaleido"
        ) from exc

    return pio.to_image(fig, format=format, width=width, height=height, scale=scale)


__all__ = [
    "VisualizationBackend",
    "VisualizationExtractionConfig",
    "VisualizationData",
    "build_visualization_data_from_fem_model",
    "extract_visualization_data_from_opensees",
    "export_plotly_figure_image",
    "ViewType",
    "VisualizationConfig",
    "COLORS",
    "create_plan_view",
    "create_elevation_view",
    "create_3d_view",
    "create_model_summary_figure",
    "get_model_statistics",
    "calculate_auto_scale_factor",
    "render_section_forces",
    "render_section_forces_plan",
]
