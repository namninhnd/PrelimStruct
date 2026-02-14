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
from src.fem.solver import analyze_model
from src.fem.visualization import create_3d_view, create_elevation_view, create_plan_view


def _make_project() -> ProjectData:
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


def test_quad_default_uses_shell_mitc4() -> None:
    model = build_fem_model(_make_project(), options=ModelBuilderOptions())
    quad_shells = [
        element
        for element in model.elements.values()
        if element.element_type == ElementType.SHELL_MITC4
    ]
    tri_shells = [
        element
        for element in model.elements.values()
        if element.element_type == ElementType.SHELL_DKGT
    ]

    assert quad_shells
    assert not tri_shells


def test_tri_toggle_creates_shelldkgt_elements(require_shell_dkgt: str) -> None:
    model = build_fem_model(
        _make_project(),
        options=ModelBuilderOptions(shell_mesh_type="tri"),
    )
    tri_shells = [
        element
        for element in model.elements.values()
        if element.element_type == ElementType.SHELL_DKGT
    ]

    assert tri_shells
    assert all(len(element.node_tags) == 3 for element in tri_shells)


def test_tri_toggle_model_analyzes_successfully(require_shell_dkgt: str) -> None:
    model = build_fem_model(
        _make_project(),
        options=ModelBuilderOptions(shell_mesh_type="tri"),
    )
    results = analyze_model(model, load_cases=["DL"])

    assert "DL" in results
    assert results["DL"].success


def test_tri_toggle_visualization_views_render(require_shell_dkgt: str) -> None:
    model = build_fem_model(
        _make_project(),
        options=ModelBuilderOptions(shell_mesh_type="tri"),
    )

    fig_plan = create_plan_view(model)
    fig_elevation = create_elevation_view(model, view_direction="X")
    fig_3d = create_3d_view(model)

    assert len(fig_plan.data) > 0
    assert len(fig_elevation.data) > 0
    assert len(fig_3d.data) > 0


def test_tri_vs_quad_global_response_parity(require_shell_dkgt: str) -> None:
    quad_model = build_fem_model(_make_project(), options=ModelBuilderOptions(shell_mesh_type="quad"))
    tri_model = build_fem_model(_make_project(), options=ModelBuilderOptions(shell_mesh_type="tri"))

    quad = analyze_model(quad_model, load_cases=["DL"], include_element_forces=False)["DL"]
    tri = analyze_model(tri_model, load_cases=["DL"], include_element_forces=False)["DL"]

    assert quad.success
    assert tri.success

    quad_reaction = abs(quad.get_total_reaction(dof=2))
    tri_reaction = abs(tri.get_total_reaction(dof=2))
    quad_disp = abs(quad.get_max_displacement(dof=2)[1])
    tri_disp = abs(tri.get_max_displacement(dof=2)[1])

    reaction_denominator = max(1.0, quad_reaction)
    displacement_denominator = max(1e-9, quad_disp)

    reaction_delta = abs(tri_reaction - quad_reaction) / reaction_denominator
    displacement_delta = abs(tri_disp - quad_disp) / displacement_denominator

    # Mixed quad/tri discretizations are expected to show larger displacement
    # sensitivity than global reaction equilibrium for the same load case.
    assert reaction_delta <= 0.05
    assert displacement_delta <= 0.30
