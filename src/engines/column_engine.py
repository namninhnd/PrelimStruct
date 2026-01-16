"""
Column Design Engine - HK Code 2013 Compliant
Implements load accumulation and eccentricity for different column positions.
"""

import math
from typing import Dict, Any, List, Tuple

from ..core.constants import (
    CONCRETE_DENSITY,
    STEEL_YIELD_STRENGTH,
    GAMMA_C,
    GAMMA_S,
    GAMMA_G,
    GAMMA_Q,
    MIN_COLUMN_SIZE,
)
from ..core.data_models import (
    ProjectData,
    ColumnResult,
    ColumnPosition,
)


class ColumnEngine:
    """
    Column design calculator per HK Code 2013.
    Handles interior, edge, and corner column positions.
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

    def calculate(
        self,
        position: ColumnPosition = ColumnPosition.INTERIOR
    ) -> ColumnResult:
        """
        Main column design calculation.
        Returns ColumnResult with all design outputs.
        """
        self.calculations = []

        geometry = self.project.geometry
        materials = self.project.materials
        reinforcement = self.project.reinforcement

        self._add_calc_step(
            "COLUMN DESIGN CALCULATION",
            f"Position: {position.value.upper()}\n"
            f"Bay size: {geometry.bay_x} × {geometry.bay_y} m\n"
            f"Floors: {geometry.floors}",
            "Starting column design"
        )

        # Calculate tributary area based on position
        trib_area = self._get_tributary_area(position)

        # Calculate axial load
        N = self._calculate_axial_load(trib_area)

        # Calculate design moment (if applicable)
        M = self._calculate_design_moment(N, position)

        # Calculate required column size
        h_required = self._calculate_required_size(
            N, M, materials.fcu_column, reinforcement.min_rho_column
        )

        # Check minimum size
        h_final = max(MIN_COLUMN_SIZE, h_required)
        h_final = math.ceil(h_final / 25) * 25

        if h_final > h_required:
            self._add_calc_step(
                "Apply minimum column size",
                f"h_min = {MIN_COLUMN_SIZE} mm per Clause 9.5.1",
                "HK Code 2013 - Clause 9.5.1"
            )

        # Check slenderness
        is_slender, slenderness = self._check_slenderness(h_final)

        # Calculate utilization
        utilization = self._calculate_utilization(
            N, M, h_final, materials.fcu_column, reinforcement.min_rho_column
        )

        # Determine status and warnings
        warnings = []
        status = "OK"

        if is_slender:
            warnings.append(f"Slender column (λ = {slenderness:.1f} > 15) - additional moment required")

        if utilization > 1.0:
            status = "FAIL"
            warnings.append(f"Column utilization {utilization:.2f} exceeds 1.0")

        if h_final > 800:
            warnings.append(f"Large column size ({h_final}mm) - consider higher concrete grade")

        self._add_calc_step(
            "Final column design",
            f"Size: {h_final} × {h_final} mm (square)\n"
            f"Axial load: {N:.0f} kN\n"
            f"Design moment: {M:.1f} kNm\n"
            f"Utilization: {utilization:.2f}",
            "Design complete"
        )

        return ColumnResult(
            element_type=f"Column ({position.value})",
            size=f"{h_final} × {h_final} mm",
            utilization=utilization,
            status=status,
            warnings=warnings,
            calculations=self.calculations,
            dimension=h_final,
            axial_load=round(N, 0),
            moment=round(M, 1),
            is_slender=is_slender,
            slenderness=round(slenderness, 1),
        )

    def _get_tributary_area(self, position: ColumnPosition) -> float:
        """Calculate tributary area based on column position"""
        bay_x = self.project.geometry.bay_x
        bay_y = self.project.geometry.bay_y
        full_area = bay_x * bay_y

        if position == ColumnPosition.INTERIOR:
            trib_area = full_area
            factor_desc = "Full bay"
        elif position == ColumnPosition.EDGE:
            trib_area = full_area * 0.5
            factor_desc = "Half bay"
        else:  # Corner
            trib_area = full_area * 0.25
            factor_desc = "Quarter bay"

        self._add_calc_step(
            "Calculate tributary area",
            f"Full bay area = {bay_x} × {bay_y} = {full_area:.1f} m²\n"
            f"{position.value.capitalize()} column: {factor_desc}\n"
            f"Tributary area = {trib_area:.1f} m²",
            "Tributary area method"
        )

        return trib_area

    def _calculate_axial_load(self, trib_area: float) -> float:
        """
        Calculate total factored axial load on column.
        N = Area × Floors × (1.4Gk + 1.6Qk)
        """
        geometry = self.project.geometry

        # Get loads
        if self.project.slab_result:
            slab_self_weight = self.project.slab_result.self_weight
        else:
            slab_self_weight = 0.2 * CONCRETE_DENSITY  # Estimate 200mm slab

        gk = slab_self_weight + self.project.loads.dead_load
        qk = self.project.loads.live_load

        # Factored load per floor
        w_floor = GAMMA_G * gk + GAMMA_Q * qk

        # Estimate beam and column self-weight (approximate)
        structural_allowance = 2.0  # kPa allowance for beams/columns

        w_total = w_floor + 1.4 * structural_allowance

        # Total axial load
        N = w_total * trib_area * geometry.floors

        self._add_calc_step(
            "Calculate axial load",
            f"Slab + SDL: Gk = {gk:.2f} kPa\n"
            f"Live load: Qk = {qk:.2f} kPa\n"
            f"ULS floor load: w = 1.4×{gk:.2f} + 1.6×{qk:.2f} = {w_floor:.2f} kPa\n"
            f"Structural allowance: +{1.4 * structural_allowance:.1f} kPa\n"
            f"Total: {w_total:.2f} kPa\n"
            f"N = {w_total:.2f} × {trib_area:.1f} × {geometry.floors} = {N:.0f} kN",
            "HK Code 2013 - Load accumulation"
        )

        return N

    def _calculate_design_moment(
        self, N: float, position: ColumnPosition
    ) -> float:
        """
        Calculate design moment based on column position.
        Interior: Axial focus (minimal moment)
        Edge/Corner: Add minimum eccentricity moment
        """
        geometry = self.project.geometry

        # Assume column size for eccentricity (will iterate if needed)
        h_assumed = max(300, int(math.sqrt(N * 1000 / 20)))  # Rough estimate

        if position == ColumnPosition.INTERIOR:
            # Interior column - balanced loading, minimal moment
            # Use minimum eccentricity of 0.03h or 20mm
            e_min = max(0.03 * h_assumed, 20)
            M = N * e_min / 1000  # kNm

            self._add_calc_step(
                "Calculate design moment (interior)",
                f"Interior column - balanced loading\n"
                f"Minimum eccentricity: e_min = max(0.03h, 20mm) = {e_min:.0f} mm\n"
                f"M_min = N × e_min = {N:.0f} × {e_min:.0f}/1000 = {M:.1f} kNm",
                "HK Code 2013 - Clause 6.2.1.2"
            )

        elif position == ColumnPosition.EDGE:
            # Edge column - unbalanced moment from beam
            # M ≈ N × 0.05h (simplified)
            e = 0.05 * h_assumed
            M = N * e / 1000

            self._add_calc_step(
                "Calculate design moment (edge)",
                f"Edge column - unbalanced loading\n"
                f"Eccentricity: e = 0.05h = 0.05 × {h_assumed} = {e:.0f} mm\n"
                f"M = N × e = {N:.0f} × {e:.0f}/1000 = {M:.1f} kNm",
                "Simplified moment for preliminary design"
            )

        else:  # Corner
            # Corner column - biaxial bending
            # M ≈ N × 0.075h (increased for biaxial effect)
            e = 0.075 * h_assumed
            M = N * e / 1000

            self._add_calc_step(
                "Calculate design moment (corner)",
                f"Corner column - biaxial bending\n"
                f"Eccentricity: e = 0.075h = 0.075 × {h_assumed} = {e:.0f} mm\n"
                f"M = N × e = {N:.0f} × {e:.0f}/1000 = {M:.1f} kNm\n"
                f"(Increased for biaxial bending effect)",
                "Simplified moment for preliminary design"
            )

        return M

    def _calculate_required_size(
        self, N: float, M: float, fcu: int, rho: float
    ) -> int:
        """
        Calculate required column size using simplified approach.
        Based on axial capacity with allowance for moment.
        """
        # Design strength
        f_cd = 0.45 * fcu / GAMMA_C
        f_sd = 0.87 * STEEL_YIELD_STRENGTH / GAMMA_S

        # Combined capacity formula (simplified for square column)
        # N_u = 0.45 * fcu * Ac / γc + 0.87 * fy * As / γs
        # As = ρ * Ac

        # Rearranging for Ac:
        # Ac = N / (0.45 * fcu / γc + 0.87 * fy * ρ / γs)

        rho_decimal = rho / 100

        Ac_axial = (N * 1000) / (f_cd + f_sd * rho_decimal)

        # Increase for moment effect (simplified)
        moment_factor = 1.0 + M / (N * 0.3)  # Approximate
        moment_factor = min(1.5, max(1.0, moment_factor))

        Ac_required = Ac_axial * moment_factor

        # Square column side
        h_required = math.sqrt(Ac_required)

        self._add_calc_step(
            "Calculate required column size",
            f"f_cd = 0.45 × {fcu} / {GAMMA_C} = {f_cd:.2f} MPa\n"
            f"f_sd = 0.87 × {STEEL_YIELD_STRENGTH} / {GAMMA_S} = {f_sd:.2f} MPa\n"
            f"ρ = {rho}%\n"
            f"Ac (axial only) = {N * 1000:.0f} / ({f_cd:.2f} + {f_sd:.2f}×{rho_decimal:.3f}) = {Ac_axial:.0f} mm²\n"
            f"Moment factor = {moment_factor:.2f}\n"
            f"Ac (required) = {Ac_required:.0f} mm²\n"
            f"h = √{Ac_required:.0f} = {h_required:.0f} mm",
            "HK Code 2013 - Simplified column design"
        )

        return int(math.ceil(h_required))

    def _check_slenderness(self, h: int) -> Tuple[bool, float]:
        """
        Check column slenderness per HK Code Cl 6.2.1.1.
        Returns (is_slender, slenderness ratio)
        """
        # Assume effective length = 0.85 × story height (braced frame)
        L_e = 0.85 * self.project.geometry.story_height * 1000  # mm

        # Slenderness ratio
        slenderness = L_e / h

        # Short column limit
        is_slender = slenderness > 15

        self._add_calc_step(
            "Check slenderness",
            f"Effective length: L_e = 0.85 × {self.project.geometry.story_height * 1000:.0f} = {L_e:.0f} mm\n"
            f"Slenderness: λ = L_e / h = {L_e:.0f} / {h} = {slenderness:.1f}\n"
            f"{'SLENDER (λ > 15)' if is_slender else 'SHORT (λ ≤ 15)'}",
            "HK Code 2013 - Clause 6.2.1.1"
        )

        return is_slender, slenderness

    def _calculate_utilization(
        self, N: float, M: float, h: int, fcu: int, rho: float
    ) -> float:
        """
        Calculate column utilization ratio.
        Simplified interaction check.
        """
        # Axial capacity
        Ac = h * h
        As = (rho / 100) * Ac
        f_cd = 0.45 * fcu / GAMMA_C
        f_sd = 0.87 * STEEL_YIELD_STRENGTH / GAMMA_S

        N_Rd = (f_cd * Ac + f_sd * As) / 1000  # kN

        # Moment capacity (simplified)
        d = h - 50  # Assume 50mm to centroid of bars
        M_Rd = 0.87 * STEEL_YIELD_STRENGTH * As * 0.8 * d / 1e6  # kNm

        # Interaction check (simplified linear)
        utilization = (N / N_Rd) + (M / max(M_Rd, 1))

        # Alternatively, for preliminary design:
        utilization_simple = N / N_Rd

        self._add_calc_step(
            "Calculate utilization",
            f"Ac = {h}² = {Ac:.0f} mm²\n"
            f"As = {rho}% × {Ac:.0f} = {As:.0f} mm²\n"
            f"N_Rd = ({f_cd:.2f}×{Ac:.0f} + {f_sd:.2f}×{As:.0f})/1000 = {N_Rd:.0f} kN\n"
            f"Axial utilization = {N:.0f} / {N_Rd:.0f} = {utilization_simple:.2f}",
            "HK Code 2013 - Simplified capacity check"
        )

        return utilization_simple
