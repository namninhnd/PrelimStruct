"""
ColumnBuilder - Builder for column elements with omission support.

This module extracts column creation logic from model_builder.py,
providing a clean API for creating columns with support for column
omissions near core walls and ghost column tracking.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from src.core.data_models import GeometryInput, ProjectData
from src.fem.fem_engine import Element, ElementType, FEMModel

if TYPE_CHECKING:
    from src.fem.model_builder import ModelBuilderOptions, NodeRegistry

logger = logging.getLogger(__name__)


class ColumnBuilder:
    """Builder for column elements with omission support.
    
    This class handles column creation with support for omitting columns
    near core walls. Omitted columns are tracked as "ghost" columns for
    visualization purposes.
    
    Attributes:
        model: FEMModel to add columns to
        project: ProjectData with geometry information
        options: ModelBuilderOptions for configuration
        element_tag: Current element tag counter
    """

    def __init__(
        self,
        model: FEMModel,
        project: ProjectData,
        options: "ModelBuilderOptions",
        initial_element_tag: int = 1,
    ):
        self.model = model
        self.project = project
        self.options = options
        self.element_tag = initial_element_tag
        self.geometry = project.geometry

    def create_columns(
        self,
        grid_nodes: Dict[Tuple[int, int, int], int],
        column_material_tag: int,
        column_section_tag: int,
        omit_column_ids: Optional[Set[str]] = None,
        registry: Optional["NodeRegistry"] = None,
    ) -> int:
        """Create all columns for the building with subdivision.
        
        Creates columns connecting grid nodes between floor levels.
        Each column is subdivided into 4 sub-elements (5 nodes) for accurate
        force diagram visualization.
        
        Columns in the omit_column_ids set are skipped and tracked as ghost columns.
        
        Args:
            grid_nodes: Dictionary mapping (ix, iy, level) to node tag
            column_material_tag: Material tag for columns
            column_section_tag: Section tag for columns
            omit_column_ids: Set of column IDs to omit (e.g., {"A-1", "B-2"})
            registry: NodeRegistry for creating intermediate nodes
            
        Returns:
            Next available element tag after column creation
        """
        if omit_column_ids is None:
            omit_column_ids = set()
        
        omitted_columns: List[str] = []
        NUM_SUBDIVISIONS = 4  # 4 sub-elements, 5 nodes
        
        for level in range(self.geometry.floors):
            for ix in range(self.geometry.num_bays_x + 1):
                for iy in range(self.geometry.num_bays_y + 1):
                    # Generate column ID for omission check
                    col_letter = chr(65 + ix)  # 65 = 'A'
                    col_id = f"{col_letter}-{iy + 1}"
                    
                    # Check if this column should be omitted
                    if col_id in omit_column_ids:
                        if level == 0:  # Only log once (at base level)
                            omitted_columns.append(col_id)
                        continue  # Skip this column
                    
                    start_node = grid_nodes[(ix, iy, level)]
                    end_node = grid_nodes[(ix, iy, level + 1)]
                    
                    # Get start and end node coordinates
                    start_node_obj = self.model.nodes[start_node]
                    end_node_obj = self.model.nodes[end_node]
                    
                    start_x, start_y, start_z = start_node_obj.x, start_node_obj.y, start_node_obj.z
                    end_x, end_y, end_z = end_node_obj.x, end_node_obj.y, end_node_obj.z
                    
                    # Create 3 intermediate nodes + reuse start/end (total 5 nodes)
                    node_tags = [start_node]
                    
                    if registry:
                        for i in range(1, NUM_SUBDIVISIONS):
                            t = i / NUM_SUBDIVISIONS  # 1/4 to 3/4
                            inter_x = start_x + t * (end_x - start_x)
                            inter_y = start_y + t * (end_y - start_y)
                            inter_z = start_z + t * (end_z - start_z)  # Z is vertical for columns
                            
                            inter_node = registry.get_or_create(
                                inter_x, inter_y, inter_z, floor_level=level
                            )
                            node_tags.append(inter_node)
                    
                    node_tags.append(end_node)
                    
                    parent_column_id = self.element_tag
                    
                    if registry:
                        for i in range(NUM_SUBDIVISIONS):
                            current_tag = self.element_tag

                            # Column local axis convention (ETABS-compatible):
                            # local_x = vertical column axis (bottom -> top),
                            # local_y = global X (depth h), local_z = global Y (width b).
                            # vecxz=(0,1,0) enforces this orientation for vertical columns.
                            # Iz = b*h^3/12 -> Mz (major-axis), Iy = h*b^3/12 -> My (minor-axis).
                            geom: Dict[str, Any] = {"vecxz": (0.0, 1.0, 0.0)}
                            geom["parent_column_id"] = parent_column_id
                            geom["sub_element_index"] = i
                            
                            self.model.add_element(
                                Element(
                                    tag=current_tag,
                                    element_type=ElementType.ELASTIC_BEAM,
                                    node_tags=[node_tags[i], node_tags[i + 1]],
                                    material_tag=column_material_tag,
                                    section_tag=column_section_tag,
                                    geometry=geom,
                                )
                            )
                            
                            self.element_tag += 1
                    else:
                        # Same column axis convention as subdivided path:
                        # vecxz=(0,1,0) => local_y=global X (depth h), local_z=global Y (width b).
                        self.model.add_element(
                            Element(
                                tag=self.element_tag,
                                element_type=ElementType.ELASTIC_BEAM,
                                node_tags=[start_node, end_node],
                                material_tag=column_material_tag,
                                section_tag=column_section_tag,
                                geometry={"vecxz": (0.0, 1.0, 0.0)},
                            )
                        )
                        self.element_tag += 1
        
        # Log omitted columns and add to model for ghost visualization
        if omitted_columns:
            logger.info(
                f"Omitted {len(omitted_columns)} columns near core wall: {', '.join(omitted_columns)}"
            )
            
            # Add ghost column locations for visualization
            for col_id in omitted_columns:
                # Parse column ID (e.g., "A-1" -> ix=0, iy=0)
                col_letter = col_id.split('-')[0]
                col_number = int(col_id.split('-')[1])
                ix = ord(col_letter) - 65  # 'A' = 0
                iy = col_number - 1
                
                x = ix * self.geometry.bay_x
                y = iy * self.geometry.bay_y
                
                self.model.omitted_columns.append({
                    "x": x,
                    "y": y,
                    "id": col_id,
                })
        
        return self.element_tag

    def get_next_element_tag(self) -> int:
        """Get the next available element tag.
        
        Returns:
            Next element tag that will be used
        """
        return self.element_tag


__all__ = ["ColumnBuilder"]
