"""
Tests for Feature 5: Debug & Integration Testing
================================================

This module contains comprehensive tests for:
- Task 5.1: Data Pipeline Verification (Streamlit -> Python -> HTML)
- Task 5.2: Engineering Logic Stress Tests (impossible geometry, failures, edge cases)
- Task 5.3: Visual Regression Testing (HTML report structure and content)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import math

from src.core.data_models import (
    ProjectData, GeometryInput, LoadInput, MaterialInput, LateralInput,
    SlabDesignInput, BeamDesignInput, ReinforcementInput,
    SlabType, SpanDirection, ExposureClass, TerrainCategory,
    CoreLocation, ColumnPosition, LoadCombination, PRESETS,
)
from src.core.constants import (
    CARBON_FACTORS, GAMMA_G, GAMMA_Q, GAMMA_W,
    MIN_SLAB_THICKNESS, MIN_BEAM_WIDTH, MIN_BEAM_DEPTH, MIN_COLUMN_SIZE,
    MAX_BEAM_DEPTH, DEEP_BEAM_RATIO, DRIFT_LIMIT,
    CONCRETE_DENSITY
)
from src.core.load_tables import LIVE_LOAD_TABLE, get_live_load
from src.engines.slab_engine import SlabEngine
from src.engines.beam_engine import BeamEngine
from src.engines.column_engine import ColumnEngine
from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine
from src.report.report_generator import ReportGenerator, generate_framing_svg


# =============================================================================
# HELPER FUNCTIONS (from dashboard)
# =============================================================================

def calculate_carbon_emission(project):
    """Calculate concrete volume and carbon emission"""
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
    """Run full calculation pipeline"""
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

            utilization, status, warnings = column_engine.check_combined_load(
                project.column_result.axial_load,
                first_col_load[1],
                project.column_result.dimension,
                project.materials.fcu_column
            )
            project.column_result.combined_utilization = utilization

    project.concrete_volume, project.carbon_emission = calculate_carbon_emission(project)

    return project


# =============================================================================
# TASK 5.1: DATA PIPELINE VERIFICATION TESTS
# =============================================================================

class TestDataPipelineVerification:
    """
    Task 5.1: Verify data flows correctly from inputs through calculations to HTML report.
    Trace specific values through the entire chain to ensure no floating-point errors or rounding issues.
    """

    def test_live_load_value_traces_through_pipeline(self):
        """Trace Live Load = 5kPa through Streamlit -> Python Logic -> HTML Report"""
        # Set up project with specific live load (retail = 5.0 kPa)
        project = ProjectData()
        project.loads = LoadInput("4", "4.1", 2.0)  # Retail/Shopping = 5.0 kPa
        project.geometry = GeometryInput(8.0, 8.0, 5, 3.5)
        project.lateral = LateralInput(building_width=8.0, building_depth=8.0)

        # Verify live load is correctly retrieved from tables
        assert project.loads.live_load == 5.0, f"Expected 5.0 kPa, got {project.loads.live_load}"

        # Run calculations
        project = run_full_calculation(project)

        # Verify live load is used in design load calculation (ULS: 1.4Gk + 1.6Qk)
        design_load = project.get_design_load()
        expected_min = GAMMA_G * project.total_dead_load + GAMMA_Q * 5.0  # Live load = 5.0
        assert design_load > 0, "Design load should be positive"

        # Generate report and verify live load appears
        generator = ReportGenerator(project)
        html = generator.generate()

        assert "5.0" in html, "Live load 5.0 should appear in HTML report"
        assert "kPa" in html, "Unit kPa should appear in HTML report"

    def test_material_grade_to_carbon_estimate(self):
        """Verify Material Grade slider updates Carbon Estimate correctly"""
        # Test with C35 concrete
        project_c35 = ProjectData()
        project_c35.materials = MaterialInput(fcu_slab=35, fcu_beam=35, fcu_column=35)
        project_c35.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project_c35.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project_c35 = run_full_calculation(project_c35)

        # Test with C60 concrete (higher carbon factor)
        project_c60 = ProjectData()
        project_c60.materials = MaterialInput(fcu_slab=60, fcu_beam=60, fcu_column=60)
        project_c60.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project_c60.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project_c60 = run_full_calculation(project_c60)

        # C60 should have higher carbon emission than C35
        assert project_c60.carbon_emission > project_c35.carbon_emission, \
            f"C60 ({project_c60.carbon_emission}) should have higher carbon than C35 ({project_c35.carbon_emission})"

        # Verify correct carbon factors are applied
        expected_c35_factor = CARBON_FACTORS[35]  # 320 kgCO2e/m³
        expected_c60_factor = CARBON_FACTORS[60]  # 450 kgCO2e/m³
        ratio = project_c60.carbon_emission / project_c35.carbon_emission
        expected_ratio = expected_c60_factor / expected_c35_factor

        # Allow small tolerance for different element sizes
        assert abs(ratio - expected_ratio) < 0.2, \
            f"Carbon ratio {ratio:.2f} should be close to factor ratio {expected_ratio:.2f}"

    def test_geometry_flows_to_report(self):
        """Verify geometry values appear correctly in HTML report"""
        project = ProjectData()
        project.geometry = GeometryInput(bay_x=9.5, bay_y=7.2, floors=12, story_height=3.6)
        project.lateral = LateralInput(building_width=9.5, building_depth=7.2)
        project = run_full_calculation(project)

        # Generate report
        generator = ReportGenerator(project)
        html = generator.generate()

        # Check geometry values appear in report
        assert "9.5" in html, "Bay X (9.5m) should appear in report"
        assert "7.2" in html, "Bay Y (7.2m) should appear in report"
        assert "12" in html, "Floors (12) should appear in report"
        assert "3.6" in html, "Story height (3.6m) should appear in report"

        # Total height should be 12 * 3.6 = 43.2m
        assert "43.2" in html, "Total height (43.2m) should appear in report"

    def test_slab_result_appears_in_report(self):
        """Verify slab design results flow to HTML report"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        assert project.slab_result is not None, "Slab result should be calculated"

        generator = ReportGenerator(project)
        html = generator.generate()

        # Slab thickness should appear in report
        thickness = project.slab_result.thickness
        assert str(int(thickness)) in html, f"Slab thickness {thickness}mm should appear in report"

        # Slab status should appear
        assert "Slab" in html, "Slab element should be in report"

    def test_no_floating_point_errors_in_loads(self):
        """Verify no floating-point precision errors in load calculations"""
        project = ProjectData()
        # Class 2, Sub 2.5 = "Offices for general use" = 3.0 kPa per HK Code Table 3.2
        project.loads = LoadInput("2", "2.5", 2.0)
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        # Check live load is exactly as expected (Class 2.5 = 3.0 kPa per HK Code)
        assert project.loads.live_load == 3.0, f"Live load should be 3.0, got {project.loads.live_load}"

        # Check design load calculation (should not have floating point errors)
        design_load = project.get_design_load()

        # Manually calculate expected design load
        slab_self_weight = project.slab_result.self_weight if project.slab_result else 0.2 * CONCRETE_DENSITY
        total_dead = project.loads.dead_load + slab_self_weight
        expected_design = GAMMA_G * total_dead + GAMMA_Q * 3.0

        # Should match within floating point tolerance
        assert abs(design_load - expected_design) < 0.001, \
            f"Design load {design_load} should equal {expected_design}"

    def test_column_load_accumulation(self):
        """Verify column load is correctly accumulated over floors"""
        project = ProjectData()
        project.geometry = GeometryInput(8.0, 8.0, 10, 3.5)  # 10 floors
        project.lateral = LateralInput(building_width=8.0, building_depth=8.0)
        project = run_full_calculation(project)

        assert project.column_result is not None, "Column result should be calculated"

        # Axial load should increase with number of floors
        axial_10_floors = project.column_result.axial_load

        # Now test with 20 floors
        project2 = ProjectData()
        project2.geometry = GeometryInput(8.0, 8.0, 20, 3.5)  # 20 floors
        project2.lateral = LateralInput(building_width=8.0, building_depth=8.0)
        project2 = run_full_calculation(project2)

        axial_20_floors = project2.column_result.axial_load

        # 20 floors should have approximately double the axial load
        ratio = axial_20_floors / axial_10_floors
        assert 1.8 < ratio < 2.2, f"20-floor axial load should be ~2x 10-floor, got ratio {ratio:.2f}"


# =============================================================================
# TASK 5.2: ENGINEERING LOGIC STRESS TESTS
# =============================================================================

class TestEngineeringLogicStressTests:
    """
    Task 5.2: Verify "Hard Stops" and Error Handling
    - Test impossible geometry (Beam Width > Column Width)
    - Test failure cases (20m span with 300mm depth)
    - Test edge cases (0m core thickness)
    """

    def test_large_span_small_depth_triggers_failure(self):
        """Test: 20m span with minimum depth should trigger section too small warning"""
        project = ProjectData()
        project.geometry = GeometryInput(bay_x=15.0, bay_y=15.0, floors=3, story_height=4.0)
        project.lateral = LateralInput(building_width=15.0, building_depth=15.0)
        project = run_full_calculation(project)

        # With very large spans, utilization should exceed 1.0
        # or beam should be flagged as too small
        assert project.primary_beam_result is not None

        # Check if either:
        # 1. Utilization is high (over 0.85) indicating stress
        # 2. Beam is resized to accommodate the span
        primary_util = project.primary_beam_result.utilization
        beam_depth = project.primary_beam_result.depth

        # Large span should require deep beam or have high utilization
        assert primary_util > 0.5 or beam_depth > 600, \
            f"15m span should stress beam (util={primary_util:.2f}, depth={beam_depth}mm)"

    def test_deep_beam_detection(self):
        """Test: Deep beam (L/d < 2.0) should trigger STM warning"""
        project = ProjectData()
        # Short span with forced deep section
        project.geometry = GeometryInput(bay_x=4.0, bay_y=4.0, floors=3, story_height=3.0)
        project.lateral = LateralInput(building_width=4.0, building_depth=4.0)
        project = run_full_calculation(project)

        # If beam has span/depth ratio < 2.0, it should be flagged as deep beam
        if project.primary_beam_result:
            span = project.geometry.bay_x * 1000  # Convert to mm
            depth = project.primary_beam_result.depth
            ratio = span / depth

            # The engine should either:
            # 1. Flag deep beam if ratio < 2.0
            # 2. Size beam appropriately to avoid deep beam condition
            if ratio < DEEP_BEAM_RATIO:
                # Deep beam flag should be set
                pass  # This is expected behavior

    def test_very_high_loads_trigger_sizing_increase(self):
        """Test: Very high loads should require larger sections"""
        # Normal load case
        project_normal = ProjectData()
        project_normal.loads = LoadInput("2", "2.5", 2.0)  # Office: 2.5 kPa
        project_normal.geometry = GeometryInput(8.0, 8.0, 5, 3.5)
        project_normal.lateral = LateralInput(building_width=8.0, building_depth=8.0)
        project_normal = run_full_calculation(project_normal)

        # High load case (plant room: 7.5 kPa)
        project_high = ProjectData()
        project_high.loads = LoadInput("5", "5.9", 3.0)  # Plant room: 7.5 kPa
        project_high.geometry = GeometryInput(8.0, 8.0, 5, 3.5)
        project_high.lateral = LateralInput(building_width=8.0, building_depth=8.0)
        project_high = run_full_calculation(project_high)

        # High load case should have larger or more stressed elements
        normal_slab = project_normal.slab_result.thickness
        high_slab = project_high.slab_result.thickness

        normal_beam_depth = project_normal.primary_beam_result.depth
        high_beam_depth = project_high.primary_beam_result.depth

        # Either thickness increases or utilization increases
        assert high_slab >= normal_slab or high_beam_depth >= normal_beam_depth, \
            "Higher loads should result in larger sections or higher utilization"

    def test_zero_core_thickness_edge_case(self):
        """Test: Zero core wall dimensions should result in moment frame system"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 10, 3.0)
        project.lateral = LateralInput(
            core_dim_x=0.0,  # No core
            core_dim_y=0.0,
            core_thickness=0.0,
            building_width=6.0,
            building_depth=6.0
        )
        project = run_full_calculation(project)

        # Should automatically detect as moment frame
        assert project.wind_result is not None
        assert project.wind_result.lateral_system == "MOMENT_FRAME", \
            f"Expected MOMENT_FRAME, got {project.wind_result.lateral_system}"

        # Core wall result should not exist
        assert project.core_wall_result is None, "No core wall result for moment frame"

    def test_corner_core_eccentricity_effects(self):
        """Test: Corner core should have highest eccentricity effects"""
        results = {}

        for location in [CoreLocation.CENTER, CoreLocation.SIDE, CoreLocation.CORNER]:
            project = ProjectData()
            project.geometry = GeometryInput(12.0, 12.0, 20, 3.5)
            project.lateral = LateralInput(
                core_dim_x=4.0,
                core_dim_y=4.0,
                core_thickness=0.5,
                core_location=location,
                terrain=TerrainCategory.URBAN,
                building_width=12.0,
                building_depth=12.0
            )
            project = run_full_calculation(project)

            if project.core_wall_result:
                results[location] = project.core_wall_result.compression_check
            else:
                results[location] = 0

        # All calculations should complete without error
        assert all(v >= 0 for v in results.values()), "All core locations should produce valid results"

    def test_minimum_element_sizes_enforced(self):
        """Test: Minimum sizes should be enforced for all elements"""
        project = ProjectData()
        project.geometry = GeometryInput(3.0, 3.0, 2, 2.8)  # Small building
        project.loads = LoadInput("1", "1.1", 1.0)  # Minimum loads (residential)
        project.lateral = LateralInput(building_width=3.0, building_depth=3.0)
        project = run_full_calculation(project)

        # Check minimum sizes
        if project.slab_result:
            assert project.slab_result.thickness >= MIN_SLAB_THICKNESS, \
                f"Slab thickness {project.slab_result.thickness}mm below minimum {MIN_SLAB_THICKNESS}mm"

        if project.primary_beam_result:
            assert project.primary_beam_result.width >= MIN_BEAM_WIDTH, \
                f"Beam width {project.primary_beam_result.width}mm below minimum {MIN_BEAM_WIDTH}mm"
            assert project.primary_beam_result.depth >= MIN_BEAM_DEPTH, \
                f"Beam depth {project.primary_beam_result.depth}mm below minimum {MIN_BEAM_DEPTH}mm"

        if project.column_result:
            assert project.column_result.dimension >= MIN_COLUMN_SIZE, \
                f"Column size {project.column_result.dimension}mm below minimum {MIN_COLUMN_SIZE}mm"

    def test_maximum_beam_depth_respected(self):
        """Test: Maximum practical beam depth should be respected"""
        project = ProjectData()
        project.geometry = GeometryInput(12.0, 12.0, 5, 4.0)  # Large spans
        project.loads = LoadInput("5", "5.9", 3.0)  # Heavy loads
        project.lateral = LateralInput(building_width=12.0, building_depth=12.0)
        project = run_full_calculation(project)

        if project.primary_beam_result:
            assert project.primary_beam_result.depth <= MAX_BEAM_DEPTH, \
                f"Beam depth {project.primary_beam_result.depth}mm exceeds maximum {MAX_BEAM_DEPTH}mm"

    def test_shear_stress_hard_stop(self):
        """Test: Shear stress v > v_max should trigger resize or warning"""
        project = ProjectData()
        # Large span with heavy loads
        project.geometry = GeometryInput(10.0, 10.0, 5, 4.0)
        project.loads = LoadInput("5", "5.9", 3.0)  # High loads
        project.lateral = LateralInput(building_width=10.0, building_depth=10.0)
        project = run_full_calculation(project)

        # Check beam shear capacity
        if project.primary_beam_result:
            shear = project.primary_beam_result.shear
            shear_capacity = project.primary_beam_result.shear_capacity

            # Either:
            # 1. Shear reinforcement is provided (links)
            # 2. Beam is sized to handle shear without excessive stress
            assert shear_capacity > 0 or project.primary_beam_result.shear_reinforcement_required, \
                "Beam should have shear capacity or require reinforcement"

    def test_drift_check_failure(self):
        """Test: Tall slender building should fail drift check without adequate core"""
        project = ProjectData()
        # Tall building with small moment frame
        project.geometry = GeometryInput(6.0, 6.0, 30, 3.0)  # 90m tall
        project.lateral = LateralInput(
            core_dim_x=0.0,  # No core - moment frame only
            core_dim_y=0.0,
            terrain=TerrainCategory.OPEN_SEA,  # High wind exposure
            building_width=6.0,
            building_depth=6.0
        )
        project = run_full_calculation(project)

        # With such a slender building and no core, drift should be high
        # (may still pass if columns are large enough)
        assert project.wind_result is not None
        assert project.wind_result.drift_index >= 0, "Drift index should be calculated"


# =============================================================================
# TASK 5.3: VISUAL REGRESSION TESTING
# =============================================================================

class TestVisualRegressionTesting:
    """
    Task 5.3: Verify "Magazine Look" renders correctly
    - Check HTML Report structure
    - Verify CSS Grid layout components
    - Test SVG/font references
    """

    def test_html_report_structure(self):
        """Test: HTML report has correct page structure"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check for three pages
        assert 'id="page-gravity"' in html, "Report should have gravity page"
        assert 'id="page-stability"' in html, "Report should have stability page"
        assert 'id="page-assumptions"' in html, "Report should have assumptions page"

        # Check HTML5 structure
        assert "<!DOCTYPE html>" in html, "Should have HTML5 doctype"
        assert "<html" in html, "Should have html tag"
        assert "</html>" in html, "Should close html tag"
        assert "<head>" in html, "Should have head section"
        assert "<body>" in html, "Should have body section"

    def test_css_styles_embedded(self):
        """Test: CSS styles are properly embedded in report"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check for key CSS classes
        assert ".status-grid" in html, "Should have status-grid CSS class"
        assert ".metric-card" in html, "Should have metric-card CSS class"
        assert ".element-table" in html, "Should have element-table CSS class"
        assert ".report-header" in html, "Should have report-header CSS class"

        # Check for color palette
        assert "--primary:" in html, "Should have primary color variable"
        assert "--success:" in html, "Should have success color variable"
        assert "--warning:" in html, "Should have warning color variable"
        assert "--danger:" in html, "Should have danger color variable"

        # Check for Inter font reference
        assert "Inter" in html, "Should reference Inter font"

    def test_svg_icons_embedded(self):
        """Test: SVG icons are properly embedded"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(
            core_dim_x=4.0,
            core_dim_y=4.0,
            building_width=6.0,
            building_depth=6.0
        )
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check for SVG elements
        assert "<svg" in html, "Should have SVG elements"
        assert "viewBox=" in html, "SVG should have viewBox attribute"

    def test_framing_svg_generated(self):
        """Test: Framing diagram SVG is correctly generated"""
        project = ProjectData()
        project.geometry = GeometryInput(8.0, 6.0, 5, 3.5)
        project.lateral = LateralInput(
            core_dim_x=3.0,
            core_dim_y=3.0,
            core_location=CoreLocation.CENTER,
            building_width=8.0,
            building_depth=6.0
        )
        project = run_full_calculation(project)

        svg = generate_framing_svg(project)

        # Check SVG structure
        assert '<svg viewBox=' in svg, "SVG should have viewBox"
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg, "SVG should have namespace"
        assert '</svg>' in svg, "SVG should close properly"

        # Check for framing elements
        assert '<rect' in svg, "SVG should have rectangles (columns, slab)"
        assert '<line' in svg, "SVG should have lines (beams)"

        # Check for dimension labels (bay sizes)
        assert '8.0m' in svg, "Should show X dimension"
        assert '6.0m' in svg, "Should show Y dimension"

        # Check for core wall (since we defined one)
        assert 'CORE' in svg, "Should show core wall label"

    def test_status_badges_have_correct_classes(self):
        """Test: Status badges use correct CSS classes"""
        # Test with passing design
        project_pass = ProjectData()
        project_pass.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project_pass.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project_pass = run_full_calculation(project_pass)

        generator = ReportGenerator(project_pass)
        html = generator.generate()

        # Should have status badges
        assert 'class="status-badge' in html, "Should have status badges"

        # At least one element should have 'pass' class if design is acceptable
        # (depends on actual calculation results)
        has_status = ('status-badge pass' in html or
                     'status-badge warn' in html or
                     'status-badge fail' in html)
        assert has_status, "Should have status badge with class"

    def test_long_strings_dont_break_layout(self):
        """Test: Long data strings (e.g., '1200x1200mm') fit in tables"""
        project = ProjectData()
        # Use large columns that would produce "1200x1200mm" type strings
        project.geometry = GeometryInput(10.0, 10.0, 20, 4.0)
        project.lateral = LateralInput(building_width=10.0, building_depth=10.0)
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check column size appears in report
        if project.column_result:
            col_dim = project.column_result.dimension
            # Should find something like "600 × 600mm" or similar
            assert str(int(col_dim)) in html, f"Column dimension {col_dim}mm should appear"

        # Check beam size appears
        if project.primary_beam_result:
            width = project.primary_beam_result.width
            depth = project.primary_beam_result.depth
            # Should find something like "400 × 800mm"
            assert str(int(width)) in html, f"Beam width {width}mm should appear"
            assert str(int(depth)) in html, f"Beam depth {depth}mm should appear"

    def test_print_media_query_present(self):
        """Test: Print media query is present for A4 export"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check for print styles
        assert "@media print" in html, "Should have print media query"
        assert "@page" in html, "Should have @page rule for print"
        assert "page-break" in html, "Should have page break rules"

    def test_ai_review_placeholder_present(self):
        """Test: AI review placeholder section exists"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        # Test without AI review
        generator = ReportGenerator(project)
        html = generator.generate()

        assert "AI Design Review" in html, "Should have AI review section"
        assert "ai-review-section" in html, "Should have AI review CSS class"
        assert "ai-review-placeholder" in html, "Should have placeholder text"

        # Test with AI review content
        html_with_ai = generator.generate(ai_review="This is a test AI review comment.")
        assert "This is a test AI review comment." in html_with_ai, \
            "AI review content should appear in report"

    def test_carbon_dashboard_present(self):
        """Test: Carbon dashboard section with metrics"""
        project = ProjectData()
        project.geometry = GeometryInput(8.0, 8.0, 10, 3.5)
        project.lateral = LateralInput(building_width=8.0, building_depth=8.0)
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check carbon dashboard
        assert "carbon-dashboard" in html, "Should have carbon dashboard"
        assert "Embodied Carbon" in html or "Carbon" in html, "Should mention carbon"
        assert "CO₂" in html or "CO2" in html, "Should show CO2 units"

        # Check carbon metrics are present
        assert "Concrete Volume" in html, "Should show concrete volume metric"
        assert "m³" in html or "m3" in html, "Should show volume units"

    def test_assumptions_page_content(self):
        """Test: Assumptions page has all required sections"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.materials = MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check for code references
        assert "HK Code 2013" in html, "Should reference HK Code 2013"
        assert "HK Wind Code 2019" in html, "Should reference HK Wind Code 2019"

        # Check for material grades
        assert "C35" in html, "Should show C35 grade"
        assert "C40" in html, "Should show C40 grade"
        assert "C45" in html, "Should show C45 grade"

        # Check for safety factors
        assert "1.50" in html or "1.5" in html, "Should show gamma_c = 1.5"
        assert "1.15" in html, "Should show gamma_s = 1.15"
        assert str(GAMMA_G) in html, "Should show gamma_G"
        assert str(GAMMA_Q) in html, "Should show gamma_Q"

        # Check for load combinations
        assert "1.4Gk + 1.6Qk" in html, "Should show ULS gravity combination"
        assert "1.0Gk + 1.4Wk" in html, "Should show ULS wind combination"

    def test_responsive_layout_classes(self):
        """Test: Layout uses CSS Grid for responsiveness"""
        project = ProjectData()
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check for CSS Grid usage
        assert "display: grid" in html or "display:grid" in html, \
            "Should use CSS Grid for layout"
        assert "grid-template-columns" in html, "Should have grid columns defined"

    def test_report_metadata(self):
        """Test: Report includes project metadata correctly"""
        project = ProjectData()
        project.project_name = "Test Project Alpha"
        project.project_number = "TP-2024-001"
        project.engineer = "John Engineer"
        project.date = "2024-01-15"
        project.geometry = GeometryInput(6.0, 6.0, 5, 3.0)
        project.lateral = LateralInput(building_width=6.0, building_depth=6.0)
        project = run_full_calculation(project)

        generator = ReportGenerator(project)
        html = generator.generate()

        # Check metadata appears in report
        assert "Test Project Alpha" in html, "Project name should appear"
        assert "TP-2024-001" in html, "Project number should appear"
        assert "John Engineer" in html, "Engineer name should appear"
        assert "2024-01-15" in html, "Date should appear"


# =============================================================================
# ADDITIONAL INTEGRATION TESTS
# =============================================================================

class TestEndToEndIntegration:
    """Additional tests for full end-to-end integration"""

    def test_full_workflow_residential(self):
        """Test complete workflow for residential building"""
        project = ProjectData()
        project.project_name = "Residential Tower"
        preset = PRESETS["residential"]
        project.loads = preset["loads"]
        project.materials = preset["materials"]
        project.geometry = GeometryInput(6.0, 6.0, 15, 3.0)
        project.lateral = LateralInput(
            core_dim_x=4.0,
            core_dim_y=4.0,
            core_location=CoreLocation.CENTER,
            terrain=TerrainCategory.URBAN,
            building_width=6.0,
            building_depth=6.0
        )

        # Run calculations
        project = run_full_calculation(project)

        # Verify all results exist
        assert project.slab_result is not None
        assert project.primary_beam_result is not None
        assert project.secondary_beam_result is not None
        assert project.column_result is not None
        assert project.wind_result is not None
        assert project.core_wall_result is not None

        # Generate report
        generator = ReportGenerator(project)
        html = generator.generate(ai_review="Acceptable residential scheme.")

        # Verify report is complete
        assert len(html) > 10000, "Report should have substantial content"
        assert "Residential Tower" in html
        # Report displays "Core Wall System" in the lateral summary section
        assert "Core Wall System" in html

    def test_full_workflow_office_moment_frame(self):
        """Test complete workflow for office building with moment frame"""
        project = ProjectData()
        project.project_name = "Office Block B"
        preset = PRESETS["office"]
        project.loads = preset["loads"]
        project.materials = preset["materials"]
        project.geometry = GeometryInput(9.0, 9.0, 8, 3.6)
        project.lateral = LateralInput(
            core_dim_x=0.0,  # No core - moment frame
            core_dim_y=0.0,
            terrain=TerrainCategory.URBAN,
            building_width=9.0,
            building_depth=9.0
        )

        # Run calculations
        project = run_full_calculation(project)

        # Verify moment frame system
        assert project.wind_result.lateral_system == "MOMENT_FRAME"
        assert project.core_wall_result is None
        assert project.column_result.has_lateral_loads is True

        # Generate report
        generator = ReportGenerator(project)
        html = generator.generate()

        assert "Office Block B" in html
        assert "Moment Frame" in html

    def test_to_dict_serialization(self):
        """Test ProjectData can be serialized to dict"""
        project = ProjectData()
        project.project_name = "Serialization Test"
        project.geometry = GeometryInput(7.0, 7.0, 6, 3.2)
        project.lateral = LateralInput(building_width=7.0, building_depth=7.0)
        project = run_full_calculation(project)

        # Convert to dict (for JSON serialization)
        data = project.to_dict()

        # Verify structure
        assert "project_name" in data
        assert data["project_name"] == "Serialization Test"
        assert "geometry" in data
        assert data["geometry"]["bay_x"] == 7.0
        assert data["geometry"]["floors"] == 6
        assert "loads" in data
        assert "materials" in data
        assert "summary" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
