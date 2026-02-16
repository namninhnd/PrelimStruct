"""
FEM Design Checks for PrelimStruct — HK Code 2013 aligned.

Provides:
- Element classification (beam/column/slab/wall)
- HK COP shear stress and reinforcement ratio checks
- Ductility warnings
- Governing element selection (Top-N)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.core.constants import (
    COVER_MM,
    GAMMA_M_SHEAR,
    K_PRIME,
    LINK_BAR_AREAS,
    LINK_YIELD_STRENGTH,
    REBAR_AREAS,
    STEEL_YIELD_STRENGTH,
)
from src.fem.fem_engine import Element, ElementType, FEMModel, Node


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class StructuralClass(Enum):
    """Design check classification for FEM elements."""
    PRIMARY_BEAM = "primary_beam"
    SECONDARY_BEAM = "secondary_beam"
    COUPLING_BEAM = "coupling_beam"
    COLUMN = "column"
    SLAB_SHELL = "slab_shell"
    WALL_SHELL = "wall_shell"


def classify_element(model: FEMModel, elem_tag: int) -> StructuralClass:
    """Classify a frame element by its structural role.

    Rules (from phase-16 plan):
    - ElementType.SECONDARY_BEAM  → SECONDARY_BEAM
    - ElementType.COUPLING_BEAM   → COUPLING_BEAM
    - ElementType.ELASTIC_BEAM with parent_column_id → COLUMN
    - ElementType.ELASTIC_BEAM without                → PRIMARY_BEAM
    """
    elem = model.elements[elem_tag]

    if elem.element_type == ElementType.SECONDARY_BEAM:
        return StructuralClass.SECONDARY_BEAM

    if elem.element_type == ElementType.COUPLING_BEAM:
        return StructuralClass.COUPLING_BEAM

    if elem.element_type == ElementType.ELASTIC_BEAM:
        if elem.geometry.get("coupling_beam") or elem.geometry.get("parent_coupling_beam_id"):
            return StructuralClass.COUPLING_BEAM
        if "parent_column_id" in elem.geometry:
            return StructuralClass.COLUMN
        return StructuralClass.PRIMARY_BEAM

    raise ValueError(
        f"Element {elem_tag} has type {elem.element_type} which is not a frame element"
    )


def classify_shell_orientation(
    model: FEMModel, shell_elem_tag: int
) -> StructuralClass:
    """Classify a shell element as slab or wall by its plane normal.

    Derive unit normal from 3 corner nodes.
    If |n_z| >= 0.9  → slab (horizontal)
    Else             → wall (vertical)
    """
    elem = model.elements[shell_elem_tag]
    node_tags = elem.node_tags[:3]

    coords = []
    for nt in node_tags:
        n = model.nodes[nt]
        coords.append((n.x, n.y, n.z))

    # Two edge vectors
    v1 = (
        coords[1][0] - coords[0][0],
        coords[1][1] - coords[0][1],
        coords[1][2] - coords[0][2],
    )
    v2 = (
        coords[2][0] - coords[0][0],
        coords[2][1] - coords[0][1],
        coords[2][2] - coords[0][2],
    )

    # Cross product → normal
    nx = v1[1] * v2[2] - v1[2] * v2[1]
    ny = v1[2] * v2[0] - v1[0] * v2[2]
    nz = v1[0] * v2[1] - v1[1] * v2[0]

    mag = math.sqrt(nx * nx + ny * ny + nz * nz)
    if mag < 1e-12:
        raise ValueError(
            f"Shell {shell_elem_tag}: degenerate element (zero-area normal)"
        )

    nz_unit = abs(nz / mag)
    return StructuralClass.SLAB_SHELL if nz_unit >= 0.9 else StructuralClass.WALL_SHELL


# ---------------------------------------------------------------------------
# HK COP Check Primitives
# ---------------------------------------------------------------------------

@dataclass
class ShearCheckResult:
    """Result of concrete shear stress check per HK Code 2013."""
    v: float            # Applied shear stress (MPa)
    v_max: float        # Maximum allowable shear stress (MPa)
    ratio: float        # v / v_max  (>1.0 ⇒ FAIL)
    passed: bool
    note: str = ""


def shear_stress_check(
    V: float, b: float, d: float, fcu: float
) -> ShearCheckResult:
    """HK Code 2013 shear stress check.

    Args:
        V:   Shear force (N)
        b:   Width (mm)
        d:   Effective depth (mm)
        fcu: Characteristic cube strength (MPa)

    Returns:
        ShearCheckResult with v, v_max, ratio, passed.
    """
    if b <= 0 or d <= 0:
        return ShearCheckResult(
            v=0.0, v_max=0.0, ratio=0.0, passed=False,
            note="Invalid section dimensions"
        )

    v = V / (b * d)                              # MPa
    v_max = min(0.8 * math.sqrt(fcu), 7.0)       # MPa
    ratio = v / v_max if v_max > 0 else 0.0
    passed = ratio <= 1.0

    return ShearCheckResult(v=v, v_max=v_max, ratio=ratio, passed=passed)


@dataclass
class RhoCheckResult:
    """Result of reinforcement ratio check."""
    rho: float          # Provided/required ratio (%)
    rho_min: float      # Minimum ratio (%)
    rho_max: float      # Maximum ratio (%)
    passed: bool
    warnings: List[str] = field(default_factory=list)


# Default HK COP thresholds by element class
_RHO_LIMITS: Dict[StructuralClass, Tuple[float, float, float]] = {
    # (min%, max%, warn_if_above%)
    StructuralClass.PRIMARY_BEAM:   (0.3, 2.5, 2.5),
    StructuralClass.SECONDARY_BEAM: (0.3, 2.5, 2.5),
    StructuralClass.COUPLING_BEAM:  (0.3, 2.5, 2.5),
    StructuralClass.SLAB_SHELL:     (0.3, 4.0, 2.5),
    StructuralClass.COLUMN:         (0.8, 4.0, 4.0),
    StructuralClass.WALL_SHELL:     (0.25, 4.0, 4.0),
}


def rho_check(
    rho: float, element_class: StructuralClass
) -> RhoCheckResult:
    """Check reinforcement ratio against HK COP limits.

    Args:
        rho:            Provided/required reinforcement ratio (%)
        element_class:  StructuralClass of the element
    """
    rho_min, rho_max, warn_cap = _RHO_LIMITS.get(
        element_class, (0.3, 4.0, 2.5)
    )

    warnings: List[str] = []
    passed = True

    if rho < rho_min:
        warnings.append(f"ρ={rho:.2f}% < ρ_min={rho_min:.2f}%")
        passed = False

    if rho > rho_max:
        warnings.append(f"ρ={rho:.2f}% > ρ_max={rho_max:.2f}%")
        passed = False

    if rho > warn_cap and rho <= rho_max:
        warnings.append(f"ρ={rho:.2f}% exceeds warning cap {warn_cap:.2f}%")

    return RhoCheckResult(
        rho=rho, rho_min=rho_min, rho_max=rho_max,
        passed=passed, warnings=warnings,
    )


@dataclass
class DuctilityCheckResult:
    """Result of column/wall ductility check."""
    n_ratio: float      # N / (fcu * Ag)
    threshold: float    # 0.6
    passed: bool
    warnings: List[str] = field(default_factory=list)


def ductility_check(
    N: float, fcu: float, Ag: float, threshold: float = 0.6
) -> DuctilityCheckResult:
    """Column/wall axial load ratio check.

    Warns if N/(fcu·Ag) > threshold (default 0.6).

    Args:
        N:    Axial force (N)
        fcu:  Characteristic cube strength (MPa)
        Ag:   Gross cross-section area (mm²)
    """
    if fcu <= 0 or Ag <= 0:
        return DuctilityCheckResult(
            n_ratio=0.0, threshold=threshold, passed=False,
            warnings=["Invalid fcu or Ag"],
        )

    n_ratio = N / (fcu * Ag)
    passed = n_ratio <= threshold
    warnings: List[str] = []
    if not passed:
        warnings.append(
            f"N/(fcu·Ag) = {n_ratio:.3f} > {threshold} — ductility warning"
        )

    return DuctilityCheckResult(
        n_ratio=n_ratio, threshold=threshold,
        passed=passed, warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Beam Flexural Design (HK COP 2013 Cl 6.1.2.4)
# ---------------------------------------------------------------------------

@dataclass
class FlexuralCheckResult:
    """Result of beam flexural design per HK COP 2013."""
    M: float            # Applied moment (N-mm)
    K: float            # M / (fcu * b * d^2)
    K_prime: float      # Singly reinforced limit (0.156)
    z: float            # Lever arm (mm)
    As_req: float       # Required steel area (mm^2)
    rho: float          # Reinforcement ratio (%)
    rebar_suggestion: str  # e.g. "4T25 (1963 mm2)"
    is_doubly: bool     # True if K > K'
    passed: bool        # rho within HK COP limits


def beam_flexural_check(
    M: float,
    b: float,
    d: float,
    fcu: float,
    fy: float = STEEL_YIELD_STRENGTH,
) -> FlexuralCheckResult:
    """Flexural design of a rectangular beam per HK COP 2013 Cl 6.1.2.4.

    Args:
        M:   Applied moment (N-mm), positive.
        b:   Section width (mm).
        d:   Effective depth (mm).
        fcu: Characteristic cube strength (MPa).
        fy:  Steel yield strength (MPa), default 500.

    Returns:
        FlexuralCheckResult with As_req, rebar suggestion, and pass/fail.
    """
    if b <= 0 or d <= 0 or fcu <= 0 or M <= 0:
        return FlexuralCheckResult(
            M=M, K=0.0, K_prime=K_PRIME, z=0.0,
            As_req=0.0, rho=0.0, rebar_suggestion="N/A",
            is_doubly=False, passed=True,
        )

    K = M / (fcu * b * d * d)
    is_doubly = K > K_PRIME

    if is_doubly:
        # Use K' for singly reinforced limit; compression steel needed
        K_use = K_PRIME
    else:
        K_use = K

    z = d * (0.5 + math.sqrt(max(0.25 - K_use / 0.9, 0.0)))
    z = min(z, 0.95 * d)

    As_req = M / (0.87 * fy * z)

    if is_doubly:
        # Additional tension steel for doubly reinforced
        M_excess = M - K_PRIME * fcu * b * d * d
        d_prime = COVER_MM + 10  # assumed compression bar center
        As_comp = M_excess / (0.87 * fy * (d - d_prime))
        As_req += As_comp

    rho = As_req / (b * d) * 100.0

    # Check rho limits
    rho_result = rho_check(rho, StructuralClass.PRIMARY_BEAM)
    rebar_suggestion = suggest_rebar(As_req, b)

    return FlexuralCheckResult(
        M=M, K=K, K_prime=K_PRIME, z=z,
        As_req=As_req, rho=rho,
        rebar_suggestion=rebar_suggestion,
        is_doubly=is_doubly, passed=rho_result.passed,
    )


# ---------------------------------------------------------------------------
# Concrete Shear Capacity (HK COP 2013 Cl 6.1.2.5)
# ---------------------------------------------------------------------------

@dataclass
class ShearCapacityResult:
    """Result of concrete shear capacity check per HK COP 2013."""
    V: float            # Applied shear (N)
    vc: float           # Concrete shear stress capacity (MPa)
    v: float            # Applied shear stress (MPa)
    Vc: float           # Concrete shear capacity (N)
    Asv_sv_req: float   # Required Asv/sv (mm^2/mm), 0 if V <= Vc
    link_suggestion: str  # e.g. "T10@200"
    passed: bool        # v <= v_max


def concrete_shear_capacity(
    V: float,
    b: float,
    d: float,
    fcu: float,
    As_prov: float,
    fyv: float = LINK_YIELD_STRENGTH,
) -> ShearCapacityResult:
    """Concrete shear capacity and required links per HK COP 2013 Cl 6.1.2.5.

    Args:
        V:       Applied shear force (N).
        b:       Section width (mm).
        d:       Effective depth (mm).
        fcu:     Characteristic cube strength (MPa).
        As_prov: Provided tension steel area (mm^2) for vc calc.
        fyv:     Link yield strength (MPa), default 250.

    Returns:
        ShearCapacityResult with vc, required links, and pass/fail.
    """
    if b <= 0 or d <= 0 or fcu <= 0:
        return ShearCapacityResult(
            V=V, vc=0.0, v=0.0, Vc=0.0,
            Asv_sv_req=0.0, link_suggestion="N/A", passed=False,
        )

    v = V / (b * d)
    v_max = min(0.8 * math.sqrt(fcu), 7.0)

    # vc formula: HK COP Cl 6.1.2.5(c)
    rho_100 = max(100.0 * As_prov / (b * d), 0.15)  # clamp low end
    rho_100 = min(rho_100, 3.0)  # clamp high end per code
    depth_factor = max((400.0 / d) ** 0.25, 0.67)  # (400/d)^1/4, min 0.67 for d>400
    fcu_factor = min((fcu / 25.0) ** (1.0 / 3.0), 1.587)  # capped at fcu=100

    vc = 0.79 * (rho_100 ** (1.0 / 3.0)) * depth_factor * fcu_factor / GAMMA_M_SHEAR
    Vc = vc * b * d

    Asv_sv_req = 0.0
    if V > Vc:
        Asv_sv_req = (V - Vc) / (0.87 * fyv * d)

    # Minimum links: Asv/sv >= 0.4*b / (0.87*fyv)
    Asv_sv_min = 0.4 * b / (0.87 * fyv)
    Asv_sv_req = max(Asv_sv_req, Asv_sv_min)

    link_suggestion = suggest_links(Asv_sv_req, b)
    passed = v <= v_max

    return ShearCapacityResult(
        V=V, vc=vc, v=v, Vc=Vc,
        Asv_sv_req=Asv_sv_req,
        link_suggestion=link_suggestion, passed=passed,
    )


# ---------------------------------------------------------------------------
# Rebar Suggestion Helpers
# ---------------------------------------------------------------------------

def suggest_rebar(As_req: float, b: float, cover: float = COVER_MM) -> str:
    """Suggest a rebar arrangement that provides As_req within beam width.

    Args:
        As_req: Required steel area (mm^2).
        b:      Section width (mm).
        cover:  Nominal cover (mm).

    Returns:
        String like "4T25 (1963 mm2)" or "N/A" if nothing fits.
    """
    if As_req <= 0:
        return "N/A"

    available_width = b - 2 * cover
    if available_width <= 0:
        return "N/A"

    # Try bar sizes from large to small for efficiency
    for bar_name in ("T40", "T32", "T25", "T20", "T16", "T12", "T10"):
        area = REBAR_AREAS[bar_name]
        dia = float(bar_name[1:])
        n = math.ceil(As_req / area)
        if n < 2:
            n = 2
        min_spacing = max(dia, 25.0)
        required_width = n * dia + (n - 1) * min_spacing
        if required_width <= available_width:
            total_area = n * area
            return f"{n}{bar_name} ({total_area:.0f} mm2)"

    return "N/A"


def suggest_links(Asv_sv_req: float, b: float) -> str:
    """Suggest link spacing for a given Asv/sv requirement.

    Args:
        Asv_sv_req: Required Asv/sv (mm^2/mm).
        b:          Section width (mm).

    Returns:
        String like "T10@200" or "N/A".
    """
    if Asv_sv_req <= 0:
        return "N/A"

    n_legs = 2  # standard 2-leg links
    for bar_name in ("T10", "T12", "T8"):
        area_per_leg = LINK_BAR_AREAS[bar_name]
        Asv = n_legs * area_per_leg
        sv = Asv / Asv_sv_req
        # Round down to nearest 25mm, clamp between 75 and 300
        sv = max(75, min(int(sv / 25) * 25, 300))
        if sv >= 75:
            return f"{bar_name}@{sv}"

    return "N/A"


# ---------------------------------------------------------------------------
# Governing Element Selection (Top-N)
# ---------------------------------------------------------------------------

@dataclass
class GoverningItem:
    """Compact summary of a governing element."""
    element_id: int
    element_class: StructuralClass
    governing_score: float
    governing_combo: str = ""
    key_metric: str = ""     # e.g. "v/v_max=0.85"
    warnings: List[str] = field(default_factory=list)


def compute_governing_score(
    shear_ratio: float = 0.0,
    rho_ratio: float = 0.0,
    deflection_ratio: float = 0.0,
    n_ratio: float = 0.0,
) -> float:
    """Compute a single governing score as the max of all utilisation ratios.

    All inputs should be dimensionless ratios (demand/capacity).
    """
    return max(shear_ratio, rho_ratio, deflection_ratio, n_ratio)


def select_top_n(
    items: List[GoverningItem], n: int = 3
) -> List[GoverningItem]:
    """Pick top-N governing items sorted by score descending."""
    return sorted(items, key=lambda it: it.governing_score, reverse=True)[:n]


# ---------------------------------------------------------------------------
# Slab Strip Checks (Gate E)
# ---------------------------------------------------------------------------

@dataclass
class SlabStripCheckResult:
    """Result of a 1m-wide slab strip design check."""
    element_id: int
    strip_width_mm: float       # always 1000 mm
    shear_check: ShearCheckResult
    rho_result: RhoCheckResult
    governing_score: float
    governing_combo: str = ""
    warnings: List[str] = field(default_factory=list)


def slab_strip_check(
    element_id: int,
    V_per_m: float,
    M_per_m: float,
    d: float,
    fcu: float,
    rho_provided: float,
    governing_combo: str = "",
) -> SlabStripCheckResult:
    """Check a 1m-wide slab strip per HK Code 2013.

    Args:
        element_id:     Element tag for identification
        V_per_m:        Shear force per metre run of slab (N/m)
        M_per_m:        Bending moment per metre run (N·mm/m) — not used directly
                        but kept for future flex-check expansion
        d:              Effective depth (mm)
        fcu:            Characteristic cube strength (MPa)
        rho_provided:   Provided reinforcement ratio (%)
        governing_combo: Name of the governing load combination
    """
    b = 1000.0  # mm — unit-width strip
    shear = shear_stress_check(V_per_m, b, d, fcu)
    rho = rho_check(rho_provided, StructuralClass.SLAB_SHELL)
    score = compute_governing_score(shear_ratio=shear.ratio)

    warnings: List[str] = list(rho.warnings)
    if not shear.passed:
        warnings.append(f"Slab strip shear v/v_max={shear.ratio:.2f}")

    return SlabStripCheckResult(
        element_id=element_id,
        strip_width_mm=b,
        shear_check=shear,
        rho_result=rho,
        governing_score=score,
        governing_combo=governing_combo,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Wall Checks (Gate F)
# ---------------------------------------------------------------------------

@dataclass
class WallCheckResult:
    """Result of a wall design check (axial + in-plane bending)."""
    element_id: int
    shear_check: ShearCheckResult
    ductility_result: DuctilityCheckResult
    rho_result: RhoCheckResult
    governing_score: float
    governing_combo: str = ""
    warnings: List[str] = field(default_factory=list)


def wall_check(
    element_id: int,
    N: float,
    V: float,
    b: float,
    d: float,
    fcu: float,
    Ag: float,
    rho_provided: float,
    governing_combo: str = "",
) -> WallCheckResult:
    """Check a wall element per HK Code 2013 (N/M envelope approach).

    Args:
        element_id:     Element tag for identification
        N:              Axial force (N)
        V:              In-plane shear force (N)
        b:              Wall thickness (mm)
        d:              Effective depth — wall length × 0.8 (mm)
        fcu:            Characteristic cube strength (MPa)
        Ag:             Gross section area (mm²)
        rho_provided:   Vertical reinforcement ratio (%)
        governing_combo: Name of the governing load combination
    """
    shear = shear_stress_check(V, b, d, fcu)
    duct = ductility_check(N, fcu, Ag)
    rho = rho_check(rho_provided, StructuralClass.WALL_SHELL)

    score = compute_governing_score(
        shear_ratio=shear.ratio,
        n_ratio=duct.n_ratio / duct.threshold if duct.threshold > 0 else 0,
    )

    warnings: List[str] = list(rho.warnings) + list(duct.warnings)
    if not shear.passed:
        warnings.append(f"Wall shear v/v_max={shear.ratio:.2f}")

    return WallCheckResult(
        element_id=element_id,
        shear_check=shear,
        ductility_result=duct,
        rho_result=rho,
        governing_score=score,
        governing_combo=governing_combo,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Coupling Beam Checks (Gate G)
# ---------------------------------------------------------------------------

@dataclass
class CouplingBeamCheckResult:
    """Result of a coupling beam design check."""
    element_id: int
    shear_check: ShearCheckResult
    rho_result: RhoCheckResult
    span_depth_ratio: float
    governing_score: float
    governing_combo: str = ""
    warnings: List[str] = field(default_factory=list)


def coupling_beam_check(
    element_id: int,
    V: float,
    b: float,
    d: float,
    fcu: float,
    span: float,
    rho_provided: float,
    governing_combo: str = "",
) -> CouplingBeamCheckResult:
    """Check a coupling beam per HK Code 2013.

    Args:
        element_id:     Element tag
        V:              Shear force (N)
        b:              Width (mm)
        d:              Effective depth (mm)
        fcu:            Characteristic cube strength (MPa)
        span:           Clear span (mm)
        rho_provided:   Longitudinal reinforcement ratio (%)
        governing_combo: Governing load combination name
    """
    shear = shear_stress_check(V, b, d, fcu)
    rho = rho_check(rho_provided, StructuralClass.COUPLING_BEAM)
    span_depth = span / d if d > 0 else 0.0

    score = compute_governing_score(shear_ratio=shear.ratio)

    warnings: List[str] = list(rho.warnings)
    if not shear.passed:
        warnings.append(f"Coupling beam shear v/v_max={shear.ratio:.2f}")
    if span_depth < 2.0:
        warnings.append(
            f"l/d={span_depth:.1f} < 2.0 — deep coupling beam, "
            "diagonal reinforcement may be required"
        )

    return CouplingBeamCheckResult(
        element_id=element_id,
        shear_check=shear,
        rho_result=rho,
        span_depth_ratio=span_depth,
        governing_score=score,
        governing_combo=governing_combo,
        warnings=warnings,
    )

