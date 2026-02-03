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
    ExposureClass,
    LoadCombination,
    PRESETS,
)
from src.core.load_tables import LIVE_LOAD_TABLE
from src.fem.load_combinations import (
    LoadCombinationLibrary,
    LoadCombinationCategory,
)
from src.fem.model_builder import get_column_omission_suggestions
from src.ui.theme import GEMINI_TOKENS


def render_sidebar(project: ProjectData) -> Dict[str, Any]:
    """Render all sidebar controls and return user inputs.
    
    Args:
        project: Current project data for default values
        
    Returns:
        Dictionary of all user inputs from sidebar controls
    """
    inputs: Dict[str, Any] = {}
    
    with st.sidebar:
        st.header("Project Settings")
        
        # Quick presets
        inputs.update(_render_preset_selector())
        
        # Geometry inputs
        inputs.update(_render_geometry_inputs(project))
        
        # Loading inputs
        inputs.update(_render_loading_inputs(project))
        
        # Material inputs
        inputs.update(_render_material_inputs(project))
        
        # Beam configuration
        inputs.update(_render_beam_config())
        
        # Lateral system
        inputs.update(_render_lateral_system(project))
        
        # Column omission
        inputs.update(_render_column_omission(project))
        
        # Overrides
        inputs.update(_render_overrides(project))
        
        # Load combinations
        inputs.update(_render_load_combinations())
    
    return inputs


def _render_preset_selector() -> Dict[str, Any]:
    """Render quick preset selector.
    
    Returns:
        Dict with 'selected_preset' key (str: preset key or 'custom')
    """
    st.markdown("##### Quick Presets")
    
    preset_options = ["Custom"] + [PRESETS[k]["name"] for k in PRESETS.keys()]
    preset_keys = ["custom"] + list(PRESETS.keys())
    
    selected_preset_name = st.selectbox(
        "Building Type",
        options=preset_options,
        help="Select a preset to auto-fill typical values"
    )
    selected_preset = preset_keys[preset_options.index(selected_preset_name)]
    
    if selected_preset != "custom" and st.button("Apply Preset"):
        preset = PRESETS[selected_preset]
        st.session_state.project.loads = preset["loads"]
        st.session_state.project.materials = preset["materials"]
        st.rerun()
    
    st.divider()
    
    return {"selected_preset": selected_preset}


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
            max_value=15.0,
            value=float(project.geometry.bay_x)
        )
    with col2:
        bay_y = st.number_input(
            "Bay Y (m)", 
            min_value=3.0, 
            max_value=15.0,
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


def _render_lateral_system(project: ProjectData) -> Dict[str, Any]:
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
    
    selected_terrain_label = st.selectbox(
        "Terrain Category",
        options=list(terrain_options.values()),
        index=list(terrain_options.keys()).index(project.lateral.terrain)
    )
    selected_terrain = list(terrain_options.keys())[
        list(terrain_options.values()).index(selected_terrain_label)
    ]
    
    has_core = st.checkbox(
        "Core Wall System",
        value=project.lateral.core_wall_config is not None
    )
    
    # Initialize defaults
    selected_core_location = "Center"
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
            CoreWallConfig.TWO_C_FACING: "Two C-Walls Facing",
            CoreWallConfig.TWO_C_BACK_TO_BACK: "Two C-Walls Back-to-Back",
            CoreWallConfig.TUBE_CENTER_OPENING: "Tube with Center Opening",
            CoreWallConfig.TUBE_SIDE_OPENING: "Tube with Side Opening"
        }
        
        # Get current config or default to I_SECTION
        current_config = project.lateral.core_wall_config or CoreWallConfig.I_SECTION
        selected_config_label = st.selectbox(
            "Core Wall Configuration",
            options=list(config_options.values()),
            index=list(config_options.keys()).index(current_config),
            help="Select the core wall configuration type for FEM modeling"
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
            help="Core wall thickness in millimeters (typical: 500mm)"
        )
        
        # Dimension inputs depend on configuration type
        if selected_core_wall_config in [
            CoreWallConfig.I_SECTION, 
            CoreWallConfig.TWO_C_FACING, 
            CoreWallConfig.TWO_C_BACK_TO_BACK
        ]:
            st.caption("I-Section / C-Wall Dimensions")
            col1, col2 = st.columns(2)
            with col1:
                flange_width = st.number_input(
                    "Flange Width (m)", 
                    min_value=2.0, 
                    max_value=15.0, 
                    value=6.0,
                    help="Width of horizontal flange"
                )
            with col2:
                web_length = st.number_input(
                    "Web Length (m)", 
                    min_value=2.0, 
                    max_value=20.0, 
                    value=8.0,
                    help="Length of vertical web"
                )
            
            # For C-walls, add opening width
            if selected_core_wall_config in [
                CoreWallConfig.TWO_C_FACING, 
                CoreWallConfig.TWO_C_BACK_TO_BACK
            ]:
                opening_width = st.number_input(
                    "Opening Width (m)", 
                    min_value=1.0, 
                    max_value=10.0, 
                    value=3.0,
                    help="Width of opening between/within C-walls"
                )
            
            # Set length from dimensions
            length_x = flange_width
            length_y = web_length
            
        else:  # TUBE configurations
            st.caption("Tube Dimensions")
            col1, col2 = st.columns(2)
            with col1:
                length_x = st.number_input(
                    "Length X (m)", 
                    min_value=2.0, 
                    max_value=15.0, 
                    value=6.0,
                    help="Outer dimension in X direction"
                )
            with col2:
                length_y = st.number_input(
                    "Length Y (m)", 
                    min_value=2.0, 
                    max_value=15.0, 
                    value=6.0,
                    help="Outer dimension in Y direction"
                )
            
            st.caption("Opening Dimensions")
            col1, col2 = st.columns(2)
            with col1:
                opening_width = st.number_input(
                    "Opening Width (m)", 
                    min_value=0.5, 
                    max_value=5.0, 
                    value=2.0,
                    help="Width of opening"
                )
            with col2:
                opening_height = st.number_input(
                    "Opening Height (m)", 
                    min_value=0.5, 
                    max_value=5.0, 
                    value=2.0,
                    help="Height of opening"
                )
        
        # Core Position UI
        st.caption("Core Position")
        core_loc_type = st.radio(
            "Position Type",
            options=["Center", "Custom"],
            index=0,
            horizontal=True,
            help="Place core at building center or define specific coordinates."
        )
        
        if core_loc_type == "Custom":
            # Get building dimensions from session state
            bay_x = st.session_state.project.geometry.bay_x
            bay_y = st.session_state.project.geometry.bay_y
            num_bays_x = st.session_state.project.geometry.num_bays_x
            num_bays_y = st.session_state.project.geometry.num_bays_y
            b_width = bay_x * num_bays_x
            b_depth = bay_y * num_bays_y
            
            st.caption(f"Building: {b_width:.1f}m x {b_depth:.1f}m")
            st.info(
                "**Coordinate System:** Origin (0, 0) is at the bottom-left corner. "
                "X-axis runs left-to-right, Y-axis runs bottom-to-top."
            )
            
            l_col, r_col = st.columns(2)
            
            # Calculate safe min/max
            core_dim_x = length_x if length_x else 6.0
            core_dim_y = length_y if length_y else 6.0
            half_core_x = core_dim_x / 2.0
            half_core_y = core_dim_y / 2.0
            min_x = max(0.0, half_core_x)
            max_x = max(min_x + 0.1, b_width - half_core_x)
            min_y = max(0.0, half_core_y)
            max_y = max(min_y + 0.1, b_depth - half_core_y)
            
            with l_col:
                custom_x = st.number_input(
                    "Center X (m)",
                    min_value=0.0,
                    max_value=float(b_width),
                    value=float(b_width / 2),
                    help=f"X-coordinate of core centroid (valid: {min_x:.1f}m - {max_x:.1f}m)"
                )
            with r_col:
                custom_y = st.number_input(
                    "Center Y (m)",
                    min_value=0.0,
                    max_value=float(b_depth),
                    value=float(b_depth / 2),
                    help=f"Y-coordinate of core centroid (valid: {min_y:.1f}m - {max_y:.1f}m)"
                )
            
            # Validation warnings
            if custom_x < min_x or custom_x > max_x:
                st.warning(f"Core may extend outside building in X direction. "
                          f"Recommended: {min_x:.1f}m - {max_x:.1f}m")
            if custom_y < min_y or custom_y > max_y:
                st.warning(f"Core may extend outside building in Y direction. "
                          f"Recommended: {min_y:.1f}m - {max_y:.1f}m")
            
            selected_core_location = "Custom"
        else:
            selected_core_location = "Center"
    
    return {
        "selected_terrain": selected_terrain,
        "has_core": has_core,
        "selected_core_wall_config": selected_core_wall_config,
        "wall_thickness": wall_thickness,
        "flange_width": flange_width,
        "web_length": web_length,
        "length_x": length_x,
        "length_y": length_y,
        "opening_width": opening_width,
        "opening_height": opening_height,
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
    """Render design override controls.
    
    Returns:
        Dict with override values (0 = use calculated)
    """
    st.markdown("##### Element Overrides")
    
    use_overrides = st.checkbox(
        "Override calculated sizes", 
        value=False,
        help="Enable manual override of structural element sizes"
    )
    
    if use_overrides:
        st.caption("Leave at 0 to use calculated values")
        override_slab_thickness = st.number_input(
            "Slab Thickness (mm)", 
            min_value=0, 
            value=0,
            help="Override slab thickness (0 = auto)"
        )
        
        st.caption("Primary Beam")
        col1, col2 = st.columns(2)
        with col1:
            override_pri_beam_width = st.number_input(
                "Pri. Width (mm)", 
                min_value=0, 
                value=0,
                help="Primary beam width (0 = auto)"
            )
        with col2:
            override_pri_beam_depth = st.number_input(
                "Pri. Depth (mm)", 
                min_value=0, 
                value=0,
                help="Primary beam depth (0 = auto)"
            )
        
        st.caption("Secondary Beam")
        col1, col2 = st.columns(2)
        with col1:
            override_sec_beam_width = st.number_input(
                "Sec. Width (mm)", 
                min_value=0, 
                value=0,
                help="Secondary beam width (0 = auto)"
            )
        with col2:
            override_sec_beam_depth = st.number_input(
                "Sec. Depth (mm)", 
                min_value=0, 
                value=0,
                help="Secondary beam depth (0 = auto)"
            )
        
        override_column_size = st.number_input(
            "Column Size (mm)", 
            min_value=0, 
            value=0,
            help="Override column dimension (0 = auto)"
        )
    else:
        override_slab_thickness = 0
        override_pri_beam_width = 0
        override_pri_beam_depth = 0
        override_sec_beam_width = 0
        override_sec_beam_depth = 0
        override_column_size = 0
    
    st.divider()
    
    return {
        "override_slab_thickness": override_slab_thickness,
        "override_pri_beam_width": override_pri_beam_width,
        "override_pri_beam_depth": override_pri_beam_depth,
        "override_sec_beam_width": override_sec_beam_width,
        "override_sec_beam_depth": override_sec_beam_depth,
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
