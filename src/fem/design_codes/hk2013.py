"""
Hong Kong Code of Practice for Structural Use of Concrete 2013 (2020 edition).

This module implements the HK2013 design code as an extension of the
ConcreteProperties library DesignCode base class.
"""

import math
import numpy as np
from scipy.interpolate import interp1d
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
        # E_cm = 3.46 * sqrt(f_cu) + 3.21 (GPa)
        elastic_modulus = 3.46 * math.sqrt(compressive_strength) + 3.21
        elastic_modulus_mpa = elastic_modulus * 1000  # Convert GPa to MPa

        # Calculate stress block parameters (HK Code 2013 Cl 6.1.2.4)
        if compressive_strength <= 60:
            alpha = 0.67
            gamma = 0.45
        else:
            # High strength concrete adjustments
            alpha = 0.67 - (compressive_strength - 60) / 400
            alpha = max(alpha, 0.50)  # Minimum 0.50
            gamma = 0.45 - (compressive_strength - 60) / 800
            gamma = max(gamma, 0.35)  # Minimum 0.35

        # Calculate flexural tensile strength (HK Code 2013 Cl 3.1.6.3)
        # f_ct = 0.6 * sqrt(f_cu)
        flexural_tensile_strength = 0.6 * math.sqrt(compressive_strength)

        # Density: 24 kN/m³ for plain concrete, 25 kN/m³ for reinforced
        # Convert to kg/mm³: 24 kN/m³ = 24000 N/m³ = 24000/9.81 kg/m³
        #                   = 2447 kg/m³ = 2.447e-6 kg/mm³
        # For ConcreteProperties: use 2.4e-6 kg/mm³
        density = 2.4e-6  # kg/mm³

        # Ultimate concrete strain (HK Code 2013 Cl 6.1.2.4)
        ultimate_strain = 0.0035

        return Concrete(
            name=name,
            density=density,
            stress_strain_profile=ssp.ConcreteLinearNoTension(
                elastic_modulus=elastic_modulus_mpa,
                ultimate_strain=ultimate_strain,
                compressive_strength=0.67 * compressive_strength,  # Service stress
            ),
            ultimate_stress_strain_profile=ssp.RectangularStressBlock(
                compressive_strength=compressive_strength,
                alpha=alpha,
                gamma=gamma,
                ultimate_strain=ultimate_strain,
            ),
            flexural_tensile_strength=flexural_tensile_strength,
            colour=colour,
        )

    def create_steel_material(
        self,
        yield_strength: float = 500,
        ductility_class: str = "B",
        colour: str = "grey",
    ) -> SteelBar:
        """Returns a steel bar material object to HK Code 2013.

        .. admonition:: Material assumptions

          - *Density*: 7850 kg/m³ (7.85 x 10⁻⁶ kg/mm³)

          - *Elastic modulus*: 200 GPa (HK Code 2013 Cl 3.2.5)

          - *Stress-strain profile*: Elastic-plastic with optional strain hardening

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
        if ductility_class not in ["A", "B", "C"]:
            msg = "ductility_class must be 'A', 'B', or 'C'."
            raise ValueError(msg)

        # Create steel grade name
        name = f"FY{yield_strength:.0f} Steel (HK Code 2013, Class {ductility_class})"

        # Elastic modulus (HK Code 2013 Cl 3.2.5)
        elastic_modulus = 200_000  # MPa

        # Density: 7850 kg/m³ = 7.85e-6 kg/mm³
        density = 7.85e-6  # kg/mm³

        # Ultimate strain based on ductility class
        # HK Code 2013 Cl 2.4.3.2
        if ductility_class == "A":
            fracture_strain = 0.025  # 2.5%
        elif ductility_class == "B":
            fracture_strain = 0.05   # 5.0%
        else:  # Class C
            fracture_strain = 0.075  # 7.5%

        return SteelBar(
            name=name,
            density=density,
            stress_strain_profile=ssp.SteelElasticPlastic(
                yield_strength=yield_strength,
                elastic_modulus=elastic_modulus,
                fracture_strain=fracture_strain,
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
