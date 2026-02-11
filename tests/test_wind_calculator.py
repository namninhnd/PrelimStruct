import pytest

from src.core.data_models import TerrainCategory
from src.fem.model_builder import _compute_floor_shears, _compute_wtz_torsional_moments
from src.fem.wind_calculator import calculate_hk_wind


def test_hk_wind_symmetric_building() -> None:
    result = calculate_hk_wind(
        total_height=30.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
    )

    assert result.base_shear_x == pytest.approx(result.base_shear_y)
    assert result.base_shear == pytest.approx(result.base_shear_x)


def test_hk_wind_rectangular_building() -> None:
    result = calculate_hk_wind(
        total_height=30.0,
        building_width_x=30.0,
        building_width_y=10.0,
        terrain=TerrainCategory.URBAN,
    )

    assert result.base_shear_y > result.base_shear_x


def test_hk_wind_terrain_factors() -> None:
    open_country = calculate_hk_wind(
        total_height=30.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.OPEN_COUNTRY,
    )
    city_centre = calculate_hk_wind(
        total_height=30.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.CITY_CENTRE,
    )

    assert open_country.base_shear > city_centre.base_shear


def test_hk_wind_zero_height() -> None:
    result = calculate_hk_wind(
        total_height=0.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
    )

    assert result.base_shear == 0.0
    assert result.base_shear_x == 0.0
    assert result.base_shear_y == 0.0


def test_compute_floor_shears_triangular() -> None:
    floor_shears = _compute_floor_shears(base_shear_kn=1200.0, story_height=3.0, floors=4)

    assert set(floor_shears.keys()) == {3.0, 6.0, 9.0, 12.0}
    assert floor_shears[12.0] > floor_shears[9.0] > floor_shears[6.0] > floor_shears[3.0]
    assert sum(floor_shears.values()) == pytest.approx(1200.0 * 1000.0)


def test_compute_wtz_torsional_moments_uses_y_basis_when_governing() -> None:
    floor_shears_x = _compute_floor_shears(base_shear_kn=300.0, story_height=3.0, floors=3)
    floor_shears_y = _compute_floor_shears(base_shear_kn=900.0, story_height=3.0, floors=3)

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
