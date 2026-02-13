"""Synthesize canonical W1-W24 wind cases from component analysis results.

The coefficient matrix is fixed from HK Wind Effects 2019 Table 2-1 expansion,
matching the project reference `windloadcombo.csv` and Phase 11 Section 5.5.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Mapping, Tuple

from src.fem.solver import AnalysisResult

logger = logging.getLogger(__name__)


COMPONENT_CASE_KEYS: Tuple[str, str, str] = ("Wx", "Wy", "Wtz")

# (Wx coefficient, Wy coefficient, Wtz coefficient)
WIND_CASE_COEFFICIENTS: Dict[str, Tuple[float, float, float]] = {
    "W1": (1.00, 0.55, 0.55),
    "W2": (1.00, 0.55, -0.55),
    "W3": (1.00, -0.55, 0.55),
    "W4": (1.00, -0.55, -0.55),
    "W5": (-1.00, 0.55, 0.55),
    "W6": (-1.00, 0.55, -0.55),
    "W7": (-1.00, -0.55, 0.55),
    "W8": (-1.00, -0.55, -0.55),
    "W9": (0.55, 1.00, 0.55),
    "W10": (0.55, 1.00, -0.55),
    "W11": (0.55, -1.00, 0.55),
    "W12": (0.55, -1.00, -0.55),
    "W13": (-0.55, 1.00, 0.55),
    "W14": (-0.55, 1.00, -0.55),
    "W15": (-0.55, -1.00, 0.55),
    "W16": (-0.55, -1.00, -0.55),
    "W17": (0.55, 0.55, 1.00),
    "W18": (0.55, 0.55, -1.00),
    "W19": (0.55, -0.55, 1.00),
    "W20": (0.55, -0.55, -1.00),
    "W21": (-0.55, 0.55, 1.00),
    "W22": (-0.55, 0.55, -1.00),
    "W23": (-0.55, -0.55, 1.00),
    "W24": (-0.55, -0.55, -1.00),
}


def synthesize_w1_w24_cases(
    component_results: Mapping[str, AnalysisResult],
) -> Dict[str, AnalysisResult]:
    """Build canonical W1-W24 analysis results from component wind cases.

    The synthesis equation is:
      W_i = c_wx * Wx + c_wy * Wy + c_wtz * Wtz
    with coefficients from ``WIND_CASE_COEFFICIENTS``.

    Raises:
        ValueError: If any required component case is missing or unsuccessful.
    """
    _validate_component_results(component_results)

    wx_result = component_results["Wx"]
    wy_result = component_results["Wy"]
    wtz_result = component_results["Wtz"]

    synthesized: Dict[str, AnalysisResult] = {}
    for case_name, coefficients in WIND_CASE_COEFFICIENTS.items():
        synthesized[case_name] = _synthesize_single_case(
            case_name=case_name,
            coefficients=coefficients,
            wx_result=wx_result,
            wy_result=wy_result,
            wtz_result=wtz_result,
        )

    return synthesized


def with_synthesized_w1_w24_cases(
    results_dict: Mapping[str, AnalysisResult],
) -> Dict[str, AnalysisResult]:
    """Return a results map extended with synthesized W1-W24 cases.

    If component wind cases are missing or unsuccessful, logs a warning
    and returns the original results without W1-W24 synthesis.
    """
    merged_results = dict(results_dict)
    try:
        merged_results.update(synthesize_w1_w24_cases(merged_results))
    except ValueError as exc:
        failed_details = []
        for key in COMPONENT_CASE_KEYS:
            r = results_dict.get(key)
            if r is None:
                failed_details.append(f"{key}: missing")
            elif not r.success:
                failed_details.append(f"{key}: failed ({r.message})")
        logger.warning(
            "W1-W24 synthesis skipped: %s. Component status: %s",
            exc,
            "; ".join(failed_details) if failed_details else "unknown",
        )
    return merged_results


def _validate_component_results(component_results: Mapping[str, AnalysisResult]) -> None:
    missing_cases = [key for key in COMPONENT_CASE_KEYS if key not in component_results]
    if missing_cases:
        raise ValueError(
            "Cannot synthesize W1-W24: missing component results "
            + ", ".join(missing_cases)
        )

    failed_cases = [
        key
        for key in COMPONENT_CASE_KEYS
        if not component_results[key].success
    ]
    if failed_cases:
        raise ValueError(
            "Cannot synthesize W1-W24: unsuccessful component results "
            + ", ".join(failed_cases)
        )


def _synthesize_single_case(
    case_name: str,
    coefficients: Tuple[float, float, float],
    wx_result: AnalysisResult,
    wy_result: AnalysisResult,
    wtz_result: AnalysisResult,
) -> AnalysisResult:
    weighted_results: List[Tuple[float, AnalysisResult]] = [
        (coefficients[0], wx_result),
        (coefficients[1], wy_result),
        (coefficients[2], wtz_result),
    ]

    combined_displacements = _combine_vector_field(weighted_results, "node_displacements")
    combined_reactions = _combine_vector_field(weighted_results, "node_reactions")
    combined_element_forces = _combine_element_forces(weighted_results)

    return AnalysisResult(
        success=True,
        message=(
            f"{case_name}: synthesized from Wx/Wy/Wtz "
            f"({coefficients[0]:+.2f}, {coefficients[1]:+.2f}, {coefficients[2]:+.2f})"
        ),
        converged=all(result.converged for _, result in weighted_results),
        iterations=max((result.iterations for _, result in weighted_results), default=0),
        node_displacements=combined_displacements,
        node_reactions=combined_reactions,
        element_forces=combined_element_forces,
    )


def _combine_vector_field(
    weighted_results: Iterable[Tuple[float, AnalysisResult]],
    field_name: str,
) -> Dict[int, List[float]]:
    combined: Dict[int, List[float]] = {}

    for factor, result in weighted_results:
        if factor == 0.0:
            continue

        vector_map: Dict[int, List[float]] = getattr(result, field_name, {})
        for node_tag, values in vector_map.items():
            if node_tag not in combined:
                combined[node_tag] = [0.0] * len(values)
            elif len(values) > len(combined[node_tag]):
                combined[node_tag].extend([0.0] * (len(values) - len(combined[node_tag])))

            for dof_idx, value in enumerate(values):
                combined[node_tag][dof_idx] += factor * value

    return combined


def _combine_element_forces(
    weighted_results: Iterable[Tuple[float, AnalysisResult]],
) -> Dict[int, Dict[str, float]]:
    combined: Dict[int, Dict[str, float]] = {}

    for factor, result in weighted_results:
        if factor == 0.0:
            continue

        for element_id, force_dict in result.element_forces.items():
            if element_id not in combined:
                combined[element_id] = {}

            for force_key, force_value in force_dict.items():
                combined[element_id][force_key] = (
                    combined[element_id].get(force_key, 0.0) + factor * force_value
                )

    return combined
