"""Integration tests: cross-element axis consistency.

Verifies that beams, columns, and coupling beams all follow
the same ETABS convention (Mz = major axis) and that vecxz
is direction-dependent for horizontal beams.
"""

import pytest

from tests.verification.benchmarks import (
    build_benchmark_project_1x1,
    make_benchmark_options,
)
from src.fem.fem_engine import ElementType


def _skip_if_no_opensees():
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


@pytest.mark.integration
class TestAxisConsistency:
    """Cross-element consistency tests for ETABS convention."""

    def test_vecxz_stored_on_beam_elements(self) -> None:
        """All beam elements should have vecxz in geometry dict."""
        _skip_if_no_opensees()
        from src.fem.model_builder import build_fem_model

        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)

        beam_count = 0
        for elem in model.elements.values():
            if elem.element_type in (ElementType.ELASTIC_BEAM, ElementType.SECONDARY_BEAM):
                vecxz = elem.geometry.get("vecxz")
                assert vecxz is not None, (
                    f"Beam element {elem.tag} missing vecxz in geometry"
                )
                beam_count += 1

        assert beam_count > 0, "No beam elements found"

    def test_x_beam_vecxz_is_0_neg1_0(self) -> None:
        """X-direction beam: vecxz = (dy/L, -dx/L, 0) = (0, -1, 0)."""
        _skip_if_no_opensees()
        from src.fem.model_builder import build_fem_model

        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)

        for elem in model.elements.values():
            if elem.element_type != ElementType.ELASTIC_BEAM:
                continue
            n_i = model.nodes[elem.node_tags[0]]
            n_j = model.nodes[elem.node_tags[1]]
            # X-direction beam: same y, same z, different x
            if abs(n_i.y - n_j.y) < 0.01 and abs(n_i.z - n_j.z) < 0.01 and abs(n_j.x - n_i.x) > 0.5:
                vecxz = elem.geometry.get("vecxz")
                assert vecxz is not None
                assert abs(vecxz[0]) < 0.01, f"X-beam vecxz[0] should be ~0, got {vecxz[0]}"
                assert abs(vecxz[1] - (-1.0)) < 0.01, f"X-beam vecxz[1] should be ~-1, got {vecxz[1]}"
                assert abs(vecxz[2]) < 0.01, f"X-beam vecxz[2] should be ~0, got {vecxz[2]}"
                return

        pytest.skip("No X-direction beam found")

    def test_y_beam_vecxz_is_1_0_0(self) -> None:
        """Y-direction beam: vecxz = (dy/L, -dx/L, 0) = (1, 0, 0)."""
        _skip_if_no_opensees()
        from src.fem.model_builder import build_fem_model

        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)

        for elem in model.elements.values():
            if elem.element_type != ElementType.ELASTIC_BEAM:
                continue
            n_i = model.nodes[elem.node_tags[0]]
            n_j = model.nodes[elem.node_tags[1]]
            # Y-direction beam: same x, same z, different y
            if abs(n_i.x - n_j.x) < 0.01 and abs(n_i.z - n_j.z) < 0.01 and abs(n_j.y - n_i.y) > 0.5:
                vecxz = elem.geometry.get("vecxz")
                assert vecxz is not None
                assert abs(vecxz[0] - 1.0) < 0.01, f"Y-beam vecxz[0] should be ~1, got {vecxz[0]}"
                assert abs(vecxz[1]) < 0.01, f"Y-beam vecxz[1] should be ~0, got {vecxz[1]}"
                assert abs(vecxz[2]) < 0.01, f"Y-beam vecxz[2] should be ~0, got {vecxz[2]}"
                return

        pytest.skip("No Y-direction beam found")

    def test_column_vecxz_is_0_1_0(self) -> None:
        """Vertical columns should have vecxz = (0, 1, 0)."""
        _skip_if_no_opensees()
        from src.fem.model_builder import build_fem_model

        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)

        for elem in model.elements.values():
            pid = elem.geometry.get("parent_column_id")
            if pid is None:
                continue
            vecxz = elem.geometry.get("vecxz")
            assert vecxz is not None, f"Column element {elem.tag} missing vecxz"
            assert abs(vecxz[0]) < 0.01, f"Column vecxz[0] should be ~0, got {vecxz[0]}"
            assert abs(vecxz[1] - 1.0) < 0.01, f"Column vecxz[1] should be ~1, got {vecxz[1]}"
            assert abs(vecxz[2]) < 0.01, f"Column vecxz[2] should be ~0, got {vecxz[2]}"
            return

        pytest.skip("No column element found")

    def test_x_and_y_beams_same_gravity_mz(self) -> None:
        """X-beam and Y-beam with same section + UDL give same |Mz| magnitude."""
        _skip_if_no_opensees()
        from src.fem.model_builder import build_fem_model
        from src.fem.solver import analyze_model

        project = build_benchmark_project_1x1()
        options = make_benchmark_options()
        model = build_fem_model(project, options)

        results = analyze_model(model, load_cases=["SDL"])
        result = results["SDL"]
        assert result.success

        z = project.geometry.story_height
        x_beam_mz = None
        y_beam_mz = None

        for elem in model.elements.values():
            if elem.element_type != ElementType.ELASTIC_BEAM:
                continue
            n_i = model.nodes[elem.node_tags[0]]
            n_j = model.nodes[elem.node_tags[1]]
            if abs(n_i.z - z) > 0.01 or abs(n_j.z - z) > 0.01:
                continue

            forces = result.element_forces.get(elem.tag, {})
            mz = abs(forces.get("Mz_i", 0.0))

            # X-direction beam
            if abs(n_i.y - n_j.y) < 0.01 and abs(n_j.x - n_i.x) > 0.5:
                if x_beam_mz is None or mz > x_beam_mz:
                    x_beam_mz = mz
            # Y-direction beam
            elif abs(n_i.x - n_j.x) < 0.01 and abs(n_j.y - n_i.y) > 0.5:
                if y_beam_mz is None or mz > y_beam_mz:
                    y_beam_mz = mz

        if x_beam_mz is None or y_beam_mz is None:
            pytest.skip("Could not find both X and Y direction beams")

        # Same section, same bay dimensions → Mz should be similar
        if x_beam_mz > 0.0 and y_beam_mz > 0.0:
            ratio = max(x_beam_mz, y_beam_mz) / min(x_beam_mz, y_beam_mz)
            assert ratio < 2.0, (
                f"X-beam Mz={x_beam_mz:.1f} and Y-beam Mz={y_beam_mz:.1f} "
                f"should be similar (ratio={ratio:.2f})"
            )
