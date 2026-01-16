"""
Beam Design Engine - HK Code 2013 Compliant
Implements pattern loading, shear hard-stop, and deep beam detection.
"""

import math
from typing import Dict, Any, List, Tuple, Optional

from ..core.constants import (
    CONCRETE_DENSITY,
    STEEL_YIELD_STRENGTH,
    LINK_YIELD_STRENGTH,
    GAMMA_C,
    GAMMA_S,
    PATTERN_LOAD_FACTOR,
    MIN_BEAM_WIDTH,
    MIN_BEAM_DEPTH,
    MAX_BEAM_DEPTH,
    MAX_BEAM_WIDTH,
    DEEP_BEAM_RATIO,
    SHEAR_STRESS_MAX_FACTOR,
    SHEAR_STRESS_MAX_LIMIT,
)
from ..core.data_models import (
    ProjectData,
    BeamResult,
)


class BeamEngine:
    """
    Beam design calculator per HK Code 2013.
    Includes pattern loading factor and shear capacity checks.
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

    def calculate_primary_beam(self, tributary_width: float) -> BeamResult:
        """
        Design primary (main) beam.
        Spans in the longer direction, supporting secondary beams or slabs.
        """
        self.calculations = []
        geometry = self.project.geometry

        # Primary beam spans the longer direction
        L_beam = max(geometry.bay_x, geometry.bay_y)

        self._add_calc_step(
            "PRIMARY BEAM DESIGN",
            f"Span = {L_beam} m, Tributary width = {tributary_width} m",
            "Main girder spanning longer direction"
        )

        return self._design_beam(L_beam, tributary_width, "Primary")

    def calculate_secondary_beam(self, tributary_width: float) -> BeamResult:
        """
        Design secondary beam.
        Spans in the shorter direction, supporting slab directly.
        """
        self.calculations = []
        geometry = self.project.geometry

        # Secondary beam spans the shorter direction
        L_beam = min(geometry.bay_x, geometry.bay_y)

        self._add_calc_step(
            "SECONDARY BEAM DESIGN",
            f"Span = {L_beam} m, Tributary width = {tributary_width} m",
            "Secondary beam spanning shorter direction"
        )

        return self._design_beam(L_beam, tributary_width, "Secondary")

    def _design_beam(
        self, L_beam: float, tributary_width: float, beam_type: str
    ) -> BeamResult:
        """
        Core beam design logic.
        Implements iterative sizing with shear checks.
        """
        materials = self.project.materials
        reinforcement = self.project.reinforcement

        # Get slab load
        slab_load = self._get_slab_load()

        # Calculate line load on beam
        line_load = slab_load * tributary_width

        self._add_calc_step(
            "Calculate beam line load",
            f"w_slab = {slab_load:.2f} kPa\n"
            f"w_beam = {slab_load:.2f} × {tributary_width} = {line_load:.2f} kN/m",
            "UDL from slab on beam"
        )

        # Check for deep beam before proceeding
        is_deep_beam, _ = self._check_deep_beam(L_beam, MIN_BEAM_DEPTH)

        if is_deep_beam:
            return self._create_deep_beam_result(L_beam, beam_type)

        # Calculate maximum allowable shear stress
        v_max = self._get_max_shear_stress(materials.fcu_beam)

        # Initial beam sizing based on span/depth ratio
        h_initial = max(MIN_BEAM_DEPTH, math.ceil((L_beam * 1000) / 18))
        b_initial = max(MIN_BEAM_WIDTH, math.ceil(h_initial / 2 / 25) * 25)

        self._add_calc_step(
            "Initial beam sizing (L/d = 18)",
            f"h_initial = max({MIN_BEAM_DEPTH}, {L_beam * 1000:.0f}/18) = {h_initial} mm\n"
            f"b_initial = max({MIN_BEAM_WIDTH}, h/2) = {b_initial} mm",
            "HK Code 2013 - Table 7.4"
        )

        # Iterative sizing loop
        result = self._iterate_beam_size(
            L_beam, line_load, b_initial, h_initial,
            materials.fcu_beam, materials.cover_beam,
            reinforcement.min_rho_beam, reinforcement.max_rho_beam,
            v_max, beam_type
        )

        return result

    def _get_slab_load(self) -> float:
        """Get design load from slab (or estimate if not calculated yet)"""
        if self.project.slab_result:
            slab_self_weight = self.project.slab_result.self_weight
        else:
            # Estimate 200mm slab
            slab_self_weight = 0.2 * CONCRETE_DENSITY

        gk = slab_self_weight + self.project.loads.dead_load
        qk = self.project.loads.live_load

        # ULS factored load
        return 1.4 * gk + 1.6 * qk

    def _get_max_shear_stress(self, fcu: int) -> float:
        """Calculate maximum allowable shear stress (v_max)"""
        v_max = min(SHEAR_STRESS_MAX_FACTOR * math.sqrt(fcu), SHEAR_STRESS_MAX_LIMIT)

        self._add_calc_step(
            "Calculate maximum shear stress limit",
            f"v_max = min(0.8√fcu, 7.0) = min(0.8×√{fcu}, 7.0) = {v_max:.2f} MPa",
            "HK Code 2013 - Clause 6.1.2.4"
        )

        return v_max

    def _check_deep_beam(self, L_beam: float, h_beam: int) -> Tuple[bool, float]:
        """Check if beam qualifies as deep beam (L/d < 2.0)"""
        ratio = (L_beam * 1000) / h_beam
        is_deep = ratio < DEEP_BEAM_RATIO

        return is_deep, ratio

    def _create_deep_beam_result(self, L_beam: float, beam_type: str) -> BeamResult:
        """Create result for deep beam case (requires STM analysis)"""
        self._add_calc_step(
            "DEEP BEAM DETECTED",
            f"L/d ratio < {DEEP_BEAM_RATIO} - Strut-and-Tie Model (STM) required",
            "HK Code 2013 - Clause 6.7"
        )

        return BeamResult(
            element_type=f"{beam_type} Beam",
            size="DEEP BEAM - STM Required",
            utilization=0.0,
            status="DEEP BEAM",
            warnings=["Deep beam detected - standard beam theory not applicable",
                     "Strut-and-Tie Model (STM) analysis required"],
            calculations=self.calculations,
            is_deep_beam=True,
        )

    def _iterate_beam_size(
        self,
        L_beam: float,
        line_load: float,
        b_initial: int,
        h_initial: int,
        fcu: int,
        cover: int,
        min_rho: float,
        max_rho: float,
        v_max: float,
        beam_type: str
    ) -> BeamResult:
        """
        Iteratively size beam to satisfy shear requirements.
        Implements shear "hard stop" check.
        """
        b = b_initial
        h = h_initial
        iteration = 0
        max_iterations = 15
        shear_ok = False
        max_size_reached = False
        shear_reinf_required = False
        shear_reinf_area = 0.0
        link_spacing = 0

        while not shear_ok and iteration < max_iterations and not max_size_reached:
            iteration += 1

            # Calculate beam self-weight
            self_weight = (b / 1000) * (h / 1000) * CONCRETE_DENSITY

            # Total load including self-weight
            total_load = line_load + self_weight

            # Apply pattern loading factor (1.1x) for moment
            moment = PATTERN_LOAD_FACTOR * total_load * (L_beam ** 2) / 8

            # Shear at support
            shear = total_load * L_beam / 2

            # Effective depth
            d_eff = h - cover - 10 - 16  # cover + link + bar/2 (T32)
            d_eff = max(d_eff, 250)

            # Check deep beam condition
            is_deep, ld_ratio = self._check_deep_beam(L_beam, h)
            if is_deep:
                return self._create_deep_beam_result(L_beam, beam_type)

            # === SHEAR "HARD STOP" CHECK ===
            v_actual = (shear * 1000) / (b * d_eff)

            if v_actual > v_max:
                # Hard stop - section cannot be designed with links
                self._add_calc_step(
                    f"Iteration {iteration}: SHEAR HARD STOP",
                    f"v = V/(bd) = {shear * 1000:.0f}/({b}×{d_eff}) = {v_actual:.2f} MPa\n"
                    f"v_max = {v_max:.2f} MPa\n"
                    f"v > v_max - RESIZE REQUIRED",
                    "HK Code 2013 - Clause 6.1.2.4 - Cannot design shear links"
                )

                # Must increase section size
                if h < MAX_BEAM_DEPTH:
                    h = min(MAX_BEAM_DEPTH, h + 100)
                if b < MAX_BEAM_WIDTH and h >= MAX_BEAM_DEPTH:
                    b = min(MAX_BEAM_WIDTH, b + 50)

                h = math.ceil(h / 25) * 25
                b = math.ceil(b / 25) * 25

                if h >= MAX_BEAM_DEPTH and b >= MAX_BEAM_WIDTH:
                    max_size_reached = True
                    self._add_calc_step(
                        "Maximum beam size reached",
                        f"Max size {b}×{h}mm still exceeds v_max",
                        "Consider deeper beam or transfer structure"
                    )

                continue

            # === CONCRETE SHEAR CAPACITY CHECK ===
            v_c, V_capacity = self._calculate_shear_capacity(
                b, d_eff, fcu, min_rho
            )

            if shear > V_capacity:
                # Check if shear reinforcement can make up the difference
                if v_actual <= v_max:
                    # Can use shear reinforcement
                    shear_reinf_required = True
                    V_s = shear - V_capacity
                    shear_reinf_area, link_spacing = self._design_shear_reinforcement(
                        V_s, d_eff, b
                    )
                    shear_ok = True

                    self._add_calc_step(
                        f"Iteration {iteration}: Shear reinforcement required",
                        f"V = {shear:.1f} kN > V_c = {V_capacity:.1f} kN\n"
                        f"v = {v_actual:.2f} MPa ≤ v_max = {v_max:.2f} MPa (OK for links)",
                        "HK Code 2013 - Clause 6.1.2.5"
                    )
                else:
                    # Increase size
                    h = min(MAX_BEAM_DEPTH, h + 75)
                    if h / b > 3:
                        b = min(MAX_BEAM_WIDTH, b + 25)
                    h = math.ceil(h / 25) * 25
                    b = math.ceil(b / 25) * 25

                    if h >= MAX_BEAM_DEPTH and b >= MAX_BEAM_WIDTH:
                        max_size_reached = True
            else:
                shear_ok = True
                shear_ratio = shear / V_capacity

                self._add_calc_step(
                    f"Iteration {iteration}: Shear capacity adequate",
                    f"Size: {b}×{h}mm\n"
                    f"V = {shear:.1f} kN ≤ V_c = {V_capacity:.1f} kN\n"
                    f"Utilization = {shear_ratio:.2f}",
                    "HK Code 2013 - Clause 6.1.2.4"
                )

                # Check if nominal shear reinforcement needed
                if shear > 0.5 * V_capacity:
                    shear_reinf_required = True
                    shear_reinf_area, link_spacing = self._design_min_shear_reinforcement(
                        b, d_eff
                    )

        # Final calculations
        self_weight = (b / 1000) * (h / 1000) * CONCRETE_DENSITY
        total_load = line_load + self_weight
        moment = PATTERN_LOAD_FACTOR * total_load * (L_beam ** 2) / 8
        shear = total_load * L_beam / 2
        d_eff = h - cover - 10 - 16

        # Calculate flexural reinforcement
        As_req, flex_utilization = self._calculate_flexural_reinforcement(
            moment, b, d_eff, fcu
        )

        # Final result
        self._add_calc_step(
            "Final beam design",
            f"Size: {b} × {h} mm\n"
            f"Moment: {moment:.2f} kNm (with {PATTERN_LOAD_FACTOR}× pattern factor)\n"
            f"Shear: {shear:.2f} kN",
            "Design complete"
        )

        # Determine status
        warnings = []
        status = "OK"

        if max_size_reached and not shear_ok:
            status = "FAIL"
            warnings.append("Maximum beam size reached - shear capacity exceeded")
            warnings.append("Consider deeper beam, transfer structure, or reduced span")

        if flex_utilization > 1.0:
            status = "FAIL"
            warnings.append(f"Flexural utilization {flex_utilization:.2f} exceeds 1.0")

        _, V_capacity = self._calculate_shear_capacity(b, d_eff, fcu, min_rho)

        return BeamResult(
            element_type=f"{beam_type} Beam",
            size=f"{b} × {h} mm",
            utilization=max(flex_utilization, shear / V_capacity if V_capacity > 0 else 0),
            status=status,
            warnings=warnings,
            calculations=self.calculations,
            width=b,
            depth=h,
            moment=round(moment, 2),
            shear=round(shear, 2),
            shear_capacity=round(V_capacity, 2),
            shear_reinforcement_required=shear_reinf_required,
            shear_reinforcement_area=round(shear_reinf_area, 1),
            link_spacing=link_spacing,
            is_deep_beam=False,
            iteration_count=iteration,
        )

    def _calculate_shear_capacity(
        self, b: int, d: int, fcu: int, rho: float
    ) -> Tuple[float, float]:
        """
        Calculate concrete shear capacity per HK Code Cl 6.1.2.4.
        Returns (v_c in MPa, V_c in kN)
        """
        # Reinforcement ratio factor (limited to 3%)
        rho_factor = min(100 * (rho / 100), 3.0)

        # Depth factor
        depth_factor = (400 / max(d, 250)) ** 0.25

        # Concrete strength factor (limited to 40 MPa)
        fcu_factor = (min(fcu, 40) / 25) ** (1/3)

        # v_c per Clause 6.1.2.4
        v_c = 0.79 * (rho_factor ** (1/3)) * depth_factor * fcu_factor / 1.25

        # Shear capacity in kN
        V_c = v_c * b * d / 1000

        self._add_calc_step(
            "Calculate concrete shear capacity",
            f"ρ factor = min(100×{rho/100:.4f}, 3.0) = {rho_factor:.3f}\n"
            f"Depth factor = (400/{d})^0.25 = {depth_factor:.3f}\n"
            f"fcu factor = ({min(fcu, 40)}/25)^(1/3) = {fcu_factor:.3f}\n"
            f"v_c = 0.79 × {rho_factor:.3f}^(1/3) × {depth_factor:.3f} × {fcu_factor:.3f} / 1.25 = {v_c:.3f} MPa\n"
            f"V_c = {v_c:.3f} × {b} × {d} / 1000 = {V_c:.1f} kN",
            "HK Code 2013 - Clause 6.1.2.4"
        )

        return v_c, V_c

    def _design_shear_reinforcement(
        self, V_s: float, d: int, b: int
    ) -> Tuple[float, int]:
        """
        Design shear reinforcement for additional shear V_s.
        Returns (A_sv/s in mm²/m, practical link spacing in mm)
        """
        # A_sv/s = V_s × 10³ / (0.87 × f_yv × d)
        A_sv_s = (V_s * 1000) / (0.87 * LINK_YIELD_STRENGTH * d)

        # Minimum shear reinforcement
        A_sv_min = (0.4 * b) / (0.87 * LINK_YIELD_STRENGTH)

        A_sv_s = max(A_sv_s, A_sv_min)

        # Calculate practical link spacing (T10 2-leg links)
        link_dia = 10
        area_per_link = math.pi * (link_dia / 2) ** 2 * 2  # 2 legs
        required_spacing = (area_per_link * 1000) / A_sv_s

        # Apply spacing limits
        max_spacing = min(int(0.75 * d), 300)
        min_spacing = 100
        link_spacing = min(max_spacing, max(min_spacing, int(required_spacing / 25) * 25))

        self._add_calc_step(
            "Design shear reinforcement",
            f"V_s = {V_s:.1f} kN\n"
            f"A_sv/s = V_s × 10³ / (0.87 × {LINK_YIELD_STRENGTH} × {d}) = {A_sv_s:.1f} mm²/m\n"
            f"Provide T{link_dia} links @ {link_spacing}mm c/c (2 legs)",
            "HK Code 2013 - Clause 6.1.2.5"
        )

        return A_sv_s, link_spacing

    def _design_min_shear_reinforcement(
        self, b: int, d: int
    ) -> Tuple[float, int]:
        """Design minimum/nominal shear reinforcement"""
        A_sv_min = (0.4 * b) / (0.87 * LINK_YIELD_STRENGTH)

        # T10 2-leg links
        link_dia = 10
        area_per_link = math.pi * (link_dia / 2) ** 2 * 2
        required_spacing = (area_per_link * 1000) / A_sv_min

        max_spacing = min(int(0.75 * d), 300)
        link_spacing = min(max_spacing, max(100, int(required_spacing / 25) * 25))

        self._add_calc_step(
            "Design minimum shear reinforcement",
            f"A_sv,min = 0.4 × {b} / (0.87 × {LINK_YIELD_STRENGTH}) = {A_sv_min:.1f} mm²/m\n"
            f"Provide T{link_dia} links @ {link_spacing}mm c/c",
            "HK Code 2013 - Clause 6.1.2.5"
        )

        return A_sv_min, link_spacing

    def _calculate_flexural_reinforcement(
        self, moment: float, b: int, d: int, fcu: int
    ) -> Tuple[float, float]:
        """
        Calculate required flexural reinforcement.
        Returns (As_required in mm², utilization ratio)
        """
        fy = STEEL_YIELD_STRENGTH

        # K = M / (bd²fcu)
        K = (moment * 1e6) / (b * d ** 2 * fcu)
        K_bal = 0.156

        utilization = K / K_bal

        if K > K_bal:
            self._add_calc_step(
                "Flexural design",
                f"K = {K:.4f} > K_bal = {K_bal}\n"
                f"Compression reinforcement required or section too small",
                "HK Code 2013 - Clause 6.1.2.4"
            )
            As_req = 0
        else:
            z = d * (0.5 + math.sqrt(0.25 - K / 0.9))
            z = min(z, 0.95 * d)
            As_req = (moment * 1e6) / (0.87 * fy * z)

            self._add_calc_step(
                "Flexural design",
                f"K = {K:.4f}, z = {z:.0f} mm\n"
                f"As,req = M / (0.87 × fy × z) = {As_req:.0f} mm²",
                "HK Code 2013 - Clause 6.1.2.4"
            )

        return As_req, utilization
