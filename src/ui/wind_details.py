"""Helpers for rendering Gate H wind detail data."""

from typing import Dict

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


def build_wind_details_dataframe(wind_result: WindResult) -> pd.DataFrame:
    """Build per-floor wind load table for read-only UI views."""
    if not has_complete_floor_wind_data(wind_result):
        raise ValueError("Per-floor wind arrays are empty or inconsistent")

    floor_count = len(wind_result.floor_elevations)
    return pd.DataFrame(
        {
            "Floor": list(range(1, floor_count + 1)),
            "Elevation (m)": wind_result.floor_elevations,
            "Wx (kN)": wind_result.floor_wind_x,
            "Wy (kN)": wind_result.floor_wind_y,
            "Wtz (kNm)": wind_result.floor_torsion_z,
        }
    )


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
