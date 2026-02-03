from __future__ import annotations

from src.core.data_models import GeometryInput, LoadInput, LateralInput, ProjectData, WindResult
from src.fem.analysis_summary import build_fem_vs_simplified_comparison, get_base_shear_from_reactions, get_top_drift
from src.fem.fem_engine import FEMModel, Node
from src.fem.solver import AnalysisResult


def _make_project() -> ProjectData:
    project = ProjectData(
        geometry=GeometryInput(6.0, 6.0, 3, 3.0, num_bays_x=1, num_bays_y=1),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        lateral=LateralInput(building_width=6.0, building_depth=6.0),
    )
    project.wind_result = WindResult(base_shear=1200.0, drift_mm=15.0)
    return project


def _make_model() -> FEMModel:
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0))
    model.add_node(Node(tag=2, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=0.0, y=0.0, z=6.0))
    return model


def test_get_base_shear_from_reactions() -> None:
    reactions = {
        1: [1000.0, 200.0, 0.0, 0.0, 0.0, 0.0],
        2: [500.0, -50.0, 0.0, 0.0, 0.0, 0.0],
    }
    assert get_base_shear_from_reactions(reactions, direction="X") == 1500.0
    assert get_base_shear_from_reactions(reactions, direction="Y") == 150.0


def test_get_top_drift_returns_mm() -> None:
    model = _make_model()
    displacements = {
        1: [0.0, 0.0, 0.0],
        2: [0.005, 0.0, 0.0],
        3: [0.012, 0.0, 0.0],
    }
    drift = get_top_drift(model, displacements, direction="X")
    assert drift == 12.0


def test_build_fem_vs_simplified_comparison() -> None:
    project = _make_project()
    model = _make_model()
    result = AnalysisResult(
        success=True,
        message="ok",
        node_displacements={3: [0.01, 0.0, 0.0]},
        node_reactions={1: [900000.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
    )

    rows = build_fem_vs_simplified_comparison(project, model, result, direction="X")

    assert rows[0].metric == "Base Shear"
    assert rows[0].simplified_value == 1200.0
    assert rows[0].fem_value == 900.0
    assert rows[1].metric == "Top Drift"
    assert rows[1].simplified_value == 15.0
    assert rows[1].fem_value == 10.0
