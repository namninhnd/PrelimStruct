"""Verification test for combination + envelope pipeline."""

from src.fem.combination_processor import combine_results, compute_envelope
from src.fem.load_combinations import LoadCombinationLibrary
from src.fem.solver import AnalysisResult


def _result(scale: float) -> AnalysisResult:
    return AnalysisResult(
        success=True,
        converged=True,
        message="ok",
        element_forces={
            42: {
                "N_i": 100.0 * scale,
                "Vy_i": 10.0 * scale,
                "Vz_i": 5.0 * scale,
                "T_i": 2.0 * scale,
                "My_i": 20.0 * scale,
                "Mz_i": 30.0 * scale,
                "N_j": 120.0 * scale,
                "Vy_j": 12.0 * scale,
                "Vz_j": 6.0 * scale,
                "T_j": 3.0 * scale,
                "My_j": 22.0 * scale,
                "Mz_j": 32.0 * scale,
            }
        },
    )


def test_combination_envelope_pipeline_governing_combo():
    solver_results = {
        "DL": _result(1.0),
        "SDL": _result(0.5),
        "LL": _result(0.4),
    }

    lc1 = next(c for c in LoadCombinationLibrary.get_all_combinations() if c.name == "LC1")
    sls1 = next(c for c in LoadCombinationLibrary.get_all_combinations() if c.name == "SLS1")

    combined = {
        "LC1": combine_results(solver_results, lc1),
        "SLS1": combine_results(solver_results, sls1),
    }

    envelope = compute_envelope(combined)[42]

    # LC1 has larger factors than SLS1 and should govern maxs
    assert envelope.N_max.governing_max_case_name == "LC1"
    assert envelope.Mz_max.governing_max_case_name == "LC1"
    assert envelope.Vy_max.governing_max_case_name == "LC1"
