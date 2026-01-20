"""
Unit tests for HK2013 design code implementation.

Tests the Hong Kong Code of Practice for Structural Use of Concrete 2013
implementation that extends the ConcreteProperties library.
"""

import pytest
import math
from src.fem.design_codes.hk2013 import HK2013


class TestHK2013Initialization:
    """Tests for HK2013 class initialization."""

    def test_initialization(self):
        """Test HK2013 design code initializes correctly."""
        hk_code = HK2013()
        assert hk_code is not None
        assert hk_code.reinforcement_class == "B"  # Default ductility class

    def test_inheritance(self):
        """Test HK2013 inherits from DesignCode base class."""
        from concreteproperties.design_codes.design_code import DesignCode
        hk_code = HK2013()
        assert isinstance(hk_code, DesignCode)


class TestConcreteMaterial:
    """Tests for concrete material creation per HK Code 2013."""

    def test_create_concrete_c40(self):
        """Test C40 concrete material creation."""
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=40)

        assert concrete is not None
        assert concrete.name == "C40 Concrete (HK Code 2013)"
        assert concrete.density == pytest.approx(2.4e-6, rel=1e-6)

    def test_elastic_modulus_c40(self):
        """Test elastic modulus calculation for C40 concrete.

        HK Code 2013 Cl 3.1.7: E_cm = 3.46 * sqrt(f_cu) + 3.21 (GPa)
        For C40: E_cm = 3.46 * sqrt(40) + 3.21 = 3.46 * 6.3246 + 3.21 = 25.08 GPa
        """
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=40)

        # Get elastic modulus from service stress-strain profile
        service_profile = concrete.stress_strain_profile
        expected_e = 3.46 * math.sqrt(40) + 3.21  # GPa
        expected_e_mpa = expected_e * 1000  # Convert to MPa

        assert service_profile.elastic_modulus == pytest.approx(
            expected_e_mpa, rel=1e-3
        )

    def test_flexural_tensile_strength_c40(self):
        """Test flexural tensile strength for C40 concrete.

        HK Code 2013 Cl 3.1.6.3: f_ct = 0.6 * sqrt(f_cu) (MPa)
        For C40: f_ct = 0.6 * sqrt(40) = 0.6 * 6.3246 = 3.79 MPa
        """
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=40)

        expected_fct = 0.6 * math.sqrt(40)
        assert concrete.flexural_tensile_strength == pytest.approx(
            expected_fct, rel=1e-3
        )

    def test_stress_block_normal_strength(self):
        """Test stress block parameters for normal strength concrete (f_cu ≤ 60 MPa).

        HK Code 2013 Cl 6.1.2.4:
        For f_cu ≤ 60 MPa: α = 0.67, γ = 0.45
        """
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=40)

        # Get ultimate stress-strain profile
        ultimate_profile = concrete.ultimate_stress_strain_profile

        assert ultimate_profile.alpha == pytest.approx(0.67, rel=1e-6)
        assert ultimate_profile.gamma == pytest.approx(0.45, rel=1e-6)
        assert ultimate_profile.compressive_strength == 40
        assert ultimate_profile.ultimate_strain == pytest.approx(0.0035, rel=1e-6)

    def test_stress_block_high_strength(self):
        """Test stress block parameters for high strength concrete (f_cu > 60 MPa).

        HK Code 2013 Cl 6.1.2.4(b):
        For f_cu > 60 MPa:
        α = 0.67 - (f_cu - 60)/400, min 0.50
        γ = 0.45 - (f_cu - 60)/800, min 0.35
        """
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=70)

        # Get ultimate stress-strain profile
        ultimate_profile = concrete.ultimate_stress_strain_profile

        # Calculate expected values for C70
        expected_alpha = 0.67 - (70 - 60) / 400
        expected_gamma = 0.45 - (70 - 60) / 800

        assert ultimate_profile.alpha == pytest.approx(expected_alpha, rel=1e-3)
        assert ultimate_profile.gamma == pytest.approx(expected_gamma, rel=1e-3)

    def test_concrete_grade_range(self):
        """Test concrete material creation for various grades."""
        hk_code = HK2013()

        # Test valid grades
        for fcu in [25, 30, 35, 40, 45, 50, 60, 70, 80]:
            concrete = hk_code.create_concrete_material(compressive_strength=fcu)
            assert concrete is not None
            assert concrete.name == f"C{fcu} Concrete (HK Code 2013)"

    def test_concrete_strength_validation(self):
        """Test validation of concrete strength range."""
        hk_code = HK2013()

        # Test invalid strengths
        with pytest.raises(ValueError, match="must be between 25 MPa and 80 MPa"):
            hk_code.create_concrete_material(compressive_strength=20)

        with pytest.raises(ValueError, match="must be between 25 MPa and 80 MPa"):
            hk_code.create_concrete_material(compressive_strength=85)

    def test_concrete_custom_colour(self):
        """Test concrete material with custom colour."""
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(
            compressive_strength=40,
            colour="blue"
        )
        assert concrete.colour == "blue"


class TestSteelMaterial:
    """Tests for steel reinforcement material creation per HK Code 2013."""

    def test_create_steel_fy500(self):
        """Test FY500 steel material creation."""
        hk_code = HK2013()
        steel = hk_code.create_steel_material(yield_strength=500)

        assert steel is not None
        assert steel.name == "FY500 Steel (HK Code 2013, Class B)"
        assert steel.density == pytest.approx(7.85e-6, rel=1e-6)

    def test_steel_elastic_modulus(self):
        """Test steel elastic modulus.

        HK Code 2013 Cl 3.2.5: E_s = 200 GPa
        """
        hk_code = HK2013()
        steel = hk_code.create_steel_material(yield_strength=500)

        # Get elastic modulus from stress-strain profile
        profile = steel.stress_strain_profile
        assert profile.elastic_modulus == pytest.approx(200_000, rel=1e-6)  # MPa

    def test_steel_ductility_class_b(self):
        """Test Class B steel (normal ductility, ε_su ≥ 5%).

        HK Code 2013 Cl 2.4.3.2
        """
        hk_code = HK2013()
        steel = hk_code.create_steel_material(
            yield_strength=500,
            ductility_class="B"
        )

        profile = steel.stress_strain_profile
        assert profile.fracture_strain == pytest.approx(0.05, rel=1e-6)  # 5%

    def test_steel_ductility_class_a(self):
        """Test Class A steel (low ductility, ε_su ≥ 2.5%)."""
        hk_code = HK2013()
        steel = hk_code.create_steel_material(
            yield_strength=460,
            ductility_class="A"
        )

        profile = steel.stress_strain_profile
        assert profile.fracture_strain == pytest.approx(0.025, rel=1e-6)  # 2.5%
        assert "Class A" in steel.name

    def test_steel_ductility_class_c(self):
        """Test Class C steel (high ductility, ε_su ≥ 7.5%)."""
        hk_code = HK2013()
        steel = hk_code.create_steel_material(
            yield_strength=500,
            ductility_class="C"
        )

        profile = steel.stress_strain_profile
        assert profile.fracture_strain == pytest.approx(0.075, rel=1e-6)  # 7.5%
        assert "Class C" in steel.name

    def test_steel_grades(self):
        """Test steel material creation for common grades."""
        hk_code = HK2013()

        # Test common steel grades in Hong Kong
        for fy in [250, 460, 500]:
            steel = hk_code.create_steel_material(yield_strength=fy)
            assert steel is not None
            assert f"FY{fy}" in steel.name

    def test_steel_strength_validation(self):
        """Test validation of steel strength range."""
        hk_code = HK2013()

        # Test invalid strengths
        with pytest.raises(ValueError, match="must be between 250 MPa and 500 MPa"):
            hk_code.create_steel_material(yield_strength=200)

        with pytest.raises(ValueError, match="must be between 250 MPa and 500 MPa"):
            hk_code.create_steel_material(yield_strength=550)

    def test_steel_ductility_validation(self):
        """Test validation of ductility class."""
        hk_code = HK2013()

        # Test invalid ductility class
        with pytest.raises(ValueError, match="must be 'A', 'B', or 'C'"):
            hk_code.create_steel_material(
                yield_strength=500,
                ductility_class="D"
            )

    def test_steel_custom_colour(self):
        """Test steel material with custom colour."""
        hk_code = HK2013()
        steel = hk_code.create_steel_material(
            yield_strength=500,
            colour="darkgrey"
        )
        assert steel.colour == "darkgrey"

    def test_steel_case_insensitive_ductility(self):
        """Test ductility class is case-insensitive."""
        hk_code = HK2013()

        steel_lower = hk_code.create_steel_material(
            yield_strength=500,
            ductility_class="b"
        )
        steel_upper = hk_code.create_steel_material(
            yield_strength=500,
            ductility_class="B"
        )

        assert steel_lower.stress_strain_profile.fracture_strain == \
               steel_upper.stress_strain_profile.fracture_strain


class TestCapacityReductionFactors:
    """Tests for capacity reduction factors (reference only for HK Code 2013)."""

    def test_flexure_reduction_factor(self):
        """Test flexure capacity reduction factor."""
        hk_code = HK2013()
        phi = hk_code.get_capacity_reduction_factor(failure_mode="flexure")
        assert phi == pytest.approx(0.85, rel=1e-6)

    def test_compression_reduction_factor(self):
        """Test compression capacity reduction factor."""
        hk_code = HK2013()
        phi = hk_code.get_capacity_reduction_factor(failure_mode="compression")
        assert phi == pytest.approx(0.70, rel=1e-6)

    def test_shear_reduction_factor(self):
        """Test shear capacity reduction factor."""
        hk_code = HK2013()
        phi = hk_code.get_capacity_reduction_factor(failure_mode="shear")
        assert phi == pytest.approx(0.75, rel=1e-6)

    def test_tension_reduction_factor(self):
        """Test tension capacity reduction factor."""
        hk_code = HK2013()
        phi = hk_code.get_capacity_reduction_factor(failure_mode="tension")
        assert phi == pytest.approx(0.90, rel=1e-6)

    def test_default_reduction_factor(self):
        """Test default capacity reduction factor."""
        hk_code = HK2013()
        phi = hk_code.get_capacity_reduction_factor(failure_mode="unknown")
        assert phi == pytest.approx(0.85, rel=1e-6)


class TestIntegration:
    """Integration tests for HK2013 design code."""

    def test_typical_design_scenario_c40_fy500(self):
        """Test typical Hong Kong design scenario with C40 concrete and FY500 steel."""
        hk_code = HK2013()

        # Create materials for typical HK building
        concrete = hk_code.create_concrete_material(compressive_strength=40)
        steel = hk_code.create_steel_material(yield_strength=500, ductility_class="B")

        # Verify material properties are consistent
        assert concrete is not None
        assert steel is not None

        # Check elastic moduli are reasonable
        concrete_e = concrete.stress_strain_profile.elastic_modulus
        steel_e = steel.stress_strain_profile.elastic_modulus

        assert concrete_e > 0
        assert steel_e > 0
        assert steel_e > concrete_e  # Steel should be stiffer

    def test_material_compatibility(self):
        """Test that concrete and steel materials are compatible."""
        hk_code = HK2013()

        # Create various combinations
        combinations = [
            (30, 460),
            (40, 500),
            (50, 500),
        ]

        for fcu, fy in combinations:
            concrete = hk_code.create_concrete_material(compressive_strength=fcu)
            steel = hk_code.create_steel_material(yield_strength=fy)

            assert concrete is not None
            assert steel is not None
            assert "HK Code 2013" in concrete.name
            assert "HK Code 2013" in steel.name

    def test_hand_calculation_verification_c40(self):
        """Verify material properties against hand calculations for C40 concrete.

        Hand calculations:
        - f_cu = 40 MPa
        - E_cm = 3.46 * sqrt(40) + 3.21 = 3.46 * 6.3246 + 3.21 = 25.08 GPa
        - f_ct = 0.6 * sqrt(40) = 0.6 * 6.3246 = 3.79 MPa
        - α = 0.67 (for f_cu ≤ 60 MPa)
        - γ = 0.45 (for f_cu ≤ 60 MPa)
        """
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=40)

        # Calculate expected values by hand
        fcu = 40
        expected_e_gpa = 3.46 * math.sqrt(fcu) + 3.21
        expected_e_mpa = expected_e_gpa * 1000
        expected_fct = 0.6 * math.sqrt(fcu)
        expected_alpha = 0.67
        expected_gamma = 0.45

        # Verify calculated properties match hand calculations
        assert concrete.stress_strain_profile.elastic_modulus == pytest.approx(
            expected_e_mpa, rel=1e-3
        )
        assert concrete.flexural_tensile_strength == pytest.approx(
            expected_fct, rel=1e-3
        )
        assert concrete.ultimate_stress_strain_profile.alpha == pytest.approx(
            expected_alpha, rel=1e-6
        )
        assert concrete.ultimate_stress_strain_profile.gamma == pytest.approx(
            expected_gamma, rel=1e-6
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
