from types import SimpleNamespace

from src.fem.design_check_summary import ORDERED_TYPE_LABELS, compute_design_checks_summary
from src.fem.fem_engine import Element, ElementType, FEMModel, Node
from src.fem.solver import AnalysisResult


def _project() -> SimpleNamespace:
    return SimpleNamespace(
        materials=SimpleNamespace(fcu_beam=40.0),
        lateral=SimpleNamespace(wall_thickness=500.0),
        primary_beam_result=SimpleNamespace(width=300, depth=600),
        secondary_beam_result=SimpleNamespace(width=250, depth=500),
        column_result=SimpleNamespace(width=400, depth=400, dimension=400),
    )


def _model() -> FEMModel:
    model = FEMModel()
    model.nodes[1] = Node(tag=1, x=0.0, y=0.0, z=0.0)
    model.nodes[2] = Node(tag=2, x=6.0, y=0.0, z=0.0)
    model.elements[1] = Element(tag=1, element_type=ElementType.ELASTIC_BEAM, node_tags=[1, 2], material_tag=1)
    return model


def test_summary_returns_warning_when_results_missing():
    summary = compute_design_checks_summary(
        project=_project(),
        model=_model(),
        results_by_case={},
        selected_combination_names=["LC1"],
    )
    assert any("no solved load cases" in msg.lower() for msg in summary.warnings)
    for label in ORDERED_TYPE_LABELS:
        assert summary.top3_by_type[label] == []


def test_summary_returns_empty_when_element_forces_not_available():
    results_by_case = {
        "DL": AnalysisResult(success=True, converged=True, message="ok", node_reactions={}, element_forces={})
    }
    summary = compute_design_checks_summary(
        project=_project(),
        model=_model(),
        results_by_case=results_by_case,
        selected_combination_names=["LC1"],
    )
    for label in ORDERED_TYPE_LABELS:
        assert summary.top3_by_type[label] == []
