"""Load-combination superposition and envelope helpers for FEM results."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from src.core.data_models import EnvelopeValue
from src.fem.load_combinations import LoadCombinationDefinition, LoadComponentType
from src.fem.results_processor import ElementForceEnvelope
from src.fem.solver import AnalysisResult


COMPONENT_TO_SOLVER_KEY: Dict[LoadComponentType, str] = {
    LoadComponentType.DL: "DL",
    LoadComponentType.SDL: "SDL",
    LoadComponentType.LL: "LL",
    LoadComponentType.WX: "Wx",
    LoadComponentType.WY: "Wy",
    LoadComponentType.WTZ: "Wtz",
}
COMPONENT_TO_SOLVER_KEY.update(
    {getattr(LoadComponentType, f"W{i}"): f"W{i}" for i in range(1, 25)}
)

_N_DOF = 6
_FORCE_COMPONENTS: Tuple[str, ...] = ("N", "Vy", "Vz", "T", "My", "Mz")
_ENVELOPE_FIELD_MAP = {
    "N": ("N_max", "N_min"),
    "Vy": ("Vy_max", "Vy_min"),
    "Vz": ("Vz_max", "Vz_min"),
    "My": ("My_max", "My_min"),
    "Mz": ("Mz_max", "Mz_min"),
    "T": ("T_max", "T_min"),
}


def combine_results(
    solver_results: Dict[str, AnalysisResult],
    combination: LoadCombinationDefinition,
) -> AnalysisResult:
    """Superpose individual load-case AnalysisResult objects with factors.

    Missing or unsuccessful components contribute zero.
    """
    weighted_results = list(_iter_weighted_results(solver_results, combination))

    combined_displacements = _combine_vector_field(weighted_results, "node_displacements")
    combined_reactions = _combine_vector_field(weighted_results, "node_reactions")
    combined_element_forces = _combine_element_forces(weighted_results)

    converged = all(result.converged for _, result in weighted_results)
    iterations = max((result.iterations for _, result in weighted_results), default=0)

    return AnalysisResult(
        success=True,
        message=f"{combination.name}: {combination.to_equation()}",
        converged=converged,
        iterations=iterations,
        node_displacements=combined_displacements,
        node_reactions=combined_reactions,
        element_forces=combined_element_forces,
    )


def compute_envelope(
    combined_results: Dict[str, AnalysisResult],
) -> Dict[int, ElementForceEnvelope]:
    """Compute element force envelopes over multiple combined results."""
    envelopes: Dict[int, ElementForceEnvelope] = {}

    for combination_name, result in combined_results.items():
        if not result.success:
            continue

        for element_id, force_dict in result.element_forces.items():
            envelope = envelopes.setdefault(element_id, ElementForceEnvelope(element_id=element_id))

            for component in _FORCE_COMPONENTS:
                key_i = f"{component}_i"
                key_j = f"{component}_j"
                if key_i not in force_dict and key_j not in force_dict:
                    continue

                value_i = force_dict.get(key_i, 0.0)
                value_j = force_dict.get(key_j, 0.0)
                max_abs = max(abs(value_i), abs(value_j))
                avg_signed = 0.5 * (value_i + value_j)

                max_field, min_field = _ENVELOPE_FIELD_MAP[component]
                max_envelope = _get_or_create_envelope_value(envelope, max_field)
                min_envelope = _get_or_create_envelope_value(envelope, min_field)

                if max_abs > max_envelope.max_value:
                    max_envelope.max_value = max_abs
                    max_envelope.governing_max_case_name = combination_name
                    max_envelope.governing_max_location = element_id

                if (
                    avg_signed < min_envelope.min_value
                    or min_envelope.governing_min_case_name is None
                ):
                    min_envelope.min_value = avg_signed
                    min_envelope.governing_min_case_name = combination_name
                    min_envelope.governing_min_location = element_id

    return envelopes


def get_applicable_combinations(
    all_combinations: List[LoadCombinationDefinition],
    available_cases: List[str],
) -> List[LoadCombinationDefinition]:
    """Filter to combinations whose required components are available."""
    available_set = set(available_cases)
    applicable: List[LoadCombinationDefinition] = []

    for combination in all_combinations:
        is_applicable = True
        for component, factor in combination.load_factors.items():
            if factor == 0.0:
                continue

            solver_key = COMPONENT_TO_SOLVER_KEY.get(component)
            if solver_key is None or solver_key not in available_set:
                is_applicable = False
                break

        if is_applicable:
            applicable.append(combination)

    return applicable


def _iter_weighted_results(
    solver_results: Dict[str, AnalysisResult],
    combination: LoadCombinationDefinition,
) -> Iterable[Tuple[float, AnalysisResult]]:
    for component, factor in combination.load_factors.items():
        if factor == 0.0:
            continue

        solver_key = COMPONENT_TO_SOLVER_KEY.get(component)
        if solver_key is None:
            continue

        component_result = solver_results.get(solver_key)
        if component_result is None or not component_result.success:
            continue

        yield factor, component_result


def _combine_vector_field(
    weighted_results: List[Tuple[float, AnalysisResult]],
    field_name: str,
) -> Dict[int, List[float]]:
    combined: Dict[int, List[float]] = {}

    for factor, result in weighted_results:
        vector_map = getattr(result, field_name, {})
        for node_tag, values in vector_map.items():
            if node_tag not in combined:
                combined[node_tag] = [0.0] * _N_DOF

            for dof_idx in range(min(len(values), _N_DOF)):
                combined[node_tag][dof_idx] += factor * values[dof_idx]

    return combined


def _combine_element_forces(
    weighted_results: List[Tuple[float, AnalysisResult]],
) -> Dict[int, Dict[str, float]]:
    combined: Dict[int, Dict[str, float]] = {}

    for factor, result in weighted_results:
        for element_id, force_dict in result.element_forces.items():
            if element_id not in combined:
                combined[element_id] = {}

            for force_key, force_value in force_dict.items():
                if force_key not in combined[element_id]:
                    combined[element_id][force_key] = 0.0
                combined[element_id][force_key] += factor * force_value

    return combined


def _get_or_create_envelope_value(
    envelope: ElementForceEnvelope,
    field_name: str,
) -> EnvelopeValue:
    current = getattr(envelope, field_name, None)
    if current is None:
        current = EnvelopeValue()
        setattr(envelope, field_name, current)
    return current
