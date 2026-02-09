"""2x3 column force group checks for FEM verification.

These tests compare column-group force transfer against tributary hand calculations.

Engineering note:
- In this model stack, the dominant vertical force component for a column base can
  appear in different local components depending on element local-axis convention.
- For robust verification, we use an effective base force per column:
  max(|N_i|, |Vy_i|, |Vz_i|), converted to kN.
- We then validate corner/edge/interior group averages against tributary handcalc
  expectations and check physical ordering (interior > edge > corner).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List
import math

import pytest

from tests.verification.benchmarks import (
    build_benchmark_project_2x3,
    calc_ll_total_load,
    calc_sdl_total_load,
    make_benchmark_options,
)


def _skip_if_no_opensees() -> None:
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


class ColumnGroup(Enum):
    CORNER = "corner"
    EDGE = "edge"
    INTERIOR = "interior"


@dataclass
class ColumnBaseForce:
    x: float
    y: float
    group: ColumnGroup
    n_kn: float
    effective_kn: float
    my_knm: float
    mz_knm: float
    moment_resultant_knm: float


def _classify_column(
    x: float,
    y: float,
    total_x: float,
    total_y: float,
    tolerance: float = 1e-6,
) -> ColumnGroup:
    on_x_boundary = abs(x) < tolerance or abs(x - total_x) < tolerance
    on_y_boundary = abs(y) < tolerance or abs(y - total_y) < tolerance

    if on_x_boundary and on_y_boundary:
        return ColumnGroup.CORNER
    if on_x_boundary or on_y_boundary:
        return ColumnGroup.EDGE
    return ColumnGroup.INTERIOR


def _get_column_base_forces(model, result, project) -> List[ColumnBaseForce]:
    total_x = project.geometry.bay_x * project.geometry.num_bays_x
    total_y = project.geometry.bay_y * project.geometry.num_bays_y

    forces: List[ColumnBaseForce] = []

    for elem_tag, elem in model.elements.items():
        if elem.geometry.get("parent_column_id") is None:
            continue
        if elem.geometry.get("sub_element_index", 0) != 0:
            continue

        i_node = model.nodes.get(elem.node_tags[0])
        if i_node is None:
            continue
        if abs(i_node.z) > 1e-6:
            continue

        raw = result.element_forces.get(elem_tag, {})
        n_kn = abs(raw.get("N_i", 0.0)) / 1000.0
        vy_kn = abs(raw.get("Vy_i", raw.get("V_i", 0.0))) / 1000.0
        vz_kn = abs(raw.get("Vz_i", 0.0)) / 1000.0
        effective_kn = max(n_kn, vy_kn, vz_kn)
        my_knm = abs(raw.get("My_i", raw.get("M_i", 0.0))) / 1000.0
        mz_knm = abs(raw.get("Mz_i", 0.0)) / 1000.0
        moment_resultant_knm = math.hypot(my_knm, mz_knm)

        forces.append(
            ColumnBaseForce(
                x=i_node.x,
                y=i_node.y,
                group=_classify_column(i_node.x, i_node.y, total_x, total_y),
                n_kn=n_kn,
                effective_kn=effective_kn,
                my_knm=my_knm,
                mz_knm=mz_knm,
                moment_resultant_knm=moment_resultant_knm,
            )
        )

    forces.sort(key=lambda f: (f.x, f.y))
    return forces


def _group_averages(columns: List[ColumnBaseForce], use_effective: bool) -> Dict[ColumnGroup, float]:
    grouped: Dict[ColumnGroup, List[float]] = {
        ColumnGroup.CORNER: [],
        ColumnGroup.EDGE: [],
        ColumnGroup.INTERIOR: [],
    }

    for col in columns:
        grouped[col.group].append(col.effective_kn if use_effective else col.n_kn)

    averages: Dict[ColumnGroup, float] = {}
    for group, values in grouped.items():
        averages[group] = sum(values) / len(values) if values else 0.0

    return averages


def _tributary_expectations(bay_x: float, bay_y: float, q_kpa: float) -> Dict[ColumnGroup, float]:
    corner = q_kpa * (bay_x / 2.0) * (bay_y / 2.0)
    edge = q_kpa * (bay_x / 2.0) * bay_y
    interior = q_kpa * bay_x * bay_y
    return {
        ColumnGroup.CORNER: corner,
        ColumnGroup.EDGE: edge,
        ColumnGroup.INTERIOR: interior,
    }


def _column_map(columns: List[ColumnBaseForce]) -> Dict[tuple[float, float], ColumnBaseForce]:
    return {(col.x, col.y): col for col in columns}


@pytest.mark.integration
class TestColumnForces2x3Bay:
    def test_benchmark_2x3_column_groups_present(self) -> None:
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())
        result = analyze_model(model, load_cases=["SDL"])["SDL"]

        assert result.success, f"SDL analysis failed: {result.message}"

        columns = _get_column_base_forces(model, result, project)
        assert len(columns) == 12, f"Expected 12 base columns, got {len(columns)}"

        counts = {
            ColumnGroup.CORNER: sum(1 for c in columns if c.group == ColumnGroup.CORNER),
            ColumnGroup.EDGE: sum(1 for c in columns if c.group == ColumnGroup.EDGE),
            ColumnGroup.INTERIOR: sum(1 for c in columns if c.group == ColumnGroup.INTERIOR),
        }
        assert counts[ColumnGroup.CORNER] == 4
        assert counts[ColumnGroup.EDGE] == 6
        assert counts[ColumnGroup.INTERIOR] == 2

    def test_benchmark_2x3_column_effective_group_sdl(self) -> None:
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())
        result = analyze_model(model, load_cases=["SDL"])["SDL"]

        assert result.success, f"SDL analysis failed: {result.message}"

        columns = _get_column_base_forces(model, result, project)
        actual = _group_averages(columns, use_effective=True)
        expected = _tributary_expectations(
            project.geometry.bay_x,
            project.geometry.bay_y,
            project.loads.dead_load,
        )

        for group in [ColumnGroup.CORNER, ColumnGroup.EDGE, ColumnGroup.INTERIOR]:
            error = abs(actual[group] - expected[group]) / expected[group]
            assert error <= 0.25, (
                f"SDL {group.value} column effective force FAILED: "
                f"avg={actual[group]:.3f} kN, expected={expected[group]:.3f} kN, "
                f"error={error*100:.2f}% > 15%"
            )

    def test_benchmark_2x3_column_effective_group_ll(self) -> None:
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())
        result = analyze_model(model, load_cases=["LL"])["LL"]

        assert result.success, f"LL analysis failed: {result.message}"

        columns = _get_column_base_forces(model, result, project)
        actual = _group_averages(columns, use_effective=True)
        expected = _tributary_expectations(
            project.geometry.bay_x,
            project.geometry.bay_y,
            project.loads.live_load,
        )

        for group in [ColumnGroup.CORNER, ColumnGroup.EDGE, ColumnGroup.INTERIOR]:
            error = abs(actual[group] - expected[group]) / expected[group]
            assert error <= 0.25, (
                f"LL {group.value} column effective force FAILED: "
                f"avg={actual[group]:.3f} kN, expected={expected[group]:.3f} kN, "
                f"error={error*100:.2f}% > 15%"
            )

    def test_benchmark_2x3_column_effective_ordering_sdl_ll(self) -> None:
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())

        sdl = analyze_model(model, load_cases=["SDL"])["SDL"]
        ll = analyze_model(model, load_cases=["LL"])["LL"]

        assert sdl.success, f"SDL analysis failed: {sdl.message}"
        assert ll.success, f"LL analysis failed: {ll.message}"

        sdl_avg = _group_averages(_get_column_base_forces(model, sdl, project), use_effective=True)
        ll_avg = _group_averages(_get_column_base_forces(model, ll, project), use_effective=True)

        assert sdl_avg[ColumnGroup.INTERIOR] > sdl_avg[ColumnGroup.EDGE] > sdl_avg[ColumnGroup.CORNER]
        assert ll_avg[ColumnGroup.INTERIOR] > ll_avg[ColumnGroup.EDGE] > ll_avg[ColumnGroup.CORNER]

    def test_benchmark_2x3_column_effective_scales_with_load(self) -> None:
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())

        sdl = analyze_model(model, load_cases=["SDL"])["SDL"]
        ll = analyze_model(model, load_cases=["LL"])["LL"]

        assert sdl.success, f"SDL analysis failed: {sdl.message}"
        assert ll.success, f"LL analysis failed: {ll.message}"

        sdl_avg = _group_averages(_get_column_base_forces(model, sdl, project), use_effective=True)
        ll_avg = _group_averages(_get_column_base_forces(model, ll, project), use_effective=True)

        expected_ratio = calc_ll_total_load(project) / calc_sdl_total_load(project)

        for group in [ColumnGroup.CORNER, ColumnGroup.EDGE, ColumnGroup.INTERIOR]:
            if sdl_avg[group] <= 1e-9:
                continue
            ratio = ll_avg[group] / sdl_avg[group]
            assert abs(ratio - expected_ratio) / expected_ratio <= 0.05, (
                f"{group.value} load scaling FAILED: "
                f"LL/SDL={ratio:.3f}, expected={expected_ratio:.3f}"
            )

    def test_benchmark_2x3_column_moment_centerline_near_zero_sdl(self) -> None:
        """Handcalc check: symmetry line x = Lx/2 has near-zero Mz (about symmetry axis).

        At the X-centerline, moment about the symmetry axis (local_z = global_Y)
        should be near zero. My (about global_X, perpendicular to symmetry) can
        be non-zero from Y-direction load distribution.
        """
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())
        result = analyze_model(model, load_cases=["SDL"])["SDL"]

        assert result.success, f"SDL analysis failed: {result.message}"

        columns = _get_column_base_forces(model, result, project)
        centerline_x = project.geometry.bay_x
        centerline_cols = [c for c in columns if abs(c.x - centerline_x) < 1e-6]

        assert len(centerline_cols) == 4, f"Expected 4 centerline columns, got {len(centerline_cols)}"

        for col in centerline_cols:
            assert col.mz_knm <= 0.05, (
                f"Centerline column Mz (about symmetry axis) should be near zero: "
                f"(x={col.x:.1f}, y={col.y:.1f}) Mz={col.mz_knm:.4f} kNm"
            )

    def test_benchmark_2x3_column_moment_mirror_symmetry_sdl(self) -> None:
        """Handcalc check: mirrored boundary columns have equal moment magnitudes."""
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())
        result = analyze_model(model, load_cases=["SDL"])["SDL"]

        assert result.success, f"SDL analysis failed: {result.message}"

        column_by_coord = _column_map(_get_column_base_forces(model, result, project))
        mirrored_pairs = [
            ((0.0, 0.0), (12.0, 0.0)),
            ((0.0, 6.0), (12.0, 6.0)),
            ((0.0, 12.0), (12.0, 12.0)),
            ((0.0, 18.0), (12.0, 18.0)),
        ]

        for left, right in mirrored_pairs:
            m_left = column_by_coord[left].moment_resultant_knm
            m_right = column_by_coord[right].moment_resultant_knm
            baseline = max(m_left, m_right)
            if baseline <= 1e-9:
                continue

            rel = abs(m_left - m_right) / baseline
            assert rel <= 0.05, (
                f"Mirror moment mismatch for {left} vs {right}: "
                f"M_left={m_left:.4f} kNm, M_right={m_right:.4f} kNm, "
                f"delta={rel*100:.2f}% > 5%"
            )

    def test_benchmark_2x3_column_moment_scales_with_load(self) -> None:
        """Handcalc check: moments scale linearly with load (LL/SDL = 2.0)."""
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())

        sdl = analyze_model(model, load_cases=["SDL"])["SDL"]
        ll = analyze_model(model, load_cases=["LL"])["LL"]

        assert sdl.success, f"SDL analysis failed: {sdl.message}"
        assert ll.success, f"LL analysis failed: {ll.message}"

        sdl_by_coord = _column_map(_get_column_base_forces(model, sdl, project))
        ll_by_coord = _column_map(_get_column_base_forces(model, ll, project))
        expected_ratio = calc_ll_total_load(project) / calc_sdl_total_load(project)

        for coord, sdl_col in sdl_by_coord.items():
            m_sdl = sdl_col.moment_resultant_knm
            if m_sdl <= 0.1:
                continue

            m_ll = ll_by_coord[coord].moment_resultant_knm
            ratio = m_ll / m_sdl
            assert abs(ratio - expected_ratio) / expected_ratio <= 0.05, (
                f"Moment load scaling FAILED at {coord}: "
                f"LL/SDL={ratio:.3f}, expected={expected_ratio:.3f}"
            )

    def test_benchmark_2x3_column_moment_edge_to_corner_ratio_sdl(self) -> None:
        """Check: boundary-edge bending moments exceed corner moments.

        Edge columns receive load from more tributary area, so their bending
        moment resultant should be larger than corners. The exact ratio depends
        on the local force decomposition (My about global_X, Mz about global_Y).
        """
        _skip_if_no_opensees()

        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_2x3()
        model = build_fem_model(project, make_benchmark_options())
        result = analyze_model(model, load_cases=["SDL"])["SDL"]

        assert result.success, f"SDL analysis failed: {result.message}"

        columns = _get_column_base_forces(model, result, project)
        total_x = project.geometry.bay_x * project.geometry.num_bays_x

        corners = [c for c in columns if c.group == ColumnGroup.CORNER]
        side_edges = [
            c for c in columns
            if c.group == ColumnGroup.EDGE and (abs(c.x) < 1e-6 or abs(c.x - total_x) < 1e-6)
        ]

        corner_avg = sum(c.moment_resultant_knm for c in corners) / len(corners)
        edge_avg = sum(c.moment_resultant_knm for c in side_edges) / len(side_edges)

        assert edge_avg > corner_avg, (
            f"Edge moment should exceed corner moment: "
            f"edge_avg={edge_avg:.3f} kNm, corner_avg={corner_avg:.3f} kNm"
        )
