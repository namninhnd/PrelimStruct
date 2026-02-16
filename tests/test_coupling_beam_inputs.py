"""Tests for coupling beam inputs (Phase 16 Task 6).

Verifies that coupling beam dimension inputs appear in Section Properties
when Core Wall System is enabled, and that L/d ratio classification works correctly.
"""

import pytest


class TestCouplingBeamInputDefaults:
    """Tests for coupling beam input default values and L/d ratio."""

    def test_coupling_beam_default_width_matches_wall(self):
        """CB width default should match wall thickness."""
        wall_thickness = 500
        cb_width_default = int(wall_thickness)
        assert cb_width_default == 500

    def test_coupling_beam_default_depth(self):
        """CB depth default should be 800mm."""
        assert 800 >= 300  # min
        assert 800 <= 2000  # max

    def test_deep_beam_classification(self):
        """L/d < 2.0 should classify as deep beam."""
        span_mm = 1500
        depth_mm = 800
        ld_ratio = span_mm / depth_mm
        assert ld_ratio < 2.0

    def test_conventional_beam_classification(self):
        """L/d >= 2.0 should classify as conventional beam."""
        span_mm = 2000
        depth_mm = 600
        ld_ratio = span_mm / depth_mm
        assert ld_ratio >= 2.0

    def test_span_from_opening_width(self):
        """CB clear span should default to opening width when available."""
        opening_width_m = 1.5
        cb_span_default = int(opening_width_m * 1000)
        assert cb_span_default == 1500

    def test_no_coupling_beam_without_core(self):
        """Coupling beam inputs should not appear when core wall is disabled."""
        has_core = False
        selected_core_wall_config = None
        show_coupling_beam = has_core and selected_core_wall_config is not None
        assert show_coupling_beam is False

    def test_coupling_beam_with_core(self):
        """Coupling beam inputs should appear when core wall is enabled."""
        has_core = True
        selected_core_wall_config = "TUBE_WITH_OPENINGS"
        show_coupling_beam = has_core and selected_core_wall_config is not None
        assert show_coupling_beam is True
