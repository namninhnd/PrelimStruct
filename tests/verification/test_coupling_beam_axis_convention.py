"""Coupling beam vecxz and axis-convention verification.

Phase 3 checks:
- Coupling beams use coordinate-based vecxz, not hardcoded values.
- X- and Y-spanning coupling beams both produce gravity bending magnitudes
  consistent with hand calculations.
"""

from math import isclose

import pytest

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
from src.fem.builders.beam_builder import BeamBuilder
from src.fem.fem_engine import Element, ElementType, FEMModel, UniformLoad
from src.fem.materials import ConcreteProperties
from src.fem.model_builder import ModelBuilderOptions, NodeRegistry, build_fem_model
from src.fem.solver import FEMSolver

SPAN_M = 1.5
UDL_KN_PER_M = 50.0
UDL_N_PER_M = UDL_KN_PER_M * 1000.0

SECTION_B_M = 0.3
SECTION_H_M = 0.8
E_PA = 30e9
G_PA = E_PA / (2.0 * (1.0 + 0.2))
IZ_M4 = SECTION_B_M * SECTION_H_M**3 / 12.0
IY_M4 = SECTION_H_M * SECTION_B_M**3 / 12.0

EXPECTED_SUPPORT_SHEAR_KN = UDL_KN_PER_M * SPAN_M / 2.0
EXPECTED_MIDSPAN_MOMENT_KNM = UDL_KN_PER_M * SPAN_M**2 / 8.0
EXPECTED_MIDSPAN_DEFLECTION_MM = (
    5.0 * UDL_N_PER_M * SPAN_M**4 / (384.0 * E_PA * IZ_M4) * 1000.0
)


def _skip_if_no_opensees() -> None:
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


def _expected_vecxz(direction: str) -> tuple[float, float, float]:
    if direction == "x":
        return (0.0, -1.0, 0.0)
    if direction == "y":
        return (1.0, 0.0, 0.0)
    raise ValueError(f"Unsupported direction '{direction}'")


def _support_restraints(direction: str) -> list[int]:
    # Pin-pin bending setup with torsion restrained along beam axis for stability.
    if direction == "x":
        return [1, 1, 1, 1, 0, 0]
    if direction == "y":
        return [1, 1, 1, 0, 1, 0]
    raise ValueError(f"Unsupported direction '{direction}'")


def _add_material_and_section(model: FEMModel) -> tuple[int, int]:
    material_tag = 1
    section_tag = 1

    model.add_material(
        material_tag,
        {
            "material_type": "Concrete01",
            "tag": material_tag,
            "fpc": -30e6,
            "epsc0": -0.002,
            "fpcu": -20e6,
            "epsU": -0.0035,
        },
    )

    model.add_section(
        section_tag,
        {
            "section_type": "ElasticBeamSection",
            "tag": section_tag,
            "E": E_PA,
            "A": SECTION_B_M * SECTION_H_M,
            "Iz": IZ_M4,
            "Iy": IY_M4,
            "G": G_PA,
            "J": 0.001,
        },
    )

    return material_tag, section_tag


def _add_coupling_beam(
    model: FEMModel,
    registry: NodeRegistry,
    start_xyz: tuple[float, float, float],
    end_xyz: tuple[float, float, float],
    direction: str,
    parent_id: int,
    start_tag: int,
    material_tag: int,
    section_tag: int,
) -> dict:
    num_subdivisions = 6

    support = _support_restraints(direction)
    start_node = registry.get_or_create(*start_xyz, restraints=support, floor_level=0)
    end_node = registry.get_or_create(*end_xyz, restraints=support, floor_level=0)

    node_tags = [start_node]
    for i in range(1, num_subdivisions):
        t = i / num_subdivisions
        x = start_xyz[0] + t * (end_xyz[0] - start_xyz[0])
        y = start_xyz[1] + t * (end_xyz[1] - start_xyz[1])
        z = start_xyz[2] + t * (end_xyz[2] - start_xyz[2])
        node_tags.append(registry.get_or_create(x, y, z, floor_level=0))
    node_tags.append(end_node)

    vecxz = _expected_vecxz(direction)

    element_tags: list[int] = []
    for i in range(num_subdivisions):
        tag = start_tag + i
        element_tags.append(tag)
        model.add_element(
            Element(
                tag=tag,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[node_tags[i], node_tags[i + 1]],
                material_tag=material_tag,
                section_tag=section_tag,
                geometry={
                    "vecxz": vecxz,
                    "coupling_beam": True,
                    "parent_coupling_beam_id": parent_id,
                    "sub_element_index": i,
                },
            )
        )
        model.add_uniform_load(
            UniformLoad(
                element_tag=tag,
                load_type="Y",
                magnitude=-UDL_N_PER_M,
                load_pattern=1,
            )
        )

    return {
        "start_node": start_node,
        "end_node": end_node,
        "node_tags": node_tags,
        "element_tags": element_tags,
        "vecxz": vecxz,
    }


def _solve_and_extract_case(case: dict, result: object) -> dict:
    start_node = case["start_node"]
    end_node = case["end_node"]

    left_reaction = result.node_reactions[start_node]
    right_reaction = result.node_reactions[end_node]

    left_support_fz_kN = left_reaction[2] / 1000.0
    right_support_fz_kN = right_reaction[2] / 1000.0

    mid_node = case["node_tags"][3]
    mid_disp = result.node_displacements[mid_node]
    mid_uz_mm = abs(mid_disp[2]) * 1000.0
    mid_horizontal_mm = max(abs(mid_disp[0]), abs(mid_disp[1])) * 1000.0

    midspan_moment_kNm = (
        left_support_fz_kN * (SPAN_M / 2.0)
        - UDL_KN_PER_M * (SPAN_M / 2.0) ** 2 / 2.0
    )

    max_horizontal_reaction_kN = max(
        abs(left_reaction[0]),
        abs(left_reaction[1]),
        abs(right_reaction[0]),
        abs(right_reaction[1]),
    ) / 1000.0

    return {
        "left_support_fz_kN": left_support_fz_kN,
        "right_support_fz_kN": right_support_fz_kN,
        "midspan_moment_kNm": midspan_moment_kNm,
        "mid_uz_mm": mid_uz_mm,
        "mid_horizontal_mm": mid_horizontal_mm,
        "max_horizontal_reaction_kN": max_horizontal_reaction_kN,
    }


def _run_single_case(direction: str) -> dict:
    model = FEMModel()
    registry = NodeRegistry(model)
    material_tag, section_tag = _add_material_and_section(model)

    if direction == "x":
        start_xyz = (0.0, 0.0, 0.0)
        end_xyz = (SPAN_M, 0.0, 0.0)
    elif direction == "y":
        start_xyz = (0.0, 0.0, 0.0)
        end_xyz = (0.0, SPAN_M, 0.0)
    else:
        raise ValueError(f"Unsupported direction '{direction}'")

    case = _add_coupling_beam(
        model=model,
        registry=registry,
        start_xyz=start_xyz,
        end_xyz=end_xyz,
        direction=direction,
        parent_id=70000,
        start_tag=1,
        material_tag=material_tag,
        section_tag=section_tag,
    )

    solver = FEMSolver()
    model.build_openseespy_model(ndm=3, ndf=6)
    result = solver.run_linear_static_analysis(load_pattern=1)
    assert result.success, f"Coupling beam analysis failed for {direction}: {result.message}"

    response = _solve_and_extract_case(case, result)
    response["vecxz_values"] = [model.elements[tag].geometry.get("vecxz") for tag in case["element_tags"]]
    response["coupling_flags"] = [model.elements[tag].geometry.get("coupling_beam") for tag in case["element_tags"]]
    return response


def _make_project_for_coupling(config: CoreWallConfig, opening_width: float) -> ProjectData:
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
        size="400x500",
        width=400,
        depth=500,
        dimension=500,
    )
    project.lateral.core_geometry = CoreWallGeometry(
        config=config,
        wall_thickness=500.0,
        length_x=6000.0,
        length_y=6000.0,
        opening_width=opening_width,
        opening_height=2200.0,
        flange_width=2500.0,
        web_length=5000.0,
    )
    return project


@pytest.mark.integration
def test_coupling_beam_x_span_matches_hand_calc() -> None:
    _skip_if_no_opensees()

    case = _run_single_case("x")

    for vecxz in case["vecxz_values"]:
        assert vecxz == pytest.approx(_expected_vecxz("x"), abs=1e-12)
    assert all(flag is True for flag in case["coupling_flags"])

    assert isclose(case["left_support_fz_kN"], EXPECTED_SUPPORT_SHEAR_KN, rel_tol=0.01)
    assert isclose(case["right_support_fz_kN"], EXPECTED_SUPPORT_SHEAR_KN, rel_tol=0.01)
    assert isclose(case["midspan_moment_kNm"], EXPECTED_MIDSPAN_MOMENT_KNM, rel_tol=0.01)
    assert case["midspan_moment_kNm"] > 0.0
    assert isclose(case["mid_uz_mm"], EXPECTED_MIDSPAN_DEFLECTION_MM, rel_tol=0.01)
    assert case["mid_horizontal_mm"] < 1e-6
    assert case["max_horizontal_reaction_kN"] < 1e-6


@pytest.mark.integration
def test_coupling_beam_y_span_matches_hand_calc() -> None:
    _skip_if_no_opensees()

    case = _run_single_case("y")

    for vecxz in case["vecxz_values"]:
        assert vecxz == pytest.approx(_expected_vecxz("y"), abs=1e-12)
    assert all(flag is True for flag in case["coupling_flags"])

    assert isclose(case["left_support_fz_kN"], EXPECTED_SUPPORT_SHEAR_KN, rel_tol=0.01)
    assert isclose(case["right_support_fz_kN"], EXPECTED_SUPPORT_SHEAR_KN, rel_tol=0.01)
    assert isclose(case["midspan_moment_kNm"], EXPECTED_MIDSPAN_MOMENT_KNM, rel_tol=0.01)
    assert case["midspan_moment_kNm"] > 0.0
    assert isclose(case["mid_uz_mm"], EXPECTED_MIDSPAN_DEFLECTION_MM, rel_tol=0.01)
    assert case["mid_horizontal_mm"] < 1e-6
    assert case["max_horizontal_reaction_kN"] < 1e-6


@pytest.mark.integration
def test_coupling_beam_both_orientations_in_same_model() -> None:
    _skip_if_no_opensees()

    model = FEMModel()
    registry = NodeRegistry(model)
    material_tag, section_tag = _add_material_and_section(model)

    x_case = _add_coupling_beam(
        model=model,
        registry=registry,
        start_xyz=(0.0, 0.0, 0.0),
        end_xyz=(SPAN_M, 0.0, 0.0),
        direction="x",
        parent_id=71000,
        start_tag=1,
        material_tag=material_tag,
        section_tag=section_tag,
    )
    y_case = _add_coupling_beam(
        model=model,
        registry=registry,
        start_xyz=(3.0, 0.0, 0.0),
        end_xyz=(3.0, SPAN_M, 0.0),
        direction="y",
        parent_id=72000,
        start_tag=100,
        material_tag=material_tag,
        section_tag=section_tag,
    )

    solver = FEMSolver()
    model.build_openseespy_model(ndm=3, ndf=6)
    result = solver.run_linear_static_analysis(load_pattern=1)
    assert result.success, f"Combined coupling beam analysis failed: {result.message}"

    x_resp = _solve_and_extract_case(x_case, result)
    y_resp = _solve_and_extract_case(y_case, result)

    assert isclose(x_resp["midspan_moment_kNm"], EXPECTED_MIDSPAN_MOMENT_KNM, rel_tol=0.01)
    assert isclose(y_resp["midspan_moment_kNm"], EXPECTED_MIDSPAN_MOMENT_KNM, rel_tol=0.01)
    assert x_resp["midspan_moment_kNm"] > 0.0
    assert y_resp["midspan_moment_kNm"] > 0.0

    x_vecxz_values = [model.elements[tag].geometry.get("vecxz") for tag in x_case["element_tags"]]
    y_vecxz_values = [model.elements[tag].geometry.get("vecxz") for tag in y_case["element_tags"]]
    for vecxz in x_vecxz_values:
        assert vecxz == pytest.approx(_expected_vecxz("x"), abs=1e-12)
    for vecxz in y_vecxz_values:
        assert vecxz == pytest.approx(_expected_vecxz("y"), abs=1e-12)


@pytest.mark.parametrize(
    ("config", "opening_width", "expected_vecxz"),
    [
        (CoreWallConfig.TUBE_WITH_OPENINGS, 1500.0, (0.0, -1.0, 0.0)),
    ],
)
def test_beam_builder_computes_coupling_vecxz_and_preserves_flag(
    config: CoreWallConfig,
    opening_width: float,
    expected_vecxz: tuple[float, float, float],
) -> None:
    project = _make_project_for_coupling(config, opening_width)
    model = FEMModel()
    registry = NodeRegistry(model)
    options = ModelBuilderOptions(
        include_core_wall=True,
        include_slabs=False,
        apply_gravity_loads=False,
        apply_wind_loads=False,
        num_secondary_beams=0,
    )

    builder = BeamBuilder(model, project, registry, options, initial_element_tag=1)
    builder.setup_materials_and_sections(
        ConcreteProperties(fcu=40.0),
        {"primary": (300.0, 600.0), "secondary": (250.0, 500.0)},
    )

    assert project.lateral.core_geometry is not None
    result = builder.create_coupling_beams(
        core_geometry=project.lateral.core_geometry,
        offset_x=0.0,
        offset_y=0.0,
        story_height=project.geometry.story_height,
    )

    assert result.element_tags
    parent_ids = set(result.element_tags)
    coupling_sub_elements = [
        e for e in model.elements.values() if e.geometry.get("parent_beam_id") in parent_ids
    ]
    assert coupling_sub_elements

    for elem in coupling_sub_elements:
        assert elem.geometry.get("coupling_beam") is True
        assert elem.geometry.get("vecxz") == pytest.approx(expected_vecxz, abs=1e-12)


@pytest.mark.parametrize(
    ("config", "opening_width", "expected_vecxz"),
    [
        (CoreWallConfig.TUBE_WITH_OPENINGS, 1500.0, (0.0, -1.0, 0.0)),
    ],
)
def test_model_builder_computes_coupling_vecxz_and_preserves_parent_key(
    config: CoreWallConfig,
    opening_width: float,
    expected_vecxz: tuple[float, float, float],
) -> None:
    project = _make_project_for_coupling(config, opening_width)
    model = build_fem_model(
        project,
        ModelBuilderOptions(
            include_core_wall=True,
            include_slabs=False,
            apply_gravity_loads=False,
            apply_wind_loads=False,
            num_secondary_beams=0,
            omit_columns_near_core=False,
        ),
    )

    coupling_sub_elements = [
        e for e in model.elements.values() if "parent_coupling_beam_id" in e.geometry
    ]
    assert coupling_sub_elements

    for elem in coupling_sub_elements:
        assert "parent_coupling_beam_id" in elem.geometry
        assert elem.geometry.get("vecxz") == pytest.approx(expected_vecxz, abs=1e-12)
