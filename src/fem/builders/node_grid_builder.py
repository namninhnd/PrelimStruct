"""
NodeGridBuilder - Builder for node grid creation with base fixity.

This module extracts node grid creation logic from model_builder.py,
providing a clean API for creating the structural grid nodes with
proper floor-based numbering and base fixity.
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from src.core.data_models import GeometryInput, ProjectData
from src.fem.fem_engine import FEMModel, Node

if TYPE_CHECKING:
    from src.fem.model_builder import NodeRegistry


class NodeGridBuilder:
    """Builder for creating node grids with floor-based numbering.
    
    Implements OpenSees BuildingTcl node numbering convention:
    - Ground level (0): nodes 1-999
    - Level N (N >= 1): nodes N*1000 to N*1000+999
    
    Attributes:
        model: FEMModel to add nodes to
        project: ProjectData with geometry information
        registry: NodeRegistry for node creation/reuse
    """

    def __init__(
        self,
        model: FEMModel,
        project: ProjectData,
        registry: "NodeRegistry",
    ):
        self.model = model
        self.project = project
        self.registry = registry
        self.geometry = project.geometry

    def create_grid_nodes(self) -> Dict[Tuple[int, int, int], int]:
        """Create all grid nodes for the building.
        
        Creates nodes at all grid intersections for all floor levels.
        Base nodes (level 0) are fully fixed. Upper nodes are free.
        
        Returns:
            Dictionary mapping (ix, iy, level) to node tag
        """
        grid_nodes: Dict[Tuple[int, int, int], int] = {}
        
        for level in range(self.geometry.floors + 1):
            z = level * self.geometry.story_height
            for ix in range(self.geometry.num_bays_x + 1):
                for iy in range(self.geometry.num_bays_y + 1):
                    x = ix * self.geometry.bay_x
                    y = iy * self.geometry.bay_y
                    # Base nodes are fully fixed
                    restraints = [1, 1, 1, 1, 1, 1] if level == 0 else None
                    tag = self.registry.get_or_create(
                        x, y, z, restraints=restraints, floor_level=level
                    )
                    grid_nodes[(ix, iy, level)] = tag
        
        return grid_nodes

    def create_core_wall_nodes(
        self,
        wall_mesh_result,
        registry_nodes_by_floor: Dict[int, List[int]],
    ) -> None:
        """Add core wall mesh nodes to model.
        
        Args:
            wall_mesh_result: Result from WallMeshGenerator.generate_mesh()
            registry_nodes_by_floor: Dictionary to track nodes by floor
        """
        for node_tag, x, y, z, floor_level in wall_mesh_result.nodes:
            # Wall base nodes are fully fixed
            restraints = [1, 1, 1, 1, 1, 1] if z == 0.0 else None
            node = Node(tag=node_tag, x=x, y=y, z=z, restraints=restraints)
            self.model.add_node(node)
            
            # Track in registry for diaphragms
            if floor_level not in registry_nodes_by_floor:
                registry_nodes_by_floor[floor_level] = []
            registry_nodes_by_floor[floor_level].append(node_tag)

    def create_slab_nodes(
        self,
        slab_mesh_result,
        existing_nodes: Dict[Tuple[float, float, float], int],
        registry_nodes_by_floor: Dict[int, List[int]],
    ) -> None:
        """Add slab mesh nodes to model.
        
        Args:
            slab_mesh_result: Result from SlabMeshGenerator.generate_mesh()
            existing_nodes: Dictionary mapping coordinates to node tags
            registry_nodes_by_floor: Dictionary to track nodes by floor
        """
        for node_data in slab_mesh_result.nodes:
            tag, x, y, z_coord, floor_lvl = node_data
            node = Node(tag=tag, x=x, y=y, z=z_coord)
            self.model.add_node(node)
            existing_nodes[(round(x, 6), round(y, 6), round(z_coord, 6))] = tag
            
            # Track in registry for diaphragm
            if floor_lvl not in registry_nodes_by_floor:
                registry_nodes_by_floor[floor_lvl] = []
            registry_nodes_by_floor[floor_lvl].append(tag)


__all__ = ["NodeGridBuilder"]
