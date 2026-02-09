"""
Tests for column subdivision into 4 sub-elements (5 nodes).

This test verifies that columns are subdivided correctly to enable
accurate force diagram visualization for cantilever columns.
"""

import pytest
from src.core.data_models import GeometryInput, MaterialInput, ProjectData
from src.fem.fem_engine import ElementType, FEMModel
from src.fem.builders.column_builder import ColumnBuilder
from src.fem.model_builder import ModelBuilderOptions, NodeRegistry


@pytest.fixture
def simple_geometry():
    """Simple 1-bay geometry for testing."""
    return GeometryInput(
        num_bays_x=1,
        num_bays_y=1,
        bay_x=6.0,
        bay_y=6.0,
        story_height=4.0,
        floors=2,
    )


@pytest.fixture
def basic_materials():
    """Basic material properties."""
    return MaterialInput(
        fcu_slab=40.0,
        fcu_beam=40.0,
        fcu_column=40.0,
    )


@pytest.fixture
def project_data(simple_geometry, basic_materials):
    """ProjectData with simple geometry."""
    return ProjectData(
        geometry=simple_geometry,
        materials=basic_materials,
    )


@pytest.fixture
def model_with_nodes(project_data):
    """FEMModel with grid nodes already created."""
    model = FEMModel()
    registry = NodeRegistry(model)
    options = ModelBuilderOptions()
    
    # Create grid nodes: 2x2 grid, 3 levels (0, 1, 2)
    grid_nodes = {}
    for level in range(3):  # floors + 1
        for ix in range(2):  # num_bays_x + 1
            for iy in range(2):  # num_bays_y + 1
                x = ix * 6.0
                y = iy * 6.0
                z = level * 4.0
                node_tag = registry.get_or_create(x, y, z, floor_level=level)
                grid_nodes[(ix, iy, level)] = node_tag
    
    return model, grid_nodes, registry, options, project_data


def test_column_creates_4_sub_elements(model_with_nodes):
    """Test that each column creates 4 sub-elements."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    next_tag = builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    # 4 columns (2x2 grid) x 2 floors x 4 sub-elements = 32 elements
    expected_elements = 4 * 2 * 4
    assert len(model.elements) == expected_elements
    
    # Element tags should increment by 32
    assert next_tag == 1000 + expected_elements


def test_column_creates_5_nodes(model_with_nodes):
    """Test that each column creates 3 intermediate nodes (5 total including start/end)."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    initial_nodes = len(model.nodes)  # 2x2x3 = 12 grid nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    # Each of 4 columns x 2 floors creates 3 intermediate nodes
    # Total: 12 initial + (4 columns x 2 floors x 3 intermediate) = 12 + 24 = 36
    expected_nodes = 12 + (4 * 2 * 3)
    assert len(model.nodes) == expected_nodes


def test_intermediate_nodes_at_correct_positions(model_with_nodes):
    """Test that intermediate nodes are at 1/4 increments."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    # Check first column (ix=0, iy=0, level=0)
    # Start z=0, end z=4
    # Intermediate at z=1.0, 2.0, 3.0
    intermediate_zs = []
    for node in model.nodes.values():
        z = node.z
        if node.x == 0.0 and node.y == 0.0:
            intermediate_zs.append(z)
    
    intermediate_zs.sort()
    # Expect: 0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0
    expected_zs = [
        0.0, 1.0, 2.0, 3.0, 4.0,
        5.0, 6.0, 7.0, 8.0,
    ]
    intermediate_zs = [round(z, 6) for z in intermediate_zs]
    assert intermediate_zs == expected_zs


def test_parent_column_id_tracking(model_with_nodes):
    """Test that parent_column_id is tracked in geometry metadata."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    # Check first column (4 sub-elements starting at tag 1000)
    first_parent_id = model.elements[1000].geometry.get("parent_column_id")
    assert first_parent_id == 1000
    
    # All 4 sub-elements should have same parent ID
    for i in range(4):
        element = model.elements[1000 + i]
        assert element.geometry.get("parent_column_id") == 1000
        assert element.geometry.get("sub_element_index") == i


def test_sub_element_sequential_connectivity(model_with_nodes):
    """Test that sub-elements connect nodes sequentially."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    # Check first column (4 sub-elements)
    # Should connect sequentially across 5 nodes
    nodes_chain = []
    for i in range(4):
        element = model.elements[1000 + i]
        start, end = element.node_tags
        if i == 0:
            nodes_chain.extend([start, end])
        else:
            # End node of previous should match start of current
            assert start == nodes_chain[-1]
            nodes_chain.append(end)
    
    # Should have 5 unique nodes
    assert len(nodes_chain) == 5


def test_element_type_remains_elastic_beam(model_with_nodes):
    """Test that element type remains ELASTIC_BEAM."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    for element in model.elements.values():
        assert element.element_type == ElementType.ELASTIC_BEAM


def test_vecxz_for_vertical_columns(model_with_nodes):
    """Test that vecxz is (0.0, 1.0, 0.0) for vertical columns."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    for element in model.elements.values():
        vecxz = element.geometry.get("vecxz")
        assert vecxz == (0.0, 1.0, 0.0)


def test_no_uniform_loads_applied_to_columns(model_with_nodes):
    """Test that no uniform loads are applied to column sub-elements."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    # Columns receive point loads from beams, not uniform loads
    assert len(model.uniform_loads) == 0


def test_element_tag_increments_correctly(model_with_nodes):
    """Test that element_tag increments by 4 for each column."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    next_tag = builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=registry,
    )
    
    # 4 columns x 2 floors = 8 columns total
    # Each column creates 4 sub-elements
    # Total elements = 8 x 4 = 32
    # Next tag = 1000 + 32 = 1032
    assert next_tag == 1032


def test_subdivision_without_registry_falls_back(model_with_nodes):
    """Test that subdivision is skipped if registry is None (backward compatibility)."""
    model, grid_nodes, registry, options, project = model_with_nodes
    
    builder = ColumnBuilder(
        model=model,
        project=project,
        options=options,
        initial_element_tag=1000,
    )
    
    # Call without registry
    next_tag = builder.create_columns(
        grid_nodes=grid_nodes,
        column_material_tag=2,
        column_section_tag=3,
        registry=None,  # No subdivision
    )
    
    # Without subdivision: 4 columns x 2 floors = 8 elements (not 32)
    assert len(model.elements) == 8
    assert next_tag == 1008
