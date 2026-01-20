"""
Core Wall Geometry Generator for FEM Analysis

This module generates geometric representations and calculates section properties
for typical tall building core wall configurations per Hong Kong design practice.
"""

from dataclasses import dataclass
from typing import List, Tuple
import math

from src.core.data_models import CoreWallConfig, CoreWallGeometry, CoreWallSectionProperties


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

        if geometry.flange_width is None or geometry.web_length is None:
            raise ValueError("I_SECTION requires flange_width and web_length")

        self.geometry = geometry
        self.t = geometry.wall_thickness
        self.b_f = geometry.flange_width  # Flange width
        self.h_w = geometry.web_length    # Web length (height)

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
