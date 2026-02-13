import pytest

from src.core.data_models import CoreLocationPreset, CoreWallConfig, TubeOpeningPlacement
from src.ui.project_builder import (
    _normalize_core_wall_config,
    _normalize_location_preset,
    _normalize_opening_placement,
)


def test_normalize_core_wall_config_rejects_removed_legacy_variant():
    with pytest.raises(ValueError, match="no longer supported"):
        _normalize_core_wall_config("two_c_facing")


def test_normalize_core_wall_config_accepts_supported_values():
    assert _normalize_core_wall_config("i_section") == CoreWallConfig.I_SECTION
    assert _normalize_core_wall_config("TUBE_WITH_OPENINGS") == CoreWallConfig.TUBE_WITH_OPENINGS


def test_normalize_location_preset_maps_legacy_custom_to_nearest_preset():
    mapped = _normalize_location_preset(
        raw_location="custom",
        total_width_x=24.0,
        total_width_y=24.0,
        length_x=6.0,
        length_y=6.0,
        custom_x=20.0,
        custom_y=20.0,
    )
    assert mapped == CoreLocationPreset.NORTHEAST


def test_normalize_location_preset_tie_break_prefers_center():
    mapped = _normalize_location_preset(
        raw_location="custom",
        total_width_x=24.0,
        total_width_y=24.0,
        length_x=6.0,
        length_y=6.0,
        custom_x=12.0,
        custom_y=15.0,
    )
    assert mapped == CoreLocationPreset.CENTER


def test_normalize_opening_placement_maps_legacy_to_top_bot_and_none():
    assert _normalize_opening_placement("top") == TubeOpeningPlacement.TOP_BOT
    assert _normalize_opening_placement("bottom") == TubeOpeningPlacement.TOP_BOT
    assert _normalize_opening_placement("both") == TubeOpeningPlacement.TOP_BOT
    assert _normalize_opening_placement("Top-Bot") == TubeOpeningPlacement.TOP_BOT
    assert _normalize_opening_placement("none") == TubeOpeningPlacement.NONE
    assert _normalize_opening_placement("invalid") == TubeOpeningPlacement.TOP_BOT
