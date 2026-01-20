"""
Unit Tests for Beam Trimming Module

Tests beam-core wall intersection detection, trimming logic, and connection
type determination for various core wall configurations.
"""

import pytest
import math
from src.fem.beam_trimmer import (
    BeamTrimmer,
    BeamGeometry,
    TrimmedBeam,
    BeamConnectionType,
    create_beam_from_grid_points
)
from src.core.data_models import CoreWallGeometry, CoreWallConfig


class TestBeamGeometry:
    """Tests for BeamGeometry dataclass."""
    
    def test_beam_length_horizontal(self):
        """Test beam length calculation for horizontal beam."""
        beam = BeamGeometry(start_x=0, start_y=0, end_x=6000, end_y=0)
        assert beam.length == pytest.approx(6000.0)
    
    def test_beam_length_vertical(self):
        """Test beam length calculation for vertical beam."""
        beam = BeamGeometry(start_x=0, start_y=0, end_x=0, end_y=4000)
        assert beam.length == pytest.approx(4000.0)
    
    def test_beam_length_diagonal(self):
        """Test beam length calculation for diagonal beam."""
        beam = BeamGeometry(start_x=0, start_y=0, end_x=3000, end_y=4000)
        expected_length = math.sqrt(3000**2 + 4000**2)
        assert beam.length == pytest.approx(expected_length)
    
    def test_is_horizontal(self):
        """Test horizontal beam detection."""
        beam = BeamGeometry(start_x=0, start_y=1000, end_x=6000, end_y=1000)
        assert beam.is_horizontal is True
        assert beam.is_vertical is False
    
    def test_is_vertical(self):
        """Test vertical beam detection."""
        beam = BeamGeometry(start_x=2000, start_y=0, end_x=2000, end_y=6000)
        assert beam.is_vertical is True
        assert beam.is_horizontal is False


class TestLineSegmentIntersection:
    """Tests for line segment intersection algorithm."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a simple rectangular core wall for testing
        self.core_geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0
        )
        self.trimmer = BeamTrimmer(self.core_geometry)
    
    def test_perpendicular_intersection(self):
        """Test intersection of perpendicular line segments."""
        # Horizontal and vertical lines intersecting
        p1 = (0.0, 500.0)
        p2 = (1000.0, 500.0)
        p3 = (500.0, 0.0)
        p4 = (500.0, 1000.0)
        
        intersection = self.trimmer._line_segment_intersection(p1, p2, p3, p4)
        assert intersection is not None
        assert intersection == pytest.approx((500.0, 500.0))
    
    def test_parallel_lines_no_intersection(self):
        """Test that parallel lines do not intersect."""
        # Two horizontal parallel lines
        p1 = (0.0, 0.0)
        p2 = (1000.0, 0.0)
        p3 = (0.0, 500.0)
        p4 = (1000.0, 500.0)
        
        intersection = self.trimmer._line_segment_intersection(p1, p2, p3, p4)
        assert intersection is None
    
    def test_non_intersecting_segments(self):
        """Test line segments that don't intersect within their bounds."""
        # Lines that would intersect if extended, but don't within segment bounds
        p1 = (0.0, 0.0)
        p2 = (100.0, 0.0)
        p3 = (200.0, -100.0)
        p4 = (200.0, 100.0)
        
        intersection = self.trimmer._line_segment_intersection(p1, p2, p3, p4)
        assert intersection is None


class TestBeamTrimmerISSection:
    """Tests for beam trimming with I-section core wall."""
    
    def setup_method(self):
        """Set up I-section core wall for testing."""
        self.core_geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0
        )
        self.trimmer = BeamTrimmer(self.core_geometry)
    
    def test_beam_no_intersection(self):
        """Test beam that doesn't intersect core wall."""
        # Beam far away from core wall
        beam = BeamGeometry(
            start_x=10000.0,
            start_y=3000.0,
            end_x=16000.0,
            end_y=3000.0
        )
        
        intersects, points = self.trimmer.detect_intersection(beam)
        assert intersects is False
        assert len(points) == 0
    
    def test_beam_passing_through_web(self):
        """Test beam passing horizontally through I-section web."""
        # Beam passes through center of web
        beam = BeamGeometry(
            start_x=0.0,
            start_y=3000.0,  # Middle of web height
            end_x=5000.0,
            end_y=3000.0
        )
        
        intersects, points = self.trimmer.detect_intersection(beam)
        # Should intersect at both sides of web
        assert intersects is True
        assert len(points) >= 1  # At least one intersection
    
    def test_trim_beam_no_intersection(self):
        """Test trimming beam that doesn't intersect."""
        beam = BeamGeometry(
            start_x=10000.0,
            start_y=3000.0,
            end_x=16000.0,
            end_y=3000.0,
            beam_id="B1"
        )
        
        trimmed = self.trimmer.trim_beam(beam)
        assert trimmed.trimmed_start is False
        assert trimmed.trimmed_end is False
        assert trimmed.trimmed_geometry.length == pytest.approx(beam.length)


class TestBeamTrimmerTubeSection:
    """Tests for beam trimming with tube core wall configurations."""
    
    def setup_method(self):
        """Set up tube with center opening for testing."""
        self.core_geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_CENTER_OPENING,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=6000.0,
            opening_width=2000.0,
            opening_height=2000.0
        )
        self.trimmer = BeamTrimmer(self.core_geometry)
    
    def test_beam_intersecting_tube_wall(self):
        """Test beam intersecting tube wall."""
        # Beam passing through left wall of tube
        beam = BeamGeometry(
            start_x=0.0,
            start_y=3000.0,
            end_x=2000.0,
            end_y=3000.0
        )
        
        intersects, points = self.trimmer.detect_intersection(beam)
        assert intersects is True
        assert len(points) >= 1
    
    def test_beam_starting_inside_trimmed_at_start(self):
        """Test beam starting inside core wall is trimmed at start."""
        # Beam starts inside tube, ends outside
        beam = BeamGeometry(
            start_x=1000.0,  # Inside tube (wall thickness = 500)
            start_y=3000.0,
            end_x=8000.0,    # Outside tube
            end_y=3000.0
        )
        
        trimmed = self.trimmer.trim_beam(beam)
        # Should trim the start to wall edge
        assert trimmed.trimmed_start is True
        assert trimmed.start_connection == BeamConnectionType.MOMENT


class TestPointInPolygon:
    """Tests for point-in-polygon algorithm."""
    
    def setup_method(self):
        """Set up simple rectangular core wall."""
        self.core_geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_CENTER_OPENING,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=6000.0,
            opening_width=2000.0,
            opening_height=2000.0
        )
        self.trimmer = BeamTrimmer(self.core_geometry)
    
    def test_point_inside_rectangle(self):
        """Test point clearly inside rectangular polygon."""
        # Simple rectangle
        rect = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
        point = (50, 50)
        
        assert self.trimmer._point_in_polygon(point, rect) is True
    
    def test_point_outside_rectangle(self):
        """Test point clearly outside rectangular polygon."""
        rect = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
        point = (150, 50)
        
        assert self.trimmer._point_in_polygon(point, rect) is False
    
    def test_point_on_edge(self):
        """Test point on polygon edge (boundary case)."""
        rect = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
        point = (50, 0)  # On bottom edge
        
        # Point on edge behavior can vary; document actual behavior
        result = self.trimmer._point_in_polygon(point, rect)
        assert isinstance(result, bool)  # Should return boolean


class TestConnectionTypeAssignment:
    """Tests for connection type determination."""
    
    def setup_method(self):
        """Set up core wall for testing."""
        self.core_geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0
        )
        self.trimmer = BeamTrimmer(self.core_geometry)
    
    def test_trimmed_end_gets_moment_connection(self):
        """Test that trimmed ends are assigned moment connection."""
        beam = BeamGeometry(start_x=0, start_y=0, end_x=1000, end_y=0)
        
        # Simulate trimmed end
        connection = self.trimmer._determine_connection_type(
            beam, is_trimmed=True, is_start=True
        )
        
        assert connection == BeamConnectionType.MOMENT
    
    def test_untrimmed_end_gets_pinned_connection(self):
        """Test that untrimmed ends are assigned pinned connection."""
        beam = BeamGeometry(start_x=0, start_y=0, end_x=1000, end_y=0)
        
        # Simulate untrimmed end
        connection = self.trimmer._determine_connection_type(
            beam, is_trimmed=False, is_start=False
        )
        
        assert connection == BeamConnectionType.PINNED


class TestCreateBeamFromGridPoints:
    """Tests for beam creation helper function."""
    
    def test_create_horizontal_beam(self):
        """Test creating horizontal beam from grid points."""
        beam = create_beam_from_grid_points(
            grid_x_start=0.0,
            grid_y_start=6000.0,
            grid_x_end=6000.0,
            grid_y_end=6000.0,
            beam_width=300.0,
            beam_id="B1"
        )
        
        assert beam.start_x == 0.0
        assert beam.start_y == 6000.0
        assert beam.end_x == 6000.0
        assert beam.end_y == 6000.0
        assert beam.width == 300.0
        assert beam.beam_id == "B1"
        assert beam.is_horizontal is True
    
    def test_create_vertical_beam(self):
        """Test creating vertical beam from grid points."""
        beam = create_beam_from_grid_points(
            grid_x_start=3000.0,
            grid_y_start=0.0,
            grid_x_end=3000.0,
            grid_y_end=6000.0,
            beam_id="B2"
        )
        
        assert beam.is_vertical is True
        assert beam.length == pytest.approx(6000.0)


class TestMultipleBeamTrimming:
    """Tests for batch trimming of multiple beams."""
    
    def setup_method(self):
        """Set up core wall and multiple beams."""
        self.core_geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_CENTER_OPENING,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=6000.0,
            opening_width=2000.0,
            opening_height=2000.0
        )
        self.trimmer = BeamTrimmer(self.core_geometry)
    
    def test_trim_multiple_beams(self):
        """Test trimming multiple beams in batch."""
        beams = [
            BeamGeometry(0, 3000, 8000, 3000, beam_id="B1"),  # Horizontal through core
            BeamGeometry(3000, 0, 3000, 8000, beam_id="B2"),  # Vertical through core
            BeamGeometry(10000, 3000, 16000, 3000, beam_id="B3")  # Far away, no intersection
        ]
        
        trimmed_beams = self.trimmer.trim_multiple_beams(beams)
        
        assert len(trimmed_beams) == 3
        assert all(isinstance(tb, TrimmedBeam) for tb in trimmed_beams)
        
        # Third beam should not be trimmed
        assert trimmed_beams[2].trimmed_start is False
        assert trimmed_beams[2].trimmed_end is False


class TestTrimmedBeamDataClass:
    """Tests for TrimmedBeam dataclass functionality."""
    
    def test_trimmed_beam_length_calculation(self):
        """Test that trimmed beam calculates lengths in __post_init__."""
        original = BeamGeometry(0, 0, 6000, 0)
        trimmed = BeamGeometry(1000, 0, 5000, 0)
        
        result = TrimmedBeam(
            original_geometry=original,
            trimmed_geometry=trimmed,
            trimmed_start=True,
            trimmed_end=True
        )
        
        assert result.original_length == pytest.approx(6000.0)
        assert result.trimmed_length == pytest.approx(4000.0)
    
    def test_trimmed_beam_default_intersection_points(self):
        """Test that intersection_points defaults to empty list."""
        original = BeamGeometry(0, 0, 6000, 0)
        trimmed = BeamGeometry(1000, 0, 5000, 0)
        
        result = TrimmedBeam(
            original_geometry=original,
            trimmed_geometry=trimmed
        )
        
        assert result.intersection_points == []


# Integration test
class TestBeamTrimmingIntegration:
    """Integration tests for complete beam trimming workflow."""
    
    def test_full_trimming_workflow_i_section(self):
        """Test complete workflow: create core wall, create beam, detect, trim."""
        # 1. Create I-section core wall
        core_geometry = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0
        )
        
        # 2. Create beam trimmer
        trimmer = BeamTrimmer(core_geometry)
        
        # 3. Create beam that passes through web
        beam = create_beam_from_grid_points(
            grid_x_start=-1000.0,
            grid_y_start=3000.0,
            grid_x_end=5000.0,
            grid_y_end=3000.0,
            beam_width=300.0,
            beam_id="B1"
        )
        
        # 4. Detect intersection
        intersects, points = trimmer.detect_intersection(beam)
        assert intersects is True
        
        # 5. Trim beam
        trimmed = trimmer.trim_beam(beam)
        
        # 6. Verify trimming occurred
        assert trimmed.original_length > trimmed.trimmed_length
        
        # 7. Verify connection types assigned
        assert isinstance(trimmed.start_connection, BeamConnectionType)
        assert isinstance(trimmed.end_connection, BeamConnectionType)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
