"""
Tests for _extract_column_dims to ensure rectangular column support.

TDD Tests for bug fix: When width=500mm and depth=800mm, FEM model
should use those exact dimensions, NOT override with dimension=800.
"""

import pytest
from src.core.data_models import (
    ColumnResult,
    GeometryInput,
    LoadInput,
    MaterialInput,
    ProjectData,
)
from src.fem.model_builder import _extract_column_dims


@pytest.fixture
def base_project() -> ProjectData:
    """Create minimal ProjectData for testing."""
    return ProjectData(
        geometry=GeometryInput(bay_x=6.0, bay_y=6.0, floors=5),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(),
    )


class TestExtractColumnDims:
    """Test _extract_column_dims() for rectangular column support."""

    def test_explicit_width_depth_not_overridden_by_dimension(self, base_project):
        """When width and depth are explicitly set, dimension should NOT override them.
        
        Bug scenario: User sets width=500, depth=800, dimension=800.
        Expected: Returns (500, 800) - rectangular column.
        Bug behavior: Returns (800, 800) - forced square.
        """
        base_project.column_result = ColumnResult(
            element_type="column",
            size="500x800",
            width=500,
            depth=800,
            dimension=800,  # This is the legacy field
        )
        
        width, depth = _extract_column_dims(base_project)
        
        # CRITICAL: Must return explicit width/depth, NOT dimension
        assert width == 500, f"Width should be 500, got {width}"
        assert depth == 800, f"Depth should be 800, got {depth}"

    def test_dimension_fallback_when_width_depth_not_set(self, base_project):
        """When width/depth are 0, dimension should be used as fallback (backward compat)."""
        base_project.column_result = ColumnResult(
            element_type="column",
            size="600x600",
            width=0,  # Not explicitly set
            depth=0,  # Not explicitly set
            dimension=600,  # Legacy square column
        )
        
        width, depth = _extract_column_dims(base_project)
        
        # Should fall back to dimension for both
        assert width == 600, f"Width should fallback to 600, got {width}"
        assert depth == 600, f"Depth should fallback to 600, got {depth}"

    def test_partial_width_set_depth_from_dimension(self, base_project):
        """When only width is set, depth should use dimension as fallback."""
        base_project.column_result = ColumnResult(
            element_type="column",
            size="500x600",
            width=500,
            depth=0,  # Not set
            dimension=600,
        )
        
        width, depth = _extract_column_dims(base_project)
        
        assert width == 500, f"Width should be explicit 500, got {width}"
        assert depth == 600, f"Depth should fallback to dimension 600, got {depth}"

    def test_partial_depth_set_width_from_dimension(self, base_project):
        """When only depth is set, width should use dimension as fallback."""
        base_project.column_result = ColumnResult(
            element_type="column",
            size="600x800",
            width=0,  # Not set
            depth=800,
            dimension=600,
        )
        
        width, depth = _extract_column_dims(base_project)
        
        assert width == 600, f"Width should fallback to dimension 600, got {width}"
        assert depth == 800, f"Depth should be explicit 800, got {depth}"

    def test_no_column_result_uses_min_size(self, base_project):
        """When no column_result, should return MIN_COLUMN_SIZE for both."""
        base_project.column_result = None
        
        width, depth = _extract_column_dims(base_project)
        
        # MIN_COLUMN_SIZE is 200mm per code
        assert width == 200
        assert depth == 200

    def test_min_size_enforced(self, base_project):
        """Dimensions below MIN_COLUMN_SIZE should be clamped to MIN_COLUMN_SIZE."""
        base_project.column_result = ColumnResult(
            element_type="column",
            size="100x150",
            width=100,  # Below MIN_COLUMN_SIZE
            depth=150,  # Below MIN_COLUMN_SIZE
            dimension=0,
        )
        
        width, depth = _extract_column_dims(base_project)
        
        # Both should be clamped to MIN_COLUMN_SIZE (200mm)
        assert width == 200
        assert depth == 200

    def test_rectangular_column_preserves_aspect_ratio(self, base_project):
        """Real-world test: 400x600 column should stay 400x600."""
        base_project.column_result = ColumnResult(
            element_type="column",
            size="400x600",
            width=400,
            depth=600,
            dimension=600,  # Might be auto-set to max(width, depth)
        )
        
        width, depth = _extract_column_dims(base_project)
        
        assert width == 400
        assert depth == 600
        # Aspect ratio should be preserved
        assert width / depth == pytest.approx(400 / 600)
