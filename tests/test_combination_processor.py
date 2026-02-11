"""Unit tests for src.fem.combination_processor."""

from src.fem.combination_processor import (
    combine_results,
    compute_envelope,
    get_applicable_combinations,
)
from src.fem.load_combinations import (
    LoadCombinationCategory,
    LoadCombinationDefinition,
    LoadCombinationLibrary,
    LoadComponentType,
)
from src.fem.solver import AnalysisResult
from src.core.data_models import LoadCombination


def _build_result(scale: float) -> AnalysisResult:
    return AnalysisResult(
        success=True,
        converged=True,
        message="ok",
        node_displacements={1: [1.0 * scale, 2.0 * scale, 3.0 * scale, 4.0 * scale, 5.0 * scale, 6.0 * scale]},
        node_reactions={10: [10.0 * scale, 20.0 * scale, 30.0 * scale, 40.0 * scale, 50.0 * scale, 60.0 * scale]},
        element_forces={
            100: {
                "N_i": 1.0 * scale,
                "Vy_i": 2.0 * scale,
                "Vz_i": 3.0 * scale,
                "T_i": 4.0 * scale,
                "My_i": 5.0 * scale,
                "Mz_i": 6.0 * scale,
                "N_j": 7.0 * scale,
                "Vy_j": 8.0 * scale,
                "Vz_j": 9.0 * scale,
                "T_j": 10.0 * scale,
                "My_j": 11.0 * scale,
                "Mz_j": 12.0 * scale,
            }
        },
    )


def test_combine_results_gravity_superposition():
    solver_results = {
        "DL": _build_result(1.0),
        "SDL": _build_result(2.0),
        "LL": _build_result(3.0),
    }
    lc1 = LoadCombinationLibrary.get_uls_gravity_combinations()[0]  # 1.4DL+1.4SDL+1.6LL

    combined = combine_results(solver_results, lc1)

    expected_factor = 1.4 * 1.0 + 1.4 * 2.0 + 1.6 * 3.0
    assert combined.success
    assert combined.node_displacements[1][0] == expected_factor
    assert combined.node_reactions[10][5] == 60.0 * expected_factor
    assert combined.element_forces[100]["Mz_j"] == 12.0 * expected_factor


def test_combine_results_missing_component_treated_as_zero():
    wind_combo = LoadCombinationDefinition(
        name="TEST_MISSING_WIND",
        combination_type=LoadCombination.ULS_WIND_1,
        category=LoadCombinationCategory.ULS_WIND,
        load_factors={
            LoadComponentType.DL: 1.4,
            LoadComponentType.W1: 1.4,
        },
        description="test",
        code_clause="test",
    )

    solver_results = {"DL": _build_result(1.0)}
    combined = combine_results(solver_results, wind_combo)

    assert combined.success
    assert combined.node_displacements[1][0] == 1.4
    assert combined.element_forces[100]["N_i"] == 1.4


def test_combine_results_simplified_wind_combo():
    solver_results = {
        "DL": _build_result(1.0),
        "SDL": _build_result(1.0),
        "W1": _build_result(2.0),
    }
    combo = next(
        c for c in LoadCombinationLibrary.get_uls_wind_combinations() if c.name == "LC_W1_MAX"
    )

    combined = combine_results(solver_results, combo)

    # 1.4*DL + 1.4*SDL + 1.4*W1 where W1 has scale 2.0
    expected = 1.4 * 1.0 + 1.4 * 1.0 + 1.4 * 2.0
    assert combined.node_reactions[10][2] == 30.0 * expected


def test_get_applicable_combinations_filters_unavailable_components():
    combos = LoadCombinationLibrary.get_all_combinations()
    available_cases = ["DL", "SDL", "LL"]

    applicable = get_applicable_combinations(combos, available_cases)
    applicable_names = {combo.name for combo in applicable}

    assert "LC1" in applicable_names
    assert "SLS1" in applicable_names
    assert "LC_W1_MAX" not in applicable_names


def test_get_applicable_combinations_supports_canonical_w_cases():
    combos = LoadCombinationLibrary.get_uls_wind_combinations()
    available_cases = ["DL", "SDL", "W1", "W2"]

    applicable = get_applicable_combinations(combos, available_cases)
    applicable_names = {combo.name for combo in applicable}

    assert "LC_W1_MAX" in applicable_names
    assert "LC_W1_MIN" in applicable_names
    assert "LC_W2_MAX" in applicable_names
    assert "LC_W2_MIN" in applicable_names
    assert "LC_W3_MAX" not in applicable_names


def test_compute_envelope_tracks_governing_combination_name():
    combo_a = AnalysisResult(
        success=True,
        converged=True,
        message="A",
        element_forces={
            1: {
                "N_i": 10.0, "N_j": 8.0,
                "Vy_i": 1.0, "Vy_j": 2.0,
                "Vz_i": 0.0, "Vz_j": 0.0,
                "T_i": 5.0, "T_j": 4.0,
                "My_i": 3.0, "My_j": 2.0,
                "Mz_i": 4.0, "Mz_j": 3.0,
            }
        },
    )
    combo_b = AnalysisResult(
        success=True,
        converged=True,
        message="B",
        element_forces={
            1: {
                "N_i": -20.0, "N_j": -10.0,
                "Vy_i": 6.0, "Vy_j": 7.0,
                "Vz_i": 0.0, "Vz_j": 0.0,
                "T_i": 9.0, "T_j": 8.0,
                "My_i": 1.0, "My_j": 1.5,
                "Mz_i": 2.0, "Mz_j": 2.5,
            }
        },
    )

    envelopes = compute_envelope({"LC_A": combo_a, "LC_B": combo_b})
    env = envelopes[1]

    assert env.N_max.max_value == 20.0
    assert env.N_max.governing_max_case_name == "LC_B"
    assert env.N_min.min_value == -15.0
    assert env.N_min.governing_min_case_name == "LC_B"
    assert env.T_max.max_value == 9.0
    assert env.T_max.governing_max_case_name == "LC_B"
