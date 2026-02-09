"""
Model builder utilities for FEM generation following OpenSees BuildingTcl conventions.

This module provides a 3-phase FEM model construction workflow:
  - Phase 1: Model Definition (materials, sections, nodes, elements)
  - Phase 2: Load Application (gravity, wind, load patterns)
  - Phase 3: Analysis Preparation (validation, diaphragms)

Floor-based node numbering scheme:
  - Ground level (0): nodes 1-999
  - Level N (N >= 1): nodes N*1000 to N*1000+999
  - Shell elements (walls): nodes 50000-59999
  - Shell elements (slabs): nodes 60000-69999
  
Reference: https://opensees.berkeley.edu/wiki/index.php?title=Getting_Started_with_BuildingTcl
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import logging
import math

logger = logging.getLogger(__name__)

from src.core.constants import CONCRETE_DENSITY, MIN_BEAM_WIDTH, MIN_BEAM_DEPTH, MIN_COLUMN_SIZE
from src.core.data_models import (
    ProjectData,
    CoreWallConfig,
    CoreWallGeometry,
    CoreWallSectionProperties,
    WindResult,
)

from src.fem.beam_trimmer import BeamConnectionType
from src.fem.core_wall_geometry import (
    ISectionCoreWall,
    TwoCFacingCoreWall,
    TwoCBackToBackCoreWall,
    TubeCenterOpeningCoreWall,
    TubeSideOpeningCoreWall,
)
from src.fem.coupling_beam import CouplingBeamGenerator
from src.fem.fem_engine import FEMModel, RigidDiaphragm, Load, Node, Element, ElementType, UniformLoad
from src.fem.materials import ConcreteProperties, get_elastic_beam_section, get_elastic_membrane_plate_section, get_plane_stress_material, get_plate_fiber_section
from src.fem.slab_element import SlabPanel, SlabMeshGenerator, SlabOpening
from src.fem.wall_element import WallPanel, WallMeshGenerator


def _group_nodes_by_elevation(model: FEMModel, tolerance: float = 1e-6) -> Dict[float, List[int]]:
    """Group node tags by z-elevation within a tolerance.

    Args:
        model: FEMModel containing nodes
        tolerance: Elevation tolerance (m) for grouping nodes on the same floor

    Returns:
        Mapping of floor elevation to list of node tags at that elevation
    """
    floors: Dict[float, List[int]] = {}
    for node in model.nodes.values():
        elevation = node.z
        matched_level = None
        for level in floors:
            if abs(level - elevation) <= tolerance:
                matched_level = level
                break
        if matched_level is None:
            floors[elevation] = [node.tag]
        else:
            floors[matched_level].append(node.tag)
    return floors


def create_floor_rigid_diaphragms(model: FEMModel,
                                  base_elevation: float = 0.0,
                                  tolerance: float = 1e-6,
                                  floor_elevations: Optional[List[float]] = None) -> Dict[float, int]:
    """Automatically create rigid diaphragms for each floor level (except base).

    Args:
        model: FEMModel with nodes already created
        base_elevation: Elevation to exclude (typically ground/foundation)
        tolerance: Elevation tolerance (m) for grouping

    Returns:
        Mapping of floor elevation to diaphragm master node tag
    """
    master_by_level: Dict[float, int] = {}

    if floor_elevations is None:
        floors = _group_nodes_by_elevation(model, tolerance)
        target_levels = list(floors.keys())
        level_nodes = floors
    else:
        target_levels = floor_elevations
        level_nodes: Dict[float, List[int]] = {}
        for level in target_levels:
            level_nodes[level] = [
                node.tag for node in model.nodes.values()
                if abs(node.z - level) <= tolerance
            ]

    for level in target_levels:
        if abs(level - base_elevation) <= tolerance:
            continue  # skip base support level
        node_tags = level_nodes.get(level, [])
        if len(node_tags) < 2:
            continue  # no diaphragm needed for a single node

        master = min(node_tags)
        slaves = [tag for tag in node_tags if tag != master]
        model.add_rigid_diaphragm(RigidDiaphragm(master_node=master, slave_nodes=slaves))
        master_by_level[level] = master

    return master_by_level


def apply_lateral_loads_to_diaphragms(model: FEMModel,
                                      floor_shears: Dict[float, float],
                                      direction: str = "X",
                                      load_pattern: int = 1,
                                      tolerance: float = 1e-6,
                                      master_lookup: Optional[Dict[float, int]] = None,
                                      torsional_moments: Optional[Dict[float, float]] = None) -> Dict[float, int]:
    """Apply lateral shear forces (and optional torsional Mz) to diaphragm masters at each floor.

    Args:
        model: FEMModel with diaphragms already added
        floor_shears: Mapping of floor elevation (m) to shear force (N)
        direction: Lateral direction ("X" or "Y")
        load_pattern: Load pattern id
        tolerance: Elevation matching tolerance (m)
        master_lookup: Optional precomputed map of elevation to master node. If not
            provided, the mapping is inferred from existing diaphragms.
        torsional_moments: Optional mapping of floor elevation (m) to torsional moment
            about Z (N-m) applied at diaphragm master

    Returns:
        Mapping of floor elevation to the master node tag used

    Raises:
        ValueError: If a floor shear cannot be mapped to a diaphragm master
    """
    direction = direction.upper()
    if direction not in ("X", "Y"):
        raise ValueError("direction must be 'X' or 'Y'")

    if master_lookup is None:
        # Infer from diaphragms by reading master node elevations
        master_lookup = {}
        for diaphragm in model.diaphragms:
            z = model.nodes[diaphragm.master_node].z
            master_lookup[z] = diaphragm.master_node

    used_masters: Dict[float, int] = {}
    levels_to_apply = set(floor_shears.keys())
    if torsional_moments:
        levels_to_apply |= set(torsional_moments.keys())

    for target_level in levels_to_apply:
        shear = floor_shears.get(target_level, 0.0)
        torque = torsional_moments.get(target_level, 0.0) if torsional_moments else 0.0
        matched_level = None
        matched_master = None
        for level, master in master_lookup.items():
            if abs(level - target_level) <= tolerance:
                matched_level = level
                matched_master = master
                break

        if matched_master is None or matched_level is None:
            raise ValueError(f"No diaphragm master found for elevation {target_level} m")

        load_values = [0.0] * 6  # Fx, Fy, Fz, Mx, My, Mz
        if direction == "X":
            load_values[0] = shear
        else:
            load_values[1] = shear
        load_values[5] = torque

        model.add_load(Load(node_tag=matched_master, load_values=load_values, load_pattern=load_pattern))
        used_masters[matched_level] = matched_master

    return used_masters


@dataclass(frozen=True)
class ModelBuilderOptions:
    """Configuration options for FEM model generation."""
    include_core_wall: bool = True
    include_slabs: bool = True
    trim_beams_at_core: bool = True
    apply_gravity_loads: bool = True
    apply_wind_loads: bool = False  # V3.5: Default False since WindEngine removed
    apply_rigid_diaphragms: bool = True
    secondary_beam_direction: str = "Y"  # "X" or "Y" - direction of secondary beams
    num_secondary_beams: int = 0  # Number of internal secondary beams per bay (default: no subdivisions)
    lateral_load_direction: str = "X"
    # Individual load pattern IDs for separate load case analysis
    dl_load_pattern: int = 1      # Dead load (self-weight: slab + beam)
    sdl_load_pattern: int = 2     # Superimposed dead load (finishes, services)
    ll_load_pattern: int = 3      # Live load
    wx_plus_pattern: int = 4      # Wind +X direction
    wx_minus_pattern: int = 5     # Wind -X direction
    wy_plus_pattern: int = 6      # Wind +Y direction
    wy_minus_pattern: int = 7     # Wind -Y direction
    tolerance: float = 1e-6
    edge_clearance_m: float = 0.5
    slab_thickness: float = 0.15
    slab_elements_per_bay: int = 1  # Mesh density multiplier (higher = finer)
    # Column omission near core walls
    omit_columns_near_core: bool = True
    column_omission_threshold: float = 0.5  # meters (400mm wall + 500mm column + 100mm clearance)
    suggested_omit_columns: Tuple[str, ...] = ()  # User-reviewable column IDs (frozen for immutability)


# Floor-based node numbering: Level N uses N*FLOOR_NODE_BASE as base tag
# Ground level (0) uses tags 1-999, Level 1 uses 1001-1999, etc.
FLOOR_NODE_BASE = 1000


@dataclass(frozen=True)
class BeamSegment:
    """Beam segment after trimming against a core wall boundary."""
    start: Tuple[float, float]
    end: Tuple[float, float]
    start_connection: BeamConnectionType
    end_connection: BeamConnectionType




class NodeRegistry:
    """Registry for unique node creation with floor-based numbering.
    
    Implements OpenSees BuildingTcl node numbering convention:
      - Ground level (0): nodes 1-999
      - Level N (N >= 1): nodes N*1000 to N*1000+999
    
    This makes node tags self-documenting: node 2005 is clearly on Level 2.
    """

    def __init__(self, model: FEMModel, tolerance: float = 1e-6) -> None:
        self.model = model
        self.tolerance = tolerance
        self._key_to_tag: Dict[Tuple[float, float, float], int] = {}
        # Track next available tag per floor level
        self._floor_counters: Dict[int, int] = {}
        # Track nodes per floor for diaphragm creation
        self.nodes_by_floor: Dict[int, List[int]] = {}

    def _key(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        return (round(x, 6), round(y, 6), round(z, 6))

    def _get_next_tag_for_floor(self, floor_level: int) -> int:
        """Get next available node tag for given floor level."""
        if floor_level not in self._floor_counters:
            if floor_level == 0:
                self._floor_counters[floor_level] = 1
            else:
                self._floor_counters[floor_level] = floor_level * FLOOR_NODE_BASE + 1
        
        tag = self._floor_counters[floor_level]
        self._floor_counters[floor_level] += 1
        return tag

    def get_or_create(self,
                      x: float,
                      y: float,
                      z: float,
                      restraints: Optional[List[int]] = None,
                      floor_level: Optional[int] = None) -> int:
        """Get existing node tag for coordinates or create a new node.
        
        Args:
            x: X coordinate (m)
            y: Y coordinate (m)
            z: Z coordinate (m)
            restraints: Boundary conditions [ux, uy, uz, rx, ry, rz]
            floor_level: Optional floor level for floor-based numbering.
                        If None, uses legacy sequential numbering.
        
        Returns:
            Node tag (existing or newly created)
        """
        key = self._key(x, y, z)
        if key in self._key_to_tag:
            tag = self._key_to_tag[key]
            if restraints:
                node = self.model.nodes[tag]
                node.restraints = [max(a, b) for a, b in zip(node.restraints, restraints)]
            return tag

        # Generate floor-based tag if floor_level provided
        if floor_level is not None:
            tag = self._get_next_tag_for_floor(floor_level)
        else:
            # Legacy sequential numbering (for backward compatibility)
            tag = self._get_next_tag_for_floor(0)
        
        node = Node(tag=tag, x=x, y=y, z=z,
                    restraints=restraints or [0, 0, 0, 0, 0, 0])
        self.model.add_node(node)
        self._key_to_tag[key] = tag
        
        # Track node by floor level
        if floor_level is not None:
            if floor_level not in self.nodes_by_floor:
                self.nodes_by_floor[floor_level] = []
            self.nodes_by_floor[floor_level].append(tag)
        
        return tag


def _get_core_wall_outline(geometry: CoreWallGeometry) -> List[Tuple[float, float]]:
    """Get core wall outline coordinates in mm based on configuration."""
    if geometry.config == CoreWallConfig.I_SECTION:
        generator = ISectionCoreWall(geometry)
    elif geometry.config == CoreWallConfig.TWO_C_FACING:
        generator = TwoCFacingCoreWall(geometry)
    elif geometry.config == CoreWallConfig.TWO_C_BACK_TO_BACK:
        generator = TwoCBackToBackCoreWall(geometry)
    elif geometry.config == CoreWallConfig.TUBE_CENTER_OPENING:
        generator = TubeCenterOpeningCoreWall(geometry)
    elif geometry.config == CoreWallConfig.TUBE_SIDE_OPENING:
        generator = TubeSideOpeningCoreWall(geometry)
    else:
        raise ValueError(f"Unsupported core wall configuration: {geometry.config}")

    return generator.get_outline_coordinates()


def _calculate_core_wall_section_properties(geometry: CoreWallGeometry) -> CoreWallSectionProperties:
    """Calculate core wall section properties based on configuration."""
    if geometry.config == CoreWallConfig.I_SECTION:
        return ISectionCoreWall(geometry).calculate_section_properties()
    if geometry.config == CoreWallConfig.TWO_C_FACING:
        return TwoCFacingCoreWall(geometry).calculate_section_properties()
    if geometry.config == CoreWallConfig.TWO_C_BACK_TO_BACK:
        return TwoCBackToBackCoreWall(geometry).calculate_section_properties()
    if geometry.config == CoreWallConfig.TUBE_CENTER_OPENING:
        return TubeCenterOpeningCoreWall(geometry).calculate_section_properties()
    if geometry.config == CoreWallConfig.TUBE_SIDE_OPENING:
        return TubeSideOpeningCoreWall(geometry).calculate_section_properties()

    raise ValueError(f"Unsupported core wall configuration: {geometry.config}")


def _get_core_opening_for_slab(
    core_geometry: CoreWallGeometry,
    offset_x: float,
    offset_y: float,
) -> Optional[SlabOpening]:
    """Extract the internal void area from core wall geometry for slab exclusion.
    
    This returns the interior space of the core wall (elevator lobby, stair area, etc.)
    that should be excluded from the slab mesh. The slab should extend TO the wall 
    outer boundary edges, but NOT exist inside the core interior.
    
    For TUBE configurations: excludes the entire interior of the tube (elevator/stair area)
    For C-facing configurations: excludes the corridor space between C-walls
    For I-SECTION: no interior void, slab extends to wall edges
    
    Args:
        core_geometry: Core wall geometry configuration
        offset_x: X offset of core wall in meters
        offset_y: Y offset of core wall in meters
        
    Returns:
        SlabOpening representing the internal void, or None if no opening exists
    """
    config = core_geometry.config
    wall_thickness_m = core_geometry.wall_thickness / 1000.0
    
    # For TUBE configurations, exclude the entire interior (elevator lobby/stair area)
    # The slab should NOT exist inside the closed box, only extend TO its outer boundary
    if config in (CoreWallConfig.TUBE_CENTER_OPENING, CoreWallConfig.TUBE_SIDE_OPENING):
        length_x_m = (core_geometry.length_x or 0) / 1000.0
        length_y_m = (core_geometry.length_y or 0) / 1000.0
        
        # The interior void is the area inside the walls
        # Interior starts at (offset + wall_thickness) and extends (length - 2*wall_thickness)
        interior_x = offset_x + wall_thickness_m
        interior_y = offset_y + wall_thickness_m
        interior_width_x = length_x_m - 2 * wall_thickness_m
        interior_width_y = length_y_m - 2 * wall_thickness_m
        
        # Ensure positive dimensions
        if interior_width_x <= 0 or interior_width_y <= 0:
            return None
            
        return SlabOpening(
            opening_id="CORE_INTERIOR_VOID",
            origin=(interior_x, interior_y),
            width_x=interior_width_x,
            width_y=interior_width_y,
            opening_type="core_interior",
        )
        
    elif config == CoreWallConfig.TWO_C_FACING:
        # Two C facing: the void is the entire corridor space between the two C-walls
        if core_geometry.opening_width is None:
            return None
            
        flange_width_m = (core_geometry.flange_width or 0) / 1000.0
        web_length_m = (core_geometry.web_length or 0) / 1000.0
        opening_width_m = core_geometry.opening_width / 1000.0
        
        # The void is between the two C-walls (corridor/lobby area)
        # This area spans the full height between flanges
        void_x = offset_x + flange_width_m
        void_y = offset_y + wall_thickness_m  # Clear of bottom flange
        void_height_m = web_length_m - 2 * wall_thickness_m  # Clear height between flanges
        
        if void_height_m <= 0:
            return None
            
        return SlabOpening(
            opening_id="CORE_CORRIDOR_VOID",
            origin=(void_x, void_y),
            width_x=opening_width_m,
            width_y=void_height_m,
            opening_type="core_corridor",
        )
        
    elif config == CoreWallConfig.TWO_C_BACK_TO_BACK:
        # Two C back-to-back: typically forms a closed box similar to tube
        # The interior space between the two C-walls should be excluded
        flange_width_m = (core_geometry.flange_width or 0) / 1000.0
        web_length_m = (core_geometry.web_length or 0) / 1000.0
        connection_m = (core_geometry.opening_width or 0) / 1000.0
        
        # The interior void is between the flanges of both C-walls
        # Total width = 2 * flange_width + 2 * wall_thickness + connection
        # Interior spans from wall_thickness to (total_width - wall_thickness)
        interior_x = offset_x + wall_thickness_m
        interior_y = offset_y + wall_thickness_m
        interior_width_x = 2 * flange_width_m + connection_m
        interior_width_y = web_length_m - 2 * wall_thickness_m
        
        if interior_width_x <= 0 or interior_width_y <= 0:
            return None
            
        return SlabOpening(
            opening_id="CORE_INTERIOR_VOID",
            origin=(interior_x, interior_y),
            width_x=interior_width_x,
            width_y=interior_width_y,
            opening_type="core_interior",
        )
        
    elif config == CoreWallConfig.I_SECTION:
        # I-section: no internal void, slab extends to wall edges on both sides
        # The I-section is solid (web connecting two flanges), no elevator lobby
        return None
        
    # Default: no specific void geometry available
    return None


def _get_core_wall_offset(project: ProjectData,
                          outline_mm: List[Tuple[float, float]],
                          edge_clearance_m: float) -> Tuple[float, float]:
    """Compute core wall offset based on building dimensions.
    
    In V3.5, core location is always defaulted to CENTER per the FEM-only transition.
    """
    if not outline_mm:
        return (0.0, 0.0)

    geometry = project.geometry
    total_x = geometry.bay_x * geometry.num_bays_x
    total_y = geometry.bay_y * geometry.num_bays_y

    min_x = min(pt[0] for pt in outline_mm)
    max_x = max(pt[0] for pt in outline_mm)
    min_y = min(pt[1] for pt in outline_mm)
    max_y = max(pt[1] for pt in outline_mm)
    core_width = (max_x - min_x) / 1000.0
    core_height = (max_y - min_y) / 1000.0

    # Task 17.2: Custom Location Support
    lateral_input = project.lateral
    if lateral_input.location_type == "Custom" and lateral_input.custom_center_x is not None and lateral_input.custom_center_y is not None:
        # User specified center (x, y)
        # Offset is top-left corner (typically), but depends on how wall panels are built.
        # Wall generator typically builds from (offset_x, offset_y) = bottom-left of bounding box
        
        # Calculate offset_x so that center is at custom_center_x
        # center_x = offset_x + core_width/2
        # => offset_x = custom_center_x - core_width/2
        offset_x = lateral_input.custom_center_x - (core_width / 2)
        offset_y = lateral_input.custom_center_y - (core_height / 2)
        
    else:
        # Default: Center placement
        offset_x = (total_x - core_width) / 2
        offset_y = (total_y - core_height) / 2

    return offset_x, offset_y


def _line_segment_intersection(p1: Tuple[float, float],
                               p2: Tuple[float, float],
                               p3: Tuple[float, float],
                               p4: Tuple[float, float],
                               tolerance: float = 1e-9) -> Optional[Tuple[float, float, float]]:
    """Compute intersection point between two line segments with parametric t on segment p1-p2."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    dx1 = x2 - x1
    dy1 = y2 - y1
    dx2 = x4 - x3
    dy2 = y4 - y3
    det = dx1 * dy2 - dy1 * dx2

    if abs(det) < tolerance:
        return None

    t = ((x3 - x1) * dy2 - (y3 - y1) * dx2) / det
    u = ((x3 - x1) * dy1 - (y3 - y1) * dx1) / det

    if -tolerance <= t <= 1 + tolerance and -tolerance <= u <= 1 + tolerance:
        x = x1 + t * dx1
        y = y1 + t * dy1
        return (x, y, t)

    return None


def _point_in_polygon(point: Tuple[float, float],
                      polygon: List[Tuple[float, float]]) -> bool:
    """Check if point is inside polygon using ray casting."""
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _split_outline_loops(outline: List[Tuple[float, float]]) -> List[List[Tuple[float, float]]]:
    """Split outline coordinates into closed loops."""
    loops: List[List[Tuple[float, float]]] = []
    current: List[Tuple[float, float]] = []
    start: Optional[Tuple[float, float]] = None

    for point in outline:
        if not current:
            current = [point]
            start = point
            continue

        current.append(point)
        if start is not None and point == start and len(current) > 2:
            loops.append(current)
            current = []
            start = None

    if current:
        loops.append(current)

    return loops


def _classify_loops(loops: List[List[Tuple[float, float]]]
                    ) -> Tuple[List[List[Tuple[float, float]]], List[List[Tuple[float, float]]]]:
    """Classify outline loops into outer boundaries and holes."""
    outer_loops: List[List[Tuple[float, float]]] = []
    hole_loops: List[List[Tuple[float, float]]] = []

    for idx, loop in enumerate(loops):
        test_point = loop[0]
        is_hole = False
        for jdx, other in enumerate(loops):
            if idx == jdx:
                continue
            if _point_in_polygon(test_point, other):
                is_hole = True
                break
        if is_hole:
            hole_loops.append(loop)
        else:
            outer_loops.append(loop)

    return outer_loops, hole_loops


def trim_beam_segment_against_polygon(start: Tuple[float, float],
                                      end: Tuple[float, float],
                                      polygon: Optional[List[Tuple[float, float]]],
                                      tolerance: float = 1e-6) -> List[BeamSegment]:
    """Trim a beam segment against a polygon boundary (coordinates in mm)."""
    if not polygon:
        return [
            BeamSegment(start=start,
                        end=end,
                        start_connection=BeamConnectionType.PINNED,
                        end_connection=BeamConnectionType.PINNED)
        ]

    outline = polygon[:]
    loops = _split_outline_loops(outline)
    if not loops:
        loops = [outline]
    outer_loops, hole_loops = _classify_loops(loops)
    if not outer_loops:
        outer_loops = loops

    def _is_inside(point: Tuple[float, float]) -> bool:
        inside_outer = any(_point_in_polygon(point, loop) for loop in outer_loops)
        inside_hole = any(_point_in_polygon(point, loop) for loop in hole_loops)
        return inside_outer and not inside_hole

    start_inside = _is_inside(start)
    end_inside = _is_inside(end)

    intersections: List[Tuple[float, float, float]] = []
    for loop in outer_loops:
        loop_points = loop[:]
        if loop_points[0] != loop_points[-1]:
            loop_points.append(loop_points[0])
        for i in range(len(loop_points) - 1):
            hit = _line_segment_intersection(
                start, end, loop_points[i], loop_points[i + 1], tolerance=tolerance
            )
            if hit is not None:
                intersections.append(hit)

    if not intersections:
        if start_inside and end_inside:
            return []
        return [
            BeamSegment(start=start,
                        end=end,
                        start_connection=BeamConnectionType.PINNED,
                        end_connection=BeamConnectionType.PINNED)
        ]

    # Deduplicate intersections by proximity and sort by parameter t
    deduped: List[Tuple[float, float, float]] = []
    for x, y, t in intersections:
        if all(math.hypot(x - dx, y - dy) > tolerance for dx, dy, _ in deduped):
            deduped.append((x, y, t))
    deduped.sort(key=lambda item: item[2])

    if start_inside and end_inside:
        return []

    segments: List[BeamSegment] = []

    if start_inside and not end_inside:
        x_i, y_i, _ = deduped[0]
        segments.append(
            BeamSegment(
                start=(x_i, y_i),
                end=end,
                start_connection=BeamConnectionType.MOMENT,
                end_connection=BeamConnectionType.PINNED,
            )
        )
        return segments

    if end_inside and not start_inside:
        x_i, y_i, _ = deduped[-1]
        segments.append(
            BeamSegment(
                start=start,
                end=(x_i, y_i),
                start_connection=BeamConnectionType.PINNED,
                end_connection=BeamConnectionType.MOMENT,
            )
        )
        return segments

    if len(deduped) < 2:
        return [
            BeamSegment(start=start,
                        end=end,
                        start_connection=BeamConnectionType.PINNED,
                        end_connection=BeamConnectionType.PINNED)
        ]

    first = deduped[0]
    last = deduped[-1]

    segments.append(
        BeamSegment(
            start=start,
            end=(first[0], first[1]),
            start_connection=BeamConnectionType.PINNED,
            end_connection=BeamConnectionType.MOMENT,
        )
    )
    segments.append(
        BeamSegment(
            start=(last[0], last[1]),
            end=end,
            start_connection=BeamConnectionType.MOMENT,
            end_connection=BeamConnectionType.PINNED,
        )
    )
    return segments


def _get_characteristic_loads(
    project: ProjectData,
    slab_thickness_m: Optional[float] = None,
) -> Tuple[float, float, float]:
    """Get unfactored characteristic loads in kPa.
    
    Returns:
        Tuple of (dead_load, sdl, live_load) in kPa
    """
    # Dead load = slab self-weight
    if project.slab_result:
        slab_self_weight = project.slab_result.self_weight  # kPa
    elif slab_thickness_m is not None:
        slab_self_weight = slab_thickness_m * CONCRETE_DENSITY
    else:
        slab_self_weight = 0.2 * 24.5  # Estimate: 200mm slab * 24.5 kN/m³
    
    # SDL = superimposed dead load (finishes, services) from user input
    sdl = project.loads.dead_load  # kPa (this is actually SDL in the UI)
    
    # Live load from code tables
    live_load = project.loads.live_load  # kPa
    
    return (slab_self_weight, sdl, live_load)


def _apply_slab_surface_loads(
    model: FEMModel,
    project: ProjectData,
    slab_element_tags: List[int],
    dl_pattern: int = 1,
    sdl_pattern: int = 2,
    ll_pattern: int = 3,
    slab_thickness_m: Optional[float] = None,
) -> None:
    """Apply surface loads to slab shell elements using separate patterns."""
    from src.fem.fem_engine import SurfaceLoad
    
    dl, sdl, ll = _get_characteristic_loads(project, slab_thickness_m=slab_thickness_m)
    
    # Convert kPa to Pa
    dl_pa = dl * 1000.0
    sdl_pa = sdl * 1000.0
    ll_pa = ll * 1000.0
    
    dl_count = 0
    sdl_count = 0
    ll_count = 0
    
    for elem_tag in slab_element_tags:
        if dl_pa > 0:
            model.add_surface_load(SurfaceLoad(
                element_tag=elem_tag,
                pressure=dl_pa,
                load_pattern=dl_pattern,
            ))
            dl_count += 1
        if sdl_pa > 0:
            model.add_surface_load(SurfaceLoad(
                element_tag=elem_tag,
                pressure=sdl_pa,
                load_pattern=sdl_pattern,
            ))
            sdl_count += 1
        if ll_pa > 0:
            model.add_surface_load(SurfaceLoad(
                element_tag=elem_tag,
                pressure=ll_pa,
                load_pattern=ll_pattern,
            ))
            ll_count += 1
    
    logger.info(
        f"Applied slab loads: DL={dl:.2f}kPa (pattern {dl_pattern}, {dl_count} elements), "
        f"SDL={sdl:.2f}kPa (pattern {sdl_pattern}, {sdl_count} elements), "
        f"LL={ll:.2f}kPa (pattern {ll_pattern}, {ll_count} elements)"
    )


def _extract_beam_sizes(project: ProjectData) -> Dict[str, Tuple[float, float]]:
    """Get beam sizes (width, depth) in mm for primary and secondary beams."""
    primary_width = MIN_BEAM_WIDTH
    primary_depth = MIN_BEAM_DEPTH
    secondary_width = MIN_BEAM_WIDTH
    secondary_depth = MIN_BEAM_DEPTH

    if project.primary_beam_result:
        primary_width = max(primary_width, project.primary_beam_result.width)
        primary_depth = max(primary_depth, project.primary_beam_result.depth)

    if project.secondary_beam_result:
        secondary_width = max(secondary_width, project.secondary_beam_result.width)
        secondary_depth = max(secondary_depth, project.secondary_beam_result.depth)

    return {
        "primary": (primary_width, primary_depth),
        "secondary": (secondary_width, secondary_depth),
    }


def _extract_column_dims(project: ProjectData) -> Tuple[float, float]:
    """Get column dimensions as (width=b, depth=h) in mm.

    Mapping convention for section creation:
    - width (b) maps to local_z direction
    - depth (h) maps to local_y direction

    Prioritizes explicit width/depth over legacy `dimension`.
    Falls back to `dimension` only if explicit width/depth are not set.
    """
    width = MIN_COLUMN_SIZE
    depth = MIN_COLUMN_SIZE

    if project.column_result:
        has_explicit_width = project.column_result.width > 0
        has_explicit_depth = project.column_result.depth > 0
        
        if has_explicit_width:
            width = max(width, project.column_result.width)
        if has_explicit_depth:
            depth = max(depth, project.column_result.depth)
        
        if project.column_result.dimension > 0:
            if not has_explicit_width:
                width = max(width, project.column_result.dimension)
            if not has_explicit_depth:
                depth = max(depth, project.column_result.dimension)

    return width, depth


def _compute_floor_shears(wind_result: WindResult,
                          story_height: float,
                          floors: int) -> Dict[float, float]:
    """Distribute base shear to floors using a triangular profile."""
    if floors <= 0:
        return {}
    heights = [story_height * level for level in range(1, floors + 1)]
    height_sum = sum(heights) if heights else 1.0
    base_shear_n = wind_result.base_shear * 1000.0
    return {
        heights[idx]: base_shear_n * (heights[idx] / height_sum)
        for idx in range(len(heights))
    }


def _extract_wall_panels(
    core_geometry: CoreWallGeometry,
    offset_x: float,
    offset_y: float,
) -> List[WallPanel]:
    """Extract individual wall panels from CoreWallGeometry configuration.
    
    Args:
        core_geometry: Core wall geometry configuration
        offset_x: X offset in meters for wall placement
        offset_y: Y offset in meters for wall placement
        
    Returns:
        List of WallPanel objects representing individual walls
    """
    panels: List[WallPanel] = []
    thickness_m = core_geometry.wall_thickness / 1000.0  # mm to m
    fcu = 40.0  # Default to C40 concrete strength for walls
    
    config = core_geometry.config
    
    if config == CoreWallConfig.I_SECTION:
        # I-section: 2 flanges (parallel to Y) + 1 web (parallel to X)
        length_x_m = core_geometry.length_x / 1000.0
        length_y_m = core_geometry.length_y / 1000.0
        flange_width_m = (core_geometry.flange_width or 2000.0) / 1000.0
        
        # Left flange (parallel to Y-axis)
        panels.append(WallPanel(
            wall_id="IW1",
            base_point=(offset_x, offset_y),
            length=length_y_m,
            thickness=thickness_m,
            height=1.0,  # Placeholder - actual height calculated by mesh generator
            orientation=90.0,  # Parallel to Y
            fcu=fcu,
        ))
        
        # Right flange (parallel to Y-axis)
        panels.append(WallPanel(
            wall_id="IW2",
            base_point=(offset_x + length_x_m, offset_y),
            length=length_y_m,
            thickness=thickness_m,
            height=1.0,
            orientation=90.0,
            fcu=fcu,
        ))
        
        # Web (parallel to X-axis, centered)
        web_y = offset_y + length_y_m / 2
        panels.append(WallPanel(
            wall_id="IW3",
            base_point=(offset_x, web_y),
            length=length_x_m,
            thickness=thickness_m,
            height=1.0,
            orientation=0.0,  # Parallel to X
            fcu=fcu,
        ))
        
    elif config == CoreWallConfig.TUBE_CENTER_OPENING:
        # Tube/box with center opening: 4 walls forming perimeter
        length_x_m = core_geometry.length_x / 1000.0
        length_y_m = core_geometry.length_y / 1000.0
        
        # Bottom wall (parallel to X)
        panels.append(WallPanel(
            wall_id="TW1",
            base_point=(offset_x, offset_y),
            length=length_x_m,
            thickness=thickness_m,
            height=1.0,
            orientation=0.0,
            fcu=fcu,
        ))
        
        # Right wall (parallel to Y)
        panels.append(WallPanel(
            wall_id="TW2",
            base_point=(offset_x + length_x_m, offset_y),
            length=length_y_m,
            thickness=thickness_m,
            height=1.0,
            orientation=90.0,
            fcu=fcu,
        ))
        
        # Top wall (parallel to X)
        panels.append(WallPanel(
            wall_id="TW3",
            base_point=(offset_x, offset_y + length_y_m),
            length=length_x_m,
            thickness=thickness_m,
            height=1.0,
            orientation=0.0,
            fcu=fcu,
        ))
        
        # Left wall (parallel to Y)
        panels.append(WallPanel(
            wall_id="TW4",
            base_point=(offset_x, offset_y),
            length=length_y_m,
            thickness=thickness_m,
            height=1.0,
            orientation=90.0,
            fcu=fcu,
        ))
        
    else:
        # For other configurations (TWO_C_FACING, TWO_C_BACK_TO_BACK, TUBE_SIDE_OPENING),
        # use simplified box representation (can be enhanced later)
        logger.warning(
            f"Wall configuration {config} using simplified box representation. "
            "Full implementation pending."
        )
        length_x_m = core_geometry.length_x / 1000.0
        length_y_m = core_geometry.length_y / 1000.0
        
        # Create 4 walls as a box
        panels.append(WallPanel("W1", (offset_x, offset_y), length_x_m, thickness_m, 1.0, 0.0, fcu))
        panels.append(WallPanel("W2", (offset_x + length_x_m, offset_y), length_y_m, thickness_m, 1.0, 90.0, fcu))
        panels.append(WallPanel("W3", (offset_x, offset_y + length_y_m), length_x_m, thickness_m, 1.0, 0.0, fcu))
        panels.append(WallPanel("W4", (offset_x, offset_y), length_y_m, thickness_m, 1.0, 90.0, fcu))
    
    return panels


def _is_near_core(x: float, y: float, core_polygon_m: Optional[List[Tuple[float, float]]], threshold_m: float) -> bool:
    """Check if point (x, y) in meters is within threshold distance of core wall polygon.
    
    Args:
        x: X coordinate in meters
        y: Y coordinate in meters
        core_polygon_m: Core wall outline in meters (converted from mm)
        threshold_m: Distance threshold in meters
        
    Returns:
        True if point is within threshold distance (or inside) the polygon
    """
    if not core_polygon_m:
        return False
    
    try:
        from shapely.geometry import Point, Polygon
        
        point = Point(x, y)
        poly = Polygon(core_polygon_m)
        distance = point.distance(poly)
        
        return distance <= threshold_m
    except ImportError:
        logger.warning("shapely library not available. Column omission proximity detection disabled.")
        return False


def _suggest_column_omissions(
    geometry,
    core_polygon_m: Optional[List[Tuple[float, float]]],
    threshold_m: float
) -> List[str]:
    """Generate list of column IDs that are within threshold distance of core wall.
    
    Args:
        geometry: ProjectData.geometry with grid information
        core_polygon_m: Core wall outline in meters
        threshold_m: Distance threshold in meters
        
    Returns:
        List of column IDs (e.g., ["A-1", "B-2"]) suggested for omission
    """
    if not core_polygon_m:
        return []
    
    suggested: List[str] = []
    
    # Column naming: ix maps to letters (A, B, C...), iy maps to numbers (1, 2, 3...)
    for ix in range(geometry.num_bays_x + 1):
        for iy in range(geometry.num_bays_y + 1):
            x = ix * geometry.bay_x
            y = iy * geometry.bay_y
            
            if _is_near_core(x, y, core_polygon_m, threshold_m):
                # Column ID format: "A-1", "B-2", etc.
                col_letter = chr(65 + ix)  # 65 = 'A'
                col_id = f"{col_letter}-{iy + 1}"
                suggested.append(col_id)
    
    return suggested


def get_column_omission_suggestions(
    project: ProjectData,
    threshold_m: float = 0.5
) -> List[str]:
    """Public API to generate column omission suggestions for UI review.
    
    This should be called by the UI before creating ModelBuilderOptions,
    so the user can review and modify the suggested omissions.
    
    Args:
        project: Project data with geometry and core wall configuration
        threshold_m: Distance threshold in meters (default 0.5m)
        
    Returns:
        List of column IDs suggested for omission (e.g., ["B-2", "C-3"])
    """
    if not project.lateral.core_geometry:
        return []
    
    # Extract core outline and convert to meters
    outline_mm = _get_core_wall_outline(project.lateral.core_geometry)
    offset_x, offset_y = _get_core_wall_offset(project, outline_mm, 0.5)  # Use default edge clearance
    core_polygon_m = [
        ((x / 1000.0) + offset_x, (y / 1000.0) + offset_y) for x, y in outline_mm
    ]
    
    return _suggest_column_omissions(project.geometry, core_polygon_m, threshold_m)


# Number of sub-elements per beam (consistent with beam_builder.py)
NUM_SUBDIVISIONS = 4


def _create_subdivided_beam(
    model: FEMModel,
    registry: "NodeRegistry",
    start_node: int,
    end_node: int,
    section_tag: int,
    material_tag: int,
    floor_level: int,
    element_tag: int,
    element_type: ElementType = ElementType.ELASTIC_BEAM,
) -> Tuple[int, int]:
    """Create a beam with 4 sub-elements and 3 intermediate nodes.
    
    Args:
        model: FEM model to add elements to
        registry: Node registry for creating intermediate nodes
        start_node: Tag of start node
        end_node: Tag of end node
        section_tag: Section property tag
        material_tag: Material tag
        floor_level: Floor level for node creation
        element_tag: Starting element tag
        element_type: Type of beam element (ELASTIC_BEAM or SECONDARY_BEAM)
        
    Returns:
        Tuple of (next_element_tag, parent_beam_id)
    """
    # Get start and end node coordinates
    start_node_obj = model.nodes[start_node]
    end_node_obj = model.nodes[end_node]
    
    start_x, start_y, start_z = start_node_obj.x, start_node_obj.y, start_node_obj.z
    end_x, end_y, end_z = end_node_obj.x, end_node_obj.y, end_node_obj.z
    
    # Create 3 intermediate nodes + reuse start/end (total 5 nodes)
    node_tags = [start_node]
    
    for i in range(1, NUM_SUBDIVISIONS):
        t = i / NUM_SUBDIVISIONS  # 1/4, 2/4, 3/4
        inter_x = start_x + t * (end_x - start_x)
        inter_y = start_y + t * (end_y - start_y)
        inter_z = start_z + t * (end_z - start_z)
        
        inter_node = registry.get_or_create(inter_x, inter_y, inter_z, floor_level=floor_level)
        node_tags.append(inter_node)
    
    node_tags.append(end_node)
    
    # Track parent beam ID for logical grouping
    parent_beam_id = element_tag
    
    dx = end_x - start_x
    dy = end_y - start_y
    length_xy = math.hypot(dx, dy)
    if length_xy > 1e-10:
        vecxz_val = (dy / length_xy, -dx / length_xy, 0.0)
    else:
        vecxz_val = (0.0, 0.0, 1.0)

    # Create 4 sub-elements connecting the 5 nodes sequentially
    for i in range(NUM_SUBDIVISIONS):
        current_tag = element_tag
        
        geom = {
            "vecxz": vecxz_val,
            "parent_beam_id": parent_beam_id,
            "sub_element_index": i,
        }
        
        model.add_element(Element(
            tag=current_tag,
            element_type=element_type,
            node_tags=[node_tags[i], node_tags[i + 1]],
            material_tag=material_tag,
            section_tag=section_tag,
            geometry=geom,
        ))
        
        element_tag += 1
    
    return element_tag, parent_beam_id


def build_fem_model(project: ProjectData,
                    options: Optional[ModelBuilderOptions] = None) -> FEMModel:
    """Build FEMModel from ProjectData geometry, results, and loads."""
    options = options or ModelBuilderOptions()
    geometry = project.geometry

    model = FEMModel()
    registry = NodeRegistry(model, tolerance=options.tolerance)

    beam_sizes = _extract_beam_sizes(project)
    column_width, column_depth = _extract_column_dims(project)

    beam_concrete = ConcreteProperties(fcu=project.materials.fcu_beam)
    column_concrete = ConcreteProperties(fcu=project.materials.fcu_column)

    beam_material_tag = 1
    column_material_tag = 2
    core_material_tag = 3

    model.add_material(beam_material_tag, {
        "material_type": "Concrete01",
        "tag": beam_material_tag,
        "fpc": -beam_concrete.design_strength * 1e6,
        "epsc0": -0.002,
        "fpcu": -0.85 * beam_concrete.design_strength * 1e6,
        "epsU": -0.0035,
    })
    model.add_material(column_material_tag, {
        "material_type": "Concrete01",
        "tag": column_material_tag,
        "fpc": -column_concrete.design_strength * 1e6,
        "epsc0": -0.002,
        "fpcu": -0.85 * column_concrete.design_strength * 1e6,
        "epsU": -0.0035,
    })

    primary_section_tag = 1
    secondary_section_tag = 2
    column_section_tag = 3
    core_section_tag = 4

    primary_section = get_elastic_beam_section(
        beam_concrete,
        width=beam_sizes["primary"][0],
        height=beam_sizes["primary"][1],
        section_tag=primary_section_tag,
    )
    secondary_section = get_elastic_beam_section(
        beam_concrete,
        width=beam_sizes["secondary"][0],
        height=beam_sizes["secondary"][1],
        section_tag=secondary_section_tag,
    )
    column_section = get_elastic_beam_section(
        column_concrete,
        width=column_width,
        height=column_depth,
        section_tag=column_section_tag,
    )

    model.add_section(primary_section_tag, primary_section)
    model.add_section(secondary_section_tag, secondary_section)
    model.add_section(column_section_tag, column_section)

    # Phase 1: Model Definition - Create nodes (OpenSees BuildingTcl pattern)
    # Use floor-based numbering: Level 0 = 1-999, Level N = N*1000+
    grid_nodes: Dict[Tuple[int, int, int], int] = {}
    for level in range(geometry.floors + 1):
        z = level * geometry.story_height
        for ix in range(geometry.num_bays_x + 1):
            for iy in range(geometry.num_bays_y + 1):
                x = ix * geometry.bay_x
                y = iy * geometry.bay_y
                restraints = [1, 1, 1, 1, 1, 1] if level == 0 else None
                tag = registry.get_or_create(x, y, z, restraints=restraints, floor_level=level)
                grid_nodes[(ix, iy, level)] = tag

    # Phase 1 (continued): Create elements
    element_tag = 1

    # Prepare column omission logic
    core_polygon_m: Optional[List[Tuple[float, float]]] = None
    omit_column_ids: set = set()
    
    if options.omit_columns_near_core and options.include_core_wall and project.lateral.core_geometry:
        # Extract core outline and convert to meters for proximity detection
        outline_mm = _get_core_wall_outline(project.lateral.core_geometry)
        offset_x, offset_y = _get_core_wall_offset(project, outline_mm, options.edge_clearance_m)
        core_polygon_m = [
            ((x / 1000.0) + offset_x, (y / 1000.0) + offset_y) for x, y in outline_mm
        ]
        
        # Use user-approved omission list (from options.suggested_omit_columns)
        # If empty, this means user hasn't been presented with suggestions yet
        omit_column_ids = set(options.suggested_omit_columns)

    # Columns
    omitted_columns: List[str] = []
    for level in range(geometry.floors):
        for ix in range(geometry.num_bays_x + 1):
            for iy in range(geometry.num_bays_y + 1):
                # Generate column ID for omission check
                col_letter = chr(65 + ix)  # 65 = 'A'
                col_id = f"{col_letter}-{iy + 1}"
                
                # Check if this column should be omitted
                if col_id in omit_column_ids:
                    if level == 0:  # Only log once (at base level)
                        omitted_columns.append(col_id)
                    continue  # Skip this column
                
                start_node = grid_nodes[(ix, iy, level)]
                end_node = grid_nodes[(ix, iy, level + 1)]

                start_node_obj = model.nodes[start_node]
                end_node_obj = model.nodes[end_node]

                start_x, start_y, start_z = start_node_obj.x, start_node_obj.y, start_node_obj.z
                end_x, end_y, end_z = end_node_obj.x, end_node_obj.y, end_node_obj.z

                node_tags = [start_node]
                for i in range(1, NUM_SUBDIVISIONS):
                    t = i / NUM_SUBDIVISIONS
                    inter_x = start_x + t * (end_x - start_x)
                    inter_y = start_y + t * (end_y - start_y)
                    inter_z = start_z + t * (end_z - start_z)
                    inter_node = registry.get_or_create(
                        inter_x, inter_y, inter_z, floor_level=level
                    )
                    node_tags.append(inter_node)

                node_tags.append(end_node)

                parent_column_id = element_tag
                for i in range(NUM_SUBDIVISIONS):
                    # Column local axis convention (ETABS-compatible):
                    # local_x = vertical column axis (bottom -> top),
                    # local_y = global X (depth h), local_z = global Y (width b).
                    # vecxz=(0,1,0) enforces this orientation for vertical columns.
                    # Iz = b*h^3/12 -> Mz (major-axis), Iy = h*b^3/12 -> My (minor-axis).
                    geom = {
                        "vecxz": (0.0, 1.0, 0.0),
                        "parent_column_id": parent_column_id,
                        "sub_element_index": i,
                    }
                    model.add_element(
                        Element(
                            tag=element_tag,
                            element_type=ElementType.ELASTIC_BEAM,
                            node_tags=[node_tags[i], node_tags[i + 1]],
                            material_tag=column_material_tag,
                            section_tag=column_section_tag,
                            geometry=geom,
                        )
                    )
                    element_tag += 1

                if options.apply_gravity_loads:
                    width_m = column_width / 1000.0
                    depth_m = column_depth / 1000.0
                    area_m2 = width_m * depth_m
                    line_weight_n = CONCRETE_DENSITY * area_m2 * 1000.0
                    for i in range(NUM_SUBDIVISIONS):
                        node_i = model.nodes.get(node_tags[i])
                        node_j = model.nodes.get(node_tags[i + 1])
                        if node_i is None or node_j is None:
                            continue
                        length_m = abs(node_j.z - node_i.z)
                        if length_m <= 1e-6:
                            continue
                        nodal_load = -line_weight_n * length_m / 2.0
                        model.add_load(
                            Load(
                                node_tag=node_tags[i],
                                load_values=[0.0, 0.0, nodal_load, 0.0, 0.0, 0.0],
                                load_pattern=options.dl_load_pattern,
                            )
                        )
                        model.add_load(
                            Load(
                                node_tag=node_tags[i + 1],
                                load_values=[0.0, 0.0, nodal_load, 0.0, 0.0, 0.0],
                                load_pattern=options.dl_load_pattern,
                            )
                        )
    
    # Log omitted columns and add to model for ghost visualization
    if omitted_columns:
        logger.info(f"Omitted {len(omitted_columns)} columns near core wall: {', '.join(omitted_columns)}")
        
        # Add ghost column locations for visualization
        for col_id in omitted_columns:
            # Parse column ID (e.g., "A-1" -> ix=0, iy=0)
            col_letter = col_id.split('-')[0]
            col_number = int(col_id.split('-')[1])
            ix = ord(col_letter) - 65  # 'A' = 0
            iy = col_number - 1
            
            x = ix * geometry.bay_x
            y = iy * geometry.bay_y
            
            model.omitted_columns.append({
                "x": x,
                "y": y,
                "id": col_id,
            })

    # Use user's explicit choice for secondary beam direction
    # If secondary beams are along X, then primary beams are along Y (primary_along_x = False)
    # If secondary beams are along Y, then primary beams are along X (primary_along_x = True)
    primary_along_x = options.secondary_beam_direction == "Y"

    core_outline_global: Optional[List[Tuple[float, float]]] = None
    core_boundary_points: List[Tuple[float, float]] = []

    # Warn if beam trimming is requested but core geometry is missing
    if options.trim_beams_at_core and not project.lateral.core_geometry:
        logger.warning(
            "Beam trimming at core wall requested but core_geometry is None. "
            "Beams will not be trimmed. Set core_geometry in LateralInput to enable trimming."
        )

    if options.include_core_wall and project.lateral.core_geometry:
        outline = _get_core_wall_outline(project.lateral.core_geometry)
        offset_x, offset_y = _get_core_wall_offset(project, outline, options.edge_clearance_m)
        core_outline_global = [
            (x + offset_x * 1000.0, y + offset_y * 1000.0) for x, y in outline
        ]
        core_boundary_points.extend(core_outline_global)

    # Beams along X direction (AT ALL GRIDLINES)
    # These are the gridline beams and should ALL be PRIMARY beams
    # Internal subdivision beams are created separately below
    for level in range(1, geometry.floors + 1):
        z = level * geometry.story_height
        for iy in range(geometry.num_bays_y + 1):  # All Y gridlines
            y = iy * geometry.bay_y
            # All gridline beams are PRIMARY beams
            section_tag = primary_section_tag
            section_dims = beam_sizes["primary"]

            for ix in range(geometry.num_bays_x):
                x_start = ix * geometry.bay_x
                x_end = (ix + 1) * geometry.bay_x
                segments = trim_beam_segment_against_polygon(
                    start=(x_start * 1000.0, y * 1000.0),
                    end=(x_end * 1000.0, y * 1000.0),
                    polygon=core_outline_global if options.trim_beams_at_core else None,
                )

                for segment in segments:
                    if math.hypot(segment.end[0] - segment.start[0],
                                  segment.end[1] - segment.start[1]) <= options.tolerance * 1000:
                        continue
                    start_node = registry.get_or_create(
                        segment.start[0] / 1000.0, segment.start[1] / 1000.0, z,
                        floor_level=level
                    )
                    end_node = registry.get_or_create(
                        segment.end[0] / 1000.0, segment.end[1] / 1000.0, z,
                        floor_level=level
                    )

                    if segment.start_connection == BeamConnectionType.MOMENT:
                        core_boundary_points.append(segment.start)
                    if segment.end_connection == BeamConnectionType.MOMENT:
                        core_boundary_points.append(segment.end)

                    element_tag, parent_beam_id = _create_subdivided_beam(
                        model=model,
                        registry=registry,
                        start_node=start_node,
                        end_node=end_node,
                        section_tag=section_tag,
                        material_tag=beam_material_tag,
                        floor_level=level,
                        element_tag=element_tag,
                        element_type=ElementType.ELASTIC_BEAM,
                    )

                    if options.apply_gravity_loads:
                        width_m = section_dims[0] / 1000.0
                        depth_m = section_dims[1] / 1000.0
                        beam_self_weight = CONCRETE_DENSITY * width_m * depth_m
                        w_total = beam_self_weight * 1000.0  # N/m
                        for sub_idx in range(NUM_SUBDIVISIONS):
                            model.add_uniform_load(
                                UniformLoad(
                                    element_tag=parent_beam_id + sub_idx,
                                    load_type="Gravity",
                                    magnitude=w_total,
                                    load_pattern=options.dl_load_pattern,
                                )
                            )

    # Beams along Y direction (AT ALL GRIDLINES)
    # These are the gridline beams and should ALL be PRIMARY beams
    # Internal subdivision beams are created separately below
    for level in range(1, geometry.floors + 1):
        z = level * geometry.story_height
        for ix in range(geometry.num_bays_x + 1):  # All X gridlines
            x = ix * geometry.bay_x
            # All gridline beams are PRIMARY beams
            section_tag = primary_section_tag
            section_dims = beam_sizes["primary"]

            for iy in range(geometry.num_bays_y):
                y_start = iy * geometry.bay_y
                y_end = (iy + 1) * geometry.bay_y
                segments = trim_beam_segment_against_polygon(
                    start=(x * 1000.0, y_start * 1000.0),
                    end=(x * 1000.0, y_end * 1000.0),
                    polygon=core_outline_global if options.trim_beams_at_core else None,
                )

                for segment in segments:
                    if math.hypot(segment.end[0] - segment.start[0],
                                  segment.end[1] - segment.start[1]) <= options.tolerance * 1000:
                        continue
                    start_node = registry.get_or_create(
                        segment.start[0] / 1000.0, segment.start[1] / 1000.0, z,
                        floor_level=level
                    )
                    end_node = registry.get_or_create(
                        segment.end[0] / 1000.0, segment.end[1] / 1000.0, z,
                        floor_level=level
                    )

                    if segment.start_connection == BeamConnectionType.MOMENT:
                        core_boundary_points.append(segment.start)
                    if segment.end_connection == BeamConnectionType.MOMENT:
                        core_boundary_points.append(segment.end)

                    element_tag, parent_beam_id = _create_subdivided_beam(
                        model=model,
                        registry=registry,
                        start_node=start_node,
                        end_node=end_node,
                        section_tag=section_tag,
                        material_tag=beam_material_tag,
                        floor_level=level,
                        element_tag=element_tag,
                        element_type=ElementType.ELASTIC_BEAM,
                    )

                    if options.apply_gravity_loads:
                        width_m = section_dims[0] / 1000.0
                        depth_m = section_dims[1] / 1000.0
                        beam_self_weight = CONCRETE_DENSITY * width_m * depth_m
                        w_total = beam_self_weight * 1000.0  # N/m
                        for sub_idx in range(NUM_SUBDIVISIONS):
                            model.add_uniform_load(
                                UniformLoad(
                                    element_tag=parent_beam_id + sub_idx,
                                    load_type="Gravity",
                                    magnitude=w_total,
                                    load_pattern=options.dl_load_pattern,
                                )
                            )

    # Internal secondary beam subdivision (NEW: Task 18.2)
    # Generate num_secondary_beams internal beams per bay, equally spaced
    # R1: Secondary beams are also trimmed at core wall boundaries
    if options.num_secondary_beams > 0:
        for level in range(1, geometry.floors + 1):
            z = level * geometry.story_height
            floor_level = level
            
            # CORRECTED LOGIC: secondary_beam_direction controls subdivision direction
            # If secondary_beam_direction="Y", create Y-direction beams
            # If secondary_beam_direction="X", create X-direction beams
            
            if options.secondary_beam_direction == "Y":
                # Secondary beams run along Y (internal to X bays)
                for ix in range(geometry.num_bays_x):
                    x_start_bay = ix * geometry.bay_x
                    x_end_bay = (ix + 1) * geometry.bay_x
                    
                    # Create num_secondary_beams equally spaced within this X bay
                    for i in range(1, options.num_secondary_beams + 1):
                        x = x_start_bay + (i / (options.num_secondary_beams + 1)) * geometry.bay_x
                        
                        # Span from y=0 to y=total_y
                        for iy in range(geometry.num_bays_y):
                            y_start = iy * geometry.bay_y
                            y_end = (iy + 1) * geometry.bay_y
                            
                            # R1: Apply beam trimming at core wall boundaries
                            segments = trim_beam_segment_against_polygon(
                                start=(x * 1000.0, y_start * 1000.0),
                                end=(x * 1000.0, y_end * 1000.0),
                                polygon=core_outline_global if options.trim_beams_at_core else None,
                            )
                            
                            for segment in segments:
                                # Skip very short segments (tolerance check)
                                if math.hypot(segment.end[0] - segment.start[0],
                                              segment.end[1] - segment.start[1]) <= options.tolerance * 1000:
                                    continue
                                
                                # Create nodes from segment endpoints (converted back to meters)
                                start_node = registry.get_or_create(
                                    segment.start[0] / 1000.0, segment.start[1] / 1000.0, z,
                                    floor_level=floor_level
                                )
                                end_node = registry.get_or_create(
                                    segment.end[0] / 1000.0, segment.end[1] / 1000.0, z,
                                    floor_level=floor_level
                                )
                                
                                # Track core boundary points for moment connections
                                if segment.start_connection == BeamConnectionType.MOMENT:
                                    core_boundary_points.append(segment.start)
                                if segment.end_connection == BeamConnectionType.MOMENT:
                                    core_boundary_points.append(segment.end)
                                
                                # Create subdivided secondary beam (6 sub-elements)
                                element_tag, _ = _create_subdivided_beam(
                                    model=model,
                                    registry=registry,
                                    start_node=start_node,
                                    end_node=end_node,
                                    section_tag=secondary_section_tag,
                                    material_tag=beam_material_tag,
                                    floor_level=floor_level,
                                    element_tag=element_tag,
                                    element_type=ElementType.SECONDARY_BEAM,
                                )

                                # Apply gravity loads to all sub-elements
                                if options.apply_gravity_loads:
                                    width_m = beam_sizes["secondary"][0] / 1000.0
                                    depth_m = beam_sizes["secondary"][1] / 1000.0
                                    beam_self_weight = CONCRETE_DENSITY * width_m * depth_m
                                    w_total = beam_self_weight * 1000.0  # N/m
                                    for sub_idx in range(NUM_SUBDIVISIONS):
                                        model.add_uniform_load(
                                            UniformLoad(
                                                element_tag=element_tag - NUM_SUBDIVISIONS + sub_idx,
                                                load_type="Gravity",
                                                magnitude=w_total,
                                                load_pattern=options.dl_load_pattern,
                                            )
                                        )

            else:  # secondary_beam_direction == "X"
                # Secondary beams run along X (internal to Y bays)
                for iy in range(geometry.num_bays_y):
                    y_start_bay = iy * geometry.bay_y
                    y_end_bay = (iy + 1) * geometry.bay_y
                    
                    # Create num_secondary_beams equally spaced within this Y bay
                    for i in range(1, options.num_secondary_beams + 1):
                        y = y_start_bay + (i / (options.num_secondary_beams + 1)) * geometry.bay_y
                        
                        # Span from x=0 to x=total_x
                        for ix in range(geometry.num_bays_x):
                            x_start = ix * geometry.bay_x
                            x_end = (ix + 1) * geometry.bay_x
                            
                            # R1: Apply beam trimming at core wall boundaries
                            segments = trim_beam_segment_against_polygon(
                                start=(x_start * 1000.0, y * 1000.0),
                                end=(x_end * 1000.0, y * 1000.0),
                                polygon=core_outline_global if options.trim_beams_at_core else None,
                            )
                            
                            for segment in segments:
                                # Skip very short segments (tolerance check)
                                if math.hypot(segment.end[0] - segment.start[0],
                                              segment.end[1] - segment.start[1]) <= options.tolerance * 1000:
                                    continue
                                
                                # Create nodes from segment endpoints (converted back to meters)
                                start_node = registry.get_or_create(
                                    segment.start[0] / 1000.0, segment.start[1] / 1000.0, z,
                                    floor_level=floor_level
                                )
                                end_node = registry.get_or_create(
                                    segment.end[0] / 1000.0, segment.end[1] / 1000.0, z,
                                    floor_level=floor_level
                                )
                                
                                # Track core boundary points for moment connections
                                if segment.start_connection == BeamConnectionType.MOMENT:
                                    core_boundary_points.append(segment.start)
                                if segment.end_connection == BeamConnectionType.MOMENT:
                                    core_boundary_points.append(segment.end)
                                
                                # Create subdivided secondary beam (6 sub-elements)
                                element_tag, _ = _create_subdivided_beam(
                                    model=model,
                                    registry=registry,
                                    start_node=start_node,
                                    end_node=end_node,
                                    section_tag=secondary_section_tag,
                                    material_tag=beam_material_tag,
                                    floor_level=floor_level,
                                    element_tag=element_tag,
                                    element_type=ElementType.SECONDARY_BEAM,
                                )

                                # Apply gravity loads to all sub-elements
                                if options.apply_gravity_loads:
                                    width_m = beam_sizes["secondary"][0] / 1000.0
                                    depth_m = beam_sizes["secondary"][1] / 1000.0
                                    beam_self_weight = CONCRETE_DENSITY * width_m * depth_m
                                    w_total = beam_self_weight * 1000.0  # N/m
                                    for sub_idx in range(NUM_SUBDIVISIONS):
                                        model.add_uniform_load(
                                            UniformLoad(
                                                element_tag=element_tag - NUM_SUBDIVISIONS + sub_idx,
                                                load_type="Gravity",
                                                magnitude=w_total,
                                                load_pattern=options.dl_load_pattern,
                                            )
                                        )



    # Core wall elements (ShellMITC4 mesh with PlateFiberSection)
    # MOVED BEFORE SLABS to allow slab mesh to snap to wall nodes
    if options.include_core_wall and project.lateral.core_geometry:
        wall_concrete = ConcreteProperties(fcu=project.materials.fcu_column)
        wall_material_tag = 10  # NDMaterial tag for wall plane stress
        wall_section_tag = 10   # PlateFiberSection tag for wall shells
        
        # Create NDMaterial for plane stress (ElasticIsotropic)
        wall_nd_material = get_plane_stress_material(wall_concrete, wall_material_tag)
        model.add_material(wall_material_tag, wall_nd_material)
        
        # Create PlateFiberSection for ShellMITC4
        thickness_m = project.lateral.core_geometry.wall_thickness / 1000.0
        wall_section = get_plate_fiber_section(
            nd_material_tag=wall_material_tag,
            thickness=thickness_m,
            section_tag=wall_section_tag,
        )
        model.add_section(wall_section_tag, wall_section)
        
        # Get wall offset
        outline = _get_core_wall_outline(project.lateral.core_geometry)
        offset_x, offset_y = _get_core_wall_offset(project, outline, options.edge_clearance_m)
        
        # Extract wall panels from core geometry
        wall_panels = _extract_wall_panels(
            project.lateral.core_geometry,
            offset_x,
            offset_y,
        )
        
        # Create wall mesh generator
        wall_mesh_generator = WallMeshGenerator(
            base_node_tag=50000,    # Use 50000-59999 range for wall nodes
            base_element_tag=50000,  # Use 50000-59999 range for wall elements
        )
        
        # Generate mesh for each wall panel
        for wall in wall_panels:
            mesh_result = wall_mesh_generator.generate_mesh(
                wall=wall,
                num_floors=geometry.floors,
                story_height=geometry.story_height,
                section_tag=wall_section_tag,
                elements_along_length=2,   # 2 elements along wall length
                elements_per_story=2,       # 2 elements per story height
            )
            
            # Add wall nodes to model
            for node_tag, x, y, z, floor_level in mesh_result.nodes:
                restraints = [1, 1, 1, 1, 1, 1] if z == 0.0 else None
                node = Node(tag=node_tag, x=x, y=y, z=z)
                model.add_node(node)
                
                # Track in registry for diaphragms
                if floor_level not in registry.nodes_by_floor:
                    registry.nodes_by_floor[floor_level] = []
                registry.nodes_by_floor[floor_level].append(node_tag)
            
            # Add wall shell elements
            for shell_quad in mesh_result.elements:
                model.add_element(
                    Element(
                        tag=shell_quad.tag,
                        element_type=ElementType.SHELL_MITC4,
                        node_tags=list(shell_quad.node_tags),
                        material_tag=wall_material_tag,
                        section_tag=shell_quad.section_tag,
                    )
                )
            
        logger.info(
            f"Generated shell mesh for {len(wall_panels)} wall panels using ShellMITC4 elements"
        )
        
        # Generate coupling beams for core walls with openings
        # Coupling beams connect wall piers across openings at each floor level
        core_geometry = project.lateral.core_geometry
        if core_geometry.opening_width is not None and core_geometry.opening_width > 0:
            coupling_beam_generator = CouplingBeamGenerator(core_geometry)
            coupling_beams = coupling_beam_generator.generate_coupling_beams(
                story_height=geometry.story_height * 1000.0,  # Convert m to mm
                top_clearance=200.0,  # mm
                bottom_clearance=200.0,  # mm
            )
            
            if coupling_beams:
                # Create coupling beam section (use beam concrete properties)
                coupling_section_tag = 20
                coupling_beam_template = coupling_beams[0]  # Use first beam as template
                
                coupling_section = get_elastic_beam_section(
                    beam_concrete,
                    width=coupling_beam_template.width,  # mm
                    height=coupling_beam_template.depth,  # mm
                    section_tag=coupling_section_tag,
                )
                model.add_section(coupling_section_tag, coupling_section)
                
                coupling_element_tag = 70000  # Use 70000+ range for coupling beams
                coupling_beams_created = 0
                
                # Generate coupling beams at each floor level
                for level in range(1, geometry.floors + 1):
                    z = level * geometry.story_height  # Elevation in m
                    
                    for cb in coupling_beams:
                        # Get beam location (convert mm to m)
                        # The location is relative to core wall origin, need to add offset
                        cb_x_center = (cb.location_x / 1000.0) + offset_x
                        cb_y_center = (cb.location_y / 1000.0) + offset_y
                        
                        # Calculate beam start and end points based on opening
                        # For TWO_C_FACING: beam spans horizontally (along X) across the opening
                        # For TUBE configs: beam may span in X or Y depending on opening location
                        half_span = (cb.clear_span / 2.0) / 1000.0  # Convert mm to m
                        
                        # Determine beam orientation based on core config
                        if core_geometry.config in (
                            CoreWallConfig.TWO_C_FACING,
                            CoreWallConfig.TUBE_CENTER_OPENING,
                        ):
                            # Beam spans along X direction (horizontal)
                            start_x = cb_x_center - half_span
                            start_y = cb_y_center
                            end_x = cb_x_center + half_span
                            end_y = cb_y_center
                        elif core_geometry.config == CoreWallConfig.TUBE_SIDE_OPENING:
                            # Beam spans along Y direction (for side opening in left wall)
                            start_x = cb_x_center
                            start_y = cb_y_center - half_span
                            end_x = cb_x_center
                            end_y = cb_y_center + half_span
                        elif core_geometry.config == CoreWallConfig.TWO_C_BACK_TO_BACK:
                            # Two beams: span along X at different Y positions
                            # The coupling beam generator creates 2 beams for this config
                            start_x = cb_x_center - half_span
                            start_y = cb_y_center
                            end_x = cb_x_center + half_span
                            end_y = cb_y_center
                        else:
                            # Default: span along X
                            start_x = cb_x_center - half_span
                            start_y = cb_y_center
                            end_x = cb_x_center + half_span
                            end_y = cb_y_center
                        
                        # Create nodes for coupling beam ends
                        start_node = registry.get_or_create(
                            start_x, start_y, z, floor_level=level
                        )
                        end_node = registry.get_or_create(
                            end_x, end_y, z, floor_level=level
                        )
                        
                        # Create 5 intermediate nodes at 1/6, 2/6, 3/6, 4/6, 5/6 positions
                        node_tags = [start_node]
                        for i in range(1, NUM_SUBDIVISIONS):
                            t = i / NUM_SUBDIVISIONS
                            inter_x = start_x + t * (end_x - start_x)
                            inter_y = start_y + t * (end_y - start_y)
                            inter_z = z  # Same elevation
                            inter_node = registry.get_or_create(
                                inter_x, inter_y, inter_z, floor_level=level
                            )
                            node_tags.append(inter_node)
                        node_tags.append(end_node)
                        
                        # Track parent coupling beam ID for logical grouping
                        parent_coupling_beam_id = coupling_element_tag

                        cb_dx = end_x - start_x
                        cb_dy = end_y - start_y
                        cb_length_xy = math.hypot(cb_dx, cb_dy)
                        if cb_length_xy > 1e-10:
                            cb_vecxz = (cb_dy / cb_length_xy, -cb_dx / cb_length_xy, 0.0)
                        else:
                            cb_vecxz = (0.0, 0.0, 1.0)
                        
                        # Create 6 sub-elements connecting the 7 nodes
                        for i in range(NUM_SUBDIVISIONS):
                            model.add_element(
                                Element(
                                    tag=coupling_element_tag,
                                    element_type=ElementType.ELASTIC_BEAM,
                                    node_tags=[node_tags[i], node_tags[i + 1]],
                                    material_tag=beam_material_tag,
                                    section_tag=coupling_section_tag,
                                    geometry={
                                        "parent_coupling_beam_id": parent_coupling_beam_id,
                                        "sub_element_index": i,
                                        "vecxz": cb_vecxz,
                                    },
                                )
                            )
                            coupling_element_tag += 1
                        coupling_beams_created += 1
                
                logger.info(
                    f"Generated {coupling_beams_created} coupling beam elements "
                    f"({len(coupling_beams)} beams per floor × {geometry.floors} floors)"
                )

    # Slab elements (ShellMITC4 with ElasticMembranePlateSection)
    slab_section_tag = 5
    slab_element_tags: List[int] = []  # Collect slab element tags for surface loads
    
    if options.include_slabs:
        slab_concrete = ConcreteProperties(fcu=project.materials.fcu_beam)
        slab_section = get_elastic_membrane_plate_section(
            slab_concrete,
            thickness=options.slab_thickness,
            section_tag=slab_section_tag,
        )
        model.add_section(slab_section_tag, slab_section)
        
        # Build existing node lookup for beam/wall node sharing
        existing_nodes: Dict[Tuple[float, float, float], int] = {}
        for node in model.nodes.values():
            existing_nodes[(round(node.x, 6), round(node.y, 6), round(node.z, 6))] = node.tag
        
        slab_generator = SlabMeshGenerator(
            base_node_tag=60000,
            base_element_tag=60000,
        )
        
        # Create opening for core wall if present
        # R3: Extract ONLY the actual internal opening (elevator shaft, stair void),
        # NOT the entire core wall footprint. Slab extends to wall boundary edges.
        slab_openings: List[SlabOpening] = []
        if options.include_core_wall and project.lateral.core_geometry:
            # Get core wall offset for positioning
            outline = _get_core_wall_outline(project.lateral.core_geometry)
            core_offset_x, core_offset_y = _get_core_wall_offset(
                project, outline, options.edge_clearance_m
            )
            
            # Extract only the actual internal opening (not entire wall footprint)
            core_internal_opening = _get_core_opening_for_slab(
                project.lateral.core_geometry,
                core_offset_x,
                core_offset_y,
            )
            
            if core_internal_opening:
                slab_openings.append(core_internal_opening)
                logger.info(
                    f"Slab opening for core: {core_internal_opening.width_x:.2f}m x "
                    f"{core_internal_opening.width_y:.2f}m at ({core_internal_opening.origin[0]:.2f}, "
                    f"{core_internal_opening.origin[1]:.2f})"
                )

        # Create slab panels for each bay on each floor
        for level in range(1, geometry.floors + 1):
            z = level * geometry.story_height
            
            for ix in range(geometry.num_bays_x):
                for iy in range(geometry.num_bays_y):
                    base_origin_x = ix * geometry.bay_x
                    base_origin_y = iy * geometry.bay_y
                    
                    # Determine sub-panels based on secondary beams
                    sub_panels = []
                    
                    # Logic: If secondary beams exist, they split the bay into (N+1) strips
                    if options.num_secondary_beams > 0:
                        if options.secondary_beam_direction == "Y":
                            # Beams run Y-dir, split Y-dimension to run strips along X
                            num_strips = options.num_secondary_beams + 1
                            strip_width = geometry.bay_y / num_strips
                            
                            for k in range(num_strips):
                                sub_panels.append({
                                    "suffix": f"_{k}",
                                    "origin": (base_origin_x, base_origin_y + k * strip_width),
                                    "dims": (geometry.bay_x, strip_width)
                                })
                        else:
                            # Beams run X-dir, split X-dimension to run strips along Y
                            num_strips = options.num_secondary_beams + 1
                            strip_width = geometry.bay_x / num_strips
                            
                            for k in range(num_strips):
                                sub_panels.append({
                                    "suffix": f"_{k}",
                                    "origin": (base_origin_x + k * strip_width, base_origin_y),
                                    "dims": (strip_width, geometry.bay_y)
                                })
                    else:
                        # No secondary beams, single panel per bay
                        sub_panels.append({
                            "suffix": "",
                            "origin": (base_origin_x, base_origin_y),
                            "dims": (geometry.bay_x, geometry.bay_y)
                        })

                    for sp in sub_panels:
                        sp_origin_x, sp_origin_y = sp["origin"]
                        sp_width_x, sp_width_y = sp["dims"]
                        
                        slab = SlabPanel(
                            slab_id=f"S{level}_{ix}_{iy}{sp['suffix']}",
                            origin=(sp_origin_x, sp_origin_y),
                            width_x=sp_width_x,
                            width_y=sp_width_y,
                            thickness=options.slab_thickness,
                            elevation=z,
                            fcu=project.materials.fcu_beam,
                        )

                        beam_div = NUM_SUBDIVISIONS
                        sec_div = options.num_secondary_beams + 1 if options.num_secondary_beams > 0 else 1
                        refinement = max(1, options.slab_elements_per_bay)
                        
                        if options.secondary_beam_direction == "Y":
                            elements_along_x = math.lcm(beam_div, sec_div) if sec_div > 1 else beam_div
                            elements_along_y = beam_div
                        else:
                            elements_along_x = beam_div
                            elements_along_y = math.lcm(beam_div, sec_div) if sec_div > 1 else beam_div
                        
                        elements_along_x *= refinement
                        elements_along_y *= refinement

                        mesh_result = slab_generator.generate_mesh(
                            slab=slab,
                            floor_level=level,
                            section_tag=slab_section_tag,
                            elements_along_x=elements_along_x,
                            elements_along_y=elements_along_y,
                            existing_nodes=existing_nodes,
                            openings=slab_openings
                        )
                        
                        # Add new slab nodes to model and existing_nodes lookup
                        for node_data in mesh_result.nodes:
                            tag, x, y, z_coord, floor_lvl = node_data
                            node = Node(tag=tag, x=x, y=y, z=z_coord)
                            model.add_node(node)
                            existing_nodes[(round(x, 6), round(y, 6), round(z_coord, 6))] = tag
                            
                            # Track in registry for diaphragm
                            if floor_lvl not in registry.nodes_by_floor:
                                registry.nodes_by_floor[floor_lvl] = []
                            registry.nodes_by_floor[floor_lvl].append(tag)
                        
                        # Add slab shell elements and collect tags
                        for elem in mesh_result.elements:
                            model.add_element(
                                Element(
                                    tag=elem.tag,
                                    element_type=ElementType.SHELL_MITC4,
                                    node_tags=list(elem.node_tags),
                                    material_tag=beam_material_tag,
                                    section_tag=elem.section_tag,
                                )
                            )
                            slab_element_tags.append(elem.tag)
                    
        
        # Apply surface loads to all slab elements
        if options.apply_gravity_loads and slab_element_tags:
            _apply_slab_surface_loads(
                model=model,
                project=project,
                slab_element_tags=slab_element_tags,
                dl_pattern=options.dl_load_pattern,
                sdl_pattern=options.sdl_load_pattern,
                ll_pattern=options.ll_load_pattern,
                slab_thickness_m=options.slab_thickness,
            )



    # Phase 2: Load Application (OpenSees BuildingTcl pattern)
    # Apply diaphragms and lateral loads
    master_by_level: Dict[float, int] = {}
    if options.apply_rigid_diaphragms:
        floor_elevations = [level * geometry.story_height for level in range(1, geometry.floors + 1)]
        master_by_level = create_floor_rigid_diaphragms(
            model,
            base_elevation=0.0,
            tolerance=options.tolerance,
            floor_elevations=floor_elevations,
        )

    if options.apply_wind_loads:
        wind_result = project.wind_result
        if wind_result is None:
            import warnings
            warnings.warn(
                "apply_wind_loads=True but project.wind_result is None. "
                "Skipping wind loads. In v3.5, calculate wind loads separately before FEM analysis.",
                UserWarning
            )
        else:
            floor_shears = _compute_floor_shears(wind_result, geometry.story_height, geometry.floors)
            if floor_shears:
                # Wind +X (pattern 4)
                apply_lateral_loads_to_diaphragms(
                    model,
                    floor_shears=floor_shears,
                    direction="X",
                    load_pattern=options.wx_plus_pattern,
                    tolerance=options.tolerance,
                    master_lookup=master_by_level if master_by_level else None,
                )
                logger.info(f"Applied Wx+ loads to {len(floor_shears)} floors (pattern {options.wx_plus_pattern})")
                
                # Wind -X (pattern 5) - negative shears
                apply_lateral_loads_to_diaphragms(
                    model,
                    floor_shears={k: -v for k, v in floor_shears.items()},
                    direction="X",
                    load_pattern=options.wx_minus_pattern,
                    tolerance=options.tolerance,
                    master_lookup=master_by_level if master_by_level else None,
                )
                logger.info(f"Applied Wx- loads to {len(floor_shears)} floors (pattern {options.wx_minus_pattern})")
                
                # Wind +Y (pattern 6)
                apply_lateral_loads_to_diaphragms(
                    model,
                    floor_shears=floor_shears,
                    direction="Y",
                    load_pattern=options.wy_plus_pattern,
                    tolerance=options.tolerance,
                    master_lookup=master_by_level if master_by_level else None,
                )
                logger.info(f"Applied Wy+ loads to {len(floor_shears)} floors (pattern {options.wy_plus_pattern})")
                
                # Wind -Y (pattern 7) - negative shears
                apply_lateral_loads_to_diaphragms(
                    model,
                    floor_shears={k: -v for k, v in floor_shears.items()},
                    direction="Y",
                    load_pattern=options.wy_minus_pattern,
                    tolerance=options.tolerance,
                    master_lookup=master_by_level if master_by_level else None,
                )
                logger.info(f"Applied Wy- loads to {len(floor_shears)} floors (pattern {options.wy_minus_pattern})")

    # Phase 3: Analysis Preparation (OpenSees BuildingTcl pattern)
    # Validate model before returning
    is_valid, errors = model.validate_model()
    if not is_valid:
        for error in errors:
            logger.warning(f"Model validation warning: {error}")

    return model


__all__ = [
    "create_floor_rigid_diaphragms",
    "apply_lateral_loads_to_diaphragms",
    "ModelBuilderOptions",
    "BeamSegment",
    "trim_beam_segment_against_polygon",
    "build_fem_model",
    "FLOOR_NODE_BASE",
    "NodeRegistry",
]
