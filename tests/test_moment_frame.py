"""
Test suite for Moment Frame System (buildings without core walls)
Tests lateral load distribution to columns and combined P+M checks.

V3.5 DEPRECATED: These tests are for the simplified calculation workflow.
The simplified WindEngine and column P+M distribution have been replaced by
the FEM module. These tests are skipped until equivalent FEM-based tests are added.

See:
- src/fem/load_combinations.py for HK Code 2019 load combinations
- src/fem/model_builder.py for FEM model construction
- src/fem/results_processor.py for result extraction
"""

import pytest

# Skip all tests in this module - deprecated workflow
pytestmark = pytest.mark.skip(reason="V3.5: Moment frame tests use deprecated simplified WindEngine. "
                                      "Migrate to FEM-based lateral analysis tests.")

from src.core.data_models import (
    ProjectData,
    GeometryInput,
    LoadInput,
    MaterialInput,
    LateralInput,
    TerrainCategory,
    ColumnPosition,
    CoreWallConfig,
    CoreWallGeometry,
)
from src.engines.wind_engine import WindEngine
from src.engines.column_engine import ColumnEngine


class TestLateralSystemDetection:
    """Test automatic detection of lateral system type"""

    def test_core_wall_system_detection(self):
        """Test that core wall system is detected when core is defined"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=15, story_height=3.5),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=8.0,  # Core defined
                core_dim_y=8.0,
                core_thickness=0.5,
            ),
        )

        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        assert wind_result.lateral_system == "CORE_WALL", "Should detect core wall system"

        print(f"✓ Core wall system detected")
        print(f"  Lateral system: {wind_result.lateral_system}")

    def test_moment_frame_system_detection(self):
        """Test that moment frame system is detected when no core"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=8, story_height=3.5),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=0,  # No core
                core_dim_y=0,
                core_thickness=0,
            ),
        )

        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        assert wind_result.lateral_system == "MOMENT_FRAME", "Should detect moment frame system"

        print(f"✓ Moment frame system detected")
        print(f"  Lateral system: {wind_result.lateral_system}")


class TestLateralLoadDistribution:
    """Test distribution of lateral loads to columns"""

    def test_load_distribution_to_columns(self):
        """Test tributary area distribution method"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=10, story_height=3.5),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=0,  # Moment frame
                core_dim_y=0,
            ),
        )

        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        # Distribute loads
        column_loads = wind_engine.distribute_lateral_to_columns(wind_result)

        # Assertions
        assert wind_result.lateral_system == "MOMENT_FRAME"
        assert len(column_loads) > 0, "Should have distributed loads to columns"

        # Get first column load
        col_id = list(column_loads.keys())[0]
        V_col, M_col = column_loads[col_id]

        assert V_col > 0, "Column shear should be positive"
        assert M_col > 0, "Column moment should be positive"

        # Check that sum of column loads approximately equals total wind load
        total_V = sum(v for v, m in column_loads.values())
        # Note: Due to multiple columns, we don't expect exact match

        print(f"✓ Lateral load distribution successful")
        print(f"  Total base shear: {wind_result.base_shear:.1f} kN")
        print(f"  Number of columns: {len(column_loads)}")
        print(f"  Shear per column: {V_col:.1f} kN")
        print(f"  Moment per column: {M_col:.1f} kNm")
        print(f"  Sum of column shears: {total_V:.1f} kN")

    def test_no_distribution_for_core_wall_system(self):
        """Test that core wall system doesn't distribute to columns"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=10, story_height=3.5),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=8.0,  # Core wall system
                core_dim_y=8.0,
                core_thickness=0.5,
            ),
        )

        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        # Try to distribute loads
        column_loads = wind_engine.distribute_lateral_to_columns(wind_result)

        # Should return empty dict for core wall system
        assert len(column_loads) == 0, "Core wall system should not distribute to columns"

        print(f"✓ Core wall system correctly skips column distribution")
        print(f"  Lateral system: {wind_result.lateral_system}")


class TestColumnCombinedLoad:
    """Test combined P+M checks for columns in moment frame"""

    def test_column_combined_pm_check(self):
        """Test column under combined axial + lateral moment"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=10, story_height=3.5),
            loads=LoadInput("2", "2.5", 2.0),
            materials=MaterialInput(fcu_column=45),
        )

        column_engine = ColumnEngine(project)

        # Typical loads for 10-story building
        P_axial = 5000  # kN (gravity load)
        M_lateral = 500  # kNm (from wind)
        h_column = 600  # mm

        utilization, status, warnings = column_engine.check_combined_load(
            P_axial, M_lateral, h_column, project.materials.fcu_column
        )

        assert utilization > 0, "Utilization should be positive"
        assert status in ["OK", "FAIL"], "Status should be OK or FAIL"

        print(f"✓ Combined P+M check completed")
        print(f"  Axial load: {P_axial} kN")
        print(f"  Lateral moment: {M_lateral} kNm")
        print(f"  Column size: {h_column} × {h_column} mm")
        print(f"  Utilization: {utilization:.3f}")
        print(f"  Status: {status}")
        print(f"  Warnings: {len(warnings)}")

    def test_column_failure_under_high_moment(self):
        """Test that column fails with excessive lateral moment"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=10, story_height=3.5),
            materials=MaterialInput(fcu_column=35),
        )

        column_engine = ColumnEngine(project)

        # High lateral moment with small column
        P_axial = 3000  # kN
        M_lateral = 2000  # kNm (very high!)
        h_column = 400  # mm (small column)

        utilization, status, warnings = column_engine.check_combined_load(
            P_axial, M_lateral, h_column, project.materials.fcu_column
        )

        # Should fail with high utilization
        assert utilization > 1.0, "Should fail with high moment"
        assert status == "FAIL", "Status should be FAIL"
        assert len(warnings) > 0, "Should have warnings"

        print(f"✓ High moment failure test passed")
        print(f"  Utilization: {utilization:.3f} (>1.0 = FAIL)")
        print(f"  Status: {status}")


class TestIntegratedMomentFrame:
    """Test complete moment frame workflow"""

    def test_complete_moment_frame_workflow(self):
        """Test end-to-end workflow for moment frame building"""
        # 8-story low-rise building WITHOUT core wall
        project = ProjectData(
            project_name="8-Story Low-Rise Moment Frame",
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=8, story_height=3.5),
            loads=LoadInput("2", "2.5", 2.0),  # Office loading
            materials=MaterialInput(fcu_column=45),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=0,  # NO CORE - Moment frame system
                core_dim_y=0,
            ),
        )

        # Step 1: Calculate wind loads
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        assert wind_result.lateral_system == "MOMENT_FRAME"
        assert wind_result.base_shear > 0

        # Step 2: Distribute loads to columns
        column_loads = wind_engine.distribute_lateral_to_columns(wind_result)

        assert len(column_loads) > 0
        col_id = list(column_loads.keys())[0]
        V_col, M_col = column_loads[col_id]

        # Step 3: Design column for gravity loads
        column_engine = ColumnEngine(project)
        column_result = column_engine.calculate(position=ColumnPosition.INTERIOR)

        # Step 4: Check column for combined P+M
        combined_util, combined_status, warnings = column_engine.check_combined_load(
            column_result.axial_load,
            M_col,
            column_result.dimension,
            project.materials.fcu_column
        )

        # Print summary
        print(f"\n{'='*70}")
        print(f"MOMENT FRAME SYSTEM - INTEGRATED WORKFLOW")
        print(f"Project: {project.project_name}")
        print(f"Height: {project.geometry.floors * project.geometry.story_height:.1f} m")
        print(f"{'='*70}")
        print(f"\nLATERAL SYSTEM:")
        print(f"  Type: {wind_result.lateral_system}")
        print(f"  Base Shear: {wind_result.base_shear:.1f} kN")
        print(f"\nCOLUMN LOADS:")
        print(f"  Number of columns: {len(column_loads)}")
        print(f"  Shear per column: {V_col:.1f} kN")
        print(f"  Moment per column: {M_col:.1f} kNm")
        print(f"\nCOLUMN DESIGN:")
        print(f"  Gravity size: {column_result.dimension} × {column_result.dimension} mm")
        print(f"  Axial load: {column_result.axial_load:.0f} kN")
        print(f"  Gravity utilization: {column_result.utilization:.3f}")
        print(f"\nCOMBINED P+M CHECK:")
        print(f"  Combined utilization: {combined_util:.3f}")
        print(f"  Status: {combined_status}")
        print(f"  Warnings: {len(warnings)}")
        print(f"{'='*70}")

        overall_ok = combined_status == "OK"
        print(f"\nOVERALL STATUS: {'✓ PASS' if overall_ok else '✗ FAIL'}")
        print(f"{'='*70}\n")

        # Assertions
        assert wind_result is not None
        assert column_loads is not None
        assert column_result is not None
        assert combined_util > 0


class TestComparisonCoreVsFrame:
    """Compare core wall vs moment frame systems"""

    def test_same_building_different_systems(self):
        """Test same building with core vs without core"""

        # Same building geometry and loads
        common_params = {
            "geometry": GeometryInput(bay_x=8.0, bay_y=8.0, floors=12, story_height=3.5),
            "loads": LoadInput("2", "2.5", 2.0),
            "materials": MaterialInput(fcu_column=45),
        }

        # Version 1: WITH core wall
        project_core = ProjectData(
            **common_params,
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=8.0,
                core_dim_y=8.0,
                core_thickness=0.5,
            ),
        )

        # Version 2: WITHOUT core (moment frame)
        project_frame = ProjectData(
            **common_params,
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_dim_x=0,  # No core
                core_dim_y=0,
            ),
        )

        # Calculate wind for both
        wind_engine_core = WindEngine(project_core)
        wind_result_core = wind_engine_core.calculate_wind_loads()

        wind_engine_frame = WindEngine(project_frame)
        wind_result_frame = wind_engine_frame.calculate_wind_loads()

        # Compare
        print(f"\n✓ System comparison completed")
        print(f"\nCORE WALL SYSTEM:")
        print(f"  Lateral system: {wind_result_core.lateral_system}")
        print(f"  Base shear: {wind_result_core.base_shear:.1f} kN")
        print(f"  Core resists 100% of lateral load")

        print(f"\nMOMENT FRAME SYSTEM:")
        print(f"  Lateral system: {wind_result_frame.lateral_system}")
        print(f"  Base shear: {wind_result_frame.base_shear:.1f} kN")

        column_loads = wind_engine_frame.distribute_lateral_to_columns(wind_result_frame)
        print(f"  Distributed to {len(column_loads)} columns")

        if column_loads:
            V_col, M_col = list(column_loads.values())[0]
            print(f"  Each column: V={V_col:.1f} kN, M={M_col:.1f} kNm")

        # Wind loads should be same (same building geometry)
        assert abs(wind_result_core.base_shear - wind_result_frame.base_shear) < 10


if __name__ == "__main__":
    print("="*70)
    print("MOMENT FRAME SYSTEM - TEST SUITE")
    print("="*70)

    # Test lateral system detection
    print("\n[1] LATERAL SYSTEM DETECTION")
    print("-" * 70)
    test_detection = TestLateralSystemDetection()
    test_detection.test_core_wall_system_detection()
    test_detection.test_moment_frame_system_detection()

    # Test load distribution
    print("\n[2] LATERAL LOAD DISTRIBUTION")
    print("-" * 70)
    test_distribution = TestLateralLoadDistribution()
    test_distribution.test_load_distribution_to_columns()
    test_distribution.test_no_distribution_for_core_wall_system()

    # Test combined P+M checks
    print("\n[3] COLUMN COMBINED P+M CHECKS")
    print("-" * 70)
    test_combined = TestColumnCombinedLoad()
    test_combined.test_column_combined_pm_check()
    test_combined.test_column_failure_under_high_moment()

    # Test integrated workflow
    print("\n[4] INTEGRATED MOMENT FRAME WORKFLOW")
    print("-" * 70)
    test_integrated = TestIntegratedMomentFrame()
    test_integrated.test_complete_moment_frame_workflow()

    # Compare systems
    print("\n[5] CORE WALL VS MOMENT FRAME COMPARISON")
    print("-" * 70)
    test_comparison = TestComparisonCoreVsFrame()
    test_comparison.test_same_building_different_systems()

    print("\n" + "="*70)
    print("ALL MOMENT FRAME TESTS COMPLETED SUCCESSFULLY! ✓")
    print("="*70)
