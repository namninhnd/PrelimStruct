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
from typing import List, Tuple, Optional
import math

from src.core.data_models import (
    CoreWallConfig,
    CoreWallGeometry,
    CouplingBeam,
)


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

        Raises:
            ValueError: If core configuration doesn't have openings
        """
        config = self.core_geometry.config

        if config == CoreWallConfig.I_SECTION:
            # I-section has no door openings, but may have openings in web
            # For now, return empty list (can be extended for web openings)
            return []

        elif config == CoreWallConfig.TWO_C_FACING:
            return self._generate_two_c_facing_beams(
                story_height, top_clearance, bottom_clearance
            )

        elif config == CoreWallConfig.TWO_C_BACK_TO_BACK:
            return self._generate_two_c_back_to_back_beams(
                story_height, top_clearance, bottom_clearance
            )

        elif config == CoreWallConfig.TUBE_CENTER_OPENING:
            return self._generate_tube_center_opening_beams(
                story_height, top_clearance, bottom_clearance
            )

        elif config == CoreWallConfig.TUBE_SIDE_OPENING:
            return self._generate_tube_side_opening_beams(
                story_height, top_clearance, bottom_clearance
            )

        else:
            raise ValueError(f"Unknown core wall configuration: {config}")

    def _generate_two_c_facing_beams(
        self,
        story_height: float,
        top_clearance: float,
        bottom_clearance: float,
    ) -> List[CouplingBeam]:
        """Generate coupling beams for TWO_C_FACING configuration.

        TWO_C_FACING has a central opening between the two C-shaped walls.
        Coupling beams span this opening to provide coupling action.

        Args:
            story_height: Story height in mm
            top_clearance: Top clearance in mm
            bottom_clearance: Bottom clearance in mm

        Returns:
            List containing one coupling beam spanning the central opening
        """
        if self.core_geometry.opening_width is None:
            raise ValueError("TWO_C_FACING requires opening_width")

        opening_width = self.core_geometry.opening_width
        opening_height = (
            self.core_geometry.opening_height
            if self.core_geometry.opening_height is not None
            else story_height - top_clearance - bottom_clearance
        )

        # Clear span is the opening width (distance between wall faces)
        clear_span = opening_width

        # Beam depth is constrained by opening height minus clearances
        beam_depth = opening_height - top_clearance - bottom_clearance

        # Beam width equals wall thickness
        beam_width = self.wall_thickness

        # Location at center of core (simplified - would need actual coordinates)
        location_x = self.core_geometry.length_x / 2.0
        location_y = self.core_geometry.length_y / 2.0

        coupling_beam = CouplingBeam(
            clear_span=clear_span,
            depth=beam_depth,
            width=beam_width,
            location_x=location_x,
            location_y=location_y,
            floor_level=0,  # Will be set per floor in FEM model
            opening_height=opening_height,
        )

        return [coupling_beam]

    def _generate_two_c_back_to_back_beams(
        self,
        story_height: float,
        top_clearance: float,
        bottom_clearance: float,
    ) -> List[CouplingBeam]:
        """Generate coupling beams for TWO_C_BACK_TO_BACK configuration.

        TWO_C_BACK_TO_BACK has two openings (one on each side).
        Coupling beams span both openings.

        Args:
            story_height: Story height in mm
            top_clearance: Top clearance in mm
            bottom_clearance: Bottom clearance in mm

        Returns:
            List containing two coupling beams (one per opening)
        """
        if self.core_geometry.opening_width is None:
            raise ValueError("TWO_C_BACK_TO_BACK requires opening_width")

        opening_width = self.core_geometry.opening_width
        opening_height = (
            self.core_geometry.opening_height
            if self.core_geometry.opening_height is not None
            else story_height - top_clearance - bottom_clearance
        )

        clear_span = opening_width
        beam_depth = opening_height - top_clearance - bottom_clearance
        beam_width = self.wall_thickness

        # Two beams: one at each opening
        # Simplified locations (would need actual wall geometry)
        beams = []

        # Beam 1: Left opening
        beam1 = CouplingBeam(
            clear_span=clear_span,
            depth=beam_depth,
            width=beam_width,
            location_x=self.core_geometry.length_x / 4.0,
            location_y=self.core_geometry.length_y / 2.0,
            floor_level=0,
            opening_height=opening_height,
        )
        beams.append(beam1)

        # Beam 2: Right opening
        beam2 = CouplingBeam(
            clear_span=clear_span,
            depth=beam_depth,
            width=beam_width,
            location_x=3.0 * self.core_geometry.length_x / 4.0,
            location_y=self.core_geometry.length_y / 2.0,
            floor_level=0,
            opening_height=opening_height,
        )
        beams.append(beam2)

        return beams

    def _generate_tube_center_opening_beams(
        self,
        story_height: float,
        top_clearance: float,
        bottom_clearance: float,
    ) -> List[CouplingBeam]:
        """Generate coupling beams for TUBE_CENTER_OPENING configuration.

        TUBE_CENTER_OPENING has a central door/corridor opening.
        One coupling beam spans this opening.

        Args:
            story_height: Story height in mm
            top_clearance: Top clearance in mm
            bottom_clearance: Bottom clearance in mm

        Returns:
            List containing one coupling beam
        """
        if self.core_geometry.opening_width is None:
            raise ValueError("TUBE_CENTER_OPENING requires opening_width")

        opening_width = self.core_geometry.opening_width
        opening_height = (
            self.core_geometry.opening_height
            if self.core_geometry.opening_height is not None
            else story_height - top_clearance - bottom_clearance
        )

        clear_span = opening_width
        beam_depth = opening_height - top_clearance - bottom_clearance
        beam_width = self.wall_thickness

        # Center location
        location_x = self.core_geometry.length_x / 2.0
        location_y = self.core_geometry.length_y / 2.0

        coupling_beam = CouplingBeam(
            clear_span=clear_span,
            depth=beam_depth,
            width=beam_width,
            location_x=location_x,
            location_y=location_y,
            floor_level=0,
            opening_height=opening_height,
        )

        return [coupling_beam]

    def _generate_tube_side_opening_beams(
        self,
        story_height: float,
        top_clearance: float,
        bottom_clearance: float,
    ) -> List[CouplingBeam]:
        """Generate coupling beams for TUBE_SIDE_OPENING configuration.

        TUBE_SIDE_OPENING has an opening in the side flange.
        One coupling beam spans this opening.

        Args:
            story_height: Story height in mm
            top_clearance: Top clearance in mm
            bottom_clearance: Bottom clearance in mm

        Returns:
            List containing one coupling beam
        """
        if self.core_geometry.opening_width is None:
            raise ValueError("TUBE_SIDE_OPENING requires opening_width")

        opening_width = self.core_geometry.opening_width
        opening_height = (
            self.core_geometry.opening_height
            if self.core_geometry.opening_height is not None
            else story_height - top_clearance - bottom_clearance
        )

        clear_span = opening_width
        beam_depth = opening_height - top_clearance - bottom_clearance
        beam_width = self.wall_thickness

        # Side opening location (simplified)
        location_x = self.core_geometry.length_x
        location_y = self.core_geometry.length_y / 2.0

        coupling_beam = CouplingBeam(
            clear_span=clear_span,
            depth=beam_depth,
            width=beam_width,
            location_x=location_x,
            location_y=location_y,
            floor_level=0,
            opening_height=opening_height,
        )

        return [coupling_beam]


def calculate_coupling_beam_properties(beam: CouplingBeam) -> dict:
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
