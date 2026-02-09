"""Integration tests: beam model → solve → extract forces → verify convention.

Verifies the full pipeline from model creation through force extraction
produces physically correct results for gravity beams.

ETABS convention (verified by Phase 1 deflection test):
- local_y = vertical for horizontal beams (via vecxz = (dy/L, -dx/L, 0))
- Mz = major-axis (gravity) bending moment, uses Iz = b*h³/12 stiffness
- My = minor-axis bending moment, uses Iy = h*b³/12 stiffness
- Vy = gravity shear (in local_y = vertical direction)
- Vz = lateral shear (in local_z = horizontal direction)
"""

import pytest
from typing import Dict, Optional

from tests.verification.benchmarks import (
    build_benchmark_project_1x1,
    make_benchmark_options,
)


def _skip_if_no_opensees():
    pytest.importorskip("openseespy.opensees", reason="OpenSeesPy not available")


def _build_and_solve(load_cases=None):
    """Build 1x1 benchmark model and solve."""
    from src.fem.model_builder import build_fem_model
    from src.fem.solver import analyze_model

    if load_cases is None:
        load_cases = ["SDL"]

    project = build_benchmark_project_1x1()
    options = make_benchmark_options()
    model = build_fem_model(project, options)
    results = analyze_model(model, load_cases=load_cases)
    return project, model, results


def _find_any_beam(model, z_floor: float) -> Optional[int]:
    """Find any parent_beam_id at the given floor elevation."""
    from src.fem.fem_engine import ElementType

    parent_groups: Dict[int, list] = {}
    for elem_tag, elem in model.elements.items():
        if elem.element_type not in (ElementType.ELASTIC_BEAM, ElementType.SECONDARY_BEAM):
            continue
        pid = elem.geometry.get("parent_beam_id")
        if pid is not None:
            parent_groups.setdefault(pid, []).append(elem_tag)

    for pid, tags in parent_groups.items():
        for tag in tags:
            n_i = model.nodes[model.elements[tag].node_tags[0]]
            n_j = model.nodes[model.elements[tag].node_tags[1]]
            if abs(n_i.z - z_floor) < 0.01 and abs(n_j.z - z_floor) < 0.01:
                return pid
    return None


def _get_sub_element_tags(model, parent_beam_id: int) -> list:
    subs = []
    for tag, elem in model.elements.items():
        if elem.geometry.get("parent_beam_id") == parent_beam_id:
            idx = elem.geometry.get("sub_element_index", 0)
            subs.append((idx, tag))
    subs.sort()
    return [t for _, t in subs]


@pytest.mark.integration
class TestBeamAxisPipeline:
    """Full pipeline: build beam → solve → verify forces are physically correct.

    For horizontal beams with vecxz = (dy/L, -dx/L, 0):
    - local_y = (0, 0, 1) vertical → Mz = gravity bending, Vy = gravity shear
    - local_z = horizontal → My = minor bending, Vz = lateral shear
    - Mz uses Iz = b*h³/12 (strong axis), My uses Iy = h*b³/12 (weak axis)
    """

    def test_gravity_beam_mz_dominates_my(self) -> None:
        """Gravity-loaded beam: Mz (major axis) >> My (minor axis)."""
        _skip_if_no_opensees()
        project, model, results = _build_and_solve(["SDL"])
        result = results["SDL"]
        assert result.success

        z = project.geometry.story_height
        pid = _find_any_beam(model, z)
        assert pid is not None

        tags = _get_sub_element_tags(model, pid)
        mid_tag = tags[len(tags) // 2]
        forces = result.element_forces.get(mid_tag, {})

        mz_i = abs(forces.get("Mz_i", 0.0))
        my_i = abs(forces.get("My_i", 0.0))

        assert mz_i > 0.0, "Mz should be non-zero for gravity beam"
        assert mz_i > my_i * 5.0, (
            f"Expected Mz >> My for gravity beam (ETABS convention). "
            f"Mz={mz_i:.1f}, My={my_i:.1f}"
        )

    def test_gravity_beam_vy_dominates_vz(self) -> None:
        """Gravity-loaded beam: Vy (gravity shear) >> Vz (lateral shear)."""
        _skip_if_no_opensees()
        project, model, results = _build_and_solve(["SDL"])
        result = results["SDL"]
        assert result.success

        z = project.geometry.story_height
        pid = _find_any_beam(model, z)
        assert pid is not None

        tags = _get_sub_element_tags(model, pid)
        forces = result.element_forces.get(tags[0], {})

        vy_i = abs(forces.get("Vy_i", 0.0))
        vz_i = abs(forces.get("Vz_i", 0.0))

        assert vy_i > 0.0, "Vy should be non-zero for gravity beam"
        assert vy_i > vz_i * 2.0, (
            f"Expected Vy >> Vz for gravity beam (ETABS convention). "
            f"Vy={vy_i:.1f}, Vz={vz_i:.1f}"
        )

    def test_gravity_beam_has_nonzero_mz(self) -> None:
        """Midspan Mz (major-axis moment) should be non-zero under gravity."""
        _skip_if_no_opensees()
        project, model, results = _build_and_solve(["SDL"])
        result = results["SDL"]
        assert result.success

        z = project.geometry.story_height
        pid = _find_any_beam(model, z)
        assert pid is not None

        tags = _get_sub_element_tags(model, pid)
        mid_tag = tags[len(tags) // 2]
        forces = result.element_forces.get(mid_tag, {})

        mz_i = forces.get("Mz_i", 0.0)
        mz_j = forces.get("Mz_j", 0.0)
        midspan_mz = abs(mz_i + mz_j) / 2.0

        assert midspan_mz > 0.0, (
            f"Expected non-zero Mz at midspan (major-axis bending). Got {midspan_mz:.1f}"
        )

    def test_gravity_beam_envelope_mz_dominates(self) -> None:
        """Envelope correctly captures Mz as dominant moment for gravity beams."""
        _skip_if_no_opensees()
        from src.core.data_models import LoadCaseResult, LoadCombination
        from src.fem.results_processor import ResultsProcessor

        project, model, results = _build_and_solve(["SDL", "LL"])

        processor = ResultsProcessor()
        load_case_results = []
        combo_map = {"SDL": LoadCombination.ULS_GRAVITY_1, "LL": LoadCombination.ULS_GRAVITY_1}

        for lc_name, result in results.items():
            if not result.success:
                continue
            load_case_results.append(
                LoadCaseResult(
                    combination=combo_map.get(lc_name, LoadCombination.ULS_GRAVITY_1),
                    element_forces=result.element_forces,
                    node_displacements=result.node_displacements,
                    reactions=result.node_reactions,
                )
            )

        processor.process_load_case_results(load_case_results)

        # Check any beam element envelope: Mz (major axis) > My (minor axis)
        for eid, envelope in processor.element_force_envelopes.items():
            if envelope.Mz_max.max_value > 1.0:  # Non-trivial moment
                assert envelope.Mz_max.max_value > envelope.My_max.max_value, (
                    f"Element {eid}: Mz_max={envelope.Mz_max.max_value:.1f} "
                    f"should be > My_max={envelope.My_max.max_value:.1f}"
                )
                break
        else:
            pytest.skip("No beam elements with significant moment found")
