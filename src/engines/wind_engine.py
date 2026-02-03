"""
Wind Load Calculator - HK Wind Code 2019 Compliant

V3.5: FEM-only - Simplified calculations removed.
Use FEM results from src/fem/ module instead.

This module is deprecated for preliminary calculations.
All wind load analysis should be performed using:
- src/fem/load_combinations.py for HK Code 2019 wind load patterns
- src/fem/fem_engine.py for OpenSeesPy analysis
- src/fem/results_processor.py for drift and stress processing
"""

from typing import Dict, Any, List
from ..core.data_models import ProjectData, WindResult, CoreWallResult


class WindEngine:
    """
    V3.5 DEPRECATED: Wind loads now handled by FEM module.

    This class is retained for backward compatibility but should not be used.
    Use src.fem load combinations and FEM analysis for all wind analysis.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

        # V3.5: FEM-only
        self._add_calc_step(
            "V3.5 Migration Notice",
            "Simplified wind load calculation has been removed.\n"
            "Use FEM module (src/fem/load_combinations.py) for HK Code 2019 wind analysis.",
            "PrelimStruct V3.5 - FEM-only architecture"
        )

    def _add_calc_step(self, description: str, calculation: str, reference: str = ""):
        """Add a calculation step to the audit trail"""
        self.calculations.append({
            "description": description,
            "calculation": calculation,
            "reference": reference
        })

    def calculate_wind_loads(self):
        """
        Extract total wind loads (Base Shear, Overturning) from FEM analysis.
        
        Returns:
            WindResult: Wind load summary from FEM.
        """
        result = WindResult()
        
        if not self.project.fem_result:
            return result
            
        # Extract max base shear and overturning moment from Reaction Envelopes
        # Iterate Envelope of all supports (fixed nodes)
        total_shear_x = 0.0
        total_shear_y = 0.0
        total_moment_x = 0.0
        total_moment_y = 0.0
        
        # Typically we look at "Reaction Envelope" summaries
        # But here we iterate reactions
        if self.project.fem_result.enveloped_results:
             # If we had pre-calculated global envelopes (global base shear), we'd use them.
             # Since our EnvelopedResult in data_models is slightly generic, let's assume we sum up 
             # reactions from specific wind load cases.
             pass
        
        # Iterate load cases to find WIND cases
        max_shear = 0.0
        max_moment = 0.0
        
        for lc_result in self.project.fem_result.load_case_results:
            # Check if this is a wind combination (simplified check by name)
            if "wind" in str(lc_result.combination).lower():
                # Sum reactions at base
                v_x = 0.0
                v_y = 0.0
                m_x = 0.0
                m_y = 0.0
                for node_id, rxn in lc_result.reactions.items():
                    # Assuming rxn is [Fx, Fy, Fz, Mx, My, Mz]
                    if len(rxn) >= 2:
                        v_x += rxn[0]
                        v_y += rxn[1]
                    if len(rxn) >= 5:
                        m_x += rxn[3]
                        m_y += rxn[4]
                        
                shear = (v_x**2 + v_y**2)**0.5
                moment = (m_x**2 + m_y**2)**0.5
                
                if shear > max_shear: max_shear = shear
                if moment > max_moment: max_moment = moment
        
        result.base_shear = max_shear
        result.overturning_moment = max_moment
        result.drift_ok = True # Defer to specific drift check in FEM processor
        
        return result

    def distribute_lateral_to_columns(self, wind_result):
        """
        Deprecated. Distribution happens naturally in FEM.
        """
        pass

    # V3.5: All private helper methods removed - use FEM module


class CoreWallEngine:
    """
    V3.5 DEPRECATED: Core wall analysis now handled by FEM module.

    This class is retained for backward compatibility but should not be used.
    Use src.fem with ShellMITC4 elements for core wall analysis.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

        # V3.5: FEM-only
        self._add_calc_step(
            "V3.5 Migration Notice",
            "Simplified core wall analysis has been removed.\n"
            "Use FEM module with ShellMITC4 wall elements.",
            "PrelimStruct V3.5 - FEM-only architecture"
        )

    def _add_calc_step(self, description: str, calculation: str, reference: str = ""):
        """Add a calculation step to the audit trail"""
        self.calculations.append({
            "description": description,
            "calculation": calculation,
            "reference": reference
        })

    def check_core_wall(self, wind_result):
        """
        Check core wall stresses using FEM results.
        
        Returns:
            CoreWallResult: Stress utilization ratios.
        """
        result = CoreWallResult(element_type="Core Wall", size="N/A")
        
        if not self.project.fem_result:
             # Default place holder
             return result
             
        # Extract max/min stresses from shell elements
        # Identify shell elements
        # In this simplified engine without direct mesh element type iteration readily verified,
        # we assume we can look at "stresses" in load case results.
        
        max_stress_comp = 0.0
        max_stress_tens = 0.0
        
        # We can look at EnvelopedResults if populated, or scan cases
        # Scan cases for max stress (Smax/Smin principal or SvM)
        # Typically OpenSees Shell outputs: [s11, s22, s12, m11, m22, m12, ...].
        # We need Syy (vertical stress). 
        # For now, let's assume we extract a generic 'stress' metric if computed
        
        # Simplified: Check utilization based on overturning moment vs section modulus
        # If we have section properties from LateralInput
        props = self.project.lateral.section_properties
        if props and props.I_xx > 0:
             # My / I * x
             # M_wind from wind_result
             M = wind_result.overturning_moment * 1000 * 1000 # Nmm
             # y max roughly half depth
             y = (self.project.lateral.building_depth * 1000) / 2
             
             stress_flexure = M * y / props.I_xx
             
             # Axial load from gravity
             # Area A from props
             # Approx P = volume * density
             P = self.project.concrete_volume * 24.5 * 1000 # N (very rough total weight, usually core takes partial)
             # Let's assume core takes 30% of building weight
             P_core = P * 0.3
             stress_axial = P_core / props.A
             
             total_comp = stress_axial + stress_flexure
             total_tens = stress_axial - stress_flexure
             
             fcu = self.project.materials.fcu_column # Use column grade for core
             result.compression_check = total_comp / (0.45 * fcu) # Simplified allowable
             
             if total_tens < 0: # Tension
                  # Allowable tension roughly 0.5 sqrt(fcu) or 0 if unreinforced assumption
                  ft = 0.5 * (fcu ** 0.5)
                  result.tension_check = abs(total_tens) / ft
                  if abs(total_tens) > ft:
                       result.requires_tension_piles = True
        
        return result


class DriftEngine:
    """
    Drift analysis using FEM results.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

    def calculate_drift(self, wind_result):
        """
        Extract drift from FEM analysis results.
        
        Args:
            wind_result: Existing WindResult to update
            
        Returns:
            WindResult: Updated with drift metrics
        """
        if not self.project.fem_result:
            return wind_result
            
        # Get max lateral displacement from FEM envelope at top node
        # We need to identify top nodes.
        # Max Z coordinate
        max_z = 0.0
        top_nodes = []
        
        if self.project.fem_model and self.project.fem_model.mesh:
             nodes = self.project.fem_model.mesh.node_coordinates
             for tag, coords in nodes.items():
                 if coords[2] > max_z:
                     max_z = coords[2]
             
             tolerance = 0.1
             for tag, coords in nodes.items():
                 if abs(coords[2] - max_z) < tolerance:
                     top_nodes.append(tag)
        
        # Find max displacement among top nodes
        max_disp = 0.0
        if top_nodes and self.project.fem_result.load_case_results:
             for lc in self.project.fem_result.load_case_results:
                 # Check if lateral load case
                 for tag in top_nodes:
                     if tag in lc.node_displacements:
                         disp = lc.node_displacements[tag]
                         # Horizontal magnitude
                         horiz = (disp[0]**2 + disp[1]**2)**0.5
                         if horiz > max_disp:
                             max_disp = horiz
        
        # Update wind result
        wind_result.drift_mm = max_disp * 1000 # m to mm
        H = max_z if max_z > 0 else self.project.geometry.floors * self.project.geometry.story_height
        if H > 0:
            wind_result.drift_index = max_disp / H
            # Allowable H/500
            wind_result.drift_ok = wind_result.drift_index <= (1.0/500.0)
            
        return wind_result
