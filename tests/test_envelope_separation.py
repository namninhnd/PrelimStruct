"""Tests for major/minor envelope separation in ResultsProcessor."""

from src.core.data_models import LoadCaseResult, LoadCombination
from src.fem.results_processor import ResultsProcessor


def _process_single_element(forces: dict, combo: LoadCombination = LoadCombination.ULS_GRAVITY_1):
    processor = ResultsProcessor()
    processor.process_load_case_results(
        [
            LoadCaseResult(
                combination=combo,
                element_forces={1: forces},
                node_displacements={},
                reactions={},
            )
        ]
    )
    return processor.element_force_envelopes[1]


def test_envelope_separates_major_minor_moment() -> None:
    envelope = _process_single_element(
        {
            "N_i": 0.0,
            "N_j": 0.0,
            "Vy_i": 30.0,
            "Vy_j": 30.0,
            "Vz_i": 0.2,
            "Vz_j": 0.2,
            "Mz_i": 45.0,
            "Mz_j": 45.0,
            "My_i": 0.5,
            "My_j": 0.5,
        }
    )

    assert envelope.Mz_max.max_value == 45.0
    assert envelope.My_max.max_value == 0.5
    assert envelope.Mz_max.max_value > envelope.My_max.max_value * 50.0


def test_envelope_separates_major_minor_shear() -> None:
    envelope = _process_single_element(
        {
            "N_i": 0.0,
            "N_j": 0.0,
            "Vy_i": 30.0,
            "Vy_j": 30.0,
            "Vz_i": 1.0,
            "Vz_j": 1.0,
            "Mz_i": 45.0,
            "Mz_j": 45.0,
            "My_i": 0.0,
            "My_j": 0.0,
        }
    )

    assert envelope.Vy_max.max_value == 30.0
    assert envelope.Vz_max.max_value == 1.0
    assert envelope.Vy_max.max_value > envelope.Vz_max.max_value * 20.0


def test_2d_fallback_maps_to_major() -> None:
    envelope = _process_single_element(
        {
            "V_i": 75.0,
            "V_j": 75.0,
            "M_i": 300.0,
            "M_j": 300.0,
        },
        combo=LoadCombination.ULS_WIND_1,
    )

    assert envelope.N_max.max_value == 0.0
    assert envelope.Vy_max.max_value == 75.0
    assert envelope.Vz_max.max_value == 0.0
    assert envelope.Mz_max.max_value == 300.0
    assert envelope.My_max.max_value == 0.0


def test_3d_forces_separate_into_correct_fields() -> None:
    envelope = _process_single_element(
        {
            "N_i": 100.0,
            "N_j": 80.0,
            "Vy_i": 120.0,
            "Vy_j": 90.0,
            "Vz_i": 40.0,
            "Vz_j": 60.0,
            "Mz_i": 300.0,
            "Mz_j": 250.0,
            "My_i": 90.0,
            "My_j": 110.0,
        },
        combo=LoadCombination.ULS_WIND_1,
    )

    assert envelope.N_max.max_value == 100.0
    assert envelope.Vy_max.max_value == 120.0
    assert envelope.Vz_max.max_value == 60.0
    assert envelope.Mz_max.max_value == 300.0
    assert envelope.My_max.max_value == 110.0
    assert envelope.Vy_max.governing_max_case == LoadCombination.ULS_WIND_1
    assert envelope.Mz_max.governing_max_case == LoadCombination.ULS_WIND_1
