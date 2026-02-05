"""Project builder module - builds ProjectData from sidebar inputs."""

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
    LoadCombination,
    ExposureClass,
    SlabResult,
    BeamResult,
    ColumnResult,
)
from src.core.constants import CONCRETE_DENSITY
from src.fem.core_wall_helpers import calculate_core_wall_properties


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
        loading_pattern_factor=inputs.get("loading_pattern_factor", 1.0),
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
            thickness=override_slab,
            self_weight=thickness_m * CONCRETE_DENSITY,
        )

    override_pri_w = inputs.get("override_pri_beam_width", 0)
    override_pri_d = inputs.get("override_pri_beam_depth", 0)
    if (override_pri_w and override_pri_w > 0) or (override_pri_d and override_pri_d > 0):
        width = override_pri_w if override_pri_w > 0 else (project.primary_beam_result.width if project.primary_beam_result else 0)
        depth = override_pri_d if override_pri_d > 0 else (project.primary_beam_result.depth if project.primary_beam_result else 0)
        project.primary_beam_result = BeamResult(width=width, depth=depth)

    override_sec_w = inputs.get("override_sec_beam_width", 0)
    override_sec_d = inputs.get("override_sec_beam_depth", 0)
    if (override_sec_w and override_sec_w > 0) or (override_sec_d and override_sec_d > 0):
        width = override_sec_w if override_sec_w > 0 else (project.secondary_beam_result.width if project.secondary_beam_result else 0)
        depth = override_sec_d if override_sec_d > 0 else (project.secondary_beam_result.depth if project.secondary_beam_result else 0)
        project.secondary_beam_result = BeamResult(width=width, depth=depth)

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
        # Get core wall dimensions (convert from m to mm)
        length_x = inputs.get("length_x")
        length_y = inputs.get("length_y")
        flange_width = inputs.get("flange_width")
        web_length = inputs.get("web_length")
        opening_width = inputs.get("opening_width")
        opening_height = inputs.get("opening_height")
        wall_thickness = inputs.get("wall_thickness", 500.0)
        
        core_geometry = CoreWallGeometry(
            config=selected_core_wall_config,
            wall_thickness=wall_thickness,
            length_x=length_x * 1000 if length_x else None,
            length_y=length_y * 1000 if length_y else None,
            opening_width=opening_width * 1000 if opening_width else None,
            opening_height=opening_height * 1000 if opening_height else None,
            flange_width=flange_width * 1000 if flange_width else None,
            web_length=web_length * 1000 if web_length else None,
        )
        
        # Calculate section properties
        section_properties = calculate_core_wall_properties(core_geometry)
        
        # Get core location
        selected_core_location = inputs.get("selected_core_location", "Center")
        custom_x = inputs.get("custom_x")
        custom_y = inputs.get("custom_y")
        
        project.lateral = LateralInput(
            terrain=inputs.get("selected_terrain", TerrainCategory.URBAN),
            building_width=total_width_x,
            building_depth=total_width_y,
            core_wall_config=selected_core_wall_config,
            wall_thickness=wall_thickness,
            core_geometry=core_geometry,
            section_properties=section_properties,
            location_type=selected_core_location,
            custom_center_x=custom_x if selected_core_location == "Custom" else None,
            custom_center_y=custom_y if selected_core_location == "Custom" else None,
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
