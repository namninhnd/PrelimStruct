"""
Visualization Projections Module.

This module handles coordinate transformations for different view types:
- Plan view (XY projection at a specific Z elevation)
- Elevation view (XZ or YZ projection along a specific axis)
- 3D view (Full 3D coordinates)
"""

from typing import Dict, List, Optional, Tuple
import numpy as np

from src.fem.fem_engine import Node, Element


# Type aliases for coordinate tuples
XYCoord = Tuple[float, float]  # Plan view coordinates
XZCoord = Tuple[float, float]  # Elevation view XZ coordinates
YZCoord = Tuple[float, float]  # Elevation view YZ coordinates
XYZCoord = Tuple[float, float, float]  # 3D coordinates


def get_floor_elevations(
    nodes: Dict[int, Node],
    tolerance: float = 0.01
) -> List[float]:
    """Get unique floor elevations from nodes.

    Args:
        nodes: Dictionary of node tag to Node
        tolerance: Elevation tolerance for uniqueness

    Returns:
        Sorted list of unique z-elevations
    """
    elevations: List[float] = []
    for node in nodes.values():
        z = node.z
        if not any(abs(z - e) < tolerance for e in elevations):
            elevations.append(z)
    return sorted(elevations)


def filter_nodes_at_elevation(
    nodes: Dict[int, Node],
    target_z: float,
    tolerance: float = 0.01
) -> Dict[int, Node]:
    """Filter nodes at a specific elevation.

    Args:
        nodes: Dictionary of node tag to Node
        target_z: Target elevation
        tolerance: Elevation tolerance

    Returns:
        Dictionary of nodes at the target elevation
    """
    return {
        tag: node for tag, node in nodes.items()
        if abs(node.z - target_z) < tolerance
    }


def project_to_plan(
    node: Node,
    target_z: Optional[float] = None
) -> XYCoord:
    """Project a node to plan view (XY) coordinates.

    Args:
        node: Node to project
        target_z: Optional target elevation (for filtering)

    Returns:
        (x, y) coordinates
    """
    return (node.x, node.y)


def project_element_to_plan(
    element: Element,
    nodes: Dict[int, Node],
    target_z: float,
    tolerance: float = 0.01
) -> Optional[List[XYCoord]]:
    """Project an element to plan view coordinates.

    Args:
        element: Element to project
        nodes: Dictionary of nodes
        target_z: Target elevation for projection
        tolerance: Elevation tolerance

    Returns:
        List of (x, y) coordinates for element nodes at target elevation,
        or None if element doesn't intersect this elevation
    """
    coords: List[XYCoord] = []
    has_node_at_elevation = False

    for node_tag in element.node_tags:
        node = nodes.get(node_tag)
        if node is None:
            continue
        if abs(node.z - target_z) < tolerance:
            coords.append((node.x, node.y))
            has_node_at_elevation = True
        else:
            # For line continuity, include nodes not at elevation
            # but mark with None to break the line
            coords.append((None, None))

    if not has_node_at_elevation:
        return None

    return coords


def project_to_elevation_xz(
    node: Node,
    target_y: Optional[float] = None,
    tolerance: float = 0.01
) -> Optional[XZCoord]:
    """Project a node to elevation view (XZ) coordinates.

    Args:
        node: Node to project
        target_y: Optional target Y coordinate (for filtering)
        tolerance: Y-coordinate tolerance

    Returns:
        (x, z) coordinates, or None if node not at target Y
    """
    if target_y is not None and abs(node.y - target_y) >= tolerance:
        return None
    return (node.x, node.z)


def project_to_elevation_yz(
    node: Node,
    target_x: Optional[float] = None,
    tolerance: float = 0.01
) -> Optional[YZCoord]:
    """Project a node to elevation view (YZ) coordinates.

    Args:
        node: Node to project
        target_x: Optional target X coordinate (for filtering)
        tolerance: X-coordinate tolerance

    Returns:
        (y, z) coordinates, or None if node not at target X
    """
    if target_x is not None and abs(node.x - target_x) >= tolerance:
        return None
    return (node.y, node.z)


def project_element_to_elevation(
    element: Element,
    nodes: Dict[int, Node],
    axis: str = "X",
    target_coord: Optional[float] = None,
    tolerance: float = 0.01
) -> Optional[List[Tuple[float, float]]]:
    """Project an element to elevation view coordinates.

    Args:
        element: Element to project
        nodes: Dictionary of nodes
        axis: Elevation axis ("X" for XZ view, "Y" for YZ view)
        target_coord: Target X or Y coordinate for filtering
        tolerance: Coordinate tolerance

    Returns:
        List of 2D coordinates for element nodes, or None if not visible
    """
    coords: List[Tuple[float, float]] = []

    for node_tag in element.node_tags:
        node = nodes.get(node_tag)
        if node is None:
            continue

        if axis == "X":
            # XZ elevation - filter by Y coordinate
            if target_coord is not None and abs(node.y - target_coord) >= tolerance:
                continue
            coords.append((node.x, node.z))
        else:
            # YZ elevation - filter by X coordinate
            if target_coord is not None and abs(node.x - target_coord) >= tolerance:
                continue
            coords.append((node.y, node.z))

    return coords if len(coords) >= 2 else None


def get_bounding_box_2d(
    nodes: Dict[int, Node]
) -> Tuple[float, float, float, float]:
    """Get 2D bounding box of nodes.

    Args:
        nodes: Dictionary of nodes

    Returns:
        Tuple of (min_x, max_x, min_y, max_y)
    """
    if not nodes:
        return (0, 1, 0, 1)

    xs = [n.x for n in nodes.values()]
    ys = [n.y for n in nodes.values()]

    return (min(xs), max(xs), min(ys), max(ys))


def get_bounding_box_3d(
    nodes: Dict[int, Node]
) -> Tuple[float, float, float, float, float, float]:
    """Get 3D bounding box of nodes.

    Args:
        nodes: Dictionary of nodes

    Returns:
        Tuple of (min_x, max_x, min_y, max_y, min_z, max_z)
    """
    if not nodes:
        return (0, 1, 0, 1, 0, 1)

    xs = [n.x for n in nodes.values()]
    ys = [n.y for n in nodes.values()]
    zs = [n.z for n in nodes.values()]

    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def calculate_camera_position(
    nodes: Dict[int, Node],
    distance_factor: float = 1.5
) -> Tuple[float, float, float]:
    """Calculate optimal camera position for 3D view.

    Args:
        nodes: Dictionary of nodes
        distance_factor: Distance multiplier from center

    Returns:
        Tuple of (eye_x, eye_y, eye_z)
    """
    bbox = get_bounding_box_3d(nodes)
    center_x = (bbox[0] + bbox[1]) / 2
    center_y = (bbox[2] + bbox[3]) / 2
    center_z = (bbox[4] + bbox[5]) / 2

    # Size of the model
    size = max(bbox[1] - bbox[0], bbox[3] - bbox[2], bbox[5] - bbox[4])

    # Position camera at an angle
    eye_x = center_x + size * distance_factor
    eye_y = center_y + size * distance_factor
    eye_z = center_z + size * distance_factor * 0.5

    return (eye_x, eye_y, eye_z)


__all__ = [
    "get_floor_elevations",
    "filter_nodes_at_elevation",
    "project_to_plan",
    "project_element_to_plan",
    "project_to_elevation_xz",
    "project_to_elevation_yz",
    "project_element_to_elevation",
    "get_bounding_box_2d",
    "get_bounding_box_3d",
    "calculate_camera_position",
]
