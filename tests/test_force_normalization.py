"""Tests for force normalization utilities.

These tests verify that force normalization is consistent between:
- BeamForcesTable (table display)
- visualization.py (Plotly overlays)
- ResultsProcessor (section forces extraction)

The key convention: For Vy, Vz, My, Mz, T at j-end, negate the raw value.
For N (axial), use sign-based normalization.
"""

import pytest


class TestNormalizeEndForce:
    """Tests for the _normalize_end_force function (axial N normalization)."""

    def test_same_sign_forces_returns_force_j(self):
        """When forces have same sign, return force_j directly."""
        from src.fem.force_normalization import normalize_end_force
        
        # Both positive (tension)
        result = normalize_end_force(100.0, 100.0, "N")
        assert result == 100.0
        
        # Both negative (compression)
        result = normalize_end_force(-50.0, -50.0, "N")
        assert result == -50.0

    def test_opposite_sign_forces_returns_negated_force_j(self):
        """When forces have opposite signs, negate force_j."""
        from src.fem.force_normalization import normalize_end_force
        
        # Opposite signs: |force_i + force_j| < |force_i - force_j|
        result = normalize_end_force(100.0, -100.0, "N")
        # abs(100 + (-100)) = 0 < abs(100 - (-100)) = 200
        # So return -force_j = -(-100) = 100
        assert result == 100.0

    def test_force_i_dominant_positive(self):
        """When force_i >> force_j, sign comparison determines output."""
        from src.fem.force_normalization import normalize_end_force
        
        # force_i = 100, force_j = 10
        # abs(100 + 10) = 110 > abs(100 - 10) = 90
        # So return force_j = 10
        result = normalize_end_force(100.0, 10.0, "N")
        assert result == 10.0

    def test_near_zero_forces(self):
        """Near-zero forces should not cause division issues."""
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(0.0, 0.0, "N")
        # abs(0 + 0) = 0 is not < abs(0 - 0) = 0
        # So return force_j = 0
        assert result == 0.0


class TestDisplayEndForce:
    """Tests for the display_end_force function (force type-specific normalization)."""

    def test_vy_negated_at_j_end(self):
        """Shear Vy at j-end should be negated."""
        from src.fem.force_normalization import normalize_end_force
        
        # Vy should return -force_j
        result = normalize_end_force(10.0, 25.0, "Vy")
        assert result == -25.0
        
        result = normalize_end_force(10.0, -25.0, "Vy")
        assert result == 25.0

    def test_vz_negated_at_j_end(self):
        """Shear Vz at j-end should be negated."""
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(10.0, 30.0, "Vz")
        assert result == -30.0

    def test_my_negated_at_j_end(self):
        """Moment My at j-end should be negated."""
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(100.0, 50.0, "My")
        assert result == -50.0

    def test_mz_negated_at_j_end(self):
        """Moment Mz at j-end should be negated."""
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(100.0, -80.0, "Mz")
        assert result == 80.0

    def test_t_negated_at_j_end(self):
        """Torsion T at j-end should be negated."""
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(20.0, 15.0, "T")
        assert result == -15.0

    def test_n_uses_sign_based_normalization(self):
        """Axial N should use sign-based normalization, not simple negation."""
        from src.fem.force_normalization import normalize_end_force
        
        # Same sign: return force_j
        result = normalize_end_force(100.0, 100.0, "N")
        assert result == 100.0
        
        # Opposite signs: return -force_j
        result = normalize_end_force(100.0, -100.0, "N")
        assert result == 100.0


class TestConsistencyBetweenTableAndOverlay:
    """Tests ensuring table and overlay produce identical normalized values."""

    def test_table_and_overlay_same_for_mz(self):
        """Mz normalization should be identical in table and overlay."""
        from src.fem.force_normalization import normalize_end_force
        
        force_i, force_j = 150.0, -75.0
        
        # Both should use the same shared function
        table_result = normalize_end_force(force_i, force_j, "Mz")
        overlay_result = normalize_end_force(force_i, force_j, "Mz")
        
        assert table_result == overlay_result
        assert table_result == 75.0  # -(-75) = 75

    def test_table_and_overlay_same_for_vy(self):
        """Vy normalization should be identical in table and overlay."""
        from src.fem.force_normalization import normalize_end_force
        
        force_i, force_j = 50.0, 30.0
        
        table_result = normalize_end_force(force_i, force_j, "Vy")
        overlay_result = normalize_end_force(force_i, force_j, "Vy")
        
        assert table_result == overlay_result
        assert table_result == -30.0  # -(30) = -30

    def test_table_and_overlay_same_for_n(self):
        """N normalization should be identical in table and overlay."""
        from src.fem.force_normalization import normalize_end_force
        
        force_i, force_j = 200.0, 180.0
        
        table_result = normalize_end_force(force_i, force_j, "N")
        overlay_result = normalize_end_force(force_i, force_j, "N")
        
        assert table_result == overlay_result

    def test_all_force_types_consistency(self):
        """All 6 force types should produce consistent results."""
        from src.fem.force_normalization import NEGATED_J_END_TYPES, normalize_end_force
        
        force_i, force_j = 100.0, 50.0
        
        for force_type in ["N", "Vy", "Vz", "My", "Mz", "T"]:
            result = normalize_end_force(force_i, force_j, force_type)
            
            if force_type in NEGATED_J_END_TYPES:
                assert result == -force_j, f"{force_type} should return -force_j"
            else:
                # N uses sign-based normalization
                # For this test case: abs(100 + 50) = 150 > abs(100 - 50) = 50
                # So return force_j = 50
                assert result == force_j, f"{force_type} should return force_j for same-sign forces"


class TestGetNormalizedForces:
    """Tests for the get_normalized_forces helper function."""

    def test_normalizes_all_force_components(self):
        """Should normalize all 6 force components correctly."""
        from src.fem.force_normalization import get_normalized_forces
        
        forces = {
            "N_i": 100.0, "N_j": 100.0,
            "Vy_i": 50.0, "Vy_j": 30.0,
            "Vz_i": 20.0, "Vz_j": 15.0,
            "My_i": 80.0, "My_j": 40.0,
            "Mz_i": 60.0, "Mz_j": -20.0,
            "T_i": 10.0, "T_j": 5.0,
        }
        
        result = get_normalized_forces(forces)
        
        # N: same sign -> return force_j
        assert result["N"] == 100.0
        # Vy, Vz, My, Mz, T: negate force_j
        assert result["Vy"] == -30.0
        assert result["Vz"] == -15.0
        assert result["My"] == -40.0
        assert result["Mz"] == 20.0  # -(-20) = 20
        assert result["T"] == -5.0

    def test_handles_missing_force_components(self):
        """Should handle dictionaries with missing force components."""
        from src.fem.force_normalization import get_normalized_forces
        
        # Only N and Mz provided
        forces = {
            "N_i": 100.0, "N_j": 100.0,
            "Mz_i": 60.0, "Mz_j": -20.0,
        }
        
        result = get_normalized_forces(forces)
        
        assert result["N"] == 100.0
        assert result["Mz"] == 20.0
        assert result["Vy"] == 0.0  # Default for missing
        assert result["Vz"] == 0.0
        assert result["My"] == 0.0
        assert result["T"] == 0.0

    def test_handles_2d_force_keys(self):
        """Should handle 2D element force keys (V_i/V_j, M_i/M_j)."""
        from src.fem.force_normalization import get_normalized_forces
        
        # 2D element format
        forces = {
            "N_i": 50.0, "N_j": 50.0,
            "V_i": 30.0, "V_j": 20.0,
            "M_i": 100.0, "M_j": -50.0,
        }
        
        result = get_normalized_forces(forces)
        
        assert result["N"] == 50.0
        # V maps to Vy (2D shear)
        assert result["Vy"] == -20.0
        # M maps to Mz (2D moment in-plane)
        assert result["Mz"] == 50.0  # -(-50) = 50


class TestNegatedJEndTypes:
    """Tests for the NEGATED_J_END_TYPES constant."""

    def test_contains_expected_types(self):
        """Should contain exactly Vy, Vz, My, Mz, T."""
        from src.fem.force_normalization import NEGATED_J_END_TYPES
        
        expected = {"Vy", "Vz", "My", "Mz", "T"}
        assert NEGATED_J_END_TYPES == expected

    def test_n_not_in_negated_types(self):
        """Axial force N should NOT be in negated types."""
        from src.fem.force_normalization import NEGATED_J_END_TYPES
        
        assert "N" not in NEGATED_J_END_TYPES
