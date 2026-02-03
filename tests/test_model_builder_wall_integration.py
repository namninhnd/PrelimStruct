"""Integration test for wall mesh generation in model_builder.py"""
import pytest
from src.core.data_models import (
    ProjectData,
    GeometryInput,
    LoadInput,
    MaterialInput,
    LateralInput,
    CoreWallConfig,
    CoreWallGeometry,
)
from src.fem.fem_engine import ElementType
from src.fem.model_builder import build_fem_model, ModelBuilderOptions


def test_wall_mesh_generation_with_i_section():
    """Test that ShellMITC4 wall mesh is generated correctly for I-section core."""
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=8.0,
            bay_y=8.0,
            floors=2,
            story_height=3.6,
            num_bays_x=2,
            num_bays_y=2,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            building_width=16.0,
            building_depth=16.0,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.I_SECTION,
                wall_thickness=500.0,  # mm
                length_x=6000.0,  # mm
                length_y=6000.0,  # mm
                flange_width=2000.0,  # mm
                web_length=6000.0,  # mm - Required for I_SECTION
            ),
        ),
    )
    
    model = build_fem_model(
        project,
        ModelBuilderOptions(
            include_core_wall=True,
            include_slabs=False,
            apply_wind_loads=False,
        ),
    )
    
    # Count ShellMITC4 elements
    shell_elements = [e for e in model.elements.values() if e.element_type == ElementType.SHELL_MITC4]
    
    # I-section: 3 walls (2 flanges + 1 web)
    # Each wall: 2 elements along length × 2 elements per story × 2 stories = 8 elements per wall
    # Total: 3 walls × 8 = 24 shell elements
    expected_shell_count = 3 * 2 * 2 * 2
    assert len(shell_elements) == expected_shell_count, \
        f"Expected {expected_shell_count} shell elements, got {len(shell_elements)}"
    
    # Verify wall material and section tags
    assert all(e.material_tag == 10 for e in shell_elements), \
        "All wall elements should use NDMaterial tag 10"
    assert all(e.section_tag == 10 for e in shell_elements), \
        "All wall elements should use PlateFiberSection tag 10"
    
    # Verify wall nodes are in correct range
    wall_node_tags = set()
    for elem in shell_elements:
        wall_node_tags.update(elem.node_tags)
    
    assert all(50000 <= tag < 60000 for tag in wall_node_tags), \
        "Wall node tags should be in range 50000-59999"
    
    # Verify NDMaterial and PlateFiberSection exist
    assert 10 in model.materials, "NDMaterial with tag 10 should exist"
    assert 10 in model.sections, "PlateFiberSection with tag 10 should exist"
    
    # Verify material type
    wall_material = model.materials[10]
    assert wall_material['material_type'] == 'ElasticIsotropic', \
        "Wall material should be ElasticIsotropic NDMaterial"
    
    # Verify section type
    wall_section = model.sections[10]
    assert wall_section['section_type'] == 'PlateFiber', \
        "Wall section should be PlateFiber"


def test_wall_mesh_generation_with_tube():
    """Test that ShellMITC4 wall mesh is generated correctly for TUBE core."""
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=6.0,
            floors=1,
            story_height=3.0,
            num_bays_x=1,
            num_bays_y=1,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            building_width=6.0,
            building_depth=6.0,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.TUBE_CENTER_OPENING,
                wall_thickness=400.0,  # mm
                length_x=4000.0,  # mm
                length_y=4000.0,  # mm
                opening_width=2000.0,  # mm - Required for TUBE_CENTER_OPENING
                opening_height=2400.0,  # mm - Required for TUBE_CENTER_OPENING
            ),
        ),
    )
    
    model = build_fem_model(
        project,
        ModelBuilderOptions(
            include_core_wall=True,
            include_slabs=False,
            apply_wind_loads=False,
        ),
    )
    
    # Count ShellMITC4 elements
    shell_elements = [e for e in model.elements.values() if e.element_type == ElementType.SHELL_MITC4]
    
    # TUBE: 4 walls
    # Each wall: 2 elements along length × 2 elements per story × 1 story = 4 elements per wall
    # Total: 4 walls × 4 = 16 shell elements
    expected_shell_count = 4 * 2 * 2 * 1
    assert len(shell_elements) == expected_shell_count, \
        f"Expected {expected_shell_count} shell elements for TUBE, got {len(shell_elements)}"


def test_wall_mesh_disabled():
    """Test that wall mesh is not generated when include_core_wall=False."""
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=6.0,
            floors=1,
            story_height=3.0,
            num_bays_x=1,
            num_bays_y=1,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            building_width=6.0,
            building_depth=6.0,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.I_SECTION,
                wall_thickness=500.0,
            ),
        ),
    )
    
    model = build_fem_model(
        project,
        ModelBuilderOptions(
            include_core_wall=False,  # Disable wall mesh
            include_slabs=False,
            apply_wind_loads=False,
        ),
    )
    
    # No shell elements should be created
    shell_elements = [e for e in model.elements.values() if e.element_type == ElementType.SHELL_MITC4]
    assert len(shell_elements) == 0, \
        f"Expected no shell elements with include_core_wall=False, got {len(shell_elements)}"
