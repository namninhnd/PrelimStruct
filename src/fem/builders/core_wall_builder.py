"""
CoreWallBuilder - Builder for core wall shell elements.

This module extracts core wall creation logic from model_builder.py,
providing a clean API for creating shell walls with mesh generation.
"""

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from src.core.data_models import CoreWallGeometry, GeometryInput, ProjectData
from src.fem.model_builder import trim_beam_segment_against_polygon
from src.fem.builders.beam_builder import BeamBuilder
from src.fem.core_wall_geometry import (
    ISectionCoreWall,
    TwoCFacingCoreWall,
    TwoCBackToBackCoreWall,
    TubeCenterOpeningCoreWall,
    TubeSideOpeningCoreWall,
)
from src.fem.fem_engine import Element, ElementType, FEMModel
from src.fem.materials import ConcreteProperties, get_plane_stress_material, get_plate_fiber_section
from src.fem.wall_element import WallPanel, WallMeshGenerator

if TYPE_CHECKING:
    from src.fem.model_builder import ModelBuilderOptions

logger = logging.getLogger(__name__)


class CoreWallBuilder:
    """Builder for core wall shell elements.
    
    This class handles creation of core wall shell elements using
    ShellMITC4 elements with PlateFiberSection for accurate modeling
    of shear wall behavior.
    
    Attributes:
        model: FEMModel to add core walls to
        project: ProjectData with geometry information
        options: ModelBuilderOptions for configuration
        wall_nodes: List of wall node tags created
        wall_elements: List of wall element tags created
    """

    def __init__(
        self,
        model: FEMModel,
        project: ProjectData,
        options: "ModelBuilderOptions",
    ):
        self.model = model
        self.project = project
        self.options = options
        self.geometry = project.geometry
        self.wall_nodes: List[int] = []
        self.wall_elements: List[int] = []
        
        # These will be set by setup_materials()
        self.wall_material_tag: Optional[int] = None
        self.wall_section_tag: Optional[int] = None

    def setup_materials(self, wall_concrete: ConcreteProperties) -> None:
        """Configure materials and sections for core walls.
        
        Args:
            wall_concrete: ConcreteProperties for wall material
        """
        self.wall_material_tag = 10  # NDMaterial tag for wall plane stress
        self.wall_section_tag = 10   # PlateFiberSection tag for wall shells
        
        # Create NDMaterial for plane stress (ElasticIsotropic)
        wall_nd_material = get_plane_stress_material(wall_concrete, self.wall_material_tag)
        self.model.add_material(self.wall_material_tag, wall_nd_material)
        
        # Create PlateFiberSection for ShellMITC4
        assert self.project.lateral.core_geometry is not None
        thickness_m = self.project.lateral.core_geometry.wall_thickness / 1000.0
        wall_section = get_plate_fiber_section(
            nd_material_tag=self.wall_material_tag,
            thickness=thickness_m,
            section_tag=self.wall_section_tag,
        )
        self.model.add_section(self.wall_section_tag, wall_section)

    def create_core_walls(
        self,
        offset_x: float,
        offset_y: float,
        registry_nodes_by_floor: Dict[int, List[int]],
    ) -> Tuple[List[int], List[int]]:
        """Create all core wall shell elements.
        
        Args:
            offset_x: X offset of core wall in meters
            offset_y: Y offset of core wall in meters
            registry_nodes_by_floor: Dictionary to track nodes by floor
            
        Returns:
            Tuple of (wall_node_tags, wall_element_tags)
        """
        assert self.wall_material_tag is not None
        assert self.wall_section_tag is not None
        assert self.project.lateral.core_geometry is not None
        
        # Extract wall panels from core geometry
        wall_panels = self._extract_wall_panels(
            self.project.lateral.core_geometry,
            offset_x,
            offset_y,
        )
        
        # Create wall mesh generator
        wall_mesh_generator = WallMeshGenerator(
            base_node_tag=50000,
            base_element_tag=50000,
        )
        
        # Generate mesh for each wall panel
        for wall in wall_panels:
            mesh_result = wall_mesh_generator.generate_mesh(
                wall=wall,
                num_floors=self.geometry.floors,
                story_height=self.geometry.story_height,
                section_tag=self.wall_section_tag,
                elements_along_length=2,
                elements_per_story=2,
            )
            
            # Add wall nodes to model
            for node_tag, x, y, z, floor_level in mesh_result.nodes:
                restraints = [1, 1, 1, 1, 1, 1] if z == 0.0 else None
                from src.fem.fem_engine import Node
                node = Node(tag=node_tag, x=x, y=y, z=z, restraints=restraints)
                self.model.add_node(node)
                self.wall_nodes.append(node_tag)
                
                # Track in registry for diaphragms
                if floor_level not in registry_nodes_by_floor:
                    registry_nodes_by_floor[floor_level] = []
                registry_nodes_by_floor[floor_level].append(node_tag)
            
            # Add wall shell elements
            for shell_quad in mesh_result.elements:
                self.model.add_element(
                    Element(
                        tag=shell_quad.tag,
                        element_type=ElementType.SHELL_MITC4,
                        node_tags=list(shell_quad.node_tags),
                        material_tag=self.wall_material_tag,
                        section_tag=shell_quad.section_tag,
                    )
                )
                self.wall_elements.append(shell_quad.tag)
        
        logger.info(
            f"Generated shell mesh for {len(wall_panels)} wall panels using ShellMITC4 elements"
        )
        
        return self.wall_nodes, self.wall_elements

    def _extract_wall_panels(
        self,
        core_geometry: CoreWallGeometry,
        offset_x: float,
        offset_y: float,
    ) -> List[WallPanel]:
        """Extract wall panels from core geometry configuration.
        
        Args:
            core_geometry: Core wall geometry configuration
            offset_x: X offset in meters
            offset_y: Y offset in meters
            
        Returns:
            List of WallPanel objects
        """
        config = core_geometry.config
        
        if config.value == "i_section":
            generator = ISectionCoreWall(core_geometry)
        elif config.value == "two_c_facing":
            generator = TwoCFacingCoreWall(core_geometry)
        elif config.value == "two_c_back_to_back":
            generator = TwoCBackToBackCoreWall(core_geometry)
        elif config.value == "tube_center_opening":
            generator = TubeCenterOpeningCoreWall(core_geometry)
        elif config.value == "tube_side_opening":
            generator = TubeSideOpeningCoreWall(core_geometry)
        else:
            raise ValueError(f"Unsupported core wall configuration: {config}")
        
        return generator.generate_panels(offset_x=offset_x * 1000.0, offset_y=offset_y * 1000.0)

    def get_material_tag(self) -> Optional[int]:
        """Get the wall material tag.
        
        Returns:
            Material tag or None if materials not set up
        """
        return self.wall_material_tag

    def get_section_tag(self) -> Optional[int]:
        """Get the wall section tag.
        
        Returns:
            Section tag or None if materials not set up
        """
        return self.wall_section_tag


__all__ = ["CoreWallBuilder"]
