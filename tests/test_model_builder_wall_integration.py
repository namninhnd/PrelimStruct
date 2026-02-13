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
    TubeOpeningPlacement,
)
from src.fem.fem_engine import ElementType
from src.fem.model_builder import (
    ModelBuilderOptions,
    _get_core_wall_offset,
    _get_core_wall_outline,
    build_fem_model,
)


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
    
    # Verify wall nodes exist (Phase 14: node tags shifted from 50000+ to registry-based)
    wall_node_tags = set()
    for elem in shell_elements:
        wall_node_tags.update(elem.node_tags)
    
    assert len(wall_node_tags) > 0, "Wall nodes should exist"
    
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
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=400.0,  # mm
                length_x=4000.0,  # mm
                length_y=4000.0,  # mm
                opening_width=2000.0,  # mm - Required for TUBE_WITH_OPENINGS
                opening_height=None,
                opening_placement=TubeOpeningPlacement.TOP_BOT,
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
    
    expected_shell_count = 6 * 2 * 2 * 1
    assert len(shell_elements) == expected_shell_count, \
        f"Expected {expected_shell_count} shell elements for TUBE, got {len(shell_elements)}"


@pytest.mark.parametrize(
    ("opening_placement", "expected_shell_count"),
    [
        (TubeOpeningPlacement.TOP_BOT, 6 * 2 * 2 * 1),
        (TubeOpeningPlacement.NONE, 4 * 2 * 2 * 1),
    ],
)
def test_wall_mesh_generation_respects_tube_opening_placement(
    opening_placement,
    expected_shell_count,
):
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
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=400.0,
                length_x=4000.0,
                length_y=4000.0,
                opening_width=2000.0,
                opening_height=None,
                opening_placement=opening_placement,
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

    shell_elements = [
        e for e in model.elements.values() if e.element_type == ElementType.SHELL_MITC4
    ]
    assert len(shell_elements) == expected_shell_count


@pytest.mark.parametrize(
    ("opening_placement", "expected_beam_count", "expected_y_levels"),
    [
        (TubeOpeningPlacement.TOP_BOT, 2, {0.0, 4.0}),
        (TubeOpeningPlacement.NONE, 0, set()),
    ],
)
def test_runtime_coupling_beam_locations_follow_opening_placement(
    opening_placement,
    expected_beam_count,
    expected_y_levels,
):
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=4.0,
            bay_y=4.0,
            floors=1,
            story_height=3.0,
            num_bays_x=1,
            num_bays_y=1,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            building_width=4.0,
            building_depth=4.0,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=400.0,
                length_x=4000.0,
                length_y=4000.0,
                opening_width=2000.0,
                opening_height=None,
                opening_placement=opening_placement,
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

    coupling_elements = [
        e
        for e in model.elements.values()
        if e.geometry and "parent_coupling_beam_id" in e.geometry
    ]
    if expected_beam_count == 0:
        assert not coupling_elements
        return

    assert coupling_elements

    beams_by_parent = {}
    for element in coupling_elements:
        parent_id = element.geometry["parent_coupling_beam_id"]
        if parent_id not in beams_by_parent:
            beams_by_parent[parent_id] = []
        beams_by_parent[parent_id].append(element)

    assert len(beams_by_parent) == expected_beam_count

    observed_y_levels = set()
    for elements in beams_by_parent.values():
        ordered = sorted(elements, key=lambda item: item.geometry["sub_element_index"])
        start_node = model.nodes[ordered[0].node_tags[0]]
        end_node = model.nodes[ordered[-1].node_tags[1]]
        observed_y_levels.add(round(start_node.y, 6))
        observed_y_levels.add(round(end_node.y, 6))

    assert observed_y_levels == expected_y_levels


def test_tube_both_opening_wall_mesh_stays_within_core_bounds():
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=4.0,
            floors=1,
            story_height=3.0,
            num_bays_x=3,
            num_bays_y=2,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            building_width=18.0,
            building_depth=8.0,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=500.0,
                length_x=3000.0,
                length_y=3000.0,
                opening_width=1000.0,
                opening_height=None,
                opening_placement=TubeOpeningPlacement.TOP_BOT,
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

    core_geometry = project.lateral.core_geometry
    assert core_geometry is not None
    outline = _get_core_wall_outline(core_geometry)
    offset_x, offset_y = _get_core_wall_offset(project, outline, edge_clearance_m=0.2)

    assert core_geometry.length_y is not None
    expected_y_min = offset_y
    expected_y_max = offset_y + (core_geometry.length_y / 1000.0)

    wall_node_tags = set()
    for elem in model.elements.values():
        if elem.element_type == ElementType.SHELL_MITC4 and elem.section_tag == 10:
            wall_node_tags.update(elem.node_tags)

    wall_nodes = [model.nodes[tag] for tag in wall_node_tags]
    ys = [node.y for node in wall_nodes]

    assert ys, "Expected wall nodes for tube core"
    assert min(ys) >= expected_y_min - 1e-6
    assert max(ys) <= expected_y_max + 1e-6


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


def test_wall_nodes_registered_in_node_registry():
    """After create_core_walls with registry, wall nodes should be findable by registry."""
    from src.fem.builders.director import FEMModelDirector
    
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
                wall_thickness=500.0,
                flange_width=3000.0,
                web_length=6000.0,
            ),
        ),
    )
    
    director = FEMModelDirector(
        project,
        ModelBuilderOptions(
            include_core_wall=True,
            include_slabs=False,
            apply_wind_loads=False,
        ),
    )
    
    model = director.build()
    
    assert director.registry is not None
    
    shell_elements = [e for e in model.elements.values() if e.element_type == ElementType.SHELL_MITC4]
    wall_node_tags = set()
    for elem in shell_elements:
        wall_node_tags.update(elem.node_tags)
    
    wall_nodes = [n for n in model.nodes.values() if n.tag in wall_node_tags]
    assert len(wall_nodes) > 0
    
    sample_wall_node = wall_nodes[0]
    found_tag = director.registry.get_existing(
        sample_wall_node.x,
        sample_wall_node.y,
        sample_wall_node.z
    )
    
    assert found_tag == sample_wall_node.tag


def test_i_section_coupling_endpoints_connected_to_wall_nodes():
    """Verify I-section coupling beam endpoint nodes are SHARED with wall mesh nodes.
    
    This is Gate D evidence item E-D2: Endpoint connectivity integration check.
    With Gate B fix, coupling beam endpoints should be found by registry.get_or_create()
    and reuse existing wall nodes instead of creating floating duplicates.
    
    PRODUCTION FIXTURE: I-section does NOT have opening_width in production paths.
    This test must NOT set opening_width to match real usage (app.py:1410, sidebar.py:455).
    """
    from src.fem.builders.director import FEMModelDirector
    
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
                wall_thickness=500.0,
                flange_width=3000.0,
                web_length=6000.0,
                # opening_width deliberately omitted - matches production (app.py:1410)
            ),
        ),
    )
    
    director = FEMModelDirector(
        project,
        ModelBuilderOptions(
            include_core_wall=True,
            include_slabs=False,
            apply_wind_loads=False,
        ),
    )
    
    model = director.build()
    
    assert director.registry is not None
    
    coupling_beams = [
        e for e in model.elements.values()
        if e.geometry.get("coupling_beam", False)
    ]
    
    assert len(coupling_beams) >= 2, \
        f"Expected at least 2 coupling beams for 2-floor I-section, got {len(coupling_beams)}"
    
    shell_elements = [e for e in model.elements.values() if e.element_type == ElementType.SHELL_MITC4]
    wall_node_tags = set()
    for elem in shell_elements:
        wall_node_tags.update(elem.node_tags)
    
    assert len(wall_node_tags) > 0, "Wall nodes should exist"
    
    coupling_beam_groups = {}
    for cb in coupling_beams:
        parent_id = cb.geometry.get("parent_beam_id", cb.tag)
        if parent_id not in coupling_beam_groups:
            coupling_beam_groups[parent_id] = []
        coupling_beam_groups[parent_id].append(cb)
    
    for parent_id, elements in coupling_beam_groups.items():
        elements_sorted = sorted(elements, key=lambda e: e.tag)
        
        first_element = elements_sorted[0]
        last_element = elements_sorted[-1]
        
        start_endpoint = first_element.node_tags[0]
        end_endpoint = last_element.node_tags[-1]
        
        assert start_endpoint in wall_node_tags, \
            f"Coupling beam group {parent_id} start endpoint {start_endpoint} not in wall nodes"
        
        assert end_endpoint in wall_node_tags, \
            f"Coupling beam group {parent_id} end endpoint {end_endpoint} not in wall nodes"
        
        start_node = model.nodes[start_endpoint]
        end_node = model.nodes[end_endpoint]
        
        found_start = director.registry.get_existing(start_node.x, start_node.y, start_node.z)
        found_end = director.registry.get_existing(end_node.x, end_node.y, end_node.z)
        
        assert found_start == start_endpoint, \
            f"Start endpoint {start_endpoint} not registered correctly"
        
        assert found_end == end_endpoint, \
            f"End endpoint {end_endpoint} not registered correctly"


def test_i_section_slab_mesh_excluded_within_coupling_band_bounds():
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=4.0,
            floors=1,
            story_height=3.0,
            num_bays_x=3,
            num_bays_y=3,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            building_width=18.0,
            building_depth=12.0,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.I_SECTION,
                wall_thickness=500.0,
                flange_width=3000.0,
                web_length=3000.0,
            ),
        ),
    )

    model = build_fem_model(
        project,
        ModelBuilderOptions(
            include_core_wall=True,
            include_slabs=True,
            apply_wind_loads=False,
            slab_elements_per_bay=2,
        ),
    )

    core_geometry = project.lateral.core_geometry
    assert core_geometry is not None
    assert core_geometry.flange_width is not None
    assert core_geometry.web_length is not None

    outline = _get_core_wall_outline(core_geometry)
    offset_x, offset_y = _get_core_wall_offset(project, outline, edge_clearance_m=0.2)

    x_min = offset_x
    x_max = offset_x + (core_geometry.flange_width / 1000.0)
    y_min = offset_y
    y_max = offset_y + (core_geometry.web_length / 1000.0)

    slab_elements = [
        elem
        for elem in model.elements.values()
        if elem.element_type == ElementType.SHELL_MITC4 and elem.section_tag == 5
    ]
    assert slab_elements

    eps = 1e-6
    slab_elements_inside_core = []
    for elem in slab_elements:
        nodes = [model.nodes[tag] for tag in elem.node_tags]
        center_x = sum(node.x for node in nodes) / 4.0
        center_y = sum(node.y for node in nodes) / 4.0
        if x_min + eps < center_x < x_max - eps and y_min + eps < center_y < y_max - eps:
            slab_elements_inside_core.append(elem.tag)

    assert not slab_elements_inside_core, (
        f"Found slab elements inside I-section coupling band: {slab_elements_inside_core}"
    )


def test_coupling_beams_receive_dead_load_self_weight_pattern():
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=6.0,
            floors=1,
            story_height=3.0,
            num_bays_x=3,
            num_bays_y=3,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            building_width=18.0,
            building_depth=18.0,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.I_SECTION,
                wall_thickness=500.0,
                flange_width=3000.0,
                web_length=3000.0,
            ),
        ),
    )

    options = ModelBuilderOptions(
        include_core_wall=True,
        include_slabs=False,
        apply_wind_loads=False,
    )
    model = build_fem_model(project, options)

    coupling_element_tags = {
        elem.tag
        for elem in model.elements.values()
        if elem.geometry and "parent_coupling_beam_id" in elem.geometry
    }
    assert coupling_element_tags

    coupling_dl_loads = [
        load
        for load in model.uniform_loads
        if load.element_tag in coupling_element_tags
        and load.load_type == "Gravity"
        and load.load_pattern == options.dl_load_pattern
    ]

    assert len(coupling_dl_loads) == len(coupling_element_tags)
    assert all(load.magnitude > 0.0 for load in coupling_dl_loads)
