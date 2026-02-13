"""
Core Wall Geometry Generator for FEM Analysis

This module generates geometric representations and calculates section properties
for typical tall building core wall configurations per Hong Kong design practice.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

from src.core.data_models import CoreWallConfig, CoreWallGeometry, CoreWallSectionProperties, TubeOpeningPlacement
from src.fem.slab_element import SlabOpening


def resolve_i_section_plan_dimensions(
    geometry: CoreWallGeometry,
    *,
    strict: bool = False,
) -> Tuple[float, float]:
    flange_width = geometry.flange_width
    web_length = geometry.web_length

    if strict:
        if flange_width is None or web_length is None:
            raise ValueError("I_SECTION requires flange_width and web_length")
        return flange_width, web_length

    if flange_width is None:
        flange_width = geometry.length_x
    if web_length is None:
        web_length = geometry.length_y

    if flange_width is None or web_length is None:
        raise ValueError("Unable to resolve I_SECTION dimensions")

    return flange_width, web_length


class ISectionCoreWall:
    """I-section core wall geometry generator.

    This represents two parallel walls blended at their ends to form an I-section.
    Common in tall buildings where elevator/stair cores require openings.

    Geometry notation:
    - Flange: Horizontal wall segments at top and bottom of I
    - Web: Vertical wall segment connecting the two flanges
    - Wall thickness: Constant throughout (typically 500mm)

    Reference coordinate system:
    - Origin at bottom-left corner of bounding box
    - X-axis horizontal (along flange width)
    - Y-axis vertical (along web height)

    CANONICAL I-SECTION ORIENTATION CONTRACT (Phase 13A Gate B):

    Plan View Coordinate System:
      - X-axis: Horizontal (flange width direction)  
      - Y-axis: Vertical (web length direction)
      - Origin: Bottom-left corner of bounding box

    Dimension Mapping:
      - flange_width (b_f) = extent in X-direction  
      - web_length (h_w) = extent in Y-direction

    Physical Layout:
      - Bottom flange: y=0 to y=t, spanning x=0 to x=b_f
      - Top flange: y=h_w-t to y=h_w, spanning x=0 to x=b_f
      - Web: x=(b_f-t)/2 to x=(b_f+t)/2, spanning y=t to y=h_w-t

    Wall Panel Simplification (intentional for FEM):
      - IW1: Left flange wall at x=0, full Y height, orientation=90°
      - IW2: Right flange wall at x=b_f, full Y height, orientation=90°
      - IW3: Web wall at y=h_w/2, full X width, orientation=0°

    Coupling Beam Placement:
      - Beam 1: y=0 (bottom), spanning x=0 to x=b_f
      - Beam 2: y=h_w (top), spanning x=0 to x=b_f
    """

    def __init__(self, geometry: CoreWallGeometry):
        """Initialize I-section core wall geometry.

        Args:
            geometry: CoreWallGeometry with config=I_SECTION and required dimensions

        Raises:
            ValueError: If geometry config is not I_SECTION or required dimensions missing
        """
        if geometry.config != CoreWallConfig.I_SECTION:
            raise ValueError(f"Expected I_SECTION config, got {geometry.config}")

        self.geometry = geometry
        self.t = geometry.wall_thickness
        self.b_f, self.h_w = resolve_i_section_plan_dimensions(geometry, strict=True)

    def calculate_area(self) -> float:
        """Calculate gross cross-sectional area of I-section.

        The I-section consists of:
        - Two flanges: 2 × (b_f × t)
        - One web: (h_w - 2×t) × t (excluding overlaps with flanges)

        Returns:
            Cross-sectional area in mm²
        """
        # Two flanges
        area_flanges = 2 * self.b_f * self.t

        # Web (subtract flange thickness to avoid double-counting corners)
        area_web = (self.h_w - 2 * self.t) * self.t

        return area_flanges + area_web

    def calculate_centroid(self) -> Tuple[float, float]:
        """Calculate centroid location of I-section.

        Uses first moment of area method:
        x̄ = (Σ A_i × x_i) / A_total
        ȳ = (Σ A_i × y_i) / A_total

        Due to symmetry about vertical axis, x̄ = b_f / 2

        Returns:
            Tuple of (centroid_x, centroid_y) in mm from bottom-left corner
        """
        # Calculate component areas and their centroids
        # Top flange
        A_top = self.b_f * self.t
        y_top = self.h_w - self.t / 2

        # Web
        A_web = (self.h_w - 2 * self.t) * self.t
        y_web = self.h_w / 2

        # Bottom flange
        A_bot = self.b_f * self.t
        y_bot = self.t / 2

        # Total area
        A_total = self.calculate_area()

        # Centroid (symmetric about vertical axis)
        centroid_x = self.b_f / 2
        centroid_y = (A_top * y_top + A_web * y_web + A_bot * y_bot) / A_total

        return (centroid_x, centroid_y)

    def calculate_second_moment_x(self) -> float:
        """Calculate second moment of area about centroidal X-X axis (I_xx).

        This is the moment of inertia about the horizontal axis through centroid,
        which governs bending resistance in the vertical plane.

        Uses parallel axis theorem:
        I_xx = Σ (I_i + A_i × d_y²)

        where:
        - I_i = local moment of inertia of component i
        - d_y = vertical distance from component centroid to section centroid

        Returns:
            Second moment of area I_xx in mm⁴
        """
        cx, cy = self.calculate_centroid()

        # Top flange (horizontal rectangle: b × h³ / 12)
        A_top = self.b_f * self.t
        I_top_local = self.b_f * self.t**3 / 12
        d_top = (self.h_w - self.t / 2) - cy
        I_top = I_top_local + A_top * d_top**2

        # Web (vertical rectangle rotated 90°)
        h_web = self.h_w - 2 * self.t
        A_web = h_web * self.t
        I_web_local = self.t * h_web**3 / 12
        d_web = 0  # Web centroid coincides with section centroid by symmetry
        I_web = I_web_local + A_web * d_web**2

        # Bottom flange
        A_bot = self.b_f * self.t
        I_bot_local = self.b_f * self.t**3 / 12
        d_bot = (self.t / 2) - cy
        I_bot = I_bot_local + A_bot * d_bot**2

        return I_top + I_web + I_bot

    def calculate_second_moment_y(self) -> float:
        """Calculate second moment of area about centroidal Y-Y axis (I_yy).

        This is the moment of inertia about the vertical axis through centroid,
        which governs bending resistance in the horizontal plane.

        Uses parallel axis theorem:
        I_yy = Σ (I_i + A_i × d_x²)

        Returns:
            Second moment of area I_yy in mm⁴
        """
        cx, cy = self.calculate_centroid()

        # Top flange (horizontal rectangle: h × b³ / 12)
        A_top = self.b_f * self.t
        I_top_local = self.t * self.b_f**3 / 12
        d_top = 0  # Symmetric about Y-axis
        I_top = I_top_local + A_top * d_top**2

        # Web (vertical rectangle at center)
        h_web = self.h_w - 2 * self.t
        A_web = h_web * self.t
        I_web_local = h_web * self.t**3 / 12
        d_web = 0  # Web at section centerline
        I_web = I_web_local + A_web * d_web**2

        # Bottom flange
        A_bot = self.b_f * self.t
        I_bot_local = self.t * self.b_f**3 / 12
        d_bot = 0  # Symmetric about Y-axis
        I_bot = I_bot_local + A_bot * d_bot**2

        return I_top + I_web + I_bot

    def calculate_torsional_constant(self) -> float:
        """Calculate torsional constant J for I-section.

        For thin-walled I-sections, use approximate formula:
        J ≈ (1/3) × Σ (b_i × t_i³)

        where b_i and t_i are the length and thickness of each wall segment.

        This is a simplified formula suitable for preliminary design.
        More accurate formulas exist but require numerical integration.

        Returns:
            Torsional constant J in mm⁴
        """
        # Top flange contribution
        J_top = (1/3) * self.b_f * self.t**3

        # Web contribution
        h_web = self.h_w - 2 * self.t
        J_web = (1/3) * h_web * self.t**3

        # Bottom flange contribution
        J_bot = (1/3) * self.b_f * self.t**3

        return J_top + J_web + J_bot

    def calculate_section_properties(self) -> CoreWallSectionProperties:
        """Calculate all section properties for I-section core wall.

        Returns:
            CoreWallSectionProperties with calculated values
        """
        cx, cy = self.calculate_centroid()

        return CoreWallSectionProperties(
            I_xx=self.calculate_second_moment_x(),
            I_yy=self.calculate_second_moment_y(),
            I_xy=0.0,  # Zero for doubly symmetric sections
            A=self.calculate_area(),
            J=self.calculate_torsional_constant(),
            centroid_x=cx,
            centroid_y=cy,
            shear_center_x=cx,  # Coincides with centroid for doubly symmetric sections
            shear_center_y=cy,
        )

    def get_outline_coordinates(self) -> List[Tuple[float, float]]:
        """Get coordinates of I-section outline for visualization.

        Returns coordinates in counter-clockwise order starting from bottom-left.

        Returns:
            List of (x, y) coordinate tuples in mm
        """
        t = self.t
        b = self.b_f
        h = self.h_w

        # Start from bottom-left, go counter-clockwise
        coords = [
            # Bottom flange
            (0, 0),
            (b, 0),
            (b, t),
            # Right side of web
            ((b + t) / 2, t),
            ((b + t) / 2, h - t),
            # Top flange
            (b, h - t),
            (b, h),
            (0, h),
            (0, h - t),
            # Left side of web
            ((b - t) / 2, h - t),
            ((b - t) / 2, t),
            # Back to start
            (0, t),
            (0, 0),
        ]

        return coords


def calculate_i_section_properties(geometry: CoreWallGeometry) -> CoreWallSectionProperties:
    """Convenience function to calculate I-section properties.

    Args:
        geometry: CoreWallGeometry with config=I_SECTION

    Returns:
        Calculated CoreWallSectionProperties
    """
    i_section = ISectionCoreWall(geometry)
    return i_section.calculate_section_properties()


class TubeWithOpeningsCoreWall:
    """Tube/box core wall geometry with optional top-bot openings."""

    @staticmethod
    def _normalize_opening_placement(placement: TubeOpeningPlacement) -> TubeOpeningPlacement:
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

    def __init__(self, geometry: CoreWallGeometry):
        """Initialize tube core wall with configurable opening placement.

        Args:
            geometry: CoreWallGeometry with config=TUBE_WITH_OPENINGS and required dimensions

        Raises:
            ValueError: If geometry config is not TUBE_WITH_OPENINGS or required dimensions missing
        """
        if geometry.config != CoreWallConfig.TUBE_WITH_OPENINGS:
            raise ValueError(f"Expected TUBE_WITH_OPENINGS config, got {geometry.config}")

        if geometry.length_x is None or geometry.length_y is None:
            raise ValueError("TUBE_WITH_OPENINGS requires length_x and length_y")
        
        self.geometry = geometry
        self.t = geometry.wall_thickness        # Wall thickness
        self.L_x = geometry.length_x            # Outer dimension in X
        self.L_y = geometry.length_y            # Outer dimension in Y
        self.placement = self._normalize_opening_placement(geometry.opening_placement)

        if self.placement == TubeOpeningPlacement.NONE:
            self.w_open = 0.0
            self.h_open = 0.0
            return

        if geometry.opening_width is None or geometry.opening_width <= 0.0:
            raise ValueError("TUBE_WITH_OPENINGS requires opening_width when placement is not NONE")

        opening_height = geometry.opening_height
        if opening_height is None or opening_height <= 0.0:
            opening_height = geometry.opening_width

        if geometry.opening_width >= geometry.length_x - 2 * geometry.wall_thickness:
            raise ValueError("Opening width must be less than inner tube width")

        if opening_height >= geometry.length_y - 2 * geometry.wall_thickness:
            raise ValueError("Opening height must be less than inner tube height")

        self.w_open = geometry.opening_width
        self.h_open = opening_height

    def calculate_area(self) -> float:
        """Calculate gross cross-sectional area of tube with opening(s).

        The tube section consists of:
        - Gross rectangular tube: L_x × L_y
        - Inner void: (L_x - 2×t) × (L_y - 2×t)
        - Minus opening(s): w_open × h_open (×1 or ×2 depending on placement)

        Returns:
            Cross-sectional area in mm²
        """
        area_gross = self.L_x * self.L_y
        area_inner_void = (self.L_x - 2 * self.t) * (self.L_y - 2 * self.t)
        area_tube = area_gross - area_inner_void
        
        opening_count = 0
        if self.placement in {TubeOpeningPlacement.TOP, TubeOpeningPlacement.BOTTOM}:
            opening_count = 1
        elif self.placement == TubeOpeningPlacement.TOP_BOT:
            opening_count = 2

        area_opening = opening_count * self.w_open * self.h_open
        
        return area_tube - area_opening

    def calculate_centroid(self) -> Tuple[float, float]:
        """Calculate centroid location of tube with opening(s).

        For a tube with symmetric opening(s) centered in the plan,
        the centroid remains at the geometric center assuming placement
        maintains symmetry.

        Returns:
            Tuple of (centroid_x, centroid_y) in mm from bottom-left corner
        """
        centroid_x = self.L_x / 2
        centroid_y = self.L_y / 2
        
        return (centroid_x, centroid_y)

    def calculate_second_moment_x(self) -> float:
        """Calculate second moment of area about centroidal X-X axis (I_xx).

        This is the moment of inertia about the horizontal axis through centroid,
        which governs bending resistance in the vertical plane.

        Uses subtraction method:
        I_xx = I_gross_rectangle - I_inner_void - I_opening(s)

        Returns:
            Second moment of area I_xx in mm⁴
        """
        I_gross = (self.L_x * self.L_y**3) / 12
        
        inner_width = self.L_x - 2 * self.t
        inner_height = self.L_y - 2 * self.t
        I_inner = (inner_width * inner_height**3) / 12
        
        opening_count = 0
        if self.placement in {TubeOpeningPlacement.TOP, TubeOpeningPlacement.BOTTOM}:
            opening_count = 1
        elif self.placement == TubeOpeningPlacement.TOP_BOT:
            opening_count = 2
        I_opening = opening_count * (self.w_open * self.h_open**3) / 12
        
        return I_gross - I_inner - I_opening

    def calculate_second_moment_y(self) -> float:
        """Calculate second moment of area about centroidal Y-Y axis (I_yy).

        Uses subtraction method:
        I_yy = I_gross_rectangle - I_inner_void - I_opening(s)

        Returns:
            Second moment of area I_yy in mm⁴
        """
        I_gross = (self.L_y * self.L_x**3) / 12
        
        inner_width = self.L_x - 2 * self.t
        inner_height = self.L_y - 2 * self.t
        I_inner = (inner_height * inner_width**3) / 12
        
        opening_count = 0
        if self.placement in {TubeOpeningPlacement.TOP, TubeOpeningPlacement.BOTTOM}:
            opening_count = 1
        elif self.placement == TubeOpeningPlacement.TOP_BOT:
            opening_count = 2
        I_opening = opening_count * (self.h_open * self.w_open**3) / 12
        
        return I_gross - I_inner - I_opening

    def calculate_torsional_constant(self) -> float:
        """Calculate torsional constant J for tube with opening(s).

        For thin-walled closed sections (tubes), uses approximate formula
        with reduction for opening(s).

        Returns:
            Torsional constant J in mm⁴
        """
        b = self.L_x - self.t
        h = self.L_y - self.t
        
        A_enclosed = b * h
        perimeter_integral = 2 * (b + h) / self.t
        J_tube = (4 * A_enclosed**2) / perimeter_integral
        
        opening_count = 0
        if self.placement in {TubeOpeningPlacement.TOP, TubeOpeningPlacement.BOTTOM}:
            opening_count = 1
        elif self.placement == TubeOpeningPlacement.TOP_BOT:
            opening_count = 2
        opening_ratio = (opening_count * self.w_open * self.h_open) / A_enclosed
        reduction_factor = max(0.3, 1 - 0.7 * opening_ratio)
        
        return J_tube * reduction_factor

    def calculate_section_properties(self) -> CoreWallSectionProperties:
        """Calculate all section properties for tube with opening(s).

        Returns:
            CoreWallSectionProperties with calculated values
        """
        cx, cy = self.calculate_centroid()

        return CoreWallSectionProperties(
            I_xx=self.calculate_second_moment_x(),
            I_yy=self.calculate_second_moment_y(),
            I_xy=0.0,
            A=self.calculate_area(),
            J=self.calculate_torsional_constant(),
            centroid_x=cx,
            centroid_y=cy,
            shear_center_x=cx,
            shear_center_y=cy,
        )

    def get_outline_coordinates(self) -> List[Tuple[float, float]]:
        """Return outer loop plus opening loop(s) for visualization."""
        outer = [
            (0, 0),
            (self.L_x, 0),
            (self.L_x, self.L_y),
            (0, self.L_y),
            (0, 0),
        ]
        
        x_open_start = (self.L_x - self.w_open) / 2
        
        openings = []
        
        if self.placement in {TubeOpeningPlacement.BOTTOM, TubeOpeningPlacement.TOP_BOT}:
            y_bottom = 0.0
            openings.append([
                (x_open_start, y_bottom),
                (x_open_start + self.w_open, y_bottom),
                (x_open_start + self.w_open, y_bottom + self.h_open),
                (x_open_start, y_bottom + self.h_open),
                (x_open_start, y_bottom),
            ])
        if self.placement in {TubeOpeningPlacement.TOP, TubeOpeningPlacement.TOP_BOT}:
            y_top = self.L_y - self.h_open
            openings.append([
                (x_open_start, y_top),
                (x_open_start + self.w_open, y_top),
                (x_open_start + self.w_open, y_top + self.h_open),
                (x_open_start, y_top + self.h_open),
                (x_open_start, y_top),
            ])
        
        result = outer[:]
        for opening_loop in openings:
            result.extend(opening_loop)
        
        return result


def calculate_tube_with_openings_properties(geometry: CoreWallGeometry) -> CoreWallSectionProperties:
    """Convenience function to calculate tube with openings properties.

    Args:
        geometry: CoreWallGeometry with config=TUBE_WITH_OPENINGS

    Returns:
        Calculated CoreWallSectionProperties
    """
    tube_openings = TubeWithOpeningsCoreWall(geometry)
    return tube_openings.calculate_section_properties()



def _get_core_wall_outline(geometry: CoreWallGeometry) -> List[Tuple[float, float]]:
    """Get core wall outline coordinates in mm based on configuration."""
    if geometry.config == CoreWallConfig.I_SECTION:
        generator = ISectionCoreWall(geometry)
    elif geometry.config == CoreWallConfig.TUBE_WITH_OPENINGS:
        generator = TubeWithOpeningsCoreWall(geometry)
    else:
        raise ValueError(f"Unsupported core wall configuration: {geometry.config}")

    return generator.get_outline_coordinates()


def _calculate_core_wall_section_properties(geometry: CoreWallGeometry) -> CoreWallSectionProperties:
    """Calculate core wall section properties based on configuration."""
    if geometry.config == CoreWallConfig.I_SECTION:
        return ISectionCoreWall(geometry).calculate_section_properties()
    if geometry.config == CoreWallConfig.TUBE_WITH_OPENINGS:
        return TubeWithOpeningsCoreWall(geometry).calculate_section_properties()

    raise ValueError(f"Unsupported core wall configuration: {geometry.config}")
