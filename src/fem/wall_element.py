"""
Wall element module for ShellMITC4 shell element modeling.

This module provides wall panel definition and mesh generation for
proper shell element wall modeling using OpenSeesPy ShellMITC4 elements
with Plate Fiber Section.

References:
    - https://openseespydoc.readthedocs.io/en/latest/src/ShellMITC4.html
    - https://opensees.berkeley.edu/wiki/index.php/Shell_Element
    - https://opensees.berkeley.edu/wiki/index.php?title=Plate_Fiber_Section
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple, Dict, Optional
import math
import logging

logger = logging.getLogger(__name__)


@dataclass
class WallPanel:
    """Single wall panel definition.
    
    Attributes:
        wall_id: Unique identifier for the wall
        base_point: (x, y) coordinates at ground level (m)
        length: Wall length in plan (m)
        thickness: Wall thickness (m), typically 0.2-0.4m
        height: Total wall height (m)
        orientation: Angle in degrees (0=along X-axis, 90=along Y-axis)
        fcu: Concrete characteristic strength (MPa)
    """
    wall_id: str
    base_point: Tuple[float, float]
    length: float
    thickness: float
    height: float
    orientation: float = 0.0
    fcu: float = 40.0
    
    def __post_init__(self):
        if self.length <= 0:
            raise ValueError("Wall length must be positive")
        if self.thickness <= 0:
            raise ValueError("Wall thickness must be positive")
        if self.height <= 0:
            raise ValueError("Wall height must be positive")

    @property
    def end_point(self) -> Tuple[float, float]:
        """Calculate end point based on base point, length, and orientation."""
        rad = math.radians(self.orientation)
        dx = self.length * math.cos(rad)
        dy = self.length * math.sin(rad)
        return (self.base_point[0] + dx, self.base_point[1] + dy)

    @property
    def normal_vector(self) -> Tuple[float, float]:
        """Get wall normal vector (perpendicular to wall face)."""
        rad = math.radians(self.orientation + 90)
        return (math.cos(rad), math.sin(rad))


@dataclass
class ShellQuad:
    """Single shell quad element definition.
    
    Nodes are ordered counter-clockwise when viewed from positive normal.
    """
    tag: int
    node_tags: Tuple[int, int, int, int]  # n1, n2, n3, n4 (CCW)
    section_tag: int
    wall_id: str
    floor_level: int
    
    def __post_init__(self):
        if len(self.node_tags) != 4:
            raise ValueError("ShellQuad requires exactly 4 node tags")


@dataclass
class WallMeshResult:
    """Result from wall mesh generation.
    
    Attributes:
        nodes: List of (tag, x, y, z, floor_level) tuples
        elements: List of ShellQuad elements
        edge_nodes: Dict mapping floor level to list of edge node tags
                   (for rigid link connections to floor beams)
    """
    nodes: List[Tuple[int, float, float, float, int]]
    elements: List[ShellQuad]
    edge_nodes: Dict[int, List[int]] = field(default_factory=dict)


class WallMeshGenerator:
    """Generate quad mesh for wall panels.
    
    Creates a structured mesh of ShellMITC4 quad elements for a wall panel.
    The mesh is refined per story with configurable elements per story height.
    """
    
    def __init__(self, 
                 base_node_tag: int = 10000,
                 base_element_tag: int = 10000):
        """Initialize mesh generator.
        
        Args:
            base_node_tag: Starting node tag for wall nodes
            base_element_tag: Starting element tag for wall elements
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
        wall: WallPanel,
        num_floors: int,
        story_height: float,
        section_tag: int,
        elements_along_length: int = 1,
        elements_per_story: int = 2,
        registry: Optional[Any] = None,
    ) -> WallMeshResult:
        """Generate mesh for a wall panel.
        
        Args:
            wall: Wall panel definition
            num_floors: Number of floors
            story_height: Height per story (m)
            section_tag: Section tag for PlateFiberSection
            elements_along_length: Number of elements along wall length
            elements_per_story: Number of elements per story height
            registry: Optional NodeRegistry for node deduplication.
                      When provided, uses get_or_create() to reuse nodes
                      at coincident coordinates (e.g. flange-web junctions).
                      Nodes are added to the OpenSeesPy model by the registry;
                      callers MUST NOT call model.add_node() or
                      registry.register_existing() afterward.
        
        Returns:
            WallMeshResult with nodes, elements, and edge nodes
        """
        nodes: List[Tuple[int, float, float, float, int]] = []
        elements: List[ShellQuad] = []
        edge_nodes: Dict[int, List[int]] = {}
        
        # Calculate node spacing
        dx_total = wall.end_point[0] - wall.base_point[0]
        dy_total = wall.end_point[1] - wall.base_point[1]
        
        num_nodes_x = elements_along_length + 1
        num_nodes_z = elements_per_story * num_floors + 1
        
        dx = dx_total / elements_along_length if elements_along_length > 0 else 0
        dy = dy_total / elements_along_length if elements_along_length > 0 else 0
        dz = story_height / elements_per_story
        
        # Generate nodes in grid pattern
        # node_grid[iz][ix] = node_tag
        node_grid: List[List[int]] = []
        
        for iz in range(num_nodes_z):
            row: List[int] = []
            z = iz * dz
            floor_level = int(z / story_height) if story_height > 0 else 0
            
            for ix in range(num_nodes_x):
                x = wall.base_point[0] + ix * dx
                y = wall.base_point[1] + ix * dy
                
                if registry is not None:
                    # Deduplicated path: registry handles node creation
                    # and adds to OpenSeesPy model internally
                    restraints = [1, 1, 1, 1, 1, 1] if z == 0.0 else None
                    tag = registry.get_or_create(
                        x, y, z,
                        restraints=restraints,
                        floor_level=floor_level,
                    )
                else:
                    # Legacy path: sequential tag assignment
                    tag = self._get_next_node_tag()
                
                nodes.append((tag, x, y, z, floor_level))
                row.append(tag)
                
                # Track edge nodes (first and last along length) at floor levels
                at_floor_level = abs(z - floor_level * story_height) < 1e-6
                if at_floor_level and (ix == 0 or ix == num_nodes_x - 1):
                    if floor_level not in edge_nodes:
                        edge_nodes[floor_level] = []
                    edge_nodes[floor_level].append(tag)
            
            node_grid.append(row)
        
        # Generate quad elements
        for iz in range(num_nodes_z - 1):
            floor_level = int((iz * dz) / story_height) if story_height > 0 else 0
            
            for ix in range(num_nodes_x - 1):
                # Counter-clockwise ordering when viewed from +normal
                n1 = node_grid[iz][ix]
                n2 = node_grid[iz][ix + 1]
                n3 = node_grid[iz + 1][ix + 1]
                n4 = node_grid[iz + 1][ix]
                
                elem = ShellQuad(
                    tag=self._get_next_element_tag(),
                    node_tags=(n1, n2, n3, n4),
                    section_tag=section_tag,
                    wall_id=wall.wall_id,
                    floor_level=floor_level,
                )
                elements.append(elem)
        
        logger.info(
            f"Generated wall mesh '{wall.wall_id}': "
            f"{len(nodes)} nodes, {len(elements)} elements"
        )
        
        return WallMeshResult(
            nodes=nodes,
            elements=elements,
            edge_nodes=edge_nodes,
        )


def create_wall_rigid_links(
    wall_edge_nodes: Dict[int, List[int]],
    floor_beam_nodes: Dict[int, List[int]],
    tolerance: float = 0.5
) -> List[Tuple[int, int]]:
    """Create rigid link pairs between wall edge nodes and floor beam nodes.
    
    Args:
        wall_edge_nodes: Dict of floor level -> list of wall edge node tags
        floor_beam_nodes: Dict of floor level -> list of beam node tags near wall
        tolerance: Maximum distance (m) for connecting nodes
    
    Returns:
        List of (master_node, slave_node) tuples for rigid links
        Master is wall node, slave is beam node
    """
    # Note: Actual coordinate-based matching requires node coordinates
    # This is a placeholder that will be refined during model_builder integration
    links: List[Tuple[int, int]] = []
    
    for floor_level, wall_nodes in wall_edge_nodes.items():
        if floor_level not in floor_beam_nodes:
            continue
        beam_nodes = floor_beam_nodes[floor_level]
        
        # For now, create links between corresponding nodes
        # Full implementation will use coordinate matching
        for i, wall_node in enumerate(wall_nodes):
            if i < len(beam_nodes):
                links.append((wall_node, beam_nodes[i]))
    
    return links


__all__ = [
    "WallPanel",
    "ShellQuad",
    "WallMeshResult",
    "WallMeshGenerator",
    "create_wall_rigid_links",
]
