import math

import pytest

from src.core.data_models import TerrainCategory, WindResult
from src.fem.model_builder import _compute_floor_shears, _compute_wtz_torsional_moments
from src.fem.wind_calculator import calculate_hk_wind, _Qoz, _Sqz_simplified


# ---------------------------------------------------------------------------
# HK COP 2019 formula unit tests
# ---------------------------------------------------------------------------


def test_Qoz_matches_table_3_1() -> None:
    """Verify Q_o,z power-law formula (Eq 3-2) against Table 3-1 values."""
    # Table 3-1 reference values (height → kPa)
    table_3_1 = {
        2.5: 1.63,
        5.0: 1.77,
        10.0: 1.97,
        20.0: 2.21,
        50.0: 2.56,
        100.0: 2.86,
        200.0: 3.20,
        500.0: 3.70,
    }
    for height, expected_kpa in table_3_1.items():
        actual = _Qoz(height)
        assert actual == pytest.approx(expected_kpa, abs=0.05), (
            f"Q_o,z at {height}m: expected {expected_kpa}, got {actual:.3f}"
        )


def test_Qoz_clamps_below_2_5m() -> None:
    """Effective height is clamped to 2.5m minimum."""
    assert _Qoz(0.0) == _Qoz(2.5)
    assert _Qoz(1.0) == _Qoz(2.5)


def test_Sqz_simplified_positive() -> None:
    """Simplified S_q (Eq 5-3) returns a positive value."""
    sq = _Sqz_simplified(H=30.0, B=20.0)
    assert sq > 0.0
    assert sq < 2.0  # Reasonable engineering range


# ---------------------------------------------------------------------------
# Integration tests for calculate_hk_wind
# ---------------------------------------------------------------------------


def test_hk_wind_symmetric_building() -> None:
    """Symmetric building should produce equal X and Y base shears."""
    result = calculate_hk_wind(
        total_height=30.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
        num_floors=10,
        story_height=3.0,
    )

    assert result.base_shear_x == pytest.approx(result.base_shear_y)
    assert result.base_shear == pytest.approx(result.base_shear_x)


def test_hk_wind_rectangular_building() -> None:
    """Wider Y-face should produce larger Vy than Vx."""
    result = calculate_hk_wind(
        total_height=30.0,
        building_width_x=30.0,
        building_width_y=10.0,
        terrain=TerrainCategory.URBAN,
        num_floors=10,
        story_height=3.0,
    )

    # Wind-Y acts on 30m face → larger force
    assert result.base_shear_y > result.base_shear_x


def test_hk_wind_zero_height() -> None:
    """Zero height should produce zero wind loads."""
    result = calculate_hk_wind(
        total_height=0.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
    )

    assert result.base_shear == 0.0
    assert result.base_shear_x == 0.0
    assert result.base_shear_y == 0.0


def test_floor_forces_increase_with_height() -> None:
    """Per-floor forces must increase monotonically with height.
    For H < 50m, S_q,z is constant so only Q_o,z increases.
    """
    result = calculate_hk_wind(
        total_height=15.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
        num_floors=5,
        story_height=3.0,
    )

    assert len(result.floor_wind_x) == 5
    for i in range(1, len(result.floor_wind_x)):
        assert result.floor_wind_x[i] > result.floor_wind_x[i - 1], (
            f"Floor {i + 1} force ({result.floor_wind_x[i]:.2f}) should be > "
            f"Floor {i} force ({result.floor_wind_x[i - 1]:.2f})"
        )


def test_sum_floor_forces_equals_base_shear() -> None:
    """Sum of per-floor forces must equal the reported base shear."""
    result = calculate_hk_wind(
        total_height=15.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
        num_floors=5,
        story_height=3.0,
    )

    assert sum(result.floor_wind_x) == pytest.approx(result.base_shear_x, rel=1e-4)
    assert sum(result.floor_wind_y) == pytest.approx(result.base_shear_y, rel=1e-4)


def test_hk_cop_traceability_fields_populated() -> None:
    """Q_o,z and S_q,z arrays should be populated for HK COP calculation."""
    result = calculate_hk_wind(
        total_height=15.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
        num_floors=5,
        story_height=3.0,
    )

    assert len(result.floor_Qoz) == 5
    assert len(result.floor_Sqz) == 5
    assert all(q > 0 for q in result.floor_Qoz)
    assert all(s > 0 for s in result.floor_Sqz)
    # Q_o,z should increase with height
    for i in range(1, 5):
        assert result.floor_Qoz[i] >= result.floor_Qoz[i - 1]


def test_topography_and_directionality_factors() -> None:
    """Adjusting S_t or S_θ should scale all forces proportionally."""
    base = calculate_hk_wind(
        total_height=30.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
        num_floors=10,
        story_height=3.0,
        topography_factor=1.0,
        directionality_factor=1.0,
    )
    scaled = calculate_hk_wind(
        total_height=30.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
        num_floors=10,
        story_height=3.0,
        topography_factor=1.5,
        directionality_factor=0.8,
    )

    # Forces should scale by S_t × S_θ = 1.5 × 0.8 = 1.2
    assert scaled.base_shear_x == pytest.approx(base.base_shear_x * 1.2, rel=1e-4)


def test_Sqz_uses_full_formula_for_tall_buildings() -> None:
    """Buildings H ≥ 50m use Eq 5-2 (varying S_q,z with height)."""
    result = calculate_hk_wind(
        total_height=60.0,
        building_width_x=30.0,
        building_width_y=30.0,
        terrain=TerrainCategory.URBAN,
        num_floors=20,
        story_height=3.0,
    )

    # Eq 5-2 produces height-varying S_q,z (not constant like Eq 5-3)
    assert result.floor_Sqz[-1] != result.floor_Sqz[0], (
        "For H >= 50m (Eq 5-2), S_q,z should vary with height"
    )


# ---------------------------------------------------------------------------
# Legacy model_builder tests (unchanged)
# ---------------------------------------------------------------------------


def test_compute_floor_shears_triangular() -> None:
    wind_result = WindResult(base_shear_x=1200.0, base_shear_y=800.0)
    floor_shears = _compute_floor_shears(
        wind_result=wind_result,
        direction="X",
        story_height=3.0,
        floors=4,
    )

    assert set(floor_shears.keys()) == {3.0, 6.0, 9.0, 12.0}
    assert floor_shears[12.0] > floor_shears[9.0] > floor_shears[6.0] > floor_shears[3.0]
    assert sum(floor_shears.values()) == pytest.approx(1200.0 * 1000.0)


def test_compute_floor_shears_prefers_per_floor_wind_data() -> None:
    wind_result = WindResult(
        base_shear_x=999.0,
        floor_elevations=[3.0, 6.0, 9.0],
        floor_wind_x=[12.0, 18.0, 30.0],
    )
    floor_shears = _compute_floor_shears(
        wind_result=wind_result,
        direction="X",
        story_height=3.0,
        floors=3,
    )

    assert floor_shears == {
        3.0: pytest.approx(12000.0),
        6.0: pytest.approx(18000.0),
        9.0: pytest.approx(30000.0),
    }


def test_compute_wtz_torsional_moments_uses_y_basis_when_governing() -> None:
    wind_result = WindResult(base_shear_x=300.0, base_shear_y=900.0)
    floor_shears_x = _compute_floor_shears(
        wind_result=wind_result,
        direction="X",
        story_height=3.0,
        floors=3,
    )
    floor_shears_y = _compute_floor_shears(
        wind_result=wind_result,
        direction="Y",
        story_height=3.0,
        floors=3,
    )

    moments, basis = _compute_wtz_torsional_moments(
        floor_shears_x=floor_shears_x,
        floor_shears_y=floor_shears_y,
        building_width=24.0,
        building_depth=18.0,
    )

    assert basis == "Y"
    eccentricity_y = 0.05 * 24.0
    for level, shear in floor_shears_y.items():
        assert moments[level] == pytest.approx(shear * eccentricity_y)
