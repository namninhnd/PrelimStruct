"""
Unit tests for general section properties calculator.

Tests validate calculations against hand-calculated values for standard shapes:
- Rectangles
- Triangles
- Hollow sections (tubes)
- Asymmetric shapes

All test values are verified with hand calculations and cross-checked with
mechanics of materials textbooks.
"""

import pytest
import math
from src.fem.section_properties import (
    calculate_polygon_area,
    calculate_polygon_centroid,
    calculate_polygon_second_moment_x,
    calculate_polygon_second_moment_y,
    calculate_polygon_product_moment,
    calculate_hollow_section_properties,
    calculate_thin_walled_torsional_constant,
    calculate_closed_tube_torsional_constant,
    calculate_principal_axes,
    calculate_radius_of_gyration,
)


class TestPolygonArea:
    """Tests for polygon area calculation."""

    def test_rectangle_area(self):
        """Test area of a rectangle (100mm × 200mm)."""
        # Rectangle: width=100, height=200
        vertices = [
            (0, 0),
            (100, 0),
            (100, 200),
            (0, 200),
        ]
        # Hand calculation: A = 100 × 200 = 20,000 mm²
        expected_area = 20_000
        assert calculate_polygon_area(vertices) == pytest.approx(expected_area, rel=1e-9)

    def test_triangle_area(self):
        """Test area of a triangle (base=100, height=150)."""
        # Right triangle with base 100, height 150
        vertices = [
            (0, 0),
            (100, 0),
            (0, 150),
        ]
        # Hand calculation: A = (1/2) × base × height = 0.5 × 100 × 150 = 7,500 mm²
        expected_area = 7_500
        assert calculate_polygon_area(vertices) == pytest.approx(expected_area, rel=1e-9)

    def test_square_area(self):
        """Test area of a square (100mm × 100mm)."""
        vertices = [
            (0, 0),
            (100, 0),
            (100, 100),
            (0, 100),
        ]
        # Hand calculation: A = 100² = 10,000 mm²
        expected_area = 10_000
        assert calculate_polygon_area(vertices) == pytest.approx(expected_area, rel=1e-9)

    def test_invalid_polygon(self):
        """Test that polygon with fewer than 3 vertices raises error."""
        with pytest.raises(ValueError, match="at least 3 vertices"):
            calculate_polygon_area([(0, 0), (100, 0)])


class TestPolygonCentroid:
    """Tests for polygon centroid calculation."""

    def test_rectangle_centroid(self):
        """Test centroid of a rectangle (100mm × 200mm)."""
        # Rectangle from (0,0) to (100,200)
        vertices = [
            (0, 0),
            (100, 0),
            (100, 200),
            (0, 200),
        ]
        # Hand calculation: Centroid at geometric center
        # x̄ = 100/2 = 50 mm
        # ȳ = 200/2 = 100 mm
        cx, cy = calculate_polygon_centroid(vertices)
        assert cx == pytest.approx(50, rel=1e-9)
        assert cy == pytest.approx(100, rel=1e-9)

    def test_triangle_centroid(self):
        """Test centroid of a right triangle."""
        # Right triangle: (0,0), (90,0), (0,60)
        vertices = [
            (0, 0),
            (90, 0),
            (0, 60),
        ]
        # Hand calculation: For right triangle with legs along axes
        # x̄ = (0 + 90 + 0)/3 = 30 mm
        # ȳ = (0 + 0 + 60)/3 = 20 mm
        cx, cy = calculate_polygon_centroid(vertices)
        assert cx == pytest.approx(30, rel=1e-9)
        assert cy == pytest.approx(20, rel=1e-9)

    def test_offset_rectangle_centroid(self):
        """Test centroid of rectangle not at origin."""
        # Rectangle from (50,100) to (150,300)
        vertices = [
            (50, 100),
            (150, 100),
            (150, 300),
            (50, 300),
        ]
        # Hand calculation: Centroid at geometric center
        # x̄ = (50 + 150)/2 = 100 mm
        # ȳ = (100 + 300)/2 = 200 mm
        cx, cy = calculate_polygon_centroid(vertices)
        assert cx == pytest.approx(100, rel=1e-9)
        assert cy == pytest.approx(200, rel=1e-9)


class TestSecondMoments:
    """Tests for second moment of area calculations."""

    def test_rectangle_I_xx(self):
        """Test I_xx for a rectangle about its centroidal axis."""
        # Rectangle: width=100mm, height=200mm
        vertices = [
            (0, 0),
            (100, 0),
            (100, 200),
            (0, 200),
        ]
        # Hand calculation: I_xx = (b × h³) / 12 = (100 × 200³) / 12
        # I_xx = 100 × 8,000,000 / 12 = 66,666,667 mm⁴
        expected_I_xx = (100 * 200**3) / 12
        I_xx = calculate_polygon_second_moment_x(vertices)
        assert I_xx == pytest.approx(expected_I_xx, rel=1e-6)

    def test_rectangle_I_yy(self):
        """Test I_yy for a rectangle about its centroidal axis."""
        # Rectangle: width=100mm, height=200mm
        vertices = [
            (0, 0),
            (100, 0),
            (100, 200),
            (0, 200),
        ]
        # Hand calculation: I_yy = (h × b³) / 12 = (200 × 100³) / 12
        # I_yy = 200 × 1,000,000 / 12 = 16,666,667 mm⁴
        expected_I_yy = (200 * 100**3) / 12
        I_yy = calculate_polygon_second_moment_y(vertices)
        assert I_yy == pytest.approx(expected_I_yy, rel=1e-6)

    def test_square_I_xx_I_yy_equal(self):
        """Test that square has equal I_xx and I_yy."""
        # Square: 100mm × 100mm
        vertices = [
            (0, 0),
            (100, 0),
            (100, 100),
            (0, 100),
        ]
        I_xx = calculate_polygon_second_moment_x(vertices)
        I_yy = calculate_polygon_second_moment_y(vertices)
        # For square, I_xx = I_yy = (100 × 100³) / 12 = 8,333,333 mm⁴
        expected_I = (100 * 100**3) / 12
        assert I_xx == pytest.approx(expected_I, rel=1e-6)
        assert I_yy == pytest.approx(expected_I, rel=1e-6)
        assert I_xx == pytest.approx(I_yy, rel=1e-9)

    def test_rectangle_product_moment(self):
        """Test product of inertia for symmetric rectangle (should be zero)."""
        # Rectangle centered at origin
        vertices = [
            (-50, -100),
            (50, -100),
            (50, 100),
            (-50, 100),
        ]
        # Hand calculation: For doubly symmetric section, I_xy = 0
        I_xy = calculate_polygon_product_moment(vertices)
        assert I_xy == pytest.approx(0, abs=1e-6)

    def test_offset_rectangle_product_moment(self):
        """Test product of inertia for rectangle not centered at origin."""
        # Rectangle from (0,0) to (100,200), centroid at (50,100)
        # When referenced to axes through centroid, I_xy should be 0 (symmetric)
        vertices = [
            (0, 0),
            (100, 0),
            (100, 200),
            (0, 200),
        ]
        centroid = calculate_polygon_centroid(vertices)
        I_xy = calculate_polygon_product_moment(vertices, centroid)
        # Hand calculation: Symmetric about both centroidal axes → I_xy = 0
        assert I_xy == pytest.approx(0, abs=1e-6)


class TestHollowSections:
    """Tests for hollow section properties (tubes with voids)."""

    def test_hollow_rectangle_area(self):
        """Test area of hollow rectangular tube."""
        # Outer: 1000mm × 2000mm, Inner: 800mm × 1600mm (wall thickness = 100mm on top/bottom, 100mm on sides)
        outer = [
            (0, 0),
            (1000, 0),
            (1000, 2000),
            (0, 2000),
        ]
        inner = [
            (100, 200),
            (900, 200),
            (900, 1800),
            (100, 1800),
        ]
        # Hand calculation:
        # A_outer = 1000 × 2000 = 2,000,000 mm²
        # A_inner = 800 × 1600 = 1,280,000 mm²
        # A_net = 2,000,000 - 1,280,000 = 720,000 mm²
        A, centroid, I_xx, I_yy, I_xy = calculate_hollow_section_properties(outer, [inner])
        expected_area = 720_000
        assert A == pytest.approx(expected_area, rel=1e-9)

    def test_hollow_rectangle_centroid_symmetric(self):
        """Test centroid of symmetric hollow rectangle (should remain at center)."""
        # Symmetric tube: outer 1000×2000, inner centered 600×1600
        outer = [
            (0, 0),
            (1000, 0),
            (1000, 2000),
            (0, 2000),
        ]
        # Inner rectangle centered: offset by 200 on sides, 200 on top/bottom
        inner = [
            (200, 200),
            (800, 200),
            (800, 1800),
            (200, 1800),
        ]
        # Hand calculation: Symmetric opening → centroid remains at (500, 1000)
        A, centroid, I_xx, I_yy, I_xy = calculate_hollow_section_properties(outer, [inner])
        assert centroid[0] == pytest.approx(500, rel=1e-9)
        assert centroid[1] == pytest.approx(1000, rel=1e-9)

    def test_hollow_rectangle_second_moments(self):
        """Test second moments for hollow rectangular tube."""
        # Outer: 200mm × 300mm, Inner: 100mm × 200mm (centered)
        outer = [
            (0, 0),
            (200, 0),
            (200, 300),
            (0, 300),
        ]
        inner = [
            (50, 50),
            (150, 50),
            (150, 250),
            (50, 250),
        ]
        # Hand calculation:
        # I_xx = (b_o × h_o³)/12 - (b_i × h_i³)/12
        # I_xx = (200 × 300³)/12 - (100 × 200³)/12
        # I_xx = 450,000,000 - 66,666,667 = 383,333,333 mm⁴
        #
        # I_yy = (h_o × b_o³)/12 - (h_i × b_i³)/12
        # I_yy = (300 × 200³)/12 - (200 × 100³)/12
        # I_yy = 200,000,000 - 16,666,667 = 183,333,333 mm⁴
        A, centroid, I_xx, I_yy, I_xy = calculate_hollow_section_properties(outer, [inner])
        expected_I_xx = (200 * 300**3) / 12 - (100 * 200**3) / 12
        expected_I_yy = (300 * 200**3) / 12 - (200 * 100**3) / 12
        assert I_xx == pytest.approx(expected_I_xx, rel=1e-6)
        assert I_yy == pytest.approx(expected_I_yy, rel=1e-6)


class TestTorsionalConstant:
    """Tests for torsional constant calculations."""

    def test_thin_walled_I_section(self):
        """Test torsional constant for I-section using thin-walled formula."""
        # I-section: 2 flanges (100mm × 10mm) + 1 web (80mm × 10mm)
        # J = (1/3) × Σ(b × t³)
        wall_segments = [
            (100, 10),  # Top flange
            (80, 10),   # Web
            (100, 10),  # Bottom flange
        ]
        # Hand calculation:
        # J = (1/3) × [100×10³ + 80×10³ + 100×10³]
        # J = (1/3) × [100,000 + 80,000 + 100,000]
        # J = (1/3) × 280,000 = 93,333.33 mm⁴
        expected_J = (1/3) * (100 * 10**3 + 80 * 10**3 + 100 * 10**3)
        J = calculate_thin_walled_torsional_constant(wall_segments)
        assert J == pytest.approx(expected_J, rel=1e-6)

    def test_closed_tube_torsional_constant(self):
        """Test torsional constant for closed rectangular tube."""
        # Rectangular tube: 1000mm × 2000mm outer, 50mm wall thickness
        # Enclosed area by centerline: (1000-50) × (2000-50) = 950 × 1950
        enclosed_area = 950 * 1950  # mm²

        # Perimeter segments (centerline): 2×950 + 2×1950 with thickness 50mm
        perimeter_segments = [
            (950, 50),   # Top
            (1950, 50),  # Right
            (950, 50),   # Bottom
            (1950, 50),  # Left
        ]
        # Hand calculation:
        # A_enclosed = 1,852,500 mm²
        # ∮(ds/t) = (950 + 1950 + 950 + 1950) / 50 = 5800 / 50 = 116 mm
        # J = 4 × A² / ∮(ds/t) = 4 × (1,852,500)² / 116
        # J = 4 × 3,431,756,250,000 / 116 = 118,371,595,689 mm⁴
        expected_J = (4 * enclosed_area**2) / ((950 + 1950 + 950 + 1950) / 50)
        J = calculate_closed_tube_torsional_constant(enclosed_area, perimeter_segments)
        assert J == pytest.approx(expected_J, rel=1e-6)

    def test_thin_walled_empty_segments_error(self):
        """Test that empty wall segments raises error."""
        with pytest.raises(ValueError, match="At least one wall segment"):
            calculate_thin_walled_torsional_constant([])

    def test_closed_tube_zero_area_error(self):
        """Test that zero enclosed area raises error."""
        with pytest.raises(ValueError, match="Enclosed area must be positive"):
            calculate_closed_tube_torsional_constant(0, [(100, 10)])


class TestPrincipalAxes:
    """Tests for principal axis calculations."""

    def test_symmetric_section_principal_axes(self):
        """Test principal axes for symmetric section (I_xy = 0)."""
        # For symmetric section, I_max = max(I_xx, I_yy), I_min = min(I_xx, I_yy)
        I_xx = 100_000_000  # mm⁴
        I_yy = 50_000_000   # mm⁴
        I_xy = 0             # Symmetric

        I_max, I_min, theta = calculate_principal_axes(I_xx, I_yy, I_xy)

        # Hand calculation: I_xy = 0 → principal axes coincide with X-Y axes
        assert I_max == pytest.approx(I_xx, rel=1e-9)
        assert I_min == pytest.approx(I_yy, rel=1e-9)
        assert theta == pytest.approx(0, abs=1e-9)

    def test_asymmetric_section_principal_axes(self):
        """Test principal axes for asymmetric section."""
        # Example: I_xx = 1000, I_yy = 600, I_xy = 200
        I_xx = 1000
        I_yy = 600
        I_xy = 200

        # Hand calculation:
        # I_avg = (1000 + 600)/2 = 800
        # delta_I = (1000 - 600)/2 = 200
        # radius = sqrt(200² + 200²) = sqrt(80,000) = 282.84
        # I_max = 800 + 282.84 = 1082.84
        # I_min = 800 - 282.84 = 517.16
        # theta = 0.5 × atan(2×200 / (1000-600)) = 0.5 × atan(400/400) = 0.5 × atan(1) = 0.5 × 0.7854 = 0.3927 rad

        I_max, I_min, theta = calculate_principal_axes(I_xx, I_yy, I_xy)

        I_avg = (I_xx + I_yy) / 2
        radius = math.sqrt(((I_xx - I_yy) / 2)**2 + I_xy**2)
        expected_I_max = I_avg + radius
        expected_I_min = I_avg - radius
        expected_theta = 0.5 * math.atan2(2 * I_xy, I_xx - I_yy)

        assert I_max == pytest.approx(expected_I_max, rel=1e-6)
        assert I_min == pytest.approx(expected_I_min, rel=1e-6)
        assert theta == pytest.approx(expected_theta, rel=1e-6)


class TestRadiusOfGyration:
    """Tests for radius of gyration calculation."""

    def test_rectangle_radius_of_gyration_x(self):
        """Test radius of gyration about X-axis for rectangle."""
        # Rectangle: 100mm × 200mm
        A = 100 * 200  # = 20,000 mm²
        I_xx = (100 * 200**3) / 12  # = 66,666,667 mm⁴

        # Hand calculation: r_x = sqrt(I_xx / A)
        # r_x = sqrt(66,666,667 / 20,000) = sqrt(3333.33) = 57.735 mm
        expected_r = math.sqrt(I_xx / A)
        r = calculate_radius_of_gyration(I_xx, A)

        assert r == pytest.approx(expected_r, rel=1e-6)
        # For rectangle about centroidal axis: r = h / sqrt(12) = 200 / sqrt(12) = 57.735 mm
        assert r == pytest.approx(200 / math.sqrt(12), rel=1e-6)

    def test_radius_of_gyration_zero_area_error(self):
        """Test that zero area raises error."""
        with pytest.raises(ValueError, match="Area must be positive"):
            calculate_radius_of_gyration(1000, 0)


class TestValidationAgainstCoreWalls:
    """Validation tests comparing general calculator with specific core wall classes."""

    def test_validate_against_rectangle(self):
        """Validate general calculator against simple rectangle."""
        # Rectangle: 500mm × 6000mm (similar to I-section web)
        vertices = [
            (0, 0),
            (500, 0),
            (500, 6000),
            (0, 6000),
        ]

        # Calculate using general functions
        A = calculate_polygon_area(vertices)
        cx, cy = calculate_polygon_centroid(vertices)
        I_xx = calculate_polygon_second_moment_x(vertices)
        I_yy = calculate_polygon_second_moment_y(vertices)

        # Hand calculations (textbook formulas)
        expected_A = 500 * 6000
        expected_cx = 250
        expected_cy = 3000
        expected_I_xx = (500 * 6000**3) / 12
        expected_I_yy = (6000 * 500**3) / 12

        assert A == pytest.approx(expected_A, rel=1e-9)
        assert cx == pytest.approx(expected_cx, rel=1e-9)
        assert cy == pytest.approx(expected_cy, rel=1e-9)
        assert I_xx == pytest.approx(expected_I_xx, rel=1e-6)
        assert I_yy == pytest.approx(expected_I_yy, rel=1e-6)

    def test_validate_hollow_tube(self):
        """Validate general calculator for hollow tube section."""
        # Tube: 8000mm × 12000mm outer, 7000mm × 11000mm inner
        outer = [
            (0, 0),
            (8000, 0),
            (8000, 12000),
            (0, 12000),
        ]
        inner = [
            (500, 500),
            (7500, 500),
            (7500, 11500),
            (500, 11500),
        ]

        # Calculate using hollow section function
        A, centroid, I_xx, I_yy, I_xy = calculate_hollow_section_properties(outer, [inner])

        # Hand calculations
        A_outer = 8000 * 12000
        A_inner = 7000 * 11000
        expected_A = A_outer - A_inner

        # Symmetric → centroid at center
        expected_cx = 4000
        expected_cy = 6000

        # I_xx = I_outer - I_inner (both about same centroid due to symmetry)
        expected_I_xx = (8000 * 12000**3) / 12 - (7000 * 11000**3) / 12
        expected_I_yy = (12000 * 8000**3) / 12 - (11000 * 7000**3) / 12

        assert A == pytest.approx(expected_A, rel=1e-9)
        assert centroid[0] == pytest.approx(expected_cx, rel=1e-9)
        assert centroid[1] == pytest.approx(expected_cy, rel=1e-9)
        assert I_xx == pytest.approx(expected_I_xx, rel=1e-6)
        assert I_yy == pytest.approx(expected_I_yy, rel=1e-6)
        assert I_xy == pytest.approx(0, abs=1e-6)  # Symmetric


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_clockwise_vertices_gives_positive_area(self):
        """Test that clockwise vertices still give positive area."""
        # Clockwise rectangle
        vertices = [
            (0, 0),
            (0, 100),
            (100, 100),
            (100, 0),
        ]
        A = calculate_polygon_area(vertices)
        # Should still give positive area due to abs() in formula
        assert A == pytest.approx(10_000, rel=1e-9)

    def test_zero_area_polygon_centroid_error(self):
        """Test that zero-area polygon raises error for centroid."""
        # Degenerate polygon (all points on a line)
        vertices = [
            (0, 0),
            (50, 0),
            (100, 0),
        ]
        with pytest.raises(ValueError, match="zero area"):
            calculate_polygon_centroid(vertices)
