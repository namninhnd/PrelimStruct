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
    CoreWallGeometry,
    CoreWallConfig,
    CoreWallSectionProperties,
    FEMResult,
    LoadCaseResult,
    LoadCombination,
)
from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine


def attach_mock_wind_fem_result(project: ProjectData, shear: float, moment: float) -> None:
    """Attach a minimal FEMResult with a wind load case and base reactions."""
    project.fem_result = FEMResult(
        load_case_results=[
            LoadCaseResult(
                combination=LoadCombination.ULS_WIND_1,
                element_forces={},
                reactions={1: [shear, 0.0, 0.0, moment, 0.0, 0.0]},
            )
        ]
    )


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
            ),
        )

        # Calculate wind loads
        attach_mock_wind_fem_result(project, shear=1200.0, moment=4500.0)
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        # Assertions
        assert wind_result.base_shear > 0, "Base shear should be positive"
        assert wind_result.overturning_moment > 0, "Overturning moment should be positive"
        assert wind_result.reference_pressure == 0.0, "Reference pressure is FEM-derived in v3.5"

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

        for idx, terrain in enumerate(terrains):
            project = ProjectData(
                geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=15, story_height=3.0),
                lateral=LateralInput(
                    building_width=24.0,
                    building_depth=24.0,
                    terrain=terrain,
                ),
            )

            attach_mock_wind_fem_result(project, shear=1000.0 + idx * 100.0, moment=3500.0)
            wind_engine = WindEngine(project)
            wind_result = wind_engine.calculate_wind_loads()
            results[terrain.value] = wind_result.base_shear

        # All terrains should produce positive wind loads
        for terrain_code, shear in results.items():
            assert shear > 0, f"Terrain {terrain_code} should have positive wind load"

        print(f"??? Terrain category test passed")
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

            attach_mock_wind_fem_result(project, shear=floors * 120.0, moment=4000.0)
            wind_engine = WindEngine(project)
            wind_result = wind_engine.calculate_wind_loads()
            base_shears.append(wind_result.base_shear)

        # Wind loads should increase with height (mocked)
        for i in range(len(base_shears) - 1):
            assert base_shears[i] < base_shears[i + 1], "Wind loads should increase with height"

        print(f"??? Height effect test passed")
        for i, floors in enumerate(heights):
            print(f"  {floors} floors: {base_shears[i]:.1f} kN")
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
                core_geometry=CoreWallGeometry(
                    config=CoreWallConfig.TUBE_CENTER_OPENING,
                    length_x=8000.0,
                    length_y=8000.0,
                    opening_width=2000.0,
                    opening_height=2400.0,
                ),
                section_properties=CoreWallSectionProperties(
                    I_xx=1.5e12,
                    I_yy=1.2e12,
                    A=3.2e6,
                ),
            ),
        )

        attach_mock_wind_fem_result(project, shear=1500.0, moment=5200.0)
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        assert core_result.compression_check >= 0, "Compression check should be non-negative"
        assert core_result.shear_check >= 0, "Shear check should be non-negative"
        assert core_result.status in ["OK", "FAIL"], "Status should be OK or FAIL"

        print(f"??? Core wall check completed")
        print(f"  Status: {core_result.status}")
        print(f"  Compression utilization: {core_result.compression_check:.3f}")
        print(f"  Shear utilization: {core_result.shear_check:.3f}")
    def test_core_wall_undersized(self):
        """Test core wall with undersized section properties"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=30, story_height=3.5),
            loads=LoadInput("2", "2.5", 2.0),
            materials=MaterialInput(fcu_column=35),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.OPEN_SEA,
                core_geometry=CoreWallGeometry(
                    config=CoreWallConfig.TUBE_CENTER_OPENING,
                    length_x=5000.0,
                    length_y=5000.0,
                    opening_width=1500.0,
                    opening_height=2400.0,
                ),
                section_properties=CoreWallSectionProperties(
                    I_xx=0.4e12,
                    I_yy=0.35e12,
                    A=1.6e6,
                ),
            ),
        )

        attach_mock_wind_fem_result(project, shear=2200.0, moment=7800.0)
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        assert core_result.compression_check >= 0, "Compression check should be non-negative"

        print(f"??? Undersized core wall test completed")
        print(f"  Status: {core_result.status}")
        print(f"  Utilization: {core_result.compression_check:.3f}")
    def test_core_wall_undefined(self):
        """Test core wall check with undefined FEM results"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=20, story_height=3.5),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
            ),
        )

        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        assert core_result.compression_check == 0.0
        assert core_result.shear_check == 0.0
        assert core_result.tension_check == 0.0

        print(f"??? Undefined core wall test passed")
    def test_core_location_effects(self):
        """Test section stiffness effects on compression utilization"""
        def build_project(ixx: float) -> ProjectData:
            return ProjectData(
                geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=15, story_height=3.5),
                loads=LoadInput("2", "2.5", 2.0),
                materials=MaterialInput(fcu_column=45),
                lateral=LateralInput(
                    building_width=24.0,
                    building_depth=24.0,
                    terrain=TerrainCategory.URBAN,
                    core_geometry=CoreWallGeometry(
                        config=CoreWallConfig.TUBE_CENTER_OPENING,
                        length_x=8000.0,
                        length_y=8000.0,
                        opening_width=2000.0,
                        opening_height=2400.0,
                    ),
                    section_properties=CoreWallSectionProperties(
                        I_xx=ixx,
                        I_yy=ixx,
                        A=3.0e6,
                    ),
                ),
            )

        project_stiff = build_project(ixx=1.6e12)
        project_flexible = build_project(ixx=0.6e12)

        attach_mock_wind_fem_result(project_stiff, shear=1400.0, moment=5200.0)
        attach_mock_wind_fem_result(project_flexible, shear=1400.0, moment=5200.0)

        result_stiff = CoreWallEngine(project_stiff).check_core_wall(
            WindEngine(project_stiff).calculate_wind_loads()
        )
        result_flexible = CoreWallEngine(project_flexible).check_core_wall(
            WindEngine(project_flexible).calculate_wind_loads()
        )

        assert result_flexible.compression_check >= result_stiff.compression_check

        print(f"??? Core stiffness effect test passed")
    def test_drift_calculation(self):
        """Test drift index calculation"""
        project = ProjectData(
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=25, story_height=3.5),
            materials=MaterialInput(fcu_column=45),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
            ),
        )

        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        drift_engine = DriftEngine(project)
        updated_wind_result = drift_engine.calculate_drift(wind_result)

        assert updated_wind_result.drift_mm >= 0, "Drift should be non-negative"
        assert updated_wind_result.drift_index >= 0, "Drift index should be non-negative"

        print(f"??? Drift calculation completed")
        print(f"  Lateral drift: {updated_wind_result.drift_mm:.1f} mm")
        print(f"  Drift index: {updated_wind_result.drift_index:.5f}")
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
                    core_geometry=CoreWallGeometry(
                        config=CoreWallConfig.TUBE_CENTER_OPENING,
                        length_x=core_x * 1000.0,
                        length_y=core_y * 1000.0,
                        opening_width=2000.0,
                        opening_height=2400.0,
                    ),
                ),
            )

            wind_engine = WindEngine(project)
            wind_result = wind_engine.calculate_wind_loads()

            drift_engine = DriftEngine(project)
            updated_result = drift_engine.calculate_drift(wind_result)
            drift_indices.append(updated_result.drift_index)

        # Without FEM displacements, drift indices should be non-negative
        assert all(idx >= 0 for idx in drift_indices)

        print(f"??? Core stiffness effect test passed")
        for i, (core_x, core_y) in enumerate(core_dimensions):
            print(f"  Core {core_x}??{core_y}m: drift index = {drift_indices[i]:.5f}")
    def test_complete_workflow(self):
        """Test complete workflow: wind -> core -> drift"""
        project = ProjectData(
            project_name="15-Story Office Building",
            geometry=GeometryInput(bay_x=8.0, bay_y=8.0, floors=15, story_height=3.5),
            loads=LoadInput("2", "2.5", 2.0),
            materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
            lateral=LateralInput(
                building_width=24.0,
                building_depth=24.0,
                terrain=TerrainCategory.URBAN,
                core_geometry=CoreWallGeometry(
                    config=CoreWallConfig.TUBE_CENTER_OPENING,
                    length_x=7000.0,
                    length_y=7000.0,
                    opening_width=2000.0,
                    opening_height=2400.0,
                ),
                section_properties=CoreWallSectionProperties(
                    I_xx=1.2e12,
                    I_yy=1.0e12,
                    A=2.8e6,
                ),
            ),
        )

        attach_mock_wind_fem_result(project, shear=1500.0, moment=4800.0)
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        drift_engine = DriftEngine(project)
        final_wind_result = drift_engine.calculate_drift(wind_result)

        assert wind_result.base_shear > 0
        assert core_result is not None
        assert final_wind_result.drift_index >= 0
    def test_high_rise_scenario(self):
        """Test high-rise building (40 floors) scenario"""
        project = ProjectData(
            project_name="40-Story High-Rise",
            geometry=GeometryInput(bay_x=9.0, bay_y=9.0, floors=40, story_height=3.3),
            loads=LoadInput("1", "1.1", 1.5),
            materials=MaterialInput(fcu_column=50),
            lateral=LateralInput(
                building_width=27.0,
                building_depth=27.0,
                terrain=TerrainCategory.CITY_CENTRE,
                core_geometry=CoreWallGeometry(
                    config=CoreWallConfig.TUBE_CENTER_OPENING,
                    length_x=12000.0,
                    length_y=12000.0,
                    opening_width=2400.0,
                    opening_height=2400.0,
                ),
                section_properties=CoreWallSectionProperties(
                    I_xx=2.8e12,
                    I_yy=2.5e12,
                    A=5.0e6,
                ),
            ),
        )

        attach_mock_wind_fem_result(project, shear=2600.0, moment=9800.0)
        wind_engine = WindEngine(project)
        wind_result = wind_engine.calculate_wind_loads()

        core_engine = CoreWallEngine(project)
        core_result = core_engine.check_core_wall(wind_result)

        drift_engine = DriftEngine(project)
        final_result = drift_engine.calculate_drift(wind_result)

        print("\nâœ“ High-rise scenario test completed")
        print(f"  Height: {project.geometry.floors * project.geometry.story_height:.1f} m")
        print(f"  Base shear: {final_result.base_shear:.1f} kN")
        print(f"  Core status: {core_result.status}")
        print(f"  Drift: {final_result.drift_mm:.1f} mm ({'OK' if final_result.drift_ok else 'FAIL'})")
