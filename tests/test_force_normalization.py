"""Tests for force normalization utilities.

These tests verify that force normalization is consistent between:
- BeamForcesTable (table display)
- visualization.py (Plotly overlays)
- ResultsProcessor (section forces extraction)

Sign convention:
- Shear (Vy, Vz): negate j-end, keep i-end raw
- Moments (My, Mz, T): keep j-end raw, negate i-end
- Axial (N): sign-based normalization at j-end
"""

class TestNormalizeEndForce:
    """Tests for axial N normalization."""

    def test_same_sign_forces_returns_force_j(self):
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(100.0, 100.0, "N")
        assert result == 100.0
        
        result = normalize_end_force(-50.0, -50.0, "N")
        assert result == -50.0

    def test_opposite_sign_forces_returns_negated_force_j(self):
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(100.0, -100.0, "N")
        assert result == 100.0

    def test_force_i_dominant_positive(self):
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(100.0, 10.0, "N")
        assert result == 10.0

    def test_near_zero_forces(self):
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(0.0, 0.0, "N")
        assert result == 0.0


class TestDisplayEndForce:
    """Tests for force type-specific j-end normalization."""

    def test_vy_negated_at_j_end(self):
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(10.0, 25.0, "Vy")
        assert result == -25.0
        
        result = normalize_end_force(10.0, -25.0, "Vy")
        assert result == 25.0

    def test_vz_negated_at_j_end(self):
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(10.0, 30.0, "Vz")
        assert result == -30.0

    def test_my_raw_at_j_end(self):
        """Moment My at j-end should be kept raw (not negated)."""
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(100.0, 50.0, "My")
        assert result == 50.0

    def test_mz_raw_at_j_end(self):
        """Moment Mz at j-end should be kept raw (not negated)."""
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(100.0, -80.0, "Mz")
        assert result == -80.0

    def test_t_raw_at_j_end(self):
        """Torsion T at j-end should be kept raw (not negated)."""
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(20.0, 15.0, "T")
        assert result == 15.0

    def test_n_uses_sign_based_normalization(self):
        from src.fem.force_normalization import normalize_end_force
        
        result = normalize_end_force(100.0, 100.0, "N")
        assert result == 100.0
        
        result = normalize_end_force(100.0, -100.0, "N")
        assert result == 100.0


class TestNormalizeIEndForce:
    """Tests for the normalize_i_end_force function."""

    def test_mz_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(100.0, "Mz") == -100.0

    def test_my_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(50.0, "My") == -50.0

    def test_t_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(20.0, "T") == -20.0

    def test_vy_not_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(30.0, "Vy") == 30.0

    def test_vz_not_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(15.0, "Vz") == 15.0

    def test_n_not_negated_at_i_end(self):
        from src.fem.force_normalization import normalize_i_end_force
        assert normalize_i_end_force(100.0, "N") == 100.0


class TestConsistencyBetweenTableAndOverlay:
    """Tests ensuring table and overlay produce identical normalized values."""

    def test_table_and_overlay_same_for_mz(self):
        from src.fem.force_normalization import normalize_end_force
        
        force_i, force_j = 150.0, -75.0
        
        table_result = normalize_end_force(force_i, force_j, "Mz")
        overlay_result = normalize_end_force(force_i, force_j, "Mz")
        
        assert table_result == overlay_result
        assert table_result == -75.0

    def test_table_and_overlay_same_for_vy(self):
        from src.fem.force_normalization import normalize_end_force
        
        force_i, force_j = 50.0, 30.0
        
        table_result = normalize_end_force(force_i, force_j, "Vy")
        overlay_result = normalize_end_force(force_i, force_j, "Vy")
        
        assert table_result == overlay_result
        assert table_result == -30.0

    def test_table_and_overlay_same_for_n(self):
        from src.fem.force_normalization import normalize_end_force
        
        force_i, force_j = 200.0, 180.0
        
        table_result = normalize_end_force(force_i, force_j, "N")
        overlay_result = normalize_end_force(force_i, force_j, "N")
        
        assert table_result == overlay_result

    def test_all_force_types_consistency(self):
        from src.fem.force_normalization import NEGATED_J_END_TYPES, NEGATED_I_END_TYPES, normalize_end_force
        
        force_i, force_j = 100.0, 50.0
        
        for force_type in ["N", "Vy", "Vz", "My", "Mz", "T"]:
            result = normalize_end_force(force_i, force_j, force_type)
            
            if force_type in NEGATED_J_END_TYPES:
                assert result == -force_j, f"{force_type} should return -force_j"
            elif force_type in NEGATED_I_END_TYPES:
                assert result == force_j, f"{force_type} should return force_j (raw) at j-end"
            else:
                assert result == force_j, f"{force_type} should return force_j for same-sign forces"


class TestGetNormalizedForces:
    """Tests for the get_normalized_forces helper function."""

    def test_normalizes_all_force_components(self):
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
        
        assert result["N"] == 100.0
        assert result["Vy"] == -30.0
        assert result["Vz"] == -15.0
        assert result["My"] == 40.0
        assert result["Mz"] == -20.0
        assert result["T"] == 5.0

    def test_handles_missing_force_components(self):
        from src.fem.force_normalization import get_normalized_forces
        
        forces = {
            "N_i": 100.0, "N_j": 100.0,
            "Mz_i": 60.0, "Mz_j": -20.0,
        }
        
        result = get_normalized_forces(forces)
        
        assert result["N"] == 100.0
        assert result["Mz"] == -20.0
        assert result["Vy"] == 0.0
        assert result["Vz"] == 0.0
        assert result["My"] == 0.0
        assert result["T"] == 0.0

    def test_handles_2d_force_keys(self):
        from src.fem.force_normalization import get_normalized_forces
        
        forces = {
            "N_i": 50.0, "N_j": 50.0,
            "V_i": 30.0, "V_j": 20.0,
            "M_i": 100.0, "M_j": -50.0,
        }
        
        result = get_normalized_forces(forces)
        
        assert result["N"] == 50.0
        assert result["Vy"] == -20.0
        assert result["Mz"] == -50.0


class TestNegatedEndTypes:
    """Tests for the NEGATED_J_END_TYPES and NEGATED_I_END_TYPES constants."""

    def test_j_end_contains_only_shear(self):
        from src.fem.force_normalization import NEGATED_J_END_TYPES
        
        expected = {"Vy", "Vz"}
        assert NEGATED_J_END_TYPES == expected

    def test_i_end_contains_moments_and_torsion(self):
        from src.fem.force_normalization import NEGATED_I_END_TYPES
        
        expected = {"My", "Mz", "T"}
        assert NEGATED_I_END_TYPES == expected

    def test_n_not_in_negated_types(self):
        from src.fem.force_normalization import NEGATED_J_END_TYPES, NEGATED_I_END_TYPES
        
        assert "N" not in NEGATED_J_END_TYPES
        assert "N" not in NEGATED_I_END_TYPES
