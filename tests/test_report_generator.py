"""
Tests for the Magazine-Style Report Generator

Tests cover:
- Report generation with complete project data
- Status badge generation
- Element summary table
- Lateral system data
- Carbon emission calculations
- SVG framing diagram
- HTML output validation
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.data_models import (
    ProjectData, GeometryInput, LoadInput, MaterialInput,
    ReinforcementInput, SlabDesignInput, BeamDesignInput,
    LateralInput, SlabResult, BeamResult, ColumnResult,
    WindResult, CoreWallResult, LoadCombination,
    ExposureClass, TerrainCategory, CoreWallGeometry, CoreWallConfig
)
from src.report.report_generator import (
    ReportGenerator, generate_report, generate_framing_svg, SVG_ICONS
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_project():
    """Create a sample project with all calculation results."""
    project = ProjectData(
        project_name="Test Building",
        project_number="TB-001",
        engineer="Test Engineer",
        date=datetime.now().strftime("%Y-%m-%d"),
        geometry=GeometryInput(
            bay_x=8.0,
            bay_y=6.0,
            floors=10,
            story_height=3.5
        ),
        loads=LoadInput(
            live_load_class="2",
            live_load_sub="2.5",
            dead_load=1.5
        ),
        materials=MaterialInput(
            fcu_slab=35,
            fcu_beam=40,
            fcu_column=45,
            exposure=ExposureClass.MODERATE
        ),
        reinforcement=ReinforcementInput(),
        slab_design=SlabDesignInput(),
        beam_design=BeamDesignInput(),
        lateral=LateralInput(
            terrain=TerrainCategory.URBAN,
            building_width=8.0,
            building_depth=6.0,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                length_x=6000.0,
                length_y=4000.0,
                opening_width=2000.0,
                opening_height=2400.0,
            ),
        ),
        load_combination=LoadCombination.ULS_GRAVITY_1
    )

    # Add slab result
    project.slab_result = SlabResult(
        element_type="slab",
        size="175mm",
        thickness=175,
        moment=25.5,
        reinforcement_area=450,
        deflection_ratio=28.5,
        self_weight=4.3,
        utilization=0.72,
        status="OK",
        warnings=[],
        calculations=[]
    )

    # Add primary beam result
    project.primary_beam_result = BeamResult(
        element_type="primary_beam",
        size="300x600",
        width=300,
        depth=600,
        moment=185.0,
        shear=125.0,
        shear_capacity=180.0,
        link_spacing=150,
        is_deep_beam=False,
        utilization=0.68,
        status="OK",
        warnings=[],
        calculations=[]
    )

    # Add secondary beam result
    project.secondary_beam_result = BeamResult(
        element_type="secondary_beam",
        size="250x500",
        width=250,
        depth=500,
        moment=95.0,
        shear=75.0,
        shear_capacity=120.0,
        link_spacing=175,
        is_deep_beam=False,
        utilization=0.55,
        status="OK",
        warnings=[],
        calculations=[]
    )

    # Add column result
    project.column_result = ColumnResult(
        element_type="column",
        size="450x450",
        dimension=450,
        axial_load=2850.0,
        moment=45.0,
        slenderness=12.5,
        lateral_shear=0,
        lateral_moment=0,
        utilization=0.78,
        status="OK",
        warnings=[],
        calculations=[]
    )

    # Add wind result
    project.wind_result = WindResult(
        base_shear=485.0,
        overturning_moment=8500.0,
        reference_pressure=2.85,
        drift_mm=28.5,
        drift_index=0.00081,
        drift_ok=True,
        lateral_system="CORE_WALL"
    )

    # Add core wall result
    project.core_wall_result = CoreWallResult(
        element_type="core_wall",
        size="6.0x4.0m",
        compression_check=0.45,
        tension_check=0.15,
        shear_check=0.32,
        requires_tension_piles=False,
        utilization=0.45,
        status="OK",
        warnings=[],
        calculations=[]
    )

    # Set carbon metrics
    project.concrete_volume = 125.5
    project.carbon_emission = 42500.0  # kgCO2e

    return project


@pytest.fixture
def moment_frame_project():
    """Create a project without core wall (moment frame system)."""
    project = ProjectData(
        project_name="Moment Frame Building",
        project_number="MF-001",
        engineer="Test Engineer",
        date=datetime.now().strftime("%Y-%m-%d"),
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=6.0,
            floors=5,
            story_height=3.2
        ),
        loads=LoadInput(
            live_load_class="2",
            live_load_sub="2.5",
            dead_load=1.5
        ),
        materials=MaterialInput(
            fcu_slab=30,
            fcu_beam=35,
            fcu_column=40,
            exposure=ExposureClass.MILD
        ),
        reinforcement=ReinforcementInput(),
        slab_design=SlabDesignInput(),
        beam_design=BeamDesignInput(),
        lateral=LateralInput(
            terrain=TerrainCategory.CITY_CENTRE,
            building_width=6.0,
            building_depth=6.0,
        ),
        load_combination=LoadCombination.ULS_GRAVITY_1
    )

    # Add minimal results
    project.slab_result = SlabResult(
        element_type="slab", size="150mm",
        thickness=150, moment=18.0, reinforcement_area=380,
        deflection_ratio=30.0, self_weight=3.7, utilization=0.65,
        status="OK", warnings=[], calculations=[]
    )

    project.primary_beam_result = BeamResult(
        element_type="primary_beam", size="300x500",
        width=300, depth=500, moment=120.0, shear=85.0,
        shear_capacity=150.0, link_spacing=175, is_deep_beam=False,
        utilization=0.58, status="OK", warnings=[], calculations=[]
    )

    project.secondary_beam_result = BeamResult(
        element_type="secondary_beam", size="250x450",
        width=250, depth=450, moment=80.0, shear=60.0,
        shear_capacity=100.0, link_spacing=200, is_deep_beam=False,
        utilization=0.52, status="OK", warnings=[], calculations=[]
    )

    project.column_result = ColumnResult(
        element_type="column", size="400x400",
        dimension=400, axial_load=1850.0, moment=35.0, slenderness=10.0,
        lateral_shear=25.0, lateral_moment=80.0, utilization=0.72,
        status="OK", warnings=[], calculations=[]
    )

    project.wind_result = WindResult(
        base_shear=180.0, overturning_moment=1450.0, reference_pressure=2.45,
        drift_mm=12.5, drift_index=0.00078, drift_ok=True,
        lateral_system="MOMENT_FRAME"
    )

    project.concrete_volume = 65.0
    project.carbon_emission = 21000.0

    return project


# =============================================================================
# BASIC REPORT GENERATION TESTS
# =============================================================================

class TestReportGenerator:
    """Test ReportGenerator class functionality."""

    def test_report_generation(self, sample_project):
        """Test basic report generation."""
        generator = ReportGenerator(sample_project)
        html = generator.generate()

        assert html is not None
        assert len(html) > 1000
        assert "<!DOCTYPE html>" in html
        assert "Test Building" in html

    def test_report_contains_project_info(self, sample_project):
        """Test that report contains project metadata."""
        generator = ReportGenerator(sample_project)
        html = generator.generate()

        assert sample_project.project_name in html
        assert sample_project.project_number in html
        assert sample_project.engineer in html

    def test_report_contains_all_pages(self, sample_project):
        """Test that report contains all three pages."""
        generator = ReportGenerator(sample_project)
        html = generator.generate()

        assert 'id="page-gravity"' in html
        assert 'id="page-stability"' in html
        assert 'id="page-assumptions"' in html

    def test_report_contains_css_styles(self, sample_project):
        """Test that CSS styles are embedded."""
        generator = ReportGenerator(sample_project)
        html = generator.generate()

        assert "<style>" in html
        assert "--primary:" in html
        assert ".status-card" in html


# =============================================================================
# STATUS AND UTILIZATION TESTS
# =============================================================================

class TestStatusGeneration:
    """Test status badge and utilization calculations."""

    def test_status_class_pass(self, sample_project):
        """Test status class for passing elements."""
        generator = ReportGenerator(sample_project)
        assert generator._get_status_class(0.5) == "pass"
        assert generator._get_status_class(0.84) == "pass"

    def test_status_class_warn(self, sample_project):
        """Test status class for warning elements."""
        generator = ReportGenerator(sample_project)
        assert generator._get_status_class(0.86) == "warn"
        assert generator._get_status_class(0.99) == "warn"

    def test_status_class_fail(self, sample_project):
        """Test status class for failing elements."""
        generator = ReportGenerator(sample_project)
        assert generator._get_status_class(1.01) == "fail"
        assert generator._get_status_class(1.5) == "fail"

    def test_overall_status_satisfactory(self, sample_project):
        """Test overall status calculation for good design."""
        generator = ReportGenerator(sample_project)
        status = generator._get_overall_status()
        assert status == "SATISFACTORY"

    def test_status_elements_built(self, sample_project):
        """Test that status elements are built correctly."""
        generator = ReportGenerator(sample_project)
        elements = generator._build_status_elements()

        assert len(elements) == 5  # Slab, Primary, Secondary, Column, Drift
        assert elements[0]['name'] == 'Slab'
        assert 'icon' in elements[0]
        assert 'utilization' in elements[0]


# =============================================================================
# ELEMENT SUMMARY TESTS
# =============================================================================

class TestElementSummary:
    """Test element summary table generation."""

    def test_element_summary_complete(self, sample_project):
        """Test that element summary includes all elements."""
        generator = ReportGenerator(sample_project)
        summary = generator._build_element_summary()

        assert len(summary) == 4  # Slab, Primary, Secondary, Column
        names = [e['name'] for e in summary]
        assert 'Slab' in names
        assert 'Primary Beam' in names
        assert 'Column' in names

    def test_element_summary_formatting(self, sample_project):
        """Test element summary data formatting."""
        generator = ReportGenerator(sample_project)
        summary = generator._build_element_summary()

        slab = next(e for e in summary if e['name'] == 'Slab')
        assert '175' in slab['size']
        assert slab['grade'] == 35
        assert slab['status'] == 'OK'


# =============================================================================
# LATERAL SYSTEM TESTS
# =============================================================================

class TestLateralData:
    """Test lateral system data generation."""

    def test_core_wall_system_data(self, sample_project):
        """Test lateral data for core wall system."""
        generator = ReportGenerator(sample_project)
        lateral = generator._build_lateral_data()

        assert lateral['has_core'] is True
        assert lateral['system_type'] == 'Core Wall System'
        assert '6.0' in lateral['core_size']
        assert lateral['core_location'] == 'CENTER'

    def test_moment_frame_system_data(self, moment_frame_project):
        """Test lateral data for moment frame system."""
        generator = ReportGenerator(moment_frame_project)
        lateral = generator._build_lateral_data()

        assert lateral['has_core'] is False
        assert lateral['system_type'] == 'Moment Frame System'

    def test_wind_values_present(self, sample_project):
        """Test that wind loading values are present."""
        generator = ReportGenerator(sample_project)
        lateral = generator._build_lateral_data()

        assert lateral['base_shear'] == '485'
        assert lateral['overturning_moment'] == '8500'


# =============================================================================
# DRIFT CHECK TESTS
# =============================================================================

class TestDriftData:
    """Test drift check data generation."""

    def test_drift_data_values(self, sample_project):
        """Test drift data values."""
        generator = ReportGenerator(sample_project)
        drift = generator._build_drift_data()

        assert drift['drift_mm'] == '28.5'
        assert drift['status'] == 'OK'
        assert drift['status_class'] == 'pass'

    def test_drift_ratio_calculation(self, sample_project):
        """Test drift ratio calculation."""
        generator = ReportGenerator(sample_project)
        drift = generator._build_drift_data()

        # Drift ratio should be calculated from drift_index
        assert drift['drift_ratio'] != '—'


# =============================================================================
# CARBON DATA TESTS
# =============================================================================

class TestCarbonData:
    """Test carbon emission data generation."""

    def test_carbon_values(self, sample_project):
        """Test carbon emission values."""
        generator = ReportGenerator(sample_project)
        carbon = generator._build_carbon_data()

        assert carbon['volume'] == '125.5'
        assert float(carbon['emission']) > 0
        assert float(carbon['intensity']) > 0


# =============================================================================
# SVG DIAGRAM TESTS
# =============================================================================

class TestFramingSVG:
    """Test SVG framing diagram generation."""

    def test_svg_generation(self, sample_project):
        """Test basic SVG generation."""
        svg = generate_framing_svg(sample_project)

        assert svg is not None
        assert '<svg' in svg
        assert '</svg>' in svg

    def test_svg_contains_dimensions(self, sample_project):
        """Test that SVG contains dimension labels."""
        svg = generate_framing_svg(sample_project)

        assert '8.0m' in svg or '8m' in svg
        assert '6.0m' in svg or '6m' in svg

    def test_svg_contains_core(self, sample_project):
        """Test that SVG contains core wall when present."""
        svg = generate_framing_svg(sample_project)

        assert 'CORE' in svg

    def test_svg_no_core_moment_frame(self, moment_frame_project):
        """Test that SVG doesn't show core for moment frame."""
        svg = generate_framing_svg(moment_frame_project)

        # Core label shouldn't appear since core_dim = 0
        # The SVG conditional section won't be added
        assert svg.count('CORE') == 0


# =============================================================================
# SVG ICONS TESTS
# =============================================================================

class TestSVGIcons:
    """Test SVG icons availability."""

    def test_all_icons_present(self):
        """Test that all required icons are defined."""
        required_icons = ['concrete', 'steel', 'wind', 'check', 'warning',
                          'error', 'building', 'carbon', 'ruler', 'core']

        for icon in required_icons:
            assert icon in SVG_ICONS
            assert '<svg' in SVG_ICONS[icon]


# =============================================================================
# FILE SAVE TESTS
# =============================================================================

class TestReportSave:
    """Test report file saving functionality."""

    def test_save_report(self, sample_project, tmp_path):
        """Test saving report to file."""
        filepath = tmp_path / "test_report.html"
        generator = ReportGenerator(sample_project)
        saved_path = generator.save(str(filepath))

        assert Path(saved_path).exists()
        with open(saved_path, 'r') as f:
            content = f.read()
        assert "Test Building" in content

    def test_convenience_function_save(self, sample_project, tmp_path):
        """Test convenience function with filepath."""
        filepath = tmp_path / "convenience_report.html"
        result = generate_report(sample_project, filepath=str(filepath))

        assert Path(result).exists()

    def test_convenience_function_string(self, sample_project):
        """Test convenience function returning HTML string."""
        result = generate_report(sample_project)

        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result


# =============================================================================
# AI REVIEW PLACEHOLDER TESTS
# =============================================================================

class TestAIReview:
    """Test AI review placeholder functionality."""

    def test_placeholder_shown_without_review(self, sample_project):
        """Test that placeholder is shown when no AI review provided."""
        generator = ReportGenerator(sample_project)
        html = generator.generate()

        assert "ai-review-placeholder" in html
        assert "AI design review commentary will be generated" in html

    def test_ai_review_injected(self, sample_project):
        """Test that AI review is injected when provided."""
        generator = ReportGenerator(sample_project)
        ai_review = "This is a custom AI review comment for testing."
        html = generator.generate(ai_review=ai_review)

        assert ai_review in html


# =============================================================================
# LOAD COMBINATION TESTS
# =============================================================================

class TestLoadCombinations:
    """Test load combination display."""

    def test_uls_gravity_display(self, sample_project):
        """Test ULS gravity combination display."""
        sample_project.load_combination = LoadCombination.ULS_GRAVITY_1
        generator = ReportGenerator(sample_project)
        name = generator._get_load_combination_name()

        assert "ULS Gravity" in name
        assert "1.4Gk" in name

    def test_uls_wind_display(self, sample_project):
        """Test ULS wind combination display."""
        sample_project.load_combination = LoadCombination.ULS_WIND_1
        generator = ReportGenerator(sample_project)
        name = generator._get_load_combination_name()

        assert "ULS Wind" in name
        assert "1.4Wk" in name


# =============================================================================
# INTEGRATION TEST
# =============================================================================

class TestReportIntegration:
    """Integration tests for complete report generation."""

    def test_complete_report_structure(self, sample_project):
        """Test that complete report has all required sections."""
        html = generate_report(sample_project)

        # Header section
        assert "Preliminary Structural Design Report" in html

        # Status badges
        assert "status-card" in html
        assert "status-badge" in html

        # Metrics
        assert "Total Height" in html
        assert "Floor Area" in html
        assert "Carbon Intensity" in html

        # Element table
        assert "Structural Element Summary" in html

        # Lateral section
        assert "Lateral Stability Analysis" in html
        assert "Wind Loading" in html

        # Drift section
        assert "Drift Check" in html

        # AI Review
        assert "AI Design Review" in html

        # Carbon dashboard
        assert "Embodied Carbon Summary" in html

        # Assumptions page
        assert "Basis of Design" in html
        assert "Code References" in html
        assert "HK Code 2013" in html
        assert "HK Wind Code 2019" in html

        # Load factors
        assert "Partial Safety Factors" in html

        # Footer
        assert "PrelimStruct" in html
        assert "Page 1 of 4" in html
