"""
Punching Shear Check - HK Code 2013 Clause 6.1.5.6
Critical check for flat slabs and slabs with concentrated loads.
"""

import math
from typing import Dict, Any, List, Tuple
from enum import Enum

from ..core.constants import (
    CONCRETE_DENSITY,
    GAMMA_C,
    SHEAR_STRESS_MAX_FACTOR,
    SHEAR_STRESS_MAX_LIMIT,
)
from ..core.data_models import ProjectData


class ColumnLocation(Enum):
    """Column location for punching shear beta factor"""
    INTERIOR = "interior"
    EDGE = "edge"
    CORNER = "corner"


class PunchingShearResult:
    """Results from punching shear check"""

    def __init__(self):
        self.V_Ed: float = 0.0          # Design shear force (kN)
        self.v_Ed: float = 0.0          # Design shear stress (MPa)
        self.v_Rd: float = 0.0          # Design shear resistance (MPa)
        self.v_max: float = 0.0         # Maximum shear stress limit (MPa)
        self.perimeter: float = 0.0     # Critical perimeter (mm)
        self.utilization: float = 0.0
        self.status: str = "OK"
        self.warnings: List[str] = []
        self.calculations: List[Dict[str, Any]] = []
        self.shear_reinforcement_required: bool = False
        self.shear_reinforcement_area: float = 0.0  # mm²


class PunchingShearEngine:
    """
    Punching shear calculator per HK Code 2013 Clause 6.1.5.6.
    Checks slab-column connections for flat slab systems.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

    def _add_calc_step(self, description: str, calculation: str, reference: str = ""):
        """Add a calculation step to the audit trail"""
        self.calculations.append({
            "description": description,
            "calculation": calculation,
            "reference": reference
        })

    def check_punching_shear(
        self,
        column_size: int,
        slab_thickness: int,
        reaction: float,
        location: ColumnLocation = ColumnLocation.INTERIOR,
        fcu: int = 35,
        rho_x: float = 0.5,
        rho_y: float = 0.5,
    ) -> PunchingShearResult:
        """
        Perform punching shear check per HK Code 2013.

        Args:
            column_size: Square column dimension (mm)
            slab_thickness: Slab thickness (mm)
            reaction: Column reaction / design shear force (kN)
            location: Column location (interior, edge, corner)
            fcu: Concrete cube strength (MPa)
            rho_x: Reinforcement ratio in x-direction (%)
            rho_y: Reinforcement ratio in y-direction (%)

        Returns:
            PunchingShearResult with all check outputs
        """
        self.calculations = []
        result = PunchingShearResult()

        self._add_calc_step(
            "PUNCHING SHEAR CHECK",
            f"Column: {column_size}×{column_size} mm\n"
            f"Slab: {slab_thickness} mm thick\n"
            f"Reaction: {reaction:.0f} kN\n"
            f"Location: {location.value}",
            "HK Code 2013 - Clause 6.1.5.6"
        )

        # Calculate effective depth
        cover = 30  # Assume 30mm cover for slab
        d = slab_thickness - cover - 12  # Assume T12 bars
        d_avg = d  # For square column, use average

        self._add_calc_step(
            "Calculate effective depth",
            f"d = {slab_thickness} - {cover} - 12 = {d} mm",
            "Effective depth to tension reinforcement"
        )

        # Calculate critical perimeter at 1.5d from column face
        u_0 = 4 * column_size  # Column perimeter
        u_1 = self._calculate_critical_perimeter(column_size, d, location)

        result.perimeter = u_1

        # Get beta factor for unbalanced moment
        beta = self._get_beta_factor(location)

        # Design shear stress
        V_Ed = beta * reaction
        v_Ed = (V_Ed * 1000) / (u_1 * d)

        result.V_Ed = V_Ed
        result.v_Ed = v_Ed

        self._add_calc_step(
            "Calculate design shear stress",
            f"β = {beta:.2f} (for {location.value} column)\n"
            f"V_Ed = β × V = {beta:.2f} × {reaction:.0f} = {V_Ed:.0f} kN\n"
            f"v_Ed = V_Ed / (u₁ × d) = {V_Ed * 1000:.0f} / ({u_1:.0f} × {d}) = {v_Ed:.3f} MPa",
            "HK Code 2013 - Clause 6.1.5.6"
        )

        # Calculate shear resistance
        v_Rd = self._calculate_shear_resistance(d, fcu, rho_x, rho_y)
        result.v_Rd = v_Rd

        # Calculate maximum shear stress
        v_max = min(SHEAR_STRESS_MAX_FACTOR * math.sqrt(fcu), SHEAR_STRESS_MAX_LIMIT)
        result.v_max = v_max

        self._add_calc_step(
            "Maximum shear stress limit",
            f"v_max = min(0.8√fcu, 7.0) = min(0.8×√{fcu}, 7.0) = {v_max:.2f} MPa",
            "HK Code 2013 - Clause 6.1.5.6"
        )

        # Check against v_max first (hard limit)
        if v_Ed > v_max:
            result.status = "FAIL"
            result.warnings.append(
                f"v_Ed = {v_Ed:.2f} MPa > v_max = {v_max:.2f} MPa - "
                "Section cannot be designed, increase slab thickness or column size"
            )
            result.utilization = v_Ed / v_max

            self._add_calc_step(
                "PUNCHING SHEAR FAILS - v_Ed > v_max",
                f"v_Ed = {v_Ed:.3f} MPa > v_max = {v_max:.2f} MPa\n"
                "Cannot design shear reinforcement - resize required",
                "HK Code 2013 - Clause 6.1.5.6"
            )

        elif v_Ed > v_Rd:
            # Shear reinforcement required
            result.shear_reinforcement_required = True
            result.utilization = v_Ed / v_Rd

            # Calculate required shear reinforcement
            A_sw = self._calculate_shear_reinforcement(v_Ed, v_Rd, u_1, d)
            result.shear_reinforcement_area = A_sw

            result.status = "OK (with shear reinforcement)"
            result.warnings.append(
                f"Punching shear reinforcement required: {A_sw:.0f} mm²"
            )

            self._add_calc_step(
                "Punching shear reinforcement required",
                f"v_Ed = {v_Ed:.3f} MPa > v_Rd = {v_Rd:.3f} MPa\n"
                f"v_Ed = {v_Ed:.3f} MPa ≤ v_max = {v_max:.2f} MPa (OK for reinforcement)\n"
                f"A_sw = {A_sw:.0f} mm² required",
                "HK Code 2013 - Clause 6.1.5.7"
            )

        else:
            # No shear reinforcement required
            result.utilization = v_Ed / v_Rd
            result.status = "OK"

            self._add_calc_step(
                "Punching shear check PASSES",
                f"v_Ed = {v_Ed:.3f} MPa ≤ v_Rd = {v_Rd:.3f} MPa\n"
                f"Utilization = {result.utilization:.2f}",
                "No shear reinforcement required"
            )

        result.calculations = self.calculations
        return result

    def _calculate_critical_perimeter(
        self, c: int, d: int, location: ColumnLocation
    ) -> float:
        """
        Calculate critical perimeter at 1.5d from column face.
        Adjusts for edge and corner columns.
        """
        # Distance to critical perimeter
        a = 1.5 * d

        if location == ColumnLocation.INTERIOR:
            # Full perimeter
            u_1 = 4 * c + 2 * math.pi * a
            formula = f"4×{c} + 2π×{a:.0f}"

        elif location == ColumnLocation.EDGE:
            # Three sides + semicircle
            u_1 = 3 * c + math.pi * a
            formula = f"3×{c} + π×{a:.0f}"

        else:  # Corner
            # Two sides + quarter circle
            u_1 = 2 * c + 0.5 * math.pi * a
            formula = f"2×{c} + 0.5π×{a:.0f}"

        self._add_calc_step(
            "Calculate critical perimeter at 1.5d",
            f"a = 1.5d = 1.5 × {d} = {a:.0f} mm\n"
            f"u₁ = {formula} = {u_1:.0f} mm",
            "HK Code 2013 - Clause 6.1.5.6"
        )

        return u_1

    def _get_beta_factor(self, location: ColumnLocation) -> float:
        """
        Get beta factor for unbalanced moment transfer.
        """
        if location == ColumnLocation.INTERIOR:
            beta = 1.15  # Typical for interior columns
        elif location == ColumnLocation.EDGE:
            beta = 1.4   # Edge columns
        else:  # Corner
            beta = 1.5   # Corner columns

        self._add_calc_step(
            "Beta factor for moment transfer",
            f"β = {beta} for {location.value} column",
            "HK Code 2013 - Clause 6.1.5.6 (simplified)"
        )

        return beta

    def _calculate_shear_resistance(
        self, d: int, fcu: int, rho_x: float, rho_y: float
    ) -> float:
        """
        Calculate design punching shear resistance v_Rd.
        Uses average reinforcement ratio.
        """
        # Average reinforcement ratio
        rho = math.sqrt(rho_x * rho_y) / 100  # Convert to decimal
        rho = min(rho, 0.02)  # Limited to 2%

        # Reinforcement factor
        rho_factor = min(100 * rho, 3.0)

        # Depth factor
        k = min(2.0, 1 + math.sqrt(200 / d))

        # Concrete strength factor (limited to 40 MPa)
        fcu_eff = min(fcu, 40)

        # v_Rd per HK Code (similar to Eurocode approach)
        v_Rd = 0.79 * (rho_factor ** (1/3)) * k * ((fcu_eff / 25) ** (1/3)) / 1.25

        self._add_calc_step(
            "Calculate shear resistance",
            f"ρ_avg = √({rho_x}% × {rho_y}%) = {rho * 100:.3f}%\n"
            f"k = 1 + √(200/{d}) = {k:.3f} (≤ 2.0)\n"
            f"v_Rd = 0.79 × {rho_factor:.3f}^(1/3) × {k:.3f} × ({fcu_eff}/25)^(1/3) / 1.25\n"
            f"v_Rd = {v_Rd:.3f} MPa",
            "HK Code 2013 - Clause 6.1.5.6"
        )

        return v_Rd

    def _calculate_shear_reinforcement(
        self, v_Ed: float, v_Rd: float, u_1: float, d: int
    ) -> float:
        """
        Calculate required punching shear reinforcement area.
        """
        # Shear to be carried by reinforcement
        v_s = v_Ed - 0.75 * v_Rd  # Allow 75% of concrete contribution

        # Required area
        # A_sw = (v_s × u₁ × d) / (0.87 × fyv × cot(θ))
        # Using cot(θ) ≈ 1.5 and fyv = 500 MPa for punching shear links

        fyv = 500  # High yield punching shear reinforcement
        A_sw = (v_s * u_1 * d) / (0.87 * fyv * 1.5)

        self._add_calc_step(
            "Calculate shear reinforcement",
            f"v_s = v_Ed - 0.75×v_Rd = {v_Ed:.3f} - 0.75×{v_Rd:.3f} = {v_s:.3f} MPa\n"
            f"A_sw = (v_s × u₁ × d) / (0.87 × fyv × 1.5)\n"
            f"A_sw = ({v_s:.3f} × {u_1:.0f} × {d}) / (0.87 × {fyv} × 1.5) = {A_sw:.0f} mm²",
            "HK Code 2013 - Clause 6.1.5.7"
        )

        return A_sw


def check_flat_slab_punching(project: ProjectData) -> PunchingShearResult:
    """
    Convenience function to check punching shear for a flat slab system.
    Uses project data to extract necessary parameters.
    """
    engine = PunchingShearEngine(project)

    # Get column size
    if project.column_result:
        column_size = project.column_result.dimension
        reaction = project.column_result.axial_load / project.geometry.floors
    else:
        column_size = 400  # Default
        reaction = 500     # Default estimate

    # Get slab thickness
    if project.slab_result:
        slab_thickness = project.slab_result.thickness
    else:
        slab_thickness = 200  # Default

    return engine.check_punching_shear(
        column_size=column_size,
        slab_thickness=slab_thickness,
        reaction=reaction,
        location=ColumnLocation.INTERIOR,
        fcu=project.materials.fcu_slab,
        rho_x=project.reinforcement.min_rho_slab,
        rho_y=project.reinforcement.min_rho_slab,
    )
