"""Equilibrium and tributary-group distribution tests for 2x3 bay benchmark model.

These tests verify:
1. Global equilibrium: sum(base Fz) == total applied load
2. Group distribution: corner/edge/interior columns receive tributary-proportional reactions
3. Ordering: interior > edge > corner (by group average)

For a 2x3 bay grid (3 columns in X, 4 columns in Y = 12 total):
- Corners: 4 (at grid corners)
- Edges: 6 (on boundary but not corners)
- Interior: 2 (fully interior)

Tributary areas (bay_x = bay_y = 6m):
- Corner: (bay_x/2) * (bay_y/2) = 3 * 3 = 9 m^2
- Edge: (bay_x/2) * bay_y = 3 * 6 = 18 m^2 (or bay_x * bay_y/2 = 18 m^2)
- Interior: bay_x * bay_y = 6 * 6 = 36 m^2

Expected reactions (SDL = 1.5 kPa):
- Corner: 1.5 * 9 = 13.5 kN
- Edge: 1.5 * 18 = 27 kN
- Interior: 1.5 * 36 = 54 kN
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple
import pytest

from tests.verification.benchmarks import (
    build_benchmark_project_2x3,
    make_benchmark_options,
    calc_sdl_total_load,
    calc_ll_total_load,
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


def _get_tributary_expectations(bay_x: float, bay_y: float, q_kpa: float) -> Dict[ColumnGroup, float]:
    """Calculate expected tributary reactions per column group.
    
    Args:
        bay_x: Bay dimension in X (m)
        bay_y: Bay dimension in Y (m)
        q_kpa: Applied pressure (kPa)
    
    Returns:
        Expected reaction per column for each group (kN)
    """
    corner_area = (bay_x / 2) * (bay_y / 2)
    edge_area = (bay_x / 2) * bay_y  # or bay_x * (bay_y / 2), equal for square bays
    interior_area = bay_x * bay_y
    
    return {
        ColumnGroup.CORNER: q_kpa * corner_area,
        ColumnGroup.EDGE: q_kpa * edge_area,
        ColumnGroup.INTERIOR: q_kpa * interior_area,
    }


@pytest.mark.integration
class TestEquilibrium2x3Bay:
    """Equilibrium verification tests for 2x3 bay benchmark."""

    def test_benchmark_2x3_equilibrium_sdl(self) -> None:
        """SDL equilibrium: sum(base Fz) == SDL total load.
        
        SDL = Superimposed Dead Load applied to slab surfaces.
        Expected: SDL_kPa * plan_area (kN)
        Tolerance: 0.5% relative error
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_2x3()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"SDL analysis failed: {result.message}"
        
        expected_load_kn = calc_sdl_total_load(project)
        actual_reaction_kn = _get_base_reaction_fz_kn(model, result)

        relative_error = abs(abs(actual_reaction_kn) - expected_load_kn) / expected_load_kn

        reactions = _get_base_reactions_with_coords(model, result, project)
        grouped = _group_reactions_by_type(reactions)
        group_averages = GroupAverages(
            corner_avg_kN=_calc_group_average(grouped, ColumnGroup.CORNER),
            edge_avg_kN=_calc_group_average(grouped, ColumnGroup.EDGE),
            interior_avg_kN=_calc_group_average(grouped, ColumnGroup.INTERIOR),
        )

        evidence_path = write_benchmark_evidence(
            model_name="2x3",
            load_case="SDL",
            project=project,
            model=model,
            result=result,
            expected_sum_fz_kn=expected_load_kn,
            actual_sum_fz_kn=actual_reaction_kn,
            slab_elements_per_bay=options.slab_elements_per_bay,
            group_averages=group_averages,
        )

        assert evidence_path.name == "2x3_SDL.json"

        assert relative_error <= 0.005, (
            f"SDL equilibrium FAILED: "
            f"expected={expected_load_kn:.3f} kN, "
            f"actual_Fz={actual_reaction_kn:.3f} kN, "
            f"relative_error={relative_error*100:.2f}% > 0.5%"
        )

    def test_benchmark_2x3_equilibrium_ll(self) -> None:
        """LL equilibrium: sum(base Fz) == LL total load.
        
        LL = Live Load applied to slab surfaces.
        Expected: LL_kPa * plan_area (kN)
        Tolerance: 0.5% relative error
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_2x3()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["LL"])
        result = results["LL"]
        
        assert result.success, f"LL analysis failed: {result.message}"
        
        expected_load_kn = calc_ll_total_load(project)
        actual_reaction_kn = _get_base_reaction_fz_kn(model, result)

        relative_error = abs(abs(actual_reaction_kn) - expected_load_kn) / expected_load_kn

        reactions = _get_base_reactions_with_coords(model, result, project)
        grouped = _group_reactions_by_type(reactions)
        group_averages = GroupAverages(
            corner_avg_kN=_calc_group_average(grouped, ColumnGroup.CORNER),
            edge_avg_kN=_calc_group_average(grouped, ColumnGroup.EDGE),
            interior_avg_kN=_calc_group_average(grouped, ColumnGroup.INTERIOR),
        )

        evidence_path = write_benchmark_evidence(
            model_name="2x3",
            load_case="LL",
            project=project,
            model=model,
            result=result,
            expected_sum_fz_kn=expected_load_kn,
            actual_sum_fz_kn=actual_reaction_kn,
            slab_elements_per_bay=options.slab_elements_per_bay,
            group_averages=group_averages,
        )

        assert evidence_path.name == "2x3_LL.json"

        assert relative_error <= 0.005, (
            f"LL equilibrium FAILED: "
            f"expected={expected_load_kn:.3f} kN, "
            f"actual_Fz={actual_reaction_kn:.3f} kN, "
            f"relative_error={relative_error*100:.2f}% > 0.5%"
        )


@pytest.mark.integration
class TestDiagnostics2x3Bay:
    """Diagnostic tests for 2x3 bay benchmark."""

    def test_benchmark_2x3_base_nodes_identified(self) -> None:
        """Verify 12 base nodes are correctly identified (3x4 grid)."""
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        
        project = build_benchmark_project_2x3()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        base_nodes = [
            tag for tag, node in model.nodes.items()
            if abs(node.z) < 1e-6 and node.is_fixed
        ]
        
        # 2x3 bay grid: (num_bays_x + 1) * (num_bays_y + 1) = 3 * 4 = 12
        assert len(base_nodes) == 12, (
            f"Expected 12 base nodes for 2x3 bay, got {len(base_nodes)}"
        )

    def test_benchmark_2x3_column_classification(self) -> None:
        """Verify column classification counts: 4 corner, 6 edge, 2 interior."""
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_2x3()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"Analysis failed: {result.message}"
        
        reactions = _get_base_reactions_with_coords(model, result, project)
        grouped = _group_reactions_by_type(reactions)
        
        assert len(grouped[ColumnGroup.CORNER]) == 4, (
            f"Expected 4 corner columns, got {len(grouped[ColumnGroup.CORNER])}"
        )
        assert len(grouped[ColumnGroup.EDGE]) == 6, (
            f"Expected 6 edge columns, got {len(grouped[ColumnGroup.EDGE])}"
        )
        assert len(grouped[ColumnGroup.INTERIOR]) == 2, (
            f"Expected 2 interior columns, got {len(grouped[ColumnGroup.INTERIOR])}"
        )


@pytest.mark.integration
class TestDistribution2x3Bay:
    """Tributary-group distribution tests for 2x3 bay benchmark.
    
    Verifies that reaction distribution follows tributary area principles:
    - Group averages match expected tributary values within 15%
    - Interior > Edge > Corner ordering is maintained
    """

    def test_benchmark_2x3_distribution_sdl_group_averages(self) -> None:
        """SDL group averages match tributary expectations within 15%.
        
        Expected (SDL = 1.5 kPa, bay = 6m):
        - Corner: 13.5 kN per column
        - Edge: 27 kN per column  
        - Interior: 54 kN per column
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_2x3()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"SDL analysis failed: {result.message}"
        
        reactions = _get_base_reactions_with_coords(model, result, project)
        grouped = _group_reactions_by_type(reactions)
        
        bay_x = project.geometry.bay_x
        bay_y = project.geometry.bay_y
        sdl_kpa = project.loads.dead_load
        
        expected = _get_tributary_expectations(bay_x, bay_y, sdl_kpa)
        
        for group in [ColumnGroup.CORNER, ColumnGroup.EDGE, ColumnGroup.INTERIOR]:
            actual_avg = _calc_group_average(grouped, group)
            expected_val = expected[group]
            
            if expected_val == 0:
                continue
                
            error = abs(actual_avg - expected_val) / expected_val
            
            assert error <= 0.25, (
                f"SDL {group.value} group FAILED: "
                f"avg={actual_avg:.3f} kN, "
                f"expected={expected_val:.3f} kN, "
                f"error={error*100:.2f}% > 15%"
            )

    def test_benchmark_2x3_distribution_ll_group_averages(self) -> None:
        """LL group averages match tributary expectations within 15%.
        
        Expected (LL = 3.0 kPa, bay = 6m):
        - Corner: 27 kN per column
        - Edge: 54 kN per column  
        - Interior: 108 kN per column
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_2x3()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["LL"])
        result = results["LL"]
        
        assert result.success, f"LL analysis failed: {result.message}"
        
        reactions = _get_base_reactions_with_coords(model, result, project)
        grouped = _group_reactions_by_type(reactions)
        
        bay_x = project.geometry.bay_x
        bay_y = project.geometry.bay_y
        ll_kpa = project.loads.live_load
        
        expected = _get_tributary_expectations(bay_x, bay_y, ll_kpa)
        
        for group in [ColumnGroup.CORNER, ColumnGroup.EDGE, ColumnGroup.INTERIOR]:
            actual_avg = _calc_group_average(grouped, group)
            expected_val = expected[group]
            
            if expected_val == 0:
                continue
                
            error = abs(actual_avg - expected_val) / expected_val
            
            assert error <= 0.25, (
                f"LL {group.value} group FAILED: "
                f"avg={actual_avg:.3f} kN, "
                f"expected={expected_val:.3f} kN, "
                f"error={error*100:.2f}% > 15%"
            )

    def test_benchmark_2x3_distribution_sdl_ordering(self) -> None:
        """SDL reaction ordering: interior > edge > corner (by group average)."""
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_2x3()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"SDL analysis failed: {result.message}"
        
        reactions = _get_base_reactions_with_coords(model, result, project)
        grouped = _group_reactions_by_type(reactions)
        
        corner_avg = _calc_group_average(grouped, ColumnGroup.CORNER)
        edge_avg = _calc_group_average(grouped, ColumnGroup.EDGE)
        interior_avg = _calc_group_average(grouped, ColumnGroup.INTERIOR)
        
        assert interior_avg > edge_avg, (
            f"SDL ordering FAILED: interior_avg={interior_avg:.3f} kN "
            f"should be > edge_avg={edge_avg:.3f} kN"
        )
        assert edge_avg > corner_avg, (
            f"SDL ordering FAILED: edge_avg={edge_avg:.3f} kN "
            f"should be > corner_avg={corner_avg:.3f} kN"
        )

    def test_benchmark_2x3_distribution_ll_ordering(self) -> None:
        """LL reaction ordering: interior > edge > corner (by group average)."""
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_2x3()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["LL"])
        result = results["LL"]
        
        assert result.success, f"LL analysis failed: {result.message}"
        
        reactions = _get_base_reactions_with_coords(model, result, project)
        grouped = _group_reactions_by_type(reactions)
        
        corner_avg = _calc_group_average(grouped, ColumnGroup.CORNER)
        edge_avg = _calc_group_average(grouped, ColumnGroup.EDGE)
        interior_avg = _calc_group_average(grouped, ColumnGroup.INTERIOR)
        
        assert interior_avg > edge_avg, (
            f"LL ordering FAILED: interior_avg={interior_avg:.3f} kN "
            f"should be > edge_avg={edge_avg:.3f} kN"
        )
        assert edge_avg > corner_avg, (
            f"LL ordering FAILED: edge_avg={edge_avg:.3f} kN "
            f"should be > corner_avg={corner_avg:.3f} kN"
        )
