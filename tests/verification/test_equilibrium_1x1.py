"""Equilibrium hard-gate tests for 1x1 bay benchmark model.

These tests verify that FEM analysis satisfies vertical equilibrium:
    Sum of base reactions (Fz) = Total applied load

For gravity loads (downward = negative), reactions are positive (upward).
This is a physics-based sanity check that catches modeling errors.
"""

import pytest
from math import isclose

from tests.verification.benchmarks import (
    build_benchmark_project_1x1,
    make_benchmark_options,
    calc_sdl_total_load,
    calc_ll_total_load,
    calc_dl_total_load,
)
from tests.verification.evidence_capture import write_benchmark_evidence


def _skip_if_no_opensees():
    """Skip test if OpenSeesPy is not available."""
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


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


@pytest.mark.integration
class TestEquilibrium1x1Bay:
    """Equilibrium verification tests for 1x1 bay benchmark."""

    def test_benchmark_1x1_equilibrium_sdl(self) -> None:
        """SDL equilibrium: sum(base Fz) == SDL total load.
        
        SDL = Superimposed Dead Load applied to slab surfaces.
        Expected: SDL_kPa * plan_area (kN)
        Tolerance: 0.5% relative error
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"SDL analysis failed: {result.message}"
        
        expected_load_kn = calc_sdl_total_load(project)
        actual_reaction_kn = _get_base_reaction_fz_kn(model, result)

        relative_error = abs(abs(actual_reaction_kn) - expected_load_kn) / expected_load_kn

        evidence_path = write_benchmark_evidence(
            model_name="1x1",
            load_case="SDL",
            project=project,
            model=model,
            result=result,
            expected_sum_fz_kn=expected_load_kn,
            actual_sum_fz_kn=actual_reaction_kn,
            slab_elements_per_bay=options.slab_elements_per_bay,
        )

        assert evidence_path.name == "1x1_SDL.json"

        assert relative_error <= 0.005, (
            f"SDL equilibrium FAILED: "
            f"expected={expected_load_kn:.3f} kN, "
            f"actual_Fz={actual_reaction_kn:.3f} kN, "
            f"relative_error={relative_error*100:.2f}% > 0.5%"
        )

    def test_benchmark_1x1_equilibrium_ll(self) -> None:
        """LL equilibrium: sum(base Fz) == LL total load.
        
        LL = Live Load applied to slab surfaces.
        Expected: LL_kPa * plan_area (kN)
        Tolerance: 0.5% relative error
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["LL"])
        result = results["LL"]
        
        assert result.success, f"LL analysis failed: {result.message}"
        
        expected_load_kn = calc_ll_total_load(project)
        actual_reaction_kn = _get_base_reaction_fz_kn(model, result)

        relative_error = abs(abs(actual_reaction_kn) - expected_load_kn) / expected_load_kn

        evidence_path = write_benchmark_evidence(
            model_name="1x1",
            load_case="LL",
            project=project,
            model=model,
            result=result,
            expected_sum_fz_kn=expected_load_kn,
            actual_sum_fz_kn=actual_reaction_kn,
            slab_elements_per_bay=options.slab_elements_per_bay,
        )

        assert evidence_path.name == "1x1_LL.json"

        assert relative_error <= 0.005, (
            f"LL equilibrium FAILED: "
            f"expected={expected_load_kn:.3f} kN, "
            f"actual_Fz={actual_reaction_kn:.3f} kN, "
            f"relative_error={relative_error*100:.2f}% > 0.5%"
        )

    def test_benchmark_1x1_equilibrium_dl(self) -> None:
        """DL equilibrium: sum(base Fz) == DL total load.
        
        DL = Dead Load (slab + beam + column self-weight).
        Expected: calc_dl_total_load(project) (kN)
        Tolerance: 1.0% relative error (higher due to self-weight complexity)
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["DL"])
        result = results["DL"]
        
        assert result.success, f"DL analysis failed: {result.message}"
        
        expected_load_kn = calc_dl_total_load(project, slab_thickness_m=0.150)
        actual_reaction_kn = _get_base_reaction_fz_kn(model, result)

        relative_error = abs(abs(actual_reaction_kn) - expected_load_kn) / expected_load_kn

        evidence_path = write_benchmark_evidence(
            model_name="1x1",
            load_case="DL",
            project=project,
            model=model,
            result=result,
            expected_sum_fz_kn=expected_load_kn,
            actual_sum_fz_kn=actual_reaction_kn,
            slab_elements_per_bay=options.slab_elements_per_bay,
        )

        assert evidence_path.name == "1x1_DL.json"

        assert relative_error <= 0.01, (
            f"DL equilibrium FAILED: "
            f"expected={expected_load_kn:.3f} kN, "
            f"actual_Fz={actual_reaction_kn:.3f} kN, "
            f"relative_error={relative_error*100:.2f}% > 1.0%"
        )


@pytest.mark.integration
class TestEquilibriumDiagnostics:
    """Diagnostic utilities for equilibrium debugging."""

    def test_benchmark_1x1_base_nodes_identified(self) -> None:
        """Verify base nodes are correctly identified for reaction extraction."""
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        base_nodes = [
            tag for tag, node in model.nodes.items()
            if abs(node.z) < 1e-6 and node.is_fixed
        ]
        
        assert len(base_nodes) == 4, (
            f"Expected 4 base nodes for 1x1 bay, got {len(base_nodes)}"
        )
        
    def test_benchmark_1x1_reactions_non_empty(self) -> None:
        """Verify analysis produces non-empty reactions."""
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"Analysis failed: {result.message}"
        assert len(result.node_reactions) > 0, "No reactions extracted"
        
        # At least one reaction should have non-zero Fz
        has_nonzero_fz = any(
            abs(rxn[2]) > 1e-10 
            for rxn in result.node_reactions.values()
        )
        assert has_nonzero_fz, "All Fz reactions are zero - load not applied?"


def _get_base_reactions_list(model, result) -> list[float]:
    """Get list of Fz reactions for each base node.
    
    Base nodes are identified as: z == 0.0 AND is_fixed.
    Returns list of absolute Fz values in kN (positive magnitudes).
    
    Args:
        model: FEMModel with nodes
        result: AnalysisResult with node_reactions
        
    Returns:
        List of Fz reaction magnitudes in kN
    """
    reactions = []
    for tag, node in model.nodes.items():
        if abs(node.z) < 1e-6 and node.is_fixed:
            if tag in result.node_reactions:
                fz_n = result.node_reactions[tag][2]
                reactions.append(abs(fz_n) / 1000.0)  # Convert N to kN, take magnitude
    return reactions


@pytest.mark.integration
class TestDistribution1x1Bay:
    """Reaction distribution sanity tests for 1x1 bay benchmark.
    
    These tests verify that reactions at the 4 base nodes are:
    1. Symmetric: within 5% of the mean (symmetry check)
    2. Tributary-based: within 10% of expected q * (area/4)
    """

    def test_benchmark_1x1_distribution_sdl_symmetry(self) -> None:
        """SDL symmetry: all 4 base reactions within 5% of mean.
        
        For a symmetric 1x1 bay under uniform pressure, all 4 corner
        reactions should be equal due to symmetry.
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"SDL analysis failed: {result.message}"
        
        reactions = _get_base_reactions_list(model, result)
        
        assert len(reactions) == 4, (
            f"Expected 4 base reactions for 1x1 bay, got {len(reactions)}"
        )
        
        mean_reaction = sum(reactions) / len(reactions)
        
        for i, r in enumerate(reactions):
            deviation = abs(r - mean_reaction) / mean_reaction
            assert deviation <= 0.05, (
                f"SDL symmetry FAILED: reaction[{i}]={r:.3f} kN, "
                f"mean={mean_reaction:.3f} kN, "
                f"deviation={deviation*100:.2f}% > 5%"
            )

    def test_benchmark_1x1_distribution_sdl_tributary(self) -> None:
        """SDL tributary: each base reaction within 10% of expected (total/4).
        
        For a 1x1 bay, each corner column supports tributary area = plan_area/4.
        Expected reaction per column = q * (plan_area/4) = total_load/4.
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"SDL analysis failed: {result.message}"
        
        reactions = _get_base_reactions_list(model, result)
        
        assert len(reactions) == 4, (
            f"Expected 4 base reactions for 1x1 bay, got {len(reactions)}"
        )
        
        total_load_kn = calc_sdl_total_load(project)
        expected_per_column = total_load_kn / 4.0
        
        for i, r in enumerate(reactions):
            error = abs(r - expected_per_column) / expected_per_column
            assert error <= 0.10, (
                f"SDL tributary FAILED: reaction[{i}]={r:.3f} kN, "
                f"expected={expected_per_column:.3f} kN, "
                f"error={error*100:.2f}% > 10%"
            )

    def test_benchmark_1x1_distribution_ll_symmetry(self) -> None:
        """LL symmetry: all 4 base reactions within 5% of mean.
        
        For a symmetric 1x1 bay under uniform live load pressure,
        all 4 corner reactions should be equal due to symmetry.
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["LL"])
        result = results["LL"]
        
        assert result.success, f"LL analysis failed: {result.message}"
        
        reactions = _get_base_reactions_list(model, result)
        
        assert len(reactions) == 4, (
            f"Expected 4 base reactions for 1x1 bay, got {len(reactions)}"
        )
        
        mean_reaction = sum(reactions) / len(reactions)
        
        for i, r in enumerate(reactions):
            deviation = abs(r - mean_reaction) / mean_reaction
            assert deviation <= 0.05, (
                f"LL symmetry FAILED: reaction[{i}]={r:.3f} kN, "
                f"mean={mean_reaction:.3f} kN, "
                f"deviation={deviation*100:.2f}% > 5%"
            )

    def test_benchmark_1x1_distribution_ll_tributary(self) -> None:
        """LL tributary: each base reaction within 10% of expected (total/4).
        
        For a 1x1 bay, each corner column supports tributary area = plan_area/4.
        Expected reaction per column = q * (plan_area/4) = total_load/4.
        """
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["LL"])
        result = results["LL"]
        
        assert result.success, f"LL analysis failed: {result.message}"
        
        reactions = _get_base_reactions_list(model, result)
        
        assert len(reactions) == 4, (
            f"Expected 4 base reactions for 1x1 bay, got {len(reactions)}"
        )
        
        total_load_kn = calc_ll_total_load(project)
        expected_per_column = total_load_kn / 4.0
        
        for i, r in enumerate(reactions):
            error = abs(r - expected_per_column) / expected_per_column
            assert error <= 0.10, (
                f"LL tributary FAILED: reaction[{i}]={r:.3f} kN, "
                f"expected={expected_per_column:.3f} kN, "
                f"error={error*100:.2f}% > 10%"
            )
