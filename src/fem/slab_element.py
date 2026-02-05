"""
Slab element module for ShellMITC4 shell element modeling.

This module provides slab panel definition and mesh generation for
floor slab modeling using OpenSeesPy ShellMITC4 elements with
Elastic Membrane Plate Section.

References:
    - https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
    - https://opensees.berkeley.edu/wiki/index.php/Elastic_Membrane_Plate_Section
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SlabPanel:
    """Single slab panel definition.
    
    Attributes:
        slab_id: Unique identifier for the slab panel
        origin: (x, y) coordinates of bottom-left corner (m)
        width_x: Slab dimension along X-axis (m)
        width_y: Slab dimension along Y-axis (m)
        thickness: Slab thickness (m), typically 0.15-0.25m
        elevation: Z-coordinate of slab (m), i.e., floor level height
        fcu: Concrete characteristic strength (MPa)
    """
    slab_id: str
    origin: Tuple[float, float]
    width_x: float
    width_y: float
    thickness: float
    elevation: float
    fcu: float = 40.0
    
    def __post_init__(self):
        if self.width_x <= 0:
            raise ValueError("Slab width_x must be positive")
        if self.width_y <= 0:
            raise ValueError("Slab width_y must be positive")
        if self.thickness <= 0:
            raise ValueError("Slab thickness must be positive")

    @property
    def corners(self) -> Tuple[Tuple[float, float, float], ...]:
        """Get 4 corner coordinates (x, y, z) in counter-clockwise order."""
        x0, y0 = self.origin
        z = self.elevation
        return (
            (x0, y0, z),                           # Bottom-left
            (x0 + self.width_x, y0, z),            # Bottom-right
            (x0 + self.width_x, y0 + self.width_y, z),  # Top-right
            (x0, y0 + self.width_y, z),            # Top-left
        )

    @property
    def area(self) -> float:
        """Slab area in m²."""
        return self.width_x * self.width_y


@dataclass
class SlabOpening:
    """Opening in a slab panel (stairs, elevator, MEP shaft).
    
    Attributes:
        opening_id: Unique identifier for the opening
        origin: (x, y) coordinates of bottom-left corner (m)
        width_x: Opening dimension along X-axis (m)
        width_y: Opening dimension along Y-axis (m)
        opening_type: Type of opening ("stair", "elevator", "mep", "generic")
    """
    opening_id: str
    origin: Tuple[float, float]
    width_x: float
    width_y: float
    opening_type: str = "generic"
    
    def __post_init__(self):
        if self.width_x <= 0:
            raise ValueError("Opening width_x must be positive")
        if self.width_y <= 0:
            raise ValueError("Opening width_y must be positive")
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Get bounding box (x_min, y_min, x_max, y_max)."""
        x0, y0 = self.origin
        return (x0, y0, x0 + self.width_x, y0 + self.width_y)
    
    def overlaps_panel(self, panel: SlabPanel) -> bool:
        """Check if opening overlaps with a slab panel."""
        ox_min, oy_min, ox_max, oy_max = self.bounds
        px_min, py_min = panel.origin
        px_max = px_min + panel.width_x
        py_max = py_min + panel.width_y
        
        return not (
            ox_max <= px_min or ox_min >= px_max or
            oy_max <= py_min or oy_min >= py_max
        )


@dataclass
class SlabQuad:
    """Single slab quad element definition.
    
    Nodes are ordered counter-clockwise when viewed from above (positive Z).
    """
    tag: int
    node_tags: Tuple[int, int, int, int]  # n1, n2, n3, n4 (CCW from above)
    section_tag: int
    slab_id: str
    floor_level: int
    
    def __post_init__(self):
        if len(self.node_tags) != 4:
            raise ValueError("SlabQuad requires exactly 4 node tags")


@dataclass
class SlabMeshResult:
    """Result from slab mesh generation.
    
    Attributes:
        nodes: List of (tag, x, y, z, floor_level) tuples
        elements: List of SlabQuad elements
        boundary_nodes: Dict mapping edge ('left', 'right', 'bottom', 'top')
                       to list of node tags for beam connectivity
    """
    nodes: List[Tuple[int, float, float, float, int]]
    elements: List[SlabQuad]
    boundary_nodes: Dict[str, List[int]] = field(default_factory=dict)


class SlabMeshGenerator:
    """Generate quad mesh for slab panels.
    
    Creates a structured mesh of ShellMITC4 quad elements for a slab panel.
    The mesh is aligned with beam grid lines for proper node sharing.
    """
    
    def __init__(self, 
                 base_node_tag: int = 50000,
                 base_element_tag: int = 50000):
        """Initialize mesh generator.
        
        Args:
            base_node_tag: Starting node tag for slab nodes
            base_element_tag: Starting element tag for slab elements
        """
        self._node_tag = base_node_tag
        self._element_tag = base_element_tag
    
    def _get_next_node_tag(self) -> int:
        tag = self._node_tag
        self._node_tag += 1
        return tag
    
    def _get_next_element_tag(self) -> int:
        tag = self._element_tag
        self._element_tag += 1
        return tag
    
    def generate_mesh(
        self,
        slab: SlabPanel,
        floor_level: int,
        section_tag: int,
        elements_along_x: Optional[int] = None,
        elements_along_y: Optional[int] = None,
        beam_subdivision_count: int = 6,
        existing_nodes: Optional[Dict[Tuple[float, float, float], int]] = None,
        openings: Optional[List['SlabOpening']] = None,
    ) -> SlabMeshResult:
        """Generate mesh for a slab panel.
        
        By default, slab mesh is aligned with beam subdivision points (6 subdivisions per bay)
        to ensure proper node sharing and force transfer at beam-slab connections.
        
        Args:
            slab: Slab panel definition
            floor_level: Floor level index (1-based)
            section_tag: Section tag for ElasticMembranePlateSection
            elements_along_x: Number of elements along X direction (default: beam_subdivision_count)
            elements_along_y: Number of elements along Y direction (default: beam_subdivision_count)
            beam_subdivision_count: Default subdivision count matching beam elements (default: 6)
                                   Used when elements_along_x/y are not provided
            existing_nodes: Optional dict mapping (x,y,z) coords to existing node tags
                           for sharing nodes with beams
            openings: Optional list of SlabOpening to exclude from mesh
        
        Returns:
            SlabMeshResult with nodes, elements, and boundary nodes
        """
        if elements_along_x is None:
            elements_along_x = beam_subdivision_count
        if elements_along_y is None:
            elements_along_y = beam_subdivision_count
        
        nodes: List[Tuple[int, float, float, float, int]] = []
        elements: List[SlabQuad] = []
        boundary_nodes: Dict[str, List[int]] = {
            'left': [],
            'right': [],
            'bottom': [],
            'top': [],
        }
        
        existing_nodes = existing_nodes or {}
        openings = openings or []
        
        num_nodes_x = elements_along_x + 1
        num_nodes_y = elements_along_y + 1
        
        dx = slab.width_x / elements_along_x
        dy = slab.width_y / elements_along_y
        
        x0, y0 = slab.origin
        z = slab.elevation
        
        # Generate nodes in grid pattern
        # node_grid[iy][ix] = node_tag
        node_grid: List[List[int]] = []
        
        for iy in range(num_nodes_y):
            row: List[int] = []
            y = y0 + iy * dy
            
            for ix in range(num_nodes_x):
                x = x0 + ix * dx
                
                # Check if node already exists (shared with beam)
                coord_key = (round(x, 6), round(y, 6), round(z, 6))
                if coord_key in existing_nodes:
                    tag = existing_nodes[coord_key]
                else:
                    tag = self._get_next_node_tag()
                    nodes.append((tag, x, y, z, floor_level))
                
                row.append(tag)
                
                # Track boundary nodes for beam connectivity
                if ix == 0:
                    boundary_nodes['left'].append(tag)
                if ix == num_nodes_x - 1:
                    boundary_nodes['right'].append(tag)
                if iy == 0:
                    boundary_nodes['bottom'].append(tag)
                if iy == num_nodes_y - 1:
                    boundary_nodes['top'].append(tag)
            
            node_grid.append(row)
        
        # Generate quad elements (CCW ordering when viewed from +Z)
        skipped_for_openings = 0
        for iy in range(num_nodes_y - 1):
            for ix in range(num_nodes_x - 1):
                # Calculate element center point for opening check
                elem_x_min = x0 + ix * dx
                elem_x_max = x0 + (ix + 1) * dx
                elem_y_min = y0 + iy * dy
                elem_y_max = y0 + (iy + 1) * dy
                elem_center_x = (elem_x_min + elem_x_max) / 2
                elem_center_y = (elem_y_min + elem_y_max) / 2
                
                # Skip element if it overlaps with any opening
                skip_element = False
                for opening in openings:
                    ox_min, oy_min, ox_max, oy_max = opening.bounds
                    # Check if element center is inside opening
                    if (ox_min <= elem_center_x <= ox_max and
                        oy_min <= elem_center_y <= oy_max):
                        skip_element = True
                        skipped_for_openings += 1
                        break
                
                if skip_element:
                    continue
                
                # Counter-clockwise ordering when viewed from above
                n1 = node_grid[iy][ix]          # Bottom-left
                n2 = node_grid[iy][ix + 1]      # Bottom-right
                n3 = node_grid[iy + 1][ix + 1]  # Top-right
                n4 = node_grid[iy + 1][ix]      # Top-left
                
                elem = SlabQuad(
                    tag=self._get_next_element_tag(),
                    node_tags=(n1, n2, n3, n4),
                    section_tag=section_tag,
                    slab_id=slab.slab_id,
                    floor_level=floor_level,
                )
                elements.append(elem)
        
        # Check mesh quality (aspect ratio)
        aspect_ratio = max(dx, dy) / min(dx, dy) if min(dx, dy) > 0 else float('inf')
        if aspect_ratio > 5:
            logger.warning(
                f"Slab mesh '{slab.slab_id}' has high aspect ratio {aspect_ratio:.2f} > 5"
            )
        
        logger.info(
            f"Generated slab mesh '{slab.slab_id}': "
            f"{len(nodes)} new nodes, {len(elements)} elements, "
            f"aspect ratio {aspect_ratio:.2f}"
        )
        
        return SlabMeshResult(
            nodes=nodes,
            elements=elements,
            boundary_nodes=boundary_nodes,
        )


def create_slab_panels_from_bays(
    num_bays_x: int,
    num_bays_y: int,
    bay_x: float,
    bay_y: float,
    floor_elevations: List[float],
    slab_thickness: float = 0.15,
    fcu: float = 40.0,
) -> List[SlabPanel]:
    """Create slab panels from structural bay grid.
    
    Args:
        num_bays_x: Number of bays in X direction
        num_bays_y: Number of bays in Y direction
        bay_x: Bay spacing in X direction (m)
        bay_y: Bay spacing in Y direction (m)
        floor_elevations: List of floor elevations (m)
        slab_thickness: Slab thickness (m)
        fcu: Concrete characteristic strength (MPa)
    
    Returns:
        List of SlabPanel objects, one per bay per floor
    """
    panels: List[SlabPanel] = []
    
    for floor_idx, elevation in enumerate(floor_elevations):
        floor_level = floor_idx + 1
        
        for ix in range(num_bays_x):
            for iy in range(num_bays_y):
                origin_x = ix * bay_x
                origin_y = iy * bay_y
                
                panel = SlabPanel(
                    slab_id=f"S{floor_level}_{ix}_{iy}",
                    origin=(origin_x, origin_y),
                    width_x=bay_x,
                    width_y=bay_y,
                    thickness=slab_thickness,
                    elevation=elevation,
                    fcu=fcu,
                )
                panels.append(panel)
    
    return panels


__all__ = [
    "SlabPanel",
    "SlabOpening",
    "SlabQuad",
    "SlabMeshResult",
    "SlabMeshGenerator",
    "create_slab_panels_from_bays",
]
