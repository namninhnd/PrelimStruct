"""
SlabBuilder - Builder for slab shell elements.

This module extracts slab creation logic from model_builder.py,
providing a clean API for creating slab mesh with openings and surface loads.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from src.core.data_models import CoreWallGeometry, GeometryInput, ProjectData
from src.core.constants import CONCRETE_DENSITY
from src.fem.fem_engine import Element, ElementType, FEMModel, SurfaceLoad
from src.fem.materials import ConcreteProperties, get_elastic_membrane_plate_section
if TYPE_CHECKING:
    from src.fem.model_builder import ModelBuilderOptions
from src.fem.slab_element import SlabMeshGenerator, SlabPanel, SlabOpening

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


def _scale_shell_mesh_divisions(base_divisions: int, shell_mesh_density: str) -> int:
    density = _normalize_shell_mesh_density(shell_mesh_density)
    if density == "coarse":
        return max(1, (base_divisions + 1) // 2)
    if density == "fine":
        return max(1, base_divisions * 2)
    return max(1, base_divisions)


def _normalize_shell_mesh_type(shell_mesh_type: str) -> str:
    mesh_type = shell_mesh_type.strip().lower()
    if mesh_type not in {"quad", "tri"}:
        raise ValueError(f"Unsupported shell_mesh_type '{shell_mesh_type}'. Use 'quad' or 'tri'.")
    return mesh_type


class SlabBuilder:
    """Builder for slab shell elements.
    
    This class handles creation of slab mesh using ShellMITC4 elements
    with ElasticMembranePlateSection. Supports core wall openings and
    surface load application.
    
    Attributes:
        model: FEMModel to add slabs to
        project: ProjectData with geometry information
        options: ModelBuilderOptions for configuration
        slab_element_tags: List of slab element tags created
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
        self.slab_element_tags: List[int] = []
        
        # This will be set by setup_section()
        self.slab_section_tag: Optional[int] = None

    def setup_section(self, slab_concrete: ConcreteProperties) -> int:
        """Configure section for slabs.
        
        Args:
            slab_concrete: ConcreteProperties for slab material
            
        Returns:
            Section tag for slabs
        """
        self.slab_section_tag = 5
        slab_section = get_elastic_membrane_plate_section(
            slab_concrete,
            thickness=self.options.slab_thickness,
            section_tag=self.slab_section_tag,
        )
        self.model.add_section(self.slab_section_tag, slab_section)
        return self.slab_section_tag

    def create_slabs(
        self,
        existing_nodes: Dict[Tuple[float, float, float], int],
        registry_nodes_by_floor: Dict[int, List[int]],
        beam_material_tag: int,
        core_offset_x: Optional[float] = None,
        core_offset_y: Optional[float] = None,
        core_internal_opening: Optional[SlabOpening] = None,
    ) -> List[int]:
        """Create all slab elements.
        
        Args:
            existing_nodes: Dictionary mapping coordinates to node tags
            registry_nodes_by_floor: Dictionary to track nodes by floor
            beam_material_tag: Material tag for slab elements
            core_offset_x: X offset of core wall (optional)
            core_offset_y: Y offset of core wall (optional)
            core_internal_opening: SlabOpening for core wall void (optional)
            
        Returns:
            List of slab element tags created
        """
        assert self.slab_section_tag is not None
        
        slab_openings: List[SlabOpening] = []
        if core_internal_opening:
            slab_openings.append(core_internal_opening)
            logger.info(
                f"Slab opening for core: {core_internal_opening.width_x:.2f}m x "
                f"{core_internal_opening.width_y:.2f}m at ({core_internal_opening.origin[0]:.2f}, "
                f"{core_internal_opening.origin[1]:.2f})"
            )

        # Create slab generator
        slab_generator = SlabMeshGenerator(
            base_node_tag=60000,
            base_element_tag=60000,
        )
        shell_mesh_type = _normalize_shell_mesh_type(self.options.shell_mesh_type)

        # Create slab panels for each bay on each floor
        for level in range(1, self.geometry.floors + 1):
            z = level * self.geometry.story_height
            
            for ix in range(self.geometry.num_bays_x):
                for iy in range(self.geometry.num_bays_y):
                    base_origin_x = ix * self.geometry.bay_x
                    base_origin_y = iy * self.geometry.bay_y
                    
                    # Determine sub-panels based on secondary beams
                    sub_panels = self._create_sub_panels(
                        base_origin_x, base_origin_y, ix, iy
                    )
                    
                    for sp in sub_panels:
                        origin = cast(Tuple[float, float], sp["origin"])
                        dims = cast(Tuple[float, float], sp["dims"])
                        suffix = str(sp["suffix"])

                        sp_origin_x, sp_origin_y = origin
                        sp_width_x, sp_width_y = dims
                        
                        slab = SlabPanel(
                            slab_id=f"S{level}_{ix}_{iy}{suffix}",
                            origin=(sp_origin_x, sp_origin_y),
                            width_x=sp_width_x,
                            width_y=sp_width_y,
                            thickness=self.options.slab_thickness,
                            elevation=z,
                            fcu=self.project.materials.fcu_beam,
                        )
                        
                        mesh_result = slab_generator.generate_mesh(
                            slab=slab,
                            floor_level=level,
                            section_tag=self.slab_section_tag,
                            elements_along_x=_scale_shell_mesh_divisions(
                                max(1, int(self.options.slab_elements_per_bay * (sp_width_x / self.geometry.bay_x))),
                                self.options.shell_mesh_density,
                            ),
                            elements_along_y=_scale_shell_mesh_divisions(
                                max(1, int(self.options.slab_elements_per_bay * (sp_width_y / self.geometry.bay_y))),
                                self.options.shell_mesh_density,
                            ),
                            existing_nodes=existing_nodes,
                            openings=slab_openings
                        )
                        
                        # Add new slab nodes to model and existing_nodes lookup
                        for node_data in mesh_result.nodes:
                            tag, x, y, z_coord, floor_lvl = node_data
                            from src.fem.fem_engine import Node
                            node = Node(tag=tag, x=x, y=y, z=z_coord)
                            self.model.add_node(node)
                            existing_nodes[(round(x, 6), round(y, 6), round(z_coord, 6))] = tag
                            
                            # Track in registry for diaphragm
                            if floor_lvl not in registry_nodes_by_floor:
                                registry_nodes_by_floor[floor_lvl] = []
                            registry_nodes_by_floor[floor_lvl].append(tag)
                        
                        # Add slab shell elements and collect tags
                        for elem in mesh_result.elements:
                            if shell_mesh_type == "quad":
                                shell_elements = [
                                    Element(
                                        tag=elem.tag,
                                        element_type=ElementType.SHELL_MITC4,
                                        node_tags=list(elem.node_tags),
                                        material_tag=beam_material_tag,
                                        section_tag=elem.section_tag,
                                    )
                                ]
                            else:
                                n1, n2, n3, n4 = elem.node_tags
                                shell_elements = [
                                    Element(
                                        tag=elem.tag,
                                        element_type=ElementType.SHELL_DKGT,
                                        node_tags=[n1, n2, n3],
                                        material_tag=beam_material_tag,
                                        section_tag=elem.section_tag,
                                    ),
                                    Element(
                                        tag=elem.tag + SHELL_TRI_TAG_OFFSET,
                                        element_type=ElementType.SHELL_DKGT,
                                        node_tags=[n1, n3, n4],
                                        material_tag=beam_material_tag,
                                        section_tag=elem.section_tag,
                                    ),
                                ]

                            for shell_element in shell_elements:
                                self.model.add_element(shell_element)
                                self.slab_element_tags.append(shell_element.tag)
        
        return self.slab_element_tags

    def _create_sub_panels(
        self,
        base_origin_x: float,
        base_origin_y: float,
        ix: int,
        iy: int,
    ) -> List[Dict[str, Any]]:
        """Create sub-panels for a bay based on secondary beam configuration.
        
        Args:
            base_origin_x: Base X origin of the bay
            base_origin_y: Base Y origin of the bay
            ix: Bay index in X direction
            iy: Bay index in Y direction
            
        Returns:
            List of sub-panel dictionaries with 'suffix', 'origin', and 'dims'
        """
        sub_panels: List[Dict[str, Any]] = []
        
        if self.options.num_secondary_beams > 0:
            if self.options.secondary_beam_direction == "Y":
                # Beams run Y-dir, splitting X-dimension
                num_strips = self.options.num_secondary_beams + 1
                strip_width = self.geometry.bay_x / num_strips
                
                for k in range(num_strips):
                    sub_panels.append({
                        "suffix": f"_{k}",
                        "origin": (base_origin_x + k * strip_width, base_origin_y),
                        "dims": (strip_width, self.geometry.bay_y)
                    })
            else:
                # Beams run X-dir, splitting Y-dimension
                num_strips = self.options.num_secondary_beams + 1
                strip_width = self.geometry.bay_y / num_strips
                
                for k in range(num_strips):
                    sub_panels.append({
                        "suffix": f"_{k}",
                        "origin": (base_origin_x, base_origin_y + k * strip_width),
                        "dims": (self.geometry.bay_x, strip_width)
                    })
        else:
            # No secondary beams, single panel per bay
            sub_panels.append({
                "suffix": "",
                "origin": (base_origin_x, base_origin_y),
                "dims": (self.geometry.bay_x, self.geometry.bay_y)
            })
        
        return sub_panels

    def apply_surface_loads(self, slab_element_tags: List[int]) -> None:
        """Apply surface loads to slab elements.
        
        Args:
            slab_element_tags: List of slab element tags to apply loads to
        """
        if not self.options.apply_gravity_loads or not slab_element_tags:
            return
        
        # Calculate design load
        design_load = self._get_slab_design_load()  # kPa
        
        # Apply to each slab element
        for elem_tag in slab_element_tags:
            self.model.add_surface_load(
                SurfaceLoad(
                    element_tag=elem_tag,
                    pressure=design_load * 1000.0,  # Convert kPa to N/m²
                    load_pattern=self.options.dl_load_pattern,
                )
            )
        
        logger.info(
            f"Applied surface loads to {len(slab_element_tags)} slab elements "
            f"({design_load:.2f} kPa)"
        )

    def _get_slab_design_load(self) -> float:
        """Get factored slab load in kPa.
        
        Returns:
            Factored design load in kPa
        """
        # Calculate total dead load
        slab_self_weight = self.options.slab_thickness * CONCRETE_DENSITY  # kPa
        total_dead = self.project.loads.dead_load + slab_self_weight
        total_live = self.project.loads.live_load
        
        # Use HK Code load factors
        from src.core.constants import GAMMA_G, GAMMA_Q
        return GAMMA_G * total_dead + GAMMA_Q * total_live

    def get_element_tags(self) -> List[int]:
        """Get all slab element tags.
        
        Returns:
            List of slab element tags
        """
        return self.slab_element_tags


__all__ = ["SlabBuilder"]
