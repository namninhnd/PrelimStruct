"""
FEMModelDirector - Director for orchestrating FEM model building.

This module implements the Director pattern to coordinate all builders
for creating a complete FEM model. It replaces the monolithic
build_fem_model() function with a clean, orchestrated approach.

Usage:
    director = FEMModelDirector(project, options)
    model = director.build()
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from src.core.data_models import ProjectData

from src.fem.model_builder import trim_beam_segment_against_polygon
from src.fem.builders.beam_builder import BeamBuilder
from src.fem.builders.column_builder import ColumnBuilder
from src.fem.builders.core_wall_builder import CoreWallBuilder
from src.fem.builders.node_grid_builder import NodeGridBuilder
from src.fem.builders.slab_builder import SlabBuilder
from src.fem.fem_engine import FEMModel
from src.fem.materials import ConcreteProperties
from src.fem.model_builder import (
    ModelBuilderOptions,
    NodeRegistry,
    _extract_beam_sizes,
    _extract_column_dims,
    _get_core_wall_offset,
    _get_core_wall_outline,
    _get_core_opening_for_slab,
    _compute_floor_shears,
    _compute_wtz_torsional_moments,
    create_floor_rigid_diaphragms,
    apply_lateral_loads_to_diaphragms,
)

logger = logging.getLogger(__name__)


class FEMModelDirector:
    """Director for orchestrating FEM model construction.
    
    This class coordinates all builders to create a complete FEM model:
    1. NodeGridBuilder - Creates grid nodes
    2. ColumnBuilder - Creates columns with omission support
    3. BeamBuilder - Creates primary, secondary, and coupling beams
    4. CoreWallBuilder - Creates core wall shell elements
    5. SlabBuilder - Creates slab shell elements
    
    Attributes:
        project: ProjectData with all inputs
        options: ModelBuilderOptions for configuration
        model: FEMModel being constructed
    """

    def __init__(
        self,
        project: ProjectData,
        options: Optional[ModelBuilderOptions] = None,
    ):
        self.project = project
        self.options = options or ModelBuilderOptions()
        self.model = FEMModel()
        self.registry: Optional[NodeRegistry] = None
        
        # Material and section tags (must match original for compatibility)
        self.beam_material_tag = 1
        self.column_material_tag = 2
        self.beam_sizes = _extract_beam_sizes(project)
        self.column_width, self.column_depth = _extract_column_dims(project)

    def build(self) -> FEMModel:
        """Build the complete FEM model.
        
        Returns:
            Fully constructed FEMModel
        """
        logger.info("Starting FEM model construction with Director pattern")
        
        # Phase 1: Setup
        self._setup_materials()
        self.registry = NodeRegistry(self.model, tolerance=self.options.tolerance)
        
        # Phase 2: Create nodes
        grid_nodes = self._build_nodes()
        
        # Phase 3: Create elements
        element_tag = self._build_columns(grid_nodes)
        element_tag = self._build_beams(element_tag)
        
        if self.options.include_core_wall and self.project.lateral.core_geometry:
            self._build_core_walls()
        
        if self.options.include_slabs:
            self._build_slabs()
        
        # Phase 4: Apply loads
        self._apply_loads()
        
        # Phase 5: Validation
        is_valid, errors = self.model.validate_model()
        if not is_valid:
            for error in errors:
                logger.warning(f"Model validation warning: {error}")
        
        logger.info("FEM model construction complete")
        return self.model

    def _require_registry(self) -> NodeRegistry:
        if self.registry is None:
            raise RuntimeError("Node registry has not been initialized")
        return self.registry

    def _setup_materials(self) -> None:
        """Setup materials and sections."""
        beam_concrete = ConcreteProperties(fcu=self.project.materials.fcu_beam)
        column_concrete = ConcreteProperties(fcu=self.project.materials.fcu_column)
        
        # Add concrete materials
        self.model.add_material(self.beam_material_tag, {
            "material_type": "Concrete01",
            "tag": self.beam_material_tag,
            "fpc": -beam_concrete.design_strength * 1e6,
            "epsc0": -0.002,
            "fpcu": -0.85 * beam_concrete.design_strength * 1e6,
            "epsU": -0.0035,
        })
        self.model.add_material(self.column_material_tag, {
            "material_type": "Concrete01",
            "tag": self.column_material_tag,
            "fpc": -column_concrete.design_strength * 1e6,
            "epsc0": -0.002,
            "fpcu": -0.85 * column_concrete.design_strength * 1e6,
            "epsU": -0.0035,
        })
        
        # Add beam/column sections
        from src.fem.materials import get_elastic_beam_section
        primary_section = get_elastic_beam_section(
            beam_concrete,
            width=self.beam_sizes["primary"][0],
            height=self.beam_sizes["primary"][1],
            section_tag=1,
        )
        secondary_section = get_elastic_beam_section(
            beam_concrete,
            width=self.beam_sizes["secondary"][0],
            height=self.beam_sizes["secondary"][1],
            section_tag=2,
        )
        # Column section mapping uses width=b (local_z) and depth=h (local_y)
        # so Iz=b*h^3/12 remains the major-axis stiffness (Mz convention).
        column_section = get_elastic_beam_section(
            column_concrete,
            width=self.column_width,
            height=self.column_depth,
            section_tag=3,
        )
        
        self.model.add_section(1, primary_section)
        self.model.add_section(2, secondary_section)
        self.model.add_section(3, column_section)

    def _build_nodes(self) -> Dict[Tuple[int, int, int], int]:
        """Build all nodes for the model.
        
        Returns:
            Dictionary mapping (ix, iy, level) to node tag
        """
        registry = self._require_registry()
        node_builder = NodeGridBuilder(
            model=self.model,
            project=self.project,
            registry=registry,
        )
        return node_builder.create_grid_nodes()

    def _build_columns(
        self,
        grid_nodes: Dict[Tuple[int, int, int], int]
    ) -> int:
        """Build all columns for the model.
        
        Args:
            grid_nodes: Dictionary mapping (ix, iy, level) to node tag
            
        Returns:
            Next available element tag
        """
        # Prepare column omission logic
        omit_column_ids: Set[str] = set()
        
        if (self.options.omit_columns_near_core and 
            self.options.include_core_wall and 
            self.project.lateral.core_geometry):
            # Use user-approved omission list
            omit_column_ids = set(self.options.suggested_omit_columns)
        
        registry = self._require_registry()

        column_builder = ColumnBuilder(
            model=self.model,
            project=self.project,
            options=self.options,
            initial_element_tag=1,
        )
        
        return column_builder.create_columns(
            grid_nodes=grid_nodes,
            column_material_tag=self.column_material_tag,
            column_section_tag=3,
            omit_column_ids=omit_column_ids,
            registry=registry,
        )

    def _build_beams(self, initial_element_tag: int) -> int:
        """Build all beams for the model.
        
        Args:
            initial_element_tag: Starting element tag
            
        Returns:
            Next available element tag
        """
        # Prepare core outline for beam trimming
        core_outline_global: Optional[List[Tuple[float, float]]] = None
        
        if self.options.trim_beams_at_core and not self.project.lateral.core_geometry:
            logger.warning(
                "Beam trimming requested but core_geometry is None. "
                "Beams will not be trimmed."
            )
        
        if self.options.include_core_wall and self.project.lateral.core_geometry:
            outline = _get_core_wall_outline(self.project.lateral.core_geometry)
            offset_x, offset_y = _get_core_wall_offset(
                self.project, outline, self.options.edge_clearance_m
            )
            core_outline_global = [
                (x + offset_x * 1000.0, y + offset_y * 1000.0) for x, y in outline
            ]
        
        registry = self._require_registry()

        beam_builder = BeamBuilder(
            model=self.model,
            project=self.project,
            registry=registry,
            options=self.options,
            initial_element_tag=initial_element_tag,
        )
        
        beam_concrete = ConcreteProperties(fcu=self.project.materials.fcu_beam)
        beam_builder.setup_materials_and_sections(
            beam_concrete=beam_concrete,
            beam_sizes=self.beam_sizes,
            beam_material_tag=self.beam_material_tag,
            primary_section_tag=1,
            secondary_section_tag=2,
        )
        
        # Create primary and secondary beams
        beam_builder.create_primary_beams(core_outline_global)
        beam_builder.create_secondary_beams(core_outline_global)
        
        return beam_builder.get_next_element_tag()

    def _build_core_walls(self) -> None:
        """Build core wall shell elements."""
        assert self.project.lateral.core_geometry is not None
        
        wall_concrete = ConcreteProperties(fcu=self.project.materials.fcu_column)
        
        core_builder = CoreWallBuilder(
            model=self.model,
            project=self.project,
            options=self.options,
        )
        core_builder.setup_materials(wall_concrete)
        
        # Get wall offset
        outline = _get_core_wall_outline(self.project.lateral.core_geometry)
        offset_x, offset_y = _get_core_wall_offset(
            self.project, outline, self.options.edge_clearance_m
        )
        
        # Create wall elements
        registry = self._require_registry()

        core_builder.create_core_walls(
            offset_x=offset_x,
            offset_y=offset_y,
            registry_nodes_by_floor=registry.nodes_by_floor,
            registry=registry,
        )
        
        # Create coupling beams using BeamBuilder
        beam_builder = BeamBuilder(
            model=self.model,
            project=self.project,
            registry=registry,
            options=self.options,
            initial_element_tag=1,  # Tag not used for coupling beams
        )
        beam_builder.setup_materials_and_sections(
            beam_concrete=ConcreteProperties(fcu=self.project.materials.fcu_beam),
            beam_sizes=self.beam_sizes,
            beam_material_tag=self.beam_material_tag,
            primary_section_tag=1,
            secondary_section_tag=2,
        )
        beam_builder.create_coupling_beams(
            core_geometry=self.project.lateral.core_geometry,
            offset_x=offset_x,
            offset_y=offset_y,
            story_height=self.project.geometry.story_height,
        )

    def _build_slabs(self) -> None:
        """Build slab shell elements."""
        slab_concrete = ConcreteProperties(fcu=self.project.materials.fcu_beam)
        
        slab_builder = SlabBuilder(
            model=self.model,
            project=self.project,
            options=self.options,
        )
        slab_builder.setup_section(slab_concrete)
        
        # Build existing node lookup
        existing_nodes: Dict[Tuple[float, float, float], int] = {}
        for node in self.model.nodes.values():
            key = (round(node.x, 6), round(node.y, 6), round(node.z, 6))
            existing_nodes[key] = node.tag
        
        # Get core opening if applicable
        core_internal_opening = None
        if self.options.include_core_wall and self.project.lateral.core_geometry:
            outline = _get_core_wall_outline(self.project.lateral.core_geometry)
            core_offset_x, core_offset_y = _get_core_wall_offset(
                self.project, outline, self.options.edge_clearance_m
            )
            core_internal_opening = _get_core_opening_for_slab(
                self.project.lateral.core_geometry,
                core_offset_x,
                core_offset_y,
            )
        
        # Create slabs
        registry = self._require_registry()

        slab_element_tags = slab_builder.create_slabs(
            existing_nodes=existing_nodes,
            registry_nodes_by_floor=registry.nodes_by_floor,
            beam_material_tag=self.beam_material_tag,
            core_internal_opening=core_internal_opening,
        )
        
        # Apply surface loads
        slab_builder.apply_surface_loads(slab_element_tags)

    def _apply_loads(self) -> None:
        """Apply loads to the model."""
        master_by_level: Dict[float, int] = {}

        # Apply rigid diaphragms
        if self.options.apply_rigid_diaphragms:
            floor_elevations = [
                level * self.project.geometry.story_height
                for level in range(1, self.project.geometry.floors + 1)
            ]
            master_by_level = create_floor_rigid_diaphragms(
                self.model,
                base_elevation=0.0,
                tolerance=self.options.tolerance,
                floor_elevations=floor_elevations,
                story_height=self.project.geometry.story_height,
            )
        
        # Apply wind loads
        if self.options.apply_wind_loads:
            wind_result = self.project.wind_result
            if wind_result is None:
                import warnings
                warnings.warn(
                    "apply_wind_loads=True but project.wind_result is None. "
                    "Skipping wind loads. V3.5: Calculate wind loads before FEM analysis.",
                    UserWarning
                )
            else:
                if wind_result.base_shear_x > 0.0 or wind_result.base_shear_y > 0.0:
                    base_shear_x = wind_result.base_shear_x
                    base_shear_y = wind_result.base_shear_y
                else:
                    base_shear_x = wind_result.base_shear
                    base_shear_y = wind_result.base_shear

                floor_shears_x = _compute_floor_shears(
                    base_shear_x,
                    self.project.geometry.story_height,
                    self.project.geometry.floors
                )

                floor_shears_y = _compute_floor_shears(
                    base_shear_y,
                    self.project.geometry.story_height,
                    self.project.geometry.floors
                )

                building_width = self.project.lateral.building_width
                if building_width <= 0.0:
                    building_width = self.project.geometry.bay_x * self.project.geometry.num_bays_x

                building_depth = self.project.lateral.building_depth
                if building_depth <= 0.0:
                    building_depth = self.project.geometry.bay_y * self.project.geometry.num_bays_y

                if floor_shears_x:
                    apply_lateral_loads_to_diaphragms(
                        self.model,
                        floor_shears=floor_shears_x,
                        direction="X",
                        load_pattern=self.options.wx_pattern,
                        tolerance=self.options.tolerance,
                        master_lookup=master_by_level if master_by_level else None,
                    )

                if floor_shears_y:
                    apply_lateral_loads_to_diaphragms(
                        self.model,
                        floor_shears=floor_shears_y,
                        direction="Y",
                        load_pattern=self.options.wy_pattern,
                        tolerance=self.options.tolerance,
                        master_lookup=master_by_level if master_by_level else None,
                    )

                torsional_moments, _ = _compute_wtz_torsional_moments(
                    floor_shears_x=floor_shears_x,
                    floor_shears_y=floor_shears_y,
                    building_width=building_width,
                    building_depth=building_depth,
                )
                if torsional_moments:
                    apply_lateral_loads_to_diaphragms(
                        self.model,
                        floor_shears={},
                        direction="X",
                        load_pattern=self.options.wtz_pattern,
                        tolerance=self.options.tolerance,
                        master_lookup=master_by_level if master_by_level else None,
                        torsional_moments=torsional_moments,
                    )


__all__ = ["FEMModelDirector"]
