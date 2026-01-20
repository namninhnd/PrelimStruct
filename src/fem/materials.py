"""
Material models for FEM analysis with HK Code 2013 compliance.

This module provides material property definitions for concrete and steel
reinforcement based on Hong Kong Code of Practice for Structural Use of Concrete 2013.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import math


class ConcreteGrade(Enum):
    """HK Code 2013 standard concrete grades (characteristic cube strength).
    
    HK Code 2013 Table 3.1 - Concrete grades
    """
    C25 = 25  # MPa
    C30 = 30
    C35 = 35
    C40 = 40
    C45 = 45
    C50 = 50
    C55 = 55
    C60 = 60
    C70 = 70
    C80 = 80


class SteelGrade(Enum):
    """HK Code 2013 standard reinforcement steel grades.
    
    HK Code 2013 Cl 2.4.3.2 - Reinforcement characteristic strength
    """
    FY250 = 250  # MPa (shear links, mild steel)
    FY460 = 460  # MPa (high yield bars, HYB)
    FY500 = 500  # MPa (high yield bars, HYB - most common in HK)


@dataclass
class ConcreteProperties:
    """HK Code 2013 concrete material properties.
    
    Attributes:
        fcu: Characteristic cube strength (MPa)
        density: Concrete density (kN/m³) - default 24 (plain), 25 (reinforced)
        E_cm: Mean modulus of elasticity (GPa)
        f_ct: Flexural tensile strength (MPa)
        gamma_c: Partial safety factor for concrete (default 1.5 for ULS)
        alpha: Stress block factor (default 0.67 for parabolic-rectangular)
        gamma: Neutral axis depth factor (default 0.45 for fcu ≤ 60 MPa)
    """
    fcu: float  # MPa
    density: float = 25.0  # kN/m³ (reinforced concrete)
    E_cm: Optional[float] = None  # GPa
    f_ct: Optional[float] = None  # MPa
    gamma_c: float = 1.5  # Partial safety factor
    alpha: float = 0.67  # Stress block parameter
    gamma: float = 0.45  # Neutral axis depth factor
    
    def __post_init__(self):
        """Calculate derived properties per HK Code 2013."""
        if self.E_cm is None:
            self.E_cm = self.calculate_elastic_modulus()
        if self.f_ct is None:
            self.f_ct = self.calculate_flexural_tensile_strength()
        
        # Update stress block parameters for high strength concrete (fcu > 60 MPa)
        # HK Code 2013 Cl 6.1.2.4(b)
        if self.fcu > 60:
            self.alpha = 0.67 - (self.fcu - 60) / 400
            self.alpha = max(self.alpha, 0.50)  # Minimum 0.50
            self.gamma = 0.45 - (self.fcu - 60) / 800
            self.gamma = max(self.gamma, 0.35)  # Minimum 0.35
    
    def calculate_elastic_modulus(self) -> float:
        """Calculate modulus of elasticity per HK Code 2013.
        
        HK Code 2013 Cl 3.1.7:
        E_cm = 3.46 * sqrt(fcu) + 3.21 GPa
        
        Returns:
            Modulus of elasticity in GPa
        """
        return 3.46 * math.sqrt(self.fcu) + 3.21
    
    def calculate_flexural_tensile_strength(self) -> float:
        """Calculate flexural tensile strength per HK Code 2013.
        
        HK Code 2013 Cl 3.1.6.3:
        f_ct = 0.6 * sqrt(fcu) MPa
        
        Returns:
            Flexural tensile strength in MPa
        """
        return 0.6 * math.sqrt(self.fcu)
    
    @property
    def design_strength(self) -> float:
        """Design compressive strength = fcu / gamma_c (MPa)."""
        return self.fcu / self.gamma_c
    
    @property
    def E_Pa(self) -> float:
        """Elastic modulus in Pa (for OpenSeesPy)."""
        E_cm = self.E_cm if self.E_cm is not None else self.calculate_elastic_modulus()
        return E_cm * 1e9  # GPa to Pa
    
    @property
    def density_kg_m3(self) -> float:
        """Density in kg/m³ (for OpenSeesPy mass)."""
        return self.density * 1000 / 9.81  # kN/m³ to kg/m³


@dataclass
class SteelProperties:
    """HK Code 2013 reinforcement steel material properties.
    
    Attributes:
        fy: Characteristic yield strength (MPa)
        Es: Modulus of elasticity (GPa) - default 200 GPa
        gamma_s: Partial safety factor for steel (default 1.15 for ULS)
        epsilon_su: Ultimate strain (default 0.05 for ductile reinforcement)
        density: Steel density (kN/m³) - default 78.5
    """
    fy: float  # MPa
    Es: float = 200.0  # GPa (constant per HK Code 2013 Cl 3.2.5)
    gamma_s: float = 1.15  # Partial safety factor
    epsilon_su: float = 0.05  # Ultimate strain (5% for Class B ductility)
    density: float = 78.5  # kN/m³
    
    @property
    def design_strength(self) -> float:
        """Design yield strength = fy / gamma_s (MPa)."""
        return self.fy / self.gamma_s
    
    @property
    def Es_Pa(self) -> float:
        """Elastic modulus in Pa (for OpenSeesPy)."""
        return self.Es * 1e9  # GPa to Pa
    
    @property
    def density_kg_m3(self) -> float:
        """Density in kg/m³ (for OpenSeesPy mass)."""
        return self.density * 1000 / 9.81  # kN/m³ to kg/m³


def create_concrete_material(grade: ConcreteGrade, 
                            density: float = 25.0,
                            gamma_c: float = 1.5) -> ConcreteProperties:
    """Factory function to create concrete material from grade.
    
    Args:
        grade: HK Code concrete grade (e.g., C25, C30, C40)
        density: Concrete density in kN/m³ (default 25.0 for reinforced)
        gamma_c: Partial safety factor (default 1.5 for ULS)
    
    Returns:
        ConcreteProperties object with all derived properties calculated
        
    Example:
        >>> concrete = create_concrete_material(ConcreteGrade.C40)
        >>> concrete.fcu
        40
        >>> round(concrete.E_cm, 2)
        24.99
    """
    return ConcreteProperties(
        fcu=grade.value,
        density=density,
        gamma_c=gamma_c,
    )


def create_steel_material(grade: SteelGrade,
                         gamma_s: float = 1.15,
                         epsilon_su: float = 0.05) -> SteelProperties:
    """Factory function to create steel material from grade.
    
    Args:
        grade: HK Code steel grade (e.g., FY500, FY460)
        gamma_s: Partial safety factor (default 1.15 for ULS)
        epsilon_su: Ultimate strain (default 0.05 for Class B ductility)
    
    Returns:
        SteelProperties object with all properties set
        
    Example:
        >>> steel = create_steel_material(SteelGrade.FY500)
        >>> steel.fy
        500
        >>> steel.Es
        200.0
    """
    return SteelProperties(
        fy=grade.value,
        gamma_s=gamma_s,
        epsilon_su=epsilon_su,
    )


def get_openseespy_concrete_material(concrete: ConcreteProperties, 
                                    material_tag: int) -> dict:
    """Generate OpenSeesPy uniaxialMaterial Concrete01 parameters.
    
    This creates a simplified concrete material model suitable for frame analysis.
    For more advanced stress-strain behavior, use ConcreteProperties library.
    
    HK Code 2013 Cl 6.1.2.4 - Ultimate concrete stress-strain
    
    Args:
        concrete: ConcreteProperties object
        material_tag: Unique material tag for OpenSeesPy
    
    Returns:
        Dictionary with OpenSeesPy material parameters:
        - material_type: "Concrete01"
        - tag: material tag
        - fpc: Compressive strength (negative, in Pa)
        - epsc0: Strain at peak stress (typically -0.002)
        - fpcu: Crushing strength (negative, in Pa)
        - epsU: Strain at crushing (typically -0.0035)
    
    Example:
        >>> concrete = create_concrete_material(ConcreteGrade.C40)
        >>> params = get_openseespy_concrete_material(concrete, material_tag=1)
        >>> params['material_type']
        'Concrete01'
    """
    # HK Code 2013 Cl 6.1.2.4 - design compressive strength
    fpc = -concrete.design_strength * 1e6  # MPa to Pa, negative for compression
    
    # Peak strain at maximum stress (typically 0.002 for concrete)
    epsc0 = -0.002
    
    # Crushing strength (typically 0.85 * fpc after peak)
    fpcu = 0.85 * fpc
    
    # Ultimate crushing strain (HK Code: typically 0.0035)
    epsU = -0.0035
    
    return {
        'material_type': 'Concrete01',
        'tag': material_tag,
        'fpc': fpc,
        'epsc0': epsc0,
        'fpcu': fpcu,
        'epsU': epsU,
    }


def get_openseespy_steel_material(steel: SteelProperties, 
                                 material_tag: int) -> dict:
    """Generate OpenSeesPy uniaxialMaterial Steel01 parameters.
    
    This creates an elastic-plastic steel material model with strain hardening.
    
    HK Code 2013 Cl 3.2.5 - Reinforcement stress-strain
    
    Args:
        steel: SteelProperties object
        material_tag: Unique material tag for OpenSeesPy
    
    Returns:
        Dictionary with OpenSeesPy material parameters:
        - material_type: "Steel01"
        - tag: material tag
        - fy: Yield strength (in Pa)
        - E0: Initial elastic modulus (in Pa)
        - b: Strain hardening ratio (typically 0.01)
    
    Example:
        >>> steel = create_steel_material(SteelGrade.FY500)
        >>> params = get_openseespy_steel_material(steel, material_tag=2)
        >>> params['material_type']
        'Steel01'
    """
    # Design yield strength
    fy = steel.design_strength * 1e6  # MPa to Pa
    
    # Elastic modulus
    E0 = steel.Es_Pa
    
    # Strain hardening ratio (typically 1% for reinforcement)
    b = 0.01
    
    return {
        'material_type': 'Steel01',
        'tag': material_tag,
        'fy': fy,
        'E0': E0,
        'b': b,
    }


def get_elastic_beam_section(concrete: ConcreteProperties,
                             width: float,
                             height: float,
                             section_tag: int) -> dict:
    """Generate elastic beam section properties for OpenSeesPy.
    
    This creates a simplified elastic section for linear static analysis.
    
    Args:
        concrete: ConcreteProperties object
        width: Section width in mm
        height: Section height (depth) in mm
        section_tag: Unique section tag for OpenSeesPy
    
    Returns:
        Dictionary with section properties:
        - section_type: "ElasticBeamSection"
        - tag: section tag
        - E: Young's modulus (Pa)
        - A: Cross-sectional area (m²)
        - Iz: Second moment of area about z-axis (m⁴)
        - Iy: Second moment of area about y-axis (m⁴)
        - G: Shear modulus (Pa)
        - J: Torsional constant (m⁴)
    """
    # Convert dimensions to meters
    b = width / 1000  # mm to m
    h = height / 1000  # mm to m
    
    # Section properties
    A = b * h  # m²
    Iz = b * h**3 / 12  # m⁴ (bending about z-axis)
    Iy = h * b**3 / 12  # m⁴ (bending about y-axis)
    
    # Shear modulus (G = E / (2 * (1 + nu)), assuming nu = 0.2 for concrete)
    G = concrete.E_Pa / (2 * 1.2)
    
    # Torsional constant (approximate for rectangular section)
    # J = k * b * h³ where k depends on b/h ratio
    ratio = max(b, h) / min(b, h)
    if ratio >= 10:
        k = 1/3
    elif ratio >= 5:
        k = 0.291
    elif ratio >= 3:
        k = 0.263
    else:
        k = 0.141 * (1 - 0.42 * min(b, h) / max(b, h))
    
    if b >= h:
        J = k * h * b**3
    else:
        J = k * b * h**3
    
    return {
        'section_type': 'ElasticBeamSection',
        'tag': section_tag,
        'E': concrete.E_Pa,
        'A': A,
        'Iz': Iz,
        'Iy': Iy,
        'G': G,
        'J': J,
    }


# Material tag counter for automatic tag generation
_material_tag_counter = 0
_section_tag_counter = 0


def get_next_material_tag() -> int:
    """Get next available material tag for OpenSeesPy."""
    global _material_tag_counter
    _material_tag_counter += 1
    return _material_tag_counter


def get_next_section_tag() -> int:
    """Get next available section tag for OpenSeesPy."""
    global _section_tag_counter
    _section_tag_counter += 1
    return _section_tag_counter


def reset_material_tags() -> None:
    """Reset material tag counter (useful for testing)."""
    global _material_tag_counter, _section_tag_counter
    _material_tag_counter = 0
    _section_tag_counter = 0
