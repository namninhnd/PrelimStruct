"""
General Section Properties Calculator for Arbitrary Polygons

This module provides general-purpose section property calculations for arbitrary
polygon sections, including hollow sections with openings. It uses numerical
integration methods based on polygon decomposition.

Used as a foundation for core wall geometry calculations and can validate
specialized geometry class calculations against general methods.

References:
- Timoshenko & Goodier, "Theory of Elasticity"
- Beer & Johnston, "Mechanics of Materials"
- Pilkey, "Analysis and Design of Elastic Beams"
"""

from typing import List, Tuple
import math


def calculate_polygon_area(vertices: List[Tuple[float, float]]) -> float:
    """Calculate area of a polygon using the shoelace formula.

    The shoelace formula (also called surveyor's formula) calculates the area
    of a simple polygon given its vertices in order.

    Formula: A = (1/2) |Σ(x_i × y_{i+1} - x_{i+1} × y_i)|

    Args:
        vertices: List of (x, y) coordinate tuples defining polygon boundary
                  in counter-clockwise order. Last vertex connects to first.

    Returns:
        Area of polygon in units²

    Raises:
        ValueError: If vertices list has fewer than 3 points
    """
    if len(vertices) < 3:
        raise ValueError("Polygon must have at least 3 vertices")

    n = len(vertices)
    area = 0.0

    for i in range(n):
        j = (i + 1) % n  # Wrap around to first vertex
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]

    return abs(area) / 2.0


def calculate_polygon_centroid(vertices: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Calculate centroid of a polygon using first moment of area.

    Uses the shoelace-based centroid formula:
    x̄ = (1/(6A)) × Σ(x_i + x_{i+1}) × (x_i × y_{i+1} - x_{i+1} × y_i)
    ȳ = (1/(6A)) × Σ(y_i + y_{i+1}) × (x_i × y_{i+1} - x_{i+1} × y_i)

    Args:
        vertices: List of (x, y) coordinate tuples defining polygon boundary
                  in counter-clockwise order

    Returns:
        Tuple of (centroid_x, centroid_y) coordinates

    Raises:
        ValueError: If vertices list has fewer than 3 points or area is zero
    """
    if len(vertices) < 3:
        raise ValueError("Polygon must have at least 3 vertices")

    n = len(vertices)
    area = calculate_polygon_area(vertices)

    if area == 0:
        raise ValueError("Polygon has zero area")

    cx = 0.0
    cy = 0.0

    for i in range(n):
        j = (i + 1) % n
        cross_product = vertices[i][0] * vertices[j][1] - vertices[j][0] * vertices[i][1]
        cx += (vertices[i][0] + vertices[j][0]) * cross_product
        cy += (vertices[i][1] + vertices[j][1]) * cross_product

    cx = cx / (6.0 * area)
    cy = cy / (6.0 * area)

    return (cx, cy)


def calculate_polygon_second_moment_x(
    vertices: List[Tuple[float, float]],
    centroid: Tuple[float, float] = None
) -> float:
    """Calculate second moment of area about centroidal X-X axis (I_xx).

    The second moment of area (moment of inertia) about the horizontal axis
    through the centroid governs bending resistance in the vertical plane.

    Uses polygon decomposition formula:
    I_xx = (1/12) × Σ(x_i × y_{i+1} - x_{i+1} × y_i) × (y_i² + y_i × y_{i+1} + y_{i+1}²)

    Then transfers to centroidal axis using parallel axis theorem if needed.

    Args:
        vertices: List of (x, y) coordinate tuples in counter-clockwise order
        centroid: Optional centroid coordinates. If None, will be calculated.

    Returns:
        Second moment of area I_xx in units⁴

    Raises:
        ValueError: If vertices list has fewer than 3 points
    """
    if len(vertices) < 3:
        raise ValueError("Polygon must have at least 3 vertices")

    if centroid is None:
        centroid = calculate_polygon_centroid(vertices)

    n = len(vertices)
    I_xx = 0.0

    # Calculate about origin first, then transfer to centroid
    for i in range(n):
        j = (i + 1) % n
        cross_product = vertices[i][0] * vertices[j][1] - vertices[j][0] * vertices[i][1]
        y_i = vertices[i][1]
        y_j = vertices[j][1]
        I_xx += cross_product * (y_i**2 + y_i * y_j + y_j**2)

    I_xx = I_xx / 12.0

    # Transfer from origin to centroidal axis using parallel axis theorem
    # I_centroid = I_origin - A × d²
    area = calculate_polygon_area(vertices)
    I_xx = I_xx - area * centroid[1]**2

    return abs(I_xx)


def calculate_polygon_second_moment_y(
    vertices: List[Tuple[float, float]],
    centroid: Tuple[float, float] = None
) -> float:
    """Calculate second moment of area about centroidal Y-Y axis (I_yy).

    The second moment of area about the vertical axis through the centroid
    governs bending resistance in the horizontal plane.

    Uses polygon decomposition formula:
    I_yy = (1/12) × Σ(x_i × y_{i+1} - x_{i+1} × y_i) × (x_i² + x_i × x_{i+1} + x_{i+1}²)

    Args:
        vertices: List of (x, y) coordinate tuples in counter-clockwise order
        centroid: Optional centroid coordinates. If None, will be calculated.

    Returns:
        Second moment of area I_yy in units⁴

    Raises:
        ValueError: If vertices list has fewer than 3 points
    """
    if len(vertices) < 3:
        raise ValueError("Polygon must have at least 3 vertices")

    if centroid is None:
        centroid = calculate_polygon_centroid(vertices)

    n = len(vertices)
    I_yy = 0.0

    # Calculate about origin first, then transfer to centroid
    for i in range(n):
        j = (i + 1) % n
        cross_product = vertices[i][0] * vertices[j][1] - vertices[j][0] * vertices[i][1]
        x_i = vertices[i][0]
        x_j = vertices[j][0]
        I_yy += cross_product * (x_i**2 + x_i * x_j + x_j**2)

    I_yy = I_yy / 12.0

    # Transfer from origin to centroidal axis
    area = calculate_polygon_area(vertices)
    I_yy = I_yy - area * centroid[0]**2

    return abs(I_yy)


def calculate_polygon_product_moment(
    vertices: List[Tuple[float, float]],
    centroid: Tuple[float, float] = None
) -> float:
    """Calculate product of inertia I_xy about centroidal axes.

    The product of inertia is zero for sections with at least one axis of symmetry.
    For asymmetric sections, I_xy is non-zero and needed for principal axis calculations.

    Uses polygon decomposition formula:
    I_xy = (1/24) × Σ(x_i × y_{i+1} - x_{i+1} × y_i) ×
           (x_i × y_j + 2 × x_i × y_i + 2 × x_j × y_j + x_j × y_i)

    Args:
        vertices: List of (x, y) coordinate tuples in counter-clockwise order
        centroid: Optional centroid coordinates. If None, will be calculated.

    Returns:
        Product of inertia I_xy in units⁴

    Raises:
        ValueError: If vertices list has fewer than 3 points
    """
    if len(vertices) < 3:
        raise ValueError("Polygon must have at least 3 vertices")

    if centroid is None:
        centroid = calculate_polygon_centroid(vertices)

    n = len(vertices)
    I_xy = 0.0

    # Calculate about origin first
    for i in range(n):
        j = (i + 1) % n
        cross_product = vertices[i][0] * vertices[j][1] - vertices[j][0] * vertices[i][1]
        x_i = vertices[i][0]
        y_i = vertices[i][1]
        x_j = vertices[j][0]
        y_j = vertices[j][1]
        I_xy += cross_product * (x_i * y_j + 2 * x_i * y_i + 2 * x_j * y_j + x_j * y_i)

    I_xy = I_xy / 24.0

    # Transfer from origin to centroidal axes
    area = calculate_polygon_area(vertices)
    I_xy = I_xy - area * centroid[0] * centroid[1]

    return I_xy  # Note: Can be positive or negative


def calculate_hollow_section_properties(
    outer_vertices: List[Tuple[float, float]],
    inner_vertices_list: List[List[Tuple[float, float]]] = None
) -> Tuple[float, Tuple[float, float], float, float, float]:
    """Calculate section properties for hollow sections (with openings).

    Calculates area, centroid, I_xx, I_yy, and I_xy for sections with voids
    (e.g., tube sections with openings). Uses subtraction method.

    Args:
        outer_vertices: Vertices defining outer boundary (counter-clockwise)
        inner_vertices_list: List of vertex lists defining voids/openings (clockwise)

    Returns:
        Tuple of:
        - area: Net cross-sectional area (units²)
        - centroid: (x, y) coordinates of centroid
        - I_xx: Second moment about centroidal X-X axis (units⁴)
        - I_yy: Second moment about centroidal Y-Y axis (units⁴)
        - I_xy: Product of inertia (units⁴)

    Raises:
        ValueError: If vertices are invalid or openings exceed outer boundary
    """
    # Calculate outer section properties
    A_outer = calculate_polygon_area(outer_vertices)
    cx_outer, cy_outer = calculate_polygon_centroid(outer_vertices)

    # Initialize with outer properties
    Q_x = A_outer * cx_outer  # First moment about Y-axis
    Q_y = A_outer * cy_outer  # First moment about X-axis
    A_net = A_outer

    # Subtract inner voids if present
    if inner_vertices_list:
        for inner_vertices in inner_vertices_list:
            A_inner = calculate_polygon_area(inner_vertices)
            cx_inner, cy_inner = calculate_polygon_centroid(inner_vertices)

            # Subtract first moments
            Q_x -= A_inner * cx_inner
            Q_y -= A_inner * cy_inner
            A_net -= A_inner

    if A_net <= 0:
        raise ValueError("Net area is zero or negative - openings exceed outer boundary")

    # Calculate net centroid
    cx_net = Q_x / A_net
    cy_net = Q_y / A_net
    centroid = (cx_net, cy_net)

    # Calculate second moments about net centroid using parallel axis theorem
    I_xx_outer = calculate_polygon_second_moment_x(outer_vertices, (cx_outer, cy_outer))
    I_yy_outer = calculate_polygon_second_moment_y(outer_vertices, (cx_outer, cy_outer))
    I_xy_outer = calculate_polygon_product_moment(outer_vertices, (cx_outer, cy_outer))

    # Transfer outer section to net centroid
    dy_outer = cy_outer - cy_net
    dx_outer = cx_outer - cx_net
    I_xx = I_xx_outer + A_outer * dy_outer**2
    I_yy = I_yy_outer + A_outer * dx_outer**2
    I_xy = I_xy_outer + A_outer * dx_outer * dy_outer

    # Subtract inner voids (transferred to net centroid)
    if inner_vertices_list:
        for inner_vertices in inner_vertices_list:
            A_inner = calculate_polygon_area(inner_vertices)
            cx_inner, cy_inner = calculate_polygon_centroid(inner_vertices)

            I_xx_inner = calculate_polygon_second_moment_x(inner_vertices, (cx_inner, cy_inner))
            I_yy_inner = calculate_polygon_second_moment_y(inner_vertices, (cx_inner, cy_inner))
            I_xy_inner = calculate_polygon_product_moment(inner_vertices, (cx_inner, cy_inner))

            # Transfer inner void to net centroid
            dy_inner = cy_inner - cy_net
            dx_inner = cx_inner - cx_net
            I_xx -= (I_xx_inner + A_inner * dy_inner**2)
            I_yy -= (I_yy_inner + A_inner * dx_inner**2)
            I_xy -= (I_xy_inner + A_inner * dx_inner * dy_inner)

    return (A_net, centroid, I_xx, I_yy, I_xy)


def calculate_thin_walled_torsional_constant(
    wall_segments: List[Tuple[float, float]]
) -> float:
    """Calculate torsional constant J for thin-walled open sections.

    For thin-walled open sections (e.g., I-sections, C-sections), use:
    J ≈ (1/3) × Σ(b_i × t_i³)

    where b_i is the length and t_i is the thickness of each wall segment.

    This is suitable for preliminary design of core walls modeled as
    assemblies of thin wall segments.

    Args:
        wall_segments: List of (length, thickness) tuples for each wall segment

    Returns:
        Torsional constant J in units⁴

    Raises:
        ValueError: If wall_segments list is empty
    """
    if not wall_segments:
        raise ValueError("At least one wall segment required")

    J = 0.0
    for length, thickness in wall_segments:
        J += (1.0 / 3.0) * length * thickness**3

    return J


def calculate_closed_tube_torsional_constant(
    enclosed_area: float,
    perimeter_segments: List[Tuple[float, float]]
) -> float:
    """Calculate torsional constant J for thin-walled closed sections.

    For thin-walled closed sections (tubes/boxes), use Bredt's formula:
    J = (4 × A_enclosed²) / (∮ ds/t)

    where:
    - A_enclosed = area enclosed by centerline of walls
    - ∮ ds/t = perimeter integral (sum of length/thickness for each segment)

    Args:
        enclosed_area: Area enclosed by centerline of walls (units²)
        perimeter_segments: List of (length, thickness) tuples for perimeter

    Returns:
        Torsional constant J in units⁴

    Raises:
        ValueError: If enclosed area is zero or perimeter is empty
    """
    if enclosed_area <= 0:
        raise ValueError("Enclosed area must be positive")

    if not perimeter_segments:
        raise ValueError("At least one perimeter segment required")

    # Calculate perimeter integral: Σ(s_i / t_i)
    perimeter_integral = sum(length / thickness for length, thickness in perimeter_segments)

    if perimeter_integral <= 0:
        raise ValueError("Perimeter integral must be positive")

    # Bredt's formula
    J = (4 * enclosed_area**2) / perimeter_integral

    return J


def calculate_principal_axes(I_xx: float, I_yy: float, I_xy: float) -> Tuple[float, float, float]:
    """Calculate principal moments of inertia and principal axis angle.

    For asymmetric sections, the principal axes are rotated from the centroidal
    X-Y axes. Principal moments are the maximum and minimum values of I.

    Formulas:
    I_max = (I_xx + I_yy)/2 + sqrt[((I_xx - I_yy)/2)² + I_xy²]
    I_min = (I_xx + I_yy)/2 - sqrt[((I_xx - I_yy)/2)² + I_xy²]
    θ = 0.5 × atan(2 × I_xy / (I_xx - I_yy))

    Args:
        I_xx: Second moment about X-X axis (units⁴)
        I_yy: Second moment about Y-Y axis (units⁴)
        I_xy: Product of inertia (units⁴)

    Returns:
        Tuple of:
        - I_max: Maximum principal moment (units⁴)
        - I_min: Minimum principal moment (units⁴)
        - theta: Principal axis angle in radians (positive counter-clockwise)

    Note:
        For symmetric sections (I_xy = 0), I_max = max(I_xx, I_yy) and theta = 0
    """
    I_avg = (I_xx + I_yy) / 2
    delta_I = (I_xx - I_yy) / 2
    radius = math.sqrt(delta_I**2 + I_xy**2)

    I_max = I_avg + radius
    I_min = I_avg - radius

    # Calculate principal axis angle
    if abs(I_xx - I_yy) < 1e-9:
        # I_xx ≈ I_yy, section has near-circular symmetry
        theta = 0.0 if abs(I_xy) < 1e-9 else math.pi / 4
    else:
        theta = 0.5 * math.atan2(2 * I_xy, I_xx - I_yy)

    return (I_max, I_min, theta)


def calculate_radius_of_gyration(I: float, A: float) -> float:
    """Calculate radius of gyration for a given moment of inertia.

    The radius of gyration is defined as:
    r = sqrt(I / A)

    It represents the distance from the centroidal axis at which the entire
    area could be concentrated to produce the same moment of inertia.

    Args:
        I: Moment of inertia (units⁴)
        A: Cross-sectional area (units²)

    Returns:
        Radius of gyration in units

    Raises:
        ValueError: If area is zero or negative
    """
    if A <= 0:
        raise ValueError("Area must be positive")

    return math.sqrt(I / A)
