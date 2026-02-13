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


class TestWallNodeDeduplication:
    """Tests for wall panel node deduplication via NodeRegistry (Gate B, Phase 14)."""

    def _make_registry(self):
        from src.fem.model_builder import NodeRegistry
        return NodeRegistry(FEMModel())

    def test_registry_none_preserves_legacy_behavior(self):
        """registry=None default gives same sequential tags as before."""
        wall = WallPanel("W1", (0.0, 0.0), 4.0, 0.3, 6.0, 0.0)
        gen = WallMeshGenerator(base_node_tag=1000, base_element_tag=5000)
        result = gen.generate_mesh(
            wall=wall, num_floors=2, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=1,
        )
        assert len(result.nodes) == 2 * 3
        tags = [n[0] for n in result.nodes]
        assert tags == list(range(1000, 1006))

    def test_same_coords_same_tag(self):
        """Two walls at identical coordinates yield same tag via registry."""
        registry = self._make_registry()
        wall_a = WallPanel("WA", (0.0, 0.0), 2.0, 0.3, 3.0, 0.0)
        wall_b = WallPanel("WB", (0.0, 0.0), 2.0, 0.3, 3.0, 0.0)
        gen = WallMeshGenerator()
        r_a = gen.generate_mesh(
            wall=wall_a, num_floors=1, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=1,
            registry=registry,
        )
        r_b = gen.generate_mesh(
            wall=wall_b, num_floors=1, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=1,
            registry=registry,
        )
        tags_a = set(n[0] for n in r_a.nodes)
        tags_b = set(n[0] for n in r_b.nodes)
        assert tags_a == tags_b

    def test_junction_node_merging_two_walls_sharing_edge(self):
        """Two collinear walls sharing an endpoint get merged nodes at junction."""
        registry = self._make_registry()
        # Wall A: (0,0)→(2,0), Wall B: (2,0)→(4,0) — share (2,0) at each z
        wall_a = WallPanel("WA", (0.0, 0.0), 2.0, 0.3, 9.0, 0.0)
        wall_b = WallPanel("WB", (2.0, 0.0), 2.0, 0.3, 9.0, 0.0)

        gen = WallMeshGenerator()
        r_a = gen.generate_mesh(
            wall=wall_a, num_floors=3, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=2,
            registry=registry,
        )
        r_b = gen.generate_mesh(
            wall=wall_b, num_floors=3, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=2,
            registry=registry,
        )
        total_raw = len(r_a.nodes) + len(r_b.nodes)
        unique_tags = set(n[0] for n in r_a.nodes) | set(n[0] for n in r_b.nodes)
        num_z_levels = 2 * 3 + 1  # 7
        expected_duplicates = 1 * num_z_levels  # 1 junction per z-level
        assert total_raw - len(unique_tags) == expected_duplicates

    def test_i_section_junction_merging(self):
        """I-section with elements_along_length=2: web midpoints match flange midpoints."""
        registry = self._make_registry()
        offset_x, offset_y = 1.0, 1.0
        length_x_m, length_y_m = 4.0, 6.0
        web_y = offset_y + length_y_m / 2

        iw1 = WallPanel("IW1", (offset_x, offset_y), length_y_m, 0.3, 9.0, 90.0)
        iw2 = WallPanel("IW2", (offset_x + length_x_m, offset_y), length_y_m, 0.3, 9.0, 90.0)
        iw3 = WallPanel("IW3", (offset_x, web_y), length_x_m, 0.3, 9.0, 0.0)

        gen = WallMeshGenerator()
        results = []
        for wall in [iw1, iw2, iw3]:
            results.append(gen.generate_mesh(
                wall=wall, num_floors=3, story_height=3.0,
                section_tag=1, elements_along_length=2, elements_per_story=2,
                registry=registry,
            ))

        total_raw = sum(len(r.nodes) for r in results)
        unique_tags = set()
        for r in results:
            unique_tags.update(n[0] for n in r.nodes)

        num_z_levels = 2 * 3 + 1  # 7
        junctions_per_level = 2  # IW3 start=IW1 mid, IW3 end=IW2 mid
        expected_duplicates = junctions_per_level * num_z_levels  # 14
        assert total_raw - len(unique_tags) == expected_duplicates

    def test_no_value_error_from_double_add(self):
        """Registry path never raises ValueError from FEMModel.add_node duplicate."""
        registry = self._make_registry()
        wall_a = WallPanel("WA", (0.0, 0.0), 2.0, 0.3, 3.0, 0.0)
        wall_b = WallPanel("WB", (0.0, 0.0), 2.0, 0.3, 3.0, 0.0)

        gen = WallMeshGenerator()
        gen.generate_mesh(
            wall=wall_a, num_floors=1, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=1,
            registry=registry,
        )
        gen.generate_mesh(
            wall=wall_b, num_floors=1, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=1,
            registry=registry,
        )

    def test_tube_walls_unaffected(self):
        """Non-overlapping walls produce same node count with or without registry."""
        walls = [
            WallPanel("TW1", (0.0, 0.0), 4.0, 0.3, 6.0, 0.0),
            WallPanel("TW2", (10.0, 0.0), 4.0, 0.3, 6.0, 0.0),
        ]

        gen1 = WallMeshGenerator(base_node_tag=1000)
        no_reg_count = 0
        for w in walls:
            r = gen1.generate_mesh(
                wall=w, num_floors=2, story_height=3.0,
                section_tag=1, elements_along_length=1, elements_per_story=1,
            )
            no_reg_count += len(r.nodes)

        registry = self._make_registry()
        gen2 = WallMeshGenerator()
        with_reg_unique = set()
        for w in walls:
            r = gen2.generate_mesh(
                wall=w, num_floors=2, story_height=3.0,
                section_tag=1, elements_along_length=1, elements_per_story=1,
                registry=registry,
            )
            with_reg_unique.update(n[0] for n in r.nodes)

        assert no_reg_count == len(with_reg_unique)

    def test_ground_nodes_get_fixed_restraints(self):
        """Nodes at z=0 get fixed restraints when created through registry."""
        registry = self._make_registry()
        wall = WallPanel("W1", (0.0, 0.0), 2.0, 0.3, 3.0, 0.0)
        gen = WallMeshGenerator()
        result = gen.generate_mesh(
            wall=wall, num_floors=1, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=1,
            registry=registry,
        )
        for tag, x, y, z, fl in result.nodes:
            node = registry.model.nodes[tag]
            if z == 0.0:
                assert node.restraints == [1, 1, 1, 1, 1, 1]
            else:
                assert node.restraints == [0, 0, 0, 0, 0, 0]

    def test_elements_reference_correct_deduplicated_tags(self):
        """Shell elements reference the merged tag at junction, not the duplicate."""
        registry = self._make_registry()
        wall_a = WallPanel("WA", (0.0, 0.0), 2.0, 0.3, 3.0, 0.0)
        wall_b = WallPanel("WB", (2.0, 0.0), 2.0, 0.3, 3.0, 0.0)

        gen = WallMeshGenerator()
        r_a = gen.generate_mesh(
            wall=wall_a, num_floors=1, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=1,
            registry=registry,
        )
        r_b = gen.generate_mesh(
            wall=wall_b, num_floors=1, story_height=3.0,
            section_tag=1, elements_along_length=1, elements_per_story=1,
            registry=registry,
        )
        # Wall A's right-side tags should equal Wall B's left-side tags at each z
        a_right_tags = set()
        for n in r_a.nodes:
            if abs(n[1] - 2.0) < 1e-6:
                a_right_tags.add(n[0])
        b_left_tags = set()
        for n in r_b.nodes:
            if abs(n[1] - 2.0) < 1e-6:
                b_left_tags.add(n[0])
        assert a_right_tags == b_left_tags
        assert len(a_right_tags) > 0

        # Verify elements in both walls reference these shared tags
        all_elem_tags = set()
        for e in r_a.elements + r_b.elements:
            all_elem_tags.update(e.node_tags)
        assert a_right_tags.issubset(all_elem_tags)
