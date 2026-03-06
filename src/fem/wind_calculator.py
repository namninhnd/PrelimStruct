"""HK COP 2019 Wind Effects calculator.

Implements height-dependent wind pressure and force distribution per:
  - Eq 3-2: Q_o,z = 3.7 × (Z / 500)^0.16  (reference pressure at height Z)
  - Eq 5-2: S_q,z full formula (H ≥ 50 m)
  - Eq 5-3: S_q,z simplified formula (H < 50 m)
  - Eq 2-1: W_z = Q_z × Cf × S_q,z × B  (along-wind force per unit height)

Reference: Code of Practice on Wind Effects in Hong Kong 2019, BD HKSAR.
"""

from __future__ import annotations

import math
from typing import List

from src.core.data_models import TerrainCategory, WindResult


# ---------------------------------------------------------------------------
# HK COP 2019 Core Formulas
# ---------------------------------------------------------------------------


def _Qoz(z: float) -> float:
    """Reference wind pressure at effective height *z* (Eq 3-2, Table 3-1).

    Args:
        z: Effective height in metres (clamped to ≥ 2.5 m).

    Returns:
        Q_o,z in kPa.
    """
    z_eff = max(z, 2.5)
    return 3.7 * (z_eff / 500.0) ** 0.16


def _Sqz_simplified(H: float, B: float) -> float:
    """Simplified size & dynamic factor for H < 50 m (Eq 5-3).

    This returns a **constant** value (no Z-dependence).

    Args:
        H: Total building height (m).
        B: Breadth of building perpendicular to wind (m).

    Returns:
        S_q (dimensionless).
    """
    Lp = H / 1.5 + 2.0 * B
    Sb_sq = 1.0 / (1.0 + (36.0 * H * H + 64.0 * B * B) / (Lp * Lp))
    Sb = math.sqrt(max(Sb_sq, 0.0))
    return 1.1 * Sb


def _Sqz_full(z: float, H: float, Sq_h: float) -> float:
    """Full size & dynamic factor for H ≥ 50 m (Eq 5-2).

    Varies linearly from a reduced value at the base to S_q,h at the top.

    Args:
        z: Height under consideration (m).
        H: Total building height (m).
        Sq_h: S_q,z evaluated at the building top.

    Returns:
        S_q,z (dimensionless).
    """
    if H <= 0.0:
        return Sq_h
    base_term = (10.0 / H) ** 0.14
    return Sq_h - 1.2 * (Sq_h - base_term) * (1.0 - z / H)


# ---------------------------------------------------------------------------
# Legacy terrain factor (kept for backward-compat display only)
# ---------------------------------------------------------------------------

TERRAIN_FACTORS = {
    TerrainCategory.OPEN_SEA: 1.0,
    TerrainCategory.OPEN_COUNTRY: 0.85,
    TerrainCategory.URBAN: 0.72,
    TerrainCategory.CITY_CENTRE: 0.60,
}

TERRAIN_NAMES = {
    TerrainCategory.OPEN_SEA: "Open Sea",
    TerrainCategory.OPEN_COUNTRY: "Open Country",
    TerrainCategory.URBAN: "Urban",
    TerrainCategory.CITY_CENTRE: "City Centre",
}


# ---------------------------------------------------------------------------
# Main Calculator
# ---------------------------------------------------------------------------


def calculate_hk_wind(
    total_height: float,
    building_width_x: float,
    building_width_y: float,
    terrain: TerrainCategory,
    force_coefficient: float = 1.3,
    topography_factor: float = 1.0,
    directionality_factor: float = 1.0,
    num_floors: int = 0,
    story_height: float = 0.0,
) -> WindResult:
    """Calculate wind loads per HK COP 2019 Wind Effects.

    Wind in X direction acts on the Y-face (area = H × B_y).
    Wind in Y direction acts on the X-face (area = H × B_x).

    Args:
        total_height: Building height (m).
        building_width_x: Total building width in X direction (m).
        building_width_y: Total building width in Y direction (m).
        terrain: Terrain category (retained for traceability).
        force_coefficient: Cf aerodynamic shape coefficient.
        topography_factor: S_t (default 1.0 for flat terrain).
        directionality_factor: S_θ (default 1.0 for all directions).
        num_floors: Number of floors (0 = skip per-floor breakdown).
        story_height: Typical storey height (m).

    Returns:
        WindResult with per-floor breakdown.
    """
    # Guard: invalid geometry
    if total_height <= 0.0 or building_width_x <= 0.0 or building_width_y <= 0.0:
        return WindResult(
            code_reference="HK COP Wind Effects 2019 - Invalid geometry (zero dimensions)",
            topography_factor=topography_factor,
            directionality_factor=directionality_factor,
            force_coefficient=force_coefficient,
        )

    # Legacy terrain factor (for backward-compatible display)
    sz = TERRAIN_FACTORS.get(terrain, TERRAIN_FACTORS[TerrainCategory.URBAN])
    terrain_name = TERRAIN_NAMES.get(terrain, "Urban")

    # Per-floor breakdown
    floor_elevations: List[float] = []
    floor_wind_x: List[float] = []
    floor_wind_y: List[float] = []
    floor_torsion_z: List[float] = []
    floor_Qoz: List[float] = []
    floor_Sqz: List[float] = []

    # Determine S_q,z strategy
    use_full_Sqz = total_height >= 50.0

    # For Eq 5-2 we need S_q,h (factor at building top).
    # Approximate S_q,h using the simplified formula evaluated at H.
    # This is the common engineering approach when detailed dynamic
    # parameters are not available.
    Sq_h = _Sqz_simplified(total_height, max(building_width_x, building_width_y))

    if num_floors > 0 and story_height > 0.0:
        for floor_idx in range(num_floors):
            elevation = (floor_idx + 1) * story_height
            floor_elevations.append(elevation)

            # Eq 3-2: Reference pressure at this floor height
            qoz = _Qoz(elevation)
            floor_Qoz.append(round(qoz, 4))

            # Design pressure with adjustment factors
            qz = qoz * topography_factor * directionality_factor

            # S_q,z at this floor
            if use_full_Sqz:
                sqz = _Sqz_full(elevation, total_height, Sq_h)
            else:
                sqz = Sq_h  # constant for H < 50 m
            floor_Sqz.append(round(sqz, 4))

            # Eq 2-1: force = Q_z × Cf × S_q,z × breadth × storey_height
            # Wind-X acts on Y-face
            floor_wx = qz * force_coefficient * sqz * building_width_y * story_height
            floor_wind_x.append(round(floor_wx, 4))

            # Wind-Y acts on X-face
            floor_wy = qz * force_coefficient * sqz * building_width_x * story_height
            floor_wind_y.append(round(floor_wy, 4))

            # Torsion: accidental eccentricity = 0.05 × max plan dimension
            eccentricity = 0.05 * max(building_width_x, building_width_y)
            floor_wtz = max(floor_wx, floor_wy) * eccentricity
            floor_torsion_z.append(round(floor_wtz, 4))

    # Aggregate totals
    base_shear_x = round(sum(floor_wind_x), 2) if floor_wind_x else 0.0
    base_shear_y = round(sum(floor_wind_y), 2) if floor_wind_y else 0.0
    otm_x = sum(fx * z for fx, z in zip(floor_wind_x, floor_elevations)) if floor_wind_x else 0.0
    otm_y = sum(fy * z for fy, z in zip(floor_wind_y, floor_elevations)) if floor_wind_y else 0.0

    # Code reference string
    sqz_eq = "Eq 5-2" if use_full_Sqz else "Eq 5-3"
    code_ref = (
        f"HK COP Wind Effects 2019 | "
        f"Terrain: {terrain_name} | "
        f"Cf={force_coefficient:.2f} | "
        f"St={topography_factor:.2f} | "
        f"Sθ={directionality_factor:.2f} | "
        f"Sq,z: {sqz_eq}"
    )

    return WindResult(
        base_shear=max(base_shear_x, base_shear_y),
        base_shear_x=round(base_shear_x, 2),
        base_shear_y=round(base_shear_y, 2),
        overturning_moment=round(max(otm_x, otm_y), 2),
        reference_pressure=0.0,
        lateral_system="CORE_WALL",
        code_reference=code_ref,
        terrain_factor=sz,
        force_coefficient=force_coefficient,
        design_pressure=0.0,
        topography_factor=topography_factor,
        directionality_factor=directionality_factor,
        floor_elevations=floor_elevations,
        floor_wind_x=floor_wind_x,
        floor_wind_y=floor_wind_y,
        floor_torsion_z=floor_torsion_z,
        floor_Qoz=floor_Qoz,
        floor_Sqz=floor_Sqz,
    )
