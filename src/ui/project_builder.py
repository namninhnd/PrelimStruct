"""Project builder module - builds ProjectData from sidebar inputs."""

import logging
from typing import Dict, Any, Optional, List, Tuple

from src.core.data_models import (
    ProjectData,
    GeometryInput,
    LoadInput,
    MaterialInput,
    LateralInput,
    TerrainCategory,
    CoreWallConfig,
    CoreWallGeometry,
    CoreLocationPreset,
    TubeOpeningPlacement,
    LoadCombination,
    ExposureClass,
    SlabResult,
    BeamResult,
    ColumnResult,
)
from src.core.constants import CONCRETE_DENSITY
from src.fem.core_wall_helpers import calculate_core_wall_properties


logger = logging.getLogger(__name__)

_REMOVED_LEGACY_CORE_WALL_VARIANTS = {
    "two_c_facing",
    "two_c_back_to_back",
    "tube_center_opening",
    "tube_side_opening",
}

_LEGACY_CUSTOM_LOCATION_TIE_BREAK_ORDER = [
    CoreLocationPreset.CENTER,
    CoreLocationPreset.NORTH,
    CoreLocationPreset.EAST,
    CoreLocationPreset.SOUTH,
    CoreLocationPreset.WEST,
    CoreLocationPreset.NORTHEAST,
    CoreLocationPreset.SOUTHEAST,
    CoreLocationPreset.SOUTHWEST,
    CoreLocationPreset.NORTHWEST,
]


def _normalize_core_wall_config(raw_config: Any) -> CoreWallConfig:
    if isinstance(raw_config, CoreWallConfig):
        return raw_config

    if isinstance(raw_config, str):
        token = raw_config.strip()
        if not token:
            raise ValueError("Core wall configuration cannot be empty")

        lowered = token.lower()
        if lowered in _REMOVED_LEGACY_CORE_WALL_VARIANTS:
            raise ValueError(
                "Legacy core wall variant '"
                f"{raw_config}' is no longer supported. "
                "Use 'i_section' or 'tube_with_openings'."
            )

        for config in CoreWallConfig:
            if lowered in (config.value.lower(), config.name.lower()):
                return config

    raise ValueError(
        f"Invalid core wall configuration: {raw_config!r}. "
        "Supported values are 'i_section' and 'tube_with_openings'."
    )


def _resolve_core_dims_m(
    total_width_x: float,
    total_width_y: float,
    length_x: Optional[float],
    length_y: Optional[float],
) -> Tuple[float, float]:
    resolved_x = length_x if length_x and length_x > 0 else max(total_width_x * 0.5, 0.1)
    resolved_y = length_y if length_y and length_y > 0 else max(total_width_y * 0.5, 0.1)
    return resolved_x, resolved_y


def _compute_preset_centers(
    total_width_x: float,
    total_width_y: float,
    core_width: float,
    core_height: float,
) -> Dict[CoreLocationPreset, Tuple[float, float]]:
    edge_clearance = 0.5

    min_x = edge_clearance + core_width / 2.0
    max_x = total_width_x - edge_clearance - core_width / 2.0
    min_y = edge_clearance + core_height / 2.0
    max_y = total_width_y - edge_clearance - core_height / 2.0

    if min_x > max_x:
        min_x = max_x = total_width_x / 2.0
    if min_y > max_y:
        min_y = max_y = total_width_y / 2.0

    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0

    return {
        CoreLocationPreset.CENTER: (total_width_x / 2.0, total_width_y / 2.0),
        CoreLocationPreset.NORTH: (mid_x, max_y),
        CoreLocationPreset.EAST: (max_x, mid_y),
        CoreLocationPreset.SOUTH: (mid_x, min_y),
        CoreLocationPreset.WEST: (min_x, mid_y),
        CoreLocationPreset.NORTHEAST: (max_x, max_y),
        CoreLocationPreset.SOUTHEAST: (max_x, min_y),
        CoreLocationPreset.SOUTHWEST: (min_x, min_y),
        CoreLocationPreset.NORTHWEST: (min_x, max_y),
    }


def _nearest_preset_for_custom_center(
    custom_x: float,
    custom_y: float,
    preset_centers: Dict[CoreLocationPreset, Tuple[float, float]],
) -> CoreLocationPreset:
    best_preset = _LEGACY_CUSTOM_LOCATION_TIE_BREAK_ORDER[0]
    best_distance_sq = float("inf")

    for preset in _LEGACY_CUSTOM_LOCATION_TIE_BREAK_ORDER:
        target_x, target_y = preset_centers[preset]
        dx = custom_x - target_x
        dy = custom_y - target_y
        distance_sq = dx * dx + dy * dy
        if distance_sq < best_distance_sq:
            best_distance_sq = distance_sq
            best_preset = preset

    return best_preset


def _normalize_location_preset(
    raw_location: Any,
    total_width_x: float,
    total_width_y: float,
    length_x: Optional[float],
    length_y: Optional[float],
    custom_x: Optional[float],
    custom_y: Optional[float],
) -> CoreLocationPreset:
    if isinstance(raw_location, CoreLocationPreset):
        return raw_location

    if isinstance(raw_location, str):
        token = raw_location.strip()
        if token:
            lowered = token.lower()
            if lowered == "custom":
                if custom_x is None or custom_y is None:
                    logger.warning(
                        "Legacy custom core location was provided without coordinates; "
                        "defaulting to CENTER."
                    )
                    return CoreLocationPreset.CENTER

                core_width, core_height = _resolve_core_dims_m(
                    total_width_x, total_width_y, length_x, length_y
                )
                preset_centers = _compute_preset_centers(
                    total_width_x, total_width_y, core_width, core_height
                )
                mapped = _nearest_preset_for_custom_center(custom_x, custom_y, preset_centers)
                logger.warning(
                    "Legacy custom core location mapped to preset '%s' (x=%.3f, y=%.3f).",
                    mapped.value,
                    custom_x,
                    custom_y,
                )
                return mapped

            for preset in CoreLocationPreset:
                if lowered in (preset.value.lower(), preset.name.lower()):
                    return preset

    logger.warning(
        "Invalid core location '%s'; defaulting to CENTER.",
        raw_location,
    )
    return CoreLocationPreset.CENTER


def _normalize_opening_placement(raw_placement: Any) -> TubeOpeningPlacement:
    if isinstance(raw_placement, TubeOpeningPlacement):
        placement = raw_placement
    elif isinstance(raw_placement, str):
        token = raw_placement.strip().lower().replace("_", "-")
        if token in {"none", "no-opening", "no opening"}:
            return TubeOpeningPlacement.NONE
        if token in {"top-bot", "both", "top", "bottom"}:
            return TubeOpeningPlacement.TOP_BOT
        placement = TubeOpeningPlacement.TOP_BOT
    else:
        placement = TubeOpeningPlacement.TOP_BOT

    if placement in {
        TubeOpeningPlacement.TOP,
        TubeOpeningPlacement.BOTTOM,
        TubeOpeningPlacement.BOTH,
    }:
        return TubeOpeningPlacement.TOP_BOT

    if placement == TubeOpeningPlacement.NONE:
        return TubeOpeningPlacement.NONE

    return TubeOpeningPlacement.TOP_BOT


def build_project_from_inputs(
    inputs: Dict[str, Any],
    project: Optional[ProjectData] = None
) -> ProjectData:
    """Build or update ProjectData from sidebar inputs.
    
    Args:
        inputs: Dict from render_sidebar() containing all user inputs
        project: Existing ProjectData to update, or None to create new
        
    Returns:
        Updated ProjectData
    """
    if project is None:
        project = ProjectData()
    
    # Build geometry
    project.geometry = GeometryInput(
        bay_x=inputs.get("bay_x", 8.0),
        bay_y=inputs.get("bay_y", 8.0),
        num_bays_x=inputs.get("num_bays_x", 3),
        num_bays_y=inputs.get("num_bays_y", 3),
        floors=inputs.get("floors", 10),
        story_height=inputs.get("story_height", 3.5),
    )
    
    # Build loads
    project.loads = LoadInput(
        live_load_class=inputs.get("selected_class", "2"),
        live_load_sub=inputs.get("selected_sub", "2.5"),
        dead_load=inputs.get("dead_load", 1.5),
        custom_live_load=inputs.get("custom_live_load_value"),
    )
    
    # Build materials
    project.materials = MaterialInput(
        fcu_slab=inputs.get("fcu_slab", 35),
        fcu_beam=inputs.get("fcu_beam", 45),
        fcu_column=inputs.get("fcu_column", 55),
        exposure=inputs.get("selected_exposure", ExposureClass.MODERATE),
    )

    # Section properties (optional overrides for FEM model)
    override_slab = inputs.get("override_slab_thickness", 0)
    if override_slab and override_slab > 0:
        thickness_m = override_slab / 1000.0
        project.slab_result = SlabResult(
            element_type="Slab",
            size=f"{int(override_slab)} mm",
            thickness=override_slab,
            self_weight=thickness_m * CONCRETE_DENSITY,
        )

    override_pri_w = inputs.get("override_pri_beam_width", 0)
    override_pri_d = inputs.get("override_pri_beam_depth", 0)
    if (override_pri_w and override_pri_w > 0) or (override_pri_d and override_pri_d > 0):
        width = override_pri_w if override_pri_w > 0 else (project.primary_beam_result.width if project.primary_beam_result else 0)
        depth = override_pri_d if override_pri_d > 0 else (project.primary_beam_result.depth if project.primary_beam_result else 0)
        project.primary_beam_result = BeamResult(
            element_type="Primary Beam",
            size=f"{int(width)} x {int(depth)} mm",
            width=width,
            depth=depth,
        )

    override_sec_w = inputs.get("override_sec_beam_width", 0)
    override_sec_d = inputs.get("override_sec_beam_depth", 0)
    if (override_sec_w and override_sec_w > 0) or (override_sec_d and override_sec_d > 0):
        width = override_sec_w if override_sec_w > 0 else (project.secondary_beam_result.width if project.secondary_beam_result else 0)
        depth = override_sec_d if override_sec_d > 0 else (project.secondary_beam_result.depth if project.secondary_beam_result else 0)
        project.secondary_beam_result = BeamResult(
            element_type="Secondary Beam",
            size=f"{int(width)} x {int(depth)} mm",
            width=width,
            depth=depth,
        )

    override_col_w = inputs.get("override_column_width", 0)
    override_col_d = inputs.get("override_column_depth", 0)
    if (override_col_w and override_col_w > 0) or (override_col_d and override_col_d > 0):
        width = override_col_w if override_col_w > 0 else (
            project.column_result.width if project.column_result else 0
        )
        depth = override_col_d if override_col_d > 0 else (
            project.column_result.depth if project.column_result else 0
        )
        if width <= 0 and project.column_result:
            width = project.column_result.dimension
        if depth <= 0 and project.column_result:
            depth = project.column_result.dimension
        project.column_result = ColumnResult(
            element_type="Column",
            size=f"{int(width)} x {int(depth)} mm",
            width=width,
            depth=depth,
            dimension=max(width, depth),
        )
    
    # Calculate total building dimensions for lateral analysis
    total_width_x = project.geometry.bay_x * project.geometry.num_bays_x
    total_width_y = project.geometry.bay_y * project.geometry.num_bays_y
    
    # Build lateral system with core wall
    has_core = inputs.get("has_core", False)
    selected_core_wall_config = inputs.get("selected_core_wall_config")
    
    if has_core and selected_core_wall_config:
        normalized_config = _normalize_core_wall_config(selected_core_wall_config)

        # Get core wall dimensions (convert from m to mm)
        length_x = inputs.get("length_x")
        length_y = inputs.get("length_y")
        flange_width = inputs.get("flange_width")
        web_length = inputs.get("web_length")
        opening_width = inputs.get("opening_width")
        opening_placement = _normalize_opening_placement(
            inputs.get("selected_opening_placement", TubeOpeningPlacement.TOP_BOT)
        )
        wall_thickness = inputs.get("wall_thickness", 500.0)

        opening_width_mm = None
        if opening_placement != TubeOpeningPlacement.NONE and opening_width:
            opening_width_mm = opening_width * 1000
        
        core_geometry = CoreWallGeometry(
            config=normalized_config,
            wall_thickness=wall_thickness,
            length_x=length_x * 1000 if length_x else 6000.0,
            length_y=length_y * 1000 if length_y else 6000.0,
            opening_width=opening_width_mm,
            opening_height=None,
            flange_width=flange_width * 1000 if flange_width else None,
            web_length=web_length * 1000 if web_length else None,
            opening_placement=opening_placement,
        )
        
        # Calculate section properties
        section_properties = calculate_core_wall_properties(core_geometry)
        
        # Get core location
        selected_core_location = inputs.get("selected_core_location", CoreLocationPreset.CENTER)
        custom_x = inputs.get("custom_x")
        custom_y = inputs.get("custom_y")
        normalized_location = _normalize_location_preset(
            selected_core_location,
            total_width_x,
            total_width_y,
            length_x,
            length_y,
            custom_x,
            custom_y,
        )
        
        project.lateral = LateralInput(
            terrain=inputs.get("selected_terrain", TerrainCategory.URBAN),
            building_width=total_width_x,
            building_depth=total_width_y,
            core_wall_config=normalized_config,
            wall_thickness=wall_thickness,
            core_geometry=core_geometry,
            section_properties=section_properties,
            location_preset=normalized_location,
            custom_center_x=custom_x,
            custom_center_y=custom_y,
        )
    else:
        project.lateral = LateralInput(
            terrain=inputs.get("selected_terrain", TerrainCategory.URBAN),
            building_width=total_width_x,
            building_depth=total_width_y,
        )
    
    # Set load combination
    project.load_combination = inputs.get("selected_load_comb", LoadCombination.ULS_GRAVITY_1)
    
    return project


def get_override_params(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Get override parameters for run_calculations from inputs.
    
    Args:
        inputs: Dict from render_sidebar()
        
    Returns:
        Dict of override parameters for run_calculations
    """
    return {
        "override_slab": inputs.get("override_slab_thickness", 0),
        "override_pri_beam_w": inputs.get("override_pri_beam_width", 0),
        "override_pri_beam_d": inputs.get("override_pri_beam_depth", 0),
        "override_sec_beam_w": inputs.get("override_sec_beam_width", 0),
        "override_sec_beam_d": inputs.get("override_sec_beam_depth", 0),
        "override_col": inputs.get("override_column_size", 0),
        "override_col_w": inputs.get("override_column_width", 0),
        "override_col_d": inputs.get("override_column_depth", 0),
        "secondary_along_x": inputs.get("secondary_along_x", True),
        "num_secondary_beams": inputs.get("num_secondary_beams", 3),
    }


def get_column_omissions_from_session() -> List[str]:
    """Get list of columns to omit from session state.
    
    Returns:
        List of column IDs marked for omission
    """
    import streamlit as st
    
    if "omit_columns" not in st.session_state:
        return []
    
    return [
        col_id for col_id, should_omit in st.session_state.omit_columns.items()
        if should_omit
    ]
