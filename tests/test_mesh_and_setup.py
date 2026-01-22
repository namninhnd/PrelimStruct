"""
Unit tests for mesh generation and model setup modules.

Tests cover:
- MeshConfig and mesh density calculations
- Beam and column mesh generation
- Mesh quality validation
- Boundary condition creation
- Support detection
- Load combination generation
"""

import pytest
import math

from src.ai.mesh_generator import (
    MeshDensity,
    ElementType,
    MeshQuality,
    MeshConfig,
    MeshElement,
    Mesh,
    MeshGenerator,
)

from src.ai.auto_setup import (
    SupportType,
    LoadType,
    BoundaryCondition,
    LoadCase,
    ModelSetupConfig,
    ModelSetup,
)


class TestMeshConfig:
    """Tests for MeshConfig class."""

    def test_create_default_config(self):
        """Test creating default mesh config."""
        config = MeshConfig()
        assert config.density == MeshDensity.MEDIUM
        assert config.beam_element_size == 1000.0
        assert config.column_element_size == 3000.0
        assert config.max_aspect_ratio == 10.0

    def test_from_geometry_coarse(self):
        """Test creating config from geometry with coarse density."""
        config = MeshConfig.from_geometry(
            typical_beam_span=9000.0,
            floor_height=3000.0,
            density=MeshDensity.COARSE,
        )
        # Coarse = 4 elements per span (factor 0.25)
        assert config.beam_element_size == 9000.0 * 0.25
        assert config.column_element_size == 3000.0

    def test_from_geometry_fine(self):
        """Test creating config from geometry with fine density."""
        config = MeshConfig.from_geometry(
            typical_beam_span=9000.0,
            floor_height=3000.0,
            density=MeshDensity.FINE,
        )
        # Fine = 16 elements per span (factor 0.0625)
        assert config.beam_element_size == 9000.0 * 0.0625


class TestMeshQuality:
    """Tests for MeshQuality validation."""

    def test_good_quality_mesh(self):
        """Test mesh with good quality metrics."""
        quality = MeshQuality(
            aspect_ratio_max=5.0,
            aspect_ratio_avg=3.0,
            skewness_max=0.5,
            skewness_avg=0.2,
            num_poor_elements=0,
        )
        assert quality.is_valid is True

    def test_poor_aspect_ratio(self):
        """Test mesh with poor aspect ratio."""
        quality = MeshQuality(
            aspect_ratio_max=15.0,  # Exceeds 10
            aspect_ratio_avg=8.0,
            skewness_max=0.5,
            skewness_avg=0.2,
            num_poor_elements=5,
        )
        assert quality.is_valid is False

    def test_poor_skewness(self):
        """Test mesh with poor skewness."""
        quality = MeshQuality(
            aspect_ratio_max=5.0,
            aspect_ratio_avg=3.0,
            skewness_max=0.90,  # Exceeds 0.85
            skewness_avg=0.6,
            num_poor_elements=3,
        )
        assert quality.is_valid is False


class TestMeshGenerator:
    """Tests for MeshGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create mesh generator for testing."""
        config = MeshConfig(
            density=MeshDensity.MEDIUM,
            beam_element_size=1000.0,
            column_element_size=3000.0,
        )
        return MeshGenerator(config)

    def test_generate_beam_mesh(self, generator):
        """Test generating beam mesh."""
        start = (0.0, 0.0, 3000.0)
        end = (9000.0, 0.0, 3000.0)
        section_depth = 600.0
        
        mesh = generator.generate_beam_mesh(start, end, section_depth)
        
        # Should create 9 elements (9000mm / 1000mm)
        assert mesh.num_elements == 9
        assert mesh.num_nodes == 10  # n+1 nodes
        assert mesh.metadata["element_type"] == "beam"
        assert mesh.metadata["length"] == 9000.0

    def test_beam_mesh_quality(self, generator):
        """Test beam mesh quality calculation."""
        start = (0.0, 0.0, 0.0)
        end = (6000.0, 0.0, 0.0)
        section_depth = 600.0
        
        mesh = generator.generate_beam_mesh(start, end, section_depth)
        
        assert mesh.quality is not None
        # Element size = 6000/6 = 1000mm, depth = 600mm, AR = 1.67
        assert mesh.quality.aspect_ratio_max < 2.0
        assert mesh.quality.num_poor_elements == 0

    def test_generate_column_mesh(self, generator):
        """Test generating column mesh."""
        base = (3000.0, 3000.0, 0.0)
        height = 90000.0  # 30 floors * 3000mm
        section_size = 900.0
        
        mesh = generator.generate_column_mesh(base, height, section_size)
        
        # Should create 30 elements (90000mm / 3000mm)
        assert mesh.num_elements == 30
        assert mesh.num_nodes == 31
        assert mesh.metadata["element_type"] == "column"

    def test_column_mesh_nodes(self, generator):
        """Test column mesh node coordinates."""
        base = (1000.0, 2000.0, 0.0)
        height = 6000.0
        section_size = 600.0
        
        mesh = generator.generate_column_mesh(base, height, section_size)
        
        # Check first and last nodes
        assert mesh.nodes[0] == (1000.0, 2000.0, 0.0)
        assert mesh.nodes[-1] == (1000.0, 2000.0, 6000.0)

    def test_refinement_zone_detection(self, generator):
        """Test refinement zone detection."""
        # Add refinement zone at (5000, 5000, 10000) with radius 2000mm
        generator.config.refinement_zones = [(5000.0, 5000.0, 10000.0, 2000.0)]
        
        # Point inside zone
        assert generator.check_refinement_needed((5000.0, 5000.0, 10000.0)) is True
        assert generator.check_refinement_needed((6000.0, 5000.0, 10000.0)) is True
        
        # Point outside zone
        assert generator.check_refinement_needed((10000.0, 10000.0, 10000.0)) is False

    def test_reset_counters(self, generator):
        """Test resetting node and element counters."""
        # Generate first mesh
        mesh1 = generator.generate_beam_mesh((0,0,0), (5000,0,0), 500)
        
        # Reset and generate second mesh
        generator.reset_counters()
        mesh2 = generator.generate_beam_mesh((0,0,0), (5000,0,0), 500)
        
        # Element IDs should start from 0 again
        assert mesh2.elements[0].id == 0


class TestBoundaryCondition:
    """Tests for BoundaryCondition class."""

    def test_create_fixed_support(self):
        """Test creating fixed support."""
        bc = BoundaryCondition.create_fixed(
            node_id=0,
            location=(1000.0, 2000.0, 0.0)
        )
        
        assert bc.support_type == SupportType.FIXED
        assert bc.dof_constraints == [1, 2, 3, 4, 5, 6]
        assert "Fixed" in bc.description

    def test_create_pinned_support(self):
        """Test creating pinned support."""
        bc = BoundaryCondition.create_pinned(
            node_id=1,
            location=(3000.0, 4000.0, 0.0)
        )
        
        assert bc.support_type == SupportType.PINNED
        assert bc.dof_constraints == [1, 2, 3]  # Translations only
        assert "Pinned" in bc.description


class TestModelSetup:
    """Tests for ModelSetup class."""

    @pytest.fixture
    def setup(self):
        """Create model setup for testing."""
        config = ModelSetupConfig(
            base_elevation=0.0,
            support_type_default=SupportType.FIXED,
        )
        return ModelSetup(config)

    def test_detect_column_base_supports(self, setup):
        """Test detecting column base supports."""
        column_locations = [
            (0.0, 0.0),
            (9000.0, 0.0),
            (0.0, 9000.0),
            (9000.0, 9000.0),
        ]
        
        supports = setup.detect_column_base_supports(column_locations)
        
        assert len(supports) == 4
        assert supports[0] == (0.0, 0.0, 0.0)
        assert supports[-1] == (9000.0, 9000.0, 0.0)

    def test_create_boundary_conditions(self, setup):
        """Test creating boundary conditions."""
        locations = [
            (1000.0, 2000.0, 0.0),
            (4000.0, 5000.0, 0.0),
        ]
        
        bcs = setup.create_boundary_conditions(locations)
        
        assert len(bcs) == 2
        assert all(bc.support_type == SupportType.FIXED for bc in bcs)
        assert bcs[0].location == (1000.0, 2000.0, 0.0)

    def test_infer_load_application_points(self, setup):
        """Test inferring load application points."""
        floor_levels = [3000.0, 6000.0, 9000.0]
        column_locations = [(0.0, 0.0), (9000.0, 0.0), (9000.0, 9000.0), (0.0, 9000.0)]
        
        load_points = setup.infer_load_application_points(floor_levels, column_locations)
        
        # Gravity loads at all floor-column intersections
        assert len(load_points["gravity"]) == 3 * 4  # 3 floors * 4 columns
        
        # Lateral loads at floor centroids
        assert len(load_points["lateral"]) == 3

    def test_generate_hk2013_load_combinations(self, setup):
        """Test generating HK Code 2013 load combinations."""
        combinations = setup.generate_hk2013_load_combinations()
        
        assert len(combinations) >= 5  # At least 5 standard combinations
        
        # Check ULS1: 1.4Gk + 1.6Qk
        uls1 = next(c for c in combinations if c["name"] == "ULS1")
        assert uls1["factors"]["dead"] == 1.4
        assert uls1["factors"]["live"] == 1.6
        
        # Check SLS1: 1.0Gk + 1.0Qk
        sls1 = next(c for c in combinations if c["name"] == "SLS1")
        assert sls1["factors"]["dead"] == 1.0
        assert sls1["factors"]["live"] == 1.0

    def test_validate_model_setup_success(self, setup):
        """Test model setup validation with valid setup."""
        locations = [(1000.0, 2000.0, 0.0)]
        setup.create_boundary_conditions(locations)
        
        validation = setup.validate_model_setup()
        
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0
        assert validation["num_supports"] == 1

    def test_validate_model_setup_no_supports(self, setup):
        """Test validation with no supports defined."""
        validation = setup.validate_model_setup()
        
        assert validation["is_valid"] is False
        assert "No boundary conditions" in validation["errors"][0]

    def test_get_setup_summary(self, setup):
        """Test getting setup summary."""
        summary = setup.get_setup_summary()
        
        assert "FEM Model Setup Summary" in summary
        assert "Base Elevation" in summary
        assert "fixed" in summary.lower()
