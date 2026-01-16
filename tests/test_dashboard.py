"""
Tests for the Streamlit Dashboard (Feature 3)
Tests that the dashboard can integrate all engines correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.data_models import (
    ProjectData, GeometryInput, LoadInput, MaterialInput, LateralInput,
    SlabDesignInput, BeamDesignInput, ReinforcementInput,
    SlabType, SpanDirection, ExposureClass, TerrainCategory,
    CoreLocation, ColumnPosition, LoadCombination, PRESETS,
)
from src.core.constants import CARBON_FACTORS
from src.engines.slab_engine import SlabEngine
from src.engines.beam_engine import BeamEngine
from src.engines.column_engine import ColumnEngine
from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine


def calculate_carbon_emission(project):
    """Calculate concrete volume and carbon emission (copied from app.py)"""
    floor_area = project.geometry.bay_x * project.geometry.bay_y
    floors = project.geometry.floors

    slab_thickness = 0.2
    if project.slab_result:
        slab_thickness = project.slab_result.thickness / 1000
    slab_volume = floor_area * slab_thickness * floors

    beam_depth = 0.5
    beam_width = 0.3
    if project.primary_beam_result:
        beam_depth = project.primary_beam_result.depth / 1000
        beam_width = project.primary_beam_result.width / 1000

    primary_beam_length = project.geometry.bay_x
    primary_beam_volume = beam_width * beam_depth * primary_beam_length * floors
    secondary_beam_volume = beam_width * beam_depth * project.geometry.bay_y * floors

    col_size = 0.4
    if project.column_result:
        col_size = project.column_result.dimension / 1000
    col_height = project.geometry.story_height * floors
    col_volume = col_size * col_size * col_height

    total_volume = slab_volume + primary_beam_volume + secondary_beam_volume + col_volume

    avg_fcu = (project.materials.fcu_slab + project.materials.fcu_beam + project.materials.fcu_column) / 3
    carbon_factor = CARBON_FACTORS.get(int(avg_fcu), 340)
    carbon_emission = total_volume * carbon_factor

    return total_volume, carbon_emission


def run_full_calculation(project):
    """Run full calculation pipeline (from app.py)"""
    slab_engine = SlabEngine(project)
    beam_engine = BeamEngine(project)
    column_engine = ColumnEngine(project)

    project.slab_result = slab_engine.calculate()

    tributary_width = project.geometry.bay_y / 2
    project.primary_beam_result = beam_engine.calculate_primary_beam(tributary_width)
    project.secondary_beam_result = beam_engine.calculate_secondary_beam(tributary_width)

    project.column_result = column_engine.calculate(ColumnPosition.INTERIOR)

    if project.lateral.building_width == 0:
        project.lateral.building_width = project.geometry.bay_x
    if project.lateral.building_depth == 0:
        project.lateral.building_depth = project.geometry.bay_y

    wind_engine = WindEngine(project)
    project.wind_result = wind_engine.calculate_wind_loads()

    if project.lateral.core_dim_x > 0 and project.lateral.core_dim_y > 0:
        drift_engine = DriftEngine(project)
        project.wind_result = drift_engine.calculate_drift(project.wind_result)

        core_engine = CoreWallEngine(project)
        project.core_wall_result = core_engine.check_core_wall(project.wind_result)
    else:
        column_loads = wind_engine.distribute_lateral_to_columns(project.wind_result)
        if column_loads and project.column_result:
            first_col_load = list(column_loads.values())[0]
            project.column_result.lateral_shear = first_col_load[0]
            project.column_result.lateral_moment = first_col_load[1]
            project.column_result.has_lateral_loads = True

            # Check combined P+M (returns tuple: utilization, status, warnings)
            utilization, status, warnings = column_engine.check_combined_load(
                project.column_result.axial_load,
                first_col_load[1],
                project.column_result.dimension,
                project.materials.fcu_column
            )
            project.column_result.combined_utilization = utilization

    project.concrete_volume, project.carbon_emission = calculate_carbon_emission(project)

    return project


class TestDashboardIntegration:
    """Test dashboard integration with all engines"""

    def test_residential_preset(self):
        """Test residential building preset"""
        project = ProjectData()
        preset = PRESETS["residential"]
        project.loads = preset["loads"]
        project.materials = preset["materials"]
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)

        project = run_full_calculation(project)

        assert project.slab_result is not None
        assert project.slab_result.thickness > 0
        assert project.primary_beam_result is not None
        assert project.column_result is not None
        assert project.wind_result is not None
        assert project.wind_result.lateral_system == "MOMENT_FRAME"
        assert project.concrete_volume > 0
        assert project.carbon_emission > 0

    def test_office_preset_with_core(self):
        """Test office building preset with core wall"""
        project = ProjectData()
        preset = PRESETS["office"]
        project.loads = preset["loads"]
        project.materials = preset["materials"]
        project.geometry = GeometryInput(8.0, 8.0, 15, 3.5)
        project.lateral = LateralInput(
            core_dim_x=5.0,
            core_dim_y=5.0,
            core_thickness=0.5,
            core_location=CoreLocation.CENTER,
            terrain=TerrainCategory.URBAN,
            building_width=8.0,
            building_depth=8.0
        )

        project = run_full_calculation(project)

        assert project.slab_result is not None
        assert project.wind_result is not None
        assert project.wind_result.lateral_system == "CORE_WALL"
        assert project.wind_result.drift_mm > 0
        assert project.core_wall_result is not None
        assert project.core_wall_result.compression_check > 0

    def test_retail_preset(self):
        """Test retail building preset (higher loads)"""
        project = ProjectData()
        preset = PRESETS["retail"]
        project.loads = preset["loads"]
        project.materials = preset["materials"]
        project.geometry = GeometryInput(10.0, 10.0, 3, 4.5)
        project.lateral = LateralInput(building_width=10.0, building_depth=10.0)

        project = run_full_calculation(project)

        assert project.slab_result is not None
        # Retail has higher live loads (5.0 kPa)
        assert project.loads.live_load == 5.0
        assert project.primary_beam_result is not None

    def test_carpark_preset(self):
        """Test car park building preset"""
        project = ProjectData()
        preset = PRESETS["carpark"]
        project.loads = preset["loads"]
        project.materials = preset["materials"]
        project.geometry = GeometryInput(8.0, 8.0, 5, 3.0)
        project.lateral = LateralInput(building_width=8.0, building_depth=8.0)

        project = run_full_calculation(project)

        assert project.slab_result is not None
        assert project.loads.live_load == 5.0  # Vehicular traffic

    def test_carbon_calculation(self):
        """Test carbon emission calculation"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.materials = MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)

        project = run_full_calculation(project)

        assert project.concrete_volume > 0
        assert project.carbon_emission > 0

        # Carbon per m2 should be reasonable (100-500 kgCO2e/m2 typical)
        floor_area = 6.0 * 6.0 * 5
        carbon_per_m2 = project.carbon_emission / floor_area
        assert 50 < carbon_per_m2 < 800

    def test_load_combinations(self):
        """Test different load combinations"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.load_combination = LoadCombination.ULS_GRAVITY

        uls_gravity_load = project.get_design_load()

        project.load_combination = LoadCombination.SLS_DEFLECTION
        sls_load = project.get_design_load()

        # ULS loads should be higher than SLS
        assert uls_gravity_load > sls_load

    def test_core_wall_locations(self):
        """Test different core wall locations"""
        for location in [CoreLocation.CENTER, CoreLocation.SIDE, CoreLocation.CORNER]:
            project = ProjectData()
            project.geometry = GeometryInput(8.0, 8.0, 10, 3.5)
            project.lateral = LateralInput(
                core_dim_x=4.0,
                core_dim_y=4.0,
                core_thickness=0.5,
                core_location=location,
                terrain=TerrainCategory.URBAN,
                building_width=8.0,
                building_depth=8.0
            )

            project = run_full_calculation(project)

            assert project.core_wall_result is not None
            # Corner locations should have higher eccentricity effects
            if location == CoreLocation.CORNER:
                # Corner core has highest stress due to eccentricity
                pass  # Just verify it runs without error

    def test_terrain_categories(self):
        """Test different terrain categories"""
        results = {}
        for terrain in TerrainCategory:
            project = ProjectData()
            project.geometry = GeometryInput(6.0, 6.0, 10, 3.0)
            project.lateral = LateralInput(
                terrain=terrain,
                building_width=6.0,
                building_depth=6.0
            )

            project = run_full_calculation(project)
            results[terrain] = project.wind_result.base_shear

        # All terrain categories should produce valid wind loads
        for terrain, base_shear in results.items():
            assert base_shear > 0, f"Terrain {terrain} should have positive wind load"

        # Verify different terrains produce different results
        assert len(set(results.values())) > 1, "Different terrains should produce different loads"


class TestStatusBadges:
    """Test status badge logic"""

    def test_utilization_status(self):
        """Test utilization-based status"""
        # This tests the logic that would be in get_status_badge
        def get_status(utilization):
            if utilization > 1.0:
                return "FAIL"
            elif utilization > 0.85:
                return "WARNING"
            else:
                return "OK"

        assert get_status(0.5) == "OK"
        assert get_status(0.9) == "WARNING"
        assert get_status(1.1) == "FAIL"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
