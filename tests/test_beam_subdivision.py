"""
Test beam element subdivision logic.

This module validates that BeamBuilder._create_beam_element() creates 4 sub-elements
with 3 intermediate nodes for accurate force diagram visualization.
"""

import pytest
from src.core.data_models import GeometryInput, ProjectData, MaterialInput
from src.fem.builders.beam_builder import BeamBuilder
from src.fem.fem_engine import FEMModel, ElementType
from src.fem.model_builder import NodeRegistry, ModelBuilderOptions
from src.fem.materials import ConcreteProperties


@pytest.fixture
def basic_geometry():
    return GeometryInput(
        floors=3,
        story_height=4.0,
        num_bays_x=2,
        num_bays_y=2,
        bay_x=8.0,
        bay_y=6.0,
    )


@pytest.fixture
def basic_materials():
    return MaterialInput(
        fcu_slab=35,
        fcu_beam=40,
        fcu_column=50,
    )


@pytest.fixture
def project(basic_geometry, basic_materials):
    return ProjectData(
        geometry=basic_geometry,
        materials=basic_materials,
    )


@pytest.fixture
def model():
    return FEMModel()


@pytest.fixture
def registry(model):
    return NodeRegistry(model)


@pytest.fixture
def options():
    return ModelBuilderOptions(
        apply_gravity_loads=True,
        trim_beams_at_core=False,
        num_secondary_beams=0,
        secondary_beam_direction="Y",
        tolerance=1e-6,
    )


@pytest.fixture
def beam_builder(model, project, registry, options):
    builder = BeamBuilder(model, project, registry, options, initial_element_tag=1)
    
    concrete = ConcreteProperties(fcu=40.0)
    beam_sizes = {
        "primary": (600.0, 900.0),
        "secondary": (500.0, 700.0),
    }
    builder.setup_materials_and_sections(concrete, beam_sizes)
    
    return builder


def test_beam_creates_4_subelements(beam_builder, registry):
    """Test that beam element subdivision creates 4 sub-elements."""
    # Create start and end nodes
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    initial_element_count = len(beam_builder.model.elements)
    
    # Create beam element (should create 4 sub-elements)
    parent_beam_id = beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    final_element_count = len(beam_builder.model.elements)
    
    # Assert: 4 sub-elements created
    assert final_element_count - initial_element_count == 4, \
        f"Expected 4 sub-elements, got {final_element_count - initial_element_count}"


def test_beam_creates_5_nodes(beam_builder, registry):
    """Test that beam subdivision creates 5 nodes (2 endpoints + 3 intermediate)."""
    # Create start and end nodes
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    initial_node_count = len(beam_builder.model.nodes)
    
    # Create beam element
    beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    final_node_count = len(beam_builder.model.nodes)
    
    # Assert: 3 new intermediate nodes created (start/end already existed)
    assert final_node_count - initial_node_count == 3, \
        f"Expected 3 new nodes, got {final_node_count - initial_node_count}"


def test_subdivision_node_positions(beam_builder, registry):
    """Test that intermediate nodes are positioned at 1/4, 2/4, 3/4."""
    # Create beam from (0,0,4) to (8,0,4) for 8m span
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    # Create beam element
    beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    # Expected x-coordinates at subdivision points (0.0L, 0.25L, 0.5L, 0.75L, 1.0L)
    expected_x_coords = [
        0.0,    # 0/4 (start)
        2.0,    # 1/4
        4.0,    # 2/4
        6.0,    # 3/4
        8.0,    # 4/4 (end)
    ]
    
    # Collect all nodes at z=4.0
    nodes_at_z4 = [node for node in beam_builder.model.nodes.values() if abs(node.z - 4.0) < 1e-6]
    nodes_at_z4_sorted = sorted(nodes_at_z4, key=lambda n: n.x)
    
    # Assert: 5 nodes exist at expected positions
    assert len(nodes_at_z4_sorted) == 5, f"Expected 5 nodes, found {len(nodes_at_z4_sorted)}"
    
    for i, expected_x in enumerate(expected_x_coords):
        actual_x = nodes_at_z4_sorted[i].x
        assert abs(actual_x - expected_x) < 1e-6, \
            f"Node {i}: expected x={expected_x}, got x={actual_x}"


def test_loads_distributed_to_subelements(beam_builder, registry):
    """Test that uniform load is applied to each sub-element."""
    # Create start and end nodes
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    initial_load_count = len(beam_builder.model.uniform_loads)
    
    # Create beam element with loads
    beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    final_load_count = len(beam_builder.model.uniform_loads)
    
    # Assert: 4 uniform loads created (one per sub-element)
    assert final_load_count - initial_load_count == 4, \
        f"Expected 4 uniform loads, got {final_load_count - initial_load_count}"


def test_parent_beam_tracking(beam_builder, registry):
    """Test that geometry metadata tracks parent beam ID."""
    # Create start and end nodes
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    # Create beam element
    parent_beam_id = beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    # Get created elements
    elements = list(beam_builder.model.elements.values())[-4:]  # Last 4 elements
    
    # Assert: All sub-elements track parent beam ID
    for i, elem in enumerate(elements):
        assert "parent_beam_id" in elem.geometry, \
            f"Sub-element {i} missing parent_beam_id in geometry"
        assert elem.geometry["parent_beam_id"] == parent_beam_id, \
            f"Sub-element {i} has wrong parent_beam_id"
        assert elem.geometry["sub_element_index"] == i, \
            f"Sub-element {i} has wrong sub_element_index"


def test_element_connectivity(beam_builder, registry):
    """Test that sub-elements connect sequentially (node[i] to node[i+1])."""
    # Create start and end nodes
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    # Create beam element
    beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    # Get created elements
    elements = list(beam_builder.model.elements.values())[-4:]  # Last 4 elements
    
    # Assert: Each element's end node is next element's start node
    for i in range(3):
        current_elem = elements[i]
        next_elem = elements[i + 1]
        
        assert current_elem.node_tags[1] == next_elem.node_tags[0], \
            f"Element {i} end node does not match element {i+1} start node"


def test_element_type_unchanged(beam_builder, registry):
    """Test that element type remains ELASTIC_BEAM."""
    # Create start and end nodes
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    # Create beam element
    beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    # Get created elements
    elements = list(beam_builder.model.elements.values())[-4:]
    
    # Assert: All sub-elements are ELASTIC_BEAM type
    for i, elem in enumerate(elements):
        assert elem.element_type == ElementType.ELASTIC_BEAM, \
            f"Sub-element {i} has wrong type: {elem.element_type}"


def test_no_loads_when_disabled(model, project, registry):
    """Test that no loads are created when apply_gravity_loads=False."""
    options = ModelBuilderOptions(
        apply_gravity_loads=False,
        trim_beams_at_core=False,
        num_secondary_beams=0,
        secondary_beam_direction="Y",
        tolerance=1e-6,
    )
    
    builder = BeamBuilder(model, project, registry, options, initial_element_tag=1)
    concrete = ConcreteProperties(fcu=40.0)
    beam_sizes = {
        "primary": (600.0, 900.0),
        "secondary": (500.0, 700.0),
    }
    builder.setup_materials_and_sections(concrete, beam_sizes)
    
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    initial_load_count = len(builder.model.uniform_loads)
    
    builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    final_load_count = len(builder.model.uniform_loads)
    
    assert final_load_count == initial_load_count, \
        f"Expected no loads, got {final_load_count - initial_load_count}"


def test_vertical_beam_subdivision(beam_builder, registry):
    """Test subdivision works for vertical beams (columns)."""
    # Create vertical beam from (0,0,0) to (0,0,4)
    start_node = registry.get_or_create(0.0, 0.0, 0.0, floor_level=0)
    end_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    
    # Create beam element
    beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    # Expected z-coordinates at subdivision points (0.0L, 0.25L, 0.5L, 0.75L, 1.0L)
    expected_z_coords = [
        0.0,         # 0/4
        4.0 * 1/4,   # 1/4
        4.0 * 2/4,   # 2/4
        4.0 * 3/4,   # 3/4
        4.0,         # 4/4
    ]
    
    # Collect all nodes at (0,0,z)
    nodes_at_origin = [node for node in beam_builder.model.nodes.values() 
                       if abs(node.x) < 1e-6 and abs(node.y) < 1e-6]
    nodes_sorted = sorted(nodes_at_origin, key=lambda n: n.z)
    
    # Assert: 5 nodes exist at expected elevations
    assert len(nodes_sorted) == 5, f"Expected 5 nodes, found {len(nodes_sorted)}"
    
    for i, expected_z in enumerate(expected_z_coords):
        actual_z = nodes_sorted[i].z
        assert abs(actual_z - expected_z) < 1e-6, \
            f"Node {i}: expected z={expected_z:.3f}, got z={actual_z:.3f}"


def test_element_tag_increment(beam_builder, registry):
    """Test that element_tag increments by 4 after creating subdivided beam."""
    # Create start and end nodes
    start_node = registry.get_or_create(0.0, 0.0, 4.0, floor_level=1)
    end_node = registry.get_or_create(8.0, 0.0, 4.0, floor_level=1)
    
    initial_tag = beam_builder.element_tag
    
    # Create beam element
    beam_builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=beam_builder.primary_section_tag,
        section_dims=(600.0, 900.0),
    )
    
    final_tag = beam_builder.element_tag
    
    # Assert: element_tag incremented by 4
    assert final_tag - initial_tag == 4, \
        f"Expected tag increment of 4, got {final_tag - initial_tag}"
