"""
Coupling Beam Design Engine - HK Code 2013 Compliant

This module implements design of coupling beams for core wall systems per
HK Code 2013. Coupling beams are critical for lateral load resistance in
tall buildings with core wall systems.

Design approach follows HK Code 2013 provisions for:
- Deep beams (Clause 6.7) - typically L/h < 2.0
- Shear design with diagonal reinforcement
- Flexural design for coupling action moments
- Detailing requirements for ductility
"""

import math
from typing import Dict, Any, List, Tuple, Optional

from ..core.constants import (
    CONCRETE_DENSITY,
    STEEL_YIELD_STRENGTH,
    LINK_YIELD_STRENGTH,
    GAMMA_C,
    GAMMA_S,
    GAMMA_SV,
    SHEAR_STRESS_MAX_FACTOR,
    SHEAR_STRESS_MAX_LIMIT,
)
from ..core.data_models import CouplingBeam, CouplingBeamResult


class CouplingBeamEngine:
    """
    Coupling beam design calculator per HK Code 2013.

    Coupling beams are deep beams that span openings in core walls,
    providing coupling action for lateral load resistance. They are
    characterized by:
    - High shear forces relative to moment
    - Short span-to-depth ratios (typically L/h < 2.0)
    - Diagonal reinforcement for shear resistance
    - Width constrained by wall thickness
    """

    def __init__(self, fcu: int = 40, fy: int = 500, fyv: int = 250):
        """Initialize coupling beam engine with material properties.

        Args:
            fcu: Characteristic concrete cube strength (MPa)
            fy: Characteristic yield strength of main reinforcement (MPa)
            fyv: Characteristic yield strength of shear reinforcement (MPa)
        """
        self.fcu = fcu
        self.fy = fy
        self.fyv = fyv
        self.calculations: List[Dict[str, Any]] = []

    def _add_calc_step(self, description: str, calculation: str, reference: str = ""):
        """Add a calculation step to the audit trail."""
        self.calculations.append({
            "description": description,
            "calculation": calculation,
            "reference": reference
        })

    def design_coupling_beam(
        self,
        beam: CouplingBeam,
        design_shear: float,
        design_moment: float,
        cover: int = 50,
    ) -> CouplingBeamResult:
        """Design coupling beam for given actions.

        Args:
            beam: CouplingBeam geometry
            design_shear: Factored design shear force (kN)
            design_moment: Factored design moment (kNm) - typically lower than shear
            cover: Concrete cover to reinforcement (mm)

        Returns:
            CouplingBeamResult with design output

        Note:
            For coupling beams, shear typically governs over flexure due to
            short span and high lateral forces. Diagonal reinforcement is
            usually required.
        """
        self.calculations = []

        self._add_calc_step(
            "COUPLING BEAM DESIGN",
            f"Clear span = {beam.clear_span:.0f} mm\n"
            f"Depth = {beam.depth:.0f} mm\n"
            f"Width = {beam.width:.0f} mm\n"
            f"L/h ratio = {beam.span_to_depth_ratio:.2f}",
            "Geometry from core wall opening"
        )

        # Check deep beam status
        is_deep = beam.is_deep_beam
        self._add_calc_step(
            "Deep beam check",
            f"L/h = {beam.span_to_depth_ratio:.2f} < 2.0 → {'YES' if is_deep else 'NO'}",
            "HK Code 2013 Cl 6.7 - Deep beam when L/h < 2.0"
        )

        # Design for shear (dominant action)
        shear_ok, shear_capacity, diagonal_rebar, link_spacing = \
            self._design_for_shear(beam, design_shear, cover)

        # Design for flexure
        flexure_ok, top_rebar, bottom_rebar = \
            self._design_for_flexure(beam, design_moment, cover)

        # Determine overall status
        if shear_ok and flexure_ok:
            status = "OK"
            warnings = []
            utilization = max(design_shear / shear_capacity,
                            design_moment / (self._calculate_moment_capacity(beam, top_rebar)))
        else:
            status = "REVIEW REQUIRED"
            warnings = []
            if not shear_ok:
                warnings.append("Shear capacity insufficient - increase depth or add diagonal bars")
            if not flexure_ok:
                warnings.append("Flexural capacity insufficient - increase reinforcement")
            utilization = 1.5  # Indicate over-capacity

        if is_deep:
            warnings.append("Deep beam - Strut-and-Tie Model (STM) recommended for final design")

        # Create result
        result = CouplingBeamResult(
            element_type="Coupling Beam",
            size=f"{beam.width:.0f}×{beam.depth:.0f}mm, L={beam.clear_span:.0f}mm",
            utilization=utilization,
            status=status,
            warnings=warnings,
            calculations=self.calculations,
            width=int(beam.width),
            depth=int(beam.depth),
            clear_span=beam.clear_span,
            moment=design_moment,
            shear=design_shear,
            shear_capacity=shear_capacity,
            top_rebar=top_rebar,
            bottom_rebar=bottom_rebar,
            diagonal_rebar=diagonal_rebar,
            link_spacing=link_spacing,
            is_deep_beam=is_deep,
            span_to_depth_ratio=beam.span_to_depth_ratio,
        )

        return result

    def _design_for_shear(
        self,
        beam: CouplingBeam,
        design_shear: float,
        cover: int,
    ) -> Tuple[bool, float, float, int]:
        """Design for shear including diagonal reinforcement.

        HK Code 2013 Cl 6.1.2.4: Shear design for beams
        For coupling beams, diagonal reinforcement is typically required.

        Args:
            beam: CouplingBeam geometry
            design_shear: Factored design shear (kN)
            cover: Concrete cover (mm)

        Returns:
            Tuple of (shear_ok, shear_capacity_kN, diagonal_rebar_mm2, link_spacing_mm)
        """
        self._add_calc_step(
            "SHEAR DESIGN",
            f"Design shear V = {design_shear:.1f} kN",
            "HK Code 2013 Cl 6.1.2"
        )

        # Effective depth
        d = beam.depth - cover - 20  # Assume 20mm bar diameter

        # Shear stress
        v = (design_shear * 1000) / (beam.width * d)  # MPa

        self._add_calc_step(
            "Calculate shear stress",
            f"d = {beam.depth} - {cover} - 20 = {d:.0f} mm\n"
            f"v = V/(b×d) = {design_shear*1000:.0f}/(({beam.width:.0f})×{d:.0f}) = {v:.2f} MPa",
            "Average shear stress"
        )

        # Maximum allowable shear stress
        # HK Code 2013: v_max = min(0.8√fcu, 7.0 MPa)
        v_max = min(SHEAR_STRESS_MAX_FACTOR * math.sqrt(self.fcu), SHEAR_STRESS_MAX_LIMIT)

        self._add_calc_step(
            "Maximum shear stress check",
            f"v_max = min(0.8√fcu, 7.0) = min(0.8×√{self.fcu}, 7.0) = {v_max:.2f} MPa\n"
            f"v = {v:.2f} MPa {'<' if v < v_max else '>'} v_max → "
            f"{'PASS' if v < v_max else 'FAIL - Section inadequate'}",
            "HK Code 2013 Cl 6.1.2.4"
        )

        # Concrete shear capacity (HK Code Cl 6.1.2.5)
        # v_c = 0.79 × (100 × rho_l)^(1/3) × (400/d)^(1/4) / gamma_m
        # Simplified for coupling beam: assume minimum reinforcement ratio
        rho_l = 0.005  # Assume 0.5% for estimation
        v_c = 0.79 * ((100 * rho_l) ** (1/3)) * ((400 / d) ** (1/4)) / GAMMA_C
        v_c = max(v_c, 0.4)  # Minimum per code

        V_c = v_c * beam.width * d / 1000  # kN

        self._add_calc_step(
            "Concrete shear resistance",
            f"v_c = 0.79×(100ρ)^(1/3)×(400/d)^(1/4)/γ_c = {v_c:.2f} MPa\n"
            f"V_c = v_c×b×d = {V_c:.1f} kN",
            "HK Code 2013 Cl 6.1.2.5"
        )

        # Shear reinforcement required
        V_s_req = design_shear - V_c  # kN

        if V_s_req > 0:
            # Diagonal reinforcement for coupling beams
            # V_s = A_sv × (fy/γ_s) × sin(α)
            # Assume α = 45° for typical diagonal bars
            alpha = 45  # degrees
            sin_alpha = math.sin(math.radians(alpha))

            # Required diagonal bar area per leg
            A_diag = (V_s_req * 1000 * GAMMA_S) / (self.fy * sin_alpha)  # mm²

            # Round up to practical bar sizes (use 2T25 minimum)
            A_diag = max(A_diag, 2 * 491)  # 2T25 = 982 mm²

            self._add_calc_step(
                "Diagonal reinforcement design",
                f"V_s required = V - V_c = {design_shear:.1f} - {V_c:.1f} = {V_s_req:.1f} kN\n"
                f"A_diag = V_s×γ_s/(fy×sin45°) = {V_s_req*1000*GAMMA_S:.0f}/({self.fy}×0.707)\n"
                f"      = {A_diag:.0f} mm² per leg\n"
                f"Provide 2T25 diagonal bars per face = 982 mm²",
                "Diagonal shear reinforcement"
            )

            diagonal_rebar = max(982, A_diag)  # 2T25
        else:
            diagonal_rebar = 0
            self._add_calc_step(
                "Diagonal reinforcement",
                "V_c > V → No diagonal reinforcement required (minimum detailing only)",
                "Conservative for coupling beams"
            )

        # Link spacing (secondary shear reinforcement)
        # Minimum links for confinement
        link_spacing = min(int(beam.depth / 4), 300)  # mm

        self._add_calc_step(
            "Link spacing",
            f"s = min(h/4, 300mm) = min({beam.depth:.0f}/4, 300) = {link_spacing} mm",
            "HK Code 2013 - Minimum detailing"
        )

        # Total shear capacity with diagonal bars
        if diagonal_rebar > 0:
            V_s = (diagonal_rebar * self.fy * sin_alpha) / (1000 * GAMMA_S)
            V_total = V_c + V_s
        else:
            V_total = V_c

        self._add_calc_step(
            "Total shear capacity",
            f"V_total = V_c + V_s = {V_c:.1f} + {V_total-V_c:.1f} = {V_total:.1f} kN\n"
            f"Utilization = V/V_total = {design_shear:.1f}/{V_total:.1f} = "
            f"{design_shear/V_total:.2f}",
            "Combined capacity"
        )

        shear_ok = (design_shear <= V_total) and (v < v_max)

        return shear_ok, V_total, diagonal_rebar, link_spacing

    def _design_for_flexure(
        self,
        beam: CouplingBeam,
        design_moment: float,
        cover: int,
    ) -> Tuple[bool, float, float]:
        """Design for flexure due to coupling action.

        Args:
            beam: CouplingBeam geometry
            design_moment: Factored design moment (kNm)
            cover: Concrete cover (mm)

        Returns:
            Tuple of (flexure_ok, top_rebar_mm2, bottom_rebar_mm2)
        """
        self._add_calc_step(
            "FLEXURAL DESIGN",
            f"Design moment M = {design_moment:.1f} kNm",
            "HK Code 2013 Cl 6.1.2.2"
        )

        # Effective depth
        d = beam.depth - cover - 20  # mm

        # Design constants (HK Code)
        # For fcu ≤ 60 MPa: K = M/(fcu×b×d²)
        K = (design_moment * 1e6) / (self.fcu * beam.width * d * d)

        self._add_calc_step(
            "Calculate K factor",
            f"d = {d:.0f} mm\n"
            f"K = M/(fcu×b×d²) = {design_moment*1e6:.0f}/({self.fcu}×{beam.width:.0f}×{d:.0f}²)\n"
            f"  = {K:.4f}",
            "Moment design parameter"
        )

        # Check if compression reinforcement needed (K > K')
        K_prime = 0.156  # For fcu = 40 MPa (typical for coupling beams)

        if K > K_prime:
            # Compression reinforcement required
            A_s_req = (K * self.fcu * beam.width * d * d) / (0.87 * self.fy * d)
            A_s2_req = ((K - K_prime) * self.fcu * beam.width * d * d) / \
                       (0.87 * self.fy * (d - cover - 20))

            self._add_calc_step(
                "Compression reinforcement required",
                f"K = {K:.4f} > K' = {K_prime:.4f}\n"
                f"Compression steel A_s2 = {A_s2_req:.0f} mm²",
                "Over-reinforced section"
            )
        else:
            # Tension reinforcement only
            z = d * (0.5 + math.sqrt(0.25 - K / 0.9))
            z = min(z, 0.95 * d)

            A_s_req = (design_moment * 1e6) / (0.87 * self.fy * z)
            A_s2_req = 0

            self._add_calc_step(
                "Tension reinforcement",
                f"z = d(0.5 + √(0.25 - K/0.9)) = {z:.0f} mm\n"
                f"A_s = M/(0.87×fy×z) = {A_s_req:.0f} mm²",
                "Singly reinforced section"
            )

        # Minimum reinforcement (HK Code Cl 9.2.1.1)
        # A_s,min = 0.13% × b × h
        A_s_min = 0.0013 * beam.width * beam.depth

        top_rebar = max(A_s_req, A_s_min)
        bottom_rebar = max(A_s2_req, A_s_min)  # Minimum bottom steel for crack control

        self._add_calc_step(
            "Minimum reinforcement check",
            f"A_s,min = 0.13%×b×h = 0.0013×{beam.width:.0f}×{beam.depth:.0f} = {A_s_min:.0f} mm²\n"
            f"Provide top: {top_rebar:.0f} mm²\n"
            f"Provide bottom: {bottom_rebar:.0f} mm² (minimum for crack control)",
            "HK Code 2013 Cl 9.2.1.1"
        )

        # Check capacity
        M_capacity = self._calculate_moment_capacity(beam, top_rebar)
        flexure_ok = design_moment <= M_capacity

        self._add_calc_step(
            "Flexural capacity check",
            f"M_capacity = {M_capacity:.1f} kNm\n"
            f"Utilization = M/M_capacity = {design_moment:.1f}/{M_capacity:.1f} = "
            f"{design_moment/M_capacity:.2f} → {'PASS' if flexure_ok else 'FAIL'}",
            "Verify adequate capacity"
        )

        return flexure_ok, top_rebar, bottom_rebar

    def _calculate_moment_capacity(self, beam: CouplingBeam, A_s: float) -> float:
        """Calculate moment capacity for given reinforcement.

        Args:
            beam: CouplingBeam geometry
            A_s: Tension reinforcement area (mm²)

        Returns:
            Moment capacity in kNm
        """
        # Simplified capacity calculation
        # M = 0.87 × fy × A_s × z (assume z ≈ 0.9d)
        d = beam.depth - 50 - 20  # Assume 50mm cover, 20mm bar
        z = 0.9 * d
        M = (0.87 * self.fy * A_s * z) / 1e6  # kNm
        return M


def estimate_coupling_beam_forces(
    beam: CouplingBeam,
    base_shear_per_wall: float,
    building_height: float,
    num_floors: int,
) -> Tuple[float, float]:
    """Estimate design forces for coupling beam from wind/seismic analysis.

    This is a simplified estimation. For accurate forces, use FEM analysis.

    Args:
        beam: CouplingBeam geometry
        base_shear_per_wall: Base shear on each wall segment (kN)
        building_height: Total building height (m)
        num_floors: Number of floors

    Returns:
        Tuple of (design_shear_kN, design_moment_kNm) at floor level

    Note:
        Actual forces depend on relative stiffness of walls and coupling beams.
        This provides conservative preliminary estimate.
    """
    # Simplified model: assume coupling beam takes portion of total shear
    # proportional to its stiffness relative to walls
    # Typical coupling beam takes 20-40% of shear in coupled system

    coupling_ratio = 0.3  # 30% coupling action (typical range 20-40%)

    # Shear force in coupling beam at given floor
    # Varies with height (maximum at base, decreasing upward)
    floor_height = building_height / num_floors
    shear_distribution_factor = 0.7  # Simplified triangular distribution

    design_shear = coupling_ratio * base_shear_per_wall * shear_distribution_factor

    # Moment in coupling beam (from shear × span/2)
    design_moment = design_shear * (beam.clear_span / 1000) / 2.0

    return design_shear, design_moment
