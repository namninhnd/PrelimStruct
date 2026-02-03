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

DEPRECATED_ENGINE_MSG = "Simplified coupling beam design removed in V3.5"
DEPRECATED_FORCE_MSG = "Simplified force estimation removed in V3.5"


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
        """Test deprecated engine raises for typical coupling beam."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        # Typical coupling beam forces (from wind analysis)
        design_shear = 800.0   # kN
        design_moment = 600.0  # kNm

        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=design_shear,
                design_moment=design_moment,
                cover=50,
            )

    def test_design_high_shear_requires_diagonal_bars(self):
        """Test deprecated engine raises for high shear case."""
        beam = CouplingBeam(
            clear_span=2500.0,
            depth=1200.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        # Very high shear (typical for coupling beams)
        design_shear = 1500.0   # kN
        design_moment = 800.0   # kNm

        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=design_shear,
                design_moment=design_moment,
            )

    def test_design_deep_beam_warning(self):
        """Test deprecated engine raises for deep beam case."""
        beam = CouplingBeam(
            clear_span=2000.0,   # 2m
            depth=1200.0,        # 1.2m (L/h = 1.67 < 2.0)
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=600.0,
                design_moment=400.0,
            )

    def test_design_minimum_reinforcement(self):
        """Test deprecated engine raises for low load case."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        # Low loads
        design_shear = 100.0   # kN
        design_moment = 50.0   # kNm

        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=design_shear,
                design_moment=design_moment,
            )
    def test_calculation_audit_trail(self):
        """Test deprecated engine raises and does not produce audit trail."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)

        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=800.0,
                design_moment=600.0,
            )
    def test_estimate_forces_typical_building(self):
        """Test deprecated estimator raises for typical tall building."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        # Typical 30-story building
        base_shear_per_wall = 5000.0  # kN
        building_height = 90.0         # m (30 floors ?? 3m)
        num_floors = 30

        with pytest.raises(NotImplementedError, match=DEPRECATED_FORCE_MSG):
            estimate_coupling_beam_forces(
                beam=beam,
                base_shear_per_wall=base_shear_per_wall,
                building_height=building_height,
                num_floors=num_floors,
            )
    def test_estimate_forces_proportional_to_base_shear(self):
        """Test deprecated estimator raises for base shear scaling."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        base_shear_1 = 1000.0  # kN
        with pytest.raises(NotImplementedError, match=DEPRECATED_FORCE_MSG):
            estimate_coupling_beam_forces(
                beam, base_shear_1, 90.0, 30
            )
    def test_complete_workflow_two_c_facing(self):
        """Test deprecated workflow raises on estimation/design."""
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
        with pytest.raises(NotImplementedError, match=DEPRECATED_FORCE_MSG):
            estimate_coupling_beam_forces(
                beam=beam,
                base_shear_per_wall=3000.0,
                building_height=90.0,
                num_floors=30,
            )

        # Step 4: Design coupling beam
        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)
        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=500.0,
                design_moment=300.0,
            )
    def test_complete_workflow_tube_center_opening(self):
        """Test deprecated workflow raises for TUBE_CENTER_OPENING."""
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
        with pytest.raises(NotImplementedError, match=DEPRECATED_FORCE_MSG):
            estimate_coupling_beam_forces(
                beam, 4000.0, 120.0, 40
            )

        engine = CouplingBeamEngine(fcu=45, fy=500, fyv=250)
        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(beam, 500.0, 300.0)
    def test_very_deep_coupling_beam(self):
        """Test coupling beam with very low L/h ratio."""
        beam = CouplingBeam(
            clear_span=1500.0,   # 1.5m
            depth=1500.0,        # 1.5m (L/h = 1.0)
            width=500.0,
        )

        assert beam.is_deep_beam is True
        assert beam.span_to_depth_ratio == pytest.approx(1.0, rel=1e-6)

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)
        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=500.0,
                design_moment=300.0,
            )
    def test_zero_moment_design(self):
        """Test deprecated engine raises for zero moment case."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)
        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=800.0,
                design_moment=0.0,
            )
    def test_zero_shear_design(self):
        """Test deprecated engine raises for zero shear case."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)
        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beam,
                design_shear=0.0,
                design_moment=500.0,
            )
    def test_small_opening_width(self):
        """Test generator with very small opening width."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            opening_width=1000.0,  # Minimum practical opening
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert len(beams) == 1
        assert beams[0].clear_span == 1000.0

    def test_large_opening_width(self):
        """Test generator with very large opening width."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            opening_width=6000.0,  # Large opening
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert len(beams) == 1
        # Large span should mean NOT a deep beam
        beam = beams[0]
        assert beam.clear_span == 6000.0

    def test_different_concrete_grades(self):
        """Test deprecated engine raises for different concrete grades."""
        beam = CouplingBeam(
            clear_span=3000.0,
            depth=1500.0,
            width=500.0,
        )

        # Lower grade
        engine_low = CouplingBeamEngine(fcu=30, fy=500, fyv=250)
        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine_low.design_coupling_beam(
                beam=beam,
                design_shear=800.0,
                design_moment=600.0,
            )

        # Higher grade
        engine_high = CouplingBeamEngine(fcu=50, fy=500, fyv=250)
        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine_high.design_coupling_beam(
                beam=beam,
                design_shear=800.0,
                design_moment=600.0,
            )
    def test_thin_wall_coupling_beam(self):
        """Test coupling beam with thin wall thickness."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=300.0,  # Thin wall
            opening_width=2500.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert len(beams) == 1
        assert beams[0].width == 300.0

        engine = CouplingBeamEngine(fcu=40, fy=500, fyv=250)
        with pytest.raises(NotImplementedError, match=DEPRECATED_ENGINE_MSG):
            engine.design_coupling_beam(
                beam=beams[0],
                design_shear=400.0,
                design_moment=300.0,
            )
    def test_thick_wall_coupling_beam(self):
        """Test coupling beam with thick wall thickness."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_CENTER_OPENING,
            wall_thickness=800.0,  # Thick wall
            opening_width=3000.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert len(beams) == 1
        assert beams[0].width == 800.0

    def test_missing_lengths_infer_core_dimensions(self):
        """Test that missing length_x/length_y are inferred for C-wall configs."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0,
            opening_width=2000.0,
            length_x=None,
            length_y=None,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert len(beams) == 1
        assert beams[0].location_x == pytest.approx((2 * 3000.0 + 2000.0) / 2.0, rel=1e-6)
        assert beams[0].location_y == pytest.approx(6000.0 / 2.0, rel=1e-6)

    def test_opening_height_none_defaults_to_story_height(self):
        """Test missing opening height uses story height for beam depth."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0,
            opening_width=2500.0,
            opening_height=None,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams(
            story_height=3000.0,
            top_clearance=200.0,
            bottom_clearance=200.0,
        )

        assert len(beams) == 1
        assert beams[0].opening_height == pytest.approx(3000.0, rel=1e-6)
        assert beams[0].depth == pytest.approx(2600.0, rel=1e-6)

    def test_zero_opening_width_returns_empty(self):
        """Test zero opening width returns no coupling beams."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0,
            opening_width=0.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert beams == []

    def test_zero_opening_height_returns_empty(self):
        """Test zero opening height returns no coupling beams."""
        core_geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_CENTER_OPENING,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=6000.0,
            opening_width=2000.0,
            opening_height=0.0,
        )

        generator = CouplingBeamGenerator(core_geom)
        beams = generator.generate_coupling_beams()

        assert beams == []


class TestCouplingBeamResultProperties:
    """Tests for CouplingBeamResult dataclass properties."""

    def test_result_creation_with_all_fields(self):
        """Test complete result creation."""
        result = CouplingBeamResult(
            element_type="Coupling Beam",
            size="500x1500",
            width=500,
            depth=1500,
            clear_span=3000.0,
            span_to_depth_ratio=2.0,
            shear=800.0,
            moment=600.0,
            shear_capacity=950.0,
            top_rebar=1200.0,
            bottom_rebar=1100.0,
            diagonal_rebar=800.0,
            link_spacing=150,
            is_deep_beam=False,
            utilization=0.84,
            status="OK",
            warnings=[],
            calculations=[],
        )

        assert result.element_type == "Coupling Beam"
        assert result.size == "500x1500"
        assert result.utilization == 0.84
        assert result.is_deep_beam is False

    def test_result_with_warnings(self):
        """Test result with warnings list."""
        result = CouplingBeamResult(
            element_type="Coupling Beam",
            size="500x1200",
            width=500,
            depth=1200,
            clear_span=2000.0,
            span_to_depth_ratio=1.67,
            shear=600.0,
            moment=400.0,
            shear_capacity=700.0,
            top_rebar=900.0,
            bottom_rebar=850.0,
            diagonal_rebar=0.0,
            link_spacing=150,
            is_deep_beam=True,
            utilization=0.86,
            status="REVIEW REQUIRED",
            warnings=["Deep beam: L/h = 1.67 < 2.0", "Consider STM analysis"],
            calculations=[],
        )

        assert len(result.warnings) == 2
        assert "Deep beam" in result.warnings[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
