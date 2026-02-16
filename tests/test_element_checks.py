"""Tests for slab strip, wall, and coupling beam checks (Gates E, F, G)."""

import math
import pytest

from src.fem.design_checks import (
    slab_strip_check,
    wall_check,
    coupling_beam_check,
)


# ── Gate E: slab_strip_check ─────────────────────────────

class TestSlabStripCheck:
    def test_basic_pass(self):
        """Moderate shear on 150mm slab."""
        result = slab_strip_check(
            element_id=100,
            V_per_m=50_000,    # 50 kN/m
            M_per_m=0,
            d=120,             # effective depth mm
            fcu=35,
            rho_provided=0.5,
        )
        assert result.shear_check.passed
        assert result.rho_result.passed
        assert result.strip_width_mm == 1000.0

    def test_high_shear_fail(self):
        """Very high shear should fail v_max."""
        result = slab_strip_check(
            element_id=200,
            V_per_m=800_000,   # 800 kN/m — extreme
            M_per_m=0,
            d=120,
            fcu=35,
            rho_provided=0.5,
        )
        assert not result.shear_check.passed
        assert result.governing_score > 1.0
        assert any("shear" in w for w in result.warnings)

    def test_low_rho_warning(self):
        """Below min rho for slab (0.3%)."""
        result = slab_strip_check(
            element_id=300,
            V_per_m=30_000,
            M_per_m=0,
            d=150,
            fcu=35,
            rho_provided=0.1,
        )
        assert not result.rho_result.passed
        assert any("ρ_min" in w for w in result.warnings)


# ── Gate F: wall_check ────────────────────────────────────

class TestWallCheck:
    def test_basic_pass(self):
        """Moderate loads on 500mm thick wall."""
        result = wall_check(
            element_id=400,
            N=2_000_000,        # 2000 kN
            V=300_000,          # 300 kN
            b=500,              # thickness mm
            d=4000 * 0.8,       # 4m wall, d = 0.8L
            fcu=40,
            Ag=500 * 4000,      # 2e6 mm²
            rho_provided=0.5,
        )
        assert result.shear_check.passed
        assert result.ductility_result.passed
        assert result.rho_result.passed

    def test_high_axial_ductility_warning(self):
        """N/(fcu·Ag) > 0.6 should trigger ductility warning."""
        result = wall_check(
            element_id=500,
            N=60_000_000,       # 60 MN — extreme
            V=100_000,
            b=500,
            d=3200,
            fcu=40,
            Ag=500 * 4000,
            rho_provided=0.5,
        )
        assert not result.ductility_result.passed
        assert any("ductility" in w for w in result.warnings)

    def test_low_wall_rho(self):
        """Below min wall rho (0.25%)."""
        result = wall_check(
            element_id=600,
            N=1_000_000,
            V=100_000,
            b=500,
            d=3200,
            fcu=40,
            Ag=500 * 4000,
            rho_provided=0.1,
        )
        assert not result.rho_result.passed


# ── Gate G: coupling_beam_check ───────────────────────────

class TestCouplingBeamCheck:
    def test_basic_pass(self):
        """Normal coupling beam."""
        result = coupling_beam_check(
            element_id=700,
            V=200_000,          # 200 kN
            b=350,
            d=450,
            fcu=40,
            span=1200,          # clear span mm
            rho_provided=1.0,
        )
        assert result.shear_check.passed
        assert result.rho_result.passed
        assert result.span_depth_ratio == pytest.approx(1200 / 450)

    def test_deep_coupling_beam_warning(self):
        """l/d < 2.0 should trigger diagonal rebar warning."""
        result = coupling_beam_check(
            element_id=800,
            V=200_000,
            b=350,
            d=800,
            fcu=40,
            span=1000,          # l/d = 1.25
            rho_provided=1.0,
        )
        assert result.span_depth_ratio < 2.0
        assert any("diagonal" in w for w in result.warnings)

    def test_high_shear_fail(self):
        """Extreme shear on coupling beam."""
        result = coupling_beam_check(
            element_id=900,
            V=2_000_000,        # 2 MN
            b=250,
            d=400,
            fcu=35,
            span=800,
            rho_provided=1.0,
        )
        assert not result.shear_check.passed
        assert result.governing_score > 1.0
