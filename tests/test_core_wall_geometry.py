"""
Unit tests for core wall geometry calculations.

Test cases include hand calculations to verify section properties.
"""

import pytest
import math
from src.core.data_models import CoreWallConfig, CoreWallGeometry
from src.fem.core_wall_geometry import (
    ISectionCoreWall, 
    calculate_i_section_properties,
    TwoCFacingCoreWall,
    calculate_two_c_facing_properties,
)


class TestISectionCoreWall:
    """Tests for I-section core wall geometry and section properties."""

    def test_initialization_valid(self):
        """Test valid I-section initialization."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )
        i_section = ISectionCoreWall(geometry)

        assert i_section.t == 500
        assert i_section.b_f == 3000
        assert i_section.h_w == 6000

    def test_initialization_wrong_config(self):
        """Test initialization with wrong config raises error."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
        )
        with pytest.raises(ValueError, match="Expected I_SECTION config"):
            ISectionCoreWall(geometry)

    def test_initialization_missing_dimensions(self):
        """Test initialization with missing dimensions raises error."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            # Missing flange_width and web_length
        )
        with pytest.raises(ValueError, match="requires flange_width and web_length"):
            ISectionCoreWall(geometry)

    def test_calculate_area_simple_case(self):
        """Test area calculation with simple dimensions.

        Hand calculation:
        - Flange width (b_f) = 3000 mm
        - Web height (h_w) = 6000 mm
        - Wall thickness (t) = 500 mm

        Area = 2 × (3000 × 500) + (6000 - 2×500) × 500
             = 2 × 1,500,000 + 5000 × 500
             = 3,000,000 + 2,500,000
             = 5,500,000 mm²
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )
        i_section = ISectionCoreWall(geometry)

        area = i_section.calculate_area()
        expected_area = 5_500_000  # mm²

        assert area == pytest.approx(expected_area, rel=1e-6)

    def test_calculate_centroid_symmetric_case(self):
        """Test centroid calculation for symmetric I-section.

        Hand calculation (using same dimensions as area test):
        - Due to symmetry, centroid_x = b_f / 2 = 3000 / 2 = 1500 mm

        For centroid_y, use first moment of area:
        Component areas and centroids:
        - Top flange: A = 3000 × 500 = 1,500,000 mm², y = 6000 - 250 = 5750 mm
        - Web: A = 5000 × 500 = 2,500,000 mm², y = 3000 mm
        - Bottom flange: A = 3000 × 500 = 1,500,000 mm², y = 250 mm

        centroid_y = (1,500,000 × 5750 + 2,500,000 × 3000 + 1,500,000 × 250) / 5,500,000
                   = (8,625,000,000 + 7,500,000,000 + 375,000,000) / 5,500,000
                   = 16,500,000,000 / 5,500,000
                   = 3000 mm
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )
        i_section = ISectionCoreWall(geometry)

        cx, cy = i_section.calculate_centroid()

        assert cx == pytest.approx(1500, rel=1e-6)
        assert cy == pytest.approx(3000, rel=1e-6)

    def test_calculate_second_moment_x(self):
        """Test I_xx calculation (about horizontal centroidal axis).

        Hand calculation for same geometry:
        Using parallel axis theorem: I = I_local + A × d²

        Top flange:
        - I_local = b × h³ / 12 = 3000 × 500³ / 12 = 31,250,000,000 mm⁴
        - d = 5750 - 3000 = 2750 mm
        - A = 1,500,000 mm²
        - I = 31,250,000,000 + 1,500,000 × 2750² = 31,250,000,000 + 11,343,750,000,000
        - I_top = 11,375,000,000,000 mm⁴

        Web:
        - I_local = t × h³ / 12 = 500 × 5000³ / 12 = 5,208,333,333,333 mm⁴
        - d = 0 (web centroid at section centroid)
        - I_web = 5,208,333,333,333 mm⁴

        Bottom flange:
        - I_local = 3000 × 500³ / 12 = 31,250,000,000 mm⁴
        - d = 250 - 3000 = -2750 mm (same magnitude as top)
        - I_bot = 31,250,000,000 + 1,500,000 × 2750² = 11,375,000,000,000 mm⁴

        Total I_xx = 11,375,000,000,000 + 5,208,333,333,333 + 11,375,000,000,000
                   = 27,958,333,333,333 mm⁴
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )
        i_section = ISectionCoreWall(geometry)

        I_xx = i_section.calculate_second_moment_x()
        expected_I_xx = 27_958_333_333_333  # mm⁴

        assert I_xx == pytest.approx(expected_I_xx, rel=1e-4)

    def test_calculate_second_moment_y(self):
        """Test I_yy calculation (about vertical centroidal axis).

        Hand calculation:
        Top flange:
        - I_local = h × b³ / 12 = 500 × 3000³ / 12 = 1,125,000,000,000 mm⁴
        - d = 0 (symmetric about Y-axis)
        - I_top = 1,125,000,000,000 mm⁴

        Web:
        - I_local = h × b³ / 12 = 5000 × 500³ / 12 = 52,083,333,333 mm⁴
        - d = 0 (at centerline)
        - I_web = 52,083,333,333 mm⁴

        Bottom flange:
        - I_bot = 1,125,000,000,000 mm⁴ (same as top)

        Total I_yy = 1,125,000,000,000 + 52,083,333,333 + 1,125,000,000,000
                   = 2,302,083,333,333 mm⁴
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )
        i_section = ISectionCoreWall(geometry)

        I_yy = i_section.calculate_second_moment_y()
        expected_I_yy = 2_302_083_333_333  # mm⁴

        assert I_yy == pytest.approx(expected_I_yy, rel=1e-4)

    def test_calculate_torsional_constant(self):
        """Test torsional constant J calculation.

        Hand calculation using thin-walled formula:
        J ≈ (1/3) × Σ (b_i × t_i³)

        Top flange: J = (1/3) × 3000 × 500³ = 125,000,000,000 mm⁴
        Web: J = (1/3) × 5000 × 500³ = 208,333,333,333 mm⁴
        Bottom flange: J = (1/3) × 3000 × 500³ = 125,000,000,000 mm⁴

        Total J = 125,000,000,000 + 208,333,333,333 + 125,000,000,000
                = 458,333,333,333 mm⁴
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )
        i_section = ISectionCoreWall(geometry)

        J = i_section.calculate_torsional_constant()
        expected_J = 458_333_333_333  # mm⁴

        assert J == pytest.approx(expected_J, rel=1e-4)

    def test_calculate_section_properties_integration(self):
        """Test complete section properties calculation."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )
        i_section = ISectionCoreWall(geometry)

        props = i_section.calculate_section_properties()

        # Verify all properties are populated
        assert props.A == pytest.approx(5_500_000, rel=1e-4)
        assert props.centroid_x == pytest.approx(1500, rel=1e-4)
        assert props.centroid_y == pytest.approx(3000, rel=1e-4)
        assert props.I_xx == pytest.approx(27_958_333_333_333, rel=1e-4)
        assert props.I_yy == pytest.approx(2_302_083_333_333, rel=1e-4)
        assert props.I_xy == pytest.approx(0, abs=1e-6)  # Symmetric section
        assert props.J == pytest.approx(458_333_333_333, rel=1e-4)
        assert props.shear_center_x == pytest.approx(1500, rel=1e-4)
        assert props.shear_center_y == pytest.approx(3000, rel=1e-4)

    def test_convenience_function(self):
        """Test the convenience function calculate_i_section_properties."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )

        props = calculate_i_section_properties(geometry)

        assert props.A == pytest.approx(5_500_000, rel=1e-4)
        assert props.I_xx == pytest.approx(27_958_333_333_333, rel=1e-4)

    def test_get_outline_coordinates(self):
        """Test outline coordinate generation for visualization."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
        )
        i_section = ISectionCoreWall(geometry)

        coords = i_section.get_outline_coordinates()

        # Should return a list of coordinate tuples
        assert isinstance(coords, list)
        assert len(coords) > 0
        assert all(isinstance(coord, tuple) and len(coord) == 2 for coord in coords)

        # Check key corner coordinates
        assert (0, 0) in coords  # Bottom-left
        assert (3000, 0) in coords  # Bottom-right
        assert (3000, 6000) in coords  # Top-right
        assert (0, 6000) in coords  # Top-left

    def test_different_dimensions(self):
        """Test with different realistic dimensions."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=400,  # Thinner wall
            flange_width=4000,   # Wider flange
            web_length=8000,     # Taller web
        )
        i_section = ISectionCoreWall(geometry)

        # Just verify calculations run without errors
        area = i_section.calculate_area()
        cx, cy = i_section.calculate_centroid()
        I_xx = i_section.calculate_second_moment_x()
        I_yy = i_section.calculate_second_moment_y()
        J = i_section.calculate_torsional_constant()

        # Basic sanity checks
        assert area > 0
        assert cx > 0 and cy > 0
        assert I_xx > 0 and I_yy > 0
        assert J > 0

        # Centroid should be at geometric center for symmetric section
        assert cx == pytest.approx(2000, rel=1e-6)  # b_f / 2
        assert cy == pytest.approx(4000, rel=1e-6)  # h_w / 2


class TestTwoCFacingCoreWall:
    """Tests for two C-shaped walls facing each other geometry and section properties."""

    def test_initialization_valid(self):
        """Test valid TWO_C_FACING initialization."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        two_c = TwoCFacingCoreWall(geometry)

        assert two_c.t == 500
        assert two_c.b_f == 3000
        assert two_c.h_w == 6000
        assert two_c.opening == 2000

    def test_initialization_wrong_config(self):
        """Test initialization with wrong config raises error."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500,
        )
        with pytest.raises(ValueError, match="Expected TWO_C_FACING config"):
            TwoCFacingCoreWall(geometry)

    def test_initialization_missing_dimensions(self):
        """Test initialization with missing dimensions raises error."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            # Missing flange_width, web_length, opening_width
        )
        with pytest.raises(ValueError, match="requires flange_width and web_length"):
            TwoCFacingCoreWall(geometry)

    def test_initialization_missing_opening_width(self):
        """Test initialization with missing opening_width raises error."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            # Missing opening_width
        )
        with pytest.raises(ValueError, match="requires opening_width"):
            TwoCFacingCoreWall(geometry)

    def test_calculate_area_simple_case(self):
        """Test area calculation with simple dimensions.

        Hand calculation:
        - Flange width (b_f) = 3000 mm (per C)
        - Web height (h_w) = 6000 mm
        - Wall thickness (t) = 500 mm
        - Opening width = 2000 mm (not affecting area)

        One C-section area:
        - 2 flanges: 2 × (3000 × 500) = 3,000,000 mm²
        - 1 web: (6000 - 2×500) × 500 = 5000 × 500 = 2,500,000 mm²
        - One C = 3,000,000 + 2,500,000 = 5,500,000 mm²

        Two C-sections:
        - Total = 2 × 5,500,000 = 11,000,000 mm²
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        two_c = TwoCFacingCoreWall(geometry)

        area = two_c.calculate_area()
        expected_area = 11_000_000  # mm²

        assert area == pytest.approx(expected_area, rel=1e-6)

    def test_calculate_centroid_symmetric_case(self):
        """Test centroid calculation for two C-facing sections.

        Hand calculation (using same dimensions as area test):
        - Total width = 2 × 3000 + 2000 = 8000 mm
        - Total height = 6000 mm
        - Due to double symmetry, centroid at geometric center:
          - centroid_x = 8000 / 2 = 4000 mm
          - centroid_y = 6000 / 2 = 3000 mm
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        two_c = TwoCFacingCoreWall(geometry)

        cx, cy = two_c.calculate_centroid()

        assert cx == pytest.approx(4000, rel=1e-6)
        assert cy == pytest.approx(3000, rel=1e-6)

    def test_calculate_second_moment_x(self):
        """Test I_xx calculation (about horizontal centroidal axis).

        Hand calculation:
        Each C-section is identical to I-section flanges + web.
        
        One C-section (same as I-section calculation):
        - Top flange: I_local = 3000 × 500³ / 12 = 31,250,000,000 mm⁴
          d = 5750 - 3000 = 2750 mm, A = 1,500,000 mm²
          I = 31,250,000,000 + 1,500,000 × 2750² = 11,375,000,000,000 mm⁴
        
        - Web: I_local = 500 × 5000³ / 12 = 5,208,333,333,333 mm⁴
          d = 0 (at centroid)
          I = 5,208,333,333,333 mm⁴
        
        - Bottom flange: I = 11,375,000,000,000 mm⁴ (same as top)
        
        One C-section I_xx = 11,375,000,000,000 + 5,208,333,333,333 + 11,375,000,000,000
                           = 27,958,333,333,333 mm⁴
        
        Two C-sections (no additional offset in Y, symmetric):
        I_xx_total = 2 × 27,958,333,333,333 = 55,916,666,666,666 mm⁴
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        two_c = TwoCFacingCoreWall(geometry)

        I_xx = two_c.calculate_second_moment_x()
        expected_I_xx = 55_916_666_666_666  # mm⁴

        assert I_xx == pytest.approx(expected_I_xx, rel=1e-4)

    def test_calculate_second_moment_y(self):
        """Test I_yy calculation (about vertical centroidal axis).

        Hand calculation:
        
        For one C-section about its own centroidal Y-axis:
        - C centroid is at b_f/2 = 1500 mm from its left edge
        
        - Top flange: I_local = 500 × 3000³ / 12 = 1,125,000,000,000 mm⁴
        
        - Web (at outer edge, distance from C center = 3000/2 - 500/2 = 1250 mm):
          I_local = 5000 × 500³ / 12 = 52,083,333,333 mm⁴
          A_web = 5000 × 500 = 2,500,000 mm²
          d = 1250 mm
          I_web = 52,083,333,333 + 2,500,000 × 1250² = 3,958,333,333,333 mm⁴
        
        - Bottom flange: I_local = 1,125,000,000,000 mm⁴ (same as top)
        
        One C about its own axis:
        I_c = 1,125,000,000,000 + 3,958,333,333,333 + 1,125,000,000,000
            = 6,208,333,333,333 mm⁴
        
        Section centroid at x = 4000 mm (total width 8000 mm)
        Left C centroid at x = 1500 mm, d_left = 1500 - 4000 = -2500 mm
        Right C centroid at x = 3000 + 2000 + 1500 = 6500 mm, d_right = 6500 - 4000 = 2500 mm
        
        A_one_c = 5,500,000 mm²
        
        I_left = 6,208,333,333,333 + 5,500,000 × 2500² = 40,583,333,333,333 mm⁴
        I_right = 6,208,333,333,333 + 5,500,000 × 2500² = 40,583,333,333,333 mm⁴
        
        I_yy_total = 40,583,333,333,333 + 40,583,333,333,333 = 81,166,666,666,666 mm⁴
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        two_c = TwoCFacingCoreWall(geometry)

        I_yy = two_c.calculate_second_moment_y()
        expected_I_yy = 81_166_666_666_666  # mm⁴

        assert I_yy == pytest.approx(expected_I_yy, rel=1e-4)

    def test_calculate_torsional_constant(self):
        """Test torsional constant J calculation.

        Hand calculation using thin-walled formula:
        J ≈ (1/3) × Σ (b_i × t_i³)

        One C-section:
        - 2 flanges: 2 × [(1/3) × 3000 × 500³] = 2 × 125,000,000,000 = 250,000,000,000 mm⁴
        - 1 web: (1/3) × 5000 × 500³ = 208,333,333,333 mm⁴
        - One C: J = 250,000,000,000 + 208,333,333,333 = 458,333,333,333 mm⁴

        Two C-sections:
        J_total = 2 × 458,333,333,333 = 916,666,666,666 mm⁴
        """
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        two_c = TwoCFacingCoreWall(geometry)

        J = two_c.calculate_torsional_constant()
        expected_J = 916_666_666_666  # mm⁴

        assert J == pytest.approx(expected_J, rel=1e-4)

    def test_calculate_section_properties_integration(self):
        """Test complete section properties calculation."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        two_c = TwoCFacingCoreWall(geometry)

        props = two_c.calculate_section_properties()

        # Verify all properties are populated
        assert props.A == pytest.approx(11_000_000, rel=1e-4)
        assert props.centroid_x == pytest.approx(4000, rel=1e-4)
        assert props.centroid_y == pytest.approx(3000, rel=1e-4)
        assert props.I_xx == pytest.approx(55_916_666_666_666, rel=1e-4)
        assert props.I_yy == pytest.approx(81_166_666_666_666, rel=1e-4)
        assert props.I_xy == pytest.approx(0, abs=1e-6)  # Symmetric section
        assert props.J == pytest.approx(916_666_666_666, rel=1e-4)
        assert props.shear_center_x == pytest.approx(4000, rel=1e-4)
        assert props.shear_center_y == pytest.approx(3000, rel=1e-4)

    def test_convenience_function(self):
        """Test the convenience function calculate_two_c_facing_properties."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )

        props = calculate_two_c_facing_properties(geometry)

        assert props.A == pytest.approx(11_000_000, rel=1e-4)
        assert props.I_xx == pytest.approx(55_916_666_666_666, rel=1e-4)

    def test_get_outline_coordinates(self):
        """Test outline coordinate generation for visualization."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        two_c = TwoCFacingCoreWall(geometry)

        coords = two_c.get_outline_coordinates()

        # Should return a list of coordinate tuples
        assert isinstance(coords, list)
        assert len(coords) > 0
        assert all(isinstance(coord, tuple) and len(coord) == 2 for coord in coords)

        # Check key corner coordinates for left C
        assert (0, 0) in coords  # Bottom-left of left C
        assert (3000, 0) in coords  # Bottom-right of left C
        assert (0, 6000) in coords  # Top-left of left C

        # Check key corner coordinates for right C (offset by 3000 + 2000 = 5000)
        assert (5000, 0) in coords  # Bottom-left of right C
        assert (8000, 0) in coords  # Bottom-right of right C
        assert (8000, 6000) in coords  # Top-right of right C

    def test_different_dimensions(self):
        """Test with different realistic dimensions."""
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=400,   # Thinner wall
            flange_width=4000,    # Wider flange
            web_length=8000,      # Taller web
            opening_width=3000,   # Wider opening
        )
        two_c = TwoCFacingCoreWall(geometry)

        # Just verify calculations run without errors
        area = two_c.calculate_area()
        cx, cy = two_c.calculate_centroid()
        I_xx = two_c.calculate_second_moment_x()
        I_yy = two_c.calculate_second_moment_y()
        J = two_c.calculate_torsional_constant()

        # Basic sanity checks
        assert area > 0
        assert cx > 0 and cy > 0
        assert I_xx > 0 and I_yy > 0
        assert J > 0

        # Centroid should be at geometric center for symmetric section
        total_width = 2 * 4000 + 3000  # 11000 mm
        assert cx == pytest.approx(total_width / 2, rel=1e-6)  # 5500 mm
        assert cy == pytest.approx(4000, rel=1e-6)  # h_w / 2

    def test_varying_opening_width(self):
        """Test that varying opening width affects I_yy but not I_xx."""
        base_geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=2000,
        )
        
        wide_opening_geometry = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500,
            flange_width=3000,
            web_length=6000,
            opening_width=4000,  # Wider opening
        )

        base_two_c = TwoCFacingCoreWall(base_geometry)
        wide_two_c = TwoCFacingCoreWall(wide_opening_geometry)

        # Area should be same (opening doesn't change material)
        assert base_two_c.calculate_area() == pytest.approx(
            wide_two_c.calculate_area(), rel=1e-6
        )

        # I_xx should be same (vertical bending not affected by horizontal spacing)
        assert base_two_c.calculate_second_moment_x() == pytest.approx(
            wide_two_c.calculate_second_moment_x(), rel=1e-4
        )

        # I_yy should be larger with wider opening (C-sections further apart)
        assert wide_two_c.calculate_second_moment_y() > base_two_c.calculate_second_moment_y()
