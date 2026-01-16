"""
Test suite for Feature 2: Lateral Stability Module
Tests wind load calculations, core wall checks, and drift analysis.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.data_models import (
    ProjectData,
    GeometryInput,
    LoadInput,
    MaterialInput,
    LateralInput,
    TerrainCategory,
)
from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine


class TestWindEngine:
    """Test wind load calculations"""

    def test_wind_engine_basic(self):
        """Test basic wind load calculation"""
        # Setup project data
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=20, story_height=3.5),
            loads=LoadInput("2", "2.5", 2.0),
            materials=MaterialInput(fcu_column=45),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=8.0,
                core_dim_y=8.0,
                core_thickness=0.35,
            ),
        )

        # Calculate wind loads
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        # Assertions
        assert wind_result.base_shear > 0, "Base shear should be positive"
        assert wind_result.overturning_moment > 0, "Overturning moment should be positive"
        assert wind_result.reference_pressure > 0, "Reference pressure should be positive"

        # Reference pressure for HK should be around 1.8 kPa
        assert 1.5 < wind_result.reference_pressure < 2.5, "Reference pressure out of expected range"

        print(f"✓ Wind load calculation successful")
        print(f"  Base shear: {wind_result.base_shear:.1f} kN")
        print(f"  Overturning moment: {wind_result.overturning_moment:.1f} kNm")
        print(f"  Reference pressure: {wind_result.reference_pressure:.3f} kPa")

    def test_terrain_categories(self):
        """Test wind loads for different terrain categories"""
        terrains = [
            TerrainCategory.OPEN_SEA,
            TerrainCategory.OPEN_COUNTRY,
            TerrainCategory.URBAN,
            TerrainCategory.CITY_CENTRE,
        ]

        results = {}

        for terrain in terrains:
            project = ProjectData(
                geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=15, story_height=3.0),
                lateral=LateralInput(
                    building_width=24.0,
                    building_depth=24.0,
                    terrain=terrain,
                ),
            )

            wind_engine = WindEngine(project)
            wind_result = wind_engine.calculate_wind_loads()
            results[terrain.value] = wind_result.base_shear

        # All terrains should produce positive wind loads
        for terrain_code, shear in results.items():
            assert shear > 0, f"Terrain {terrain_code} should have positive wind load"

        # Results should be reasonable (1000-10000 kN for 15-story building)
        for terrain_code, shear in results.items():
            assert 1000 < shear < 10000, f"Terrain {terrain_code} wind load out of range"

        print(f"✓ Terrain category test passed")
        for terrain, shear in results.items():
            print(f"  Terrain {terrain}: {shear:.1f} kN")

    def test_height_effect(self):
        """Test that wind loads increase with building height"""
        heights = [5, 10, 20, 30]
        base_shears = []

        for floors in heights:
            project = ProjectData(
                geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=floors, story_height=3.5),
                lateral=LateralInput(
                    building_width=24.0,
                    building_depth=24.0,
                    terrain=TerrainCategory.URBAN,
                ),
            )

            wind_engine = WindEngine(project)
            wind_result = wind_engine.calculate_wind_loads()
            base_shears.append(wind_result.base_shear)

        # Wind loads should increase with height
        for i in range(len(base_shears) - 1):
            assert base_shears[i] < base_shears[i + 1], "Wind loads should increase with height"

        print(f"✓ Height effect test passed")
        for i, floors in enumerate(heights):
            print(f"  {floors} floors: {base_shears[i]:.1f} kN")


class TestCoreWallEngine:
    """Test core wall stress checks"""

    def test_core_wall_adequate(self):
        """Test core wall with adequate dimensions"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=20, story_height=3.5),
            loads=LoadInput("2", "2.5", 2.0),
            materials=MaterialInput(fcu_column=45),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=8.0,
                core_dim_y=8.0,
                core_thickness=0.35,
            ),
        )

        # Calculate wind loads first
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        # Check core wall
        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        # Assertions
        assert core_result.utilization > 0, "Utilization should be positive"
        assert core_result.status in ["OK", "FAIL"], "Status should be OK or FAIL"

        print(f"✓ Core wall check completed")
        print(f"  Status: {core_result.status}")
        print(f"  Compression utilization: {core_result.compression_check:.3f}")
        print(f"  Shear utilization: {core_result.shear_check:.3f}")
        print(f"  Tension check: {core_result.tension_check:.2f} MPa")
        print(f"  Tension piles required: {core_result.requires_tension_piles}")

    def test_core_wall_undersized(self):
        """Test core wall with inadequate dimensions"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=30, story_height=3.5),
            loads=LoadInput("2", "2.5", 2.0),
            materials=MaterialInput(fcu_column=35),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.OPEN_SEA,  # High wind
                core_dim_x=5.0,  # Small core
                core_dim_y=5.0,
                core_thickness=0.25,  # Thin walls
            ),
        )

        # Calculate wind loads
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        # Check core wall
        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        # Small core should have high utilization or fail
        assert core_result.utilization > 0.5, "Undersized core should have high utilization"

        print(f"✓ Undersized core wall test completed")
        print(f"  Status: {core_result.status}")
        print(f"  Utilization: {core_result.utilization:.3f}")
        print(f"  Warnings: {len(core_result.warnings)}")

    def test_core_wall_undefined(self):
        """Test core wall check with undefined dimensions"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=20, story_height=3.5),
            lateral=LateralInput(
                core_dim_x=0,  # Not defined
                core_dim_y=0,
                core_thickness=0,
            ),
        )

        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        assert core_result.status == "NOT DEFINED", "Should detect undefined core"
        assert len(core_result.warnings) > 0, "Should have warning about undefined core"

        print(f"✓ Undefined core wall test passed")
        print(f"  Status: {core_result.status}")


class TestDriftEngine:
    """Test building drift calculations"""

    def test_drift_calculation(self):
        """Test drift index calculation"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=25, story_height=3.5),
            materials=MaterialInput(fcu_column=45),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=8.0,
                core_dim_y=8.0,
                core_thickness=0.35,
            ),
        )

        # Calculate wind loads
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        # Calculate drift
        drift_engine = DriftEngine(project)
        updated_wind_result = drift_engine.calculate_drift(wind_result)

        # Assertions
        assert updated_wind_result.drift_index > 0, "Drift index should be positive"
        assert updated_wind_result.drift_index < 0.01, "Drift index should be reasonable"

        # Drift limit is 1/500 = 0.002
        drift_limit = 1.0 / 500.0

        print(f"✓ Drift calculation completed")
        print(f"  Drift index: {updated_wind_result.drift_index:.5f}")
        print(f"  Drift limit: {drift_limit:.5f}")
        print(f"  Status: {'OK' if updated_wind_result.drift_ok else 'FAIL'}")

    def test_drift_with_varying_stiffness(self):
        """Test drift response to core stiffness changes"""
        core_dimensions = [(6.0, 6.0), (8.0, 8.0), (10.0, 10.0)]
        drift_indices = []

        for core_x, core_y in core_dimensions:
            project = ProjectData(
                geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=20, story_height=3.5),
                materials=MaterialInput(fcu_column=45),
                lateral=LateralInput(
                    building_width=24.0,
                    building_depth=24.0,
                    terrain=TerrainCategory.URBAN,
                    core_dim_x=core_x,
                    core_dim_y=core_y,
                    core_thickness=0.35,
                ),
            )

            wind_engine = WindEngine(project)
            wind_result = wind_engine.calculate_wind_loads()

            drift_engine = DriftEngine(project)
            updated_result = drift_engine.calculate_drift(wind_result)
            drift_indices.append(updated_result.drift_index)

        # Larger core should have smaller drift
        for i in range(len(drift_indices) - 1):
            assert drift_indices[i] > drift_indices[i + 1], "Larger core should reduce drift"

        print(f"✓ Core stiffness effect test passed")
        for i, (core_x, core_y) in enumerate(core_dimensions):
            print(f"  Core {core_x}×{core_y}m: drift index = {drift_indices[i]:.5f}")


class TestIntegratedWorkflow:
    """Test complete lateral stability workflow"""

    def test_complete_workflow(self):
        """Test complete workflow: wind -> core -> drift"""
        # Setup 15-story office building
        project = ProjectData(
            project_name="15-Story Office Building",
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=15, story_height=3.5),
            loads=LoadInput("2", "2.5", 2.0),  # Office loading
            materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=7.0,
                core_dim_y=7.0,
                core_thickness=0.30,
            ),
        )

        # Step 1: Calculate wind loads
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        assert wind_result.base_shear > 0
        assert wind_result.overturning_moment > 0

        # Step 2: Check core wall capacity
        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        assert core_result.status in ["OK", "FAIL"]

        # Step 3: Calculate building drift
        drift_engine = DriftEngine(project)
        final_wind_result = drift_engine.calculate_drift(wind_result)

        assert final_wind_result.drift_index > 0

        # Print summary
        print(f"\n{'='*60}")
        print(f"LATERAL STABILITY ANALYSIS SUMMARY")
        print(f"Project: {project.project_name}")
        print(f"Height: {project.geometry.floors * project.geometry.story_height:.1f} m")
        print(f"{'='*60}")
        print(f"\nWIND LOADS:")
        print(f"  Base Shear: {final_wind_result.base_shear:.1f} kN")
        print(f"  Overturning Moment: {final_wind_result.overturning_moment:.1f} kNm")
        print(f"\nCORE WALL CAPACITY:")
        print(f"  Status: {core_result.status}")
        print(f"  Compression Util: {core_result.compression_check:.3f}")
        print(f"  Shear Util: {core_result.shear_check:.3f}")
        print(f"  Tension Piles: {'Yes' if core_result.requires_tension_piles else 'No'}")
        print(f"\nDRIFT CHECK:")
        print(f"  Drift Index: {final_wind_result.drift_index:.5f}")
        print(f"  Limit: 0.00200")
        print(f"  Status: {'OK' if final_wind_result.drift_ok else 'FAIL'}")
        print(f"{'='*60}")

        # Overall pass criteria
        overall_ok = (
            core_result.status == "OK" and
            final_wind_result.drift_ok
        )

        print(f"\nOVERALL STATUS: {'✓ PASS' if overall_ok else '✗ FAIL'}")
        print(f"{'='*60}\n")

        assert wind_result is not None, "Wind analysis should complete"
        assert core_result is not None, "Core wall check should complete"
        assert final_wind_result is not None, "Drift analysis should complete"

    def test_high_rise_scenario(self):
        """Test high-rise building (40 floors) scenario"""
        project = ProjectData(
            project_name="40-Story High-Rise",
            geometry=GeometryInput(bay_x=9.0, bay_y=9.0, floors=40, story_height=3.3),
            loads=LoadInput("1", "1.1", 1.5),  # Residential
            materials=MaterialInput(fcu_column=50),
            lateral=LateralInput(
                building_width=27.0,
                building_depth=27.0,
                terrain=TerrainCategory.CITY_CENTRE,
                core_dim_x=12.0,
                core_dim_y=12.0,
                core_thickness=0.50,
            ),
        )

        # Run complete analysis
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        drift_engine = DriftEngine(project)
        final_result = drift_engine.calculate_drift(wind_result)

        print(f"\n✓ High-rise scenario test completed")
        print(f"  Height: {project.geometry.floors * project.geometry.story_height:.1f} m")
        print(f"  Base shear: {final_result.base_shear:.1f} kN")
        print(f"  Core status: {core_result.status}")
        print(f"  Drift: {final_result.drift_index:.5f} {'OK' if final_result.drift_ok else 'FAIL'}")


if __name__ == "__main__":
    print("="*60)
    print("FEATURE 2: LATERAL STABILITY MODULE - TEST SUITE")
    print("="*60)

    # Run Wind Engine tests
    print("\n[1] WIND ENGINE TESTS")
    print("-" * 60)
    test_wind = TestWindEngine()
    test_wind.test_wind_engine_basic()
    test_wind.test_terrain_categories()
    test_wind.test_height_effect()

    # Run Core Wall Engine tests
    print("\n[2] CORE WALL ENGINE TESTS")
    print("-" * 60)
    test_core = TestCoreWallEngine()
    test_core.test_core_wall_adequate()
    test_core.test_core_wall_undersized()
    test_core.test_core_wall_undefined()

    # Run Drift Engine tests
    print("\n[3] DRIFT ENGINE TESTS")
    print("-" * 60)
    test_drift = TestDriftEngine()
    test_drift.test_drift_calculation()
    test_drift.test_drift_with_varying_stiffness()

    # Run integrated workflow tests
    print("\n[4] INTEGRATED WORKFLOW TESTS")
    print("-" * 60)
    test_integrated = TestIntegratedWorkflow()
    test_integrated.test_complete_workflow()
    test_integrated.test_high_rise_scenario()

    print("\n" + "="*60)
    print("ALL TESTS COMPLETED SUCCESSFULLY! ✓")
    print("="*60)
