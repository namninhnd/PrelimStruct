"""Slab mesh refinement stability tests for 2x3 bay benchmark model.

These tests verify that FEM results are stable under mesh refinement:
1. Analysis succeeds for both mesh levels (slab_elements_per_bay=1 and 2)
2. Equilibrium still holds (sum base Fz ~= expected total SDL) within 0.5%
3. Group-average reactions change by <= 5% between mesh 1 and mesh 2

For a 2x3 bay grid (3 columns in X, 4 columns in Y = 12 total):
- Corners: 4 (at grid corners)
- Edges: 6 (on boundary but not corners)
- Interior: 2 (fully interior)
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import pytest

from tests.verification.benchmarks import (
    build_benchmark_project_2x3,
    make_benchmark_options,
    calc_sdl_total_load,
)
from tests.verification.evidence_capture import write_benchmark_evidence
from tests.verification.evidence_writer import GroupAverages


def _skip_if_no_opensees():
    """Skip test if OpenSeesPy is not available."""
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


class ColumnGroup(Enum):
    """Column classification based on grid position."""
    CORNER = "corner"
    EDGE = "edge"
    INTERIOR = "interior"


@dataclass
class BaseReaction:
    """Base reaction data for a single column."""
    tag: int
    x: float
    y: float
    fz_kn: float
    group: ColumnGroup


def classify_column(
    x: float,
    y: float,
    total_x: float,
    total_y: float,
    tolerance: float = 1e-6,
) -> ColumnGroup:
    """Classify column as corner, edge, or interior based on coordinates.
    
    Args:
        x: X coordinate of column
        y: Y coordinate of column
        total_x: Total building dimension in X
        total_y: Total building dimension in Y
        tolerance: Coordinate comparison tolerance
    
    Returns:
        ColumnGroup classification
    """
    on_x_boundary = abs(x) < tolerance or abs(x - total_x) < tolerance
    on_y_boundary = abs(y) < tolerance or abs(y - total_y) < tolerance
    
    if on_x_boundary and on_y_boundary:
        return ColumnGroup.CORNER
    elif on_x_boundary or on_y_boundary:
        return ColumnGroup.EDGE
    else:
        return ColumnGroup.INTERIOR


def _get_base_reactions_with_coords(model, result, project) -> List[BaseReaction]:
    """Extract base reactions with coordinates and group classification.
    
    Args:
        model: FEMModel with nodes
        result: AnalysisResult with node_reactions
        project: ProjectData for geometry info
    
    Returns:
        List of BaseReaction with group classifications
    """
    geometry = project.geometry
    total_x = geometry.bay_x * geometry.num_bays_x
    total_y = geometry.bay_y * geometry.num_bays_y
    
    reactions = []
    for tag, node in model.nodes.items():
        if abs(node.z) < 1e-6 and node.is_fixed:
            if tag in result.node_reactions:
                fz_n = result.node_reactions[tag][2]
                fz_kn = abs(fz_n) / 1000.0
                group = classify_column(node.x, node.y, total_x, total_y)
                reactions.append(BaseReaction(
                    tag=tag,
                    x=node.x,
                    y=node.y,
                    fz_kn=fz_kn,
                    group=group,
                ))
    return reactions


def _get_base_reaction_fz_kn(model, result) -> float:
    """Sum vertical reactions at base nodes.
    
    Base nodes are identified as: z == 0.0 AND is_fixed.
    Reactions are in N, returned in kN.
    
    Args:
        model: FEMModel with nodes
        result: AnalysisResult with node_reactions
        
    Returns:
        Sum of Fz reactions in kN (positive = upward)
    """
    sum_fz_n = 0.0
    for tag, node in model.nodes.items():
        if abs(node.z) < 1e-6 and node.is_fixed:
            if tag in result.node_reactions:
                sum_fz_n += result.node_reactions[tag][2]
    return sum_fz_n / 1000.0


def _group_reactions_by_type(reactions: List[BaseReaction]) -> Dict[ColumnGroup, List[float]]:
    """Group reaction magnitudes by column type.
    
    Returns:
        Dict mapping ColumnGroup to list of Fz values in kN
    """
    grouped: Dict[ColumnGroup, List[float]] = {
        ColumnGroup.CORNER: [],
        ColumnGroup.EDGE: [],
        ColumnGroup.INTERIOR: [],
    }
    for r in reactions:
        grouped[r.group].append(r.fz_kn)
    return grouped


def _calc_group_average(reactions_by_group: Dict[ColumnGroup, List[float]], group: ColumnGroup) -> float:
    """Calculate average reaction for a column group."""
    values = reactions_by_group[group]
    if not values:
        return 0.0
    return sum(values) / len(values)


@dataclass
class MeshRunResult:
    """Results from a single mesh refinement run."""
    mesh_level: int
    success: bool
    message: str
    total_reaction_kn: float
    corner_avg_kn: float
    edge_avg_kn: float
    interior_avg_kn: float
    evidence_path: Optional[Path] = None


def _run_mesh_analysis(
    project,
    mesh_level: int,
    emit_evidence: bool = False,
) -> MeshRunResult:
    """Run SDL analysis with specified mesh level and extract results.
    
    Args:
        project: ProjectData for 2x3 benchmark
        mesh_level: slab_elements_per_bay value
    
    Returns:
        MeshRunResult with reaction data
    """
    from src.fem.model_builder import build_fem_model
    from src.fem.solver import analyze_model
    
    options = make_benchmark_options(slab_elements_per_bay=mesh_level)
    model = build_fem_model(project, options)
    
    results = analyze_model(model, load_cases=["SDL"])
    result = results["SDL"]
    
    if not result.success:
        return MeshRunResult(
            mesh_level=mesh_level,
            success=False,
            message=result.message,
            total_reaction_kn=0.0,
            corner_avg_kn=0.0,
            edge_avg_kn=0.0,
            interior_avg_kn=0.0,
        )

    total_reaction_kn = _get_base_reaction_fz_kn(model, result)
    reactions = _get_base_reactions_with_coords(model, result, project)
    grouped = _group_reactions_by_type(reactions)

    corner_avg = _calc_group_average(grouped, ColumnGroup.CORNER)
    edge_avg = _calc_group_average(grouped, ColumnGroup.EDGE)
    interior_avg = _calc_group_average(grouped, ColumnGroup.INTERIOR)

    evidence_path = None
    if emit_evidence:
        evidence_path = write_benchmark_evidence(
            model_name="2x3",
            load_case="SDL",
            project=project,
            model=model,
            result=result,
            expected_sum_fz_kn=calc_sdl_total_load(project),
            actual_sum_fz_kn=total_reaction_kn,
            slab_elements_per_bay=mesh_level,
            group_averages=GroupAverages(
                corner_avg_kN=corner_avg,
                edge_avg_kN=edge_avg,
                interior_avg_kN=interior_avg,
            ),
            mesh_level=mesh_level,
        )

    return MeshRunResult(
        mesh_level=mesh_level,
        success=True,
        message="OK",
        total_reaction_kn=total_reaction_kn,
        corner_avg_kn=corner_avg,
        edge_avg_kn=edge_avg,
        interior_avg_kn=interior_avg,
        evidence_path=evidence_path,
    )


@pytest.mark.integration
class TestMeshRefinementStability2x3:
    """Mesh refinement stability tests for 2x3 bay benchmark.
    
    Verifies that results are stable when slab_elements_per_bay changes from 1 to 2:
    - Both analyses succeed
    - Equilibrium still holds (<= 0.5% error)
    - Group-average reactions change by <= 5%
    """

    def test_mesh_refinement_both_levels_succeed(self) -> None:
        """Both mesh levels (1 and 2) should run without analysis failure."""
        _skip_if_no_opensees()
        
        project = build_benchmark_project_2x3()
        
        result_mesh1 = _run_mesh_analysis(project, mesh_level=1, emit_evidence=True)
        result_mesh2 = _run_mesh_analysis(project, mesh_level=2, emit_evidence=True)
        
        assert result_mesh1.success, (
            f"Mesh level 1 analysis FAILED: {result_mesh1.message}"
        )
        assert result_mesh2.success, (
            f"Mesh level 2 analysis FAILED: {result_mesh2.message}"
        )

    def test_mesh_refinement_equilibrium_still_holds(self) -> None:
        """Equilibrium should still hold for both mesh levels (<= 0.5% error)."""
        _skip_if_no_opensees()
        
        project = build_benchmark_project_2x3()
        expected_load_kn = calc_sdl_total_load(project)
        
        result_mesh1 = _run_mesh_analysis(project, mesh_level=1, emit_evidence=True)
        result_mesh2 = _run_mesh_analysis(project, mesh_level=2, emit_evidence=True)
        
        assert result_mesh1.success, f"Mesh 1 failed: {result_mesh1.message}"
        assert result_mesh2.success, f"Mesh 2 failed: {result_mesh2.message}"
        
        error_mesh1 = abs(abs(result_mesh1.total_reaction_kn) - expected_load_kn) / expected_load_kn
        assert error_mesh1 <= 0.005, (
            f"Mesh 1 equilibrium FAILED: "
            f"expected={expected_load_kn:.3f} kN, "
            f"actual={result_mesh1.total_reaction_kn:.3f} kN, "
            f"error={error_mesh1*100:.2f}% > 0.5%"
        )
        
        error_mesh2 = abs(abs(result_mesh2.total_reaction_kn) - expected_load_kn) / expected_load_kn
        assert error_mesh2 <= 0.005, (
            f"Mesh 2 equilibrium FAILED: "
            f"expected={expected_load_kn:.3f} kN, "
            f"actual={result_mesh2.total_reaction_kn:.3f} kN, "
            f"error={error_mesh2*100:.2f}% > 0.5%"
        )

    def test_mesh_refinement_corner_stability(self) -> None:
        """Corner group-average reactions should be stable (<= 5% change)."""
        _skip_if_no_opensees()
        
        project = build_benchmark_project_2x3()
        
        result_mesh1 = _run_mesh_analysis(project, mesh_level=1)
        result_mesh2 = _run_mesh_analysis(project, mesh_level=2)
        
        assert result_mesh1.success, f"Mesh 1 failed: {result_mesh1.message}"
        assert result_mesh2.success, f"Mesh 2 failed: {result_mesh2.message}"
        
        avg1 = result_mesh1.corner_avg_kn
        avg2 = result_mesh2.corner_avg_kn
        
        if avg1 == 0:
            pytest.skip("Corner average is zero, cannot compute relative change")
        
        relative_change = abs(avg2 - avg1) / avg1
        
        assert relative_change <= 0.05, (
            f"Corner stability FAILED: "
            f"mesh1_avg={avg1:.3f} kN, "
            f"mesh2_avg={avg2:.3f} kN, "
            f"change={relative_change*100:.2f}% > 5%"
        )

    def test_mesh_refinement_edge_stability(self) -> None:
        """Edge group-average reactions should be stable (<= 5% change)."""
        _skip_if_no_opensees()
        
        project = build_benchmark_project_2x3()
        
        result_mesh1 = _run_mesh_analysis(project, mesh_level=1)
        result_mesh2 = _run_mesh_analysis(project, mesh_level=2)
        
        assert result_mesh1.success, f"Mesh 1 failed: {result_mesh1.message}"
        assert result_mesh2.success, f"Mesh 2 failed: {result_mesh2.message}"
        
        avg1 = result_mesh1.edge_avg_kn
        avg2 = result_mesh2.edge_avg_kn
        
        if avg1 == 0:
            pytest.skip("Edge average is zero, cannot compute relative change")
        
        relative_change = abs(avg2 - avg1) / avg1
        
        assert relative_change <= 0.05, (
            f"Edge stability FAILED: "
            f"mesh1_avg={avg1:.3f} kN, "
            f"mesh2_avg={avg2:.3f} kN, "
            f"change={relative_change*100:.2f}% > 5%"
        )

    def test_mesh_refinement_interior_stability(self) -> None:
        """Interior group-average reactions should be stable (<= 5% change)."""
        _skip_if_no_opensees()
        
        project = build_benchmark_project_2x3()
        
        result_mesh1 = _run_mesh_analysis(project, mesh_level=1)
        result_mesh2 = _run_mesh_analysis(project, mesh_level=2)
        
        assert result_mesh1.success, f"Mesh 1 failed: {result_mesh1.message}"
        assert result_mesh2.success, f"Mesh 2 failed: {result_mesh2.message}"
        
        avg1 = result_mesh1.interior_avg_kn
        avg2 = result_mesh2.interior_avg_kn
        
        if avg1 == 0:
            pytest.skip("Interior average is zero, cannot compute relative change")
        
        relative_change = abs(avg2 - avg1) / avg1
        
        assert relative_change <= 0.05, (
            f"Interior stability FAILED: "
            f"mesh1_avg={avg1:.3f} kN, "
            f"mesh2_avg={avg2:.3f} kN, "
            f"change={relative_change*100:.2f}% > 5%"
        )

    def test_mesh_refinement_all_groups_combined(self) -> None:
        """Combined test: all groups should be stable under mesh refinement.
        
        This is the main mesh refinement stability test that checks:
        1. Both analyses succeed
        2. Equilibrium holds for both (<= 0.5% error)
        3. All group averages stable (<= 5% change)
        """
        _skip_if_no_opensees()
        
        project = build_benchmark_project_2x3()
        expected_load_kn = calc_sdl_total_load(project)
        
        result_mesh1 = _run_mesh_analysis(project, mesh_level=1, emit_evidence=True)
        result_mesh2 = _run_mesh_analysis(project, mesh_level=2, emit_evidence=True)
        
        assert result_mesh1.success, f"Mesh 1 analysis FAILED: {result_mesh1.message}"
        assert result_mesh2.success, f"Mesh 2 analysis FAILED: {result_mesh2.message}"
        
        for mesh_result in [result_mesh1, result_mesh2]:
            error = abs(abs(mesh_result.total_reaction_kn) - expected_load_kn) / expected_load_kn
            assert error <= 0.005, (
                f"Mesh {mesh_result.mesh_level} equilibrium FAILED: "
                f"error={error*100:.2f}% > 0.5%"
            )
        
        groups = [
            ("corner", result_mesh1.corner_avg_kn, result_mesh2.corner_avg_kn),
            ("edge", result_mesh1.edge_avg_kn, result_mesh2.edge_avg_kn),
            ("interior", result_mesh1.interior_avg_kn, result_mesh2.interior_avg_kn),
        ]
        
        for group_name, avg1, avg2 in groups:
            if avg1 == 0:
                continue
            
            relative_change = abs(avg2 - avg1) / avg1
            
            assert relative_change <= 0.05, (
                f"{group_name.capitalize()} stability FAILED: "
                f"mesh1={avg1:.3f} kN, mesh2={avg2:.3f} kN, "
                f"change={relative_change*100:.2f}% > 5%"
            )

        assert result_mesh1.evidence_path is not None
        assert result_mesh2.evidence_path is not None
        assert result_mesh1.evidence_path.name == "2x3_SDL_mesh1.json"
        assert result_mesh2.evidence_path.name == "2x3_SDL_mesh2.json"
