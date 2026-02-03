"""
Coupling Beam Design Engine - HK Code 2013 Compliant

V3.5: FEM-only - Simplified calculations removed.
Use FEM results from src/fem/ module instead.

This module is deprecated for preliminary calculations.
All coupling beam design should be performed using:
- src/fem/model_builder.py for coupling beam geometry
- src/fem/fem_engine.py for OpenSeesPy deep beam analysis
- src/fem/design_codes/hk2013.py for strut-and-tie modeling (STM)
"""

from typing import Dict, Any, List
from ..core.data_models import CouplingBeam


class CouplingBeamEngine:
    """
    V3.5 DEPRECATED: Coupling beam design now handled by FEM module.

    This class is retained for backward compatibility but should not be used.
    Use src.fem for deep beam analysis with strut-and-tie modeling.

    Coupling beams are deep beams that span openings in core walls,
    providing coupling action for lateral load resistance. Per HK Code 2013
    Clause 6.7, these require strut-and-tie modeling (STM) when L/h < 2.0.
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

        # V3.5: FEM-only
        self._add_calc_step(
            "V3.5 Migration Notice",
            "Simplified coupling beam design has been removed.\n"
            "Use FEM module with deep beam elements and STM modeling.",
            "PrelimStruct V3.5 - FEM-only architecture"
        )

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
    ):
        """
        V3.5 DEPRECATED: Use FEM module instead.

        Raises:
            NotImplementedError: Simplified methods removed in V3.5
        """
        raise NotImplementedError(
            "Simplified coupling beam design removed in V3.5. "
            "Use src.fem for deep beam analysis with strut-and-tie modeling (STM)."
        )

    # V3.5: All private helper methods removed - use FEM module


def estimate_coupling_beam_forces(
    beam: CouplingBeam,
    base_shear_per_wall: float,
    building_height: float,
    num_floors: int,
):
    """
    V3.5 DEPRECATED: Use FEM module instead.

    Raises:
        NotImplementedError: Simplified methods removed in V3.5
    """
    raise NotImplementedError(
        "Simplified force estimation removed in V3.5. "
        "Use FEM analysis for accurate coupling beam forces."
    )
