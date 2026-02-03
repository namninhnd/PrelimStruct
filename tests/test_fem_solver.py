import numpy as np

from src.fem.fem_engine import Load, create_simple_frame_model
from src.fem.materials import ConcreteGrade, reset_material_tags
from src.fem.solver import AnalysisResult, FEMSolver, analyze_model


def test_analysis_result_helpers() -> None:
    result = AnalysisResult(
        success=True,
        message="ok",
        node_displacements={
            1: [0.0, 0.0, -0.01, 0.0, 0.0, 0.0],
            2: [0.0, 0.0, 0.02, 0.0, 0.0, 0.0],
        },
        node_reactions={1: [0.0, 0.0, 500.0, 0.0, 0.0, 0.0]},
    )

    node_tag, uz = result.get_max_displacement(dof=2)
    assert node_tag == 2
    assert uz == 0.02
    assert result.get_total_reaction(dof=2) == 500.0


def test_analyze_model_success(ops_monkeypatch) -> None:
    reset_material_tags()
    model = create_simple_frame_model(
        bay_width=4.0,
        bay_height=3.0,
        n_bays=1,
        n_stories=1,
        concrete_grade=ConcreteGrade.C30,
        beam_width=300,
        beam_height=500,
        column_width=400,
        column_height=400,
    )

    # Apply a simple nodal load at the top-right node (tag 4)
    model.add_load(Load(node_tag=4, load_values=[0, 0, -10000, 0, 0, 0], load_pattern=1))

    # Fake analysis results
    ops_monkeypatch.displacements = {
        1: [0, 0, 0, 0, 0, 0],
        2: [0, 0, 0, 0, 0, 0],
        3: [0, 0, -0.004, 0, 0, 0],
        4: [0, 0, -0.006, 0, 0, 0],
    }
    ops_monkeypatch.reactions = {
        1: [0, 0, 6000, 0, 0, 0],
        2: [0, 0, 4000, 0, 0, 0],
    }
    ops_monkeypatch.element_forces = {
        1: [0.0] * 12,
        2: [0.0] * 12,
        3: [0.0] * 12,
    }

    result = analyze_model(model)

    assert result.success
    assert result.converged
    assert result.node_displacements[4][2] == -0.006
    assert result.node_reactions[1][2] == 6000
    assert result.element_forces[3]["Mz_i"] == 0.0


def test_fem_solver_frequency_extraction(ops_monkeypatch) -> None:
    ops_monkeypatch.eigenvalues = [4 * np.pi**2, 9 * np.pi**2]
    solver = FEMSolver()
    freqs = solver.get_natural_frequencies(n_modes=2)

    assert freqs is not None
    # Frequencies should be sqrt(lambda)/(2*pi) so values become [1, 1.5] Hz
    assert np.allclose(freqs, np.array([1.0, 1.5]))
