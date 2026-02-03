"""
Hong Kong Code of Practice for Structural Use of Concrete 2013 (2020 edition).

This module implements the HK2013 design code as an extension of the
ConcreteProperties library DesignCode base class.
"""

from dataclasses import dataclass, field
import math
from concreteproperties.design_codes.design_code import DesignCode
from concreteproperties.concrete_section import ConcreteSection
from concreteproperties.material import Concrete, SteelBar
import concreteproperties.stress_strain_profile as ssp

# Import default units from concreteproperties
try:
    from concreteproperties.utils import DEFAULT_UNITS, si_n_mm
except ImportError:
    # Fallback if the utils module structure is different
    DEFAULT_UNITS = None
    si_n_mm = None


def _calculate_elastic_modulus_mpa(compressive_strength: float) -> float:
    """Calculate elastic modulus in MPa per HK Code 2013 Cl 3.1.7."""
    return (3.46 * math.sqrt(compressive_strength) + 3.21) * 1000


def _calculate_stress_block_parameters(
    compressive_strength: float,
) -> tuple[float, float]:
    """Calculate HK Code 2013 stress block parameters (Cl 6.1.2.4(b)).

    Args:
        compressive_strength: Characteristic cube strength f_cu in MPa.

    Returns:
        Tuple of (alpha, gamma) stress block coefficients.
    """
    if compressive_strength <= 60:
        return 0.67, 0.45

    alpha = 0.67 - (compressive_strength - 60) / 400
    gamma = 0.45 - (compressive_strength - 60) / 800
    return max(alpha, 0.50), max(gamma, 0.35)


def _get_steel_fracture_strain(ductility_class: str) -> float:
    """Map HK Code 2013 ductility classes to fracture strain (Cl 2.4.3.2)."""
    ductility = ductility_class.upper()
    fracture_strains = {"A": 0.025, "B": 0.05, "C": 0.075}
    if ductility not in fracture_strains:
        msg = "ductility_class must be 'A', 'B', or 'C'."
        raise ValueError(msg)
    return fracture_strains[ductility]


class HKConcreteServiceProfile(ssp.ConcreteServiceProfile):
    """HK Code 2013 service stress-strain profile (linear, no tension).

    HK Code 2013 Cl 3.1.7 (elastic modulus) and Cl 6.1.2.4 (0.67 f_cu service
    stress) with no tensile capacity.
    """

    def __init__(
        self,
        compressive_strength: float,
        ultimate_strain: float = 0.0035,
        stress_factor: float = 0.67,
        elastic_modulus: float | None = None,
    ) -> None:
        """Build linear no-tension profile anchored at 0.67f_cu."""
        if compressive_strength < 25 or compressive_strength > 80:
            msg = "compressive_strength must be between 25 MPa and 80 MPa."
            raise ValueError(msg)

        self.compressive_strength = compressive_strength
        self.ultimate_strain = ultimate_strain
        self.stress_factor = stress_factor
        self.elastic_modulus = elastic_modulus or _calculate_elastic_modulus_mpa(
            compressive_strength
        )

        service_strength = self.stress_factor * self.compressive_strength
        compressive_strain = service_strength / self.elastic_modulus

        strains = [-1e-6, 0.0, compressive_strain, self.ultimate_strain]
        stresses = [0.0, 0.0, service_strength, service_strength]

        super().__init__(
            strains=strains,
            stresses=stresses,
            ultimate_strain=ultimate_strain,
        )


class HKConcreteUltimateProfile(ssp.ConcreteUltimateProfile):
    """HK Code 2013 ultimate rectangular stress block (Cl 6.1.2.4)."""

    def __init__(
        self,
        compressive_strength: float,
        ultimate_strain: float = 0.0035,
    ) -> None:
        """Create rectangular stress block with HK high-strength adjustments."""
        if compressive_strength < 25 or compressive_strength > 80:
            msg = "compressive_strength must be between 25 MPa and 80 MPa."
            raise ValueError(msg)

        self.alpha, self.gamma = _calculate_stress_block_parameters(
            compressive_strength
        )
        self.compressive_strength = compressive_strength
        self.ultimate_strain = ultimate_strain

        plateau_start = self.ultimate_strain * (1 - self.gamma)
        plateau_stress = self.alpha * self.compressive_strength

        strains = [0.0, plateau_start, plateau_start, self.ultimate_strain]
        stresses = [0.0, 0.0, plateau_stress, plateau_stress]

        super().__init__(
            strains=strains,
            stresses=stresses,
            compressive_strength=compressive_strength,
        )

    def get_stress(
        self,
        strain: float,
    ) -> float:
        """Return stress with plateau tolerance for rectangular stress block."""
        if strain >= self.strains[1] - 1e-8:
            return self.stresses[2]
        return 0.0


@dataclass
class HKSteelProfile(ssp.SteelProfile):
    """HK Code 2013 reinforcement steel stress-strain (elastic-plastic).

    HK Code 2013 Cl 3.2.5 (E_s = 200 GPa) and Cl 2.4.3.2 ductility classes
    (Class A 2.5%, Class B 5.0%, Class C 7.5%). Optional strain hardening via
    hardening_ratio (fraction of f_y).
    """

    yield_strength: float
    ductility_class: str = "B"
    elastic_modulus: float = 200_000
    hardening_ratio: float | None = None
    fracture_strain: float = field(init=False)
    strains: list[float] = field(init=False)
    stresses: list[float] = field(init=False)

    def __post_init__(self) -> None:
        """Build symmetric elastic-plastic profile with optional hardening."""
        self.fracture_strain = _get_steel_fracture_strain(self.ductility_class)

        yield_strain = self.yield_strength / self.elastic_modulus
        self.strains = [
            -self.fracture_strain,
            -yield_strain,
            0.0,
            yield_strain,
            self.fracture_strain,
        ]

        if self.hardening_ratio is None:
            stress_y = self.yield_strength
            self.stresses = [-stress_y, -stress_y, 0.0, stress_y, stress_y]
        else:
            ultimate_strength = self.yield_strength * (1 + self.hardening_ratio)
            self.stresses = [
                -ultimate_strength,
                -self.yield_strength,
                0.0,
                self.yield_strength,
                ultimate_strength,
            ]

        super().__post_init__()


class HKShearSteelProfile(HKSteelProfile):
    """HK Code 2013 shear link/stirrup steel profile (elastic-plastic).

    Defaults to mild steel links (f_yv = 250 MPa, Class A ductility 2.5%).
    """

    def __init__(
        self,
        yield_strength: float = 250,
        ductility_class: str = "A",
        elastic_modulus: float = 200_000,
        hardening_ratio: float | None = None,
    ) -> None:
        super().__init__(
            yield_strength=yield_strength,
            ductility_class=ductility_class,
            elastic_modulus=elastic_modulus,
            hardening_ratio=hardening_ratio,
        )


class HK2013(DesignCode):
    """Design code class for Hong Kong Code of Practice for Structural Use of
    Concrete 2013 (2020 edition).

    This class extends the ConcreteProperties library DesignCode base class to provide
    material properties, stress-strain profiles, and design provisions specific to
    HK Code 2013.

    .. note::
        This design code only supports :class:`~concreteproperties.material.Concrete`
        and :class:`~concreteproperties.material.SteelBar` material objects.

    References:
        - Code of Practice for Structural Use of Concrete 2013 (2020 edition)
        - Manual for Design and Detailing of Reinforced Concrete to HK Code 2013
    """

    def __init__(self) -> None:
        """Initializes the HK2013 design code class."""
        super().__init__()
        self.reinforcement_class = "B"  # Default to Class B (ductile)

    def assign_concrete_section(
        self,
        concrete_section: ConcreteSection,
    ) -> None:
        """Assigns a concrete section to the design code.

        Args:
            concrete_section: Concrete section object to analyse

        Raises:
            ValueError: If there is meshed reinforcement within the concrete_section
        """
        self.concrete_section = concrete_section

        # Check for meshed reinforcement (not supported)
        if hasattr(concrete_section, 'reinf_geometries_meshed') and \
           concrete_section.reinf_geometries_meshed:
            msg = "Meshed reinforcement is not supported in this design code."
            raise ValueError(msg)

        # Assign default units if not provided
        if DEFAULT_UNITS is not None and si_n_mm is not None:
            if self.concrete_section.default_units is DEFAULT_UNITS:
                self.concrete_section.default_units = si_n_mm
                self.concrete_section.gross_properties.default_units = si_n_mm

        # Determine reinforcement ductility class based on ultimate strain
        # HK Code 2013 Cl 2.4.3.2: Class B requires ε_su ≥ 5%
        self.reinforcement_class = "B"  # Default to Class B (ductile)

        if hasattr(concrete_section, 'reinf_geometries_lumped'):
            for steel_geom in concrete_section.reinf_geometries_lumped:
                ultimate_strain = abs(
                    steel_geom.material.stress_strain_profile.get_ultimate_tensile_strain()
                )
                if ultimate_strain < 0.05:  # Less than 5%
                    self.reinforcement_class = "A"  # Low ductility

        # Calculate squash and tensile load
        if hasattr(self, 'squash_tensile_load'):
            squash, tensile = self.squash_tensile_load()
            self.squash_load = squash
            self.tensile_load = tensile

    def create_concrete_material(
        self,
        compressive_strength: float,
        colour: str = "lightgrey",
    ) -> Concrete:
        """Returns a concrete material object to HK Code 2013.

        .. admonition:: Material assumptions

          - *Density*: 24 kN/m³ (2.4 x 10⁻⁶ kg/mm³) for normal weight concrete

          - *Elastic modulus*: HK Code 2013 Cl 3.1.7:
            E_cm = 3.46√f_cu + 3.21 (GPa)

          - *Service stress-strain profile*: Linear with no tension, compressive
            strength at 0.67f_cu (characteristic strength)

          - *Ultimate stress-strain profile*: Rectangular stress block per
            HK Code 2013 Cl 6.1.2.4:
            - α = 0.67 for f_cu ≤ 60 MPa
            - α = 0.67 - (f_cu - 60)/400 for f_cu > 60 MPa (min 0.50)
            - γ = 0.45 for f_cu ≤ 60 MPa
            - γ = 0.45 - (f_cu - 60)/800 for f_cu > 60 MPa (min 0.35)

          - *Ultimate concrete strain*: 0.0035 (HK Code 2013 Cl 6.1.2.4)

          - *Flexural tensile strength*: HK Code 2013 Cl 3.1.6.3:
            f_ct = 0.6√f_cu (MPa)

        Args:
            compressive_strength: Characteristic cube strength at 28 days (f_cu)
                in megapascals (MPa). Typical range: 25-80 MPa.
            colour: Colour of the concrete for rendering. Defaults to "lightgrey".

        Raises:
            ValueError: If compressive_strength is not between 25 MPa and 80 MPa.

        Returns:
            Concrete material object with HK Code 2013 properties

        Example:
            >>> hk_code = HK2013()
            >>> concrete = hk_code.create_concrete_material(40)
            >>> concrete.name
            'C40 Concrete (HK Code 2013)'
        """
        # Validate input range
        if compressive_strength < 25 or compressive_strength > 80:
            msg = "compressive_strength must be between 25 MPa and 80 MPa."
            raise ValueError(msg)

        # Create concrete grade name
        name = f"C{compressive_strength:.0f} Concrete (HK Code 2013)"

        # Calculate elastic modulus (HK Code 2013 Cl 3.1.7)
        elastic_modulus_mpa = _calculate_elastic_modulus_mpa(compressive_strength)

        # Calculate stress block parameters (HK Code 2013 Cl 6.1.2.4)
        alpha, gamma = _calculate_stress_block_parameters(compressive_strength)

        # Calculate flexural tensile strength (HK Code 2013 Cl 3.1.6.3)
        # f_ct = 0.6 * sqrt(f_cu)
        flexural_tensile_strength = 0.6 * math.sqrt(compressive_strength)

        # Density: 25 kN/m³ for reinforced concrete
        # Convert to kg/mm³: 25 kN/m³ = 25_000 / 9.81 kg/m³ = 2548 kg/m³
        # For ConcreteProperties: use 2.5e-6 kg/mm³
        density = 2.5e-6  # kg/mm³

        # Ultimate concrete strain (HK Code 2013 Cl 6.1.2.4)
        ultimate_strain = 0.0035

        return Concrete(
            name=name,
            density=density,
            stress_strain_profile=HKConcreteServiceProfile(
                compressive_strength=compressive_strength,
                ultimate_strain=ultimate_strain,
                elastic_modulus=elastic_modulus_mpa,
            ),
            ultimate_stress_strain_profile=HKConcreteUltimateProfile(
                compressive_strength=compressive_strength,
                ultimate_strain=ultimate_strain,
            ),
            flexural_tensile_strength=flexural_tensile_strength,
            colour=colour,
        )

    def create_steel_material(
        self,
        yield_strength: float = 500,
        ductility_class: str = "B",
        strain_hardening_ratio: float | None = None,
        colour: str = "grey",
    ) -> SteelBar:
        """Returns a steel bar material object to HK Code 2013.

        .. admonition:: Material assumptions

          - *Density*: 7850 kg/m³ (7.85 x 10⁻⁶ kg/mm³)

          - *Elastic modulus*: 200 GPa (HK Code 2013 Cl 3.2.5)

          - *Stress-strain profile*: Elastic-plastic with optional strain hardening
            (set strain_hardening_ratio to amplify plateau)

          - *Ultimate strain*: Depends on ductility class
            - Class A (Low ductility): ε_su = 2.5%
            - Class B (Normal ductility): ε_su = 5.0%
            - Class C (High ductility): ε_su = 7.5%

        Args:
            yield_strength: Characteristic yield strength (f_y) in MPa.
                Common values in Hong Kong:
                - 250 MPa for mild steel links/stirrups
                - 460 MPa for high yield bars (HYB)
                - 500 MPa for high yield bars (HYB) - most common
                Defaults to 500 MPa.
            ductility_class: Reinforcement ductility class per HK Code 2013
                - "A": Low ductility (ε_su ≥ 2.5%)
                - "B": Normal ductility (ε_su ≥ 5.0%) - default
                - "C": High ductility (ε_su ≥ 7.5%)
                Defaults to "B".
            strain_hardening_ratio: Optional strain hardening ratio (e.g., 0.1 gives
                1.1 f_y at fracture strain). Defaults to None (perfectly plastic).
            colour: Colour of the steel for rendering. Defaults to "grey".

        Raises:
            ValueError: If yield_strength is not between 250 MPa and 500 MPa,
                or if ductility_class is not "A", "B", or "C".

        Returns:
            SteelBar material object with HK Code 2013 properties

        Example:
            >>> hk_code = HK2013()
            >>> steel = hk_code.create_steel_material(500, ductility_class="B")
            >>> steel.name
            'FY500 Steel (HK Code 2013, Class B)'
        """
        # Validate input range
        if yield_strength < 250 or yield_strength > 500:
            msg = "yield_strength must be between 250 MPa and 500 MPa."
            raise ValueError(msg)

        # Validate ductility class
        ductility_class = ductility_class.upper()
        _ = _get_steel_fracture_strain(ductility_class)

        # Create steel grade name
        name = f"FY{yield_strength:.0f} Steel (HK Code 2013, Class {ductility_class})"

        # Elastic modulus (HK Code 2013 Cl 3.2.5)
        elastic_modulus = 200_000  # MPa

        # Density: 7850 kg/m³ = 7.85e-6 kg/mm³
        density = 7.85e-6  # kg/mm³

        # Ultimate strain based on ductility class
        # HK Code 2013 Cl 2.4.3.2
        return SteelBar(
            name=name,
            density=density,
            stress_strain_profile=HKSteelProfile(
                yield_strength=yield_strength,
                elastic_modulus=elastic_modulus,
                ductility_class=ductility_class,
                hardening_ratio=strain_hardening_ratio,
            ),
            colour=colour,
        )

    def get_capacity_reduction_factor(
        self,
        failure_mode: str = "flexure",
    ) -> float:
        """Returns the capacity reduction factor (phi) per HK Code 2013.

        HK Code 2013 uses partial safety factors rather than phi factors.
        This method provides equivalent capacity reduction for comparison.

        Args:
            failure_mode: Type of failure mode:
                - "flexure": Flexural failure (ductile)
                - "compression": Compression-controlled failure
                - "shear": Shear failure
                - "tension": Tension-controlled failure
                Defaults to "flexure".

        Returns:
            Equivalent capacity reduction factor (for reference only)

        Note:
            HK Code 2013 uses partial safety factors (γ_c = 1.5, γ_s = 1.15)
            rather than capacity reduction factors. This method is provided
            for comparison with other design codes.
        """
        # HK Code 2013 does not use phi factors like AS3600 or ACI318
        # Instead, it uses partial safety factors on materials
        # Provided here for reference/comparison purposes only

        factors = {
            "flexure": 0.85,      # Approximate equivalent
            "compression": 0.70,  # Approximate equivalent
            "shear": 0.75,        # Approximate equivalent
            "tension": 0.90,      # Approximate equivalent
        }

        return factors.get(failure_mode, 0.85)
