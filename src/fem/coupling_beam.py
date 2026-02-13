"""
Coupling Beam System for Core Walls

This module generates coupling beams that span openings in core wall configurations.
Coupling beams provide critical coupling action for lateral load resistance in tall
buildings by connecting core wall segments.

Per HK Code 2013:
- Coupling beams are typically deep beams (L/h < 2.0)
- Width equals wall thickness for compatibility
- Require diagonal reinforcement for high shear forces
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import math

from src.core.data_models import (
    CoreWallConfig,
    CoreWallGeometry,
    CouplingBeam,
    TubeOpeningPlacement,
)
from src.fem.core_wall_geometry import resolve_i_section_plan_dimensions


class CouplingBeamGenerator:
    """Generate coupling beams for core wall openings.

    This class detects openings in core wall configurations and automatically
    generates coupling beams spanning those openings. Coupling beams are deep
    beams that connect core wall segments for lateral load resistance.

    Design considerations:
    - Beam width = wall thickness (for compatibility with walls)
    - Beam depth = opening height - clearances (top/bottom cover)
    - Clear span = distance between wall faces
    - Deep beam provisions apply when L/h < 2.0
    """

    def __init__(self, core_geometry: CoreWallGeometry):
        """Initialize coupling beam generator.

        Args:
            core_geometry: Core wall geometry configuration

        Raises:
            ValueError: If core geometry configuration is invalid
        """
        self.core_geometry = core_geometry
        self.wall_thickness = core_geometry.wall_thickness

    def _resolve_core_dimensions(self) -> Tuple[float, float]:
        config = self.core_geometry.config

        if config == CoreWallConfig.I_SECTION:
            return resolve_i_section_plan_dimensions(self.core_geometry)

        length_x = self.core_geometry.length_x
        length_y = self.core_geometry.length_y

        if length_x is not None and length_y is not None:
            return length_x, length_y

        if config == CoreWallConfig.TUBE_WITH_OPENINGS:
            raise ValueError("TUBE_WITH_OPENINGS requires length_x and length_y")

        raise ValueError(f"Unable to resolve core dimensions for configuration: {config}")

    def _resolve_opening_dimensions(
        self,
        story_height: float,
        top_clearance: float,
        bottom_clearance: float,
    ) -> Optional[Tuple[float, float, float]]:
        placement = self._normalize_tube_opening_placement(self.core_geometry.opening_placement)
        if placement == TubeOpeningPlacement.NONE:
            return None

        opening_width = self.core_geometry.opening_width
        if opening_width is None:
            return None
        if opening_width <= 0:
            return None

        opening_height = self.core_geometry.opening_height
        if opening_height is None:
            opening_height = opening_width
        if opening_height <= 0:
            return None

        beam_depth = opening_height - top_clearance - bottom_clearance
        if beam_depth <= 0:
            return None

        return opening_width, opening_height, beam_depth

    @staticmethod
    def _normalize_tube_opening_placement(placement: TubeOpeningPlacement) -> TubeOpeningPlacement:
        if placement == TubeOpeningPlacement.BOTH:
            return TubeOpeningPlacement.TOP_BOT
        if placement in {
            TubeOpeningPlacement.TOP_BOT,
            TubeOpeningPlacement.TOP,
            TubeOpeningPlacement.BOTTOM,
            TubeOpeningPlacement.NONE,
        }:
            return placement
        return TubeOpeningPlacement.NONE

    def generate_coupling_beams(
        self,
        story_height: float = 3000.0,
        top_clearance: float = 200.0,
        bottom_clearance: float = 200.0,
    ) -> List[CouplingBeam]:
        """Generate coupling beams for all openings in core wall.

        Args:
            story_height: Story height in mm (default 3000mm)
            top_clearance: Top clearance from slab soffit to beam top (mm)
            bottom_clearance: Bottom clearance from floor slab to beam bottom (mm)

        Returns:
            List of CouplingBeam objects, one per opening
        """
        config = self.core_geometry.config

        if config == CoreWallConfig.I_SECTION:
            return self._generate_i_section_coupling_beams(
                story_height,
                top_clearance,
                bottom_clearance,
            )

        elif config == CoreWallConfig.TUBE_WITH_OPENINGS:
            return self._generate_tube_with_openings_beams(
                story_height, top_clearance, bottom_clearance
            )

        else:
            raise ValueError(f"Unknown core wall configuration: {config}")

    def _generate_i_section_coupling_beams(
        self,
        story_height: float,
        top_clearance: float,
        bottom_clearance: float,
    ) -> List[CouplingBeam]:
        length_x, length_y = self._resolve_core_dimensions()
        beam_width = self.wall_thickness
        beam_depth = story_height - top_clearance - bottom_clearance
        if beam_depth <= 0:
            return []

        return [
            CouplingBeam(
                clear_span=length_x,
                depth=beam_depth,
                width=beam_width,
                location_x=length_x / 2.0,
                location_y=0.0,
                floor_level=0,
                opening_height=length_y,
            ),
            CouplingBeam(
                clear_span=length_x,
                depth=beam_depth,
                width=beam_width,
                location_x=length_x / 2.0,
                location_y=length_y,
                floor_level=0,
                opening_height=length_y,
            ),
        ]

    def _generate_tube_with_openings_beams(
        self,
        story_height: float,
        top_clearance: float,
        bottom_clearance: float,
    ) -> List[CouplingBeam]:
        opening_data = self._resolve_opening_dimensions(
            story_height, top_clearance, bottom_clearance
        )
        if opening_data is None:
            return []
        opening_width, opening_height, beam_depth = opening_data

        clear_span = opening_width
        beam_width = self.wall_thickness

        length_x, length_y = self._resolve_core_dimensions()
        placement = self._normalize_tube_opening_placement(self.core_geometry.opening_placement)

        beams: List[CouplingBeam] = []

        if placement in {TubeOpeningPlacement.TOP, TubeOpeningPlacement.TOP_BOT}:
            beams.append(CouplingBeam(
                clear_span=clear_span,
                depth=beam_depth,
                width=beam_width,
                location_x=length_x / 2.0,
                location_y=length_y,
                floor_level=0,
                opening_height=opening_height,
            ))
        if placement in {TubeOpeningPlacement.BOTTOM, TubeOpeningPlacement.TOP_BOT}:
            beams.append(CouplingBeam(
                clear_span=clear_span,
                depth=beam_depth,
                width=beam_width,
                location_x=length_x / 2.0,
                location_y=0.0,
                floor_level=0,
                opening_height=opening_height,
            ))

        return beams


def calculate_coupling_beam_properties(beam: CouplingBeam) -> Dict[str, Any]:
    """Calculate key properties for coupling beam analysis.

    Args:
        beam: CouplingBeam instance

    Returns:
        Dictionary containing:
        - span_to_depth_ratio: L/h ratio
        - is_deep_beam: Boolean indicating deep beam status
        - gross_area: Gross cross-sectional area (mm²)
        - second_moment: Second moment of area I_xx (mm⁴)
    """
    L_over_h = beam.span_to_depth_ratio
    is_deep = beam.is_deep_beam

    # Gross section properties (uncracked)
    gross_area = beam.width * beam.depth
    second_moment = (beam.width * beam.depth**3) / 12.0

    return {
        "span_to_depth_ratio": L_over_h,
        "is_deep_beam": is_deep,
        "gross_area": gross_area,
        "second_moment": second_moment,
    }
