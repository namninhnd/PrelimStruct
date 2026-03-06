from pathlib import Path

import pytest

from src.core.data_models import TerrainCategory, WindResult
from src.fem.wind_calculator import calculate_hk_wind
from src.ui.wind_details import (
    build_wind_details_dataframe,
    build_wind_details_summary,
    has_complete_floor_wind_data,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_wind_details_dataframe_has_expected_columns_and_floor_numbers() -> None:
    result = calculate_hk_wind(
        total_height=30.0,
        building_width_x=20.0,
        building_width_y=20.0,
        terrain=TerrainCategory.URBAN,
        num_floors=10,
        story_height=3.0,
    )

    df = build_wind_details_dataframe(result)
    # HK COP 2019: includes Qo,z and Sq,z traceability columns
    expected_cols = [
        "Floor", "Elevation (m)", "Qo,z (kPa)", "Sq,z",
        "Wx (kN)", "Wy (kN)", "Wtz (kNm)",
    ]
    assert list(df.columns) == expected_cols
    assert len(df) == 10
    assert df["Floor"].iloc[0] == 1
    assert df["Floor"].iloc[-1] == 10


def test_wind_details_dataframe_without_traceability() -> None:
    """Manual mode WindResult has no Qo,z/Sq,z → only basic columns."""
    manual_result = WindResult(
        floor_elevations=[3.0, 6.0],
        floor_wind_x=[10.0, 12.0],
        floor_wind_y=[15.0, 18.0],
        floor_torsion_z=[1.0, 1.2],
        # No floor_Qoz/floor_Sqz
    )
    df = build_wind_details_dataframe(manual_result)
    assert "Qo,z (kPa)" not in df.columns
    assert "Sq,z" not in df.columns


def test_wind_details_summary_matches_calculated_base_shears() -> None:
    result = calculate_hk_wind(
        total_height=30.0,
        building_width_x=30.0,
        building_width_y=10.0,
        terrain=TerrainCategory.OPEN_COUNTRY,
        num_floors=10,
        story_height=3.0,
    )

    summary = build_wind_details_summary(result)
    # Allow rounding tolerance (base_shear_x/y rounded to 2dp, sum from 4dp values)
    assert summary["sum_wx"] == pytest.approx(result.base_shear_x, abs=0.1)
    assert summary["sum_wy"] == pytest.approx(result.base_shear_y, abs=0.1)
    assert summary["terrain_factor"] == pytest.approx(0.85)


def test_wind_details_helper_rejects_inconsistent_per_floor_arrays() -> None:
    inconsistent = WindResult(
        floor_elevations=[3.0, 6.0],
        floor_wind_x=[10.0],
        floor_wind_y=[10.0, 10.0],
        floor_torsion_z=[1.0, 1.0],
    )

    assert not has_complete_floor_wind_data(inconsistent)
    with pytest.raises(ValueError):
        build_wind_details_dataframe(inconsistent)


def test_gate_h_ui_rendering_markers_present_in_app_and_fem_views() -> None:
    app_text = _read("app.py")
    fem_views_text = _read("src/ui/views/fem_views.py")

    # app.py imports the wind detail helpers
    assert "build_wind_details_dataframe" in app_text
    assert "build_wind_details_summary" in app_text

    # fem_views.py has the display markers
    assert "Wind Loads (Read-only)" in fem_views_text
    assert "Calculation Traceability" in fem_views_text
    assert "build_wind_details_dataframe" in fem_views_text
