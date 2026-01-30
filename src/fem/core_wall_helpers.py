"""Core wall helper functions for section properties, outline generation, and coupling beams."""

from typing import Optional, List, Tuple

from src.core.data_models import (
    CoreWallConfig,
    CoreWallGeometry,
    CoreWallSectionProperties,
)
from src.fem.core_wall_geometry import (
    ISectionCoreWall,
    TwoCFacingCoreWall,
    TwoCBackToBackCoreWall,
    TubeCenterOpeningCoreWall,
    TubeSideOpeningCoreWall,
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
            return core_wall.calculate_section_properties()
        elif geometry.config == CoreWallConfig.TWO_C_FACING:
            core_wall = TwoCFacingCoreWall(geometry)
            return core_wall.calculate_section_properties()
        elif geometry.config == CoreWallConfig.TWO_C_BACK_TO_BACK:
            core_wall = TwoCBackToBackCoreWall(geometry)
            return core_wall.calculate_section_properties()
        elif geometry.config == CoreWallConfig.TUBE_CENTER_OPENING:
            core_wall = TubeCenterOpeningCoreWall(geometry)
            return core_wall.calculate_section_properties()
        elif geometry.config == CoreWallConfig.TUBE_SIDE_OPENING:
            core_wall = TubeSideOpeningCoreWall(geometry)
            return core_wall.calculate_section_properties()
        else:
            return None
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
            return core_wall.get_outline_coordinates()
        elif geometry.config == CoreWallConfig.TWO_C_FACING:
            core_wall = TwoCFacingCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        elif geometry.config == CoreWallConfig.TWO_C_BACK_TO_BACK:
            core_wall = TwoCBackToBackCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        elif geometry.config == CoreWallConfig.TUBE_CENTER_OPENING:
            core_wall = TubeCenterOpeningCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        elif geometry.config == CoreWallConfig.TUBE_SIDE_OPENING:
            core_wall = TubeSideOpeningCoreWall(geometry)
            return core_wall.get_outline_coordinates()
        else:
            return None
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
