"""
Unit tests for slab element module.

Tests for SlabPanel, SlabMeshGenerator, SlabOpening, and ShellMITC4 element creation.
"""

import pytest
import math

from src.fem.slab_element import (
    SlabPanel,
    SlabOpening,
    SlabQuad,
    SlabMeshResult,
    SlabMeshGenerator,
    create_slab_panels_from_bays,
)
from src.fem.fem_engine import FEMModel, Node, Element, ElementType
from src.fem.materials import (
    ConcreteProperties,
    get_elastic_membrane_plate_section,
)


class TestSlabPanel:
    """Tests for SlabPanel dataclass."""

    def test_slab_panel_creation(self):
        """Test basic slab panel creation."""
        slab = SlabPanel(
            slab_id="S1_0_0",
            origin=(0.0, 0.0),
            width_x=8.0,
            width_y=6.0,
            thickness=0.15,
            elevation=3.0,
        )
        assert slab.slab_id == "S1_0_0"
        assert slab.width_x == 8.0
        assert slab.width_y == 6.0
        assert slab.thickness == 0.15
        assert slab.elevation == 3.0

    def test_slab_panel_corners(self):
        """Test corner coordinate calculation."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(2.0, 3.0),
            width_x=4.0,
            width_y=5.0,
            thickness=0.15,
            elevation=6.0,
        )
        corners = slab.corners
        assert len(corners) == 4
        assert corners[0] == (2.0, 3.0, 6.0)      # Bottom-left
        assert corners[1] == (6.0, 3.0, 6.0)      # Bottom-right
        assert corners[2] == (6.0, 8.0, 6.0)      # Top-right
        assert corners[3] == (2.0, 8.0, 6.0)      # Top-left

    def test_slab_panel_area(self):
        """Test area calculation."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(0.0, 0.0),
            width_x=8.0,
            width_y=6.0,
            thickness=0.15,
            elevation=3.0,
        )
        assert slab.area == 48.0

    def test_slab_panel_validation_negative_width(self):
        """Test that negative width raises ValueError."""
        with pytest.raises(ValueError, match="width_x must be positive"):
            SlabPanel(
                slab_id="S1",
                origin=(0.0, 0.0),
                width_x=-1.0,
                width_y=6.0,
                thickness=0.15,
                elevation=3.0,
            )

    def test_slab_panel_validation_negative_thickness(self):
        """Test that negative thickness raises ValueError."""
        with pytest.raises(ValueError, match="thickness must be positive"):
            SlabPanel(
                slab_id="S1",
                origin=(0.0, 0.0),
                width_x=8.0,
                width_y=6.0,
                thickness=0.0,
                elevation=3.0,
            )


class TestSlabQuad:
    """Tests for SlabQuad dataclass."""

    def test_slab_quad_creation(self):
        """Test basic slab quad creation."""
        quad = SlabQuad(
            tag=100,
            node_tags=(1, 2, 3, 4),
            section_tag=10,
            slab_id="S1_0_0",
            floor_level=1,
        )
        assert quad.tag == 100
        assert len(quad.node_tags) == 4

    def test_slab_quad_wrong_node_count(self):
        """Test that wrong node count raises ValueError."""
        with pytest.raises(ValueError, match="exactly 4 node tags"):
            SlabQuad(
                tag=100,
                node_tags=(1, 2, 3),  # Only 3 nodes
                section_tag=10,
                slab_id="S1",
                floor_level=1,
            )


class TestSlabMeshGenerator:
    """Tests for SlabMeshGenerator class."""

    def test_mesh_generation_basic(self):
        """Test basic mesh generation for a simple slab."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(0.0, 0.0),
            width_x=8.0,
            width_y=6.0,
            thickness=0.15,
            elevation=3.0,
        )
        generator = SlabMeshGenerator(base_node_tag=1000, base_element_tag=5000)
        
        result = generator.generate_mesh(
            slab=slab,
            floor_level=1,
            section_tag=10,
            elements_along_x=2,
            elements_along_y=2,
        )
        
        # 3 nodes along X × 3 nodes along Y = 9 nodes
        expected_nodes = 3 * 3
        assert len(result.nodes) == expected_nodes
        
        # 2 elements along X × 2 elements along Y = 4 elements
        expected_elements = 2 * 2
        assert len(result.elements) == expected_elements

    def test_mesh_generation_single_element(self):
        """Test mesh with single element."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(0.0, 0.0),
            width_x=8.0,
            width_y=6.0,
            thickness=0.15,
            elevation=3.0,
        )
        generator = SlabMeshGenerator()
        
        result = generator.generate_mesh(
            slab=slab,
            floor_level=1,
            section_tag=1,
            elements_along_x=1,
            elements_along_y=1,
        )
        
        # 2 nodes along X × 2 nodes along Y = 4 nodes
        assert len(result.nodes) == 4
        # 1 element
        assert len(result.elements) == 1

    def test_mesh_node_coordinates(self):
        """Test that generated node coordinates are correct."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(2.0, 3.0),
            width_x=4.0,
            width_y=6.0,
            thickness=0.15,
            elevation=9.0,
        )
        generator = SlabMeshGenerator(base_node_tag=100)
        
        result = generator.generate_mesh(
            slab=slab,
            floor_level=1,
            section_tag=1,
            elements_along_x=1,
            elements_along_y=1,
        )
        
        # Check first node (bottom-left)
        first_node = result.nodes[0]
        assert abs(first_node[1] - 2.0) < 1e-6  # x = origin[0]
        assert abs(first_node[2] - 3.0) < 1e-6  # y = origin[1]
        assert abs(first_node[3] - 9.0) < 1e-6  # z = elevation

    def test_mesh_boundary_nodes(self):
        """Test that boundary nodes are tracked correctly."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(0.0, 0.0),
            width_x=8.0,
            width_y=6.0,
            thickness=0.15,
            elevation=3.0,
        )
        generator = SlabMeshGenerator()
        
        result = generator.generate_mesh(
            slab=slab,
            floor_level=1,
            section_tag=1,
            elements_along_x=2,
            elements_along_y=2,
        )
        
        # Boundary nodes should be tracked for each edge
        assert 'left' in result.boundary_nodes
        assert 'right' in result.boundary_nodes
        assert 'bottom' in result.boundary_nodes
        assert 'top' in result.boundary_nodes
        
        # Left edge: 3 nodes (num_nodes_y)
        assert len(result.boundary_nodes['left']) == 3

    def test_mesh_existing_nodes(self):
        """Test node sharing with existing beam nodes."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(0.0, 0.0),
            width_x=8.0,
            width_y=6.0,
            thickness=0.15,
            elevation=3.0,
        )
        
        # Pre-existing beam nodes at corners
        existing = {
            (0.0, 0.0, 3.0): 1,
            (8.0, 0.0, 3.0): 2,
            (8.0, 6.0, 3.0): 3,
            (0.0, 6.0, 3.0): 4,
        }
        
        generator = SlabMeshGenerator(base_node_tag=100)
        
        result = generator.generate_mesh(
            slab=slab,
            floor_level=1,
            section_tag=1,
            elements_along_x=1,
            elements_along_y=1,
            existing_nodes=existing,
        )
        
        # No new nodes should be created since all corners exist
        assert len(result.nodes) == 0


class TestCreateSlabPanelsFromBays:
    """Tests for create_slab_panels_from_bays helper function."""

    def test_creates_correct_number_of_panels(self):
        """Test that correct number of panels are created."""
        panels = create_slab_panels_from_bays(
            num_bays_x=2,
            num_bays_y=3,
            bay_x=8.0,
            bay_y=6.0,
            floor_elevations=[3.0, 6.0],
            slab_thickness=0.15,
        )
        
        # 2 * 3 bays * 2 floors = 12 panels
        assert len(panels) == 12

    def test_panel_coordinates(self):
        """Test that panel coordinates are correct."""
        panels = create_slab_panels_from_bays(
            num_bays_x=2,
            num_bays_y=2,
            bay_x=8.0,
            bay_y=6.0,
            floor_elevations=[3.0],
            slab_thickness=0.15,
        )
        
        # First panel (0, 0)
        assert panels[0].origin == (0.0, 0.0)
        assert panels[0].width_x == 8.0
        assert panels[0].width_y == 6.0
        assert panels[0].elevation == 3.0


class TestMaterialsIntegration:
    """Tests for slab shell element material functions."""

    def test_elastic_membrane_plate_section(self):
        """Test ElasticMembranePlateSection creation."""
        concrete = ConcreteProperties(fcu=40.0)
        params = get_elastic_membrane_plate_section(concrete, 0.15, section_tag=100)
        
        assert params['section_type'] == 'ElasticMembranePlateSection'
        assert params['tag'] == 100
        assert params['E'] == concrete.E_Pa
        assert params['nu'] == 0.2
        assert params['h'] == 0.15

    def test_elastic_membrane_plate_section_negative_thickness(self):
        """Test that negative thickness raises ValueError."""
        concrete = ConcreteProperties(fcu=40.0)
        with pytest.raises(ValueError, match="Thickness must be positive"):
            get_elastic_membrane_plate_section(concrete, -0.1, section_tag=100)


class TestFEMModelIntegration:
    """Tests for FEMModel integration with slab shell elements."""

    def test_shell_mitc4_slab_in_model(self):
        """Test adding SHELL_MITC4 slab element to FEMModel."""
        model = FEMModel()
        
        # Create 4 corner nodes (horizontal slab at z=3m)
        model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
        model.add_node(Node(tag=2, x=8.0, y=0.0, z=3.0))
        model.add_node(Node(tag=3, x=8.0, y=6.0, z=3.0))
        model.add_node(Node(tag=4, x=0.0, y=6.0, z=3.0))
        
        # Add ElasticMembranePlateSection
        concrete = ConcreteProperties(fcu=40.0)
        section = get_elastic_membrane_plate_section(concrete, 0.15, section_tag=1)
        model.add_section(1, section)
        
        # Add dummy material (required by Element)
        model.add_material(1, {'material_type': 'dummy', 'tag': 1})
        
        # Add SHELL_MITC4 element
        elem = Element(
            tag=1,
            element_type=ElementType.SHELL_MITC4,
            node_tags=[1, 2, 3, 4],
            material_tag=1,
            section_tag=1,
        )
        model.add_element(elem)
        
        assert len(model.elements) == 1
        assert model.elements[1].element_type == ElementType.SHELL_MITC4

    def test_model_validation_with_slab_elements(self):
        """Test model validation passes with slab elements."""
        model = FEMModel()
        
        # Fixed base nodes (support columns)
        model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1,1,1,1,1,1]))
        model.add_node(Node(tag=2, x=8.0, y=0.0, z=0.0, restraints=[1,1,1,1,1,1]))
        model.add_node(Node(tag=3, x=8.0, y=6.0, z=0.0, restraints=[1,1,1,1,1,1]))
        model.add_node(Node(tag=4, x=0.0, y=6.0, z=0.0, restraints=[1,1,1,1,1,1]))
        
        # Slab nodes at z=3m
        model.add_node(Node(tag=5, x=0.0, y=0.0, z=3.0))
        model.add_node(Node(tag=6, x=8.0, y=0.0, z=3.0))
        model.add_node(Node(tag=7, x=8.0, y=6.0, z=3.0))
        model.add_node(Node(tag=8, x=0.0, y=6.0, z=3.0))
        
        concrete = ConcreteProperties(fcu=40.0)
        section = get_elastic_membrane_plate_section(concrete, 0.15, section_tag=1)
        model.add_section(1, section)
        model.add_material(1, {'material_type': 'dummy', 'tag': 1})
        
        elem = Element(
            tag=1,
            element_type=ElementType.SHELL_MITC4,
            node_tags=[5, 6, 7, 8],
            material_tag=1,
            section_tag=1,
        )
        model.add_element(elem)
        
        is_valid, errors = model.validate_model()
        # Model should be valid or only have minor warnings
        assert is_valid or len([e for e in errors if "no fixed" not in e.lower()]) == 0


class TestSlabOpening:
    """Tests for SlabOpening dataclass."""

    def test_opening_creation(self):
        """Test basic opening creation."""
        opening = SlabOpening(
            opening_id="STAIR1",
            origin=(2.0, 3.0),
            width_x=3.0,
            width_y=4.0,
            opening_type="stair",
        )
        assert opening.opening_id == "STAIR1"
        assert opening.width_x == 3.0
        assert opening.width_y == 4.0
        assert opening.opening_type == "stair"

    def test_opening_bounds(self):
        """Test bounds calculation."""
        opening = SlabOpening(
            opening_id="O1",
            origin=(2.0, 3.0),
            width_x=4.0,
            width_y=5.0,
        )
        bounds = opening.bounds
        assert bounds == (2.0, 3.0, 6.0, 8.0)

    def test_opening_validation_negative_width(self):
        """Test that negative width raises ValueError."""
        with pytest.raises(ValueError, match="width_x must be positive"):
            SlabOpening(
                opening_id="O1",
                origin=(0.0, 0.0),
                width_x=-1.0,
                width_y=2.0,
            )

    def test_opening_overlaps_panel(self):
        """Test opening-panel overlap detection."""
        panel = SlabPanel(
            slab_id="S1",
            origin=(0.0, 0.0),
            width_x=8.0,
            width_y=6.0,
            thickness=0.15,
            elevation=3.0,
        )
        
        # Opening inside panel
        opening_inside = SlabOpening(
            opening_id="O1",
            origin=(2.0, 2.0),
            width_x=2.0,
            width_y=2.0,
        )
        assert opening_inside.overlaps_panel(panel) is True
        
        # Opening outside panel
        opening_outside = SlabOpening(
            opening_id="O2",
            origin=(10.0, 10.0),
            width_x=2.0,
            width_y=2.0,
        )
        assert opening_outside.overlaps_panel(panel) is False
        
        # Opening partially overlapping
        opening_partial = SlabOpening(
            opening_id="O3",
            origin=(7.0, 5.0),
            width_x=3.0,
            width_y=3.0,
        )
        assert opening_partial.overlaps_panel(panel) is True


class TestMeshOpeningExclusion:
    """Tests for opening exclusion in mesh generation."""

    def test_mesh_with_center_opening(self):
        """Test mesh excludes elements overlapping center opening."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(0.0, 0.0),
            width_x=9.0,
            width_y=9.0,
            thickness=0.15,
            elevation=3.0,
        )
        
        # Opening in center of slab (should exclude center element)
        opening = SlabOpening(
            opening_id="STAIR1",
            origin=(3.0, 3.0),
            width_x=3.0,
            width_y=3.0,
        )
        
        generator = SlabMeshGenerator()
        
        # Without opening: 3x3 = 9 elements
        result_no_opening = generator.generate_mesh(
            slab=slab,
            floor_level=1,
            section_tag=1,
            elements_along_x=3,
            elements_along_y=3,
        )
        assert len(result_no_opening.elements) == 9
        
        # With opening: should exclude center element = 8 elements
        generator2 = SlabMeshGenerator()
        result_with_opening = generator2.generate_mesh(
            slab=slab,
            floor_level=1,
            section_tag=1,
            elements_along_x=3,
            elements_along_y=3,
            openings=[opening],
        )
        assert len(result_with_opening.elements) == 8

    def test_mesh_with_corner_opening(self):
        """Test mesh excludes corner elements overlapping opening."""
        slab = SlabPanel(
            slab_id="S1",
            origin=(0.0, 0.0),
            width_x=6.0,
            width_y=6.0,
            thickness=0.15,
            elevation=3.0,
        )
        
        # Opening in bottom-left corner
        opening = SlabOpening(
            opening_id="O1",
            origin=(0.0, 0.0),
            width_x=2.0,
            width_y=2.0,
        )
        
        generator = SlabMeshGenerator()
        
        result = generator.generate_mesh(
            slab=slab,
            floor_level=1,
            section_tag=1,
            elements_along_x=3,
            elements_along_y=3,
            openings=[opening],
        )
        
        # 3x3 = 9 elements, minus 1 corner element = 8
        assert len(result.elements) == 8

