"""Utilities for writing benchmark evidence during verification tests."""

from pathlib import Path
from typing import Optional

from src.core.data_models import ProjectData
from tests.verification.evidence_writer import (
    EvidenceRecord,
    GroupAverages,
    InputSpec,
    ReactionRecord,
    write_evidence,
)


def _calc_relative_error_percent(
    expected_sum_fz_kn: float,
    actual_sum_fz_kn: float,
) -> float:
    expected_abs = abs(expected_sum_fz_kn)
    actual_abs = abs(actual_sum_fz_kn)

    if expected_abs < 1e-12:
        return 0.0 if actual_abs < 1e-12 else 100.0

    return abs(actual_abs - expected_abs) / expected_abs * 100.0


def get_base_reaction_records(model, result) -> list[ReactionRecord]:
    """Collect deterministic base reaction records from model/result."""
    records = []

    for tag, node in model.nodes.items():
        if abs(node.z) < 1e-6 and node.is_fixed and tag in result.node_reactions:
            records.append(
                ReactionRecord(
                    node_tag=tag,
                    x=node.x,
                    y=node.y,
                    Fz_kN=abs(result.node_reactions[tag][2]) / 1000.0,
                )
            )

    records.sort(key=lambda rec: (rec.x, rec.y, rec.node_tag))
    return records


def write_benchmark_evidence(
    model_name: str,
    load_case: str,
    project: ProjectData,
    model,
    result,
    expected_sum_fz_kn: float,
    actual_sum_fz_kn: float,
    slab_elements_per_bay: int,
    group_averages: Optional[GroupAverages] = None,
    mesh_level: Optional[int] = None,
) -> Path:
    """Write one benchmark evidence JSON and return its path."""
    input_spec = InputSpec(
        model=model_name,
        load_case=load_case,
        bay_x=project.geometry.bay_x,
        bay_y=project.geometry.bay_y,
        slab_elements_per_bay=slab_elements_per_bay,
    )

    record = EvidenceRecord(
        input_spec=input_spec,
        load_case=load_case,
        expected_sum_Fz_kN=expected_sum_fz_kn,
        actual_sum_Fz_kN=actual_sum_fz_kn,
        relative_error_percent=_calc_relative_error_percent(
            expected_sum_fz_kn,
            actual_sum_fz_kn,
        ),
        reactions=get_base_reaction_records(model, result),
        group_averages=group_averages,
    )

    return write_evidence(model_name, load_case, record, mesh_level=mesh_level)
