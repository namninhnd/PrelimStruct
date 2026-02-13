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
        assert "HK Wind Code 2019" in result.code_reference
        assert "Sz=" in result.code_reference
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
    
    def test_design_pressure_stored(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            reference_pressure=3.0,
            num_floors=10,
            story_height=3.0,
        )
        
        assert result.design_pressure == pytest.approx(3.0 * 0.72)

    def test_reference_pressure_preserves_input_q0(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            reference_pressure=3.0,
            num_floors=10,
            story_height=3.0,
        )

        assert result.reference_pressure == pytest.approx(3.0)
        assert result.design_pressure == pytest.approx(3.0 * 0.72)


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
        
        assert sum_wx == pytest.approx(result.base_shear_x, rel=1e-6)
        assert sum_wy == pytest.approx(result.base_shear_y, rel=1e-6)

    def test_per_floor_wind_uses_design_pressure_not_reference_pressure(self) -> None:
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
            reference_pressure=3.0,
            force_coefficient=1.3,
            num_floors=10,
            story_height=3.0,
        )

        expected_wx = result.design_pressure * 1.3 * (3.0 * 20.0)
        assert result.floor_wind_x[0] == pytest.approx(expected_wx)

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
        result = calculate_hk_wind(
            total_height=30.0,
            building_width_x=20.0,
            building_width_y=20.0,
            terrain=TerrainCategory.URBAN,
        )
        
        assert result.base_shear > 0
        assert result.base_shear_x > 0
        assert result.base_shear_y > 0
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
    
    def test_default_values_are_safe(self) -> None:
        result = WindResult()
        
        assert result.code_reference == "HK Wind Code 2019 - Simplified Analysis"
        assert result.terrain_factor == 0.0
        assert result.force_coefficient == 0.0
        assert result.design_pressure == 0.0
        assert result.floor_elevations == []
        assert result.floor_wind_x == []
        assert result.floor_wind_y == []
        assert result.floor_torsion_z == []


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
            assert wtz == pytest.approx(expected_wtz, rel=1e-6), \
                f"Floor {i+1}: wtz={wtz:.2f}, expected={expected_wtz:.2f}"
