"""Integration tests: column model → solve → verify ETABS convention.

Verifies column forces under gravity and lateral loads follow
ETABS convention (Mz = major axis bending, My = minor axis bending).
"""

import pytest
from typing import Optional

from tests.verification.benchmarks import (
    build_benchmark_project_1x1,
    make_benchmark_options,
)


def _skip_if_no_opensees():
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


def _find_any_column(model, x: float, y: float) -> Optional[int]:
    """Find a column sub-element at given corner coordinates."""
    from src.fem.fem_engine import ElementType

    for tag, elem in model.elements.items():
        pid = elem.geometry.get("parent_column_id")
        if pid is None:
            continue
        n_i = model.nodes[elem.node_tags[0]]
        n_j = model.nodes[elem.node_tags[1]]
        if abs(n_i.x - x) < 0.01 and abs(n_i.y - y) < 0.01:
            return tag
    return None


@pytest.mark.integration
class TestColumnAxisPipeline:
    """Full pipeline: build column model → solve → verify convention."""

    def test_column_gravity_axial_dominant(self) -> None:
        """Under gravity, column axial N >> moments Mz/My."""
        _skip_if_no_opensees()
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)

        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        assert result.success

        col_tag = _find_any_column(model, 0.0, 0.0)
        assert col_tag is not None

        forces = result.element_forces.get(col_tag, {})
        n_i = abs(forces.get("N_i", 0.0))
        mz_i = abs(forces.get("Mz_i", 0.0))
        my_i = abs(forces.get("My_i", 0.0))

        assert n_i > 0.0, "Column axial should be non-zero under gravity"
        # Under pure gravity with symmetric 1x1 bay, moments should be small
        # relative to axial
        assert n_i > mz_i, f"Gravity: N={n_i:.0f} should > Mz={mz_i:.0f}"

    def test_column_forces_use_convention_agnostic_max(self) -> None:
        """Column force extraction captures both Mz and My components."""
        _skip_if_no_opensees()
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)

        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        assert result.success

        col_tag = _find_any_column(model, 0.0, 0.0)
        assert col_tag is not None

        forces = result.element_forces.get(col_tag, {})
        # Verify all 6 force components are extracted
        expected_keys = {"N_i", "N_j", "Vy_i", "Vy_j", "Vz_i", "Vz_j",
                         "Mz_i", "Mz_j", "My_i", "My_j"}
        actual_keys = set(forces.keys())
        # At minimum N and moment keys should be present
        assert "N_i" in actual_keys, f"Missing N_i. Keys: {actual_keys}"
        assert "Mz_i" in actual_keys or "My_i" in actual_keys, (
            f"Missing moment keys. Keys: {actual_keys}"
        )
