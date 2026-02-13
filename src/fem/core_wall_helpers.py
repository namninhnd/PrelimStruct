"""Core wall helper functions for section properties, outline generation, and coupling beams."""

from typing import Optional, List, Tuple

from src.core.data_models import (
    CoreWallConfig,
    CoreWallGeometry,
    CoreWallSectionProperties,
)
from src.fem.core_wall_geometry import (
    ISectionCoreWall,
    TubeWithOpeningsCoreWall,
)
from src.fem.coupling_beam import CouplingBeamGenerator


def calculate_core_wall_properties(geometry: CoreWallGeometry) -> Optional[CoreWallSectionProperties]:
    """Calculate section properties for core wall geometry.

    Args:
        geometry: CoreWallGeometry with configuration and dimensions

    Returns:
        CoreWallSectionProperties or None if calculation fails
    """
    try:
        if geometry.config == CoreWallConfig.I_SECTION:
            core_wall = ISectionCoreWall(geometry)
        elif geometry.config == CoreWallConfig.TUBE_WITH_OPENINGS:
            core_wall = TubeWithOpeningsCoreWall(geometry)
        else:
            return None
        return core_wall.calculate_section_properties()
    except Exception:
        return None


def get_core_wall_outline(geometry: CoreWallGeometry) -> Optional[List[Tuple[float, float]]]:
    """Get outline coordinates for core wall visualization.

    Args:
        geometry: CoreWallGeometry with configuration and dimensions

    Returns:
        List of (x, y) tuples or None if generation fails
    """
    try:
        if geometry.config == CoreWallConfig.I_SECTION:
            core_wall = ISectionCoreWall(geometry)
        elif geometry.config == CoreWallConfig.TUBE_WITH_OPENINGS:
            core_wall = TubeWithOpeningsCoreWall(geometry)
        else:
            return None
        return core_wall.get_outline_coordinates()
    except Exception:
        return None


def get_coupling_beams(geometry: CoreWallGeometry, story_height: float = 3000.0) -> list:
    """Generate coupling beams for core wall openings.

    Args:
        geometry: CoreWallGeometry with configuration and dimensions
        story_height: Story height in mm (default 3000mm)

    Returns:
        List of CouplingBeam objects or empty list if none
    """
    try:
        generator = CouplingBeamGenerator(geometry)
        return generator.generate_coupling_beams(story_height=story_height)
    except Exception:
        return []
