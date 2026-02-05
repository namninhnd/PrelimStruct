"""
BeamBuilder - Unified beam element creation for FEM models.

This module extracts and unifies the 4x duplicated beam creation code from
model_builder.py, providing a clean API for creating:
- Primary beams (gridline beams in X and Y directions)
- Secondary beams (internal subdivision beams)
- Coupling beams (at core wall openings)

Usage:
    builder = BeamBuilder(model, project, registry, options)
    builder.setup_materials_and_sections(beam_concrete, beam_sizes)
    
    # Create all beam types
    primary_beams = builder.create_primary_beams(core_outline_global)
    secondary_beams = builder.create_secondary_beams(core_outline_global)
    coupling_beams = builder.create_coupling_beams(
        core_geometry, offset_x, offset_y, geometry.story_height
    )
"""

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from src.core.constants import CONCRETE_DENSITY
from src.core.data_models import CoreWallConfig, CoreWallGeometry, GeometryInput, ProjectData
from src.fem.beam_trimmer import BeamConnectionType
from src.fem.model_builder import BeamSegment, trim_beam_segment_against_polygon
from src.fem.coupling_beam import CouplingBeamGenerator
from src.fem.fem_engine import Element, ElementType, FEMModel, UniformLoad
from src.fem.materials import ConcreteProperties, get_elastic_beam_section

if TYPE_CHECKING:
    from src.fem.model_builder import ModelBuilderOptions, NodeRegistry

logger = logging.getLogger(__name__)


@dataclass
class BeamCreationResult:
    """Result of beam creation operation."""
    element_tags: List[int]
    node_tags: List[int]  # Unique nodes created/used
    core_boundary_points: List[Tuple[float, float]]  # Points where beams connect to core


class BeamBuilder:
    """Builder for beam elements in FEM model.
    
    This class unifies the beam creation logic that was previously duplicated
    in model_builder.py for primary beams, secondary beams, and coupling beams.
    
    Attributes:
        model: FEMModel to add beams to
        project: ProjectData with geometry and material info
        registry: NodeRegistry for node creation/reuse
        options: ModelBuilderOptions for configuration
        element_tag: Current element tag counter (starts at provided value)
    """

    def __init__(
        self,
        model: FEMModel,
        project: ProjectData,
        registry: "NodeRegistry",
        options: "ModelBuilderOptions",
        initial_element_tag: int = 1,
    ):
        self.model = model
        self.project = project
        self.registry = registry
        self.options = options
        self.element_tag = initial_element_tag
        self.geometry = project.geometry
        
        # These will be set by setup_materials_and_sections()
        self.beam_material_tag: Optional[int] = None
        self.primary_section_tag: Optional[int] = None
        self.secondary_section_tag: Optional[int] = None
        self.coupling_section_tag: Optional[int] = None
        self.beam_sizes: Optional[Dict[str, Tuple[float, float]]] = None
        self.beam_concrete: Optional[ConcreteProperties] = None

    def setup_materials_and_sections(
        self,
        beam_concrete: ConcreteProperties,
        beam_sizes: Dict[str, Tuple[float, float]],
        beam_material_tag: int = 1,
        primary_section_tag: int = 1,
        secondary_section_tag: int = 2,
    ) -> None:
        """Configure materials and sections for beam creation.
        
        Args:
            beam_concrete: ConcreteProperties for beam material
            beam_sizes: Dict with 'primary' and 'secondary' keys containing (width, depth) in mm
            beam_material_tag: Material tag for beam elements
            primary_section_tag: Section tag for primary beams
            secondary_section_tag: Section tag for secondary beams
        """
        self.beam_concrete = beam_concrete
        self.beam_sizes = beam_sizes
        self.beam_material_tag = beam_material_tag
        self.primary_section_tag = primary_section_tag
        self.secondary_section_tag = secondary_section_tag

    def _create_beam_element(
        self,
        start_node: int,
        end_node: int,
        section_tag: int,
        load_pattern: int = 1,
        section_dims: Optional[Tuple[float, float]] = None,
        geometry_override: Optional[Dict] = None,
    ) -> int:
        """Create a subdivided beam element (6 sub-elements, 7 nodes) and add to model.
        
        This method creates 6 sub-elements between start_node and end_node to enable
        accurate parabolic force diagram visualization using real analysis forces.
        
        Args:
            start_node: Start node tag
            end_node: End node tag
            section_tag: Section tag for the beam
            load_pattern: Load pattern for gravity loads
            section_dims: (width, depth) in mm for self-weight calculation
            geometry_override: Optional geometry dict override
            
        Returns:
            Element tag of first created sub-element (parent beam ID)
        """
        NUM_SUBDIVISIONS = 6
        
        # Get start and end node coordinates
        start_node_obj = self.model.nodes[start_node]
        end_node_obj = self.model.nodes[end_node]
        
        start_x, start_y, start_z = start_node_obj.x, start_node_obj.y, start_node_obj.z
        end_x, end_y, end_z = end_node_obj.x, end_node_obj.y, end_node_obj.z
        
        # Determine floor level from start node elevation
        floor_level = int(round(start_z / self.geometry.story_height))
        
        # Create 5 intermediate nodes + reuse start/end (total 7 nodes)
        node_tags = [start_node]
        
        for i in range(1, NUM_SUBDIVISIONS):
            t = i / NUM_SUBDIVISIONS  # 1/6, 2/6, 3/6, 4/6, 5/6
            inter_x = start_x + t * (end_x - start_x)
            inter_y = start_y + t * (end_y - start_y)
            inter_z = start_z + t * (end_z - start_z)  # Same elevation for horizontal beams
            
            inter_node = self.registry.get_or_create(
                inter_x, inter_y, inter_z, floor_level=floor_level
            )
            node_tags.append(inter_node)
        
        node_tags.append(end_node)
        
        # Track parent beam ID for logical grouping
        parent_beam_id = self.element_tag
        
        # Default geometry
        geom_base = geometry_override if geometry_override else {"local_y": (0.0, 0.0, 1.0)}
        
        # Create 6 sub-elements connecting the 7 nodes sequentially
        for i in range(NUM_SUBDIVISIONS):
            current_tag = self.element_tag
            
            # Add parent beam tracking to geometry metadata
            geom = geom_base.copy()
            geom["parent_beam_id"] = parent_beam_id
            geom["sub_element_index"] = i
            
            self.model.add_element(
                Element(
                    tag=current_tag,
                    element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[node_tags[i], node_tags[i + 1]],
                    material_tag=self.beam_material_tag,
                    section_tag=section_tag,
                    geometry=geom,
                )
            )

            # Apply gravity loads proportionally to each sub-element
            if self.options.apply_gravity_loads and section_dims:
                width_m = section_dims[0] / 1000.0
                depth_m = section_dims[1] / 1000.0
                beam_self_weight = CONCRETE_DENSITY * width_m * depth_m
                w_total = beam_self_weight * 1000.0  # N/m
                
                self.model.add_uniform_load(
                    UniformLoad(
                        element_tag=current_tag,
                        load_type="Gravity",
                        magnitude=w_total,
                        load_pattern=load_pattern,
                    )
                )

            self.element_tag += 1
        
        return parent_beam_id

    def _process_beam_segments(
        self,
        segments: List,
        z: float,
        floor_level: int,
        section_tag: int,
        section_dims: Tuple[float, float],
        core_boundary_points: List[Tuple[float, float]],
        load_pattern: int = 1,
    ) -> List[int]:
        """Process beam segments and create elements.
        
        Args:
            segments: List of BeamSegment objects from trim_beam_segment_against_polygon
            z: Elevation (m)
            floor_level: Floor level number
            section_tag: Section tag for beams
            section_dims: (width, depth) in mm
            core_boundary_points: List to append core boundary connection points
            load_pattern: Load pattern for gravity loads
            
        Returns:
            List of created element tags
        """
        created_elements = []
        
        for segment in segments:
            # Skip very short segments
            if math.hypot(
                segment.end[0] - segment.start[0],
                segment.end[1] - segment.start[1]
            ) <= self.options.tolerance * 1000:
                continue
            
            # Create nodes from segment endpoints
            start_node = self.registry.get_or_create(
                segment.start[0] / 1000.0,
                segment.start[1] / 1000.0,
                z,
                floor_level=floor_level
            )
            end_node = self.registry.get_or_create(
                segment.end[0] / 1000.0,
                segment.end[1] / 1000.0,
                z,
                floor_level=floor_level
            )
            
            # Track core boundary points for moment connections
            if segment.start_connection == BeamConnectionType.MOMENT:
                core_boundary_points.append(segment.start)
            if segment.end_connection == BeamConnectionType.MOMENT:
                core_boundary_points.append(segment.end)
            
            # Create beam element
            elem_tag = self._create_beam_element(
                start_node=start_node,
                end_node=end_node,
                section_tag=section_tag,
                load_pattern=load_pattern,
                section_dims=section_dims,
            )
            created_elements.append(elem_tag)
        
        return created_elements

    def create_primary_beams(
        self,
        core_outline_global: Optional[List[Tuple[float, float]]] = None,
    ) -> BeamCreationResult:
        """Create primary beams along all gridlines.
        
        Creates beams in both X and Y directions at all gridlines.
        These are the main structural beams connecting columns.
        
        Args:
            core_outline_global: Optional core wall outline in mm for beam trimming
            
        Returns:
            BeamCreationResult with created element tags and nodes
        """
        if not self.beam_sizes:
            raise ValueError("Beam sizes not set. Call setup_materials_and_sections() first.")
        
        created_elements = []
        all_nodes = set()
        core_boundary_points = []
        
        section_dims = self.beam_sizes["primary"]
        
        # Beams along X direction (at all Y gridlines)
        for level in range(1, self.geometry.floors + 1):
            z = level * self.geometry.story_height
            
            for iy in range(self.geometry.num_bays_y + 1):
                y = iy * self.geometry.bay_y
                
                for ix in range(self.geometry.num_bays_x):
                    x_start = ix * self.geometry.bay_x
                    x_end = (ix + 1) * self.geometry.bay_x
                    
                    # Trim beam at core wall if needed
                    segments = trim_beam_segment_against_polygon(
                        start=(x_start * 1000.0, y * 1000.0),
                        end=(x_end * 1000.0, y * 1000.0),
                        polygon=core_outline_global if self.options.trim_beams_at_core else None,
                    )
                    
                    elem_tags = self._process_beam_segments(
                        segments=segments,
                        z=z,
                        floor_level=level,
                        section_tag=self.primary_section_tag,
                        section_dims=section_dims,
                        core_boundary_points=core_boundary_points,
                        load_pattern=self.options.dl_load_pattern,
                    )
                    created_elements.extend(elem_tags)
        
        # Beams along Y direction (at all X gridlines)
        for level in range(1, self.geometry.floors + 1):
            z = level * self.geometry.story_height
            
            for ix in range(self.geometry.num_bays_x + 1):
                x = ix * self.geometry.bay_x
                
                for iy in range(self.geometry.num_bays_y):
                    y_start = iy * self.geometry.bay_y
                    y_end = (iy + 1) * self.geometry.bay_y
                    
                    # Trim beam at core wall if needed
                    segments = trim_beam_segment_against_polygon(
                        start=(x * 1000.0, y_start * 1000.0),
                        end=(x * 1000.0, y_end * 1000.0),
                        polygon=core_outline_global if self.options.trim_beams_at_core else None,
                    )
                    
                    elem_tags = self._process_beam_segments(
                        segments=segments,
                        z=z,
                        floor_level=level,
                        section_tag=self.primary_section_tag,
                        section_dims=section_dims,
                        core_boundary_points=core_boundary_points,
                        load_pattern=self.options.dl_load_pattern,
                    )
                    created_elements.extend(elem_tags)
        
        return BeamCreationResult(
            element_tags=created_elements,
            node_tags=list(all_nodes),
            core_boundary_points=core_boundary_points,
        )

    def create_secondary_beams(
        self,
        core_outline_global: Optional[List[Tuple[float, float]]] = None,
    ) -> BeamCreationResult:
        """Create secondary (internal subdivision) beams.
        
        Creates num_secondary_beams internal beams per bay, equally spaced.
        Direction is controlled by options.secondary_beam_direction.
        
        Args:
            core_outline_global: Optional core wall outline in mm for beam trimming
            
        Returns:
            BeamCreationResult with created element tags and nodes
        """
        if not self.beam_sizes:
            raise ValueError("Beam sizes not set. Call setup_materials_and_sections() first.")
        
        if self.options.num_secondary_beams <= 0:
            return BeamCreationResult(element_tags=[], node_tags=[], core_boundary_points=[])
        
        created_elements = []
        all_nodes = set()
        core_boundary_points = []
        
        section_dims = self.beam_sizes["secondary"]
        
        for level in range(1, self.geometry.floors + 1):
            z = level * self.geometry.story_height
            floor_level = level
            
            if self.options.secondary_beam_direction == "Y":
                # Secondary beams run along Y (internal to X bays)
                for ix in range(self.geometry.num_bays_x):
                    x_start_bay = ix * self.geometry.bay_x
                    x_end_bay = (ix + 1) * self.geometry.bay_x
                    
                    for i in range(1, self.options.num_secondary_beams + 1):
                        x = x_start_bay + (i / (self.options.num_secondary_beams + 1)) * self.geometry.bay_x
                        
                        for iy in range(self.geometry.num_bays_y):
                            y_start = iy * self.geometry.bay_y
                            y_end = (iy + 1) * self.geometry.bay_y
                            
                            segments = trim_beam_segment_against_polygon(
                                start=(x * 1000.0, y_start * 1000.0),
                                end=(x * 1000.0, y_end * 1000.0),
                                polygon=core_outline_global if self.options.trim_beams_at_core else None,
                            )
                            
                            elem_tags = self._process_beam_segments(
                                segments=segments,
                                z=z,
                                floor_level=floor_level,
                                section_tag=self.secondary_section_tag,
                                section_dims=section_dims,
                                core_boundary_points=core_boundary_points,
                                load_pattern=self.options.dl_load_pattern,
                            )
                            created_elements.extend(elem_tags)
            
            else:  # secondary_beam_direction == "X"
                # Secondary beams run along X (internal to Y bays)
                for iy in range(self.geometry.num_bays_y):
                    y_start_bay = iy * self.geometry.bay_y
                    y_end_bay = (iy + 1) * self.geometry.bay_y
                    
                    for i in range(1, self.options.num_secondary_beams + 1):
                        y = y_start_bay + (i / (self.options.num_secondary_beams + 1)) * self.geometry.bay_y
                        
                        for ix in range(self.geometry.num_bays_x):
                            x_start = ix * self.geometry.bay_x
                            x_end = (ix + 1) * self.geometry.bay_x
                            
                            segments = trim_beam_segment_against_polygon(
                                start=(x_start * 1000.0, y * 1000.0),
                                end=(x_end * 1000.0, y * 1000.0),
                                polygon=core_outline_global if self.options.trim_beams_at_core else None,
                            )
                            
                            elem_tags = self._process_beam_segments(
                                segments=segments,
                                z=z,
                                floor_level=floor_level,
                                section_tag=self.secondary_section_tag,
                                section_dims=section_dims,
                                core_boundary_points=core_boundary_points,
                                load_pattern=self.options.dl_load_pattern,
                            )
                            created_elements.extend(elem_tags)
        
        return BeamCreationResult(
            element_tags=created_elements,
            node_tags=list(all_nodes),
            core_boundary_points=core_boundary_points,
        )

    def create_coupling_beams(
        self,
        core_geometry: CoreWallGeometry,
        offset_x: float,
        offset_y: float,
        story_height: float,
    ) -> BeamCreationResult:
        """Create coupling beams at core wall openings.
        
        Coupling beams connect wall piers across openings at each floor level.
        
        Args:
            core_geometry: Core wall geometry configuration
            offset_x: X offset of core wall in meters
            offset_y: Y offset of core wall in meters
            story_height: Story height in meters
            
        Returns:
            BeamCreationResult with created element tags and nodes
        """
        if not self.beam_sizes or not self.beam_concrete:
            raise ValueError("Beam materials not set. Call setup_materials_and_sections() first.")
        
        created_elements = []
        all_nodes = set()
        
        # Only create if there's an opening
        if core_geometry.opening_width is None or core_geometry.opening_width <= 0:
            return BeamCreationResult(element_tags=[], node_tags=[], core_boundary_points=[])
        
        # Generate coupling beam geometry
        coupling_beam_generator = CouplingBeamGenerator(core_geometry)
        coupling_beams = coupling_beam_generator.generate_coupling_beams(
            story_height=story_height * 1000.0,  # Convert m to mm
            top_clearance=200.0,
            bottom_clearance=200.0,
        )
        
        if not coupling_beams:
            return BeamCreationResult(element_tags=[], node_tags=[], core_boundary_points=[])
        
        # Create coupling beam section
        self.coupling_section_tag = 20
        coupling_beam_template = coupling_beams[0]
        
        coupling_section = get_elastic_beam_section(
            self.beam_concrete,
            width=coupling_beam_template.width,
            height=coupling_beam_template.depth,
            section_tag=self.coupling_section_tag,
        )
        self.model.add_section(self.coupling_section_tag, coupling_section)
        
        # Generate coupling beams at each floor
        coupling_element_tag = 70000  # Use 70000+ range for coupling beams
        
        for level in range(1, self.geometry.floors + 1):
            z = level * story_height
            
            for cb in coupling_beams:
                # Null safety check for coupling beam properties
                if cb.location_x is None or cb.location_y is None or cb.clear_span is None:
                    logger.warning(
                        f"Skipping coupling beam with invalid properties: "
                        f"loc_x={cb.location_x}, loc_y={cb.location_y}, span={cb.clear_span}"
                    )
                    continue

                # Get beam location (convert mm to m)
                cb_x_center = (cb.location_x / 1000.0) + offset_x
                cb_y_center = (cb.location_y / 1000.0) + offset_y
                
                half_span = (cb.clear_span / 2.0) / 1000.0
                
                # Determine beam orientation based on core config
                if core_geometry.config in (
                    CoreWallConfig.TWO_C_FACING,
                    CoreWallConfig.TUBE_CENTER_OPENING,
                ):
                    # Beam spans along X
                    start_x = cb_x_center - half_span
                    start_y = cb_y_center
                    end_x = cb_x_center + half_span
                    end_y = cb_y_center
                elif core_geometry.config == CoreWallConfig.TUBE_SIDE_OPENING:
                    # Beam spans along Y
                    start_x = cb_x_center
                    start_y = cb_y_center - half_span
                    end_x = cb_x_center
                    end_y = cb_y_center + half_span
                else:
                    # Default: span along X
                    start_x = cb_x_center - half_span
                    start_y = cb_y_center
                    end_x = cb_x_center + half_span
                    end_y = cb_y_center
                
                # Create nodes
                start_node = self.registry.get_or_create(
                    start_x, start_y, z, floor_level=level
                )
                end_node = self.registry.get_or_create(
                    end_x, end_y, z, floor_level=level
                )
                
                # Create coupling beam element using subdivision method (6 sub-elements, 7 nodes)
                # Store original element_tag, use coupling beam range, then restore
                original_element_tag = self.element_tag
                self.element_tag = coupling_element_tag
                
                parent_beam_id = self._create_beam_element(
                    start_node=start_node,
                    end_node=end_node,
                    section_tag=self.coupling_section_tag,
                    load_pattern=self.options.dl_load_pattern,
                    section_dims=(coupling_beam_template.width, coupling_beam_template.depth),
                    geometry_override={"local_y": (0.0, 0.0, 1.0), "coupling_beam": True},
                )
                
                # Restore element_tag and increment coupling beam base
                coupling_element_tag = self.element_tag
                self.element_tag = original_element_tag
                
                created_elements.append(parent_beam_id)
                all_nodes.add(start_node)
                all_nodes.add(end_node)
        
        logger.info(
            f"Generated {len(created_elements)} coupling beam elements "
            f"({len(coupling_beams)} beams per floor × {self.geometry.floors} floors)"
        )
        
        return BeamCreationResult(
            element_tags=created_elements,
            node_tags=list(all_nodes),
            core_boundary_points=[],
        )

    def get_next_element_tag(self) -> int:
        """Get the next available element tag.
        
        Returns:
            Next element tag that will be used
        """
        return self.element_tag


__all__ = ["BeamBuilder", "BeamCreationResult"]
