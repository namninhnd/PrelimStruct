"""
Unit tests for wall element module.

Tests for WallPanel, WallMeshGenerator, and ShellMITC4 element creation.
"""

import pytest
import math

from src.fem.wall_element import (
    WallPanel,
    ShellQuad,
    WallMeshResult,
    WallMeshGenerator,
    create_wall_rigid_links,
)
from src.fem.fem_engine import FEMModel, Node, Element, ElementType
from src.fem.materials import (
    ConcreteProperties,
    get_plane_stress_material,
    get_plate_fiber_section,
)


class TestWallPanel:
    """Tests for WallPanel dataclass."""

    def test_wall_panel_creation(self):
        """Test basic wall panel creation."""
        wall = WallPanel(
            wall_id="W1",
            base_point=(0.0, 0.0),
            length=6.0,
            thickness=0.3,
            height=30.0,
            orientation=0.0,
        )
        assert wall.wall_id == "W1"
        assert wall.length == 6.0
        assert wall.thickness == 0.3

    def test_wall_panel_end_point_x_direction(self):
        """Test end point calculation for X-direction wall."""
        wall = WallPanel(
            wall_id="W1",
            base_point=(2.0, 3.0),
            length=5.0,
            thickness=0.25,
            height=15.0,
            orientation=0.0,  # Along X-axis
        )
        end = wall.end_point
        assert abs(end[0] - 7.0) < 1e-6  # x = 2.0 + 5.0
        assert abs(end[1] - 3.0) < 1e-6  # y unchanged

    def test_wall_panel_end_point_y_direction(self):
        """Test end point calculation for Y-direction wall."""
        wall = WallPanel(
            wall_id="W2",
            base_point=(1.0, 2.0),
            length=4.0,
            thickness=0.3,
            height=12.0,
            orientation=90.0,  # Along Y-axis
        )
        end = wall.end_point
        assert abs(end[0] - 1.0) < 1e-6  # x unchanged
        assert abs(end[1] - 6.0) < 1e-6  # y = 2.0 + 4.0

    def test_wall_panel_validation_negative_length(self):
        """Test that negative length raises ValueError."""
        with pytest.raises(ValueError, match="length must be positive"):
            WallPanel(
                wall_id="W1",
                base_point=(0.0, 0.0),
                length=-1.0,
                thickness=0.3,
                height=10.0,
            )

    def test_wall_panel_validation_negative_thickness(self):
        """Test that negative thickness raises ValueError."""
        with pytest.raises(ValueError, match="thickness must be positive"):
            WallPanel(
                wall_id="W1",
                base_point=(0.0, 0.0),
                length=5.0,
                thickness=0.0,
                height=10.0,
            )


class TestShellQuad:
    """Tests for ShellQuad dataclass."""

    def test_shell_quad_creation(self):
        """Test basic shell quad creation."""
        quad = ShellQuad(
            tag=100,
            node_tags=(1, 2, 3, 4),
            section_tag=10,
            wall_id="W1",
            floor_level=0,
        )
        assert quad.tag == 100
        assert len(quad.node_tags) == 4

    def test_shell_quad_wrong_node_count(self):
        """Test that wrong node count raises ValueError."""
        with pytest.raises(ValueError, match="exactly 4 node tags"):
            ShellQuad(
                tag=100,
                node_tags=(1, 2, 3),  # Only 3 nodes
                section_tag=10,
                wall_id="W1",
                floor_level=0,
            )


class TestWallMeshGenerator:
    """Tests for WallMeshGenerator class."""

    def test_mesh_generation_basic(self):
        """Test basic mesh generation for a simple wall."""
        wall = WallPanel(
            wall_id="W1",
            base_point=(0.0, 0.0),
            length=6.0,
            thickness=0.3,
            height=9.0,
        )
        generator = WallMeshGenerator(base_node_tag=1000, base_element_tag=5000)
        
        result = generator.generate_mesh(
            wall=wall,
            num_floors=3,
            story_height=3.0,
            section_tag=10,
            elements_along_length=2,
            elements_per_story=2,
        )
        
        # 3 nodes along length × 7 nodes along height (2 elements per story × 3 floors + 1)
        expected_nodes = 3 * 7
        assert len(result.nodes) == expected_nodes
        
        # 2 elements along length × 6 elements along height
        expected_elements = 2 * 6
        assert len(result.elements) == expected_elements

    def test_mesh_generation_single_element_per_story(self):
        """Test mesh with single element per story."""
        wall = WallPanel(
            wall_id="W1",
            base_point=(0.0, 0.0),
            length=4.0,
            thickness=0.25,
            height=6.0,
        )
        generator = WallMeshGenerator()
        
        result = generator.generate_mesh(
            wall=wall,
            num_floors=2,
            story_height=3.0,
            section_tag=1,
            elements_along_length=1,
            elements_per_story=1,
        )
        
        # 2 nodes along length × 3 nodes along height
        assert len(result.nodes) == 2 * 3
        # 1 element along length × 2 elements along height
        assert len(result.elements) == 1 * 2

    def test_mesh_node_coordinates(self):
        """Test that generated node coordinates are correct."""
        wall = WallPanel(
            wall_id="W1",
            base_point=(1.0, 2.0),
            length=4.0,
            thickness=0.3,
            height=6.0,
            orientation=0.0,  # Along X
        )
        generator = WallMeshGenerator(base_node_tag=100)
        
        result = generator.generate_mesh(
            wall=wall,
            num_floors=2,
            story_height=3.0,
            section_tag=1,
            elements_along_length=1,
            elements_per_story=1,
        )
        
        # Check first node (bottom-left)
        first_node = result.nodes[0]
        assert abs(first_node[1] - 1.0) < 1e-6  # x = base_point[0]
        assert abs(first_node[2] - 2.0) < 1e-6  # y = base_point[1]
        assert abs(first_node[3] - 0.0) < 1e-6  # z = 0 (ground level)

    def test_mesh_edge_nodes(self):
        """Test that edge nodes are tracked correctly."""
        wall = WallPanel(
            wall_id="W1",
            base_point=(0.0, 0.0),
            length=4.0,
            thickness=0.3,
            height=6.0,
        )
        generator = WallMeshGenerator()
        
        result = generator.generate_mesh(
            wall=wall,
            num_floors=2,
            story_height=3.0,
            section_tag=1,
            elements_along_length=1,
            elements_per_story=1,
        )
        
        # Edge nodes should be tracked at each floor level
        assert 0 in result.edge_nodes  # Ground level
        assert 1 in result.edge_nodes  # Floor 1
        assert 2 in result.edge_nodes  # Floor 2


class TestMaterialsIntegration:
    """Tests for shell element material functions."""

    def test_plane_stress_material(self):
        """Test PlaneStress NDMaterial creation."""
        concrete = ConcreteProperties(fcu=40.0)
        params = get_plane_stress_material(concrete, material_tag=100)
        
        assert params['material_type'] == 'ElasticIsotropic'
        assert params['tag'] == 100
        assert params['E'] == concrete.E_Pa
        assert params['nu'] == 0.2

    def test_plate_fiber_section(self):
        """Test PlateFiberSection creation."""
        params = get_plate_fiber_section(
            nd_material_tag=100,
            thickness=0.3,
            section_tag=200,
        )
        
        assert params['section_type'] == 'PlateFiber'
        assert params['tag'] == 200
        assert params['matTag'] == 100
        assert params['h'] == 0.3

    def test_plate_fiber_section_negative_thickness(self):
        """Test that negative thickness raises ValueError."""
        with pytest.raises(ValueError, match="Thickness must be positive"):
            get_plate_fiber_section(
                nd_material_tag=100,
                thickness=-0.1,
                section_tag=200,
            )


class TestFEMModelIntegration:
    """Tests for FEMModel integration with shell elements."""

    def test_shell_mitc4_element_in_model(self):
        """Test adding SHELL_MITC4 element to FEMModel."""
        model = FEMModel()
        
        # Create 4 corner nodes
        model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0))
        model.add_node(Node(tag=2, x=1.0, y=0.0, z=0.0))
        model.add_node(Node(tag=3, x=1.0, y=0.0, z=1.0))
        model.add_node(Node(tag=4, x=0.0, y=0.0, z=1.0))
        
        # Add NDMaterial
        concrete = ConcreteProperties(fcu=40.0)
        nd_mat = get_plane_stress_material(concrete, material_tag=1)
        model.add_material(1, nd_mat)
        
        # Add PlateFiberSection
        section = get_plate_fiber_section(nd_material_tag=1, thickness=0.3, section_tag=1)
        model.add_section(1, section)
        
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

    def test_model_validation_with_shell_elements(self):
        """Test model validation passes with shell elements."""
        model = FEMModel()
        
        # Fixed base nodes
        model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1,1,1,1,1,1]))
        model.add_node(Node(tag=2, x=1.0, y=0.0, z=0.0, restraints=[1,1,1,1,1,1]))
        model.add_node(Node(tag=3, x=1.0, y=0.0, z=1.0))
        model.add_node(Node(tag=4, x=0.0, y=0.0, z=1.0))
        
        concrete = ConcreteProperties(fcu=40.0)
        nd_mat = get_plane_stress_material(concrete, material_tag=1)
        model.add_material(1, nd_mat)
        
        section = get_plate_fiber_section(nd_material_tag=1, thickness=0.3, section_tag=1)
        model.add_section(1, section)
        
        elem = Element(
            tag=1,
            element_type=ElementType.SHELL_MITC4,
            node_tags=[1, 2, 3, 4],
            material_tag=1,
            section_tag=1,
        )
        model.add_element(elem)
        
        is_valid, errors = model.validate_model()
        # Model should be valid (has nodes, elements, and supports)
        assert is_valid or len([e for e in errors if "no fixed" not in e.lower()]) == 0
