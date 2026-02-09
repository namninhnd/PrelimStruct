import pytest

from src.core.data_models import (
    BeamResult,
    ColumnResult,
    GeometryInput,
    LateralInput,
    LoadInput,
    MaterialInput,
    ProjectData,
    WindResult,
)
from src.fem.model_builder import ModelBuilderOptions, build_fem_model
from src.fem.solver import analyze_model


def _skip_if_no_opensees() -> None:
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


def _make_wind_project() -> ProjectData:
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=6.0,
            floors=3,
            story_height=3.0,
            num_bays_x=1,
            num_bays_y=1,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(building_width=6.0, building_depth=6.0),
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


def _sum_base_reactions(model, result, index: int) -> float:
    total = 0.0
    for tag, node in model.nodes.items():
        if abs(node.z) < 1e-6 and node.is_fixed and tag in result.node_reactions:
            total += result.node_reactions[tag][index]
    return total / 1000.0


def _mean_top_displacement(model, result, index: int) -> float:
    top_z = max(node.z for node in model.nodes.values())
    top_tags = [tag for tag, node in model.nodes.items() if abs(node.z - top_z) < 1e-6]
    values = [result.node_displacements[tag][index] for tag in top_tags if tag in result.node_displacements]
    if not values:
        return 0.0
    return sum(values) / len(values)


@pytest.mark.integration
def test_wx_equilibrium_and_displacement() -> None:
    _skip_if_no_opensees()

    project = _make_wind_project()
    project.wind_result = WindResult(base_shear=900.0, base_shear_x=900.0, base_shear_y=300.0)

    model = build_fem_model(
        project,
        ModelBuilderOptions(
            include_core_wall=False,
            include_slabs=False,
            apply_gravity_loads=False,
            apply_wind_loads=True,
            apply_rigid_diaphragms=True,
        ),
    )

    result = analyze_model(model, load_cases=["Wx+"])["Wx+"]
    assert result.success, result.message

    reaction_fx = _sum_base_reactions(model, result, 0)
    relative_error = abs(abs(reaction_fx) - project.wind_result.base_shear_x) / project.wind_result.base_shear_x
    assert relative_error <= 0.05

    top_dx = _mean_top_displacement(model, result, 0)
    assert abs(top_dx) > 0.0


@pytest.mark.integration
def test_wy_equilibrium_and_displacement() -> None:
    _skip_if_no_opensees()

    project = _make_wind_project()
    project.wind_result = WindResult(base_shear=900.0, base_shear_x=300.0, base_shear_y=900.0)

    model = build_fem_model(
        project,
        ModelBuilderOptions(
            include_core_wall=False,
            include_slabs=False,
            apply_gravity_loads=False,
            apply_wind_loads=True,
            apply_rigid_diaphragms=True,
        ),
    )

    result = analyze_model(model, load_cases=["Wy+"])["Wy+"]
    assert result.success, result.message

    reaction_fy = _sum_base_reactions(model, result, 1)
    relative_error = abs(abs(reaction_fy) - project.wind_result.base_shear_y) / project.wind_result.base_shear_y
    assert relative_error <= 0.05

    top_dy = _mean_top_displacement(model, result, 1)
    assert abs(top_dy) > 0.0
