"""
Integration tests for HK2013 materials against HK Code 2013 expectations.

Focus:
- Material property values vs HK Code formulas (elastic modulus, stress blocks)
- Stress-strain curve behaviour for concrete and steel profiles
- Simple hand-calculated resultant forces for a fully compressed block
"""

import math

import pytest

from src.fem.design_codes.hk2013 import (
    HK2013,
    HKConcreteUltimateProfile,
    HKSteelProfile,
)


@pytest.mark.parametrize(
    "fcu,expected_alpha,expected_gamma",
    [
        (25, 0.67, 0.45),
        (60, 0.67, 0.45),
        (80, 0.67 - (80 - 60) / 400, 0.45 - (80 - 60) / 800),
    ],
)
def test_concrete_stress_block_parameters_against_code(fcu, expected_alpha, expected_gamma):
    """Validate HK stress block parameters across strength range."""
    hk_code = HK2013()
    concrete = hk_code.create_concrete_material(compressive_strength=fcu)
    profile: HKConcreteUltimateProfile = concrete.ultimate_stress_strain_profile

    assert profile.alpha == pytest.approx(expected_alpha, rel=1e-6)
    assert profile.gamma == pytest.approx(expected_gamma, rel=1e-6)
    assert profile.get_stress(profile.ultimate_strain) == pytest.approx(
        expected_alpha * fcu, rel=1e-6
    )


def test_concrete_block_compression_force_matches_hand_calc():
    """Rectangular block compression force matches alpha*f_cu*area hand calc."""
    fcu = 40
    area_mm2 = 500 * 500  # 500 mm x 500 mm block
    hk_code = HK2013()
    concrete = hk_code.create_concrete_material(compressive_strength=fcu)
    profile: HKConcreteUltimateProfile = concrete.ultimate_stress_strain_profile

    plateau_stress = profile.get_stress(profile.ultimate_strain)
    expected_force_n = plateau_stress * area_mm2  # MPa * mm^2 = N

    assert plateau_stress == pytest.approx(0.67 * fcu, rel=1e-6)
    assert expected_force_n == pytest.approx(0.67 * fcu * area_mm2, rel=1e-6)


def test_steel_profile_symmetry_and_hardening():
    """Steel profile symmetry and hardening plateau follow HK ductility classes."""
    profile = HKSteelProfile(yield_strength=500, ductility_class="C", hardening_ratio=0.1)
    fy = 500
    fu = fy * 1.1
    eps_y = fy / profile.elastic_modulus

    # Symmetric stresses about zero
    near_yield_stress = profile.get_stress(eps_y * 1.01)
    assert near_yield_stress == pytest.approx(
        fy + (fu - fy) * (eps_y * 0.01) / (profile.fracture_strain - eps_y),
        rel=1e-6,
    )
    assert profile.get_stress(-eps_y * 1.01) == pytest.approx(-near_yield_stress, rel=1e-6)

    # Hardening plateau at fracture strain (7.5% for Class C)
    assert profile.get_ultimate_tensile_strain() == pytest.approx(-0.075, rel=1e-6)
    assert profile.get_stress(profile.fracture_strain) == pytest.approx(fu, rel=1e-6)


# ============================================================================
# Additional integration tests for HK2013 design code
# ============================================================================


class TestConcreteElasticModulusFormula:
    """Test elastic modulus formula across concrete grades."""

    @pytest.mark.parametrize("fcu", [25, 30, 35, 40, 45, 50, 60, 70, 80])
    def test_elastic_modulus_formula(self, fcu):
        """Test E_cm = 3.46√f_cu + 3.21 GPa for all grades."""
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=fcu)

        expected_e_gpa = 3.46 * math.sqrt(fcu) + 3.21
        expected_e_mpa = expected_e_gpa * 1000

        assert concrete.stress_strain_profile.elastic_modulus == pytest.approx(
            expected_e_mpa, rel=1e-3
        )


class TestConcreteFlexuralTensileStrength:
    """Test flexural tensile strength formula across concrete grades."""

    @pytest.mark.parametrize("fcu", [25, 30, 35, 40, 45, 50, 60, 70, 80])
    def test_flexural_tensile_strength_formula(self, fcu):
        """Test f_ct = 0.6√f_cu for all grades."""
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=fcu)

        expected_fct = 0.6 * math.sqrt(fcu)
        assert concrete.flexural_tensile_strength == pytest.approx(expected_fct, rel=1e-3)


class TestHighStrengthConcrete:
    """Test high strength concrete (f_cu > 60 MPa) adjustments."""

    @pytest.mark.parametrize(
        "fcu",
        [70, 80],
    )
    def test_high_strength_stress_block_adjustments(self, fcu):
        """Test stress block parameter reduction for f_cu > 60 MPa."""
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=fcu)
        profile: HKConcreteUltimateProfile = concrete.ultimate_stress_strain_profile

        expected_alpha = max(0.50, 0.67 - (fcu - 60) / 400)
        expected_gamma = max(0.35, 0.45 - (fcu - 60) / 800)

        assert profile.alpha == pytest.approx(expected_alpha, rel=1e-4)
        assert profile.gamma == pytest.approx(expected_gamma, rel=1e-4)


class TestSteelDuctilityClasses:
    """Test steel ductility class strain limits."""

    @pytest.mark.parametrize(
        "ductility_class,expected_strain",
        [
            ("A", 0.025),  # 2.5%
            ("B", 0.05),   # 5.0%
            ("C", 0.075),  # 7.5%
        ],
    )
    def test_ductility_class_strain_limits(self, ductility_class, expected_strain):
        """Test that ductility classes have correct fracture strains."""
        hk_code = HK2013()
        steel = hk_code.create_steel_material(
            yield_strength=500,
            ductility_class=ductility_class
        )

        assert steel.stress_strain_profile.fracture_strain == pytest.approx(
            expected_strain, rel=1e-6
        )


class TestMaterialDensities:
    """Test material densities match HK Code 2013."""

    def test_concrete_density(self):
        """Test reinforced concrete density = 25 kN/m³."""
        hk_code = HK2013()
        concrete = hk_code.create_concrete_material(compressive_strength=40)

        # ConcreteProperties uses kg/mm³ unit system
        expected_density = 2.5e-6  # kg/mm³ = 2500 kg/m³ = 25 kN/m³
        assert concrete.density == pytest.approx(expected_density, rel=1e-6)

    def test_steel_density(self):
        """Test steel density = 78.5 kN/m³."""
        hk_code = HK2013()
        steel = hk_code.create_steel_material(yield_strength=500)

        # ConcreteProperties uses kg/mm³ unit system
        expected_density = 7.85e-6  # kg/mm³ = 7850 kg/m³
        assert steel.density == pytest.approx(expected_density, rel=1e-6)


class TestServiceProfileBehavior:
    """Test service profile stress-strain behavior."""

    def test_service_no_tension(self):
        """Test that service profile returns 0 stress for tensile strains."""
        from src.fem.design_codes.hk2013 import HKConcreteServiceProfile

        profile = HKConcreteServiceProfile(compressive_strength=40)

        # Tensile strains (positive for tension in some conventions, negative in others)
        assert profile.get_stress(-1e-4) == pytest.approx(0.0, abs=1e-12)
        assert profile.get_stress(-1e-3) == pytest.approx(0.0, abs=1e-12)

    def test_service_linear_compression(self):
        """Test that service profile is linear in compression up to limit."""
        from src.fem.design_codes.hk2013 import HKConcreteServiceProfile

        fcu = 40
        profile = HKConcreteServiceProfile(compressive_strength=fcu)

        e_mod = profile.elastic_modulus
        max_stress = 0.67 * fcu
        max_strain = max_stress / e_mod

        # Linear portion
        test_strain = max_strain * 0.5
        expected_stress = e_mod * test_strain
        assert profile.get_stress(test_strain) == pytest.approx(expected_stress, rel=1e-4)


class TestUltimateProfileBehavior:
    """Test ultimate profile stress-strain behavior."""

    def test_ultimate_plateau_stress(self):
        """Test that ultimate profile reaches plateau stress."""
        profile = HKConcreteUltimateProfile(compressive_strength=40)

        plateau_strain = profile.strains[1]  # End of zero region
        plateau_stress = profile.alpha * 40

        # Just past the plateau start should give full stress
        test_strain = plateau_strain + 1e-5
        assert profile.get_stress(test_strain) == pytest.approx(plateau_stress, rel=1e-4)

    def test_ultimate_strain_limit(self):
        """Test that ultimate strain is 0.0035."""
        profile = HKConcreteUltimateProfile(compressive_strength=40)

        assert profile.ultimate_strain == pytest.approx(0.0035, rel=1e-6)
