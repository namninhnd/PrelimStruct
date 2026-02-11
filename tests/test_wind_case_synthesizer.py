"""Unit tests for canonical W1-W24 wind case synthesis."""

import pytest

from src.fem.solver import AnalysisResult
from src.fem.wind_case_synthesizer import (
    COMPONENT_CASE_KEYS,
    WIND_CASE_COEFFICIENTS,
    synthesize_w1_w24_cases,
    with_synthesized_w1_w24_cases,
)


def _build_result(scale: float, success: bool = True, converged: bool = True, iterations: int = 0) -> AnalysisResult:
    return AnalysisResult(
        success=success,
        converged=converged,
        iterations=iterations,
        message="ok" if success else "failed",
        node_displacements={
            1: [
                1.0 * scale,
                -2.0 * scale,
                3.0 * scale,
                -4.0 * scale,
                5.0 * scale,
                -6.0 * scale,
            ]
        },
        node_reactions={
            10: [
                10.0 * scale,
                -20.0 * scale,
                30.0 * scale,
                -40.0 * scale,
                50.0 * scale,
                -60.0 * scale,
            ]
        },
        element_forces={
            100: {
                "N_i": 1.5 * scale,
                "Vy_i": -2.5 * scale,
                "Mz_j": 3.5 * scale,
            }
        },
    )


def _expected(case_name: str, wx_value: float, wy_value: float, wtz_value: float) -> float:
    coeff_wx, coeff_wy, coeff_wtz = WIND_CASE_COEFFICIENTS[case_name]
    return coeff_wx * wx_value + coeff_wy * wy_value + coeff_wtz * wtz_value


def test_matrix_contains_24_cases_with_expected_golden_rows() -> None:
    assert COMPONENT_CASE_KEYS == ("Wx", "Wy", "Wtz")
    assert len(WIND_CASE_COEFFICIENTS) == 24

    assert WIND_CASE_COEFFICIENTS["W1"] == (1.0, 0.55, 0.55)
    assert WIND_CASE_COEFFICIENTS["W7"] == (-1.0, -0.55, 0.55)
    assert WIND_CASE_COEFFICIENTS["W13"] == (-0.55, 1.0, 0.55)
    assert WIND_CASE_COEFFICIENTS["W19"] == (0.55, -0.55, 1.0)
    assert WIND_CASE_COEFFICIENTS["W24"] == (-0.55, -0.55, -1.0)


def test_synthesize_selected_cases_matches_linear_superposition() -> None:
    wx = _build_result(scale=2.0, iterations=5)
    wy = _build_result(scale=3.0, iterations=7)
    wtz = _build_result(scale=5.0, iterations=9)

    synthesized = synthesize_w1_w24_cases({"Wx": wx, "Wy": wy, "Wtz": wtz})

    assert len(synthesized) == 24
    for case_name in ("W1", "W2", "W7", "W13", "W19"):
        case_result = synthesized[case_name]

        expected_disp = _expected(
            case_name,
            wx.node_displacements[1][0],
            wy.node_displacements[1][0],
            wtz.node_displacements[1][0],
        )
        expected_reaction = _expected(
            case_name,
            wx.node_reactions[10][5],
            wy.node_reactions[10][5],
            wtz.node_reactions[10][5],
        )
        expected_force = _expected(
            case_name,
            wx.element_forces[100]["Mz_j"],
            wy.element_forces[100]["Mz_j"],
            wtz.element_forces[100]["Mz_j"],
        )

        assert case_result.node_displacements[1][0] == pytest.approx(expected_disp)
        assert case_result.node_reactions[10][5] == pytest.approx(expected_reaction)
        assert case_result.element_forces[100]["Mz_j"] == pytest.approx(expected_force)
        assert case_result.converged
        assert case_result.iterations == 9


def test_sign_permutation_pairs_are_applied_correctly() -> None:
    wx = _build_result(scale=1.0)
    wy = _build_result(scale=2.0)
    wtz = _build_result(scale=4.0)

    synthesized = synthesize_w1_w24_cases({"Wx": wx, "Wy": wy, "Wtz": wtz})

    # W1/W2 differ only by Wtz sign, so delta must be 2*0.55*Wtz contribution.
    w1 = synthesized["W1"].node_displacements[1][0]
    w2 = synthesized["W2"].node_displacements[1][0]
    assert (w1 - w2) == pytest.approx(2.0 * 0.55 * wtz.node_displacements[1][0])

    # W1/W5 differ only by Wx sign, so delta must be 2*1.0*Wx contribution.
    w5 = synthesized["W5"].node_reactions[10][0]
    assert (synthesized["W1"].node_reactions[10][0] - w5) == pytest.approx(
        2.0 * wx.node_reactions[10][0]
    )


def test_with_synthesized_cases_preserves_original_results() -> None:
    dl = _build_result(scale=1.2)
    wx = _build_result(scale=2.0)
    wy = _build_result(scale=3.0)
    wtz = _build_result(scale=4.0)

    merged = with_synthesized_w1_w24_cases(
        {
            "DL": dl,
            "Wx": wx,
            "Wy": wy,
            "Wtz": wtz,
        }
    )

    assert merged["DL"] is dl
    assert "W1" in merged
    assert "W24" in merged
    assert merged["W24"].success


def test_synthesize_fails_fast_when_component_case_is_missing() -> None:
    with pytest.raises(ValueError, match="missing component results Wtz"):
        synthesize_w1_w24_cases(
            {
                "Wx": _build_result(scale=1.0),
                "Wy": _build_result(scale=1.0),
            }
        )


def test_synthesize_fails_fast_when_component_case_is_unsuccessful() -> None:
    with pytest.raises(ValueError, match="unsuccessful component results Wy"):
        synthesize_w1_w24_cases(
            {
                "Wx": _build_result(scale=1.0),
                "Wy": _build_result(scale=1.0, success=False),
                "Wtz": _build_result(scale=1.0),
            }
        )
