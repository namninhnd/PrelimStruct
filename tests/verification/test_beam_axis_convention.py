"""Beam axis-convention verification with hand-calculation checks.

Phase 1 intent:
- Ensure beam vecxz follows beam plan direction
- Ensure local y aligns with global vertical for horizontal beams
- Validate simply-supported beam hand-calcs (V = wL/2, M = wL^2/8, deflection)
"""

from math import isclose

import pytest

from src.core.data_models import GeometryInput, MaterialInput, ProjectData
from src.fem.builders.beam_builder import BeamBuilder
from src.fem.fem_engine import ElementType, FEMModel, UniformLoad
from src.fem.materials import ConcreteProperties
from src.fem.model_builder import ModelBuilderOptions, NodeRegistry, _create_subdivided_beam
from src.fem.solver import FEMSolver

SPAN_M = 6.0
UDL_KN_PER_M = 10.0
UDL_N_PER_M = UDL_KN_PER_M * 1000.0

SECTION_B_M = 0.3
SECTION_H_M = 0.5
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
    raise ValueError(f"Unsupported beam direction '{direction}'")


def _support_restraints(direction: str) -> list[int]:
    # Pin-pin for bending, with beam-axis torsion restrained for stability.
    if direction == "x":
        return [1, 1, 1, 1, 0, 0]
    if direction == "y":
        return [1, 1, 1, 0, 1, 0]
    raise ValueError(f"Unsupported beam direction '{direction}'")


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


def _build_subdivided_beam_model(direction: str) -> tuple[FEMModel, int, int, list[int]]:
    model = FEMModel()
    registry = NodeRegistry(model)

    if direction == "x":
        start_xyz = (0.0, 0.0, 0.0)
        end_xyz = (SPAN_M, 0.0, 0.0)
    elif direction == "y":
        start_xyz = (0.0, 0.0, 0.0)
        end_xyz = (0.0, SPAN_M, 0.0)
    else:
        raise ValueError(f"Unsupported beam direction '{direction}'")

    support = _support_restraints(direction)
    start_node = registry.get_or_create(*start_xyz, restraints=support, floor_level=0)
    end_node = registry.get_or_create(*end_xyz, restraints=support, floor_level=0)

    material_tag, section_tag = _add_material_and_section(model)

    _, parent_beam_id = _create_subdivided_beam(
        model=model,
        registry=registry,
        start_node=start_node,
        end_node=end_node,
        section_tag=section_tag,
        material_tag=material_tag,
        floor_level=0,
        element_tag=1,
        element_type=ElementType.ELASTIC_BEAM,
    )

    sub_element_tags = sorted(
        [
            elem_tag
            for elem_tag, elem in model.elements.items()
            if elem.geometry.get("parent_beam_id") == parent_beam_id
        ],
        key=lambda tag: model.elements[tag].geometry.get("sub_element_index", 0),
    )

    for elem_tag in sub_element_tags:
        model.add_uniform_load(
            UniformLoad(
                element_tag=elem_tag,
                load_type="Y",
                magnitude=-UDL_N_PER_M,
                load_pattern=1,
            )
        )

    return model, start_node, end_node, sub_element_tags


def _run_beam_case(direction: str) -> dict:
    model, start_node, end_node, sub_element_tags = _build_subdivided_beam_model(direction)

    solver = FEMSolver()
    model.build_openseespy_model(ndm=3, ndf=6)
    result = solver.run_linear_static_analysis(load_pattern=1)

    assert result.success, f"Analysis failed for {direction}-beam: {result.message}"

    left_reaction = result.node_reactions[start_node]
    right_reaction = result.node_reactions[end_node]

    left_support_fz_kN = left_reaction[2] / 1000.0
    right_support_fz_kN = right_reaction[2] / 1000.0

    mid_node = model.elements[sub_element_tags[1]].node_tags[1]
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

    vecxz_values = [
        model.elements[tag].geometry.get("vecxz") for tag in sub_element_tags
    ]

    return {
        "left_support_fz_kN": left_support_fz_kN,
        "right_support_fz_kN": right_support_fz_kN,
        "midspan_moment_kNm": midspan_moment_kNm,
        "mid_uz_mm": mid_uz_mm,
        "mid_horizontal_mm": mid_horizontal_mm,
        "max_horizontal_reaction_kN": max_horizontal_reaction_kN,
        "vecxz_values": vecxz_values,
    }


@pytest.mark.parametrize(
    ("direction", "start_xyz", "end_xyz"),
    [
        ("x", (0.0, 0.0, 4.0), (SPAN_M, 0.0, 4.0)),
        ("y", (0.0, 0.0, 4.0), (0.0, SPAN_M, 4.0)),
    ],
)
def test_beam_builder_computes_vecxz_from_beam_direction(
    direction: str,
    start_xyz: tuple[float, float, float],
    end_xyz: tuple[float, float, float],
) -> None:
    model = FEMModel()
    registry = NodeRegistry(model)
    project = ProjectData(
        geometry=GeometryInput(bay_x=6.0, bay_y=6.0, floors=1, story_height=4.0),
        materials=MaterialInput(fcu_slab=40, fcu_beam=40, fcu_column=40),
    )
    options = ModelBuilderOptions(
        apply_gravity_loads=False,
        trim_beams_at_core=False,
        num_secondary_beams=0,
    )

    builder = BeamBuilder(model, project, registry, options, initial_element_tag=1)
    builder.setup_materials_and_sections(
        ConcreteProperties(fcu=40.0),
        {"primary": (300.0, 500.0), "secondary": (250.0, 450.0)},
    )

    start_node = registry.get_or_create(*start_xyz, floor_level=1)
    end_node = registry.get_or_create(*end_xyz, floor_level=1)
    assert builder.primary_section_tag is not None

    parent_beam_id = builder._create_beam_element(
        start_node=start_node,
        end_node=end_node,
        section_tag=builder.primary_section_tag,
        section_dims=(300.0, 500.0),
    )

    sub_elements = [
        elem
        for elem in model.elements.values()
        if elem.geometry.get("parent_beam_id") == parent_beam_id
    ]

    assert len(sub_elements) == 4
    expected_vecxz = _expected_vecxz(direction)
    for elem in sub_elements:
        assert elem.geometry.get("vecxz") == pytest.approx(expected_vecxz, abs=1e-12)


@pytest.mark.integration
def test_beam_axis_convention_x_direction_matches_hand_calc() -> None:
    _skip_if_no_opensees()

    case = _run_beam_case("x")

    for vecxz in case["vecxz_values"]:
        assert vecxz == pytest.approx(_expected_vecxz("x"), abs=1e-12)

    assert isclose(case["left_support_fz_kN"], EXPECTED_SUPPORT_SHEAR_KN, rel_tol=0.01)
    assert isclose(case["right_support_fz_kN"], EXPECTED_SUPPORT_SHEAR_KN, rel_tol=0.01)
    assert isclose(case["midspan_moment_kNm"], EXPECTED_MIDSPAN_MOMENT_KNM, rel_tol=0.01)
    assert case["midspan_moment_kNm"] > 0.0

    assert isclose(case["mid_uz_mm"], EXPECTED_MIDSPAN_DEFLECTION_MM, rel_tol=0.01)
    assert case["mid_horizontal_mm"] < 1e-6
    assert case["max_horizontal_reaction_kN"] < 1e-6


@pytest.mark.integration
def test_beam_axis_convention_y_direction_matches_x_direction() -> None:
    _skip_if_no_opensees()

    case_x = _run_beam_case("x")
    case_y = _run_beam_case("y")

    for vecxz in case_y["vecxz_values"]:
        assert vecxz == pytest.approx(_expected_vecxz("y"), abs=1e-12)

    assert isclose(case_y["left_support_fz_kN"], EXPECTED_SUPPORT_SHEAR_KN, rel_tol=0.01)
    assert isclose(case_y["right_support_fz_kN"], EXPECTED_SUPPORT_SHEAR_KN, rel_tol=0.01)
    assert isclose(case_y["midspan_moment_kNm"], EXPECTED_MIDSPAN_MOMENT_KNM, rel_tol=0.01)
    assert case_y["midspan_moment_kNm"] > 0.0

    assert isclose(case_y["mid_uz_mm"], EXPECTED_MIDSPAN_DEFLECTION_MM, rel_tol=0.01)
    assert case_y["mid_horizontal_mm"] < 1e-6
    assert case_y["max_horizontal_reaction_kN"] < 1e-6

    assert isclose(case_y["left_support_fz_kN"], case_x["left_support_fz_kN"], rel_tol=0.01)
    assert isclose(case_y["right_support_fz_kN"], case_x["right_support_fz_kN"], rel_tol=0.01)
    assert isclose(case_y["midspan_moment_kNm"], case_x["midspan_moment_kNm"], rel_tol=0.01)
    assert isclose(case_y["mid_uz_mm"], case_x["mid_uz_mm"], rel_tol=0.01)
