"""
Helpers for summarizing FEM design results and comparisons.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.core.data_models import ProjectData
from src.fem.fem_engine import FEMModel
from src.fem.solver import AnalysisResult


@dataclass(frozen=True)
class FEMComparisonRow:
    """Row of FEM comparison (hand-calc baseline vs FEM)."""
    metric: str
    simplified_value: Optional[float]
    fem_value: Optional[float]
    unit: str
    note: str = ""


def get_base_shear_from_reactions(reactions: Dict[int, List[float]],
                                  direction: str = "X") -> float:
    """Calculate base shear from reaction forces (N)."""
    direction = direction.upper()
    index = 0 if direction == "X" else 1
    return sum(values[index] for values in reactions.values())


def get_top_drift(model: FEMModel,
                  displacements: Dict[int, List[float]],
                  direction: str = "X") -> Optional[float]:
    """Calculate top drift (mm) from node displacements."""
    if not model.nodes:
        return None

    direction = direction.upper()
    index = 0 if direction == "X" else 1
    max_z = max(node.z for node in model.nodes.values())
    top_nodes = [node.tag for node in model.nodes.values() if abs(node.z - max_z) < 1e-6]
    if not top_nodes:
        return None

    max_disp = 0.0
    has_disp = False
    for tag in top_nodes:
        disp = displacements.get(tag)
        if disp and len(disp) > index:
            max_disp = max(max_disp, abs(disp[index]))
            has_disp = True

    if not has_disp:
        return None

    return max_disp * 1000.0


def build_fem_comparison(project: ProjectData,
                         model: FEMModel,
                         result: Optional[AnalysisResult],
                         direction: str = "X") -> List[FEMComparisonRow]:
    """Build comparison rows between hand-calc baseline and FEM results."""
    rows: List[FEMComparisonRow] = []
    wind = project.wind_result

    simplified_base_shear = wind.base_shear if wind else None
    fem_base_shear = None
    if result and result.node_reactions:
        fem_base_shear = get_base_shear_from_reactions(
            result.node_reactions, direction=direction
        ) / 1000.0

    rows.append(FEMComparisonRow(
        metric="Base Shear",
        simplified_value=simplified_base_shear,
        fem_value=fem_base_shear,
        unit="kN",
        note="Wind base shear vs FEM reactions",
    ))

    simplified_drift = wind.drift_mm if wind else None
    fem_drift = None
    if result and result.node_displacements:
        fem_drift = get_top_drift(model, result.node_displacements, direction=direction)

    rows.append(FEMComparisonRow(
        metric="Top Drift",
        simplified_value=simplified_drift,
        fem_value=fem_drift,
        unit="mm",
        note="Hand-calc drift vs FEM top displacement",
    ))

    return rows


__all__ = [
    "FEMComparisonRow",
    "get_base_shear_from_reactions",
    "get_top_drift",
    "build_fem_comparison",
]
