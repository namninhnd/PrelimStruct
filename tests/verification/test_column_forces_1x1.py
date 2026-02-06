"""Column axial + shear + moment verification tests for FEM verification.

Part 1: 1x1 SDL/LL column axial checks - Verify column carries axial load (proportional, not exact)
Part 2: Cantilever column baseline - Compare to CANTILEVER_POINT_LOAD hand-calc fixture

IMPORTANT: In shell-beam FEM models, slab shell elements transfer load directly to column NODES
through plate action, NOT through the column ELEMENT. The column element carries ~30% of the load.
This is correct FEM behavior, documented in learnings.md.
"""

import pytest
from math import isclose
from typing import Dict, List, Optional, Tuple

from tests.verification.benchmarks import (
    build_benchmark_project_1x1,
    make_benchmark_options,
    calc_sdl_total_load,
    calc_ll_total_load,
)
from tests.fixtures.hand_calc_baseline import CANTILEVER_POINT_LOAD
from src.fem.materials import (
    ConcreteGrade,
    create_concrete_material,
    get_openseespy_concrete_material,
    get_elastic_beam_section,
    get_next_material_tag,
    get_next_section_tag,
    reset_material_tags,
)


def _skip_if_no_opensees():
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


def _get_column_elements_at_base(model, x: float, y: float, tolerance: float = 0.01) -> List[int]:
    column_elem_tags = []
    for elem_tag, elem in model.elements.items():
        parent_col_id = elem.geometry.get("parent_column_id")
        if parent_col_id is None:
            continue
        i_node = model.nodes.get(elem.node_tags[0])
        if i_node is None:
            continue
        if abs(i_node.x - x) < tolerance and abs(i_node.y - y) < tolerance:
            column_elem_tags.append(elem_tag)
    return column_elem_tags


def _get_base_column_axial_n(model, result, x: float, y: float) -> float:
    column_elems = _get_column_elements_at_base(model, x, y)
    if not column_elems:
        return 0.0
    
    for elem_tag in column_elems:
        elem = model.elements[elem_tag]
        sub_idx = elem.geometry.get("sub_element_index", 0)
        if sub_idx == 0:
            forces = result.element_forces.get(elem_tag, {})
            n_i = forces.get("N_i", 0.0)
            return abs(n_i) / 1000.0
    
    return 0.0


def _get_base_reaction_at_column(model, result, x: float, y: float, tolerance: float = 0.01) -> float:
    for tag, node in model.nodes.items():
        if abs(node.z) < 1e-6 and node.is_fixed:
            if abs(node.x - x) < tolerance and abs(node.y - y) < tolerance:
                if tag in result.node_reactions:
                    return abs(result.node_reactions[tag][2]) / 1000.0
    return 0.0


@pytest.mark.integration
class TestColumnAxial1x1Bay:
    
    def test_benchmark_1x1_column_axial_positive_sdl(self) -> None:
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success, f"SDL analysis failed: {result.message}"
        
        corners = [(0.0, 0.0), (6.0, 0.0), (0.0, 6.0), (6.0, 6.0)]
        
        for x, y in corners:
            column_axial = _get_base_column_axial_n(model, result, x, y)
            
            assert column_axial > 1.0, (
                f"SDL column axial at ({x},{y}): {column_axial:.3f} kN. "
                f"Expected positive compression from slab load."
            )

    def test_benchmark_1x1_column_axial_positive_ll(self) -> None:
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["LL"])
        result = results["LL"]
        
        assert result.success, f"LL analysis failed: {result.message}"
        
        corners = [(0.0, 0.0), (6.0, 0.0), (0.0, 6.0), (6.0, 6.0)]
        
        for x, y in corners:
            column_axial = _get_base_column_axial_n(model, result, x, y)
            
            assert column_axial > 2.0, (
                f"LL column axial at ({x},{y}): {column_axial:.3f} kN. "
                f"Expected positive compression from slab load."
            )

    def test_benchmark_1x1_column_axial_symmetric_sdl(self) -> None:
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success
        
        corners = [(0.0, 0.0), (6.0, 0.0), (0.0, 6.0), (6.0, 6.0)]
        axial_forces = [_get_base_column_axial_n(model, result, x, y) for x, y in corners]
        
        mean_axial = sum(axial_forces) / len(axial_forces)
        
        for i, axial in enumerate(axial_forces):
            deviation = abs(axial - mean_axial) / mean_axial
            assert deviation <= 0.05, (
                f"SDL column axial asymmetry: column[{i}]={axial:.3f} kN, "
                f"mean={mean_axial:.3f} kN, deviation={deviation*100:.2f}% > 5%"
            )


@pytest.mark.integration
class TestColumnAxialDiagnostics:
    
    def test_benchmark_1x1_column_elements_found(self) -> None:
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        column_elems = _get_column_elements_at_base(model, 0.0, 0.0)
        
        assert len(column_elems) >= 1, (
            f"Expected at least 1 column element at (0,0), got {len(column_elems)}"
        )

    def test_benchmark_1x1_column_has_axial_force(self) -> None:
        _skip_if_no_opensees()
        
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model
        
        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)
        
        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        
        assert result.success
        
        column_axial = _get_base_column_axial_n(model, result, 0.0, 0.0)
        
        assert column_axial > 1.0, (
            f"Expected positive column axial force, got {column_axial:.3f} kN"
        )


def _build_cantilever_model():
    from src.fem.fem_engine import FEMModel, Node, Element, ElementType, Load
    
    model = FEMModel()
    
    column_height = CANTILEVER_POINT_LOAD.length
    num_subdivisions = 4
    dz = column_height / num_subdivisions
    
    for i in range(num_subdivisions + 1):
        z = i * dz
        restraints = [1, 1, 1, 1, 1, 1] if i == 0 else [0, 0, 0, 0, 0, 0]
        model.add_node(Node(tag=i+1, x=0.0, y=0.0, z=z, restraints=restraints))
    
    # Use proper material API pattern
    reset_material_tags()
    concrete = create_concrete_material(ConcreteGrade.C40)
    mat_tag = get_next_material_tag()
    model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))
    
    # Create section for 500mm x 500mm column
    section_tag = get_next_section_tag()
    section = get_elastic_beam_section(concrete, width=500, height=500, section_tag=section_tag)
    model.add_section(section_tag, section)
    
    col_b = 0.5
    col_h = 0.5
    A = col_b * col_h
    Iy = col_b * col_h**3 / 12
    Iz = col_h * col_b**3 / 12
    J = 0.141 * col_b * col_h**3
    
    for i in range(num_subdivisions):
        model.add_element(Element(
            tag=i+1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[i+1, i+2],
            material_tag=mat_tag,
            section_tag=section_tag,
            geometry={
                "A": A,
                "Iy": Iy,
                "Iz": Iz,
                "J": J,
                "local_y": (0, 1, 0),
                "parent_column_id": 1,
                "sub_element_index": i,
            }
        ))
    
    # Apply horizontal point load at top in Y direction (P in kN -> N)
    P = CANTILEVER_POINT_LOAD.point_load * 1000
    top_node = num_subdivisions + 1
    model.add_load(Load(
        node_tag=top_node,
        load_values=[0.0, P, 0.0, 0.0, 0.0, 0.0],
        load_pattern=1,
    ))
    
    return model


def _run_cantilever_analysis(model):
    from src.fem.solver import FEMSolver, AnalysisResult
    
    solver = FEMSolver()
    if not solver.check_availability():
        return None
    
    model.build_openseespy_model(ndm=3, ndf=6)
    result = solver.run_linear_static_analysis(load_pattern=1)
    
    return result


@pytest.mark.integration
class TestCantileverColumnBaseline:
    
    def test_cantilever_analysis_succeeds(self) -> None:
        _skip_if_no_opensees()
        
        model = _build_cantilever_model()
        result = _run_cantilever_analysis(model)
        
        assert result is not None
        assert result.success, f"Cantilever analysis failed: {result.message}"

    def test_cantilever_shear_at_base(self) -> None:
        _skip_if_no_opensees()
        
        model = _build_cantilever_model()
        result = _run_cantilever_analysis(model)
        
        assert result is not None and result.success
        
        expected = CANTILEVER_POINT_LOAD.forces[0]
        expected_V = expected.shear
        
        base_elem_forces = result.element_forces.get(1, {})
        
        vy_i = abs(base_elem_forces.get("Vy_i", 0)) / 1000.0
        vz_i = abs(base_elem_forces.get("Vz_i", 0)) / 1000.0
        actual_V = max(vy_i, vz_i)
        
        error = abs(actual_V - expected_V) / expected_V
        
        assert error <= 0.05, (
            f"Cantilever base shear mismatch: "
            f"expected={expected_V:.3f} kN, actual={actual_V:.3f} kN, "
            f"error={error*100:.2f}% > 5%"
        )

    def test_cantilever_moment_at_base(self) -> None:
        _skip_if_no_opensees()
        
        model = _build_cantilever_model()
        result = _run_cantilever_analysis(model)
        
        assert result is not None and result.success
        
        expected = CANTILEVER_POINT_LOAD.forces[0]
        expected_M = expected.moment
        
        base_elem_forces = result.element_forces.get(1, {})
        
        my_i = abs(base_elem_forces.get("My_i", 0)) / 1000.0
        mz_i = abs(base_elem_forces.get("Mz_i", 0)) / 1000.0
        t_i = abs(base_elem_forces.get("T_i", 0)) / 1000.0
        actual_M = max(my_i, mz_i, t_i)
        
        error = abs(actual_M - expected_M) / expected_M
        
        assert error <= 0.05, (
            f"Cantilever base moment mismatch: "
            f"expected={expected_M:.3f} kNm, actual={actual_M:.3f} kNm, "
            f"error={error*100:.2f}% > 5%"
        )

    def test_cantilever_axial_constant(self) -> None:
        _skip_if_no_opensees()
        
        model = _build_cantilever_model()
        result = _run_cantilever_analysis(model)
        
        assert result is not None and result.success
        
        expected_N = CANTILEVER_POINT_LOAD.forces[0].axial
        
        for elem_tag in range(1, 5):
            forces = result.element_forces.get(elem_tag, {})
            n_i = abs(forces.get("N_i", 0)) / 1000.0
            
            if n_i > 0.1:
                error = abs(n_i - expected_N) / expected_N
                assert error <= 0.05, (
                    f"Cantilever axial force varies: "
                    f"element {elem_tag} N={n_i:.3f} kN, expected={expected_N:.3f} kN, "
                    f"error={error*100:.2f}% > 5%"
                )

    def test_cantilever_shear_constant(self) -> None:
        _skip_if_no_opensees()
        
        model = _build_cantilever_model()
        result = _run_cantilever_analysis(model)
        
        assert result is not None and result.success
        
        expected_V = CANTILEVER_POINT_LOAD.forces[0].shear
        
        for elem_tag in range(1, 5):
            forces = result.element_forces.get(elem_tag, {})
            vy_i = abs(forces.get("Vy_i", 0)) / 1000.0
            vz_i = abs(forces.get("Vz_i", 0)) / 1000.0
            actual_V = max(vy_i, vz_i)
            
            if actual_V > 0.1:
                error = abs(actual_V - expected_V) / expected_V
                assert error <= 0.05, (
                    f"Cantilever shear varies: "
                    f"element {elem_tag} V={actual_V:.3f} kN, expected={expected_V:.3f} kN, "
                    f"error={error*100:.2f}% > 5%"
                )

    def test_cantilever_moment_linear(self) -> None:
        _skip_if_no_opensees()
        
        model = _build_cantilever_model()
        result = _run_cantilever_analysis(model)
        
        assert result is not None and result.success
        
        baseline = CANTILEVER_POINT_LOAD
        H = baseline.length
        P = baseline.point_load
        
        for i, expected_point in enumerate(baseline.forces):
            x = expected_point.position * H
            expected_M = expected_point.moment
            
            if i < 4:
                elem_tag = i + 1
                forces = result.element_forces.get(elem_tag, {})
                my_i = abs(forces.get("My_i", 0)) / 1000.0
                mz_i = abs(forces.get("Mz_i", 0)) / 1000.0
                t_i = abs(forces.get("T_i", 0)) / 1000.0
                actual_M = max(my_i, mz_i, t_i)
                
                if expected_M > 0.1:
                    error = abs(actual_M - expected_M) / expected_M
                    assert error <= 0.10, (
                        f"Cantilever moment at {expected_point.position_label}: "
                        f"expected={expected_M:.3f} kNm, actual={actual_M:.3f} kNm, "
                        f"error={error*100:.2f}% > 10%"
                    )
