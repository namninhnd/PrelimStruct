from types import SimpleNamespace

from src.fem.design_check_summary import ORDERED_TYPE_LABELS, compute_design_checks_summary
from src.fem.fem_engine import Element, ElementType, FEMModel, Node
from src.fem.solver import AnalysisResult


def _make_model() -> FEMModel:
    model = FEMModel()
    model.nodes[1] = Node(tag=1, x=0.0, y=0.0, z=0.0)
    model.nodes[2] = Node(tag=2, x=6.0, y=0.0, z=0.0)
    model.nodes[3] = Node(tag=3, x=0.0, y=8.0, z=0.0)
    model.nodes[4] = Node(tag=4, x=0.0, y=8.0, z=3.0)
    model.nodes[5] = Node(tag=5, x=1.0, y=1.0, z=0.0)
    model.nodes[6] = Node(tag=6, x=1.0, y=2.0, z=0.0)
    model.nodes[7] = Node(tag=7, x=1.0, y=2.0, z=3.0)
    model.nodes[8] = Node(tag=8, x=1.0, y=1.0, z=3.0)

    model.elements[101] = Element(tag=101, element_type=ElementType.ELASTIC_BEAM, node_tags=[1, 2], material_tag=1)
    model.elements[102] = Element(tag=102, element_type=ElementType.SECONDARY_BEAM, node_tags=[1, 3], material_tag=1)
    model.elements[103] = Element(
        tag=103,
        element_type=ElementType.ELASTIC_BEAM,
        node_tags=[3, 4],
        material_tag=1,
        geometry={"parent_column_id": "C1"},
    )
    model.elements[104] = Element(
        tag=104,
        element_type=ElementType.ELASTIC_BEAM,
        node_tags=[2, 3],
        material_tag=1,
        geometry={"coupling_beam": True},
    )
    model.elements[201] = Element(tag=201, element_type=ElementType.SHELL_MITC4, node_tags=[5, 6, 7, 8], material_tag=1)
    return model


def _make_case(v_scale: float) -> AnalysisResult:
    return AnalysisResult(
        success=True,
        converged=True,
        message="ok",
        element_forces={
            101: {"Vy_i": 100.0 * v_scale, "N_i": 50.0 * v_scale},
            102: {"Vy_i": 80.0 * v_scale, "N_i": 40.0 * v_scale},
            103: {"Vy_i": 30.0 * v_scale, "N_i": 300.0 * v_scale},
            104: {"Vy_i": 90.0 * v_scale, "N_i": 45.0 * v_scale},
        },
        node_reactions={
            5: [20.0 * v_scale, 0.0, 100.0 * v_scale, 0.0, 0.0, 0.0],
            6: [10.0 * v_scale, 0.0, 120.0 * v_scale, 0.0, 0.0, 0.0],
        },
    )


def _make_project() -> SimpleNamespace:
    return SimpleNamespace(
        materials=SimpleNamespace(fcu_beam=40.0),
        lateral=SimpleNamespace(wall_thickness=500.0),
        primary_beam_result=SimpleNamespace(width=300, depth=600),
        secondary_beam_result=SimpleNamespace(width=250, depth=500),
        column_result=SimpleNamespace(width=400, depth=400, dimension=400),
        coupling_beam_width_mm=500,
        coupling_beam_depth_mm=800,
    )


def test_design_check_summary_returns_per_type_top3():
    model = _make_model()
    project = _make_project()
    results_by_case = {"DL": _make_case(1.0), "SDL": _make_case(0.6), "LL": _make_case(0.8)}

    summary = compute_design_checks_summary(
        project=project,
        model=model,
        results_by_case=results_by_case,
        selected_combination_names=["LC1"],
        top_n=3,
    )

    for label in ORDERED_TYPE_LABELS:
        assert label in summary.top3_by_type

    assert summary.top3_by_type["Primary Beam"]
    assert summary.top3_by_type["Secondary Beam"]
    assert summary.top3_by_type["Column"]
    assert summary.top3_by_type["Coupling Beam"]
    assert summary.top3_by_type["Wall"]
    assert summary.top3_by_type["Slab Strip X"] or summary.top3_by_type["Slab Strip Y"]


def test_design_check_summary_warns_when_selected_combinations_inapplicable():
    model = _make_model()
    project = _make_project()
    results_by_case = {"DL": _make_case(1.0), "SDL": _make_case(0.6), "LL": _make_case(0.8)}

    summary = compute_design_checks_summary(
        project=project,
        model=model,
        results_by_case=results_by_case,
        selected_combination_names=["NOT_A_REAL_COMB"],
        top_n=3,
    )

    assert any("not applicable" in msg.lower() for msg in summary.warnings)
