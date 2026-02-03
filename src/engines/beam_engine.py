"""
Beam Design Engine - HK Code 2013 Compliant

V3.5: FEM-only - Simplified calculations removed.
Use FEM results from src/fem/ module instead.

This module is deprecated for preliminary calculations.
All beam design should be performed using:
- src/fem/model_builder.py for geometry to FEM conversion
- src/fem/fem_engine.py for OpenSeesPy analysis
- src/fem/results_processor.py for post-processing
"""

from typing import Dict, Any, List
from ..core.data_models import ProjectData, BeamResult, FEMElementType
from ..core.load_tables import get_cover


class BeamEngine:
    """
    V3.5 DEPRECATED: Beam design now handled by FEM module.

    This class is retained for backward compatibility but should not be used.
    Use src.fem.FEMModel for all beam analysis.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

        # V3.5: FEM-only
        self._add_calc_step(
            "V3.5 Migration Notice",
            "Simplified beam design has been removed.\n"
            "Use FEM module (src/fem/) for all structural analysis.",
            "PrelimStruct V3.5 - FEM-only architecture"
        )

    def _add_calc_step(self, description: str, calculation: str, reference: str = ""):
        """Add a calculation step to the audit trail"""
        self.calculations.append({
            "description": description,
            "calculation": calculation,
            "reference": reference
        })

    def calculate_primary_beam(self, tributary_width: float):
        """
        Perform primary beam design checks using FEM results.
        
        Args:
           tributary_width: Ignored in FEM mode (used for compatibility signature)
        """
        return self._calculate_beam_from_fem("Primary Beam")

    def calculate_secondary_beam(self, tributary_width: float):
        """
        Perform secondary beam design checks using FEM results.
        
        Args:
           tributary_width: Ignored in FEM mode (used for compatibility signature)
        """
        return self._calculate_beam_from_fem("Secondary Beam")

    def _calculate_beam_from_fem(self, label: str) -> BeamResult:
        """Internal method to verify beam design from FEM forces."""
        # Default result
        h = 600 # Estimate
        b = 300
        result = BeamResult(
            element_type="Beam",
            size=f"{b}x{h}",
            status="FAIL",
            width=b,
            depth=h
        )

        if not self.project.fem_result:
            result.warnings.append("No FEM results found. Run analysis first.")
            return result

        # Extract max M and V
        max_M = 0.0
        max_V = 0.0
        
        # Identify beam elements
        # For now, just take ALL beam elements. In refined version, filter by 'primary'/'secondary' tag if available
        # But ProjectData doesn't store 'primary' vs 'secondary' tags in Element yet (generic mesh).
        # So we just envelope all beams.
        beam_ids = set()
        if self.project.fem_model and self.project.fem_model.mesh:
            for elem in self.project.fem_model.mesh.elements:
                if elem.element_type == FEMElementType.BEAM:
                    beam_ids.add(elem.element_id)
        
        check_ids = beam_ids if beam_ids else None

        for lc_result in self.project.fem_result.load_case_results:
            for elem_id, forces in lc_result.element_forces.items():
                if check_ids and elem_id not in check_ids:
                    continue
                
                # Check M and V
                # OpenSees BeamColumn: Mz, Vy usually
                m_abs = 0.0
                v_abs = 0.0
                
                # Try to find moments
                for key in ["Mz", "Mz_i", "Mz_j", "M_max"]:
                    if key in forces: m_abs = max(m_abs, abs(forces[key]))
                
                # Try to find shear
                for key in ["Vy", "Vy_i", "Vy_j", "V_max"]:
                    if key in forces: v_abs = max(v_abs, abs(forces[key]))
                    
                if m_abs > max_M: max_M = m_abs
                if v_abs > max_V: max_V = v_abs

        result.moment = max_M
        result.shear = max_V
        
        # Design Check (HK Code 2013)
        cover = self.project.materials.cover_beam
        bar_dia = 20
        d = h - cover - bar_dia/2
        fcu = self.project.materials.fcu_beam
        fy = self.project.materials.fy
        fyv = self.project.materials.fyv
        
        # Flexure
        K = (max_M * 1e6) / (b * d**2 * fcu)
        if K > 0.156:
             result.status = "FAIL"
             result.warnings.append(f"Section over-reinforced (K={K:.3f})")
             return result
             
        import math
        z_d = 0.5 + math.sqrt(0.25 - K/0.9)
        z = min(0.95 * d, z_d * d)
        As_req = (max_M * 1e6) / (0.87 * fy * z)
        
        # Shear
        # v = V / (b*d)
        v = (max_V * 1000) / (b * d)
        v_c = 0.6 # Simplified shear capacity for prelim check
        vc_max = min(0.8 * math.sqrt(fcu), 7.0)
        
        if v > vc_max:
             result.status = "FAIL"
             result.warnings.append(f"Shear too high (v={v:.2f} MPa > {vc_max:.2f})")
        elif v > v_c:
             result.shear_reinforcement_required = True
             # Calculate links
             # Asv/sv = b(v-vc) / (0.87fyv)
             result.shear_reinforcement_area = (b * (v - v_c)) / (0.87 * fyv) * 1000 # per m
             result.status = "OK"
        else:
             result.status = "OK"
             
        result.shear_capacity = v_c * b * d / 1000.0 # kN
        
        return result

    # V3.5: All private helper methods removed - use FEM module
