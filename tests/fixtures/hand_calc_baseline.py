"""
Hand calculation baseline for subdivision force validation.

This module provides analytically calculated force values at subdivision points
for simple beam and column cases. These values serve as the baseline for validating
subdivision accuracy (1% tolerance).

Reference formulas:
- Simply Supported Beam with UDL: M(x) = wx(L-x)/2, V(x) = w(L/2 - x)
- Fixed-End Beam with UDL: Standard fixed-end moment formulas
- Cantilever Column with Point Load: M(x) = P(H-x), V(x) = P
"""

from dataclasses import dataclass
from typing import List, Tuple

# Tolerance for force comparison (1% = 0.01)
TOLERANCE = 0.01


@dataclass
class ForceAtPoint:
    """Force values at a specific point along a member."""
    position: float  # Position as fraction of length (0.0 to 1.0)
    position_label: str  # Human-readable label (e.g., "0.5L", "L/2")
    moment: float  # Bending moment in kN.m
    shear: float  # Shear force in kN
    axial: float = 0.0  # Axial force in kN (default 0 for beams)


@dataclass
class BaselineCase:
    """A complete test case with geometry, loading, and expected forces."""
    name: str
    description: str
    length: float  # Member length in meters
    loading_description: str
    
    # Loading parameters
    udl: float = 0.0  # Uniform distributed load in kN/m
    point_load: float = 0.0  # Point load in kN
    point_load_position: float = 0.0  # Position of point load as fraction of length
    
    # Expected forces at subdivision points
    forces: List[ForceAtPoint] = None
    
    def __post_init__(self):
        """Calculate expected forces if not provided."""
        if self.forces is None:
            self.forces = []


# =============================================================================
# CASE 1: Simply Supported Beam with UDL
# =============================================================================
# Configuration: w = 10 kN/m, L = 6m
# Formulas:
#   M(x) = wx(L-x)/2
#   M_max at x = L/2: wL²/8 = 10 * 36 / 8 = 45 kN.m
#   V(x) = w(L/2 - x)
#   V_max at support: wL/2 = 10 * 6 / 2 = 30 kN

SIMPLY_SUPPORTED_UDL = BaselineCase(
    name="simply_supported_udl",
    description="Simply supported beam with uniform distributed load",
    length=6.0,  # meters
    loading_description="UDL w = 10 kN/m over entire span",
    udl=10.0,
    forces=[
        # x = 0L (left support)
        ForceAtPoint(
            position=0.0,
            position_label="0L",
            moment=0.0,  # Simply supported = 0 moment at support
            shear=30.0,  # V = w*L/2 = 10*6/2 = 30 kN
        ),
        # x = 0.25L (1.5m)
        ForceAtPoint(
            position=0.25,
            position_label="0.25L",
            moment=10.0 * 1.5 * (6.0 - 1.5) / 2,  # M(1.5m) = 10*1.5*4.5/2 = 33.75 kN.m
            shear=10.0 * (3.0 - 1.5),  # V(1.5m) = 10*(3-1.5) = 15 kN
        ),
        # x = 0.5L (midspan)
        ForceAtPoint(
            position=0.5,
            position_label="0.5L",
            moment=45.0,  # M_max = wL^2/8 = 10*36/8 = 45 kN.m
            shear=0.0,  # V = 0 at midspan for symmetric loading
        ),
        # x = 0.75L (4.5m)
        ForceAtPoint(
            position=0.75,
            position_label="0.75L",
            moment=10.0 * 4.5 * (6.0 - 4.5) / 2,  # M(4.5m) = 10*4.5*1.5/2 = 33.75 kN.m
            shear=10.0 * (3.0 - 4.5),  # V(4.5m) = 10*(3-4.5) = -15 kN
        ),
        # x = 1.0L (right support)
        ForceAtPoint(
            position=1.0,
            position_label="1.0L",
            moment=0.0,  # Simply supported = 0 moment at support
            shear=-30.0,  # V = -w*L/2 = -30 kN
        ),
    ]
)


# =============================================================================
# CASE 2: Fixed-End Beam with UDL
# =============================================================================
# Configuration: w = 10 kN/m, L = 6m
# Formulas:
#   M_support = -wL²/12 = -10*36/12 = -30 kN.m
#   M_midspan = wL²/24 = 10*36/24 = 15 kN.m
#   V at support = wL/2 = 30 kN
#   M(x) = -wL²/12 + wLx/2 - wx²/2
#   V(x) = wL/2 - wx

FIXED_END_UDL = BaselineCase(
    name="fixed_end_udl",
    description="Fixed-end beam with uniform distributed load",
    length=6.0,  # meters
    loading_description="UDL w = 10 kN/m over entire span, both ends fixed",
    udl=10.0,
    forces=[
        # x = 0L (left support)
        ForceAtPoint(
            position=0.0,
            position_label="0L",
            moment=-30.0,  # M = -wL^2/12 = -10*36/12 = -30 kN.m
            shear=30.0,  # V = wL/2 = 10*6/2 = 30 kN
        ),
        # x = 0.25L (1.5m)
        ForceAtPoint(
            position=0.25,
            position_label="0.25L",
            moment=-30.0 + 10.0*6.0*1.5/2 - 10.0*1.5**2/2,  # M(1.5m) = -30 + 45 - 11.25 = 3.75 kN.m
            shear=30.0 - 10.0*1.5,  # V(1.5m) = 30 - 15 = 15 kN
        ),
        # x = 0.5L (midspan = 3m)
        ForceAtPoint(
            position=0.5,
            position_label="0.5L",
            moment=15.0,  # M = wL^2/24 = 10*36/24 = 15 kN.m
            shear=0.0,  # V = 0 at midspan for symmetric loading
        ),
        # x = 0.75L (4.5m)
        ForceAtPoint(
            position=0.75,
            position_label="0.75L",
            moment=-30.0 + 10.0*6.0*4.5/2 - 10.0*4.5**2/2,  # M(4.5m) = -30 + 135 - 101.25 = 3.75 kN.m
            shear=30.0 - 10.0*4.5,  # V(4.5m) = 30 - 45 = -15 kN
        ),
        # x = 1.0L (right support)
        ForceAtPoint(
            position=1.0,
            position_label="1.0L",
            moment=-30.0,  # M = -wL^2/12 = -30 kN.m (symmetric)
            shear=-30.0,  # V = -wL/2 = -30 kN
        ),
    ]
)


# =============================================================================
# CASE 3: Cantilever Column with Point Load
# =============================================================================
# Configuration: P = 50 kN at top, H = 4m
# Formulas:
#   M(x) = P(H - x) measured from base
#   M_base = P*H = 50*4 = 200 kN.m
#   M_mid = P*H/2 = 50*2 = 100 kN.m
#   V(x) = P (constant shear)

CANTILEVER_POINT_LOAD = BaselineCase(
    name="cantilever_point_load",
    description="Cantilever column with point load at top",
    length=4.0,  # meters (height)
    loading_description="Point load P = 50 kN at free end (top)",
    point_load=50.0,
    point_load_position=1.0,  # At free end
    forces=[
        # x = 0L (base - fixed end)
        ForceAtPoint(
            position=0.0,
            position_label="0L",
            moment=200.0,  # M = P*H = 50*4 = 200 kN.m
            shear=50.0,  # V = P = 50 kN
            axial=50.0,  # Axial force = P (for column)
        ),
        # x = 0.25L (1m from base)
        ForceAtPoint(
            position=0.25,
            position_label="0.25H",
            moment=50.0 * (4.0 - 1.0),  # M = 50*3 = 150 kN.m
            shear=50.0,
            axial=50.0,
        ),
        # x = 0.5L (mid-height = 2m from base)
        ForceAtPoint(
            position=0.5,
            position_label="0.5H",
            moment=100.0,  # M = P*H/2 = 50*2 = 100 kN.m
            shear=50.0,
            axial=50.0,
        ),
        # x = 0.75L (3m from base)
        ForceAtPoint(
            position=0.75,
            position_label="0.75H",
            moment=50.0 * (4.0 - 3.0),  # M = 50*1 = 50 kN.m
            shear=50.0,
            axial=50.0,
        ),
        # x = 1.0L (top - free end)
        ForceAtPoint(
            position=1.0,
            position_label="1.0H",
            moment=0.0,  # M = 0 at free end
            shear=50.0,
            axial=50.0,
        ),
    ]
)


# Export all baseline cases
ALL_BASELINE_CASES = [
    SIMPLY_SUPPORTED_UDL,
    FIXED_END_UDL,
    CANTILEVER_POINT_LOAD,
]


def get_baseline_case(name: str) -> BaselineCase:
    """Retrieve a baseline case by name."""
    for case in ALL_BASELINE_CASES:
        if case.name == name:
            return case
    raise ValueError(f"Baseline case '{name}' not found. Available: {[c.name for c in ALL_BASELINE_CASES]}")


def get_expected_forces_at_position(case: BaselineCase, position: float, tolerance: float = 0.01) -> ForceAtPoint:
    """
    Get expected force values at a specific position.
    
    Args:
        case: The baseline case
        position: Position as fraction of length (0.0 to 1.0)
        tolerance: Position matching tolerance
        
    Returns:
        ForceAtPoint: Expected forces at that position
        
    Raises:
        ValueError: If position not found in baseline data
    """
    for force_point in case.forces:
        if abs(force_point.position - position) < tolerance:
            return force_point
    
    raise ValueError(
        f"Position {position} not found in baseline case '{case.name}'. "
        f"Available positions: {[f.position for f in case.forces]}"
    )
