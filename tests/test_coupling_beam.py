"""
Unit tests for Coupling Beam System

Tests cover:
1. CouplingBeam data model properties and validation
2. Coupling beam geometry generation for all core wall configurations
3. Coupling beam design per HK Code 2013
4. Deep beam detection and special provisions
5. Diagonal reinforcement calculations
"""

import pytest
import math
from src.core.data_models import (
    CoreWallConfig,
    CoreWallGeometry,
    CouplingBeam,
    CouplingBeamResult,
)
from src.fem.coupling_beam import CouplingBeamGenerator, calculate_coupling_beam_properties
from src.engines.coupling_beam_engine import CouplingBeamEngine, estimate_coupling_beam_forces


class TestCouplingBeamDataModel:
    """Test CouplingBeam data model and properties."""

    def test_coupling_beam_creation(self):
        """Test basic coupling beam creation."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        assert beam.clear_span == 3000.0
        assert beam.depth == 1500.0
        assert beam.width == 500.0

    def test_span_to_depth_ratio(self):
        """Test span-to-depth ratio calculation."""
        beam = CouplingBeam(
            clear_span=3000.0,  # 3m
            depth=1500.0,        # 1.5m
            width=500.0,
        )

        expected_ratio = 3000.0 / 1500.0
        assert beam.span_to_depth_ratio == pytest.approx(expected_ratio, rel=1e-6)
        assert beam.span_to_depth_ratio == pytest.approx(2.0, rel=1e-6)

    def test_is_deep_beam_true(self):
        """Test deep beam detection when L/h < 2.0."""
        beam = CouplingBeam(
            clear_span=2500.0,   # 2.5m
            depth=1500.0,        # 1.5m (L/h = 1.67)
            width=500.0,
        )

        assert beam.is_deep_beam is True
        assert beam.span_to_depth_ratio < 2.0

    def test_is_deep_beam_false(self):
        """Test deep beam detection when L/h >= 2.0."""
        beam = CouplingBeam(
            clear_span=4000.0,   # 4m
            depth=1500.0,        # 1.5m (L/h = 2.67)
            width=500.0,
        )

        assert beam.is_deep_beam is False
        assert beam.span_to_depth_ratio >= 2.0

    def test_is_deep_beam_boundary(self):
        """Test deep beam detection at boundary L/h = 2.0."""
        beam = CouplingBeam(
            clear_span=3000.0,   # 3m
            depth=1500.0,        # 1.5m (L/h = 2.0)
            width=500.0,
        )

        # At boundary, should NOT be deep beam (< not <=)
        assert beam.is_deep_beam is False
        assert beam.span_to_depth_ratio == pytest.approx(2.0, rel=1e-6)


class TestCouplingBeamGenerator:
    """Test coupling beam geometry generation."""

    def test_generator_initialization(self):
        """Test generator initialization with core geometry."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            opening_width=3000.0,
        )

        generator = CouplingBeamGenerator(core_geom)

        assert generator.core_geometry == core_geom
        assert generator.wall_thickness == 500.0

    def test_two_c_facing_beam_generation(self):
        """Test coupling beam generation for TWO_C_FACING configuration."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            length_x=8000.0,
            length_y=8000.0,
            opening_width=3000.0,
            opening_height=2400.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams(
            story_height=3000.0,
            top_clearance=200.0,
            bottom_clearance=200.0,
        )

        assert len(beams) == 1
        beam = beams[0]
        assert beam.clear_span == 3000.0
        assert beam.width == 500.0
        assert beam.depth == pytest.approx(2400.0 - 200.0 - 200.0, rel=1e-6)

    def test_two_c_back_to_back_beam_generation(self):
        """Test coupling beam generation for TWO_C_BACK_TO_BACK configuration."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_BACK_TO_BACK,
            wall_thickness=500.0,
            length_x=10000.0,
            length_y=6000.0,
            opening_width=2500.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams(story_height=3000.0)

        # TWO_C_BACK_TO_BACK has 2 openings
        assert len(beams) == 2
        for beam in beams:
            assert beam.clear_span == 2500.0
            assert beam.width == 500.0

    def test_tube_center_opening_beam_generation(self):
        """Test coupling beam generation for TUBE_CENTER_OPENING configuration."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_CENTER_OPENING,
            wall_thickness=500.0,
            opening_width=2000.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert len(beams) == 1
        assert beams[0].clear_span == 2000.0

    def test_tube_side_opening_beam_generation(self):
        """Test coupling beam generation for TUBE_SIDE_OPENING configuration."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_SIDE_OPENING,
            wall_thickness=500.0,
            opening_width=2500.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert len(beams) == 1
        assert beams[0].clear_span == 2500.0

    def test_i_section_no_coupling_beams(self):
        """Test that I_SECTION returns no coupling beams (no door openings)."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        # I-section has no door openings
        assert len(beams) == 0

    def test_missing_opening_width_raises_error(self):
        """Test that missing opening_width raises ValueError."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            # opening_width missing
        )

        generator = CouplingBeamGenerator(core_geom)

        with pytest.raises(ValueError, match="requires opening_width"):
            generator.generate_coupling_beams()


class TestCouplingBeamProperties:
    """Test coupling beam property calculations."""

    def test_calculate_properties_typical_beam(self):
        """Test property calculation for typical coupling beam."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        props = calculate_coupling_beam_properties(beam)

        assert props["span_to_depth_ratio"] == pytest.approx(2.0, rel=1e-6)
        assert props["is_deep_beam"] is False

        # Gross area = b × h
        expected_area = 500.0 * 1500.0
        assert props["gross_area"] == pytest.approx(expected_area, rel=1e-6)

        # Second moment I = b×h³/12
        expected_I = (500.0 * 1500.0**3) / 12.0
        assert props["second_moment"] == pytest.approx(expected_I, rel=1e-6)

    def test_calculate_properties_deep_beam(self):
        """Test property calculation for deep beam."""
        beam = CouplingBeam(
            clear_span=2000.0,   # 2m
            depth=1200.0,        # 1.2m (L/h = 1.67)
            width=600.0,
        )

        props = calculate_coupling_beam_properties(beam)

        assert props["span_to_depth_ratio"] == pytest.approx(2000.0/1200.0, rel=1e-6)
        assert props["is_deep_beam"] is True


class TestCouplingBeamEngine:
    """Test coupling beam design engine."""

    def test_engine_initialization(self):
        """Test engine initialization with material properties."""
        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        assert engine.fcu == 40
        assert engine.fy == 500
        assert engine.fyv == 250

    def test_design_coupling_beam_typical(self):
        """Test design of typical coupling beam."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        # Typical coupling beam forces (from wind analysis)
        design_shear = 800.0   # kN
        design_moment = 600.0  # kNm

        result = engine.design_coupling_beam(
            beam=beam,
            design_shear=design_shear,
            design_moment=design_moment,
            cover=50,
        )

        # Check result structure
        assert isinstance(result, CouplingBeamResult)
        assert result.element_type == "Coupling Beam"
        assert result.width == 500
        assert result.depth == 1500
        assert result.clear_span == 3000.0
        assert result.shear == design_shear
        assert result.moment == design_moment

        # Check that design is reasonable
        assert result.shear_capacity > 0
        assert result.top_rebar > 0
        assert result.link_spacing > 0

    def test_design_high_shear_requires_diagonal_bars(self):
        """Test that high shear force triggers diagonal reinforcement."""
        beam = CouplingBeam(
            clear_span=2500.0,
            depth=1200.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        # Very high shear (typical for coupling beams)
        design_shear = 1500.0   # kN
        design_moment = 800.0   # kNm

        result = engine.design_coupling_beam(
            beam=beam,
            design_shear=design_shear,
            design_moment=design_moment,
        )

        # Should require diagonal reinforcement
        assert result.diagonal_rebar > 0
        assert result.shear_capacity >= design_shear

    def test_design_deep_beam_warning(self):
        """Test that deep beam triggers appropriate warning."""
        beam = CouplingBeam(
            clear_span=2000.0,   # 2m
            depth=1200.0,        # 1.2m (L/h = 1.67 < 2.0)
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        result = engine.design_coupling_beam(
            beam=beam,
            design_shear=600.0,
            design_moment=400.0,
        )

        # Should flag as deep beam
        assert result.is_deep_beam is True
        assert any("Deep beam" in warning for warning in result.warnings)
        assert any("STM" in warning or "Strut" in warning for warning in result.warnings)

    def test_design_minimum_reinforcement(self):
        """Test that minimum reinforcement is provided even for low loads."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        # Low loads
        design_shear = 100.0   # kN
        design_moment = 50.0   # kNm

        result = engine.design_coupling_beam(
            beam=beam,
            design_shear=design_shear,
            design_moment=design_moment,
        )

        # Should still provide minimum reinforcement
        # A_s,min = 0.13% × b × h = 0.0013 × 500 × 1500 = 975 mm²
        expected_min = 0.0013 * 500 * 1500
        assert result.top_rebar >= expected_min
        assert result.bottom_rebar >= expected_min

    def test_calculation_audit_trail(self):
        """Test that design produces calculation audit trail."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        result = engine.design_coupling_beam(
            beam=beam,
            design_shear=800.0,
            design_moment=600.0,
        )

        # Should have calculation steps
        assert len(result.calculations) > 0

        # Check for key calculation steps
        calc_descriptions = [calc["description"] for calc in result.calculations]
        assert any("COUPLING BEAM DESIGN" in desc for desc in calc_descriptions)
        assert any("SHEAR DESIGN" in desc for desc in calc_descriptions)
        assert any("FLEXURAL DESIGN" in desc for desc in calc_descriptions)


class TestEstimateCouplingBeamForces:
    """Test coupling beam force estimation."""

    def test_estimate_forces_typical_building(self):
        """Test force estimation for typical tall building."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        # Typical 30-story building
        base_shear_per_wall = 5000.0  # kN
        building_height = 90.0         # m (30 floors × 3m)
        num_floors = 30

        shear, moment = estimate_coupling_beam_forces(
            beam=beam,
            base_shear_per_wall=base_shear_per_wall,
            building_height=building_height,
            num_floors=num_floors,
        )

        # Should be reasonable values
        assert shear > 0
        assert moment > 0

        # Moment should be related to shear by span
        # M ≈ V × L / 2
        expected_moment_approx = shear * (beam.clear_span / 1000) / 2.0
        assert moment == pytest.approx(expected_moment_approx, rel=0.1)

    def test_estimate_forces_proportional_to_base_shear(self):
        """Test that forces scale with base shear."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        base_shear_1 = 1000.0  # kN
        shear_1, moment_1 = estimate_coupling_beam_forces(
            beam, base_shear_1, 90.0, 30
        )

        base_shear_2 = 2000.0  # kN (double)
        shear_2, moment_2 = estimate_coupling_beam_forces(
            beam, base_shear_2, 90.0, 30
        )

        # Forces should approximately double
        assert shear_2 == pytest.approx(2.0 * shear_1, rel=1e-6)
        assert moment_2 == pytest.approx(2.0 * moment_1, rel=1e-6)


class TestCouplingBeamIntegration:
    """Integration tests for complete coupling beam workflow."""

    def test_complete_workflow_two_c_facing(self):
        """Test complete workflow: geometry → generation → design."""
        # Step 1: Define core wall geometry
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            length_x=8000.0,
            length_y=8000.0,
            opening_width=3000.0,
            opening_height=2400.0,
        )

        # Step 2: Generate coupling beams
        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams(
            story_height=3000.0,
            top_clearance=200.0,
            bottom_clearance=200.0,
        )

        assert len(beams) == 1
        beam = beams[0]

        # Step 3: Estimate forces
        shear, moment = estimate_coupling_beam_forces(
            beam=beam,
            base_shear_per_wall=3000.0,
            building_height=90.0,
            num_floors=30,
        )

        # Step 4: Design coupling beam
        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)
        result = engine.design_coupling_beam(
            beam=beam,
            design_shear=shear,
            design_moment=moment,
        )

        # Verify complete design
        assert result.status in ["OK", "REVIEW REQUIRED"]
        assert result.shear_capacity > 0
        assert result.top_rebar > 0
        assert result.bottom_rebar > 0
        assert result.link_spacing > 0
        assert len(result.calculations) > 0

    def test_complete_workflow_tube_center_opening(self):
        """Test complete workflow for TUBE_CENTER_OPENING."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_CENTER_OPENING,
            wall_thickness=600.0,
            length_x=10000.0,
            length_y=10000.0,
            opening_width=2500.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert len(beams) == 1
        beam = beams[0]

        # Higher forces for tube core
        shear, moment = estimate_coupling_beam_forces(
            beam, 4000.0, 120.0, 40
        )

        engine = CouplingBeamEngine(fcu=45, fy=500, fyv=250)
        result = engine.design_coupling_beam(beam, shear, moment)

        assert result.utilization > 0
        assert result.diagonal_rebar >= 0  # May or may not need diagonal bars


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
