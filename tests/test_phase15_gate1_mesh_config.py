from src.core.data_models import (
    BeamResult,
    ColumnResult,
    CoreWallConfig,
    CoreWallGeometry,
    GeometryInput,
    LateralInput,
    LoadInput,
    MaterialInput,
    ProjectData,
)
from src.fem.fem_engine import ElementType
from src.fem.model_builder import ModelBuilderOptions, build_fem_model
from src.ui.views.fem_views import _get_cache_key


def _make_gate1_project() -> ProjectData:
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=6.0,
            floors=2,
            story_height=3.0,
            num_bays_x=2,
            num_bays_y=2,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            core_wall_config=CoreWallConfig.I_SECTION,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.I_SECTION,
                wall_thickness=500.0,
                flange_width=3000.0,
                web_length=6000.0,
                length_x=3000.0,
                length_y=6000.0,
            ),
            building_width=12.0,
            building_depth=12.0,
        ),
    )

    project.primary_beam_result = BeamResult(
        element_type="Primary Beam",
        size="300x600",
        width=300,
        depth=600,
    )
    project.secondary_beam_result = BeamResult(
        element_type="Secondary Beam",
        size="250x500",
        width=250,
        depth=500,
    )
    project.column_result = ColumnResult(
        element_type="Column",
        size="400",
        dimension=400,
    )
    return project


def test_gate1_default_mesh_options_keep_quad_shells() -> None:
    project = _make_gate1_project()
    options = ModelBuilderOptions(include_core_wall=True, include_slabs=True)

    model = build_fem_model(project, options=options)
    shell_elements = [
        element
        for element in model.elements.values()
        if element.element_type == ElementType.SHELL_MITC4
    ]

    assert options.shell_mesh_type == "quad"
    assert options.shell_mesh_density == "medium"
    assert shell_elements


def test_gate1_cache_key_changes_with_shell_mesh_type() -> None:
    project = _make_gate1_project()
    key_quad = _get_cache_key(project, ModelBuilderOptions(shell_mesh_type="quad"))
    key_tri = _get_cache_key(project, ModelBuilderOptions(shell_mesh_type="tri"))

    assert key_quad != key_tri


def test_gate1_cache_key_changes_with_shell_mesh_density() -> None:
    project = _make_gate1_project()
    key_medium = _get_cache_key(project, ModelBuilderOptions(shell_mesh_density="medium"))
    key_fine = _get_cache_key(project, ModelBuilderOptions(shell_mesh_density="fine"))

    assert key_medium != key_fine
