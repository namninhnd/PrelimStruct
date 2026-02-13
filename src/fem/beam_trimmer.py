"""
Beam Trimming Module for Core Wall Intersection Handling

This module handles the geometric intersection detection and beam trimming logic
for beams that pass through or terminate at core wall boundaries. This is a critical
requirement for accurate FEM modeling of tall buildings with core wall lateral systems.

Per Hong Kong structural design practice, beams should terminate at the external face
of core walls to avoid geometric conflicts and provide proper load transfer.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional
import math

from src.core.data_models import CoreWallGeometry, CoreWallConfig


class BeamConnectionType(Enum):
    """Connection types for beams at core wall interface.
    
    These connection types define the structural behavior at the beam-wall junction
    and affect the FEM boundary conditions and moment transfer characteristics.
    """
    MOMENT = "moment"      # Full moment connection (rigid joint)
    PINNED = "pinned"      # Pinned connection (shear transfer only)
    FIXED = "fixed"        # Fixed connection (full restraint)


@dataclass
class BeamGeometry:
    """Geometric definition of a beam in plan view.
    
    Attributes:
        start_x: X-coordinate of beam start point (mm)
        start_y: Y-coordinate of beam start point (mm)
        end_x: X-coordinate of beam end point (mm)
        end_y: Y-coordinate of beam end point (mm)
        width: Beam width (mm), default 300mm
        beam_id: Unique identifier for beam tracking
    """
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    width: float = 300.0  # mm
    beam_id: Optional[str] = None
    
    @property
    def length(self) -> float:
        """Calculate beam length in mm."""
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        return math.sqrt(dx**2 + dy**2)
    
    @property
    def is_horizontal(self) -> bool:
        """Check if beam is horizontal (aligned with X-axis)."""
        return abs(self.end_y - self.start_y) < 1.0  # 1mm tolerance
    
    @property
    def is_vertical(self) -> bool:
        """Check if beam is vertical (aligned with Y-axis)."""
        return abs(self.end_x - self.start_x) < 1.0  # 1mm tolerance


@dataclass
class TrimmedBeam:
    """Result of beam trimming operation.
    
    Attributes:
        original_geometry: Original beam geometry before trimming
        trimmed_geometry: New beam geometry after trimming
        start_connection: Connection type at beam start
        end_connection: Connection type at beam end
        trimmed_start: True if start was trimmed
        trimmed_end: True if end was trimmed
        original_length: Original beam length (mm)
        trimmed_length: Trimmed beam length (mm)
        intersection_points: List of (x, y) coordinates where beam intersects core wall
    """
    original_geometry: BeamGeometry
    trimmed_geometry: BeamGeometry
    start_connection: BeamConnectionType = BeamConnectionType.PINNED
    end_connection: BeamConnectionType = BeamConnectionType.PINNED
    trimmed_start: bool = False
    trimmed_end: bool = False
    original_length: float = 0.0
    trimmed_length: float = 0.0
    intersection_points: List[Tuple[float, float]] = field(default_factory=list)
    
    def __post_init__(self):
        self.original_length = self.original_geometry.length
        self.trimmed_length = self.trimmed_geometry.length


class BeamTrimmer:
    """Beam trimming engine for core wall intersection handling.
    
    This class implements geometric intersection detection and beam trimming logic
    for various core wall configurations. Beams are trimmed at the external edges
    of core walls to prevent overlap and ensure proper structural connectivity.
    """
    
    def __init__(self, core_geometry: CoreWallGeometry):
        """Initialize beam trimmer with core wall geometry.
        
        Args:
            core_geometry: CoreWallGeometry defining the core wall configuration
        """
        self.core_geometry = core_geometry
        self.wall_outline = self._generate_wall_outline()
    
    def _generate_wall_outline(self) -> List[Tuple[float, float]]:
        """Generate core wall outline coordinates in plan view.
        
        This creates a polygon representing the external boundary of the core wall
        in plan view. The outline is used for intersection detection with beams.
        
        Returns:
            List of (x, y) coordinate tuples defining the wall outline polygon
        """
        from src.fem.core_wall_geometry import (
            ISectionCoreWall,
            TubeWithOpeningsCoreWall,
        )
        
        config = self.core_geometry.config
        
        if config == CoreWallConfig.I_SECTION:
            generator = ISectionCoreWall(self.core_geometry)
        elif config == CoreWallConfig.TUBE_WITH_OPENINGS:
            # Route to center-opening trimming logic
            generator = TubeWithOpeningsCoreWall(self.core_geometry)
        else:
            raise ValueError(f"Unsupported core wall configuration: {config}")
        
        return generator.get_outline_coordinates()
    
    def detect_intersection(self, beam: BeamGeometry) -> Tuple[bool, List[Tuple[float, float]]]:
        """Detect if beam intersects with core wall outline.
        
        Uses line-segment intersection algorithm to check if the beam centerline
        intersects with any edge of the core wall outline polygon.
        
        Args:
            beam: BeamGeometry to check for intersection
        
        Returns:
            Tuple of (intersects, intersection_points)
            - intersects: True if beam intersects core wall
            - intersection_points: List of (x, y) coordinates where intersections occur
        """
        intersection_points = []
        
        # Beam as line segment
        beam_start = (beam.start_x, beam.start_y)
        beam_end = (beam.end_x, beam.end_y)
        
        # Check intersection with each edge of wall outline
        outline = self.wall_outline
        num_points = len(outline)
        
        for i in range(num_points - 1):
            wall_start = outline[i]
            wall_end = outline[i + 1]
            
            intersection = self._line_segment_intersection(
                beam_start, beam_end,
                wall_start, wall_end
            )
            
            if intersection is not None:
                intersection_points.append(intersection)
        
        return len(intersection_points) > 0, intersection_points
    
    def _line_segment_intersection(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        p4: Tuple[float, float]
    ) -> Optional[Tuple[float, float]]:
        """Calculate intersection point between two line segments.
        
        Uses parametric line segment intersection algorithm.
        Line 1: p1 to p2
        Line 2: p3 to p4
        
        Args:
            p1: Start point of first line segment (x, y)
            p2: End point of first line segment (x, y)
            p3: Start point of second line segment (x, y)
            p4: End point of second line segment (x, y)
        
        Returns:
            Intersection point (x, y) if lines intersect, None otherwise
        """
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        # Calculate direction vectors
        dx1 = x2 - x1
        dy1 = y2 - y1
        dx2 = x4 - x3
        dy2 = y4 - y3
        
        # Calculate determinant
        det = dx1 * dy2 - dy1 * dx2
        
        # Lines are parallel if determinant is zero
        if abs(det) < 1e-10:
            return None
        
        # Calculate parametric coordinates
        t1 = ((x3 - x1) * dy2 - (y3 - y1) * dx2) / det
        t2 = ((x3 - x1) * dy1 - (y3 - y1) * dx1) / det
        
        # Check if intersection occurs within both line segments
        # Use tolerance to handle floating point precision
        tolerance = 1e-6
        if -tolerance <= t1 <= 1.0 + tolerance and -tolerance <= t2 <= 1.0 + tolerance:
            # Calculate intersection point
            x = x1 + t1 * dx1
            y = y1 + t1 * dy1
            return (x, y)
        
        return None
    
    def _point_in_polygon(self, point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """Check if a point is inside a polygon using ray casting algorithm.
        
        Args:
            point: Point coordinates (x, y)
            polygon: List of polygon vertex coordinates
        
        Returns:
            True if point is inside polygon, False otherwise
        """
        x, y = point
        num_vertices = len(polygon)
        inside = False
        
        j = num_vertices - 1
        for i in range(num_vertices):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
    
    def trim_beam(self, beam: BeamGeometry) -> TrimmedBeam:
        """Trim beam at core wall edges to prevent overlap.
        
        This method:
        1. Detects intersections between beam and core wall outline
        2. Calculates new beam endpoints at the core wall external faces
        3. Determines appropriate connection types at trimmed ends
        4. Preserves beam orientation and alignment
        
        Args:
            beam: BeamGeometry to be trimmed
        
        Returns:
            TrimmedBeam with updated geometry and connection information
        """
        # Check for intersection
        intersects, intersection_points = self.detect_intersection(beam)
        
        if not intersects:
            # No intersection, return original beam
            return TrimmedBeam(
                original_geometry=beam,
                trimmed_geometry=beam,
                start_connection=BeamConnectionType.PINNED,
                end_connection=BeamConnectionType.PINNED,
                trimmed_start=False,
                trimmed_end=False,
                intersection_points=[]
            )
        
        # Determine which end(s) to trim
        beam_start = (beam.start_x, beam.start_y)
        beam_end = (beam.end_x, beam.end_y)
        
        start_inside = self._point_in_polygon(beam_start, self.wall_outline)
        end_inside = self._point_in_polygon(beam_end, self.wall_outline)
        
        # Sort intersection points by distance from beam start
        sorted_intersections = sorted(
            intersection_points,
            key=lambda pt: math.sqrt((pt[0] - beam.start_x)**2 + (pt[1] - beam.start_y)**2)
        )
        
        # Determine new beam endpoints
        new_start_x, new_start_y = beam.start_x, beam.start_y
        new_end_x, new_end_y = beam.end_x, beam.end_y
        trimmed_start = False
        trimmed_end = False
        
        if start_inside and len(sorted_intersections) > 0:
            # Beam starts inside core wall, trim start to first intersection
            new_start_x, new_start_y = sorted_intersections[0]
            trimmed_start = True
        
        if end_inside and len(sorted_intersections) > 0:
            # Beam ends inside core wall, trim end to last intersection
            new_end_x, new_end_y = sorted_intersections[-1]
            trimmed_end = True
        
        if not start_inside and not end_inside and len(sorted_intersections) >= 2:
            # Beam passes through core wall, trim both ends
            new_start_x, new_start_y = sorted_intersections[0]
            new_end_x, new_end_y = sorted_intersections[-1]
            trimmed_start = True
            trimmed_end = True
        
        # Create trimmed beam geometry
        trimmed_geometry = BeamGeometry(
            start_x=new_start_x,
            start_y=new_start_y,
            end_x=new_end_x,
            end_y=new_end_y,
            width=beam.width,
            beam_id=beam.beam_id
        )
        
        # Determine connection types
        start_connection = self._determine_connection_type(beam, trimmed_start, is_start=True)
        end_connection = self._determine_connection_type(beam, trimmed_end, is_start=False)
        
        return TrimmedBeam(
            original_geometry=beam,
            trimmed_geometry=trimmed_geometry,
            start_connection=start_connection,
            end_connection=end_connection,
            trimmed_start=trimmed_start,
            trimmed_end=trimmed_end,
            intersection_points=sorted_intersections
        )
    
    def _determine_connection_type(
        self,
        beam: BeamGeometry,
        is_trimmed: bool,
        is_start: bool
    ) -> BeamConnectionType:
        """Determine appropriate connection type at beam end.
        
        Connection type selection criteria:
        - If trimmed at core wall: MOMENT (rigid connection for lateral load transfer)
        - If not trimmed: PINNED (typical gravity frame connection)
        
        Args:
            beam: Original beam geometry
            is_trimmed: True if this end was trimmed
            is_start: True if checking start end, False for end end
        
        Returns:
            Appropriate BeamConnectionType for this end
        """
        if is_trimmed:
            # Trimmed at core wall → moment connection for lateral load transfer
            return BeamConnectionType.MOMENT
        else:
            # Regular connection → pinned (typical for gravity frames)
            return BeamConnectionType.PINNED
    
    def trim_multiple_beams(self, beams: List[BeamGeometry]) -> List[TrimmedBeam]:
        """Trim multiple beams in batch.
        
        Args:
            beams: List of BeamGeometry objects to trim
        
        Returns:
            List of TrimmedBeam results
        """
        return [self.trim_beam(beam) for beam in beams]


def create_beam_from_grid_points(
    grid_x_start: float,
    grid_y_start: float,
    grid_x_end: float,
    grid_y_end: float,
    beam_width: float = 300.0,
    beam_id: Optional[str] = None
) -> BeamGeometry:
    """Convenience function to create beam from grid intersection points.
    
    Args:
        grid_x_start: X-coordinate of start grid line (mm)
        grid_y_start: Y-coordinate of start grid line (mm)
        grid_x_end: X-coordinate of end grid line (mm)
        grid_y_end: Y-coordinate of end grid line (mm)
        beam_width: Beam width (mm), default 300mm
        beam_id: Optional beam identifier
    
    Returns:
        BeamGeometry object representing the beam
    """
    return BeamGeometry(
        start_x=grid_x_start,
        start_y=grid_y_start,
        end_x=grid_x_end,
        end_y=grid_y_end,
        width=beam_width,
        beam_id=beam_id
    )
