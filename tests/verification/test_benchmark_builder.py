"""Tests for benchmark builders and independent load calculators.

These tests verify that:
1. Benchmark project builders create ProjectData matching specs
2. Independent load calculators match FEM model creation logic
"""

import pytest
from math import isclose

from src.core.constants import CONCRETE_DENSITY
from src.core.data_models import (
    BeamResult,
    ColumnResult,
    GeometryInput,
    LoadInput,
    MaterialInput,
    ProjectData,
    SlabResult,
)
from src.fem.model_builder import ModelBuilderOptions


class TestBenchmarkBuilders:
    """Tests for benchmark project builders."""

    def test_build_benchmark_project_1x1_geometry(self) -> None:
        """1x1 benchmark should have 6m bay, 1 floor, 4m story."""
        from tests.verification.benchmarks import build_benchmark_project_1x1

        project = build_benchmark_project_1x1()

        assert project.geometry.bay_x == 6.0
        assert project.geometry.bay_y == 6.0
        assert project.geometry.num_bays_x == 1
        assert project.geometry.num_bays_y == 1
        assert project.geometry.floors == 1
        assert project.geometry.story_height == 4.0

    def test_build_benchmark_project_1x1_slab(self) -> None:
        """1x1 benchmark should have 150mm slab."""
        from tests.verification.benchmarks import build_benchmark_project_1x1

        project = build_benchmark_project_1x1()

        assert project.slab_result is not None
        assert project.slab_result.thickness == 150

    def test_build_benchmark_project_1x1_beams(self) -> None:
        """1x1 benchmark should have 300x600 beams."""
        from tests.verification.benchmarks import build_benchmark_project_1x1

        project = build_benchmark_project_1x1()

        assert project.primary_beam_result is not None
        assert project.primary_beam_result.width == 300
        assert project.primary_beam_result.depth == 600

    def test_build_benchmark_project_1x1_columns(self) -> None:
        """1x1 benchmark should have 500x500 columns."""
        from tests.verification.benchmarks import build_benchmark_project_1x1

        project = build_benchmark_project_1x1()

        assert project.column_result is not None
        assert project.column_result.dimension == 500

    def test_build_benchmark_project_1x1_materials(self) -> None:
        """1x1 benchmark should have fcu=40."""
        from tests.verification.benchmarks import build_benchmark_project_1x1

        project = build_benchmark_project_1x1()

        assert project.materials.fcu_beam == 40
        assert project.materials.fcu_column == 40
        assert project.materials.fcu_slab == 40

    def test_build_benchmark_project_2x3_geometry(self) -> None:
        """2x3 benchmark should have 2 bays in X, 3 bays in Y."""
        from tests.verification.benchmarks import build_benchmark_project_2x3

        project = build_benchmark_project_2x3()

        assert project.geometry.num_bays_x == 2
        assert project.geometry.num_bays_y == 3
        assert project.geometry.bay_x == 6.0
        assert project.geometry.bay_y == 6.0
        assert project.geometry.floors == 1
        assert project.geometry.story_height == 4.0

    def test_build_benchmark_project_2x3_sections(self) -> None:
        """2x3 benchmark should have same sections as 1x1."""
        from tests.verification.benchmarks import build_benchmark_project_2x3

        project = build_benchmark_project_2x3()

        assert project.primary_beam_result.width == 300
        assert project.primary_beam_result.depth == 600
        assert project.column_result.dimension == 500
        assert project.slab_result.thickness == 150


class TestBenchmarkOptions:
    """Tests for make_benchmark_options helper."""

    def test_make_benchmark_options_defaults(self) -> None:
        """Benchmark options should disable core wall and secondary beams."""
        from tests.verification.benchmarks import make_benchmark_options

        options = make_benchmark_options()

        assert options.include_core_wall is False
        assert options.include_slabs is True
        assert options.num_secondary_beams == 0

    def test_make_benchmark_options_configurable_slab_mesh(self) -> None:
        """slab_elements_per_bay should be configurable."""
        from tests.verification.benchmarks import make_benchmark_options

        options = make_benchmark_options(slab_elements_per_bay=4)

        assert options.slab_elements_per_bay == 4


class TestIndependentLoadCalculators:
    """Tests for independent hand-calc load calculators."""

    def test_calc_sdl_total_load_1x1(self) -> None:
        """SDL total = SDL_kPa * plan_area for 1x1."""
        from tests.verification.benchmarks import (
            build_benchmark_project_1x1,
            calc_sdl_total_load,
        )

        project = build_benchmark_project_1x1()
        sdl_kpa = project.loads.dead_load  # Superimposed dead load

        # Plan area = 6m * 6m = 36 m²
        expected_sdl_kn = sdl_kpa * 36.0

        actual = calc_sdl_total_load(project)
        assert isclose(actual, expected_sdl_kn, rel_tol=1e-9)

    def test_calc_sdl_total_load_2x3(self) -> None:
        """SDL total = SDL_kPa * plan_area for 2x3."""
        from tests.verification.benchmarks import (
            build_benchmark_project_2x3,
            calc_sdl_total_load,
        )

        project = build_benchmark_project_2x3()
        sdl_kpa = project.loads.dead_load

        # Plan area = 6m * 2 * 6m * 3 = 216 m²
        expected_sdl_kn = sdl_kpa * 216.0

        actual = calc_sdl_total_load(project)
        assert isclose(actual, expected_sdl_kn, rel_tol=1e-9)

    def test_calc_ll_total_load_1x1(self) -> None:
        """LL total = LL_kPa * plan_area for 1x1."""
        from tests.verification.benchmarks import (
            build_benchmark_project_1x1,
            calc_ll_total_load,
        )

        project = build_benchmark_project_1x1()
        ll_kpa = project.loads.live_load

        # Plan area = 6m * 6m = 36 m²
        expected_ll_kn = ll_kpa * 36.0

        actual = calc_ll_total_load(project)
        assert isclose(actual, expected_ll_kn, rel_tol=1e-9)

    def test_calc_dl_slab_self_weight_1x1(self) -> None:
        """Slab DL = thickness * density * area."""
        from tests.verification.benchmarks import (
            build_benchmark_project_1x1,
            calc_slab_self_weight,
        )

        project = build_benchmark_project_1x1()

        # 150mm slab, 24.5 kN/m³, 36 m² area
        thickness_m = 0.150
        expected_slab_kn = CONCRETE_DENSITY * thickness_m * 36.0

        actual = calc_slab_self_weight(project, slab_thickness_m=0.150)
        assert isclose(actual, expected_slab_kn, rel_tol=1e-9)

    def test_calc_dl_beam_self_weight_1x1(self) -> None:
        """Beam DL: line load * total length."""
        from tests.verification.benchmarks import (
            build_benchmark_project_1x1,
            calc_beam_self_weight,
        )

        project = build_benchmark_project_1x1()

        # Beam: 300x600mm
        beam_b = 0.300
        beam_h = 0.600
        line_load_kn_m = CONCRETE_DENSITY * beam_b * beam_h

        # 1x1 bay: X-gridline beams = 2 * 1 * 6m = 12m
        #          Y-gridline beams = 2 * 1 * 6m = 12m
        # Total = 24m
        total_beam_length = 24.0
        expected_beam_kn = line_load_kn_m * total_beam_length

        actual = calc_beam_self_weight(project)
        assert isclose(actual, expected_beam_kn, rel_tol=1e-9)

    def test_calc_dl_beam_self_weight_2x3(self) -> None:
        """Beam DL for 2x3 grid."""
        from tests.verification.benchmarks import (
            build_benchmark_project_2x3,
            calc_beam_self_weight,
        )

        project = build_benchmark_project_2x3()

        beam_b = 0.300
        beam_h = 0.600
        line_load_kn_m = CONCRETE_DENSITY * beam_b * beam_h

        # 2x3 bay:
        # X-gridline beams: (num_bays_y + 1) * num_bays_x * bay_x = 4 * 2 * 6 = 48m
        # Y-gridline beams: (num_bays_x + 1) * num_bays_y * bay_y = 3 * 3 * 6 = 54m
        # Total = 102m
        total_beam_length = 48.0 + 54.0
        expected_beam_kn = line_load_kn_m * total_beam_length

        actual = calc_beam_self_weight(project)
        assert isclose(actual, expected_beam_kn, rel_tol=1e-9)

    def test_calc_dl_column_self_weight_1x1(self) -> None:
        """Column DL: density * area * height * count."""
        from tests.verification.benchmarks import (
            build_benchmark_project_1x1,
            calc_column_self_weight,
        )

        project = build_benchmark_project_1x1()

        # Column: 500x500mm
        col_b = 0.500
        col_h = 0.500
        story_height = 4.0

        # 1x1 bay: 4 columns, 1 floor
        n_columns = 4
        floors = 1
        expected_col_kn = (
            CONCRETE_DENSITY * col_b * col_h * story_height * n_columns * floors
        )

        actual = calc_column_self_weight(project)
        assert isclose(actual, expected_col_kn, rel_tol=1e-9)

    def test_calc_dl_column_self_weight_2x3(self) -> None:
        """Column DL for 2x3 grid."""
        from tests.verification.benchmarks import (
            build_benchmark_project_2x3,
            calc_column_self_weight,
        )

        project = build_benchmark_project_2x3()

        col_b = 0.500
        col_h = 0.500
        story_height = 4.0

        # 2x3 bay: (2+1) * (3+1) = 12 columns, 1 floor
        n_columns = 12
        floors = 1
        expected_col_kn = (
            CONCRETE_DENSITY * col_b * col_h * story_height * n_columns * floors
        )

        actual = calc_column_self_weight(project)
        assert isclose(actual, expected_col_kn, rel_tol=1e-9)

    def test_calc_dl_total_combines_components(self) -> None:
        """Total DL = slab + beam + column self-weights."""
        from tests.verification.benchmarks import (
            build_benchmark_project_1x1,
            calc_dl_total_load,
            calc_slab_self_weight,
            calc_beam_self_weight,
            calc_column_self_weight,
        )

        project = build_benchmark_project_1x1()
        slab_thickness_m = 0.150

        expected_total = (
            calc_slab_self_weight(project, slab_thickness_m=slab_thickness_m)
            + calc_beam_self_weight(project)
            + calc_column_self_weight(project)
        )

        actual = calc_dl_total_load(project, slab_thickness_m=slab_thickness_m)
        assert isclose(actual, expected_total, rel_tol=1e-9)
