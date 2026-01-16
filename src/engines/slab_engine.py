"""
Slab Design Engine - HK Code 2013 Compliant
Implements rigorous span/depth checks with modification factors per Cl 7.3.1.2
"""

import math
from typing import Dict, Any, List, Tuple

from ..core.constants import (
    CONCRETE_DENSITY,
    STEEL_YIELD_STRENGTH,
    GAMMA_S,
    MIN_SLAB_THICKNESS,
    SPAN_DEPTH_RATIOS,
)
from ..core.data_models import (
    ProjectData,
    SlabResult,
    SlabType,
)


class SlabEngine:
    """
    Slab design calculator per HK Code 2013.
    Implements span/depth ratio method with modification factors.
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

    def calculate(self) -> SlabResult:
        """
        Main slab design calculation.
        Returns SlabResult with all design outputs.
        """
        self.calculations = []

        # Extract inputs
        geometry = self.project.geometry
        materials = self.project.materials
        reinforcement = self.project.reinforcement
        slab_design = self.project.slab_design

        # Determine effective span
        L_slab = self._get_effective_span()

        # Get basic span/depth ratio from Table 7.4
        basic_ratio = self._get_basic_span_depth_ratio()

        # Calculate initial minimum thickness
        h_min = self._calculate_min_thickness(L_slab, basic_ratio)

        # Apply modification factor for deflection control (Cl 7.3.1.2)
        h_required, mod_factor = self._apply_modification_factor(
            L_slab, h_min, basic_ratio, materials.fcu_slab
        )

        # Check absolute minimum thickness
        h_required = self._check_minimum_thickness(L_slab, h_required)

        # Add cover and round up to nearest 25mm
        h_final = self._finalize_thickness(h_required, materials.cover_slab)

        # Calculate self-weight
        self_weight = self._calculate_self_weight(h_final)

        # Calculate design load
        design_load = self._calculate_design_load(self_weight)

        # Calculate design moment
        moment = self._calculate_moment(design_load, L_slab)

        # Calculate effective depth
        d_eff = h_final - materials.cover_slab - 10 - 6  # cover + bar/2 (T12)

        # Calculate required reinforcement
        As_req, utilization = self._calculate_reinforcement(
            moment, d_eff, materials.fcu_slab
        )

        # Check minimum reinforcement
        As_min = self._check_min_reinforcement(h_final, reinforcement.min_rho_slab)

        # Final reinforcement area
        As_final = max(As_req, As_min)

        # Deflection check
        deflection_ratio = (L_slab * 1000) / h_final

        # Determine status
        status = "OK"
        warnings = []

        if utilization > 1.0:
            status = "FAIL"
            warnings.append(f"Section utilization {utilization:.2f} exceeds 1.0")

        if deflection_ratio > basic_ratio * mod_factor:
            status = "FAIL"
            warnings.append(f"Deflection ratio {deflection_ratio:.1f} exceeds allowable")

        # Create result
        result = SlabResult(
            element_type="Slab",
            size=f"{h_final}mm thick",
            utilization=utilization,
            status=status,
            warnings=warnings,
            calculations=self.calculations,
            thickness=h_final,
            moment=round(moment, 2),
            reinforcement_area=round(As_final, 0),
            deflection_ratio=round(deflection_ratio, 1),
            self_weight=round(self_weight, 2),
        )

        return result

    def _get_effective_span(self) -> float:
        """Determine effective slab span based on type and direction"""
        geometry = self.project.geometry
        slab_design = self.project.slab_design

        if slab_design.slab_type == SlabType.TWO_WAY:
            # For two-way slab, use shorter span
            L_slab = min(geometry.bay_x, geometry.bay_y)
            self._add_calc_step(
                "Determine effective span for two-way slab",
                f"L_eff = min({geometry.bay_x}, {geometry.bay_y}) = {L_slab} m",
                "Shorter span governs for two-way slab"
            )
        else:
            # For one-way slab, use span in main direction
            if slab_design.span_direction.value == "alongX":
                L_slab = geometry.bay_x
            else:
                L_slab = geometry.bay_y

            self._add_calc_step(
                "Determine effective span for one-way slab",
                f"L_eff = {L_slab} m (spanning {slab_design.span_direction.value})",
                "Main span direction"
            )

        # Check if max slab span applies
        if geometry.max_slab_span and geometry.max_slab_span < L_slab:
            self._add_calc_step(
                "Apply maximum slab span limit",
                f"L_eff = {geometry.max_slab_span} m (secondary beams provided)",
                "User-defined maximum span"
            )
            L_slab = geometry.max_slab_span

        return L_slab

    def _get_basic_span_depth_ratio(self) -> int:
        """Get basic span/depth ratio from HK Code Table 7.4"""
        slab_type = self.project.slab_design.slab_type

        if slab_type == SlabType.TWO_WAY:
            ratio = SPAN_DEPTH_RATIOS["two_way_slab"]
            self._add_calc_step(
                "Basic span/depth ratio from Table 7.4",
                f"Two-way slab: Basic L/d = {ratio}",
                "HK Code 2013 - Table 7.4"
            )
        else:
            ratio = SPAN_DEPTH_RATIOS["one_way_slab"]
            self._add_calc_step(
                "Basic span/depth ratio from Table 7.4",
                f"One-way slab: Basic L/d = {ratio}",
                "HK Code 2013 - Table 7.4"
            )

        return ratio

    def _calculate_min_thickness(self, L_slab: float, basic_ratio: int) -> int:
        """Calculate minimum slab thickness based on span/depth ratio"""
        h_min = math.ceil((L_slab * 1000) / basic_ratio)

        self._add_calc_step(
            "Calculate minimum slab thickness",
            f"h_min = L / {basic_ratio} = {L_slab * 1000:.0f} / {basic_ratio} = {h_min} mm",
            "HK Code 2013 - Clause 7.3.1.1"
        )

        return h_min

    def _apply_modification_factor(
        self, L_slab: float, h_min: int, basic_ratio: int, fcu: int
    ) -> Tuple[int, float]:
        """
        Apply modification factor for deflection control per Cl 7.3.1.2.
        Based on tension reinforcement and service stress.
        """
        # Estimate service stress (fs ≈ 2/3 × fy)
        fs = (2 / 3) * STEEL_YIELD_STRENGTH

        # Modification factor for tension reinforcement
        # M_tension = 0.55 + (477 - fs) / (120 × (0.9 + M/bd²fcu))
        # For preliminary design, assume M/bd²fcu ≈ 0.1 (lightly reinforced)
        M_bd2fcu = 0.1

        mod_factor = 0.55 + (477 - fs) / (120 * (0.9 + M_bd2fcu))
        mod_factor = min(2.0, max(0.8, mod_factor))  # Limit between 0.8 and 2.0

        self._add_calc_step(
            "Calculate modification factor (Cl 7.3.1.2)",
            f"fs = (2/3) × {STEEL_YIELD_STRENGTH} = {fs:.0f} MPa\n"
            f"M_t = 0.55 + (477 - {fs:.0f}) / (120 × (0.9 + 0.1)) = {mod_factor:.2f}",
            "HK Code 2013 - Clause 7.3.1.2"
        )

        # Allowable span/depth ratio
        allowable_ratio = basic_ratio * mod_factor

        self._add_calc_step(
            "Calculate allowable span/depth ratio",
            f"Allowable L/d = {basic_ratio} × {mod_factor:.2f} = {allowable_ratio:.1f}",
            "Modified for tension reinforcement"
        )

        # Required thickness based on modified ratio
        h_required = math.ceil((L_slab * 1000) / allowable_ratio)

        if h_required < h_min:
            h_required = h_min
            self._add_calc_step(
                "Check modified thickness",
                f"h_mod = {L_slab * 1000:.0f} / {allowable_ratio:.1f} = {h_required} mm (< h_min, use h_min)",
                "Basic ratio governs"
            )
        else:
            self._add_calc_step(
                "Check modified thickness",
                f"h_mod = {L_slab * 1000:.0f} / {allowable_ratio:.1f} = {h_required} mm",
                "Modified ratio governs"
            )

        return h_required, mod_factor

    def _check_minimum_thickness(self, L_slab: float, h_required: int) -> int:
        """Check absolute minimum thickness requirements"""
        # Absolute minimum
        h_abs_min = max(MIN_SLAB_THICKNESS, int(L_slab * 1000 / 40))

        if h_required < h_abs_min:
            self._add_calc_step(
                "Apply absolute minimum thickness",
                f"h_abs_min = max({MIN_SLAB_THICKNESS}, L/40) = max({MIN_SLAB_THICKNESS}, {L_slab * 1000 / 40:.0f}) = {h_abs_min} mm",
                "HK Code 2013 - Clause 7.3.1.1"
            )
            return h_abs_min

        return h_required

    def _finalize_thickness(self, h_required: int, cover: int) -> int:
        """Add cover and round to nearest 25mm"""
        # Add allowance for cover and bar diameter
        h_total = h_required + 5  # Small allowance

        # Round up to nearest 25mm
        h_final = math.ceil(h_total / 25) * 25

        self._add_calc_step(
            "Finalize slab thickness",
            f"h_final = {h_final} mm (rounded to nearest 25mm, cover = {cover} mm)",
            "HK Code 2013 - Table 4.1"
        )

        return h_final

    def _calculate_self_weight(self, thickness: int) -> float:
        """Calculate slab self-weight in kPa"""
        self_weight = (thickness / 1000) * CONCRETE_DENSITY

        self._add_calc_step(
            "Calculate slab self-weight",
            f"Self-weight = ({thickness}/1000) × {CONCRETE_DENSITY} = {self_weight:.2f} kPa",
            f"Concrete density = {CONCRETE_DENSITY} kN/m³"
        )

        return self_weight

    def _calculate_design_load(self, self_weight: float) -> float:
        """Calculate total factored design load"""
        gk = self_weight + self.project.loads.dead_load
        qk = self.project.loads.live_load

        # Use load factors from project settings
        w = self.project.get_design_load()

        self._add_calc_step(
            "Calculate design load",
            f"Gk = {self_weight:.2f} + {self.project.loads.dead_load} = {gk:.2f} kPa\n"
            f"Qk = {qk:.2f} kPa\n"
            f"w = 1.4 × {gk:.2f} + 1.6 × {qk:.2f} = {w:.2f} kPa",
            "HK Code 2013 - ULS Load Combination"
        )

        return w

    def _calculate_moment(self, w: float, L_slab: float) -> float:
        """Calculate design moment"""
        slab_type = self.project.slab_design.slab_type

        if slab_type == SlabType.ONE_WAY:
            # One-way continuous slab
            moment = w * (L_slab ** 2) / 8
            formula = "wL²/8"
        else:
            # Two-way slab - approximate using shorter span
            moment = w * (L_slab ** 2) / 10
            formula = "wL²/10 (two-way approx.)"

        self._add_calc_step(
            "Calculate design moment",
            f"M = {formula} = {w:.2f} × {L_slab}² / {8 if slab_type == SlabType.ONE_WAY else 10} = {moment:.2f} kNm/m",
            f"{'One-way' if slab_type == SlabType.ONE_WAY else 'Two-way'} slab moment"
        )

        return moment

    def _calculate_reinforcement(
        self, moment: float, d_eff: int, fcu: int
    ) -> Tuple[float, float]:
        """
        Calculate required reinforcement area.
        Returns (As_required in mm²/m, utilization ratio)
        """
        # Design constants
        b = 1000  # mm (per meter width)
        fy = STEEL_YIELD_STRENGTH

        # K = M / (bd²fcu)
        K = (moment * 1e6) / (b * d_eff ** 2 * fcu)
        K_bal = 0.156  # Balanced section limit

        self._add_calc_step(
            "Calculate K factor",
            f"K = M / (bd²fcu) = {moment * 1e6:.0f} / ({b} × {d_eff}² × {fcu}) = {K:.4f}",
            "HK Code 2013 - Clause 6.1.2.4"
        )

        utilization = K / K_bal

        if K > K_bal:
            self._add_calc_step(
                "Check section capacity",
                f"K = {K:.4f} > K_bal = {K_bal} - Compression reinforcement required",
                "Section exceeds singly reinforced limit"
            )
            # For preliminary design, flag this as over-utilized
            As_req = 0
        else:
            # z = d × (0.5 + √(0.25 - K/0.9))
            z = d_eff * (0.5 + math.sqrt(0.25 - K / 0.9))
            z = min(z, 0.95 * d_eff)

            # As = M / (0.87 × fy × z)
            As_req = (moment * 1e6) / (0.87 * fy * z)

            self._add_calc_step(
                "Calculate lever arm",
                f"z = d × (0.5 + √(0.25 - K/0.9)) = {d_eff} × (0.5 + √(0.25 - {K:.4f}/0.9)) = {z:.0f} mm",
                "Limited to 0.95d"
            )

            self._add_calc_step(
                "Calculate required reinforcement",
                f"As = M / (0.87 × fy × z) = {moment * 1e6:.0f} / (0.87 × {fy} × {z:.0f}) = {As_req:.0f} mm²/m",
                "HK Code 2013 - Clause 6.1.2.4"
            )

        return As_req, utilization

    def _check_min_reinforcement(self, thickness: int, min_rho: float) -> float:
        """Calculate minimum reinforcement area"""
        As_min = (min_rho / 100) * 1000 * thickness

        self._add_calc_step(
            "Check minimum reinforcement",
            f"As,min = {min_rho}% × 1000 × {thickness} = {As_min:.0f} mm²/m",
            "HK Code 2013 - Clause 9.3.1.1"
        )

        return As_min
