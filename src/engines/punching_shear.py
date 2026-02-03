"""
Punching Shear Check - HK Code 2013 Clause 6.1.5.6

V3.5: FEM-only - Simplified calculations removed.
Use FEM results from src/fem/ module instead.

This module is deprecated for preliminary calculations.
All punching shear checks should be performed using:
- src/fem/fem_engine.py for slab-column connection analysis
- src/fem/results_processor.py for punching stress extraction
- src/fem/design_codes/hk2013.py for code-based checks
"""

from typing import Dict, Any, List
from enum import Enum
from ..core.data_models import ProjectData, FEMElementType
from ..core.load_tables import get_cover


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
    V3.5 DEPRECATED: Punching shear checks now handled by FEM module.

    This class is retained for backward compatibility but should not be used.
    Use src.fem for flat slab punching shear analysis per HK Code 2013 Clause 6.1.5.6.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

        # V3.5: FEM-only
        self._add_calc_step(
            "V3.5 Migration Notice",
            "Simplified punching shear check has been removed.\n"
            "Use FEM module for slab-column connection analysis.",
            "PrelimStruct V3.5 - FEM-only architecture"
        )

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
    ):
        """
        Perform punching shear check using FEM results (or passed reaction if verifying specifically).
        
        Note: If reaction is passed, it overrides FEM extraction. 
        In strict FEM mode, we should fetch reaction from FEM.
        """
        result = PunchingShearResult()
        
        # If reaction provided is 0 or dummy, try to fetch from FEM
        V_Ed = reaction
        
        # If reaction is provided as arg (like in tests), use it.
        # Otherwise if reaction == 0, fetch from FEM
        if V_Ed == 0 and self.project.fem_result:
             # Find max column reaction
             # Simplified: just iterate all reactions
             max_Fz = 0.0
             for lc in self.project.fem_result.load_case_results:
                 for _, rxn in lc.reactions.items():
                     if len(rxn) >= 3:
                         max_Fz = max(max_Fz, abs(rxn[2]))
             V_Ed = max_Fz
             
        result.V_Ed = V_Ed

        # Calculate effective depth d
        cover = self.project.materials.cover_slab # Default 25mm
        bar_dia = 16 # Approx
        d = slab_thickness - cover - bar_dia
        
        # Beta factor for eccentricity (HK Code 2013 Cl 6.1.5.6)
        # Simplified beta values
        beta = 1.15 # Interior
        if location == ColumnLocation.EDGE:
            beta = 1.4
        elif location == ColumnLocation.CORNER:
            beta = 1.5
            
        # Critical perimeter u1 at 2d from face
        # Rectangular column c1 x c2 (assume square c x c)
        c = column_size
        
        if location == ColumnLocation.INTERIOR:
            u1 = 4*c + 2 * 3.14159 * 2 * d
        elif location == ColumnLocation.EDGE:
            u1 = 3*c + 3.14159 * 2 * d # Approximate for edge
        else: # Corner
            u1 = 2*c + 0.5 * 3.14159 * 2 * d
            
        result.perimeter = u1
        
        # Design shear stress v_Ed
        # v_Ed = beta * V_Ed / (u1 * d)
        # V_Ed in kN -> N
        if u1 > 0 and d > 0:
            result.v_Ed = beta * (V_Ed * 1000) / (u1 * d)
            
        # Design shear resistance v_Rd (without shear reinf)
        # v_c = 0.79 * (100*As/bd)^(1/3) * (400/d)^(1/4) / gamma_m
        # Using simplified rho input
        rho = min((rho_x + rho_y)/2 / 100.0, 0.02) # Max 2%
        
        # HK Code formula (approx)
        # v_c depends on fcu too
        # v_c = 0.79 * (100*rho)^(1/3) * (400/d)^(1/4) * (fcu/25)^(1/3) / 1.25(material factor)
        
        term1 = (100 * rho)**(1.0/3.0)
        term2 = (400 / d)**0.25 if d > 0 else 1.0
        term3 = (min(fcu, 80) / 25.0)**(1.0/3.0)
        
        v_c_characteristic = 0.79 * term1 * term2 * term3
        result.v_Rd = v_c_characteristic / 1.25
        
        # Max shear stress at column face v_max
        # u0 = perimeter of column
        if location == ColumnLocation.INTERIOR:
            u0 = 4*c
        elif location == ColumnLocation.EDGE:
            u0 = 3*c
        else:
            u0 = 2*c
            
        if u0 > 0 and d > 0:
            result.v_max = beta * (V_Ed * 1000) / (u0 * d)
            
        # Max allowable v_max (0.8 sqrt(fcu) or 7 MPa)
        import math
        v_max_limit = min(0.8 * math.sqrt(fcu), 7.0)
        
        # Checks
        result.utilization = result.v_Ed / result.v_Rd if result.v_Rd > 0 else 999.0
        
        if result.v_max > v_max_limit:
            result.status = "FAIL"
            result.warnings.append(f"Max shear at face exceeded ({result.v_max:.2f} > {v_max_limit:.2f})")
        elif result.v_Ed > result.v_Rd:
            result.status = "FAIL"
            result.shear_reinforcement_required = True
            result.warnings.append(f"Punching shear failure (v_Ed {result.v_Ed:.2f} > v_Rd {result.v_Rd:.2f})")
        else:
            result.status = "OK"
            
        return result

    # V3.5: All private helper methods removed - use FEM module


def check_flat_slab_punching(project: ProjectData):
    """
    V3.5 DEPRECATED: Use FEM module instead.

    Raises:
        NotImplementedError: Simplified methods removed in V3.5
    """
    raise NotImplementedError(
        "Simplified punching shear check removed in V3.5. "
        "Use src.fem for flat slab analysis with ShellMITC4 elements."
    )
