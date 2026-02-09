"""Column axis-convention verification against hand calculations.

This test suite validates the current column vecxz convention:
- vecxz = (0, 1, 0)
- local_x = vertical column axis
- local_y = global X, local_z = global Y
"""

from math import isclose

import pytest

from src.fem.fem_engine import Element, ElementType, FEMModel, Load, Node
from src.fem.solver import FEMSolver

COLUMN_HEIGHT_M = 3.0
POINT_LOAD_KN = 100.0
POINT_LOAD_N = POINT_LOAD_KN * 1000.0
E_PA = 30e9
G_PA = E_PA / (2.0 * (1.0 + 0.2))


def _skip_if_no_opensees() -> None:
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


def _create_cantilever_column_model(
    width_mm: float,
    depth_mm: float,
    load_fx_n: float,
    load_fy_n: float,
    num_subdivisions: int = 4,
) -> tuple[FEMModel, int]:
    model = FEMModel()
    dz = COLUMN_HEIGHT_M / num_subdivisions

    for i in range(num_subdivisions + 1):
        z = i * dz
        restraints = [1, 1, 1, 1, 1, 1] if i == 0 else [0, 0, 0, 0, 0, 0]
        model.add_node(Node(tag=i + 1, x=0.0, y=0.0, z=z, restraints=restraints))

    width_m = width_mm / 1000.0
    depth_m = depth_mm / 1000.0
    area_m2 = width_m * depth_m
    iz_m4 = width_m * depth_m**3 / 12.0
    iy_m4 = depth_m * width_m**3 / 12.0

    model.add_material(
        1,
        {
            "material_type": "Concrete01",
            "tag": 1,
            "fpc": -30e6,
            "epsc0": -0.002,
            "fpcu": -20e6,
            "epsU": -0.0035,
        },
    )
    model.add_section(
        1,
        {
            "section_type": "ElasticBeamSection",
            "tag": 1,
            "E": E_PA,
            "A": area_m2,
            "Iz": iz_m4,
            "Iy": iy_m4,
            "G": G_PA,
            "J": 0.001,
        },
    )

    for i in range(num_subdivisions):
        model.add_element(
            Element(
                tag=i + 1,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[i + 1, i + 2],
                material_tag=1,
                section_tag=1,
                geometry={
                    "vecxz": (0.0, 1.0, 0.0),
                    "parent_column_id": 1,
                    "sub_element_index": i,
                },
            )
        )

    top_node = num_subdivisions + 1
    model.add_load(
        Load(
            node_tag=top_node,
            load_values=[load_fx_n, load_fy_n, 0.0, 0.0, 0.0, 0.0],
            load_pattern=1,
        )
    )

    return model, top_node


def _run_column_case(width_mm: float, depth_mm: float, load_fx_n: float, load_fy_n: float) -> dict:
    model, top_node = _create_cantilever_column_model(
        width_mm=width_mm,
        depth_mm=depth_mm,
        load_fx_n=load_fx_n,
        load_fy_n=load_fy_n,
    )

    solver = FEMSolver()
    model.build_openseespy_model(ndm=3, ndf=6)
    result = solver.run_linear_static_analysis(load_pattern=1)
    assert result.success, f"Column analysis failed: {result.message}"

    base_reaction = result.node_reactions[1]
    top_disp = result.node_displacements[top_node]

    # For vecxz=(0,1,0) in a vertical column:
    # local_y = global X and local_z = global Y.
    local_my_kNm = abs(base_reaction[3]) / 1000.0  # global Mx
    local_mz_kNm = abs(base_reaction[4]) / 1000.0  # global My

    return {
        "local_my_kNm": local_my_kNm,
        "local_mz_kNm": local_mz_kNm,
        "ux_mm": abs(top_disp[0]) * 1000.0,
        "uy_mm": abs(top_disp[1]) * 1000.0,
        "vecxz_values": [elem.geometry.get("vecxz") for elem in model.elements.values()],
    }


@pytest.mark.integration
def test_column_x_load_maps_to_major_axis_mz() -> None:
    _skip_if_no_opensees()

    case = _run_column_case(width_mm=300.0, depth_mm=500.0, load_fx_n=POINT_LOAD_N, load_fy_n=0.0)

    expected_moment = POINT_LOAD_KN * COLUMN_HEIGHT_M
    expected_deflection_mm = (
        POINT_LOAD_N * COLUMN_HEIGHT_M**3
        / (3.0 * E_PA * (0.3 * 0.5**3 / 12.0))
        * 1000.0
    )

    for vecxz in case["vecxz_values"]:
        assert vecxz == pytest.approx((0.0, 1.0, 0.0), abs=1e-12)

    assert isclose(case["local_mz_kNm"], expected_moment, rel_tol=0.01)
    assert case["local_mz_kNm"] > 0.0
    assert case["local_my_kNm"] < 1e-6
    assert isclose(case["ux_mm"], expected_deflection_mm, rel_tol=0.01)
    assert case["uy_mm"] < 1e-6


@pytest.mark.integration
def test_column_y_load_maps_to_minor_axis_my_with_expected_ratio() -> None:
    _skip_if_no_opensees()

    case_x = _run_column_case(width_mm=300.0, depth_mm=500.0, load_fx_n=POINT_LOAD_N, load_fy_n=0.0)
    case_y = _run_column_case(width_mm=300.0, depth_mm=500.0, load_fx_n=0.0, load_fy_n=POINT_LOAD_N)

    expected_moment = POINT_LOAD_KN * COLUMN_HEIGHT_M
    expected_deflection_y_mm = (
        POINT_LOAD_N * COLUMN_HEIGHT_M**3
        / (3.0 * E_PA * (0.5 * 0.3**3 / 12.0))
        * 1000.0
    )

    assert isclose(case_y["local_my_kNm"], expected_moment, rel_tol=0.01)
    assert case_y["local_my_kNm"] > 0.0
    assert case_y["local_mz_kNm"] < 1e-6
    assert isclose(case_y["uy_mm"], expected_deflection_y_mm, rel_tol=0.01)
    assert case_y["ux_mm"] < 1e-6

    stiffness_ratio = case_y["uy_mm"] / case_x["ux_mm"]
    assert isclose(stiffness_ratio, 2.7777777777777777, rel_tol=0.01)


@pytest.mark.integration
def test_square_column_is_symmetric_between_x_and_y() -> None:
    _skip_if_no_opensees()

    case_x = _run_column_case(width_mm=400.0, depth_mm=400.0, load_fx_n=POINT_LOAD_N, load_fy_n=0.0)
    case_y = _run_column_case(width_mm=400.0, depth_mm=400.0, load_fx_n=0.0, load_fy_n=POINT_LOAD_N)

    expected_moment = POINT_LOAD_KN * COLUMN_HEIGHT_M

    assert isclose(case_x["local_mz_kNm"], expected_moment, rel_tol=0.01)
    assert isclose(case_y["local_my_kNm"], expected_moment, rel_tol=0.01)
    assert isclose(case_x["ux_mm"], case_y["uy_mm"], rel_tol=0.01)
