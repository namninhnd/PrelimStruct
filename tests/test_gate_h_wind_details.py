import pytest

from src.core.data_models import TerrainCategory, WindResult
from src.fem.wind_calculator import calculate_hk_wind


class TestGateHWindResultTraceability:
    
    def test_code_reference_field_populated(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        assert result.code_reference is not None
        assert "HK COP Wind Effects 2019" in result.code_reference
        assert "Cf=" in result.code_reference
    
    def test_terrain_factor_stored(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        # Legacy terrain_factor still stored for backward compat
        assert result.terrain_factor == pytest.approx(0.72)
    
    def test_force_coefficient_stored(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            force_coefficient=1.5,
            num_floors=10,
            story_height=3.0,
        )
        
        assert result.force_coefficient == pytest.approx(1.5)
    
    def test_topography_factor_stored(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            topography_factor=1.2,
            num_floors=10,
            story_height=3.0,
        )
        
        assert result.topography_factor == pytest.approx(1.2)

    def test_directionality_factor_stored(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            directionality_factor=0.85,
            num_floors=10,
            story_height=3.0,
        )

        assert result.directionality_factor == pytest.approx(0.85)


class TestGateHPerFloorWindLoads:
    
    def test_floor_elevations_populated(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        assert len(result.floor_elevations) == 10
        assert result.floor_elevations[0] == pytest.approx(3.0)
        assert result.floor_elevations[9] == pytest.approx(30.0)
    
    def test_floor_wind_x_populated(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        assert len(result.floor_wind_x) == 10
        assert all(wx > 0 for wx in result.floor_wind_x)
    
    def test_floor_wind_y_populated(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        assert len(result.floor_wind_y) == 10
        assert all(wy > 0 for wy in result.floor_wind_y)
    
    def test_floor_torsion_z_populated(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        assert len(result.floor_torsion_z) == 10
        assert all(wtz > 0 for wtz in result.floor_torsion_z)
    
    def test_per_floor_loads_sum_to_base_shear(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        sum_wx = sum(result.floor_wind_x)
        sum_wy = sum(result.floor_wind_y)
        
        # base_shear_x/y are rounded to 2dp; sum of 4dp per-floor values may differ slightly
        assert sum_wx == pytest.approx(result.base_shear_x, abs=0.1)
        assert sum_wy == pytest.approx(result.base_shear_y, abs=0.1)

    def test_per_floor_wind_forces_increase_with_height(self) -> None:
        """HK COP 2019: Q_o,z increases with height → floor forces increase."""
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            force_coefficient=1.3,
            num_floors=10,
            story_height=3.0,
        )

        for i in range(1, len(result.floor_wind_x)):
            assert result.floor_wind_x[i] > result.floor_wind_x[i - 1]

    def test_per_floor_arrays_have_consistent_lengths(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )

        assert len(result.floor_elevations) == len(result.floor_wind_x)
        assert len(result.floor_wind_x) == len(result.floor_wind_y)
        assert len(result.floor_wind_y) == len(result.floor_torsion_z)


class TestGateHBackwardCompatibility:
    
    def test_legacy_calculation_without_floors(self) -> None:
        """Without num_floors, base shear is zero (no floor loop runs)."""
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
        )
        
        # HK COP 2019: no floors → no per-floor forces → zero base shear
        assert result.base_shear == 0.0
        assert result.base_shear_x == 0.0
        assert result.base_shear_y == 0.0
        assert len(result.floor_elevations) == 0
        assert len(result.floor_wind_x) == 0
        assert len(result.floor_wind_y) == 0
        assert len(result.floor_torsion_z) == 0
    
    def test_zero_floors_returns_empty_arrays(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=0,
            story_height=3.0,
        )
        
        assert len(result.floor_elevations) == 0
        assert len(result.floor_wind_x) == 0
        assert len(result.floor_wind_y) == 0
        assert len(result.floor_torsion_z) == 0
    
    def test_zero_story_height_returns_empty_arrays(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=0.0,
        )
        
        assert len(result.floor_elevations) == 0


class TestGateHWindResultFields:
    
    def test_all_new_fields_present_in_dataclass(self) -> None:
        result = WindResult()
        
        assert hasattr(result, 'code_reference')
        assert hasattr(result, 'terrain_factor')
        assert hasattr(result, 'force_coefficient')
        assert hasattr(result, 'design_pressure')
        assert hasattr(result, 'floor_elevations')
        assert hasattr(result, 'floor_wind_x')
        assert hasattr(result, 'floor_wind_y')
        assert hasattr(result, 'floor_torsion_z')
        # HK COP 2019 fields
        assert hasattr(result, 'floor_Qoz')
        assert hasattr(result, 'floor_Sqz')
        assert hasattr(result, 'topography_factor')
        assert hasattr(result, 'directionality_factor')
    
    def test_default_values_are_safe(self) -> None:
        result = WindResult()
        
        assert "HK COP Wind Effects 2019" in result.code_reference
        assert result.terrain_factor == 0.0
        assert result.force_coefficient == 0.0
        assert result.design_pressure == 0.0
        assert result.topography_factor == 1.0
        assert result.directionality_factor == 1.0
        assert result.floor_elevations == []
        assert result.floor_wind_x == []
        assert result.floor_wind_y == []
        assert result.floor_torsion_z == []
        assert result.floor_Qoz == []
        assert result.floor_Sqz == []


class TestGateHPerFloorWindConsistency:
    
    def test_symmetric_building_has_equal_floor_loads(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        for wx, wy in zip(result.floor_wind_x, result.floor_wind_y):
            assert wx == pytest.approx(wy)
    
    def test_rectangular_building_has_correct_dominant_direction(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=30.0,
            building_width_y=10.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        for wx, wy in zip(result.floor_wind_x, result.floor_wind_y):
            assert wy > wx
    
    def test_torsion_based_on_governing_direction(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=30.0,
            building_width_y=10.0,
            terrain=TerrainCategory.URBAN,
            num_floors=10,
            story_height=3.0,
        )
        
        eccentricity = 0.05 * max(30.0, 10.0)
        
        for i, (wx, wy, wtz) in enumerate(zip(
            result.floor_wind_x, result.floor_wind_y, result.floor_torsion_z
        )):
            expected_wtz = max(wx, wy) * eccentricity
            assert wtz == pytest.approx(expected_wtz, rel=1e-4), \
                f"Floor {i+1}: wtz={wtz:.2f}, expected={expected_wtz:.2f}"
