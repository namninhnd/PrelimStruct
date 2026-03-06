"""Helpers for rendering Gate H wind detail data."""

from typing import Dict, List

import pandas as pd

from src.core.data_models import WindResult


def has_complete_floor_wind_data(wind_result: WindResult) -> bool:
    """Return True when per-floor wind arrays are present and aligned."""
    lengths = (
        len(wind_result.floor_elevations),
        len(wind_result.floor_wind_x),
        len(wind_result.floor_wind_y),
        len(wind_result.floor_torsion_z),
    )
    return lengths[0] > 0 and all(length == lengths[0] for length in lengths)


def _has_hk_cop_traceability(wind_result: WindResult) -> bool:
    """Return True when HK COP 2019 per-floor traceability arrays are present."""
    n = len(wind_result.floor_elevations)
    return (
        n > 0
        and len(wind_result.floor_Qoz) == n
        and len(wind_result.floor_Sqz) == n
    )


def build_wind_details_dataframe(wind_result: WindResult) -> pd.DataFrame:
    """Build per-floor wind load table for read-only UI views."""
    if not has_complete_floor_wind_data(wind_result):
        raise ValueError("Per-floor wind arrays are empty or inconsistent")

    floor_count = len(wind_result.floor_elevations)
    data: Dict[str, List] = {
        "Floor": list(range(1, floor_count + 1)),
        "Elevation (m)": wind_result.floor_elevations,
    }

    # HK COP 2019 traceability columns (if available)
    if _has_hk_cop_traceability(wind_result):
        data["Qo,z (kPa)"] = [round(v, 2) for v in wind_result.floor_Qoz]
        data["Sq,z"] = [round(v, 3) for v in wind_result.floor_Sqz]

    data["Wx (kN)"] = [round(v, 1) for v in wind_result.floor_wind_x]
    data["Wy (kN)"] = [round(v, 1) for v in wind_result.floor_wind_y]
    data["Wtz (kNm)"] = [round(v, 1) for v in wind_result.floor_torsion_z]

    return pd.DataFrame(data)


def build_wind_details_summary(wind_result: WindResult) -> Dict[str, float]:
    """Build summary values displayed under the per-floor wind table."""
    return {
        "total_floors": float(len(wind_result.floor_elevations)),
        "sum_wx": float(sum(wind_result.floor_wind_x)),
        "sum_wy": float(sum(wind_result.floor_wind_y)),
        "terrain_factor": float(wind_result.terrain_factor),
        "force_coefficient": float(wind_result.force_coefficient),
        "design_pressure": float(wind_result.design_pressure),
    }
