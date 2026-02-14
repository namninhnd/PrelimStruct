"""
CoreWallBuilder - Builder for core wall shell elements.

This module extracts core wall creation logic from model_builder.py,
providing a clean API for creating shell walls with mesh generation.
"""

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from src.core.data_models import CoreWallConfig, CoreWallGeometry, GeometryInput, ProjectData, TubeOpeningPlacement
from src.fem.core_wall_geometry import resolve_i_section_plan_dimensions
from src.fem.model_builder import trim_beam_segment_against_polygon
from src.fem.builders.beam_builder import BeamBuilder
from src.fem.fem_engine import Element, ElementType, FEMModel
from src.fem.materials import ConcreteProperties, get_plane_stress_material, get_plate_fiber_section
from src.fem.wall_element import WallPanel, WallMeshGenerator

if TYPE_CHECKING:
    from src.fem.model_builder import ModelBuilderOptions, NodeRegistry

logger = logging.getLogger(__name__)
SHELL_TRI_TAG_OFFSET = 300000


def _normalize_shell_mesh_density(shell_mesh_density: str) -> str:
    density = shell_mesh_density.strip().lower()
    if density not in {"coarse", "medium", "fine"}:
        raise ValueError(
            f"Unsupported shell_mesh_density '{shell_mesh_density}'. "
            "Use 'coarse', 'medium', or 'fine'."
        )
    return density


def _wall_mesh_divisions_for_density(shell_mesh_density: str) -> Tuple[int, int]:
    density = _normalize_shell_mesh_density(shell_mesh_density)
    if density == "coarse":
        return 1, 1
    if density == "fine":
        return 4, 3
    return 2, 2


def _normalize_shell_mesh_type(shell_mesh_type: str) -> str:
    mesh_type = shell_mesh_type.strip().lower()
    if mesh_type not in {"quad", "tri"}:
        raise ValueError(f"Unsupported shell_mesh_type '{shell_mesh_type}'. Use 'quad' or 'tri'.")
    return mesh_type


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
        registry: Optional["NodeRegistry"] = None,
    ) -> Tuple[List[int], List[int]]:
        """Create all core wall shell elements.
        
        Args:
            offset_x: X offset of core wall in meters
            offset_y: Y offset of core wall in meters
            registry_nodes_by_floor: Dictionary to track nodes by floor
            registry: Optional NodeRegistry for registering wall nodes
            
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
        wall_elements_along_length, wall_elements_per_story = _wall_mesh_divisions_for_density(
            self.options.shell_mesh_density
        )
        shell_mesh_type = _normalize_shell_mesh_type(self.options.shell_mesh_type)
        for wall in wall_panels:
            mesh_result = wall_mesh_generator.generate_mesh(
                wall=wall,
                num_floors=self.geometry.floors,
                story_height=self.geometry.story_height,
                section_tag=self.wall_section_tag,
                elements_along_length=wall_elements_along_length,
                elements_per_story=wall_elements_per_story,
                registry=registry,
            )
            
            # Add wall nodes to model
            for node_tag, x, y, z, floor_level in mesh_result.nodes:
                if registry is None:
                    restraints = [1, 1, 1, 1, 1, 1] if z == 0.0 else None
                    from src.fem.fem_engine import Node
                    node = Node(
                        tag=node_tag,
                        x=x,
                        y=y,
                        z=z,
                        restraints=restraints or [0, 0, 0, 0, 0, 0],
                    )
                    self.model.add_node(node)
                
                self.wall_nodes.append(node_tag)
                
                # Track in registry for diaphragms
                if floor_level not in registry_nodes_by_floor:
                    registry_nodes_by_floor[floor_level] = []
                registry_nodes_by_floor[floor_level].append(node_tag)
            
            # Add wall shell elements
            for shell_quad in mesh_result.elements:
                if shell_mesh_type == "quad":
                    shell_elements = [
                        Element(
                            tag=shell_quad.tag,
                            element_type=ElementType.SHELL_MITC4,
                            node_tags=list(shell_quad.node_tags),
                            material_tag=self.wall_material_tag,
                            section_tag=shell_quad.section_tag,
                        )
                    ]
                else:
                    n1, n2, n3, n4 = shell_quad.node_tags
                    shell_elements = [
                        Element(
                            tag=shell_quad.tag,
                            element_type=ElementType.SHELL_DKGT,
                            node_tags=[n1, n2, n3],
                            material_tag=self.wall_material_tag,
                            section_tag=shell_quad.section_tag,
                        ),
                        Element(
                            tag=shell_quad.tag + SHELL_TRI_TAG_OFFSET,
                            element_type=ElementType.SHELL_DKGT,
                            node_tags=[n1, n3, n4],
                            material_tag=self.wall_material_tag,
                            section_tag=shell_quad.section_tag,
                        ),
                    ]

                for shell_element in shell_elements:
                    self.model.add_element(shell_element)
                    self.wall_elements.append(shell_element.tag)
        
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
        thickness_m = core_geometry.wall_thickness / 1000.0
        fcu = 40.0
        panels: List[WallPanel] = []
        
        if config == CoreWallConfig.I_SECTION:
            length_x_mm, length_y_mm = resolve_i_section_plan_dimensions(core_geometry)
            length_x_m = length_x_mm / 1000.0
            length_y_m = length_y_mm / 1000.0
            
            panels.append(WallPanel(
                wall_id="IW1",
                base_point=(offset_x, offset_y),
                length=length_y_m,
                thickness=thickness_m,
                height=1.0,
                orientation=90.0,
                fcu=fcu,
            ))
            panels.append(WallPanel(
                wall_id="IW2",
                base_point=(offset_x + length_x_m, offset_y),
                length=length_y_m,
                thickness=thickness_m,
                height=1.0,
                orientation=90.0,
                fcu=fcu,
            ))
            web_y = offset_y + length_y_m / 2
            panels.append(WallPanel(
                wall_id="IW3",
                base_point=(offset_x, web_y),
                length=length_x_m,
                thickness=thickness_m,
                height=1.0,
                orientation=0.0,
                fcu=fcu,
            ))
            
        elif config == CoreWallConfig.TUBE_WITH_OPENINGS:
            length_x_m = core_geometry.length_x / 1000.0
            length_y_m = core_geometry.length_y / 1000.0
            opening_width_m = core_geometry.opening_width / 1000.0 if core_geometry.opening_width else 0.0
            placement = core_geometry.opening_placement
            if placement in {
                TubeOpeningPlacement.BOTH,
                TubeOpeningPlacement.TOP,
                TubeOpeningPlacement.BOTTOM,
            }:
                placement = TubeOpeningPlacement.TOP_BOT

            opening_enabled = placement == TubeOpeningPlacement.TOP_BOT

            has_top_bot_openings = (
                opening_enabled
                and opening_width_m > 0.0
                and opening_width_m < length_x_m
            )

            if has_top_bot_openings:
                side_length = (length_x_m - opening_width_m) / 2.0
                panels.append(WallPanel("TW1_left", (offset_x, offset_y), side_length, thickness_m, 1.0, 0.0, fcu))
                panels.append(WallPanel("TW1_right", (offset_x + side_length + opening_width_m, offset_y), side_length, thickness_m, 1.0, 0.0, fcu))
                panels.append(WallPanel("TW2", (offset_x + length_x_m, offset_y), length_y_m, thickness_m, 1.0, 90.0, fcu))
                panels.append(WallPanel("TW3_left", (offset_x, offset_y + length_y_m), side_length, thickness_m, 1.0, 0.0, fcu))
                panels.append(WallPanel("TW3_right", (offset_x + side_length + opening_width_m, offset_y + length_y_m), side_length, thickness_m, 1.0, 0.0, fcu))
                panels.append(WallPanel("TW4", (offset_x, offset_y), length_y_m, thickness_m, 1.0, 90.0, fcu))
            else:
                panels.append(WallPanel("TW1", (offset_x, offset_y), length_x_m, thickness_m, 1.0, 0.0, fcu))
                panels.append(WallPanel("TW2", (offset_x + length_x_m, offset_y), length_y_m, thickness_m, 1.0, 90.0, fcu))
                panels.append(WallPanel("TW3", (offset_x, offset_y + length_y_m), length_x_m, thickness_m, 1.0, 0.0, fcu))
                panels.append(WallPanel("TW4", (offset_x, offset_y), length_y_m, thickness_m, 1.0, 90.0, fcu))
            
        else:
            raise ValueError(f"Unsupported core wall configuration: {config}")
        
        return panels

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
