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


class TwoCFacingCoreWall:
    """Two C-shaped core walls facing each other geometry generator.

    This configuration represents two C-shaped walls arranged to face each other,
    creating an opening in the middle. Common in tall buildings with central
    corridors or lift lobbies between the two C-walls.

    Geometry notation:
    - Each C-wall consists of: 2 flanges + 1 web
    - Left C-wall: opens to the right (facing right)
    - Right C-wall: opens to the left (facing left)
    - Opening: Clear space between the two C-walls
    - Wall thickness: Constant throughout (typically 500mm)

    Coordinate system:
    - Origin at bottom-left corner of bounding box
    - X-axis horizontal (along total width)
    - Y-axis vertical (along height)
    
    Configuration:
        Left C (opening to right):
        ┌──────┐
        │      
        │      
        │      
        └──────┘
        
        <--opening width-->
        
        Right C (opening to left):
               ┌──────┐
                      │
                      │
                      │
               └──────┘
    """

    def __init__(self, geometry: CoreWallGeometry):
        """Initialize two C-shaped facing core walls geometry.

        Args:
            geometry: CoreWallGeometry with config=TWO_C_FACING and required dimensions

        Raises:
            ValueError: If geometry config is not TWO_C_FACING or required dimensions missing
        """
        if geometry.config != CoreWallConfig.TWO_C_FACING:
            raise ValueError(f"Expected TWO_C_FACING config, got {geometry.config}")

        if geometry.flange_width is None or geometry.web_length is None:
            raise ValueError("TWO_C_FACING requires flange_width and web_length")
        
        if geometry.opening_width is None:
            raise ValueError("TWO_C_FACING requires opening_width")

        self.geometry = geometry
        self.t = geometry.wall_thickness       # Wall thickness
        self.b_f = geometry.flange_width       # Flange width (for each C)
        self.h_w = geometry.web_length         # Web height/length (vertical dimension)
        self.opening = geometry.opening_width  # Opening width between the two C-walls

    def calculate_area(self) -> float:
        """Calculate gross cross-sectional area of two C-shaped walls facing each other.

        Each C-section consists of:
        - Two flanges (top and bottom): 2 × (b_f × t)
        - One web (connecting flanges): (h_w - 2×t) × t

        Total area = 2 × (area of one C)

        Returns:
            Cross-sectional area in mm²
        """
        # One C-section area (same as I-section calculation)
        # Two flanges + one web
        area_one_c = 2 * self.b_f * self.t + (self.h_w - 2 * self.t) * self.t
        
        # Two C-sections
        return 2 * area_one_c

    def calculate_centroid(self) -> Tuple[float, float]:
        """Calculate centroid location of two C-sections facing each other.

        Uses first moment of area method for each component.
        Due to double symmetry (both horizontal and vertical), 
        centroid is at geometric center of bounding box.

        Total width = 2 × b_f + opening_width
        Total height = h_w

        Returns:
            Tuple of (centroid_x, centroid_y) in mm from bottom-left corner
        """
        # Total bounding box dimensions
        total_width = 2 * self.b_f + self.opening
        
        # By double symmetry, centroid is at center
        centroid_x = total_width / 2
        centroid_y = self.h_w / 2
        
        return (centroid_x, centroid_y)

    def calculate_second_moment_x(self) -> float:
        """Calculate second moment of area about centroidal X-X axis (I_xx).

        This is the moment of inertia about the horizontal axis through centroid,
        which governs bending resistance in the vertical plane.

        Uses parallel axis theorem for each component of both C-sections:
        I_xx = Σ (I_i + A_i × d_y²)

        Returns:
            Second moment of area I_xx in mm⁴
        """
        cx, cy = self.calculate_centroid()
        I_xx_total = 0.0

        # Process both C-sections (left and right are symmetric about Y-axis)
        # Each C has: top flange, web, bottom flange
        
        # For one C-section:
        # Top flange
        A_top = self.b_f * self.t
        I_top_local = self.b_f * self.t**3 / 12
        d_top = (self.h_w - self.t / 2) - cy
        I_top = I_top_local + A_top * d_top**2
        
        # Web
        h_web = self.h_w - 2 * self.t
        A_web = h_web * self.t
        I_web_local = self.t * h_web**3 / 12
        d_web = 0  # Web centroid coincides with section centroid (by symmetry)
        I_web = I_web_local + A_web * d_web**2
        
        # Bottom flange
        A_bot = self.b_f * self.t
        I_bot_local = self.b_f * self.t**3 / 12
        d_bot = (self.t / 2) - cy
        I_bot = I_bot_local + A_bot * d_bot**2
        
        # One C-section contribution
        I_one_c = I_top + I_web + I_bot
        
        # Two identical C-sections (symmetric about Y-axis, no additional parallel axis offset)
        I_xx_total = 2 * I_one_c
        
        return I_xx_total

    def calculate_second_moment_y(self) -> float:
        """Calculate second moment of area about centroidal Y-Y axis (I_yy).

        This is the moment of inertia about the vertical axis through centroid,
        which governs bending resistance in the horizontal plane.

        Uses parallel axis theorem for each component.

        Returns:
            Second moment of area I_yy in mm⁴
        """
        cx, cy = self.calculate_centroid()
        I_yy_total = 0.0

        # Left C-section (positioned from x=0 to x=b_f)
        # Distance from left C centroid to section centroid
        x_left_c = self.b_f / 2  # Centroid of left C is at its geometric center
        d_left = x_left_c - cx
        
        # Right C-section (positioned from x=(b_f + opening) to x=(2*b_f + opening))
        x_right_c = self.b_f + self.opening + self.b_f / 2
        d_right = x_right_c - cx
        
        # For one C-section about its own centroidal Y-axis:
        # Top flange
        A_top = self.b_f * self.t
        I_top_local = self.t * self.b_f**3 / 12
        
        # Web (at outer edge of C, distance from C centroid = b_f/2 - t/2)
        h_web = self.h_w - 2 * self.t
        A_web = h_web * self.t
        I_web_local = h_web * self.t**3 / 12
        d_web_from_c_center = self.b_f / 2 - self.t / 2
        I_web_about_c_center = I_web_local + A_web * d_web_from_c_center**2
        
        # Bottom flange (same as top)
        A_bot = self.b_f * self.t
        I_bot_local = self.t * self.b_f**3 / 12
        
        # One C-section about its own centroidal axis
        I_one_c_local = I_top_local + I_web_about_c_center + I_bot_local
        
        # Area of one C-section
        A_one_c = 2 * self.b_f * self.t + (self.h_w - 2 * self.t) * self.t
        
        # Apply parallel axis theorem for both C-sections
        I_left_c = I_one_c_local + A_one_c * d_left**2
        I_right_c = I_one_c_local + A_one_c * d_right**2
        
        I_yy_total = I_left_c + I_right_c
        
        return I_yy_total

    def calculate_torsional_constant(self) -> float:
        """Calculate torsional constant J for two C-sections facing each other.

        For thin-walled sections, use approximate formula:
        J ≈ (1/3) × Σ (b_i × t_i³)

        Sum contributions from all wall segments in both C-sections.

        Returns:
            Torsional constant J in mm⁴
        """
        # Each C-section has:
        # - 2 flanges of length b_f
        # - 1 web of length (h_w - 2*t)
        
        # One C-section contribution
        J_flange = (1/3) * self.b_f * self.t**3
        J_web = (1/3) * (self.h_w - 2 * self.t) * self.t**3
        J_one_c = 2 * J_flange + J_web
        
        # Two C-sections
        J_total = 2 * J_one_c
        
        return J_total

    def calculate_section_properties(self) -> CoreWallSectionProperties:
        """Calculate all section properties for two C-facing core walls.

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
        """Get coordinates of two C-facing sections outline for visualization.

        Returns coordinates in counter-clockwise order for each C-section.

        Returns:
            List of (x, y) coordinate tuples in mm
        """
        t = self.t
        b = self.b_f
        h = self.h_w
        opening = self.opening

        # Left C-section (opening to the right)
        left_c = [
            # Start from bottom-left outer corner, go counter-clockwise
            (0, 0),
            (b, 0),
            (b, t),
            # Inner edge (right side, opening side)
            (t, t),
            (t, h - t),
            # Continue to top
            (b, h - t),
            (b, h),
            (0, h),
            (0, h - t),
            # Left outer edge
            (0, h - t),
            (0, 0),
        ]

        # Right C-section (opening to the left)
        # Offset by (b + opening)
        x_offset = b + opening
        right_c = [
            # Start from bottom-left of right C
            (x_offset, 0),
            (x_offset + b, 0),
            (x_offset + b, h),
            (x_offset + b, h - t),
            # Continue along top
            (x_offset + b, h - t),
            (x_offset + b, h),
            (x_offset + b, h),
            (x_offset, h),
            (x_offset, h - t),
            # Inner edge (left side, opening side)
            (x_offset + b - t, h - t),
            (x_offset + b - t, t),
            (x_offset, t),
            (x_offset, 0),
        ]

        # Combine both C-sections (keeping them separate for visualization)
        return left_c + right_c


def calculate_two_c_facing_properties(geometry: CoreWallGeometry) -> CoreWallSectionProperties:
    """Convenience function to calculate two C-facing section properties.

    Args:
        geometry: CoreWallGeometry with config=TWO_C_FACING

    Returns:
        Calculated CoreWallSectionProperties
    """
    two_c_facing = TwoCFacingCoreWall(geometry)
    return two_c_facing.calculate_section_properties()


class TwoCBackToBackCoreWall:
    """Two C-shaped core walls arranged back-to-back geometry generator.

    This configuration represents two C-shaped walls arranged back-to-back,
    connected along their open sides. This creates a closed rectangular
    perimeter with two internal corridors running parallel to each other.
    Common in tall buildings with dual service cores.

    Geometry notation:
    - Each C-wall consists of: 2 flanges + 1 web
    - Left C-wall: opens to the right
    - Right C-wall: opens to the left
    - Connection: The two C-walls share/touch along their open sides
    - Wall thickness: Constant throughout (typically 500mm)

    Coordinate system:
    - Origin at bottom-left corner of bounding box
    - X-axis horizontal (along total width)
    - Y-axis vertical (along height)

    Configuration (top view):
        Left C (opening to right):      Right C (opening to left):
        ┌──────┐                        ┌──────┐
        │      │<--shared connection--->│      │
        │      │                        │      │
        │      │                        │      │
        └──────┘                        └──────┘

    The two C-walls are arranged so their webs are adjacent (back-to-back),
    with a connection/gap width parameter.
    """

    def __init__(self, geometry: CoreWallGeometry):
        """Initialize two C-shaped back-to-back core walls geometry.

        Args:
            geometry: CoreWallGeometry with config=TWO_C_BACK_TO_BACK and required dimensions

        Raises:
            ValueError: If geometry config is not TWO_C_BACK_TO_BACK or required dimensions missing
        """
        if geometry.config != CoreWallConfig.TWO_C_BACK_TO_BACK:
            raise ValueError(f"Expected TWO_C_BACK_TO_BACK config, got {geometry.config}")

        if geometry.flange_width is None or geometry.web_length is None:
            raise ValueError("TWO_C_BACK_TO_BACK requires flange_width and web_length")

        # For back-to-back, connection_width represents spacing between the two webs
        # If not specified, assume webs are adjacent (touching)
        connection_width = geometry.opening_width if geometry.opening_width is not None else 0.0

        self.geometry = geometry
        self.t = geometry.wall_thickness       # Wall thickness
        self.b_f = geometry.flange_width       # Flange width (for each C)
        self.h_w = geometry.web_length         # Web height/length (vertical dimension)
        self.connection = connection_width     # Spacing between webs (0 = touching)

    def calculate_area(self) -> float:
        """Calculate gross cross-sectional area of two C-shaped walls back-to-back.

        Each C-section consists of:
        - Two flanges (top and bottom): 2 × (b_f × t)
        - One web (connecting flanges): (h_w - 2×t) × t

        Total area = 2 × (area of one C)
        Note: Connection width doesn't affect area (it's just spacing)

        Returns:
            Cross-sectional area in mm²
        """
        # One C-section area
        area_one_c = 2 * self.b_f * self.t + (self.h_w - 2 * self.t) * self.t

        # Two C-sections
        return 2 * area_one_c

    def calculate_centroid(self) -> Tuple[float, float]:
        """Calculate centroid location of two C-sections back-to-back.

        For back-to-back arrangement, the two C-sections are symmetric about
        both horizontal and vertical axes through the geometric center.

        Total width = 2 × b_f + 2 × t + connection_width
        (Each C extends b_f, plus thickness of web on each side, plus connection gap)

        Total height = h_w

        Returns:
            Tuple of (centroid_x, centroid_y) in mm from bottom-left corner
        """
        # Total bounding box dimensions
        # Left C: 0 to b_f (with web at right edge extending to b_f + t)
        # Connection: b_f + t to b_f + t + connection
        # Right C: b_f + t + connection to 2*b_f + 2*t + connection
        total_width = 2 * self.b_f + 2 * self.t + self.connection

        # By double symmetry, centroid is at geometric center
        centroid_x = total_width / 2
        centroid_y = self.h_w / 2

        return (centroid_x, centroid_y)

    def calculate_second_moment_x(self) -> float:
        """Calculate second moment of area about centroidal X-X axis (I_xx).

        This is the moment of inertia about the horizontal axis through centroid,
        which governs bending resistance in the vertical plane.

        Uses parallel axis theorem for each component of both C-sections:
        I_xx = Σ (I_i + A_i × d_y²)

        Returns:
            Second moment of area I_xx in mm⁴
        """
        cx, cy = self.calculate_centroid()
        I_xx_total = 0.0

        # Process both C-sections (symmetric about horizontal centroidal axis)
        # Each C has: top flange, web, bottom flange

        # For one C-section (same calculation as I-section):
        # Top flange
        A_top = self.b_f * self.t
        I_top_local = self.b_f * self.t**3 / 12
        d_top = (self.h_w - self.t / 2) - cy
        I_top = I_top_local + A_top * d_top**2

        # Web
        h_web = self.h_w - 2 * self.t
        A_web = h_web * self.t
        I_web_local = self.t * h_web**3 / 12
        d_web = 0  # Web centroid coincides with section centroid (by symmetry)
        I_web = I_web_local + A_web * d_web**2

        # Bottom flange
        A_bot = self.b_f * self.t
        I_bot_local = self.b_f * self.t**3 / 12
        d_bot = (self.t / 2) - cy
        I_bot = I_bot_local + A_bot * d_bot**2

        # One C-section contribution
        I_one_c = I_top + I_web + I_bot

        # Two identical C-sections (symmetric about X-axis, no additional offset)
        I_xx_total = 2 * I_one_c

        return I_xx_total

    def calculate_second_moment_y(self) -> float:
        """Calculate second moment of area about centroidal Y-Y axis (I_yy).

        This is the moment of inertia about the vertical axis through centroid,
        which governs bending resistance in the horizontal plane.

        For back-to-back arrangement, each C is positioned symmetrically about
        the vertical centroidal axis.

        Returns:
            Second moment of area I_yy in mm⁴
        """
        cx, cy = self.calculate_centroid()
        I_yy_total = 0.0

        # Total width = 2*b_f + 2*t + connection
        # Left C-section positioned from x=0 to x=(b_f + t)
        # Left C centroid at x = b_f/2 (centroid of C-shape)
        x_left_c = self.b_f / 2
        d_left = x_left_c - cx

        # Right C-section positioned from x=(b_f + t + connection) to x=(2*b_f + 2*t + connection)
        x_right_c = self.b_f + self.t + self.connection + self.b_f / 2
        d_right = x_right_c - cx

        # For one C-section about its own centroidal Y-axis:
        # Top flange (centered on C)
        A_top = self.b_f * self.t
        I_top_local = self.t * self.b_f**3 / 12

        # Web (at edge of C, distance from C centroid = b_f/2 - t/2)
        h_web = self.h_w - 2 * self.t
        A_web = h_web * self.t
        I_web_local = h_web * self.t**3 / 12
        d_web_from_c_center = self.b_f / 2 - self.t / 2  # Web at outer edge
        I_web_about_c_center = I_web_local + A_web * d_web_from_c_center**2

        # Bottom flange (same as top)
        A_bot = self.b_f * self.t
        I_bot_local = self.t * self.b_f**3 / 12

        # One C-section about its own centroidal axis
        I_one_c_local = I_top_local + I_web_about_c_center + I_bot_local

        # Area of one C-section
        A_one_c = 2 * self.b_f * self.t + (self.h_w - 2 * self.t) * self.t

        # Apply parallel axis theorem for both C-sections
        I_left_c = I_one_c_local + A_one_c * d_left**2
        I_right_c = I_one_c_local + A_one_c * d_right**2

        I_yy_total = I_left_c + I_right_c

        return I_yy_total

    def calculate_torsional_constant(self) -> float:
        """Calculate torsional constant J for two C-sections back-to-back.

        For thin-walled sections, use approximate formula:
        J ≈ (1/3) × Σ (b_i × t_i³)

        Sum contributions from all wall segments in both C-sections.

        Returns:
            Torsional constant J in mm⁴
        """
        # Each C-section has:
        # - 2 flanges of length b_f
        # - 1 web of length (h_w - 2*t)

        # One C-section contribution
        J_flange = (1/3) * self.b_f * self.t**3
        J_web = (1/3) * (self.h_w - 2 * self.t) * self.t**3
        J_one_c = 2 * J_flange + J_web

        # Two C-sections
        J_total = 2 * J_one_c

        return J_total

    def calculate_section_properties(self) -> CoreWallSectionProperties:
        """Calculate all section properties for two C-back-to-back core walls.

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
        """Get coordinates of two C-back-to-back sections outline for visualization.

        Returns coordinates in counter-clockwise order for each C-section.

        Returns:
            List of (x, y) coordinate tuples in mm
        """
        t = self.t
        b = self.b_f
        h = self.h_w
        conn = self.connection

        # Left C-section (opening to the right)
        # Positioned from x=0 to x=(b + t)
        left_c = [
            # Start from bottom-left outer corner, go counter-clockwise
            (0, 0),
            (b, 0),
            (b, t),
            # Inner edge (right side, at web inner face)
            (b + t, t),
            (b + t, h - t),
            # Top flange
            (b, h - t),
            (b, h),
            (0, h),
            (0, h - t),
            # Back to start (outer left edge)
            (0, t),
            (0, 0),
        ]

        # Right C-section (opening to the left, mirror of left C)
        # Positioned from x=(b + t + conn) to x=(2*b + 2*t + conn)
        x_offset = b + t + conn
        right_c = [
            # Start from bottom-left of right C (inner web face)
            (x_offset, 0),
            (x_offset, t),
            # Bottom flange
            (x_offset + b, t),
            (x_offset + b, 0),
            (x_offset + b + t, 0),
            (x_offset + b + t, h),
            # Top flange
            (x_offset + b, h),
            (x_offset + b, h - t),
            # Inner edge
            (x_offset, h - t),
            (x_offset, h),
            (x_offset, 0),
        ]

        # Combine both C-sections
        return left_c + right_c


def calculate_two_c_back_to_back_properties(geometry: CoreWallGeometry) -> CoreWallSectionProperties:
    """Convenience function to calculate two C-back-to-back section properties.

    Args:
        geometry: CoreWallGeometry with config=TWO_C_BACK_TO_BACK

    Returns:
        Calculated CoreWallSectionProperties
    """
    two_c_back_to_back = TwoCBackToBackCoreWall(geometry)
    return two_c_back_to_back.calculate_section_properties()


class TubeCenterOpeningCoreWall:
    """Tube/box core wall with center opening geometry generator.

    This represents a rectangular tube (box) core wall with an opening in the center,
    typically for a door or corridor. Common in tall buildings where elevator/stair
    cores require access openings.

    Geometry notation:
    - Tube: Rectangular box formed by 4 walls (left, right, top, bottom)
    - Opening: Rectangular cutout in the center (typically centered)
    - Wall thickness: Constant throughout (typically 500mm)
    - The opening creates a frame-like structure

    Coordinate system:
    - Origin at bottom-left corner of outer bounding box
    - X-axis horizontal (along tube width)
    - Y-axis vertical (along tube height)
    
    Configuration (plan view):
        ┌─────────────────────┐
        │                     │
        │    ┌─────────┐      │ <- Top wall
        │    │ OPENING │      │
        │    └─────────┘      │ <- Bottom wall of opening
        │                     │
        └─────────────────────┘
        ^                     ^
        Left wall          Right wall
    """

    def __init__(self, geometry: CoreWallGeometry):
        """Initialize tube core wall with center opening geometry.

        Args:
            geometry: CoreWallGeometry with config=TUBE_CENTER_OPENING and required dimensions

        Raises:
            ValueError: If geometry config is not TUBE_CENTER_OPENING or required dimensions missing
        """
        if geometry.config != CoreWallConfig.TUBE_CENTER_OPENING:
            raise ValueError(f"Expected TUBE_CENTER_OPENING config, got {geometry.config}")

        if geometry.length_x is None or geometry.length_y is None:
            raise ValueError("TUBE_CENTER_OPENING requires length_x and length_y")
        
        if geometry.opening_width is None or geometry.opening_height is None:
            raise ValueError("TUBE_CENTER_OPENING requires opening_width and opening_height")

        # Validate opening is smaller than tube interior
        if geometry.opening_width >= geometry.length_x - 2 * geometry.wall_thickness:
            raise ValueError("Opening width must be less than inner tube width")
        
        if geometry.opening_height >= geometry.length_y - 2 * geometry.wall_thickness:
            raise ValueError("Opening height must be less than inner tube height")

        self.geometry = geometry
        self.t = geometry.wall_thickness        # Wall thickness
        self.L_x = geometry.length_x            # Outer dimension in X
        self.L_y = geometry.length_y            # Outer dimension in Y
        self.w_open = geometry.opening_width    # Opening width
        self.h_open = geometry.opening_height   # Opening height

    def calculate_area(self) -> float:
        """Calculate gross cross-sectional area of tube with center opening.

        The tube section consists of:
        - Gross rectangular tube: L_x × L_y
        - Inner void: (L_x - 2×t) × (L_y - 2×t)
        - Minus center opening: w_open × h_open

        Area = (Gross tube - Inner void) - Opening
             = 4 wall segments - Opening

        Returns:
            Cross-sectional area in mm²
        """
        # Gross outer rectangle
        area_gross = self.L_x * self.L_y
        
        # Inner void (hollow tube interior)
        area_inner_void = (self.L_x - 2 * self.t) * (self.L_y - 2 * self.t)
        
        # Tube area (before accounting for opening)
        area_tube = area_gross - area_inner_void
        
        # Subtract center opening (cuts through one wall)
        area_opening = self.w_open * self.h_open
        
        return area_tube - area_opening

    def calculate_centroid(self) -> Tuple[float, float]:
        """Calculate centroid location of tube with center opening.

        For a tube with symmetric opening centered in the plan,
        the opening reduces material symmetrically, so centroid remains
        at the geometric center of the outer bounding box.

        If opening is not centered, centroid would shift.
        Assuming centered opening for this implementation.

        Returns:
            Tuple of (centroid_x, centroid_y) in mm from bottom-left corner
        """
        # For doubly symmetric tube with centered opening
        # Centroid remains at geometric center
        centroid_x = self.L_x / 2
        centroid_y = self.L_y / 2
        
        return (centroid_x, centroid_y)

    def calculate_second_moment_x(self) -> float:
        """Calculate second moment of area about centroidal X-X axis (I_xx).

        This is the moment of inertia about the horizontal axis through centroid,
        which governs bending resistance in the vertical plane.

        Uses subtraction method:
        I_xx = I_gross_rectangle - I_inner_void - I_opening

        All components are about the same centroidal axis (centered).

        Returns:
            Second moment of area I_xx in mm⁴
        """
        # Gross outer rectangle about its own centroid
        I_gross = (self.L_x * self.L_y**3) / 12
        
        # Inner void (hollow interior) about tube centroid
        inner_width = self.L_x - 2 * self.t
        inner_height = self.L_y - 2 * self.t
        I_inner = (inner_width * inner_height**3) / 12
        
        # Opening (centered) about tube centroid
        # Opening is centered, so no parallel axis offset
        I_opening = (self.w_open * self.h_open**3) / 12
        
        return I_gross - I_inner - I_opening

    def calculate_second_moment_y(self) -> float:
        """Calculate second moment of area about centroidal Y-Y axis (I_yy).

        This is the moment of inertia about the vertical axis through centroid,
        which governs bending resistance in the horizontal plane.

        Uses subtraction method:
        I_yy = I_gross_rectangle - I_inner_void - I_opening

        Returns:
            Second moment of area I_yy in mm⁴
        """
        # Gross outer rectangle about its own centroid
        I_gross = (self.L_y * self.L_x**3) / 12
        
        # Inner void (hollow interior) about tube centroid
        inner_width = self.L_x - 2 * self.t
        inner_height = self.L_y - 2 * self.t
        I_inner = (inner_height * inner_width**3) / 12
        
        # Opening (centered) about tube centroid
        # Opening is centered, so no parallel axis offset
        I_opening = (self.h_open * self.w_open**3) / 12
        
        return I_gross - I_inner - I_opening

    def calculate_torsional_constant(self) -> float:
        """Calculate torsional constant J for tube with center opening.

        For thin-walled closed sections (tubes), the torsional constant is:
        J = (4 × A_enclosed²) / (∮ ds/t)

        Where:
        - A_enclosed = area enclosed by centerline of walls
        - ∮ ds/t = perimeter integral (sum of length/thickness for each wall)

        The center opening creates additional complexity. For preliminary design,
        use thin-walled approximation considering the tube minus opening effect.

        Simplified approach: Use thin-walled formula for rectangular tube,
        then apply reduction factor for opening.

        Returns:
            Torsional constant J in mm⁴
        """
        # Centerline dimensions (midline of wall thickness)
        b = self.L_x - self.t  # Centerline width
        h = self.L_y - self.t  # Centerline height
        
        # Enclosed area by centerline
        A_enclosed = b * h
        
        # Perimeter integral: sum of (length / thickness) for each wall
        # For rectangular tube with constant thickness:
        # ∮ ds/t = 2(b + h) / t
        perimeter_integral = 2 * (b + h) / self.t
        
        # Torsional constant for closed tube
        J_tube = (4 * A_enclosed**2) / perimeter_integral
        
        # Reduction factor for opening (empirical approximation)
        # Opening reduces torsional stiffness
        # Reduction ≈ (1 - A_opening / A_enclosed)
        opening_ratio = (self.w_open * self.h_open) / A_enclosed
        reduction_factor = max(0.3, 1 - 0.7 * opening_ratio)  # Minimum 30% retained
        
        return J_tube * reduction_factor

    def calculate_section_properties(self) -> CoreWallSectionProperties:
        """Calculate all section properties for tube with center opening.

        Returns:
            CoreWallSectionProperties with calculated values
        """
        cx, cy = self.calculate_centroid()

        return CoreWallSectionProperties(
            I_xx=self.calculate_second_moment_x(),
            I_yy=self.calculate_second_moment_y(),
            I_xy=0.0,  # Zero for doubly symmetric sections with centered opening
            A=self.calculate_area(),
            J=self.calculate_torsional_constant(),
            centroid_x=cx,
            centroid_y=cy,
            shear_center_x=cx,  # Coincides with centroid for doubly symmetric sections
            shear_center_y=cy,
        )

    def get_outline_coordinates(self) -> List[Tuple[float, float]]:
        """Get coordinates of tube with center opening outline for visualization.

        Returns coordinates for outer perimeter and inner opening perimeter.

        Returns:
            List of (x, y) coordinate tuples in mm
        """
        # Outer perimeter (counter-clockwise from bottom-left)
        outer = [
            (0, 0),
            (self.L_x, 0),
            (self.L_x, self.L_y),
            (0, self.L_y),
            (0, 0),  # Close outer perimeter
        ]
        
        # Center opening (assuming centered)
        # Calculate opening position (centered in tube)
        x_open_start = (self.L_x - self.w_open) / 2
        y_open_start = (self.L_y - self.h_open) / 2
        
        opening = [
            (x_open_start, y_open_start),
            (x_open_start + self.w_open, y_open_start),
            (x_open_start + self.w_open, y_open_start + self.h_open),
            (x_open_start, y_open_start + self.h_open),
            (x_open_start, y_open_start),  # Close opening perimeter
        ]
        
        # Combine outer and opening (separate loops for visualization)
        return outer + opening


def calculate_tube_center_opening_properties(geometry: CoreWallGeometry) -> CoreWallSectionProperties:
    """Convenience function to calculate tube with center opening properties.

    Args:
        geometry: CoreWallGeometry with config=TUBE_CENTER_OPENING

    Returns:
        Calculated CoreWallSectionProperties
    """
    tube_opening = TubeCenterOpeningCoreWall(geometry)
    return tube_opening.calculate_section_properties()


class TubeSideOpeningCoreWall:
    """Tube/box core wall with side flange opening geometry generator.

    This represents a rectangular tube (box) core wall with an opening in one of the
    side flanges (typically left or right wall). This creates an asymmetric section.
    Common in tall buildings where elevator/stair cores require side access doors.

    Geometry notation:
    - Tube: Rectangular box formed by 4 walls (left, right, top, bottom)
    - Opening: Rectangular cutout in one of the side flanges (left or right wall)
    - Wall thickness: Constant throughout (typically 500mm)
    - The opening creates asymmetry in one direction

    Coordinate system:
    - Origin at bottom-left corner of outer bounding box
    - X-axis horizontal (along tube width)
    - Y-axis vertical (along tube height)

    Configuration (plan view with opening in left wall):
        ┌─────────────────────┐
        │                     │ <- Top wall
             ┌─────┐
             │OPEN │          │
             └─────┘
        │                     │ <- Bottom wall
        └─────────────────────┘
        ^                     ^
        Left wall          Right wall
        (with opening)     (solid)
    """

    def __init__(self, geometry: CoreWallGeometry):
        """Initialize tube core wall with side opening geometry.

        Args:
            geometry: CoreWallGeometry with config=TUBE_SIDE_OPENING and required dimensions

        Raises:
            ValueError: If geometry config is not TUBE_SIDE_OPENING or required dimensions missing
        """
        if geometry.config != CoreWallConfig.TUBE_SIDE_OPENING:
            raise ValueError(f"Expected TUBE_SIDE_OPENING config, got {geometry.config}")

        if geometry.length_x is None or geometry.length_y is None:
            raise ValueError("TUBE_SIDE_OPENING requires length_x and length_y")

        if geometry.opening_width is None or geometry.opening_height is None:
            raise ValueError("TUBE_SIDE_OPENING requires opening_width and opening_height")

        # Validate opening is smaller than the wall it's in
        # Opening is in the vertical wall (running along Y-direction)
        if geometry.opening_height >= geometry.length_y - 2 * geometry.wall_thickness:
            raise ValueError("Opening height must be less than inner tube height")

        # Opening width is limited by wall thickness (can't be wider than the wall depth)
        if geometry.opening_width >= geometry.wall_thickness:
            raise ValueError("Opening width must be less than wall thickness for side opening")

        self.geometry = geometry
        self.t = geometry.wall_thickness        # Wall thickness
        self.L_x = geometry.length_x            # Outer dimension in X
        self.L_y = geometry.length_y            # Outer dimension in Y
        self.w_open = geometry.opening_width    # Opening width (into wall depth)
        self.h_open = geometry.opening_height   # Opening height (vertical extent)

    def calculate_area(self) -> float:
        """Calculate gross cross-sectional area of tube with side opening.

        The tube section consists of:
        - Gross rectangular tube: L_x × L_y
        - Inner void: (L_x - 2×t) × (L_y - 2×t)
        - Minus side opening: w_open × h_open (cuts through left wall)

        Area = (Gross tube - Inner void) - Opening

        Returns:
            Cross-sectional area in mm²
        """
        # Gross outer rectangle
        area_gross = self.L_x * self.L_y

        # Inner void (hollow tube interior)
        area_inner_void = (self.L_x - 2 * self.t) * (self.L_y - 2 * self.t)

        # Tube area (before accounting for opening)
        area_tube = area_gross - area_inner_void

        # Subtract side opening (cuts through left wall)
        area_opening = self.w_open * self.h_open

        return area_tube - area_opening

    def calculate_centroid(self) -> Tuple[float, float]:
        """Calculate centroid location of tube with side opening.

        For a tube with opening in the left wall, the centroid shifts:
        - X-direction: Shifts right (away from opening) due to material removed from left
        - Y-direction: May shift depending on opening vertical position (assuming centered)

        Uses first moment of area method:
        x̄ = (A_total × x_total - A_opening × x_opening) / (A_total - A_opening)

        Assuming opening is centered vertically for this implementation.

        Returns:
            Tuple of (centroid_x, centroid_y) in mm from bottom-left corner
        """
        # For tube without opening, centroid would be at geometric center
        A_tube = self.L_x * self.L_y - (self.L_x - 2 * self.t) * (self.L_y - 2 * self.t)
        x_tube = self.L_x / 2
        y_tube = self.L_y / 2

        # Opening is in left wall (at x = w_open/2 from left edge)
        # Assuming opening is centered vertically
        A_opening = self.w_open * self.h_open
        x_opening = self.w_open / 2
        y_opening = self.L_y / 2  # Centered vertically

        # Calculate centroid using subtraction method
        # Q_x = A_tube × x_tube - A_opening × x_opening
        # Q_y = A_tube × y_tube - A_opening × y_opening
        A_net = A_tube - A_opening

        centroid_x = (A_tube * x_tube - A_opening * x_opening) / A_net
        centroid_y = (A_tube * y_tube - A_opening * y_opening) / A_net

        return (centroid_x, centroid_y)

    def calculate_second_moment_x(self) -> float:
        """Calculate second moment of area about centroidal X-X axis (I_xx).

        This is the moment of inertia about the horizontal axis through centroid,
        which governs bending resistance in the vertical plane.

        Uses subtraction method with parallel axis theorem:
        I_xx = I_gross_rectangle - I_inner_void - I_opening (all transferred to section centroid)

        Returns:
            Second moment of area I_xx in mm⁴
        """
        cx, cy = self.calculate_centroid()

        # Gross outer rectangle about section centroid
        I_gross_local = (self.L_x * self.L_y**3) / 12
        y_gross = self.L_y / 2
        d_gross = y_gross - cy
        A_gross = self.L_x * self.L_y
        I_gross = I_gross_local + A_gross * d_gross**2

        # Inner void about section centroid
        inner_width = self.L_x - 2 * self.t
        inner_height = self.L_y - 2 * self.t
        I_inner_local = (inner_width * inner_height**3) / 12
        y_inner = self.L_y / 2
        d_inner = y_inner - cy
        A_inner = inner_width * inner_height
        I_inner = I_inner_local + A_inner * d_inner**2

        # Opening about section centroid (assuming centered vertically)
        I_opening_local = (self.w_open * self.h_open**3) / 12
        y_opening = self.L_y / 2  # Centered vertically
        d_opening = y_opening - cy
        A_opening = self.w_open * self.h_open
        I_opening = I_opening_local + A_opening * d_opening**2

        return I_gross - I_inner - I_opening

    def calculate_second_moment_y(self) -> float:
        """Calculate second moment of area about centroidal Y-Y axis (I_yy).

        This is the moment of inertia about the vertical axis through centroid,
        which governs bending resistance in the horizontal plane.

        The side opening creates asymmetry, affecting I_yy calculation.

        Returns:
            Second moment of area I_yy in mm⁴
        """
        cx, cy = self.calculate_centroid()

        # Gross outer rectangle about section centroid
        I_gross_local = (self.L_y * self.L_x**3) / 12
        x_gross = self.L_x / 2
        d_gross = x_gross - cx
        A_gross = self.L_x * self.L_y
        I_gross = I_gross_local + A_gross * d_gross**2

        # Inner void about section centroid
        inner_width = self.L_x - 2 * self.t
        inner_height = self.L_y - 2 * self.t
        I_inner_local = (inner_height * inner_width**3) / 12
        x_inner = self.L_x / 2
        d_inner = x_inner - cx
        A_inner = inner_width * inner_height
        I_inner = I_inner_local + A_inner * d_inner**2

        # Opening about section centroid (in left wall)
        I_opening_local = (self.h_open * self.w_open**3) / 12
        x_opening = self.w_open / 2  # Opening starts at left edge
        d_opening = x_opening - cx
        A_opening = self.w_open * self.h_open
        I_opening = I_opening_local + A_opening * d_opening**2

        return I_gross - I_inner - I_opening

    def calculate_product_moment(self) -> float:
        """Calculate product of inertia I_xy about centroidal axes.

        For asymmetric sections (like tube with side opening), I_xy is generally non-zero.

        I_xy = Σ (I_xy,i + A_i × dx_i × dy_i)

        where dx_i and dy_i are distances from component centroid to section centroid.

        For rectangles aligned with axes, local I_xy = 0, so:
        I_xy = Σ (A_i × dx_i × dy_i)

        Returns:
            Product of inertia I_xy in mm⁴
        """
        cx, cy = self.calculate_centroid()

        # Gross outer rectangle
        x_gross = self.L_x / 2
        y_gross = self.L_y / 2
        dx_gross = x_gross - cx
        dy_gross = y_gross - cy
        A_gross = self.L_x * self.L_y
        I_xy_gross = A_gross * dx_gross * dy_gross

        # Inner void (subtract)
        inner_width = self.L_x - 2 * self.t
        inner_height = self.L_y - 2 * self.t
        x_inner = self.L_x / 2
        y_inner = self.L_y / 2
        dx_inner = x_inner - cx
        dy_inner = y_inner - cy
        A_inner = inner_width * inner_height
        I_xy_inner = A_inner * dx_inner * dy_inner

        # Opening (subtract)
        x_opening = self.w_open / 2
        y_opening = self.L_y / 2  # Centered vertically
        dx_opening = x_opening - cx
        dy_opening = y_opening - cy
        A_opening = self.w_open * self.h_open
        I_xy_opening = A_opening * dx_opening * dy_opening

        return I_xy_gross - I_xy_inner - I_xy_opening

    def calculate_torsional_constant(self) -> float:
        """Calculate torsional constant J for tube with side opening.

        For thin-walled closed sections (tubes), the torsional constant is:
        J = (4 × A_enclosed²) / (∮ ds/t)

        The side opening disrupts the closed section, significantly reducing torsional stiffness.
        Use reduction factor based on opening size.

        Returns:
            Torsional constant J in mm⁴
        """
        # Centerline dimensions (midline of wall thickness)
        b = self.L_x - self.t  # Centerline width
        h = self.L_y - self.t  # Centerline height

        # Enclosed area by centerline
        A_enclosed = b * h

        # Perimeter integral for closed tube
        perimeter_integral = 2 * (b + h) / self.t

        # Torsional constant for closed tube
        J_tube = (4 * A_enclosed**2) / perimeter_integral

        # Reduction factor for side opening
        # Side opening disrupts closed section more than center opening
        # Reduction based on opening height relative to wall height
        opening_ratio = self.h_open / self.L_y
        reduction_factor = max(0.2, 1 - 0.8 * opening_ratio)  # Minimum 20% retained

        return J_tube * reduction_factor

    def calculate_section_properties(self) -> CoreWallSectionProperties:
        """Calculate all section properties for tube with side opening.

        Returns:
            CoreWallSectionProperties with calculated values
        """
        cx, cy = self.calculate_centroid()

        return CoreWallSectionProperties(
            I_xx=self.calculate_second_moment_x(),
            I_yy=self.calculate_second_moment_y(),
            I_xy=self.calculate_product_moment(),  # Non-zero for asymmetric section
            A=self.calculate_area(),
            J=self.calculate_torsional_constant(),
            centroid_x=cx,
            centroid_y=cy,
            shear_center_x=cx,  # Approximation - exact calculation requires detailed analysis
            shear_center_y=cy,
        )

    def get_outline_coordinates(self) -> List[Tuple[float, float]]:
        """Get coordinates of tube with side opening outline for visualization.

        Returns coordinates for outer perimeter and opening cutout.

        Returns:
            List of (x, y) coordinate tuples in mm
        """
        # Outer perimeter (counter-clockwise from bottom-left)
        outer = [
            (0, 0),
            (self.L_x, 0),
            (self.L_x, self.L_y),
            (0, self.L_y),
            (0, 0),  # Close outer perimeter
        ]

        # Side opening in left wall (assuming centered vertically)
        y_open_start = (self.L_y - self.h_open) / 2

        opening = [
            (0, y_open_start),
            (self.w_open, y_open_start),
            (self.w_open, y_open_start + self.h_open),
            (0, y_open_start + self.h_open),
            (0, y_open_start),  # Close opening perimeter
        ]

        # Combine outer and opening (separate loops for visualization)
        return outer + opening


def calculate_tube_side_opening_properties(geometry: CoreWallGeometry) -> CoreWallSectionProperties:
    """Convenience function to calculate tube with side opening properties.

    Args:
        geometry: CoreWallGeometry with config=TUBE_SIDE_OPENING

    Returns:
        Calculated CoreWallSectionProperties
    """
    tube_side_opening = TubeSideOpeningCoreWall(geometry)
    return tube_side_opening.calculate_section_properties()
