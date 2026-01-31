"""
FEM Builders package - Modular builders for FEM model components.

This package provides builder classes for creating specific components
of FEM models in a modular, testable way using the Builder pattern.

Available builders:
- BeamBuilder: Creates beam elements (primary, secondary, coupling)
- ColumnBuilder: Creates column elements with omission support
- CoreWallBuilder: Creates core wall shell elements
- NodeGridBuilder: Creates node grids with floor-based numbering
- SlabBuilder: Creates slab shell elements with surface loads

Example usage:
    from src.fem.builders import BeamBuilder, ColumnBuilder
    
Note: FEMModelDirector must be imported separately to avoid circular imports:
    from src.fem.builders.director import FEMModelDirector
"""

from src.fem.builders.beam_builder import BeamBuilder, BeamCreationResult
from src.fem.builders.column_builder import ColumnBuilder
from src.fem.builders.core_wall_builder import CoreWallBuilder
from src.fem.builders.node_grid_builder import NodeGridBuilder
from src.fem.builders.slab_builder import SlabBuilder

__all__ = [
    # Builders
    "BeamBuilder",
    "BeamCreationResult",
    "ColumnBuilder",
    "CoreWallBuilder",
    "NodeGridBuilder",
    "SlabBuilder",
]
