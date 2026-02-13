"""Sidebar controls for PrelimStruct dashboard."""

from typing import Dict, Any, Optional, List
import streamlit as st

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
    ExposureClass,
    LoadCombination,
    WindResult,
)
from src.core.load_tables import LIVE_LOAD_TABLE
from src.fem.load_combinations import (
    LoadCombinationLibrary,
    LoadCombinationCategory,
)
from src.fem.model_builder import get_column_omission_suggestions
from src.fem.wind_calculator import calculate_hk_wind
from src.ui.theme import GEMINI_TOKENS


def render_sidebar(project: ProjectData) -> Dict[str, Any]:
    """Render all sidebar controls and return user inputs.
    
    Args:
        project: Current project data for default values
        
    Returns:
        Dictionary of all user inputs from sidebar controls
    """
    inputs: Dict[str, Any] = {}
    inputs_locked = _is_inputs_locked()
    
    with st.sidebar:
        st.header("Project Settings")

        if inputs_locked:
            st.warning("🔒 **Inputs locked** - Analysis results active. Click 'Unlock to Modify' in FEM section to change inputs.")
        
        # Geometry inputs
        inputs.update(_render_geometry_inputs(project))
        
        # Loading inputs
        inputs.update(_render_loading_inputs(project))
        
        # Material inputs
        inputs.update(_render_material_inputs(project))
        
        # Beam configuration
        inputs.update(_render_beam_config())
        
        # Lateral system
        inputs.update(_render_lateral_system(project, inputs_locked))
        
        # Column omission
        inputs.update(_render_column_omission(project))
        
        # Overrides
        inputs.update(_render_overrides(project))
        
        # Load combinations
        inputs.update(_render_load_combinations())
    
    return inputs


def _is_inputs_locked() -> bool:
    return st.session_state.get("fem_inputs_locked", False)


def _render_geometry_inputs(project: ProjectData) -> Dict[str, Any]:
    """Render geometry input controls.
    
    Returns:
        Dict with keys: bay_x, bay_y, num_bays_x, num_bays_y, floors, story_height
    """
    st.markdown("##### Geometry")
    
    col1, col2 = st.columns(2)
    with col1:
        bay_x = st.number_input(
            "Bay X (m)", 
            min_value=3.0, 
            value=float(project.geometry.bay_x)
        )
    with col2:
        bay_y = st.number_input(
            "Bay Y (m)", 
            min_value=3.0, 
            value=float(project.geometry.bay_y)
        )
    
    col1, col2 = st.columns(2)
    with col1:
        num_bays_x = st.number_input(
            "Bays in X", 
            min_value=1, 
            max_value=10,
            value=project.geometry.num_bays_x,
            help="Number of bays in X direction"
        )
    with col2:
        num_bays_y = st.number_input(
            "Bays in Y", 
            min_value=1, 
            max_value=10,
            value=project.geometry.num_bays_y,
            help="Number of bays in Y direction"
        )
    
    col1, col2 = st.columns(2)
    with col1:
        floors = st.number_input(
            "Floors", 
            min_value=1, 
            max_value=50,
            value=project.geometry.floors
        )
    with col2:
        story_height = st.number_input(
            "Story Height (m)", 
            min_value=2.5, 
            max_value=6.0,
            value=float(project.geometry.story_height)
        )
    
    st.divider()
    
    return {
        "bay_x": bay_x,
        "bay_y": bay_y,
        "num_bays_x": num_bays_x,
        "num_bays_y": num_bays_y,
        "floors": floors,
        "story_height": story_height,
    }


def _render_loading_inputs(project: ProjectData) -> Dict[str, Any]:
    """Render loading input controls.
    
    Returns:
        Dict with keys: selected_class, selected_sub, dead_load, custom_live_load_value
    """
    st.markdown("##### Loading")
    
    # Live load class selection - include "9: Other (Custom)" option
    class_options = [(k, v["name"]) for k, v in LIVE_LOAD_TABLE.items()]
    class_options.append(("9", "Other (Custom)"))  # Add custom option as Class 9
    class_labels = [f"{k}: {name}" for k, name in class_options]
    class_keys = [k for k, _ in class_options]
    
    # Get current class, default to "2" if not in valid options
    current_class = project.loads.live_load_class
    if current_class in class_keys:
        default_class_idx = class_keys.index(current_class)
    else:
        default_class_idx = class_keys.index("2") if "2" in class_keys else 0
    
    selected_class_label = st.selectbox(
        "Live Load Class",
        options=class_labels,
        index=default_class_idx
    )
    selected_class = class_keys[class_labels.index(selected_class_label)]
    
    # Custom live load input when "9: Other (Custom)" is selected
    custom_live_load_value: Optional[float] = None
    if selected_class == "9":
        # Show custom kPa input with validation (0.5 - 20.0 kPa)
        current_custom = project.loads.custom_live_load
        default_custom = current_custom if current_custom is not None else 5.0
        custom_live_load_value = st.number_input(
            "Custom Live Load (kPa)",
            min_value=0.5,
            max_value=20.0,
            value=float(default_custom),
            help="Enter custom live load value (0.5 - 20.0 kPa) for special loading conditions"
        )
        selected_sub = "9.0"  # Placeholder subdivision for custom
    else:
        # Live load subdivision from HK Code tables
        if selected_class in LIVE_LOAD_TABLE:
            sub_options = [(e.code, e.description, e.get_load()) for e in LIVE_LOAD_TABLE[selected_class]["loads"]]
            sub_labels = [f"{code}: {desc} ({load:.1f} kPa)" for code, desc, load in sub_options]
            sub_codes = [code for code, _, _ in sub_options]
            
            current_sub = project.loads.live_load_sub
            default_idx = sub_codes.index(current_sub) if current_sub in sub_codes else 0
            
            selected_sub_label = st.selectbox("Subdivision", options=sub_labels, index=default_idx)
            selected_sub = sub_codes[sub_labels.index(selected_sub_label)]
        else:
            selected_sub = "2.5"
    
    dead_load = st.number_input(
        "SDL (kPa)", 
        min_value=0.5, 
        max_value=10.0,
        value=float(project.loads.dead_load),
        help="Superimposed Dead Load (finishes, services)"
    )
    
    st.divider()
    
    return {
        "selected_class": selected_class,
        "selected_sub": selected_sub,
        "dead_load": dead_load,
        "custom_live_load_value": custom_live_load_value,
    }


def _render_material_inputs(project: ProjectData) -> Dict[str, Any]:
    """Render material input controls.
    
    Returns:
        Dict with keys: fcu_slab, fcu_beam, fcu_column, selected_exposure
    """
    st.markdown("##### Materials")
    
    concrete_grades = [25, 30, 35, 40, 45, 50, 55, 60]
    
    col1, col2 = st.columns(2)
    with col1:
        fcu_slab = st.selectbox(
            "Slab fcu", 
            options=concrete_grades,
            index=concrete_grades.index(project.materials.fcu_slab)
        )
    with col2:
        fcu_beam = st.selectbox(
            "Beam fcu", 
            options=concrete_grades,
            index=concrete_grades.index(project.materials.fcu_beam)
        )
    
    fcu_column = st.selectbox(
        "Column fcu", 
        options=concrete_grades,
        index=concrete_grades.index(project.materials.fcu_column)
    )
    
    exposure_options = {
        ExposureClass.MILD: "1: Mild (Interior)",
        ExposureClass.MODERATE: "2: Moderate (Sheltered)",
        ExposureClass.SEVERE: "3: Severe (Exposed)",
        ExposureClass.VERY_SEVERE: "4: Very Severe (Marine)",
        ExposureClass.ABRASIVE: "5: Abrasive (Chemical)"
    }
    
    selected_exposure_label = st.selectbox(
        "Exposure Class",
        options=list(exposure_options.values()),
        index=list(exposure_options.keys()).index(project.materials.exposure)
    )
    selected_exposure = list(exposure_options.keys())[
        list(exposure_options.values()).index(selected_exposure_label)
    ]
    
    st.divider()
    
    return {
        "fcu_slab": fcu_slab,
        "fcu_beam": fcu_beam,
        "fcu_column": fcu_column,
        "selected_exposure": selected_exposure,
    }


def _render_beam_config() -> Dict[str, Any]:
    """Render beam configuration controls.
    
    Returns:
        Dict with keys: secondary_along_x, num_secondary_beams
    """
    st.markdown("##### Beam Configuration")
    
    secondary_beam_dir = st.radio(
        "Secondary Beam Direction",
        options=["Along X", "Along Y"],
        index=0,
        horizontal=True,
        help="Direction of secondary beams (internal beams). Primary beams are on the perimeter."
    )
    secondary_along_x = secondary_beam_dir == "Along X"
    
    num_secondary_beams = st.number_input(
        "Number of Secondary Beams",
        min_value=0, 
        max_value=10, 
        value=3,
        help="Number of internal secondary beams equally spaced within the bay (0 = no secondary beams)"
    )
    
    st.divider()
    
    return {
        "secondary_along_x": secondary_along_x,
        "num_secondary_beams": num_secondary_beams,
    }


def _render_lateral_system(project: ProjectData, inputs_locked: bool) -> Dict[str, Any]:
    """Render lateral system and core wall configuration.
    
    Returns:
        Dict with keys for terrain, core wall config, dimensions, and position
    """
    st.markdown("##### Lateral System")
    
    terrain_options = {
        TerrainCategory.OPEN_SEA: "A: Open Sea",
        TerrainCategory.OPEN_COUNTRY: "B: Open Country",
        TerrainCategory.URBAN: "C: Urban",
        TerrainCategory.CITY_CENTRE: "D: City Centre"
    }
    
    current_terrain = project.lateral.terrain
    if current_terrain in terrain_options:
        terrain_index = list(terrain_options.keys()).index(current_terrain)
    else:
        terrain_index = list(terrain_options.keys()).index(TerrainCategory.URBAN)

    selected_terrain_label = st.selectbox(
        "Terrain Category",
        options=list(terrain_options.values()),
        index=terrain_index,
        disabled=inputs_locked,
    )
    selected_terrain = list(terrain_options.keys())[
        list(terrain_options.values()).index(selected_terrain_label)
    ]

    width_x = project.geometry.bay_x * project.geometry.num_bays_x
    width_y = project.geometry.bay_y * project.geometry.num_bays_y
    existing_wind = project.wind_result
    default_vx = 0.0
    default_vy = 0.0
    default_reference_pressure = 3.0
    default_force_coefficient = 1.3
    if existing_wind is not None:
        if existing_wind.base_shear_x > 0.0 or existing_wind.base_shear_y > 0.0:
            default_vx = existing_wind.base_shear_x
            default_vy = existing_wind.base_shear_y
        else:
            default_vx = existing_wind.base_shear
            default_vy = existing_wind.base_shear
        if existing_wind.reference_pressure > 0.0:
            default_reference_pressure = existing_wind.reference_pressure

    wind_input_mode = st.radio(
        "Wind Input Mode",
        options=["Manual", "HK Code Calculator"],
        key="sidebar_module_wind_input_mode",
        horizontal=True,
        disabled=inputs_locked,
    )

    if wind_input_mode == "Manual":
        base_shear_x = st.number_input(
            "Base Shear Vx (kN)",
            min_value=0.0,
            value=float(default_vx),
            step=10.0,
            key="sidebar_module_wind_base_shear_x",
            disabled=inputs_locked,
        )
        base_shear_y = st.number_input(
            "Base Shear Vy (kN)",
            min_value=0.0,
            value=float(default_vy),
            step=10.0,
            key="sidebar_module_wind_base_shear_y",
            disabled=inputs_locked,
        )
        reference_pressure = st.number_input(
            "Reference Pressure q0 (kPa)",
            min_value=0.0,
            value=float(default_reference_pressure),
            step=0.1,
            key="sidebar_module_wind_reference_pressure_manual",
            disabled=inputs_locked,
        )

        if base_shear_x > 0.0 or base_shear_y > 0.0:
            project_wind_result = WindResult(
                base_shear=max(base_shear_x, base_shear_y),
                base_shear_x=base_shear_x,
                base_shear_y=base_shear_y,
                reference_pressure=reference_pressure,
                lateral_system="CORE_WALL",
            )
        else:
            project_wind_result = None
    else:
        reference_pressure = st.number_input(
            "Reference Pressure q0 (kPa)",
            min_value=0.0,
            value=float(default_reference_pressure),
            step=0.1,
            key="sidebar_module_wind_reference_pressure_calc",
            disabled=inputs_locked,
        )
        force_coefficient = st.number_input(
            "Force Coefficient Cf",
            min_value=0.0,
            value=float(default_force_coefficient),
            step=0.1,
            key="sidebar_module_wind_force_coefficient",
            disabled=inputs_locked,
        )

        project_wind_result = calculate_hk_wind(
            total_height=project.geometry.floors * project.geometry.story_height,
            building_width_x=width_x,
            building_width_y=width_y,
            terrain=selected_terrain,
            reference_pressure=reference_pressure,
            force_coefficient=force_coefficient,
            num_floors=project.geometry.floors,
            story_height=project.geometry.story_height,
        )
        st.info(
            f"Vx = {project_wind_result.base_shear_x:.1f} kN, "
            f"Vy = {project_wind_result.base_shear_y:.1f} kN"
        )

    project.wind_result = project_wind_result
    
    has_core = st.checkbox(
        "Core Wall System",
        value=project.lateral.core_wall_config is not None,
        disabled=inputs_locked,
    )
    
    # Initialize defaults
    selected_core_location = CoreLocationPreset.CENTER
    selected_opening_placement = TubeOpeningPlacement.TOP_BOT
    custom_x: Optional[float] = None
    custom_y: Optional[float] = None
    selected_core_wall_config: Optional[CoreWallConfig] = None
    wall_thickness = 500.0
    flange_width: Optional[float] = None
    web_length: Optional[float] = None
    length_x: Optional[float] = None
    length_y: Optional[float] = None
    opening_width: Optional[float] = None
    opening_height: Optional[float] = None
    
    if has_core:
        # Core wall configuration dropdown
        config_options = {
            CoreWallConfig.I_SECTION: "I-Section (2 Walls Blended)",
            CoreWallConfig.TUBE_WITH_OPENINGS: "Tube with Openings",
        }
        
        # Get current config or default to I_SECTION
        current_config = project.lateral.core_wall_config or CoreWallConfig.I_SECTION
        selected_config_label = st.selectbox(
            "Core Wall Configuration",
            options=list(config_options.values()),
            index=list(config_options.keys()).index(current_config),
            help="Select the core wall configuration type for FEM modeling",
            disabled=inputs_locked,
        )
        selected_core_wall_config = list(config_options.keys())[
            list(config_options.values()).index(selected_config_label)
        ]
        
        # Wall thickness input
        wall_thickness = st.number_input(
            "Wall Thickness (mm)",
            min_value=200, 
            max_value=1000, 
            value=500,
            help="Core wall thickness in millimeters (typical: 500mm)",
            disabled=inputs_locked,
        )
        
        # Dimension inputs depend on configuration type
        if selected_core_wall_config == CoreWallConfig.I_SECTION:
            st.caption("I-Section Dimensions")
            col1, col2 = st.columns(2)
            with col1:
                flange_width = st.number_input(
                    "Flange Width (m)", 
                    min_value=2.0, 
                    max_value=15.0, 
                    value=3.0,
                    help="Width of horizontal flange",
                    disabled=inputs_locked,
                )
            with col2:
                web_length = st.number_input(
                    "Web Length (m)", 
                    min_value=2.0, 
                    max_value=20.0, 
                    value=3.0,
                    help="Length of vertical web",
                    disabled=inputs_locked,
                )
            
            # Set length from dimensions
            length_x = flange_width
            length_y = web_length
            
        else:  # TUBE_WITH_OPENINGS
            st.caption("Tube Dimensions")
            col1, col2 = st.columns(2)
            with col1:
                length_x = st.number_input(
                    "Length X (m)", 
                    min_value=2.0, 
                    max_value=15.0, 
                    value=3.0,
                    help="Outer dimension in X direction",
                    disabled=inputs_locked,
                )
            with col2:
                length_y = st.number_input(
                    "Length Y (m)", 
                    min_value=2.0, 
                    max_value=15.0, 
                    value=3.0,
                    help="Outer dimension in Y direction",
                    disabled=inputs_locked,
                )
            
            placement_labels = {
                TubeOpeningPlacement.TOP_BOT: "Top-Bot",
                TubeOpeningPlacement.NONE: "None",
            }
            selected_placement_label = st.selectbox(
                "Opening Placement",
                options=list(placement_labels.values()),
                index=0,
                help="Choose where tube core openings are placed.",
                disabled=inputs_locked,
                key="sidebar_module_opening_placement",
            )
            selected_opening_placement = list(placement_labels.keys())[
                list(placement_labels.values()).index(selected_placement_label)
            ]

            st.caption("Opening Dimension")
            opening_size = st.number_input(
                "Opening Size (m)",
                min_value=0.5,
                max_value=5.0,
                value=1.0,
                help="Single opening dimension used for top and bottom openings.",
                disabled=inputs_locked or selected_opening_placement == TubeOpeningPlacement.NONE,
            )
            opening_width = (
                None
                if selected_opening_placement == TubeOpeningPlacement.NONE
                else opening_size
            )
            opening_height = None
        
        # Core Location Preset
        st.caption("Core Position")
        preset_labels = {
            CoreLocationPreset.CENTER: "Center",
            CoreLocationPreset.NORTH: "North",
            CoreLocationPreset.SOUTH: "South",
            CoreLocationPreset.EAST: "East",
            CoreLocationPreset.WEST: "West",
            CoreLocationPreset.NORTHEAST: "Northeast",
            CoreLocationPreset.NORTHWEST: "Northwest",
            CoreLocationPreset.SOUTHEAST: "Southeast",
            CoreLocationPreset.SOUTHWEST: "Southwest",
        }
        selected_preset_label = st.selectbox(
            "Location Preset",
            options=list(preset_labels.values()),
            index=0,
            help="Select core wall placement in floor plan. All presets enforce bounding-box clearance.",
            disabled=inputs_locked,
        )
        selected_core_location = list(preset_labels.keys())[
            list(preset_labels.values()).index(selected_preset_label)
        ]
    
    return {
        "selected_terrain": selected_terrain,
        "wind_input_mode": wind_input_mode,
        "has_core": has_core,
        "selected_core_wall_config": selected_core_wall_config,
        "wall_thickness": wall_thickness,
        "flange_width": flange_width,
        "web_length": web_length,
        "length_x": length_x,
        "length_y": length_y,
        "opening_width": opening_width,
        "opening_height": opening_height,
        "selected_opening_placement": selected_opening_placement,
        "selected_core_location": selected_core_location,
        "custom_x": custom_x,
        "custom_y": custom_y,
    }


def _render_column_omission(project: ProjectData) -> Dict[str, Any]:
    """Render column omission controls.
    
    Returns:
        Empty dict - column omission uses session state directly
    """
    # Only show if core wall is configured
    if not project.lateral.core_wall_config:
        return {}
    
    st.divider()
    with st.expander("🔍 Column Omission Review", expanded=False):
        st.info("Columns within 0.5m of core walls can be omitted to avoid conflicts.")
        
        # Get suggestions
        try:
            suggestions = get_column_omission_suggestions(
                project=project,
                threshold_m=0.5
            )
            
            if suggestions:
                st.write(f"**{len(suggestions)} columns suggested for omission:**")
                
                # Initialize session state for omissions if not exists
                if "omit_columns" not in st.session_state:
                    st.session_state.omit_columns = {col_id: True for col_id in suggestions}
                else:
                    # Add new suggestions as True, keep existing preference
                    for col_id in suggestions:
                        if col_id not in st.session_state.omit_columns:
                            st.session_state.omit_columns[col_id] = True
                
                # Display checkboxes
                cols = st.columns(3)
                approved_count = 0
                for i, col_id in enumerate(sorted(suggestions)):
                    col_idx = i % 3
                    is_checked = st.session_state.omit_columns.get(col_id, True)
                    with cols[col_idx]:
                        new_val = st.checkbox(f"{col_id}", value=is_checked, key=f"omit_chk_{col_id}")
                        st.session_state.omit_columns[col_id] = new_val
                        if new_val:
                            approved_count += 1
                
                st.caption(f"✅ {approved_count} columns set to be omitted.")
            else:
                st.success("No columns detected near core wall.")
                
        except Exception as e:
            st.error(f"Could not calculate omissions: {str(e)}")
    
    return {}


def _render_overrides(project: ProjectData) -> Dict[str, Any]:
    """Render section property inputs for FEM model.
    
    Returns:
        Dict with section property values (0 = use calculated)
    """
    st.markdown("##### Section Properties")
    st.caption("Leave at 0 to use calculated values")

    slab_default = project.slab_result.thickness if project.slab_result else 0
    override_slab_thickness = st.number_input(
        "Slab Thickness (mm)",
        min_value=0,
        value=slab_default,
        help="Slab thickness used for FEM (0 = auto)"
    )

    st.caption("Primary Beam")
    col1, col2 = st.columns(2)
    with col1:
        pri_width_default = project.primary_beam_result.width if project.primary_beam_result else 0
        override_pri_beam_width = st.number_input(
            "Pri. Width (mm)",
            min_value=0,
            value=pri_width_default,
            help="Primary beam width (0 = auto)"
        )
    with col2:
        pri_depth_default = project.primary_beam_result.depth if project.primary_beam_result else 0
        override_pri_beam_depth = st.number_input(
            "Pri. Depth (mm)",
            min_value=0,
            value=pri_depth_default,
            help="Primary beam depth (0 = auto)"
        )

    st.caption("Secondary Beam")
    col1, col2 = st.columns(2)
    with col1:
        sec_width_default = project.secondary_beam_result.width if project.secondary_beam_result else 0
        override_sec_beam_width = st.number_input(
            "Sec. Width (mm)",
            min_value=0,
            value=sec_width_default,
            help="Secondary beam width (0 = auto)"
        )
    with col2:
        sec_depth_default = project.secondary_beam_result.depth if project.secondary_beam_result else 0
        override_sec_beam_depth = st.number_input(
            "Sec. Depth (mm)",
            min_value=0,
            value=sec_depth_default,
            help="Secondary beam depth (0 = auto)"
        )

    st.caption("Column")
    col1, col2 = st.columns(2)
    with col1:
        col_width_default = 0
        if project.column_result:
            col_width_default = project.column_result.width or project.column_result.dimension
        override_column_width = st.number_input(
            "Column Width (mm)",
            min_value=0,
            value=col_width_default,
            help="Column width (0 = auto)"
        )
    with col2:
        col_depth_default = 0
        if project.column_result:
            col_depth_default = project.column_result.depth or project.column_result.dimension
        override_column_depth = st.number_input(
            "Column Depth (mm)",
            min_value=0,
            value=col_depth_default,
            help="Column depth (0 = auto)"
        )

    override_column_size = max(override_column_width, override_column_depth)
    
    st.divider()
    
    return {
        "override_slab_thickness": override_slab_thickness,
        "override_pri_beam_width": override_pri_beam_width,
        "override_pri_beam_depth": override_pri_beam_depth,
        "override_sec_beam_width": override_sec_beam_width,
        "override_sec_beam_depth": override_sec_beam_depth,
        "override_column_width": override_column_width,
        "override_column_depth": override_column_depth,
        "override_column_size": override_column_size,
    }


def _render_load_combinations() -> Dict[str, Any]:
    """Render load combination selector.
    
    Returns:
        Dict with selected_load_comb (LoadCombination enum)
    """
    st.markdown("##### Load Combinations")
    
    # Get all available combinations from library
    all_combinations = LoadCombinationLibrary.get_all_combinations()
    
    # Group combinations by category
    gravity_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.ULS_GRAVITY]
    wind_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.ULS_WIND]
    seismic_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.ULS_SEISMIC]
    accidental_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.ULS_ACCIDENTAL]
    sls_combos = [c for c in all_combinations if c.category == LoadCombinationCategory.SLS]
    
    def render_combo_category(
        category_name: str,
        combos: list,
        category_key: str,
        expanded: bool = False
    ) -> int:
        """Render a collapsible category section with checkboxes."""
        if not combos:
            return 0
        
        selected_count = sum(1 for c in combos if c.name in st.session_state.selected_combinations)
        total_count = len(combos)
        
        with st.expander(f"{category_name} ({selected_count}/{total_count})", expanded=expanded):
            # Select All / Select None buttons
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
            with btn_col1:
                if st.button("All", key=f"select_all_{category_key}", width="stretch"):
                    for c in combos:
                        st.session_state.selected_combinations.add(c.name)
                    st.rerun()
            with btn_col2:
                if st.button("None", key=f"select_none_{category_key}", width="stretch"):
                    for c in combos:
                        st.session_state.selected_combinations.discard(c.name)
                    st.rerun()
            
            # Scrollable container for combinations (using container with max height)
            if len(combos) > 10:
                combo_container = st.container(height=300)
            else:
                combo_container = st.container()
            
            with combo_container:
                if len(combos) > 10:
                    # Wind combos - use 3 columns for compact display
                    cols = st.columns(3)
                    for i, combo in enumerate(combos):
                        col_idx = i % 3
                        with cols[col_idx]:
                            is_selected = combo.name in st.session_state.selected_combinations
                            label = f"{combo.name}"
                            if st.checkbox(label, value=is_selected, key=f"combo_{combo.name}",
                                          help=combo.to_equation()):
                                st.session_state.selected_combinations.add(combo.name)
                            else:
                                st.session_state.selected_combinations.discard(combo.name)
                else:
                    # Other categories - use 2 columns
                    cols = st.columns(2) if len(combos) > 1 else st.columns(1)
                    for i, combo in enumerate(combos):
                        col_idx = i % len(cols)
                        with cols[col_idx]:
                            is_selected = combo.name in st.session_state.selected_combinations
                            label = f"{combo.name}: {combo.to_equation()}"
                            if st.checkbox(label, value=is_selected, key=f"combo_{combo.name}",
                                          help=combo.description):
                                st.session_state.selected_combinations.add(combo.name)
                            else:
                                st.session_state.selected_combinations.discard(combo.name)
        
        return selected_count
    
    # Render each category
    render_combo_category("Gravity (ULS)", gravity_combos, "gravity", expanded=True)
    render_combo_category("Wind (ULS)", wind_combos, "wind", expanded=False)
    render_combo_category("Seismic (ULS)", seismic_combos, "seismic", expanded=False)
    render_combo_category("Accidental (ULS)", accidental_combos, "accidental", expanded=False)
    render_combo_category("Serviceability (SLS)", sls_combos, "sls", expanded=True)
    
    # Total count display
    total_selected = len(st.session_state.selected_combinations)
    total_available = len(all_combinations)
    st.caption(f"**Total: {total_selected}/{total_available} combinations selected**")
    
    # Active combination for simplified design (backwards compatibility)
    active_combo_options = {}
    for c in all_combinations:
        if c.name in st.session_state.selected_combinations:
            active_combo_options[c.combination_type] = f"{c.name}: {c.to_equation()}"
    
    if active_combo_options:
        st.markdown("**Active Combination for Design:**")
        selected_comb_label = st.selectbox(
            "Active Combination",
            options=list(active_combo_options.values()),
            index=0,
            label_visibility="collapsed",
            help="This combination is used for the simplified design calculations"
        )
        # Find the LoadCombination enum for the selected label
        selected_load_comb = list(active_combo_options.keys())[
            list(active_combo_options.values()).index(selected_comb_label)
        ]
    else:
        # Fallback to default if nothing selected
        selected_load_comb = LoadCombination.ULS_GRAVITY_1
        st.warning("No combinations selected. Using default ULS Gravity combination.")
    
    return {"selected_load_comb": selected_load_comb}
