"""
Column Design Engine - HK Code 2013 Compliant

V3.5: FEM-only - Simplified calculations removed.
Use FEM results from src/fem/ module instead.

This module is deprecated for preliminary calculations.
All column design should be performed using:
- src/fem/model_builder.py for geometry to FEM conversion
- src/fem/fem_engine.py for OpenSeesPy analysis
- src/fem/results_processor.py for post-processing
"""

from typing import Dict, Any, List
from ..core.data_models import ProjectData, ColumnPosition, ColumnResult, FEMElementType
from ..core.load_tables import get_cover


class ColumnEngine:
    """
    V3.5 DEPRECATED: Column design now handled by FEM module.

    This class is retained for backward compatibility but should not be used.
    Use src.fem.FEMModel for all column analysis.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

        # V3.5: FEM-only
        self._add_calc_step(
            "V3.5 Migration Notice",
            "Simplified column design has been removed.\n"
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

    def calculate(
        self,
        position: ColumnPosition = ColumnPosition.INTERIOR
    ):
        """
        Perform column design checks using FEM results.
        
        Args:
            position: Ignored in FEM mode (used for compatibility)
        """
        # Default result
        h = 600
        b = 600
        result = ColumnResult(
            element_type="Column",
            size=f"{b}x{h}",
            status="FAIL",
            dimension=b
        )

        if not self.project.fem_result:
            result.warnings.append("No FEM results found. Run analysis first.")
            return result

        # Extract max Axial (N) and Moment (M)
        max_N = 0.0
        max_M = 0.0
        
        # Identify column elements
        # For now, just envelope ALL column elements.
        col_ids = set()
        if self.project.fem_model and self.project.fem_model.mesh:
            for elem in self.project.fem_model.mesh.elements:
                # Assuming specialized element type or just generic BEAM
                # If we distinguish columns via some tag or type, use it.
                # Here we assume element_type could be BEAM, but in future maybe COLUMN
                if elem.element_type == FEMElementType.BEAM:
                    # Basic heuristic: if vertical? Not easy to check without node coords easily accessible here.
                    # For prelim, we'll assume any 'Beam' could be a column if vertical.
                    # But since we Envelope ALL beams in BeamEngine, we might be double counting.
                    # As a placeholder, we accept 'BEAM' type here too for now.
                    col_ids.add(elem.element_id)
        
        check_ids = col_ids if col_ids else None

        for lc_result in self.project.fem_result.load_case_results:
            for elem_id, forces in lc_result.element_forces.items():
                if check_ids and elem_id not in check_ids:
                    continue
                
                # Check N (Axial) and M (Moment)
                n_abs = 0.0
                m_abs = 0.0
                
                # Axial
                for key in ["N", "P", "Fz", "N_i", "N_j"]:
                    if key in forces: n_abs = max(n_abs, abs(forces[key]))
                
                # Moment
                # Combine Mx and My maybe? Or check individually.
                # HK Code: Combined axial + moment
                mx = 0.0
                my = 0.0
                if "Mx" in forces: mx = abs(forces["Mx"])
                if "My" in forces: my = abs(forces["My"])
                if "Mz" in forces: mx = abs(forces["Mz"]) # Local axis 
                
                # Simple envelope max
                m_comb = (mx**2 + my**2)**0.5
                m_abs = max(m_abs, m_comb)
                
                if n_abs > max_N: max_N = n_abs
                if m_abs > max_M: max_M = m_abs

        result.axial_load = max_N
        result.moment = max_M
        
        # Design Check (HK Code 2013)
        fcu = self.project.materials.fcu_column
        Ac = b * h
        
        # Slenderness check (simplified)
        # l_e / h. Assume l_e = 0.85 * 3.0m
        le = 0.85 * 3000
        slenderness = le / h
        result.slenderness = slenderness
        result.is_slender = slenderness > 15 # Rough limit for braced
        
        # Capacity Check (Simplified interaction)
        # N_cap = 0.35 fcu Ac + 0.67 fy Asc
        # This is pure axial. Interaction is more complex.
        # Use simple interaction formula: N/Nuz + M/Muz <= 1.0 (Approx)
        
        # For prelim, check if N < 0.4 fcu Ac (typical limit for sizing)
        N_limit = 0.4 * fcu * Ac / 1000.0 # kN
        
        if max_N > N_limit:
            result.status = "FAIL"
            result.warnings.append(f"Axial load too high (N={max_N:.0f} > {N_limit:.0f})")
            result.combined_utilization = max_N / N_limit
        else:
            result.status = "OK"
            result.combined_utilization = max_N / N_limit
            
        # Add moment check roughly
        # Check if eccentricity e = M/N is large.
        
        return result

    # Combined load checks delegated to FEM results processor

    # V3.5: All private helper methods removed - use FEM module
